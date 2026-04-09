"""VoicePaste entry point — wires recorder, transcriber, hotkey, paster, and menubar together."""

import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

import rumps
import sounddevice as sd
from faster_whisper import WhisperModel

import config
import enhancer
import overlay
import paster
import transcriber
from hotkey import HotkeyListener
from recorder import Recorder


class Mode(Enum):
    """User-facing app modes with menubar icon and terminal status line."""

    IDLE = ("\U0001f399\ufe0f", "VoicePaste ready")
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


def log_debug(message: str) -> None:
    """Print a timestamped debug log line for tracing intermittent failures."""
    timestamp = datetime.now().strftime(config.LOG_TIME_FORMAT)[:-3]
    print(f"[{timestamp}] {message}")


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
        state.mode = mode
    state.app.title = mode.icon
    if state.overlay_controller is not None:
        state.overlay_controller.set_mode(overlay_mode(mode))
    print(mode.message)


def handle_press(state: AppState) -> None:
    """Hotkey pressed — start recording. Runs on the pynput listener thread."""
    with state.state_lock:
        state.hotkey_press_count += 1
        press_count = state.hotkey_press_count
        current_mode = state.mode
        current_recording_id = state.active_recording_id
    log_debug(
        f"[hotkey] press #{press_count} received while mode={current_mode.name} "
        f"active_recording_id={current_recording_id}"
    )
    if current_mode != Mode.IDLE:
        log_debug(
            f"[hotkey] press #{press_count} ignored because the app is busy in "
            f"mode={current_mode.name}"
        )
        return  # busy with a previous transcription; ignore re-presses
    try:
        state.recorder.start()
    except Exception as exc:
        log_debug(f"[hotkey] press #{press_count} failed to start recording: {exc}")
        print(f"\u274c failed to start recording: {exc}")
        print("   If this looks like a microphone permission issue, grant access in")
        print(
            "   System Settings \u2192 Privacy & Security \u2192 Microphone and restart."
        )
        return
    with state.state_lock:
        state.recording_attempt_count += 1
        state.active_recording_id = state.recording_attempt_count
        recording_id = state.active_recording_id
    log_debug(f"[recording {recording_id}] started from hotkey press #{press_count}")
    set_mode(state, Mode.RECORDING)


def handle_release(state: AppState) -> None:
    """Hotkey released — immediately hand off to a worker thread and return.

    Returns instantly so the pynput listener thread is never blocked by
    recorder.stop() (which calls PortAudio's Pa_StopStream and can hang
    if the audio device is briefly unavailable).
    """
    with state.state_lock:
        state.hotkey_release_count += 1
        release_count = state.hotkey_release_count
        current_mode = state.mode
        recording_id = state.active_recording_id
        release_in_progress = state.release_in_progress
        if current_mode == Mode.RECORDING and not release_in_progress:
            state.release_in_progress = True
    log_debug(
        f"[hotkey] release #{release_count} received while mode={current_mode.name} "
        f"active_recording_id={recording_id}"
    )
    if current_mode != Mode.RECORDING:
        log_debug(
            f"[hotkey] release #{release_count} ignored because the app is in "
            f"mode={current_mode.name}"
        )
        return
    if release_in_progress:
        log_debug(f"[hotkey] release #{release_count} ignored because stop is in progress")
        return
    threading.Thread(
        target=_release_worker,
        args=(state, recording_id),
        name=f"release-worker-{recording_id}",
        daemon=True,
    ).start()


def _release_worker(state: AppState, recording_id: Optional[int]) -> None:
    """Stop recording, validate, transcribe, and paste — runs off the pynput thread."""
    try:
        result = state.recorder.stop(reason="hotkey_release")
        audio = result.audio
        log_debug(
            f"[recording {recording_id}] recorder.stop completed "
            f"(was_recording={result.was_recording}, stop_reason={result.stop_reason}, "
            f"previous_stop_reason={result.previous_stop_reason}, "
            f"duration={result.duration_seconds:.2f}s, chunks={result.chunk_count}, "
            f"samples={audio.size})"
        )

        if audio.size == 0:
            if (
                not result.was_recording
                and result.previous_stop_reason == "max_duration"
            ):
                log_debug(
                    f"[recording {recording_id}] no audio returned because the "
                    "recorder had already auto-stopped at max duration"
                )
            else:
                log_debug(f"[recording {recording_id}] no audio captured after release")
            print("\u26a0\ufe0f  no audio captured \u2014 skipping")
            return

        min_samples = int(config.MIN_RECORDING_SECONDS * config.SAMPLE_RATE)
        if audio.size < min_samples:
            seconds = audio.size / config.SAMPLE_RATE
            log_debug(
                f"[recording {recording_id}] clip too short "
                f"({seconds:.2f}s < {config.MIN_RECORDING_SECONDS:.2f}s)"
            )
            print(f"\u26a0\ufe0f  clip too short ({seconds:.2f}s) \u2014 skipping")
            return

        set_mode(state, Mode.TRANSCRIBING)

        text = transcriber.transcribe(state.model, audio)
        if not text:
            print("\u26a0\ufe0f  empty transcription \u2014 skipping")
            return
        if (
            config.READABILITY_MODE == "openai"
            and len(text.strip()) >= config.MIN_TEXT_LENGTH_FOR_ENHANCEMENT
        ):
            set_mode(state, Mode.ENHANCING)
        final_text = enhancer.enhance(text, logger=log_debug)
        print(f"\U0001f4dd {final_text}")
        paster.paste(final_text)
    except Exception as exc:
        log_debug(f"[recording {recording_id}] worker error: {exc}")
        print(f"\u274c worker error: {exc}")
    finally:
        with state.state_lock:
            if state.active_recording_id == recording_id:
                state.active_recording_id = None
            state.release_in_progress = False
        set_mode(state, Mode.IDLE)


def check_accessibility() -> None:
    """Verify macOS Accessibility permission for the running Python binary.

    Required for pynput (global hotkey and synthetic Cmd+V).
    Exits cleanly with step-by-step instructions if not granted.
    """
    try:
        from ApplicationServices import AXIsProcessTrusted
    except ImportError:
        # pyobjc bridge unavailable — defer to runtime failure in pynput.
        return
    if AXIsProcessTrusted():
        return
    print("\u274c Accessibility permission not granted.")
    print()
    print("   VoicePaste needs Accessibility access to listen for the global")
    print("   hotkey and paste at the cursor (pynput).")
    print()
    print("   Open System Settings \u2192 Privacy & Security \u2192 Accessibility")
    print("   and enable the Python binary running VoicePaste:")
    print(f"     {sys.executable}")
    print()
    print("   Then restart VoicePaste.")
    sys.exit(1)


def check_microphone() -> None:
    """Verify mic capture by briefly opening an InputStream.

    On first run this triggers the macOS Microphone permission prompt.
    Exits cleanly with instructions if access is denied.
    """
    try:
        stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        stream.start()
        stream.stop()
        stream.close()
    except Exception as exc:
        print(f"\u274c microphone access failed: {exc}")
        print()
        print("   Open System Settings \u2192 Privacy & Security \u2192 Microphone")
        print("   and enable the Python binary running VoicePaste:")
        print(f"     {sys.executable}")
        print()
        print("   Then restart VoicePaste.")
        sys.exit(1)


def main() -> None:
    """Entry point — permission checks, model load, wire components, run menubar loop."""
    print("VoicePaste starting\u2026")

    check_accessibility()
    check_microphone()

    print("Loading Whisper model\u2026")
    try:
        model = transcriber.load_model()
    except Exception as exc:
        print(f"\u274c model load failed: {exc}")
        sys.exit(1)

    app = rumps.App("VoicePaste", title=Mode.IDLE.icon, quit_button="Quit")
    state = AppState(app=app, model=model, recorder=Recorder(logger=log_debug))
    try:
        state.overlay_controller = overlay.FloatingPillController()
    except Exception as exc:
        log_debug(f"[overlay] unavailable: {exc}")
        print(f"⚠️  floating pill unavailable: {exc}")

    listener = HotkeyListener(
        on_press=lambda: handle_press(state),
        on_release=lambda: handle_release(state),
    )
    state.hotkey = listener
    listener.start()

    print(Mode.IDLE.message)
    print("Hold Right Option to record. Release to transcribe. Quit from the menubar.")

    try:
        app.run()
    finally:
        listener.stop()
        if state.overlay_controller is not None:
            state.overlay_controller.close()


if __name__ == "__main__":
    main()
