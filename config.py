"""Single source of truth for all VoicePaste constants."""

from pynput import keyboard

SAMPLE_RATE: int = 16000
MAX_DURATION: int = 60  # seconds — safety auto-stop
MIN_RECORDING_SECONDS: float = 0.3
MODEL_SIZE: str = "base.en"
DEVICE: str = "cpu"
COMPUTE_TYPE: str = "int8"  # quantized — smaller, faster, same quality
HOTKEY: keyboard.Key = keyboard.Key.alt_r
LOG_TIME_FORMAT: str = "%Y-%m-%d %H:%M:%S.%f"

READABILITY_MODE: str = "openai"  # "off" or "openai"
OPENAI_MODEL: str = "gpt-4o-mini"
OPENAI_TIMEOUT_SECONDS: int = 5
OPENAI_MAX_OUTPUT_TOKENS: int = 500
OPENAI_API_KEY_ENV: str = "OPENAI_API_KEY"
MIN_TEXT_LENGTH_FOR_ENHANCEMENT: int = 50
