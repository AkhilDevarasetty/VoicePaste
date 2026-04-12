"""Microphone capture via sounddevice."""

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

import config


def _hostapi_name(hostapi_index: object) -> str:
    """Return the PortAudio host API name for the provided host API index."""
    if not isinstance(hostapi_index, int):
        return "unknown"
    try:
        hostapi_info = sd.query_hostapis(hostapi_index)
    except Exception:
        return f"hostapi#{hostapi_index}"
    name = hostapi_info.get("name")
    if isinstance(name, str) and name:
        return name
    return f"hostapi#{hostapi_index}"


def describe_default_input_device() -> str:
    """Return a human-readable summary of the current default input device."""
    try:
        default_device = sd.default.device
    except Exception as exc:
        return f"default input device unavailable: {exc}"

    input_device: object = default_device
    if isinstance(default_device, (list, tuple)):
        input_device = default_device[0] if default_device else None
    if input_device in {None, -1}:
        return f"default_device={default_device!r}, input_device=none"

    try:
        device_info = sd.query_devices(device=input_device, kind="input")
    except Exception as exc:
        return (
            f"default_device={default_device!r}, input_device={input_device!r}, "
            f"query_failed={exc}"
        )

    return (
        f"default_device={default_device!r}, input_device={input_device!r}, "
        f"name={device_info.get('name')!r}, hostapi={_hostapi_name(device_info.get('hostapi'))}, "
        f"default_samplerate={device_info.get('default_samplerate')}, "
        f"max_input_channels={device_info.get('max_input_channels')}"
    )


@dataclass
class RecordingResult:
    """Captured audio plus metadata describing how recording ended."""

    audio: np.ndarray
    started_at: Optional[datetime]
    stopped_at: datetime
    stop_reason: str
    was_recording: bool
    chunk_count: int
    duration_seconds: float
    previous_stop_reason: Optional[str]


class Recorder:
    """Captures mono float32 audio from the default input device.

    Non-blocking start/stop API. ``start()`` opens a sounddevice ``InputStream``
    that appends audio chunks to an internal buffer from sounddevice's PortAudio
    callback thread; ``stop()`` halts the stream and returns the concatenated
    1-D array. A safety ``threading.Timer`` enforces ``config.MAX_DURATION`` as
    an upper bound so a stuck hotkey can never record forever.
    """

    def __init__(self, logger: Optional[Callable[[str], None]] = None) -> None:
        """Initialize a recorder with no active stream."""
        self._logger = logger
        self._stream: Optional[sd.InputStream] = None
        self._chunks: list[np.ndarray] = []
        self._timer: Optional[threading.Timer] = None
        self._started_at: Optional[datetime] = None
        self._last_stop_reason: Optional[str] = None
        self._last_chunk_at: Optional[datetime] = None
        self._callback_count: int = 0
        self._accepting_audio = False
        self._start_block_reason: Optional[str] = None
        self._lock = threading.Lock()

    def _log(self, message: str) -> None:
        """Emit a debug log line when a logger callback is available."""
        if self._logger is not None:
            self._logger(f"[recorder] {message}")

    def _handle_timeout(self) -> None:
        """Auto-stop recording when the max-duration timer fires."""
        self._log(f"max-duration timer fired at {config.MAX_DURATION}s")
        result = self.stop(reason="max_duration")
        if result.was_recording:
            self._log(
                "auto-stop completed "
                f"(duration={result.duration_seconds:.2f}s, chunks={result.chunk_count}, "
                f"samples={result.audio.size})"
            )

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        """sounddevice PortAudio callback — copy each chunk into the buffer."""
        if status:
            # Non-fatal: typically input overflow under load. Print and continue.
            print(f"⚠️  audio status: {status}")
            self._log(f"audio status warning: {status}")
        with self._lock:
            if not self._accepting_audio:
                return
            self._chunks.append(indata.copy())
            self._callback_count += 1
            self._last_chunk_at = datetime.now()

    def start(self) -> None:
        """Begin capturing audio. Non-blocking. Idempotent if already recording."""
        with self._lock:
            if self._stream is not None:
                return
            if self._start_block_reason is not None:
                raise RuntimeError(self._start_block_reason)
            self._chunks = []
            self._started_at = datetime.now()
            self._last_chunk_at = None
            self._callback_count = 0
            self._accepting_audio = True
        self._log(
            "creating InputStream "
            f"(sample_rate={config.SAMPLE_RATE}, channels=1, dtype=float32)"
        )
        stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._log("starting InputStream")
        stream.start()
        timer = threading.Timer(config.MAX_DURATION, self._handle_timeout)
        timer.daemon = True
        timer.start()
        self._log(f"max-duration timer started for {config.MAX_DURATION}s")
        with self._lock:
            self._stream = stream
            self._timer = timer
            started_at = self._started_at
        self._log(
            "recording started "
            f"(started_at={started_at}, sample_rate={config.SAMPLE_RATE}, "
            f"max_duration={config.MAX_DURATION}s)"
        )

    def stop(self, reason: str = "manual") -> RecordingResult:
        """Stop recording and return the captured audio plus stop metadata.

        Returns an empty array if not currently recording. Safe to call from
        any thread; concurrent or repeat calls are no-ops after the first.
        """
        stopped_at = datetime.now()
        with self._lock:
            stream = self._stream
            timer = self._timer
            chunks = self._chunks
            started_at = self._started_at
            previous_stop_reason = self._last_stop_reason
            last_chunk_at = self._last_chunk_at
            callback_count = self._callback_count
            self._stream = None
            self._timer = None
            self._chunks = []
            self._started_at = None
            self._last_chunk_at = None
            self._callback_count = 0
            self._accepting_audio = False
        self._log(
            "stop requested "
            f"(reason={reason}, previous_stop_reason={previous_stop_reason}, "
            f"callback_count={callback_count}, last_chunk_at={last_chunk_at})"
        )
        if stream is None:
            self._log(
                "stop() found no active recording "
                f"(requested_reason={reason}, previous_stop_reason={previous_stop_reason})"
            )
            return RecordingResult(
                audio=np.zeros(0, dtype=np.float32),
                started_at=started_at,
                stopped_at=stopped_at,
                stop_reason=reason,
                was_recording=False,
                chunk_count=0,
                duration_seconds=0.0,
                previous_stop_reason=previous_stop_reason,
            )
        if timer is not None:
            timer.cancel()
            self._log(f"max-duration timer cancelled for reason={reason}")
        # sounddevice itself uses stop() before close() in its exit handler,
        # with an inline note that close() can hang without the prior stop().
        # Keep that ordering here, but still bound the wait so the app doesn't
        # freeze forever if Core Audio/PortAudio wedges.
        self._log(f"stopping InputStream for reason={reason}")
        cleanup_done = threading.Event()
        cleanup_error: list[BaseException] = []

        def _cleanup_stream() -> None:
            """Stop and close the stream on a background thread."""
            try:
                cleanup_thread_name = threading.current_thread().name
                stop_started_at = time.perf_counter()
                self._log(f"{cleanup_thread_name} calling InputStream.stop")
                stream.stop(ignore_errors=True)
                self._log(
                    f"{cleanup_thread_name} InputStream.stop returned "
                    f"(elapsed={time.perf_counter() - stop_started_at:.3f}s)"
                )
                close_started_at = time.perf_counter()
                self._log(f"{cleanup_thread_name} calling InputStream.close")
                stream.close(ignore_errors=True)
                self._log(
                    f"{cleanup_thread_name} InputStream.close returned "
                    f"(elapsed={time.perf_counter() - close_started_at:.3f}s)"
                )
            except Exception as exc:
                cleanup_error.append(exc)
                self._log(f"stream cleanup raised {type(exc).__name__}: {exc}")
            finally:
                cleanup_done.set()

        cleanup_thread = threading.Thread(
            target=_cleanup_stream,
            name=f"recorder-cleanup-{reason}",
            daemon=True,
        )
        cleanup_thread.start()
        cleanup_wait_started_at = time.perf_counter()
        if cleanup_done.wait(config.STREAM_CLEANUP_TIMEOUT_SECONDS):
            self._log(
                "stream cleanup finished "
                f"(elapsed={time.perf_counter() - cleanup_wait_started_at:.3f}s, "
                f"errors={len(cleanup_error)})"
            )
            with self._lock:
                self._start_block_reason = None
        else:
            blocked_reason = (
                "microphone cleanup is stuck inside PortAudio/Core Audio. "
                "Restart VoicePaste and close any browser/app still using the mic."
            )
            with self._lock:
                self._start_block_reason = blocked_reason
            self._log(
                "⚠️  stream cleanup did NOT finish within "
                f"{config.STREAM_CLEANUP_TIMEOUT_SECONDS}s — blocking future "
                "recordings to avoid reusing a poisoned audio backend "
                f"(reason={reason}, device_snapshot={describe_default_input_device()})"
            )
        if chunks:
            audio = np.concatenate(chunks, axis=0).flatten()
        else:
            audio = np.zeros(0, dtype=np.float32)
        duration_seconds = audio.size / config.SAMPLE_RATE
        if duration_seconds == 0.0 and started_at is not None:
            duration_seconds = (stopped_at - started_at).total_seconds()
        last_chunk_age_seconds: Optional[float] = None
        if last_chunk_at is not None:
            last_chunk_age_seconds = (stopped_at - last_chunk_at).total_seconds()
        result = RecordingResult(
            audio=audio,
            started_at=started_at,
            stopped_at=stopped_at,
            stop_reason=reason,
            was_recording=True,
            chunk_count=len(chunks),
            duration_seconds=duration_seconds,
            previous_stop_reason=previous_stop_reason,
        )
        with self._lock:
            self._last_stop_reason = reason
        self._log(
            "recording stopped "
            f"(reason={reason}, duration={duration_seconds:.2f}s, "
            f"chunks={len(chunks)}, callbacks={callback_count}, samples={audio.size}, "
            f"last_chunk_age={last_chunk_age_seconds})"
        )
        return result
