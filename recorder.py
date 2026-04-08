"""Microphone capture via sounddevice."""

import threading
from typing import Optional

import numpy as np
import sounddevice as sd

import config


class Recorder:
    """Captures mono float32 audio from the default input device.

    Non-blocking start/stop API. ``start()`` opens a sounddevice ``InputStream``
    that appends audio chunks to an internal buffer from sounddevice's PortAudio
    callback thread; ``stop()`` halts the stream and returns the concatenated
    1-D array. A safety ``threading.Timer`` enforces ``config.MAX_DURATION`` as
    an upper bound so a stuck hotkey can never record forever.
    """

    def __init__(self) -> None:
        """Initialize a recorder with no active stream."""
        self._stream: Optional[sd.InputStream] = None
        self._chunks: list[np.ndarray] = []
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

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
            self._chunks.append(indata.copy())

    def start(self) -> None:
        """Begin capturing audio. Non-blocking. Idempotent if already recording."""
        with self._lock:
            if self._stream is not None:
                return
            self._chunks = []
        stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        stream.start()
        timer = threading.Timer(config.MAX_DURATION, self.stop)
        timer.daemon = True
        timer.start()
        with self._lock:
            self._stream = stream
            self._timer = timer

    def stop(self) -> np.ndarray:
        """Stop recording and return the captured audio as a 1-D float32 array.

        Returns an empty array if not currently recording. Safe to call from
        any thread; concurrent or repeat calls are no-ops after the first.
        """
        with self._lock:
            stream = self._stream
            timer = self._timer
            chunks = self._chunks
            self._stream = None
            self._timer = None
            self._chunks = []
        if stream is None:
            return np.zeros(0, dtype=np.float32)
        if timer is not None:
            timer.cancel()
        # Release lock before stream.stop()/close() — they block until the
        # PortAudio callback drains, and the callback also takes _lock.
        stream.stop()
        stream.close()
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks, axis=0).flatten()
