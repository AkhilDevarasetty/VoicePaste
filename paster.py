"""Clipboard write + auto-paste at cursor via pyperclip and pynput."""

import pyperclip
from pynput.keyboard import Controller, Key

_keyboard = Controller()


def paste(text: str) -> None:
    """Copy ``text`` to the clipboard and simulate Cmd+V at the cursor.

    Trusts the caller to have validated that ``text`` is non-empty — that
    check is the responsibility of main.py per the spec's skip-condition
    rules. The user's previous clipboard contents are intentionally
    overwritten and not restored, matching the VoicePaste behavior of
    leaving the transcript on the clipboard for re-paste.

    Requires macOS Accessibility permission for the running Python binary
    (same permission used by pynput); without it, the synthesised Cmd+V
    will silently fail to inject the keystroke.
    """
    pyperclip.copy(text)
    with _keyboard.pressed(Key.cmd):
        _keyboard.press("v")
        _keyboard.release("v")
