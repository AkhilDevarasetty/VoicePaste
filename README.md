# VoicePaste

A macOS voice-to-text utility that is **fully local by default**. Hold **Right Option**, talk, release, and your speech is transcribed by `faster-whisper` and pasted at the cursor. An optional cloud cleanup pass can be enabled for transcript text only (not audio) to improve readability before paste.

---

## 1. Prerequisites

| Requirement | Notes |
|---|---|
| **macOS** on Apple Silicon (M1/M2/M3) | CPU inference only — no Metal/GPU required |
| **Python 3.10+** | 3.11 is what this project was built and tested against |
| ~150 MB free disk | For the `base.en` Whisper model that downloads on first run |
| A working microphone | Built-in is fine |

> Already have `python3` somewhere but not sure if it's 3.10+? Run `python3 --version`. macOS ships with 3.9 by default — that's too old. Install a newer one with [Homebrew](https://brew.sh) (`brew install python@3.12`), [pyenv](https://github.com/pyenv/pyenv), or Anaconda.

---

## 2. Setup

```bash
# 1. Clone (or copy) this directory, then cd into it
cd /path/to/voicepaste

# 2. Create a virtual environment using a Python 3.10+ interpreter.
#    Replace the python binary on the left with whichever 3.10+ you have:
python3.11 -m venv venv

# 3. Activate it and install pinned dependencies
source venv/bin/activate
pip install -r requirements.txt
```

The first time you actually run the app, `faster-whisper` will download the `base.en` model (~150 MB) from Hugging Face into `~/.cache/huggingface/`. Subsequent runs use the local cache.

### Optional cloud enhancement

By default, VoicePaste stays fully local. If you want transcript readability cleanup before paste, you can enable the optional OpenAI enhancement mode:

1. Add your API key to your shell environment:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

To make that persistent, add the same line to your shell rc file such as `~/.zshrc`, then open a new terminal.

2. In `config.py`, change:

```python
READABILITY_MODE = "openai"
```

When this mode is enabled:
- Only the transcribed text is sent to OpenAI
- Audio never leaves your machine
- The app uses `gpt-4o-mini` to improve readability while preserving meaning
- If the API key is missing, the request times out, or the API fails, VoicePaste falls back to the raw transcript and still pastes it

---

## 3. macOS Permissions

VoicePaste needs **two** permissions in System Settings → Privacy & Security. Both are bound to the **specific Python binary** that runs VoicePaste — not Python in general — so you have to point macOS at the venv interpreter you just created.

### Find the right Python binary

After running the setup steps above, the binary lives at:

```
/path/to/voicepaste/venv/bin/python3.11
```

To get the real path on your machine:

```bash
# From inside the voicepaste directory, with venv activated:
realpath ./venv/bin/python
```

Copy that path — you'll paste it into Finder twice in the next two sections.

### 3a. Microphone

The **first time** you run `python main.py`, macOS will pop a dialog asking to allow microphone access for the Python binary. Click **Allow** and you're done.

If you missed the prompt or already clicked Deny:

1. Open **System Settings → Privacy & Security → Microphone**
2. If you see an entry for your Python binary, toggle it **on**
3. If not, you'll need to add it manually:
   - Use the `+` button (some macOS versions show this; others just want you to drag)
   - In the file picker, press `⌘ + ⇧ + G` to open "Go to folder"
   - Paste the full path from `realpath ./venv/bin/python` and press Return
   - Select the binary and click Open
   - Toggle the new entry **on**

### 3b. Accessibility

Accessibility is required for two reasons:
- **pynput** uses it to listen for the global Right-Option hotkey
- **pyautogui** uses it to send the synthetic ⌘V keystroke that pastes the transcript

Unlike Microphone, macOS does **not** automatically prompt you for Accessibility. **What you need to grant it to depends on how you launch VoicePaste** — macOS attributes the request to the *parent process* (the terminal/app you run it from), not to the Python binary itself:

| How you run `python main.py` | Grant Accessibility to |
|---|---|
| Terminal.app | Terminal |
| iTerm2 | iTerm2 |
| VS Code integrated terminal | Visual Studio Code |
| Claude Code desktop app | Claude (Anthropic) |

Steps:

1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the `+` button
3. Navigate to and select the app you use to run VoicePaste (e.g. Terminal, iTerm2)
4. Make sure its toggle is **on**
5. **Restart VoicePaste** — Accessibility is checked at process start

VoicePaste will refuse to launch if Accessibility isn't granted, and will print the path of the running Python binary to help you identify which parent app needs the permission.

---

## 4. Running

```bash
source venv/bin/activate
python main.py
```

You should see:

```
VoicePaste starting…
Loading Whisper model…
VoicePaste ready
Hold Right Option to record. Release to transcribe. Quit from the menubar.
```

A 🎙️ icon appears in your menubar. Quit any time from the menubar's **Quit** entry.

---

## 5. Hotkey Usage

| Action | What happens |
|---|---|
| **Hold** Right Option | Recording starts. Menubar turns 🔴, terminal prints `🎙️ Recording...` |
| **Release** Right Option | Recording stops. Menubar turns ⏳, terminal prints `🔄 Transcribing...` |
| Optional cloud cleanup enabled | After transcription, menubar briefly turns ✨ and terminal prints `✨ Enhancing...` |
| Transcription completes | Menubar returns to 🎙️, transcript prints to terminal AND is pasted at the cursor |
| Hold longer than 60 seconds | Auto-stop kicks in (safety limit, configurable in `config.py`) |
| Hold less than 0.3 seconds | Skipped — too short, terminal warns and resets |
| Hold but say nothing (silence) | Skipped — VAD finds no speech, terminal warns and resets |

The transcript also lands on your clipboard, so you can paste it again with ⌘V if needed.

---

## 6. Troubleshooting

### `❌ Accessibility permission not granted.` at startup

You haven't enabled Accessibility for the venv Python yet. Follow **Section 3b**.

If you already added the binary and still see this error, the most common cause is that macOS is tracking a stale entry. **Remove the entry** from System Settings → Privacy & Security → Accessibility (select it, click `−`), then add it again following Section 3b.

### `❌ microphone access failed: [...]` at startup

You denied the mic prompt, or never got it. Follow **Section 3a**. Same stale-entry trick applies if needed.

### Right Option does nothing — no Recording state, no errors

This is almost always Accessibility permission silently not working. Things to try, in order:

1. Confirm the venv binary is **toggled on** in System Settings → Privacy & Security → Accessibility (the toggle, not just the presence in the list)
2. Remove the entry, restart VoicePaste, re-add it
3. Make sure no other app is intercepting Right Option (Karabiner-Elements, BetterTouchTool, Logi Options+, etc.)

### `ModuleNotFoundError: No module named 'requests'`

The pinned `faster-whisper==1.0.3` imports `requests` but newer versions of `huggingface-hub` no longer pull it in transitively. `requests` is listed in `requirements.txt`, so this only happens if you installed deps before that line was added. Fix:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### `Warning: You are sending unauthenticated requests to the HF Hub.`

Cosmetic. Hugging Face is reminding you that anonymous downloads have rate limits. The `base.en` model is small and downloads once — you can ignore this. If you do hit a rate limit, set `HF_TOKEN` in your environment to a free Hugging Face token.

### Transcript is wrong / poor quality

`base.en` is the smallest English-only model — fast but the least accurate. To upgrade, edit `config.py`:

```python
MODEL_SIZE = "small.en"   # or "medium.en", "large-v3"
```

Larger models are slower and use more RAM, but transcribe much more accurately. `small.en` is a good middle ground on M1.

### Verify the model loads at all

Before debugging the full app, run the standalone model-load smoke test:

```bash
source venv/bin/activate
python test.py
```

You should see two timestamped lines and `model loaded: WhisperModel`. If this fails but `pip install` succeeded, it's almost always a corrupted Hugging Face cache — delete `~/.cache/huggingface/hub/models--Systran--faster-whisper-base.en/` and re-run.

### Transcribing is slow

The first transcription after startup is always slower (model warm-up). Subsequent ones should be ~1–3 seconds for short clips on M1. If they're consistently slow:

- Check Activity Monitor — make sure nothing else is pegging the CPU
- Try `COMPUTE_TYPE = "int8"` (already the default) which is the fastest CPU mode
- Drop to a smaller model in `config.py`

### `pip install` fails building a wheel

Some of the dependencies (`pyautogui`, `pyperclip`, `rumps`) build native code via pyobjc. If the build fails, install Xcode Command Line Tools and try again:

```bash
xcode-select --install
```

### Recording starts but `audio status: input overflow` prints repeatedly

PortAudio can't keep up with the input rate, usually because the system is under load. The recording will still work — overflows just drop a few samples. If it's frequent, close other apps that use audio (Zoom, browser tabs with video, music players).

---

## Project Layout

```
voicepaste/
├── main.py              Entry point — wires everything together
├── recorder.py          Mic capture (sounddevice)
├── transcriber.py       Whisper model + transcription (faster-whisper)
├── hotkey.py            Global Right-Option listener (pynput)
├── paster.py            Clipboard write + auto-paste (pyperclip + pyautogui)
├── config.py            All tunables — sample rate, model size, hotkey, etc.
├── requirements.txt     Pinned dependencies
├── test.py              Standalone smoke test — loads the Whisper model and prints config
└── README.md            This file
```

All configurable values live in `config.py`. Don't hardcode anything elsewhere.

## Privacy

VoicePaste is fully local by default.

If you enable `READABILITY_MODE = "openai"`:
- audio still stays on your device
- only transcript text is sent to OpenAI for cleanup
- if the enhancement step fails, VoicePaste pastes the original transcript instead of blocking

---

## Roadmap

**Phase 2** (not yet built): replace the menubar icon with a small floating, always-on-top pill window. Same hotkey logic, different UI layer (tkinter or PyQt). The core modules above stay unchanged.
