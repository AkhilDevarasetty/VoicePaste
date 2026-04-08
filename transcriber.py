"""Whisper model loading and transcription via faster-whisper."""

import numpy as np
from faster_whisper import WhisperModel

import config


def load_model() -> WhisperModel:
    """Load the Whisper model using settings from config.py."""
    return WhisperModel(
        config.MODEL_SIZE,
        device=config.DEVICE,
        compute_type=config.COMPUTE_TYPE,
    )


def transcribe(model: WhisperModel, audio: np.ndarray) -> str:
    """Transcribe a mono float32 audio array (sampled at config.SAMPLE_RATE) to text.

    Uses VAD filtering to skip silent regions. Returns the joined transcript
    with surrounding whitespace stripped; an empty string means no speech was
    detected and the caller should warn and reset.
    """
    segments, _info = model.transcribe(audio, vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments).strip()
