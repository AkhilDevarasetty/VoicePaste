"""VoicePaste entry point — wires recorder, transcriber, hotkey, paster, and menubar together."""

import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4

import rumps
from faster_whisper import WhisperModel

try:
    import AppKit
except ImportError:
    AppKit = None

import app_logger
import config
import db
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
    db_path: Path
    hotkey: Optional[HotkeyListener] = None
    overlay_controller: Optional[overlay.FloatingPillController] = None
    mode: Mode = Mode.IDLE
    state_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    hotkey_press_count: int = 0
    hotkey_release_count: int = 0
    recording_attempt_count: int = 0
    active_recording_id: Optional[int] = None
    release_in_progress: bool = False


def overlay_mode(mode: Mode) -> overlay.OverlayMode:
    """Map app modes to the smaller set of floating pill overlay states."""
    if mode == Mode.RECORDING:
        return overlay.RECORDING_MODE
    if mode in {Mode.TRANSCRIBING, Mode.ENHANCING}:
        return overlay.PROCESSING_MODE
    return overlay.IDLE_MODE


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


def handle_press(state: AppState) -> None:
    """Hotkey pressed — start recording. Runs on the pynput listener thread."""
    with state.state_lock:
        state.hotkey_press_count += 1
        press_count = state.hotkey_press_count
        current_mode = state.mode
        current_recording_id = state.active_recording_id
    state.logger.debug(
        f"[hotkey] press #{press_count} received while mode={current_mode.name} "
        f"active_recording_id={current_recording_id}"
    )
    if current_mode != Mode.IDLE:
        state.logger.debug(
            f"[hotkey] press #{press_count} ignored because the app is busy in "
            f"mode={current_mode.name}"
        )
        return  # busy with a previous transcription; ignore re-presses
    try:
        state.recorder.start()
    except Exception as exc:
        state.logger.exception(
            f"\u274c failed to start recording on press #{press_count}",
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
        recording_id = state.active_recording_id
    state.logger.debug(
        f"[recording {recording_id}] started from hotkey press #{press_count}"
    )
    set_mode(state, Mode.RECORDING)
    play_feedback_sound(state.logger, config.RECORDING_START_SOUND_NAME)


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
        if current_mode == Mode.RECORDING and not release_in_progress:
            state.release_in_progress = True
    state.logger.debug(
        f"[hotkey] release #{release_count} received while mode={current_mode.name} "
        f"active_recording_id={recording_id}"
    )
    if current_mode != Mode.RECORDING:
        state.logger.debug(
            f"[hotkey] release #{release_count} ignored because the app is in "
            f"mode={current_mode.name}"
        )
        return
    if release_in_progress:
        state.logger.debug(
            f"[hotkey] release #{release_count} ignored because stop is in progress"
        )
        return
    threading.Thread(
        target=_release_worker,
        args=(state, recording_id, "hotkey_release"),
        name=f"release-worker-{recording_id}",
        daemon=True,
    ).start()


def _handle_max_duration(state: AppState) -> None:
    """Kick off processing immediately when the recorder auto-stops at max duration."""
    with state.state_lock:
        recording_id = state.active_recording_id
        current_mode = state.mode
        release_in_progress = state.release_in_progress
        if current_mode != Mode.RECORDING or release_in_progress:
            return
        state.release_in_progress = True
    state.logger.debug(
        f"[recording {recording_id}] max-duration reached; starting processing immediately"
    )
    threading.Thread(
        target=_release_worker,
        args=(state, recording_id, "max_duration_followup"),
        name=f"max-duration-worker-{recording_id}",
        daemon=True,
    ).start()


def _release_worker(
    state: AppState,
    recording_id: Optional[int],
    stop_reason: str,
) -> None:
    """Stop recording, validate, transcribe, and paste — runs off the pynput thread."""
    worker_started = time.perf_counter()
    raw_text: Optional[str] = None
    final_text: Optional[str] = None
    duration_seconds: Optional[float] = None
    transcription_latency_ms: Optional[int] = None
    enhancement_latency_ms: Optional[int] = None
    state.logger.debug(f"[recording {recording_id}] release worker started")
    try:
        stop_started = time.perf_counter()
        result = state.recorder.stop(reason=stop_reason)
        stop_elapsed = time.perf_counter() - stop_started
        audio = result.audio
        duration_seconds = result.duration_seconds
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
                and result.previous_stop_reason == "max_duration"
            ):
                state.logger.debug(
                    f"[recording {recording_id}] no audio returned because the "
                    "recorder had already auto-stopped at max duration"
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
        raw_text = transcriber.transcribe(state.model, audio, logger=state.logger.debug)
        transcription_elapsed = time.perf_counter() - transcription_started
        transcription_latency_ms = int(round(transcription_elapsed * 1000))
        if not raw_text:
            state.logger.warning("\u26a0\ufe0f  empty transcription \u2014 skipping")
            return
        state.logger.debug(
            f"[recording {recording_id}] transcription result "
            f"(chars={len(raw_text)}, words={len(raw_text.split())}, elapsed={transcription_elapsed:.2f}s)"
        )
        readability_mode = db.get_setting(
            state.db_path,
            "readability_mode",
            config.READABILITY_MODE,
        )
        enhancement_elapsed = 0.0
        if (
            readability_mode == "openai"
            and len(raw_text.strip()) >= config.MIN_TEXT_LENGTH_FOR_ENHANCEMENT
        ):
            set_mode(state, Mode.ENHANCING)
        enhancement_started = time.perf_counter()
        final_text = enhancer.enhance(
            raw_text,
            readability_mode=readability_mode,
            logger=state.logger.debug,
        )
        enhancement_elapsed = time.perf_counter() - enhancement_started
        enhancement_latency_ms = int(round(enhancement_elapsed * 1000))
        state.logger.debug(
            f"[recording {recording_id}] final text ready "
            f"(chars={len(final_text)}, words={len(final_text.split())}, "
            f"enhancement_elapsed={enhancement_elapsed:.2f}s)"
        )
        state.logger.transcript(final_text)
        target_app = _capture_frontmost_app_name()
        paste_started = time.perf_counter()
        try:
            paster.paste(final_text, logger=state.logger.debug)
        except Exception as exc:
            _persist_transcript(
                state,
                {
                    "id": uuid4().hex,
                    "created_at": _utcnow_iso(),
                    "status": "paste_failed",
                    "raw_text": raw_text,
                    "final_text": final_text,
                    "duration_seconds": duration_seconds,
                    "transcription_latency_ms": transcription_latency_ms,
                    "enhancement_latency_ms": enhancement_latency_ms,
                    "target_app": target_app,
                    "error_message": str(exc),
                },
            )
            state.logger.exception(
                f"\u274c paste failed for recording {recording_id}",
                exc,
            )
            return
        paste_elapsed = time.perf_counter() - paste_started
        play_feedback_sound(state.logger, config.PASTE_COMPLETE_SOUND_NAME)
        total_elapsed = time.perf_counter() - worker_started
        state.logger.debug(
            f"[recording {recording_id}] pipeline completed "
            f"(stop={stop_elapsed:.2f}s, transcribe={transcription_elapsed:.2f}s, "
            f"enhance={enhancement_elapsed:.2f}s, paste={paste_elapsed:.2f}s, "
            f"total={total_elapsed:.2f}s)"
        )
        _persist_transcript(
            state,
            {
                "id": uuid4().hex,
                "created_at": _utcnow_iso(),
                "status": "completed",
                "raw_text": raw_text,
                "final_text": final_text,
                "duration_seconds": duration_seconds,
                "transcription_latency_ms": transcription_latency_ms,
                "enhancement_latency_ms": enhancement_latency_ms,
                "target_app": target_app,
                "error_message": None,
            },
        )
    except Exception as exc:
        state.logger.exception(f"\u274c worker error for recording {recording_id}", exc)
        _persist_transcript(
            state,
            {
                "id": uuid4().hex,
                "created_at": _utcnow_iso(),
                "status": "failed",
                "raw_text": raw_text,
                "final_text": final_text,
                "duration_seconds": duration_seconds,
                "transcription_latency_ms": transcription_latency_ms,
                "enhancement_latency_ms": enhancement_latency_ms,
                "target_app": None,
                "error_message": str(exc),
            },
        )
    finally:
        with state.state_lock:
            if state.active_recording_id == recording_id:
                state.active_recording_id = None
            state.release_in_progress = False
        set_mode(state, Mode.IDLE)


def _capture_frontmost_app_name() -> Optional[str]:
    """Return the current frontmost app name without risking pipeline failure."""
    if AppKit is None:
        return None
    try:
        app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None
        name = app.localizedName()
        return str(name) if name else None
    except Exception:
        return None


def _persist_transcript(state: AppState, transcript: dict[str, object]) -> None:
    """Persist a transcript row without interrupting the user-facing flow."""
    try:
        db.insert_transcript(state.db_path, transcript)
    except Exception as exc:
        state.logger.exception("⚠️ transcript persistence failed", exc)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    db.init_db(config.DB_PATH)
    logger.info("VoicePaste starting\u2026")
    logger.info(f"Session log: {logger.log_path}")
    logger.info(f"SQLite DB: {config.DB_PATH}")
    logger.debug(
        f"[session] cwd={Path.cwd()} executable={sys.executable}"
    )
    logger.debug(
        "[session] config "
        f"(model={config.MODEL_SIZE}, sample_rate={config.SAMPLE_RATE}, "
        f"max_duration={config.MAX_DURATION}, readability_mode={config.READABILITY_MODE}, "
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
        on_max_duration=lambda: _handle_max_duration(state_ref["state"]),
    )
    state = AppState(
        app=app,
        logger=logger,
        model=model,
        recorder=recorder,
        db_path=config.DB_PATH,
    )
    state_ref["state"] = state
    try:
        state.overlay_controller = overlay.FloatingPillController()
    except Exception as exc:
        logger.exception("⚠️  floating pill unavailable", exc)

    listener = HotkeyListener(
        on_press=lambda: handle_press(state),
        on_release=lambda: handle_release(state),
        logger=logger.debug,
    )
    state.hotkey = listener
    listener.start()

    logger.info(Mode.IDLE.message)
    logger.info("Hold Right Option to record. Release to transcribe. Quit from the menubar.")

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
