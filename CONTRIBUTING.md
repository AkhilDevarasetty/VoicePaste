# Contributing to VoicePaste

Thanks for your interest in contributing! VoicePaste is a small project and contributions of all kinds are welcome — bug reports, feature ideas, docs improvements, and code.

## Workflow

`main` is protected. Do not push directly to `main`.

For code changes:
1. Sync from the latest `main`
2. Create a branch for your work
3. Make your changes and test them locally
4. Open a pull request into `main`

## Getting Started

```bash
git clone https://github.com/AkhilDevarasetty/VoicePaste.git
cd VoicePaste
make install
make run
```

You'll need macOS on Apple Silicon, Python 3.10+, and the Microphone + Accessibility permissions described in the README.

If your preferred Python is not the default `python3`, point `make` at it explicitly:

```bash
make install PYTHON=/opt/homebrew/bin/python3.11
```

## Project Conventions

- **All config in `config.py`** — no hardcoded values anywhere else
- **Threading, not asyncio** — the macOS UI and audio libraries require it
- **Type hints** on every function
- **Brief docstring** on every function
- **No global mutable state** — shared state flows through the `AppState` dataclass

## How to Help

- **Bug reports** — open an issue with steps to reproduce and your macOS / Python version
- **Feature ideas** — check the Roadmap section in the README first, then open an issue
- **Code contributions** — fork or branch from the latest `main`, keep changes scoped, and open a PR instead of pushing to `main`

## Pull Requests

Before requesting review:

- Make sure the project still installs with `make install`
- Run the app locally with `make run` when your change affects runtime behavior
- Update docs when setup, behavior, or contributor workflow changes
- Keep PRs focused so they are easy to review

PRs should include:

- a short summary of what changed
- why the change is needed
- any local testing you ran
- screenshots or terminal output when helpful

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
