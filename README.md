# VoicePaste

A macOS voice-to-text utility that is **fully local by default**. Hold **Right Option**, talk, release, and your speech is transcribed by `faster-whisper` and pasted at the cursor. An optional cloud cleanup pass can be enabled for transcript text only (not audio) to improve readability before paste.

> **Note:** This is the initial phase of the project which uses a Menubar icon (🎙️/🔴/⏳) to show recording state. In **Phase 2**, the UI will transition to a floating, always-on-top pill window.

![VoicePaste Menubar Action Demo](assets/VoicePaste%20Menubar%20Action%20Demo.gif)

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

VoicePaste requires **two** permissions in **System Settings → Privacy & Security**. 

In modern versions of macOS, these permissions must be granted to the **parent application** running the script (e.g., the terminal you use to run `python main.py`), rather than the Python executable itself.

| How you run `python main.py` | Grant permissions to |
|---|---|
| Terminal.app | Terminal |
| iTerm2 | iTerm2 |
| VS Code integrated terminal | Visual Studio Code |
| Claude Code desktop app | Claude (Anthropic) |

### 3a. Microphone (Audio Recording)

The **first time** you run the app, macOS will typically prompt you: *"Terminal would like to access the microphone"*. Click **Allow** and you're good to go.

If you missed the prompt or accidentally clicked Deny:
1. Open **System Settings → Privacy & Security → Microphone**
2. Find your terminal app (e.g., Terminal, iTerm) in the list and toggle it **on**.

### 3b. Accessibility (Hotkeys & Pasting)

Accessibility is required for two reasons:
- **pynput** uses it to listen for the global `Right-Option` hotkey in the background.
- **pynput** also uses it to send the synthetic `⌘V` keystroke that automatically pastes the transcript.

Unlike the Microphone, macOS does **not** automatically prompt you to grant Accessibility access to terminal scripts. 

Steps to enable it manually:
1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the `+` button at the bottom of the list.
3. Navigate to and select the app you use to run VoicePaste (e.g., `Terminal` under Applications/Utilities, or `iTerm` / `Visual Studio Code` under Applications).
4. Make sure its toggle is **on**.
5. **Restart VoicePaste** — Accessibility permissions are only checked when the process starts.

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

### Note on Cursor Focus

VoicePaste relies on sending a simulated `⌘V` automatically when transcription finishes. **If you record your voice without the cursor actively placed in a text field** (e.g., you click away to another app or the desktop), the automatic paste will be lost. *However, the transcribed text is still saved to your system clipboard, so you can manually paste it later.*

---

## 6. Troubleshooting

### Recording is stuck sometimes

Occasionally, the app might get stuck in the recording state. The root cause of this issue is currently under investigation.

**Workaround:** If this happens, please click the recording menubar icon, select **Quit** to close VoicePaste, and restart the application from your terminal.

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

Some of the dependencies (`pynput`, `pyperclip`, `rumps`) build native code via pyobjc. If the build fails, install Xcode Command Line Tools and try again:

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
├── paster.py            Clipboard write + auto-paste (pyperclip + pynput)
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

**Future enhancement** (not yet built): add a hands-free dictation mode for long-form speech. Keep hold-to-talk for short dictation, but add a separate long-form trigger such as `Fn + Space` or a double-tap on Right Option. For long-form mode, chunk audio internally if needed, preserve everything the user said, and paste the combined result once at the end instead of forcing the user to hold a key for long paragraphs.

**Future enhancement** (not yet built): let the user drag the floating pill to a custom location. Keep a stable default position, allow dragging only while idle, and persist the chosen location across restarts.

**Future enhancement** (not yet built): support chunk-aware readability for burst dictation. Keep the raw transcript from each chunk, then if AI readability mode is enabled, run one final readability pass over the combined text so the cleanup step sees the full context instead of improving each chunk in isolation.

**Future enhancement**: voice formatting commands. Support spoken formatting actions such as newline, bullet list, paragraph break, and similar editing helpers.

**Future enhancement**: voice workflow commands. Support spoken requests that transform or refine dictated text, such as rewrite, summarize, or improve tone.

**Future enhancement**: voice agent actions. Support explicit spoken commands that trigger higher-level agent actions on the computer with clear confirmation and safety boundaries.
