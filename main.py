"""VoicePaste entry point — wires recorder, transcriber, hotkey, paster, and menubar together."""

import sys
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
import rumps
import sounddevice as sd
from faster_whisper import WhisperModel

import config
import paster
import transcriber
from hotkey import HotkeyListener
from recorder import Recorder


class Mode(Enum):
    """User-facing app modes with menubar icon and terminal status line."""

    IDLE = ("\U0001f399\ufe0f", "VoicePaste ready")
    RECORDING = ("\U0001f534", "\U0001f399\ufe0f Recording...")
    TRANSCRIBING = ("\u23f3", "\U0001f504 Transcribing...")

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
    mode: Mode = Mode.IDLE


def set_mode(state: AppState, mode: Mode) -> None:
    """Update mode, menubar icon, and terminal status line atomically.

    Called from the pynput listener thread (press/release) and the worker
    thread (after transcription). Cocoa technically wants UI mutations on
    the main thread, but rumps' ``app.title`` setter is a simple string
    assignment that survives cross-thread use in practice.
    """
    state.mode = mode
    state.app.title = mode.icon
    print(mode.message)


def handle_press(state: AppState) -> None:
    """Hotkey pressed — start recording. Runs on the pynput listener thread."""
    if state.mode != Mode.IDLE:
        return  # busy with a previous transcription; ignore re-presses
    try:
        state.recorder.start()
    except Exception as exc:
        print(f"\u274c failed to start recording: {exc}")
        print("   If this looks like a microphone permission issue, grant access in")
        print(
            "   System Settings \u2192 Privacy & Security \u2192 Microphone and restart."
        )
        return
    set_mode(state, Mode.RECORDING)


def handle_release(state: AppState) -> None:
    """Hotkey released — immediately hand off to a worker thread and return.

    Returns instantly so the pynput listener thread is never blocked by
    recorder.stop() (which calls PortAudio's Pa_StopStream and can hang
    if the audio device is briefly unavailable).
    """
    if state.mode != Mode.RECORDING:
        return
    threading.Thread(target=_release_worker, args=(state,), daemon=True).start()


def _release_worker(state: AppState) -> None:
    """Stop recording, validate, transcribe, and paste — runs off the pynput thread."""
    try:
        audio = state.recorder.stop()

        if audio.size == 0:
            print("\u26a0\ufe0f  no audio captured \u2014 skipping")
            return

        min_samples = int(0.3 * config.SAMPLE_RATE)
        if audio.size < min_samples:
            seconds = audio.size / config.SAMPLE_RATE
            print(f"\u26a0\ufe0f  clip too short ({seconds:.2f}s) \u2014 skipping")
            return

        set_mode(state, Mode.TRANSCRIBING)

        text = transcriber.transcribe(state.model, audio)
        if not text:
            print("\u26a0\ufe0f  empty transcription \u2014 skipping")
            return
        print(f"\U0001f4dd {text}")
        paster.paste(text)
    except Exception as exc:
        print(f"\u274c worker error: {exc}")
    finally:
        set_mode(state, Mode.IDLE)


def check_accessibility() -> None:
    """Verify macOS Accessibility permission for the running Python binary.

    Required for pynput (global hotkey) and pyautogui (synthetic Cmd+V).
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
    print("   hotkey (pynput) and paste at the cursor (pyautogui).")
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
    state = AppState(app=app, model=model, recorder=Recorder())

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


if __name__ == "__main__":
    main()
