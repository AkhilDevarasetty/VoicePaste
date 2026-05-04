"""Global hotkey listener for hold-to-talk and hands-free mode via pynput."""

import threading
from typing import Callable, Optional

from pynput import keyboard

import config


class HotkeyListener:
    """Listen globally for the configured hold and hands-free shortcuts."""

    def __init__(
        self,
        on_hold_press: Callable[[], None],
        on_hold_release: Callable[[], None],
        on_hands_free_start: Callable[[], None],
        logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Wire up the listener with callbacks for the configured shortcuts."""
        self._on_hold_press = on_hold_press
        self._on_hold_release = on_hold_release
        self._on_hands_free_start = on_hands_free_start
        self._logger = logger
        self._hold_active = False
        self._hold_press_pending = False
        self._hold_press_timer: Optional[threading.Timer] = None
        self._hands_free_chord_active = False
        self._pressed_keys: set[object] = set()
        self._lock = threading.Lock()
        self._listener: Optional[keyboard.Listener] = None

    def _log(self, message: str) -> None:
        """Emit a debug log line when a logger callback is available."""
        if self._logger is not None:
            self._logger(f"[hotkey] {message}")

    def _handle_press(self, key: object) -> None:
        """pynput on_press dispatcher — debounces hold and hands-free chord events."""
        hands_free_start = False
        with self._lock:
            self._pressed_keys.add(key)

            if key == config.HOTKEY and not self._hold_active and not self._hold_press_pending:
                self._schedule_hold_press_locked()

            if (
                config.HANDS_FREE_HOTKEY_MODIFIER in self._pressed_keys
                and config.HANDS_FREE_HOTKEY_TRIGGER in self._pressed_keys
                and not self._hands_free_chord_active
            ):
                self._cancel_hold_press_timer_locked()
                self._hands_free_chord_active = True
                hands_free_start = True

        if hands_free_start:
            try:
                self._on_hands_free_start()
            except Exception as exc:
                self._log(f"hands-free-start callback failed: {exc}")
                raise

    def _handle_release(self, key: object) -> None:
        """pynput on_release dispatcher — fires once per matched hold press."""
        hold_release = False
        with self._lock:
            self._pressed_keys.discard(key)

            if key == config.HOTKEY:
                if self._hold_press_pending:
                    self._cancel_hold_press_timer_locked()
                elif self._hold_active:
                    self._hold_active = False
                    hold_release = True

            if key in {
                config.HANDS_FREE_HOTKEY_MODIFIER,
                config.HANDS_FREE_HOTKEY_TRIGGER,
            }:
                self._hands_free_chord_active = False

        if hold_release:
            try:
                self._on_hold_release()
            except Exception as exc:
                self._log(f"hold-release callback failed: {exc}")
                raise

    def _schedule_hold_press_locked(self) -> None:
        """Delay hold-to-talk start long enough to detect the hands-free chord."""
        self._cancel_hold_press_timer_locked()
        self._hold_press_pending = True
        timer = threading.Timer(
            config.HOLD_HOTKEY_CHORD_GRACE_SECONDS,
            self._fire_hold_press,
        )
        timer.daemon = True
        timer.start()
        self._hold_press_timer = timer

    def _cancel_hold_press_timer_locked(self) -> None:
        """Cancel any pending delayed hold-to-talk start."""
        self._hold_press_pending = False
        if self._hold_press_timer is not None:
            self._hold_press_timer.cancel()
            self._hold_press_timer = None

    def _fire_hold_press(self) -> None:
        """Start hold-to-talk after the chord grace window passes."""
        should_fire = False
        with self._lock:
            self._hold_press_timer = None
            if (
                self._hold_press_pending
                and not self._hold_active
                and not self._hands_free_chord_active
                and config.HOTKEY in self._pressed_keys
            ):
                self._hold_press_pending = False
                self._hold_active = True
                should_fire = True
            else:
                self._hold_press_pending = False
        if not should_fire:
            return
        try:
            self._on_hold_press()
        except Exception as exc:
            with self._lock:
                self._hold_active = False
            self._log(f"hold-press callback failed: {exc}")
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
            self._cancel_hold_press_timer_locked()
            self._hold_active = False
            self._hands_free_chord_active = False
            self._pressed_keys.clear()
        self._log("listener stopped")
