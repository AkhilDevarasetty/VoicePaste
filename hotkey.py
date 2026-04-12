"""Global hotkey listener (Right Option) via pynput."""

import threading
from typing import Callable, Optional

from pynput import keyboard

import config


class HotkeyListener:
    """Listens globally for ``config.HOTKEY`` and fires press/release callbacks.

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
        logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Wire up the listener with callbacks for the configured hotkey."""
        self._on_press = on_press
        self._on_release = on_release
        self._logger = logger
        self._held = False
        self._lock = threading.Lock()
        self._listener: Optional[keyboard.Listener] = None

    def _log(self, message: str) -> None:
        """Emit a debug log line when a logger callback is available."""
        if self._logger is not None:
            self._logger(f"[hotkey] {message}")

    def _handle_press(self, key: object) -> None:
        """pynput on_press dispatcher — debounces auto-repeat."""
        if key != config.HOTKEY:
            return
        with self._lock:
            if self._held:
                return
            self._held = True
        try:
            self._on_press()
        except Exception as exc:
            with self._lock:
                self._held = False
            self._log(f"press callback failed: {exc}")
            raise

    def _handle_release(self, key: object) -> None:
        """pynput on_release dispatcher — fires once per matched press."""
        if key != config.HOTKEY:
            return
        with self._lock:
            if not self._held:
                return
            self._held = False
        try:
            self._on_release()
        except Exception as exc:
            self._log(f"release callback failed: {exc}")
            raise

    def start(self) -> None:
        """Start the listener thread. Non-blocking. Idempotent."""
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.start()
        self._log("listener started")

    def stop(self) -> None:
        """Stop the listener thread. Idempotent."""
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None
        with self._lock:
            self._held = False
        self._log("listener stopped")
