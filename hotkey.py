"""Global hotkey listener for dictation and action-mode triggers via pynput."""

import threading
from typing import Callable, Optional

from pynput import keyboard

import config


class HotkeyListener:
    """Listens globally for the configured dictation and action hotkeys.

    pynput's listener delivers a fresh ``on_press`` event for every OS
    key-repeat tick while a key is held. This class debounces those: the
    ``on_press`` callback runs exactly once when the key transitions from
    released to pressed, and ``on_release`` runs exactly once on the matching
    transition back.

    Runs in its own thread (``pynput.keyboard.Listener`` is itself a
    ``threading.Thread`` subclass), so ``start()`` is non-blocking and the
    main thread is free to run the rumps menubar loop.

    Requires macOS Accessibility permission for the running Python binary.
    If permission is missing, pynput will fail at listener-start time and
    the caller (main.py) is expected to surface a friendly message.
    """

    def __init__(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
        on_action_press: Optional[Callable[[], None]] = None,
        on_action_release: Optional[Callable[[], None]] = None,
        logger: Optional[Callable[[str], None]] = None,
        on_key_press: Optional[Callable[[object], None]] = None,
        on_key_release: Optional[Callable[[object], None]] = None,
    ) -> None:
        """Wire up the listener with callbacks for the configured hotkeys."""
        self._on_press = on_press
        self._on_release = on_release
        self._on_action_press = on_action_press
        self._on_action_release = on_action_release
        self._logger = logger
        self._on_key_press = on_key_press
        self._on_key_release = on_key_release
        self._dictation_held = False
        self._action_held = False
        self._lock = threading.Lock()
        self._listener: Optional[keyboard.Listener] = None

    def _log(self, message: str) -> None:
        """Emit a debug log line when a logger callback is available."""
        if self._logger is not None:
            self._logger(f"[hotkey] {message}")

    def _handle_press(self, key: object) -> None:
        """pynput on_press dispatcher — debounces auto-repeat."""
        if self._on_key_press is not None:
            self._on_key_press(key)
        with self._lock:
            if key == config.HOTKEY:
                if self._dictation_held:
                    return
                self._dictation_held = True
                callback = self._on_press
            elif key == config.ACTION_HOTKEY:
                if self._action_held:
                    return
                self._action_held = True
                callback = self._on_action_press
            else:
                return
        try:
            if callback is not None:
                callback()
        except Exception as exc:
            with self._lock:
                if key == config.HOTKEY:
                    self._dictation_held = False
                elif key == config.ACTION_HOTKEY:
                    self._action_held = False
            self._log(f"press callback failed: {exc}")
            raise

    def _handle_release(self, key: object) -> None:
        """pynput on_release dispatcher — fires once per matched press."""
        if self._on_key_release is not None:
            self._on_key_release(key)
        with self._lock:
            if key == config.HOTKEY:
                if not self._dictation_held:
                    return
                self._dictation_held = False
                callback = self._on_release
            elif key == config.ACTION_HOTKEY:
                if not self._action_held:
                    return
                self._action_held = False
                callback = self._on_action_release
            else:
                return
        try:
            if callback is not None:
                callback()
        except Exception as exc:
            self._log(f"release callback failed: {exc}")
            raise

    def is_running(self) -> bool:
        """Return whether the pynput listener thread is alive."""
        listener = self._listener
        return listener is not None and listener.is_alive()

    def start(self) -> None:
        """Start the listener thread. Non-blocking. Idempotent."""
        if self.is_running():
            return
        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.start()
        self._log("listener started")

    def restart(self) -> None:
        """Replace the listener thread with a fresh instance."""
        self.stop()
        self.start()

    def stop(self) -> None:
        """Stop the listener thread. Idempotent."""
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None
        with self._lock:
            self._dictation_held = False
            self._action_held = False
        self._log("listener stopped")
