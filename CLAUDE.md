# VoicePaste — Claude Code Project Spec

## Project Overview
A macOS voice-to-text desktop app that runs 100% locally.
- Hold Right Option key → record mic → release → transcribe → auto-paste at cursor
- No internet, no API calls, no subscriptions
- Uses faster-whisper (OpenAI's Whisper model, optimized runtime by Systran)
- Target machine: Apple Silicon (M1/M2/M3), macOS

---

## How to Work on This Project

### Ground Rules
- Build module by module — do not write everything at once
- After each module, run a quick test to verify it works before moving on
- All config values must live in config.py — no hardcoded values anywhere else
- No asyncio — use threading only
- Type hints on every function
- Brief docstring on every function
- No global mutable state — use a shared AppState dataclass

### Build Order (follow this exactly)
1. Create project structure + requirements.txt
2. config.py
3. transcriber.py → test model loads correctly
4. recorder.py
5. hotkey.py
6. paster.py
7. main.py → wire everything together
8. README.md

---

## Project Structure

voicepaste/
├── main.py              # Entry point, wires all modules together
├── recorder.py          # Mic capture logic
├── transcriber.py       # Whisper model load + transcription
├── hotkey.py            # Global hotkey listener (pynput)
├── paster.py            # Clipboard + auto-paste at cursor
├── config.py            # All constants — single source of truth
├── requirements.txt     # Pinned dependencies
└── README.md            # Setup + permissions guide

---

## Tech Stack

| Purpose         | Library          |
|-----------------|------------------|
| Whisper runtime | faster-whisper   |
| Mic capture     | sounddevice      |
| Audio arrays    | numpy            |
| Global hotkey   | pynput           |
| Clipboard       | pyperclip        |
| Auto-paste      | pynput        |
| Menubar icon    | rumps            |

---

## config.py Values

SAMPLE_RATE = 16000
MAX_DURATION = 60        # seconds — safety auto-stop
MODEL_SIZE = "base.en"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"    # quantized — smaller, faster, same quality
HOTKEY = keyboard.Key.alt_r

---

## Behavior Requirements

### States & Feedback
| State        | Menubar Icon | Terminal Output         |
|--------------|--------------|--------------------------|
| Idle         | Grey mic 🎙️  | "VoicePaste ready"      |
| Recording    | Red mic 🔴   | "🎙️ Recording..."        |
| Transcribing | Yellow ⏳    | "🔄 Transcribing..."     |
| Done         | Grey mic 🎙️  | prints transcribed text  |

### Skip Conditions
- Audio clip < 0.3 seconds → warn and reset
- Transcription returns empty string → warn and reset

### VAD
- Enable VAD filter in faster-whisper transcription call

---

## Error Handling

| Scenario                  | Behavior                              |
|---------------------------|---------------------------------------|
| Mic permission denied     | Print clear error message, exit clean |
| Model load failure        | Print error, exit clean               |
| No audio captured         | Warn, reset state                     |
| Accessibility denied      | Print pynput permission instructions  |

---

## Environment

- Python 3.10+
- venv at ./venv
- Run command: source venv/bin/activate && python main.py
- Apple Silicon M1/M2/M3 — CPU inference only (no Metal/GPU for now)

---

## macOS Permissions Required
1. Microphone — for sounddevice to capture audio
2. Accessibility — for pynput to listen to global hotkeys

Both must be granted in System Settings → Privacy & Security.
README must include step-by-step instructions for both.

---

## Phase 2 (do NOT build yet — note for future)
Replace menubar icon with a floating always-on-top window (pill shaped).
Same hotkey logic, just different UI layer using tkinter or PyQt.
Core logic in all modules stays unchanged.

## Future Enhancement (do NOT build yet — note for future)
Add a hands-free dictation mode for long-form speech.
- Keep current hold Right Option behavior for short dictation.
- Add a separate hands-free trigger, likely `Fn + Space` or double-tap Right Option.
- In hands-free mode, do not force the user to hold a key for long paragraphs.
- Record/transcribe in chunks internally when needed, but accumulate the full result and paste once at the end.
- Provide a clear stop action for hands-free mode, likely the same trigger again or `Esc`.
- Do not silently drop spoken content when `MAX_DURATION` is hit; long-form mode should preserve captured speech.

## Future Enhancement (do NOT build yet — note for future)
Add draggable placement for the floating pill overlay.
- Keep a stable default fixed position.
- Let the user drag the pill to another location when idle.
- Persist the chosen position across restarts.
- Do not enable dragging while recording or processing.

## Future Enhancement (do NOT build yet — note for future)
Add chunk-aware readability enhancement for burst dictation.
- When the user dictates in multiple short chunks, keep each raw transcript chunk.
- If AI readability mode is enabled, do not improve each chunk independently as the final output.
- After the full burst/session ends, combine the chunks and run one final readability pass using the full context.
- Use the combined context-aware result as the final pasted output.
