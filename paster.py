"""Clipboard write + auto-paste at cursor via pyperclip and pyautogui."""

import pyautogui
import pyperclip


def paste(text: str) -> None:
    """Copy ``text`` to the clipboard and simulate Cmd+V at the cursor.

    Trusts the caller to have validated that ``text`` is non-empty — that
    check is the responsibility of main.py per the spec's skip-condition
    rules. The user's previous clipboard contents are intentionally
    overwritten and not restored, matching the WhisperFlow behavior of
    leaving the transcript on the clipboard for re-paste.

    Requires macOS Accessibility permission for the running Python binary
    (same permission used by pynput); without it, ``pyautogui.hotkey``
    will silently fail to inject the keystroke.
    """
    pyperclip.copy(text)
    pyautogui.hotkey("command", "v")
