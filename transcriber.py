"""Whisper model loading and transcription via faster-whisper."""

import time
from typing import Callable, Optional

import numpy as np
from faster_whisper import WhisperModel

import config


def load_model(logger: Optional[Callable[[str], None]] = None) -> WhisperModel:
    """Load the Whisper model using settings from config.py."""
    start_time = time.perf_counter()
    _log(
        logger,
        "loading model "
        f"(size={config.MODEL_SIZE}, device={config.DEVICE}, "
        f"compute_type={config.COMPUTE_TYPE})",
    )
    model = WhisperModel(
        config.MODEL_SIZE,
        device=config.DEVICE,
        compute_type=config.COMPUTE_TYPE,
    )
    elapsed = time.perf_counter() - start_time
    _log(logger, f"model loaded successfully in {elapsed:.2f}s")
    return model


def transcribe(
    model: WhisperModel,
    audio: np.ndarray,
    logger: Optional[Callable[[str], None]] = None,
) -> str:
    """Transcribe a mono float32 audio array (sampled at config.SAMPLE_RATE) to text.

    Uses VAD filtering to skip silent regions. Returns the joined transcript
    with surrounding whitespace stripped; an empty string means no speech was
    detected and the caller should warn and reset.
    """
    start_time = time.perf_counter()
    duration_seconds = audio.size / config.SAMPLE_RATE
    _log(
        logger,
        "starting transcription "
        f"(samples={audio.size}, duration={duration_seconds:.2f}s, vad_filter=True)",
    )
    segments, info = model.transcribe(audio, vad_filter=True)
    texts = [segment.text.strip() for segment in segments if segment.text.strip()]
    transcript = " ".join(texts).strip()
    elapsed = time.perf_counter() - start_time
    language = getattr(info, "language", "unknown")
    language_probability = getattr(info, "language_probability", None)
    probability_text = ""
    if isinstance(language_probability, (float, int)):
        probability_text = f", language_probability={language_probability:.2f}"
    _log(
        logger,
        "transcription completed "
        f"(segments={len(texts)}, chars={len(transcript)}, language={language}"
        f"{probability_text}, elapsed={elapsed:.2f}s)",
    )
    return transcript


def _log(logger: Optional[Callable[[str], None]], message: str) -> None:
    """Emit a namespaced log message when a logger callback is provided."""
    if logger is not None:
        logger(f"[transcriber] {message}")
