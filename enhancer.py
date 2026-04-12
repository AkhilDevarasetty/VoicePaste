"""Optional transcript readability enhancement."""

import os
import time
from typing import Callable, Optional

import requests

import config


def enhance(text: str, logger: Optional[Callable[[str], None]] = None) -> str:
    """Improve transcript readability according to the configured mode.

    Returns the original transcript unchanged when enhancement is disabled,
    skipped, or fails for any reason. This keeps paste behavior reliable even
    when the optional cloud cleanup path is unavailable.
    """
    start_time = time.perf_counter()
    cleaned = text.strip()
    if not cleaned:
        _log(logger, "skipping enhancement for empty transcript")
        return cleaned
    _log(
        logger,
        f"enhancement requested (mode={config.READABILITY_MODE}, chars={len(cleaned)})",
    )
    if config.READABILITY_MODE == "off":
        _log(logger, "enhancement disabled; using raw transcript")
        return cleaned
    if config.READABILITY_MODE != "openai":
        _log(
            logger,
            f"unsupported readability mode '{config.READABILITY_MODE}'; using raw transcript",
        )
        return cleaned
    if len(cleaned) < config.MIN_TEXT_LENGTH_FOR_ENHANCEMENT:
        _log(
            logger,
            f"skipping enhancement for short transcript ({len(cleaned)} chars < "
            f"{config.MIN_TEXT_LENGTH_FOR_ENHANCEMENT})",
        )
        return cleaned
    enhanced = _enhance_openai(cleaned, logger)
    elapsed = time.perf_counter() - start_time
    _log(
        logger,
        f"enhancement finished (input_chars={len(cleaned)}, output_chars={len(enhanced)}, elapsed={elapsed:.2f}s)",
    )
    return enhanced


def _enhance_openai(text: str, logger: Optional[Callable[[str], None]] = None) -> str:
    """Enhance transcript readability with the OpenAI Chat Completions API."""
    request_started = time.perf_counter()
    api_key = os.getenv(config.OPENAI_API_KEY_ENV, "").strip()
    if not api_key:
        _log(
            logger,
            f"missing {config.OPENAI_API_KEY_ENV}; using raw transcript",
        )
        return text

    payload = {
        "model": config.OPENAI_MODEL,
        "temperature": 0,
        "max_tokens": config.OPENAI_MAX_OUTPUT_TOKENS,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You clean up raw voice-to-text transcripts for readability while "
                    "preserving the speaker's original meaning, tone, and factual content."
                ),
            },
            {
                "role": "user",
                "content": _build_prompt(text),
            },
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=config.OPENAI_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as exc:
        elapsed = time.perf_counter() - request_started
        _log(
            logger,
            f"OpenAI enhancement failed after {elapsed:.2f}s: {exc}; using raw transcript",
        )
        return text
    except ValueError as exc:
        elapsed = time.perf_counter() - request_started
        _log(
            logger,
            f"OpenAI returned invalid JSON after {elapsed:.2f}s: {exc}; using raw transcript",
        )
        return text

    enhanced = _extract_text(body)
    if not enhanced:
        elapsed = time.perf_counter() - request_started
        _log(
            logger,
            f"OpenAI returned empty enhancement after {elapsed:.2f}s; using raw transcript",
        )
        return text
    elapsed = time.perf_counter() - request_started
    _log(logger, f"OpenAI enhancement succeeded in {elapsed:.2f}s")
    return enhanced


def _build_prompt(text: str) -> str:
    """Build the transcript-cleanup prompt with strict constraints."""
    return (
        "You receive a raw voice-to-text transcript. Clean it up by:\n"
        "- Fixing punctuation, capitalization, and obvious grammar errors\n"
        "- Removing filler words like um, uh, ah, and you know only when they are clearly fillers\n"
        "- Breaking long run-on sentences into shorter readable sentences\n"
        "- Splitting very long text into short paragraphs when it improves readability\n\n"
        "Do NOT:\n"
        "- Add information that was not in the original transcript\n"
        "- Change the original meaning or intent\n"
        "- Rephrase technical terms, code snippets, names, or jargon\n"
        "- Change the speaker's tone\n"
        "- Output any explanation, preamble, markdown, or quotation marks\n\n"
        "Output only the cleaned transcript text.\n\n"
        f"Transcript:\n{text}"
    )


def _extract_text(body: object) -> str:
    """Extract the cleaned transcript text from a chat completions response."""
    if not isinstance(body, dict):
        return ""
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""
    message = first_choice.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if not isinstance(content, str):
        return ""
    return content.strip()


def _log(logger: Optional[Callable[[str], None]], message: str) -> None:
    """Emit a namespaced log message when a logger callback is provided."""
    if logger is not None:
        logger(f"[enhancer] {message}")
