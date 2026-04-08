"""Single source of truth for all VoicePaste constants."""

from pynput import keyboard

SAMPLE_RATE: int = 16000
MAX_DURATION: int = 60  # seconds — safety auto-stop
MODEL_SIZE: str = "base.en"
DEVICE: str = "cpu"
COMPUTE_TYPE: str = "int8"  # quantized — smaller, faster, same quality
HOTKEY: keyboard.Key = keyboard.Key.alt_r
