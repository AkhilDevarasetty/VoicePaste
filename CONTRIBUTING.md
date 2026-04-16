# Contributing to VoicePaste

Thanks for your interest in contributing! VoicePaste is a small project and contributions of all kinds are welcome — bug reports, feature ideas, docs improvements, and code.

## Getting Started

```bash
git clone https://github.com/AkhilDevarasetty/VoicePaste.git
cd VoicePaste
make install
make run
```

You'll need macOS on Apple Silicon, Python 3.10+, and the Microphone + Accessibility permissions described in the README.

## Project Conventions

- **All config in `config.py`** — no hardcoded values anywhere else
- **Threading, not asyncio** — the macOS UI and audio libraries require it
- **Type hints** on every function
- **Brief docstring** on every function
- **No global mutable state** — shared state flows through the `AppState` dataclass

## How to Help

- **Bug reports** — open an issue with steps to reproduce and your macOS / Python version
- **Feature ideas** — check the Roadmap section in the README first, then open an issue
- **Code contributions** — fork, create a branch, make your changes, and open a PR

## Code Layout

| File | Purpose |
|---|---|
| `main.py` | Entry point — wires all modules together |
| `recorder.py` | Native macOS mic capture (AVFoundation via PyObjC) |
| `transcriber.py` | Whisper model + transcription |
| `enhancer.py` | Optional cloud readability cleanup |
| `hotkey.py` | Global hotkey listener (pynput) |
| `paster.py` | Clipboard + auto-paste |
| `overlay.py` | Floating pill UI (AppKit) |
| `app_logger.py` | Session logging |
| `config.py` | All tunables — single source of truth |
