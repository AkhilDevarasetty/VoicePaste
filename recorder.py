"""Microphone capture via sounddevice."""

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

import config


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
        self._accepting_audio = False
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
        with self._lock:
            if not self._accepting_audio:
                return
            self._chunks.append(indata.copy())

    def start(self) -> None:
        """Begin capturing audio. Non-blocking. Idempotent if already recording."""
        with self._lock:
            if self._stream is not None:
                return
            self._chunks = []
            self._started_at = datetime.now()
            self._accepting_audio = True
        stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        stream.start()
        timer = threading.Timer(config.MAX_DURATION, self._handle_timeout)
        timer.daemon = True
        timer.start()
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
            self._stream = None
            self._timer = None
            self._chunks = []
            self._started_at = None
            self._accepting_audio = False
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
        # Use abort() instead of stop() for input-only streams. This avoids
        # waiting for PortAudio to drain buffers, which is where we've seen
        # intermittent hangs during hotkey release on macOS.
        stream.abort(ignore_errors=True)
        stream.close(ignore_errors=True)
        if chunks:
            audio = np.concatenate(chunks, axis=0).flatten()
        else:
            audio = np.zeros(0, dtype=np.float32)
        duration_seconds = audio.size / config.SAMPLE_RATE
        if duration_seconds == 0.0 and started_at is not None:
            duration_seconds = (stopped_at - started_at).total_seconds()
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
            f"chunks={len(chunks)}, samples={audio.size})"
        )
        return result
