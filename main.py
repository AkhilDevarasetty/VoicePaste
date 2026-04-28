"""VoicePaste entry point — wires recorder, transcriber, hotkey, paster, and menubar together."""

import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import rumps
from faster_whisper import WhisperModel

try:
    import AppKit
except ImportError:
    AppKit = None

import app_logger
import config
import enhancer
import overlay
import paster
import transcriber
from hotkey import HotkeyListener
from recorder import (
    Recorder,
    describe_default_input_device,
    probe_microphone_access,
)


class Mode(Enum):
    """User-facing app modes with menubar icon and terminal status line."""

    IDLE = ("", "VoicePaste ready")
    RECORDING = ("\U0001f534", "\U0001f399\ufe0f Recording...")
    TRANSCRIBING = ("\u23f3", "\U0001f504 Transcribing...")
    ENHANCING = ("\u2728", "\u2728 Enhancing...")

    @property
    def icon(self) -> str:
        """Single-glyph menubar title for this mode."""
        return self.value[0]

    @property
    def message(self) -> str:
        """Terminal status line for this mode."""
        return self.value[1]


@dataclass
class AppState:
    """Shared state passed to every event handler.

    Holds references to all long-lived components (rumps app, Whisper model,
    Recorder, HotkeyListener) plus the current mode. Mutated only via
    ``set_mode()`` so the menubar icon and terminal output stay in sync.
    """

    app: rumps.App
    logger: app_logger.SessionLogger
    model: WhisperModel
    recorder: Recorder
    hotkey: Optional[HotkeyListener] = None
    overlay_controller: Optional[overlay.FloatingPillController] = None
    mode: Mode = Mode.IDLE
    state_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    hotkey_press_count: int = 0
    hotkey_release_count: int = 0
    recording_attempt_count: int = 0
    active_recording_id: Optional[int] = None
    release_in_progress: bool = False
    recording_session_kind: Optional[str] = None
    hands_free_start_count: int = 0
    hands_free_stop_count: int = 0


def overlay_mode(mode: Mode) -> overlay.OverlayMode:
    """Map app modes to the smaller set of floating pill overlay states."""
    if mode == Mode.RECORDING:
        return overlay.RECORDING_MODE
    if mode in {Mode.TRANSCRIBING, Mode.ENHANCING}:
        return overlay.PROCESSING_MODE
    return overlay.IDLE_MODE


def sync_overlay_interaction(state: AppState) -> None:
    """Keep the overlay click affordance aligned with hands-free state."""
    if state.overlay_controller is None:
        return
    with state.state_lock:
        enable_stop = (
            state.mode == Mode.RECORDING
            and state.recording_session_kind == "hands_free"
        )
    state.overlay_controller.set_hands_free_stop_enabled(enable_stop)


def set_mode(state: AppState, mode: Mode) -> None:
    """Update mode, menubar icon, and terminal status line atomically.

    Called from the pynput listener thread (press/release) and the worker
    thread (after transcription). Cocoa technically wants UI mutations on
    the main thread, but rumps' ``app.title`` setter is a simple string
    assignment that survives cross-thread use in practice.
    """
    with state.state_lock:
        previous_mode = state.mode
        state.mode = mode
    state.logger.debug(f"[state] mode transition {previous_mode.name} -> {mode.name}")
    state.app.title = mode.icon
    if state.overlay_controller is not None:
        state.overlay_controller.set_mode(overlay_mode(mode))
    sync_overlay_interaction(state)
    state.logger.info(mode.message)


def play_feedback_sound(
    logger: app_logger.SessionLogger,
    sound_name: str,
) -> None:
    """Play a short macOS-native feedback sound when enabled."""
    if not config.ENABLE_FEEDBACK_SOUNDS:
        return
    if AppKit is None:
        logger.debug(f"[sound] AppKit unavailable; skipped sound {sound_name!r}")
        return
    try:
        sound = AppKit.NSSound.soundNamed_(sound_name)
        if sound is None:
            logger.debug(f"[sound] sound {sound_name!r} not found")
            return
        played = sound.play()
        if not played:
            logger.debug(f"[sound] sound {sound_name!r} did not start playing")
    except Exception as exc:
        logger.debug(
            f"[sound] failed to play {sound_name!r}: {type(exc).__name__}: {exc}"
        )


def _is_hands_free_recording_active(state: AppState) -> bool:
    """Return whether a hands-free recording session is currently active."""
    with state.state_lock:
        return (
            state.mode == Mode.RECORDING
            and state.recording_session_kind == "hands_free"
        )


def _start_recording_session(
    state: AppState,
    session_kind: str,
    source_label: str,
    failure_label: str,
) -> None:
    """Start a recording session and reuse the existing recorder pipeline."""
    with state.state_lock:
        current_mode = state.mode
        current_recording_id = state.active_recording_id
    state.logger.debug(
        f"[recording] {source_label} start requested while mode={current_mode.name} "
        f"active_recording_id={current_recording_id}"
    )
    if current_mode != Mode.IDLE:
        state.logger.debug(
            f"[recording] {source_label} start ignored because the app is busy in "
            f"mode={current_mode.name}"
        )
        return
    try:
        state.recorder.start(session_kind=session_kind)
    except Exception as exc:
        state.logger.exception(
            failure_label,
            exc,
        )
        state.logger.info("   If this looks like a microphone permission issue, grant access in")
        state.logger.info(
            "   System Settings \u2192 Privacy & Security \u2192 Microphone and restart."
        )
        return
    with state.state_lock:
        state.recording_attempt_count += 1
        state.active_recording_id = state.recording_attempt_count
        state.recording_session_kind = session_kind
        recording_id = state.active_recording_id
    state.logger.debug(
        f"[recording {recording_id}] started "
        f"(session_kind={session_kind}, source={source_label})"
    )
    set_mode(state, Mode.RECORDING)
    play_feedback_sound(state.logger, config.RECORDING_START_SOUND_NAME)
    if session_kind == "hands_free":
        state.logger.info(
            "Hands-free recording started. Click the pill stop button, or pause for "
            f"{config.HANDS_FREE_SILENCE_SECONDS:.0f}s."
        )


def handle_press(state: AppState) -> None:
    """Hold-to-talk hotkey pressed — start recording."""
    with state.state_lock:
        state.hotkey_press_count += 1
        press_count = state.hotkey_press_count
        current_mode = state.mode
        current_recording_id = state.active_recording_id
    state.logger.debug(
        f"[hotkey] hold press #{press_count} received while mode={current_mode.name} "
        f"active_recording_id={current_recording_id}"
    )
    _start_recording_session(
        state,
        session_kind="hold",
        source_label=f"hold press #{press_count}",
        failure_label=f"\u274c failed to start recording on hold press #{press_count}",
    )


def handle_release(state: AppState) -> None:
    """Hotkey released — immediately hand off to a worker thread and return.

    Returns instantly so the pynput listener thread is never blocked by
    recorder.stop() while the app is transitioning out of recording.
    """
    with state.state_lock:
        state.hotkey_release_count += 1
        release_count = state.hotkey_release_count
        current_mode = state.mode
        recording_id = state.active_recording_id
        release_in_progress = state.release_in_progress
        session_kind = state.recording_session_kind
        if current_mode == Mode.RECORDING and not release_in_progress:
            state.release_in_progress = True
    state.logger.debug(
        f"[hotkey] hold release #{release_count} received while mode={current_mode.name} "
        f"active_recording_id={recording_id} session_kind={session_kind}"
    )
    if current_mode != Mode.RECORDING:
        state.logger.debug(
            f"[hotkey] hold release #{release_count} ignored because the app is in "
            f"mode={current_mode.name}"
        )
        return
    if session_kind == "hands_free":
        with state.state_lock:
            if state.release_in_progress:
                state.release_in_progress = False
        state.logger.debug(
            f"[hotkey] hold release #{release_count} ignored because hands-free recording is active"
        )
        return
    if release_in_progress:
        state.logger.debug(
            f"[hotkey] hold release #{release_count} ignored because stop is in progress"
        )
        return
    threading.Thread(
        target=_release_worker,
        args=(state, recording_id, "hotkey_release"),
        name=f"release-worker-{recording_id}",
        daemon=True,
    ).start()


def handle_hands_free_start(state: AppState) -> None:
    """Start a hands-free recording session from the dedicated chord."""
    with state.state_lock:
        state.hands_free_start_count += 1
        start_count = state.hands_free_start_count
        current_mode = state.mode
        current_recording_id = state.active_recording_id
        current_session_kind = state.recording_session_kind
        release_in_progress = state.release_in_progress
    state.logger.debug(
        f"[hotkey] hands-free start #{start_count} received while mode={current_mode.name} "
        f"active_recording_id={current_recording_id}"
    )
    if (
        current_mode == Mode.RECORDING
        and current_session_kind == "hold"
        and not release_in_progress
    ):
        converted = state.recorder.enable_hands_free_mode()
        if not converted:
            state.logger.debug(
                f"[recording] hands-free start #{start_count} conversion failed while hold recording was active"
            )
            return
        with state.state_lock:
            state.recording_session_kind = "hands_free"
            recording_id = state.active_recording_id
        sync_overlay_interaction(state)
        state.logger.debug(
            f"[recording {recording_id}] converted active hold recording to hands-free "
            f"(source=hands-free start #{start_count})"
        )
        state.logger.info(
            "Hands-free mode engaged. Click the pill stop button, or pause for "
            f"{config.HANDS_FREE_SILENCE_SECONDS:.0f}s."
        )
        return
    _start_recording_session(
        state,
        session_kind="hands_free",
        source_label=f"hands-free start #{start_count}",
        failure_label=f"\u274c failed to start hands-free recording #{start_count}",
    )


def handle_hands_free_stop(state: AppState) -> None:
    """Stop a hands-free session from the pill."""
    with state.state_lock:
        state.hands_free_stop_count += 1
        stop_count = state.hands_free_stop_count
        current_mode = state.mode
        recording_id = state.active_recording_id
        session_kind = state.recording_session_kind
        release_in_progress = state.release_in_progress
        if (
            current_mode == Mode.RECORDING
            and session_kind == "hands_free"
            and not release_in_progress
        ):
            state.release_in_progress = True
    state.logger.debug(
        f"[hotkey] hands-free stop #{stop_count} received while mode={current_mode.name} "
        f"active_recording_id={recording_id} session_kind={session_kind}"
    )
    if current_mode != Mode.RECORDING or session_kind != "hands_free":
        state.logger.debug(
            f"[hotkey] hands-free stop #{stop_count} ignored because hands-free is not active"
        )
        return
    if release_in_progress:
        state.logger.debug(
            f"[hotkey] hands-free stop #{stop_count} ignored because stop is in progress"
        )
        return
    threading.Thread(
        target=_release_worker,
        args=(state, recording_id, "hands_free_pill"),
        name=f"hands-free-stop-worker-{recording_id}",
        daemon=True,
    ).start()


def _handle_auto_stop(state: AppState, stop_reason: str) -> None:
    """Kick off processing immediately when the recorder auto-stops."""
    followup_reason = {
        "max_duration": "max_duration_followup",
        "silence_timeout": "silence_timeout_followup",
    }.get(stop_reason)
    if followup_reason is None:
        state.logger.debug(f"[recording] unknown auto-stop reason ignored: {stop_reason}")
        return
    with state.state_lock:
        recording_id = state.active_recording_id
        current_mode = state.mode
        release_in_progress = state.release_in_progress
        if current_mode != Mode.RECORDING or release_in_progress:
            state.logger.debug(
                f"[recording {recording_id}] auto-stop callback ignored "
                f"(reason={stop_reason}, mode={current_mode.name}, "
                f"release_in_progress={release_in_progress})"
            )
            return
        state.release_in_progress = True
    state.logger.debug(
        f"[recording {recording_id}] auto-stop callback received "
        f"(reason={stop_reason}); starting processing immediately"
    )
    threading.Thread(
        target=_release_worker,
        args=(state, recording_id, followup_reason),
        name=f"auto-stop-worker-{recording_id}",
        daemon=True,
    ).start()


def _release_worker(
    state: AppState,
    recording_id: Optional[int],
    stop_reason: str,
) -> None:
    """Stop recording, validate, transcribe, and paste — runs off the pynput thread."""
    worker_started = time.perf_counter()
    state.logger.debug(f"[recording {recording_id}] release worker started")
    try:
        stop_started = time.perf_counter()
        result = state.recorder.stop(reason=stop_reason)
        stop_elapsed = time.perf_counter() - stop_started
        audio = result.audio
        state.logger.debug(
            f"[recording {recording_id}] recorder.stop completed "
            f"(was_recording={result.was_recording}, stop_reason={result.stop_reason}, "
            f"previous_stop_reason={result.previous_stop_reason}, "
            f"duration={result.duration_seconds:.2f}s, chunks={result.chunk_count}, "
            f"samples={audio.size}, elapsed={stop_elapsed:.2f}s)"
        )

        if audio.size == 0:
            if (
                not result.was_recording
                and result.previous_stop_reason in {"max_duration", "silence_timeout"}
            ):
                state.logger.debug(
                    f"[recording {recording_id}] no audio returned because the "
                    "recorder had already auto-stopped before the follow-up stop"
                )
            else:
                state.logger.debug(
                    f"[recording {recording_id}] no audio captured after release"
                )
            state.logger.warning("\u26a0\ufe0f  no audio captured \u2014 skipping")
            return

        min_samples = int(config.MIN_RECORDING_SECONDS * config.SAMPLE_RATE)
        if audio.size < min_samples:
            seconds = audio.size / config.SAMPLE_RATE
            state.logger.debug(
                f"[recording {recording_id}] clip too short "
                f"({seconds:.2f}s < {config.MIN_RECORDING_SECONDS:.2f}s)"
            )
            state.logger.warning(
                f"\u26a0\ufe0f  clip too short ({seconds:.2f}s) \u2014 skipping"
            )
            return

        set_mode(state, Mode.TRANSCRIBING)

        transcription_started = time.perf_counter()
        text = transcriber.transcribe(state.model, audio, logger=state.logger.debug)
        transcription_elapsed = time.perf_counter() - transcription_started
        if not text:
            state.logger.warning("\u26a0\ufe0f  empty transcription \u2014 skipping")
            return
        state.logger.debug(
            f"[recording {recording_id}] transcription result "
            f"(chars={len(text)}, words={len(text.split())}, elapsed={transcription_elapsed:.2f}s)"
        )
        enhancement_elapsed = 0.0
        if (
            config.READABILITY_MODE == "openai"
            and len(text.strip()) >= config.MIN_TEXT_LENGTH_FOR_ENHANCEMENT
        ):
            set_mode(state, Mode.ENHANCING)
        enhancement_started = time.perf_counter()
        final_text = enhancer.enhance(text, logger=state.logger.debug)
        enhancement_elapsed = time.perf_counter() - enhancement_started
        state.logger.debug(
            f"[recording {recording_id}] final text ready "
            f"(chars={len(final_text)}, words={len(final_text.split())}, "
            f"enhancement_elapsed={enhancement_elapsed:.2f}s)"
        )
        state.logger.transcript(final_text)
        paste_started = time.perf_counter()
        paster.paste(final_text, logger=state.logger.debug)
        paste_elapsed = time.perf_counter() - paste_started
        play_feedback_sound(state.logger, config.PASTE_COMPLETE_SOUND_NAME)
        total_elapsed = time.perf_counter() - worker_started
        state.logger.debug(
            f"[recording {recording_id}] pipeline completed "
            f"(stop={stop_elapsed:.2f}s, transcribe={transcription_elapsed:.2f}s, "
            f"enhance={enhancement_elapsed:.2f}s, paste={paste_elapsed:.2f}s, "
            f"total={total_elapsed:.2f}s)"
        )
    except Exception as exc:
        state.logger.exception(f"\u274c worker error for recording {recording_id}", exc)
    finally:
        with state.state_lock:
            if state.active_recording_id == recording_id:
                state.active_recording_id = None
            state.release_in_progress = False
            state.recording_session_kind = None
        set_mode(state, Mode.IDLE)


def check_accessibility(logger: app_logger.SessionLogger) -> None:
    """Verify macOS Accessibility permission for the host app running VoicePaste.

    Required for pynput (global hotkey and synthetic Cmd+V).
    Exits cleanly with step-by-step instructions if not granted.
    """
    try:
        from ApplicationServices import AXIsProcessTrusted
    except ImportError:
        # pyobjc bridge unavailable — defer to runtime failure in pynput.
        logger.debug("[startup] ApplicationServices unavailable; skipping explicit Accessibility preflight")
        return
    logger.debug("[startup] checking Accessibility permission")
    if AXIsProcessTrusted():
        logger.debug("[startup] Accessibility permission confirmed")
        return
    logger.error("\u274c Accessibility permission not granted.")
    logger.info("")
    logger.info("   VoicePaste needs Accessibility access to listen for the global")
    logger.info("   hotkey and paste at the cursor (pynput).")
    logger.info("")
    logger.info("   Open System Settings \u2192 Privacy & Security \u2192 Accessibility")
    logger.info("   and enable the app that is running VoicePaste:")
    logger.info("     Terminal, iTerm, Visual Studio Code, or Claude")
    logger.info("")
    logger.info("   Then restart VoicePaste.")
    sys.exit(1)


def check_microphone(logger: app_logger.SessionLogger) -> None:
    """Verify mic capture by briefly opening the AVFoundation recorder.

    On first run this triggers the macOS Microphone permission prompt.
    Exits cleanly with instructions if access is denied.
    """
    try:
        logger.debug(
            "[startup] default input device snapshot before probe: "
            f"{describe_default_input_device()}"
        )
        logger.debug(
            "[startup] checking microphone access before probe "
            f"(sample_rate={config.SAMPLE_RATE}, "
            "channels=1, dtype=float32)"
        )
        probe_microphone_access(logger.debug)
        logger.debug("[startup] microphone access confirmed")
    except Exception as exc:
        logger.exception("\u274c microphone access failed", exc)
        logger.info("")
        logger.info("   Open System Settings \u2192 Privacy & Security \u2192 Microphone")
        logger.info("   and enable the app that is running VoicePaste:")
        logger.info("     Terminal, iTerm, Visual Studio Code, or Claude")
        logger.info("")
        logger.info("   Then restart VoicePaste.")
        sys.exit(1)


def main() -> None:
    """Entry point — permission checks, model load, wire components, run menubar loop."""
    logger = app_logger.SessionLogger(Path(__file__).resolve().parent)
    logger.info("VoicePaste starting\u2026")
    logger.info(f"Session log: {logger.log_path}")
    logger.debug(
        f"[session] cwd={Path.cwd()} executable={sys.executable}"
    )
    logger.debug(
        "[session] config "
        f"(model={config.MODEL_SIZE}, sample_rate={config.SAMPLE_RATE}, "
        f"max_duration={config.MAX_DURATION}, "
        f"hands_free_silence={config.HANDS_FREE_SILENCE_SECONDS}s, "
        f"readability_mode={config.READABILITY_MODE}, "
        f"sensitive_logging={config.LOG_SENSITIVE_CONTENT})"
    )

    check_accessibility(logger)
    check_microphone(logger)

    logger.info("Loading Whisper model\u2026")
    try:
        model = transcriber.load_model(logger=logger.debug)
    except Exception as exc:
        logger.exception("\u274c model load failed", exc)
        sys.exit(1)

    icon_path = str(Path(__file__).parent / "assets" / "branding" / "voicepaste-menubarTemplate.png")
    app = rumps.App("VoicePaste", title=Mode.IDLE.icon, icon=icon_path, template=True, quit_button="Quit")
    state_ref: dict[str, AppState] = {}
    recorder = Recorder(
        logger=logger.debug,
        on_auto_stop=lambda reason: _handle_auto_stop(state_ref["state"], reason),
    )
    state = AppState(
        app=app,
        logger=logger,
        model=model,
        recorder=recorder,
    )
    state_ref["state"] = state
    try:
        state.overlay_controller = overlay.FloatingPillController(
            on_hands_free_stop=lambda: handle_hands_free_stop(state)
        )
    except Exception as exc:
        logger.exception("⚠️  floating pill unavailable", exc)

    listener = HotkeyListener(
        on_hold_press=lambda: handle_press(state),
        on_hold_release=lambda: handle_release(state),
        on_hands_free_start=lambda: handle_hands_free_start(state),
        logger=logger.debug,
    )
    state.hotkey = listener
    listener.start()

    logger.info(Mode.IDLE.message)
    logger.info(
        "Hold Right Option to record. Press Right Option + Right Command for hands-free. "
        "Click the pill stop button to stop hands-free. Quit from the menubar."
    )

    try:
        app.run()
    finally:
        logger.debug("[shutdown] app.run exited; stopping listeners and closing overlay")
        listener.stop()
        state.recorder.close()
        if state.overlay_controller is not None:
            state.overlay_controller.close()
        logger.debug("[shutdown] cleanup complete")


if __name__ == "__main__":
    main()
