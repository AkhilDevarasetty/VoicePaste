"""Microphone capture with pluggable backends and idle stream teardown."""

import os
import threading
import tempfile
import time
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal, Optional

import numpy as np

try:
    from AVFoundation import (
        AVCaptureDevice,
        AVAudioRecorder,
        AVFormatIDKey,
        AVLinearPCMBitDepthKey,
        AVLinearPCMIsBigEndianKey,
        AVLinearPCMIsFloatKey,
        AVMediaTypeAudio,
        AVNumberOfChannelsKey,
        AVSampleRateKey,
    )
    from CoreAudio import kAudioFormatLinearPCM
    from Foundation import NSDate, NSRunLoop, NSURL
except ImportError:
    AVCaptureDevice = None
    AVAudioRecorder = None
    AVFormatIDKey = None
    AVLinearPCMBitDepthKey = None
    AVLinearPCMIsBigEndianKey = None
    AVLinearPCMIsFloatKey = None
    AVMediaTypeAudio = None
    AVNumberOfChannelsKey = None
    AVSampleRateKey = None
    kAudioFormatLinearPCM = None
    NSDate = None
    NSRunLoop = None
    NSURL = None

try:
    import soundcard as sc
except ImportError:
    sc = None

try:
    import sounddevice as sd
except ImportError:
    sd = None

import config


AudioBackend = Literal["pyobjc", "soundcard", "sounddevice"]


def active_audio_backend() -> AudioBackend:
    """Return the configured audio backend, validating supported values."""
    backend = config.AUDIO_BACKEND.lower()
    if backend not in {"pyobjc", "soundcard", "sounddevice"}:
        raise ValueError(
            f"Unsupported AUDIO_BACKEND={config.AUDIO_BACKEND!r}. "
            "Expected 'pyobjc', 'soundcard', or 'sounddevice'."
        )
    return backend


def _hostapi_name(hostapi_index: object) -> str:
    """Return the PortAudio host API name for the provided host API index."""
    if sd is None:
        return "sounddevice unavailable"
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
    if active_audio_backend() == "pyobjc":
        return _describe_default_input_device_pyobjc()
    if active_audio_backend() == "soundcard":
        return _describe_default_input_device_soundcard()
    return _describe_default_input_device_sounddevice()


def _describe_default_input_device_sounddevice() -> str:
    """Describe the default input device when using the sounddevice backend."""
    if sd is None:
        return "backend=sounddevice, module unavailable"
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


def _describe_default_input_device_soundcard() -> str:
    """Describe the default microphone when using the SoundCard backend."""
    if sc is None:
        return "backend=soundcard, module unavailable"
    try:
        mic = sc.default_microphone()
    except Exception as exc:
        return f"backend=soundcard, default_microphone query failed: {exc}"
    if mic is None:
        return "backend=soundcard, default_microphone=none"
    try:
        mic_name = mic.name
    except Exception as exc:
        mic_name = f"<unavailable: {type(exc).__name__}: {exc}>"
    try:
        mic_channels = mic.channels
    except Exception as exc:
        mic_channels = f"<unavailable: {type(exc).__name__}: {exc}>"
    return (
        "backend=soundcard, "
        f"name={mic_name!r}, "
        f"id={getattr(mic, 'id', None)!r}, "
        f"channels={mic_channels!r}"
    )


def _describe_default_input_device_pyobjc() -> str:
    """Describe the default microphone when using the PyObjC backend."""
    if AVCaptureDevice is None or AVMediaTypeAudio is None:
        return "backend=pyobjc, module unavailable"
    try:
        device = AVCaptureDevice.defaultDeviceWithMediaType_(AVMediaTypeAudio)
    except Exception as exc:
        return f"backend=pyobjc, default audio device query failed: {exc}"
    if device is None:
        return "backend=pyobjc, default_audio_device=none"
    try:
        name = device.localizedName()
    except Exception as exc:
        name = f"<unavailable: {type(exc).__name__}: {exc}>"
    try:
        unique_id = device.uniqueID()
    except Exception as exc:
        unique_id = f"<unavailable: {type(exc).__name__}: {exc}>"
    try:
        connected = device.isConnected()
    except Exception as exc:
        connected = f"<unavailable: {type(exc).__name__}: {exc}>"
    return (
        "backend=pyobjc, "
        f"name={name!r}, "
        f"unique_id={unique_id!r}, "
        f"connected={connected!r}"
    )


def _default_input_device_id() -> Optional[tuple]:
    """Return a stable identifier for the current default input device."""
    if active_audio_backend() == "pyobjc":
        return _default_input_device_id_pyobjc()
    if active_audio_backend() == "soundcard":
        return _default_input_device_id_soundcard()
    return _default_input_device_id_sounddevice()


def _default_input_device_id_sounddevice() -> Optional[tuple]:
    """Return the default input device identifier for sounddevice."""
    if sd is None:
        return None
    try:
        info = sd.query_devices(kind="input")
        return (info.get("name"), info.get("hostapi"), info.get("index"))
    except Exception:
        return None


def _default_input_device_id_soundcard() -> Optional[tuple]:
    """Return the default microphone identifier for SoundCard."""
    if sc is None:
        return None
    try:
        microphones = sc.all_microphones()
        if not microphones:
            return None
        mic = sc.default_microphone()
    except Exception:
        return None
    if mic is None:
        return None
    return (
        getattr(mic, "name", repr(mic)),
        getattr(mic, "id", None),
    )


def _default_input_device_id_pyobjc() -> Optional[tuple]:
    """Return the default microphone identifier for the PyObjC backend."""
    if AVCaptureDevice is None or AVMediaTypeAudio is None:
        return None
    try:
        device = AVCaptureDevice.defaultDeviceWithMediaType_(AVMediaTypeAudio)
    except Exception:
        return None
    if device is None:
        return None
    try:
        name = device.localizedName()
    except Exception:
        name = "unknown"
    try:
        unique_id = device.uniqueID()
    except Exception:
        unique_id = None
    return (name, unique_id)


def probe_microphone_access(logger: Optional[Callable[[str], None]] = None) -> None:
    """Open the configured backend briefly to trigger permissions and validate input."""
    backend = active_audio_backend()
    if backend == "pyobjc":
        _probe_microphone_access_pyobjc(logger)
        return
    if backend == "soundcard":
        _probe_microphone_access_soundcard(logger)
        return
    _probe_microphone_access_sounddevice(logger)


def _probe_microphone_access_sounddevice(
    logger: Optional[Callable[[str], None]] = None,
) -> None:
    """Probe microphone access through sounddevice/PortAudio."""
    if sd is None:
        raise RuntimeError(
            "AUDIO_BACKEND is 'sounddevice' but the sounddevice package is not installed."
        )
    if logger is not None:
        logger(
            "[startup] checking microphone input settings with sounddevice "
            f"(sample_rate={config.SAMPLE_RATE}, channels=1, dtype=float32)"
        )
    sd.check_input_settings(
        samplerate=config.SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    if logger is not None:
        logger("[startup] sounddevice input settings accepted")
        logger("[startup] checking microphone access with a short sounddevice InputStream probe")
    stream = sd.InputStream(
        samplerate=config.SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    if logger is not None:
        logger("[startup] sounddevice InputStream probe created")
    stream.start()
    if logger is not None:
        logger("[startup] sounddevice InputStream probe started")
    stream.stop()
    if logger is not None:
        logger("[startup] sounddevice InputStream probe stopped")
    stream.close()
    if logger is not None:
        logger("[startup] sounddevice InputStream probe closed")


def _probe_microphone_access_soundcard(
    logger: Optional[Callable[[str], None]] = None,
) -> None:
    """Probe microphone access through SoundCard/CoreAudio."""
    if sc is None:
        raise RuntimeError(
            "AUDIO_BACKEND is 'soundcard' but the SoundCard package is not installed."
        )
    microphones = sc.all_microphones()
    if not microphones:
        raise RuntimeError("SoundCard did not enumerate any microphones on this system.")
    mic = sc.default_microphone()
    if mic is None:
        raise RuntimeError("No default microphone available for SoundCard.")
    if logger is not None:
        logger(
            "[startup] checking microphone access with SoundCard "
            f"(sample_rate={config.SAMPLE_RATE}, channels=1, "
            f"blocksize={config.SOUNDCARD_BLOCKSIZE})"
        )
    with mic.recorder(
        samplerate=config.SAMPLE_RATE,
        channels=1,
        blocksize=config.SOUNDCARD_BLOCKSIZE,
    ) as recorder:
        if logger is not None:
            logger("[startup] SoundCard recorder probe opened")
        data = np.asarray(
            recorder.record(numframes=config.SOUNDCARD_BLOCKSIZE),
            dtype=np.float32,
        )
        if logger is not None:
            logger(
                "[startup] SoundCard recorder probe read "
                f"{data.shape[0] if data.ndim > 0 else 0} frames"
            )
    if logger is not None:
        logger("[startup] SoundCard recorder probe closed")


def _create_pyobjc_recorder(path: Path) -> object:
    """Create and prepare an AVAudioRecorder configured for 16 kHz mono WAV."""
    if (
        AVAudioRecorder is None
        or NSURL is None
        or AVFormatIDKey is None
        or AVSampleRateKey is None
        or AVNumberOfChannelsKey is None
        or AVLinearPCMBitDepthKey is None
        or AVLinearPCMIsFloatKey is None
        or AVLinearPCMIsBigEndianKey is None
        or kAudioFormatLinearPCM is None
    ):
        raise RuntimeError(
            "AUDIO_BACKEND is 'pyobjc' but AVFoundation/CoreAudio bindings are not installed."
        )
    url = NSURL.fileURLWithPath_(str(path))
    settings = {
        AVFormatIDKey: kAudioFormatLinearPCM,
        AVSampleRateKey: float(config.SAMPLE_RATE),
        AVNumberOfChannelsKey: 1,
        AVLinearPCMBitDepthKey: 16,
        AVLinearPCMIsFloatKey: False,
        AVLinearPCMIsBigEndianKey: False,
    }
    recorder, error = AVAudioRecorder.alloc().initWithURL_settings_error_(
        url,
        settings,
        None,
    )
    if recorder is None:
        raise RuntimeError(f"AVAudioRecorder initialization failed: {error}")
    if not recorder.prepareToRecord():
        raise RuntimeError("AVAudioRecorder.prepareToRecord() returned False.")
    return recorder


def _sleep_native(seconds: float) -> None:
    """Wait while giving Foundation-backed APIs a chance to process queued work."""
    if NSRunLoop is not None and NSDate is not None:
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(seconds)
        )
        return
    time.sleep(seconds)


def _read_wav_file(path: Path) -> np.ndarray:
    """Load a mono float32 waveform from the provided WAV file path."""
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()
        raw_frames = wav_file.readframes(frame_count)

    if sample_rate != config.SAMPLE_RATE:
        raise RuntimeError(
            f"Unexpected sample rate from AVAudioRecorder: {sample_rate} "
            f"(expected {config.SAMPLE_RATE})."
        )
    if sample_width == 2:
        audio = np.frombuffer(raw_frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(raw_frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise RuntimeError(f"Unsupported WAV sample width: {sample_width}")

    if channels > 1:
        audio = audio.reshape(-1, channels)[:, 0]
    return audio


def _probe_microphone_access_pyobjc(
    logger: Optional[Callable[[str], None]] = None,
) -> None:
    """Probe microphone access through AVFoundation via PyObjC."""
    current_device = _default_input_device_id_pyobjc()
    fd, path_str = tempfile.mkstemp(prefix="voicepaste-pyobjc-probe-", suffix=".wav")
    os.close(fd)
    path = Path(path_str)
    try:
        if logger is not None:
            logger(
                "[startup] checking microphone access with PyObjC AVFoundation "
                f"(sample_rate={config.SAMPLE_RATE}, channels=1, device={current_device})"
            )
        recorder = _create_pyobjc_recorder(path)
        if logger is not None:
            logger("[startup] AVAudioRecorder probe created")
        started = recorder.record()
        if logger is not None:
            logger(f"[startup] AVAudioRecorder probe start result={started}")
        if not started:
            raise RuntimeError(
                "AVAudioRecorder failed to start. "
                "Check microphone permission for the host app."
            )
        _sleep_native(0.05)
        recorder.stop()
        if logger is not None:
            logger("[startup] AVAudioRecorder probe stopped")
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


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

    Supports a PortAudio-based ``sounddevice`` backend and a CoreAudio-based
    ``soundcard`` backend. Both keep a persistent capture object open across
    recordings for fast reuse and close it after a configurable idle timeout
    so the macOS orange mic indicator disappears when not actively dictating.
    """

    def __init__(
        self,
        logger: Optional[Callable[[str], None]] = None,
        on_auto_stop: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialize a recorder with no active stream."""
        self._logger = logger
        self._on_auto_stop = on_auto_stop

        # Stream lifecycle — guarded by _stream_lock
        self._stream = None
        self._stream_device_id: Optional[tuple] = None
        self._stream_lock = threading.Lock()
        self._soundcard_context = None
        self._soundcard_recorder = None
        self._soundcard_thread: Optional[threading.Thread] = None
        self._soundcard_stop_event: Optional[threading.Event] = None
        self._pyobjc_recorder = None
        self._pyobjc_recording_path: Optional[Path] = None

        # Teardown tracking — _teardown_in_progress is written only by the
        # teardown thread (under _stream_lock at initiation time, set back
        # to False in the teardown finally-block).  _teardown_done is an
        # Event that callers can wait on.
        self._teardown_in_progress: bool = False
        self._teardown_done = threading.Event()
        self._teardown_done.set()  # no teardown pending at init

        # Recording state — _accepting_audio is read lock-free by the
        # PortAudio callback (atomic bool read under CPython GIL).
        # _recording_lock guards the chunk snapshot in stop().
        self._chunks: list[np.ndarray] = []
        self._accepting_audio: bool = False
        self._started_at: Optional[datetime] = None
        self._last_chunk_at: Optional[datetime] = None
        self._callback_count: int = 0
        self._last_stop_reason: Optional[str] = None
        self._pending_stop_result: Optional[RecordingResult] = None
        self._session_kind: str = "hold"
        self._speech_detected: bool = False
        self._silence_started_at: Optional[float] = None
        self._recording_lock = threading.Lock()

        # Idle timeout — guarded by _idle_timer_lock
        self._idle_timer: Optional[threading.Timer] = None
        self._idle_timer_lock = threading.Lock()

        # Max-duration safety timer
        self._max_timer: Optional[threading.Timer] = None
        self._meter_timer: Optional[threading.Timer] = None
        self._meter_timer_lock = threading.Lock()
        self._metering_enabled: bool = False

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        """Emit a debug log line when a logger callback is available."""
        if self._logger is not None:
            self._logger(f"[recorder] {message}")

    # ------------------------------------------------------------------
    # PortAudio callback — lock-free
    # ------------------------------------------------------------------

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: object,
    ) -> None:
        """PortAudio callback — runs at real-time priority, no locks.

        ``_accepting_audio`` is a Python bool; reads are atomic under the
        CPython GIL.  ``list.append`` is also GIL-atomic.  One in-flight
        callback may append a final chunk after ``stop()`` flips the flag
        — that extra ~10 ms of audio is intentional and harmless.
        """
        if status:
            print(f"⚠️  audio status: {status}")
            self._log(f"audio status warning: {status}")
        if not self._accepting_audio:
            return
        self._chunks.append(indata.copy())
        self._callback_count += 1
        self._last_chunk_at = datetime.now()

    # ------------------------------------------------------------------
    # Stream lifecycle
    # ------------------------------------------------------------------

    def _ensure_stream(self) -> None:
        """Guarantee a live capture backend exists, creating one if needed."""
        backend = active_audio_backend()
        if backend == "pyobjc":
            return
        if backend == "soundcard":
            self._ensure_soundcard_stream()
            return
        self._ensure_sounddevice_stream()

    def _ensure_sounddevice_stream(self) -> None:
        """Guarantee a live InputStream exists, creating one if needed.

        If a previous teardown is still in progress we wait up to
        ``STREAM_TEARDOWN_WAIT_SECONDS`` for it to finish before attempting
        to open a new stream.  Opening a new stream while an old one's
        teardown is hung may deadlock at the Core Audio device level.
        """
        with self._stream_lock:
            current_device = _default_input_device_id()

            if self._stream is not None:
                # Stream exists — check if it is still usable.
                if self._stream.active:
                    if (
                        not config.STREAM_DEVICE_CHECK_ENABLED
                        or current_device == self._stream_device_id
                    ):
                        return  # reuse — common fast path
                    # Device changed while stream was open.
                    self._log(
                        f"input device changed "
                        f"({self._stream_device_id} -> {current_device}), "
                        "tearing down old stream"
                    )
                    self._teardown_stream_locked(reason="device_change")
                else:
                    self._log("stream exists but is not active, tearing down")
                    self._teardown_stream_locked(reason="stream_inactive")
                # Fall through to wait-and-create below.

            needs_wait = self._teardown_in_progress

        # Wait for any in-progress teardown OUTSIDE the lock so other
        # threads are not blocked.
        if needs_wait:
            self._log(
                "waiting for previous teardown to complete "
                f"(timeout={config.STREAM_TEARDOWN_WAIT_SECONDS}s)"
            )
            completed = self._teardown_done.wait(
                timeout=config.STREAM_TEARDOWN_WAIT_SECONDS,
            )
            if not completed:
                self._log(
                    "previous teardown still hung after "
                    f"{config.STREAM_TEARDOWN_WAIT_SECONDS}s"
                )
                raise RuntimeError(
                    "Previous stream teardown still in progress. "
                    "Try again in a few seconds, or restart VoicePaste."
                )

        # Re-acquire lock and create stream.
        with self._stream_lock:
            # Another thread may have created the stream while we waited.
            if self._stream is not None and self._stream.active:
                return
            self._log(
                "creating persistent InputStream "
                f"(sample_rate={config.SAMPLE_RATE}, channels=1, "
                f"dtype=float32, device={current_device})"
            )
            if sd is None:
                raise RuntimeError(
                    "AUDIO_BACKEND is 'sounddevice' but the sounddevice package is not installed."
                )
            stream = sd.InputStream(
                samplerate=config.SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=self._callback,
            )
            stream.start()
            self._stream = stream
            self._stream_device_id = current_device
            self._log("persistent InputStream started")

    def _ensure_soundcard_stream(self) -> None:
        """Guarantee a live SoundCard recorder thread exists, creating one if needed."""
        with self._stream_lock:
            current_device = _default_input_device_id()

            if self._soundcard_recorder is not None:
                thread_alive = (
                    self._soundcard_thread is not None
                    and self._soundcard_thread.is_alive()
                )
                if thread_alive:
                    if (
                        not config.STREAM_DEVICE_CHECK_ENABLED
                        or current_device == self._stream_device_id
                    ):
                        return
                    self._log(
                        f"input device changed "
                        f"({self._stream_device_id} -> {current_device}), "
                        "tearing down old SoundCard recorder"
                    )
                    self._teardown_stream_locked(reason="device_change")
                else:
                    self._log(
                        "SoundCard recorder exists but capture thread is not alive, tearing down"
                    )
                    self._teardown_stream_locked(reason="stream_inactive")

            needs_wait = self._teardown_in_progress

        if needs_wait:
            self._log(
                "waiting for previous teardown to complete "
                f"(timeout={config.STREAM_TEARDOWN_WAIT_SECONDS}s)"
            )
            completed = self._teardown_done.wait(
                timeout=config.STREAM_TEARDOWN_WAIT_SECONDS,
            )
            if not completed:
                self._log(
                    "previous teardown still hung after "
                    f"{config.STREAM_TEARDOWN_WAIT_SECONDS}s"
                )
                raise RuntimeError(
                    "Previous stream teardown still in progress. "
                    "Try again in a few seconds, or restart VoicePaste."
                )

        with self._stream_lock:
            thread_alive = (
                self._soundcard_thread is not None
                and self._soundcard_thread.is_alive()
            )
            if self._soundcard_recorder is not None and thread_alive:
                return
            if sc is None:
                raise RuntimeError(
                    "AUDIO_BACKEND is 'soundcard' but the SoundCard package is not installed."
                )
            microphones = sc.all_microphones()
            if not microphones:
                raise RuntimeError(
                    "SoundCard did not enumerate any microphones on this system."
                )
            mic = sc.default_microphone()
            if mic is None:
                raise RuntimeError("No default microphone available for SoundCard.")
            self._log(
                "creating persistent SoundCard recorder "
                f"(sample_rate={config.SAMPLE_RATE}, channels=1, "
                f"blocksize={config.SOUNDCARD_BLOCKSIZE}, device={current_device})"
            )
            context = mic.recorder(
                samplerate=config.SAMPLE_RATE,
                channels=1,
                blocksize=config.SOUNDCARD_BLOCKSIZE,
            )
            recorder = context.__enter__()
            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._soundcard_capture_loop,
                args=(recorder, stop_event),
                name="soundcard-capture",
                daemon=True,
            )
            thread.start()
            self._soundcard_context = context
            self._soundcard_recorder = recorder
            self._soundcard_stop_event = stop_event
            self._soundcard_thread = thread
            self._stream_device_id = current_device
            self._log("persistent SoundCard recorder started")

    def _soundcard_capture_loop(self, recorder: object, stop_event: threading.Event) -> None:
        """Continuously drain SoundCard frames while the recorder stays open."""
        try:
            while not stop_event.is_set():
                data = np.asarray(
                    recorder.record(numframes=config.SOUNDCARD_BLOCKSIZE),
                    dtype=np.float32,
                )
                if data.size == 0:
                    continue
                if data.ndim == 1:
                    chunk = data.reshape(-1, 1)
                else:
                    chunk = data[:, :1]
                if not self._accepting_audio:
                    continue
                self._chunks.append(chunk.copy())
                self._callback_count += 1
                self._last_chunk_at = datetime.now()
        except Exception as exc:
            self._log(f"SoundCard capture loop stopped with error: {type(exc).__name__}: {exc}")

    def _teardown_stream_locked(self, reason: str) -> None:
        """Begin tearing down the current capture backend on a background thread.

        Caller MUST hold ``_stream_lock``.  The stream reference is
        cleared immediately so ``_ensure_stream`` knows it needs a new
        one.  The actual ``abort()``/``close()`` happens on a daemon
        thread.  ``_teardown_done`` is signaled when it finishes (or
        fails).
        """
        if active_audio_backend() == "soundcard":
            self._teardown_soundcard_stream_locked(reason)
            return
        self._teardown_sounddevice_stream_locked(reason)

    def _teardown_sounddevice_stream_locked(self, reason: str) -> None:
        """Tear down the active sounddevice InputStream on a background thread."""
        stream = self._stream
        self._stream = None
        self._stream_device_id = None

        if stream is None:
            return

        self._teardown_in_progress = True
        self._teardown_done.clear()

        def _do_teardown() -> None:
            teardown_started = time.perf_counter()
            try:
                self._log(f"teardown calling abort (reason={reason})")
                stream.abort(ignore_errors=True)
                abort_elapsed = time.perf_counter() - teardown_started
                self._log(f"teardown abort returned (elapsed={abort_elapsed:.3f}s)")

                close_started = time.perf_counter()
                self._log(f"teardown calling close (reason={reason})")
                stream.close(ignore_errors=True)
                close_elapsed = time.perf_counter() - close_started
                self._log(
                    f"teardown completed "
                    f"(reason={reason}, abort={abort_elapsed:.3f}s, "
                    f"close={close_elapsed:.3f}s, "
                    f"total={time.perf_counter() - teardown_started:.3f}s)"
                )
            except Exception as exc:
                self._log(
                    f"teardown error (reason={reason}): "
                    f"{type(exc).__name__}: {exc}"
                )
            finally:
                self._teardown_in_progress = False
                self._teardown_done.set()

        threading.Thread(
            target=_do_teardown,
            name=f"stream-teardown-{reason}",
            daemon=True,
        ).start()

    def _teardown_soundcard_stream_locked(self, reason: str) -> None:
        """Tear down the active SoundCard recorder on a background thread."""
        context = self._soundcard_context
        thread = self._soundcard_thread
        stop_event = self._soundcard_stop_event
        self._soundcard_context = None
        self._soundcard_recorder = None
        self._soundcard_thread = None
        self._soundcard_stop_event = None
        self._stream_device_id = None

        if context is None and thread is None and stop_event is None:
            return

        self._teardown_in_progress = True
        self._teardown_done.clear()

        def _do_teardown() -> None:
            teardown_started = time.perf_counter()
            try:
                if stop_event is not None:
                    self._log(f"teardown signalling SoundCard capture thread (reason={reason})")
                    stop_event.set()
                if thread is not None:
                    self._log(f"teardown joining SoundCard capture thread (reason={reason})")
                    thread.join(timeout=config.STREAM_TEARDOWN_WAIT_SECONDS)
                if context is not None:
                    close_started = time.perf_counter()
                    self._log(f"teardown closing SoundCard recorder (reason={reason})")
                    context.__exit__(None, None, None)
                    close_elapsed = time.perf_counter() - close_started
                    self._log(
                        f"teardown completed "
                        f"(reason={reason}, close={close_elapsed:.3f}s, "
                        f"total={time.perf_counter() - teardown_started:.3f}s)"
                    )
                else:
                    self._log(
                        f"teardown completed "
                        f"(reason={reason}, total={time.perf_counter() - teardown_started:.3f}s)"
                    )
            except Exception as exc:
                self._log(
                    f"teardown error (reason={reason}): "
                    f"{type(exc).__name__}: {exc}"
                )
            finally:
                self._teardown_in_progress = False
                self._teardown_done.set()

        threading.Thread(
            target=_do_teardown,
            name=f"stream-teardown-{reason}",
            daemon=True,
        ).start()

    # ------------------------------------------------------------------
    # Idle timeout
    # ------------------------------------------------------------------

    def _start_idle_timer(self) -> None:
        """Start the countdown to close the stream after idle."""
        with self._idle_timer_lock:
            if self._idle_timer is not None:
                self._idle_timer.cancel()
            timer = threading.Timer(
                config.STREAM_IDLE_TIMEOUT_SECONDS,
                self._handle_idle_timeout,
            )
            timer.daemon = True
            timer.start()
            self._idle_timer = timer
        self._log(
            f"idle timer started ({config.STREAM_IDLE_TIMEOUT_SECONDS}s)"
        )

    def _cancel_idle_timer(self) -> None:
        """Cancel a pending idle timer (user started a new recording)."""
        with self._idle_timer_lock:
            if self._idle_timer is not None:
                self._idle_timer.cancel()
                self._idle_timer = None

    def _cancel_meter_timer(self) -> None:
        """Cancel the hands-free silence polling timer."""
        with self._meter_timer_lock:
            self._metering_enabled = False
            if self._meter_timer is not None:
                self._meter_timer.cancel()
                self._meter_timer = None

    def _schedule_meter_poll(self) -> None:
        """Schedule the next hands-free meter poll when metering is enabled."""
        with self._meter_timer_lock:
            if not self._metering_enabled:
                return
            timer = threading.Timer(
                config.HANDS_FREE_METER_POLL_SECONDS,
                self._poll_pyobjc_meters,
            )
            timer.daemon = True
            timer.start()
            self._meter_timer = timer

    def _enable_hands_free_metering(self, recorder: object) -> None:
        """Enable PyObjC level metering so silence can end hands-free sessions."""
        if self._session_kind != "hands_free":
            self._cancel_meter_timer()
            return
        try:
            recorder.setMeteringEnabled_(True)
        except Exception as exc:
            self._cancel_meter_timer()
            self._log(
                "hands-free meter polling unavailable; "
                f"falling back to Esc/max-duration only: {type(exc).__name__}: {exc}"
            )
            return
        with self._recording_lock:
            self._speech_detected = False
            self._silence_started_at = None
        with self._meter_timer_lock:
            self._metering_enabled = True
        self._log(
            "hands-free meter polling enabled "
            f"(poll={config.HANDS_FREE_METER_POLL_SECONDS:.1f}s, "
            f"threshold={config.HANDS_FREE_SILENCE_THRESHOLD_DB:.1f}dB, "
            f"silence={config.HANDS_FREE_SILENCE_SECONDS:.1f}s)"
        )
        self._schedule_meter_poll()

    def _poll_pyobjc_meters(self) -> None:
        """Poll AVAudioRecorder metering for hands-free silence detection."""
        with self._meter_timer_lock:
            self._meter_timer = None
            metering_enabled = self._metering_enabled
        if not metering_enabled or not self._accepting_audio:
            return

        with self._stream_lock:
            recorder = self._pyobjc_recorder
        if recorder is None:
            return

        try:
            recorder.updateMeters()
            power_db = float(recorder.averagePowerForChannel_(0))
        except Exception as exc:
            self._log(
                "hands-free meter polling disabled after error: "
                f"{type(exc).__name__}: {exc}"
            )
            self._cancel_meter_timer()
            return

        now = time.monotonic()
        should_fire_silence_timeout = False
        should_log_speech_detected = False
        should_log_silence_started = False
        should_log_silence_reset = False
        with self._recording_lock:
            if not self._accepting_audio or self._session_kind != "hands_free":
                pass
            elif power_db > config.HANDS_FREE_SILENCE_THRESHOLD_DB:
                if not self._speech_detected:
                    self._speech_detected = True
                    should_log_speech_detected = True
                if self._silence_started_at is not None:
                    self._silence_started_at = None
                    should_log_silence_reset = True
            elif self._speech_detected:
                if self._silence_started_at is None:
                    self._silence_started_at = now
                    should_log_silence_started = True
                elif now - self._silence_started_at >= config.HANDS_FREE_SILENCE_SECONDS:
                    self._silence_started_at = None
                    should_fire_silence_timeout = True

        if should_log_speech_detected:
            self._log(
                f"hands-free speech detected (power={power_db:.1f}dB)"
            )
        if should_log_silence_started:
            self._log(
                "hands-free silence countdown started "
                f"(power={power_db:.1f}dB, timeout={config.HANDS_FREE_SILENCE_SECONDS:.1f}s)"
            )
        if should_log_silence_reset:
            self._log(
                f"hands-free silence countdown reset by speech (power={power_db:.1f}dB)"
            )
        if should_fire_silence_timeout:
            self._handle_silence_timeout()
            return

        with self._meter_timer_lock:
            should_reschedule = self._metering_enabled and self._accepting_audio
        if should_reschedule:
            self._schedule_meter_poll()

    def _handle_idle_timeout(self) -> None:
        """Idle timer fired — close the stream if not recording."""
        if self._accepting_audio:
            self._log(
                "idle timeout fired but recording is active, skipping close"
            )
            return
        self._log("idle timeout fired, closing persistent stream")
        with self._stream_lock:
            self._teardown_stream_locked(reason="idle_timeout")
        with self._idle_timer_lock:
            self._idle_timer = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, session_kind: str = "hold") -> None:
        """Begin capturing audio.  Non-blocking.  Idempotent if already recording."""
        self._session_kind = session_kind
        if active_audio_backend() == "pyobjc":
            self._start_pyobjc(session_kind=session_kind)
            return
        self._cancel_idle_timer()
        self._cancel_meter_timer()
        self._ensure_stream()

        # Reset recording state.  _accepting_audio is written last so the
        # callback cannot see a half-initialised buffer.
        self._chunks = []
        self._started_at = datetime.now()
        self._last_chunk_at = None
        self._callback_count = 0
        self._pending_stop_result = None
        self._speech_detected = False
        self._silence_started_at = None
        self._accepting_audio = True

        if session_kind == "hands_free":
            self._log(
                "hands-free silence detection unavailable for backend="
                f"{active_audio_backend()}; using Esc/max-duration only"
            )

        # Max-duration safety timer.
        self._max_timer = threading.Timer(
            config.MAX_DURATION, self._handle_timeout
        )
        self._max_timer.daemon = True
        self._max_timer.start()

        self._log(
            "recording started "
            f"(started_at={self._started_at}, sample_rate={config.SAMPLE_RATE}, "
            f"max_duration={config.MAX_DURATION}s, session_kind={session_kind})"
        )

    def _start_pyobjc(self, session_kind: str = "hold") -> None:
        """Begin capturing audio through AVFoundation-backed AVAudioRecorder."""
        self._cancel_idle_timer()
        self._cancel_meter_timer()
        with self._stream_lock:
            if self._pyobjc_recorder is not None and self._started_at is not None:
                return
            current_device = _default_input_device_id_pyobjc()
            fd, path_str = tempfile.mkstemp(
                prefix="voicepaste-recording-",
                suffix=".wav",
            )
            os.close(fd)
            path = Path(path_str)
            recorder = _create_pyobjc_recorder(path)
            self._pyobjc_recorder = recorder
            self._pyobjc_recording_path = path
            self._stream_device_id = current_device

        self._chunks = []
        self._started_at = datetime.now()
        self._last_chunk_at = None
        self._callback_count = 0
        self._pending_stop_result = None
        self._speech_detected = False
        self._silence_started_at = None
        self._accepting_audio = True

        started = self._pyobjc_recorder.record()
        if not started:
            with self._stream_lock:
                recorder = self._pyobjc_recorder
                path = self._pyobjc_recording_path
                self._pyobjc_recorder = None
                self._pyobjc_recording_path = None
                self._stream_device_id = None
            if recorder is not None:
                try:
                    recorder.stop()
                except Exception:
                    pass
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
            self._accepting_audio = False
            self._started_at = None
            raise RuntimeError(
                "AVAudioRecorder failed to start. "
                "Check microphone permission for the host app."
            )

        self._max_timer = threading.Timer(
            config.MAX_DURATION,
            self._handle_timeout,
        )
        self._max_timer.daemon = True
        self._max_timer.start()

        if session_kind == "hands_free":
            self._enable_hands_free_metering(self._pyobjc_recorder)

        self._log(
            "recording started "
            f"(backend=pyobjc, started_at={self._started_at}, "
            f"sample_rate={config.SAMPLE_RATE}, max_duration={config.MAX_DURATION}s, "
            f"session_kind={session_kind})"
        )

    def enable_hands_free_mode(self) -> bool:
        """Convert an active recording session into hands-free mode."""
        if not self._accepting_audio or self._started_at is None:
            self._log("hands-free conversion ignored because no recording is active")
            return False
        if self._session_kind == "hands_free":
            self._log("hands-free conversion ignored because session is already hands-free")
            return True

        self._session_kind = "hands_free"
        with self._recording_lock:
            self._speech_detected = False
            self._silence_started_at = None

        if active_audio_backend() == "pyobjc":
            with self._stream_lock:
                recorder = self._pyobjc_recorder
            if recorder is None:
                self._log(
                    "hands-free conversion failed because the PyObjC recorder is unavailable"
                )
                return False
            self._enable_hands_free_metering(recorder)
        else:
            self._log(
                "hands-free conversion enabled without silence detection "
                f"(backend={active_audio_backend()})"
            )

        self._log("recording session converted to hands-free mode")
        return True

    def stop(self, reason: str = "manual") -> RecordingResult:
        """Stop capturing audio and return the recorded chunks.

        Does NOT tear down the stream — starts the idle timer instead.
        Nearly instantaneous.
        """
        if active_audio_backend() == "pyobjc":
            return self._stop_pyobjc(reason=reason)
        stopped_at = datetime.now()
        self._cancel_meter_timer()

        # Gate closes — callback stops collecting immediately.
        self._accepting_audio = False

        # Snapshot and clear recording state under lock (not held by callback).
        with self._recording_lock:
            chunks = self._chunks
            started_at = self._started_at
            last_chunk_at = self._last_chunk_at
            callback_count = self._callback_count
            previous_stop_reason = self._last_stop_reason
            was_recording = started_at is not None
            self._chunks = []
            self._started_at = None
            self._last_chunk_at = None
            self._callback_count = 0
            self._speech_detected = False
            self._silence_started_at = None

        # Cancel max-duration timer.
        if self._max_timer is not None:
            self._max_timer.cancel()
            self._max_timer = None

        # Start idle countdown — stream stays open for quick re-use.
        self._start_idle_timer()

        self._log(
            "stop requested "
            f"(reason={reason}, previous_stop_reason={previous_stop_reason}, "
            f"callback_count={callback_count}, last_chunk_at={last_chunk_at})"
        )

        if not was_recording:
            if self._pending_stop_result is not None:
                pending_result = self._pending_stop_result
                self._pending_stop_result = None
                self._log(
                    "stop() returning cached auto-stop result "
                    f"(requested_reason={reason}, cached_stop_reason={pending_result.stop_reason}, "
                    f"duration={pending_result.duration_seconds:.2f}s, "
                    f"samples={pending_result.audio.size})"
                )
                return pending_result
            self._log(
                "stop() found no active recording "
                f"(requested_reason={reason}, "
                f"previous_stop_reason={previous_stop_reason})"
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

        # Concatenate captured audio.
        if chunks:
            audio = np.concatenate(chunks, axis=0).flatten()
        else:
            audio = np.zeros(0, dtype=np.float32)

        duration_seconds = audio.size / config.SAMPLE_RATE
        if duration_seconds == 0.0 and started_at is not None:
            duration_seconds = (stopped_at - started_at).total_seconds()

        last_chunk_age: Optional[float] = None
        if last_chunk_at is not None:
            last_chunk_age = (stopped_at - last_chunk_at).total_seconds()

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

        self._last_stop_reason = reason

        self._log(
            "recording stopped "
            f"(reason={reason}, duration={duration_seconds:.2f}s, "
            f"chunks={len(chunks)}, callbacks={callback_count}, "
            f"samples={audio.size}, last_chunk_age={last_chunk_age})"
        )
        return result

    def _stop_pyobjc(self, reason: str = "manual") -> RecordingResult:
        """Stop AVFoundation recording and return the recorded waveform."""
        stopped_at = datetime.now()
        self._cancel_meter_timer()
        self._accepting_audio = False

        with self._recording_lock:
            started_at = self._started_at
            previous_stop_reason = self._last_stop_reason
            was_recording = started_at is not None
            self._chunks = []
            self._started_at = None
            self._last_chunk_at = None
            self._callback_count = 0
            self._speech_detected = False
            self._silence_started_at = None

        with self._stream_lock:
            recorder = self._pyobjc_recorder
            path = self._pyobjc_recording_path
            self._pyobjc_recorder = None
            self._pyobjc_recording_path = None
            self._stream_device_id = None

        if self._max_timer is not None:
            self._max_timer.cancel()
            self._max_timer = None

        self._log(
            "stop requested "
            f"(backend=pyobjc, reason={reason}, previous_stop_reason={previous_stop_reason})"
        )

        if not was_recording or recorder is None or path is None:
            if self._pending_stop_result is not None:
                pending_result = self._pending_stop_result
                self._pending_stop_result = None
                self._log(
                    "stop() returning cached auto-stop result "
                    f"(backend=pyobjc, requested_reason={reason}, "
                    f"cached_stop_reason={pending_result.stop_reason}, "
                    f"duration={pending_result.duration_seconds:.2f}s, "
                    f"samples={pending_result.audio.size})"
                )
                return pending_result
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

        try:
            recorder.stop()
        except Exception as exc:
            self._log(f"AVAudioRecorder.stop() raised {type(exc).__name__}: {exc}")

        for _ in range(10):
            if path.exists() and path.stat().st_size > 44:
                break
            _sleep_native(0.05)

        if path.exists():
            try:
                audio = _read_wav_file(path)
            finally:
                path.unlink(missing_ok=True)
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
            chunk_count=1 if audio.size else 0,
            duration_seconds=duration_seconds,
            previous_stop_reason=previous_stop_reason,
        )

        self._last_stop_reason = reason

        self._log(
            "recording stopped "
            f"(backend=pyobjc, reason={reason}, duration={duration_seconds:.2f}s, "
            f"chunks={result.chunk_count}, samples={audio.size})"
        )
        return result

    def _handle_timeout(self) -> None:
        """Auto-stop recording when the max-duration timer fires."""
        self._log(f"max-duration timer fired at {config.MAX_DURATION}s")
        result = self.stop(reason="max_duration")
        if result.was_recording:
            self._pending_stop_result = result
            self._log(
                "auto-stop completed "
                f"(duration={result.duration_seconds:.2f}s, "
                f"chunks={result.chunk_count}, samples={result.audio.size})"
            )
            if self._on_auto_stop is not None:
                try:
                    self._on_auto_stop("max_duration")
                except Exception as exc:
                    self._log(
                        "auto-stop callback failed: "
                        f"{type(exc).__name__}: {exc}"
                    )

    def _handle_silence_timeout(self) -> None:
        """Auto-stop hands-free recording when post-speech silence is too long."""
        self._log(
            "hands-free silence timeout fired "
            f"after {config.HANDS_FREE_SILENCE_SECONDS:.1f}s"
        )
        result = self.stop(reason="silence_timeout")
        if result.was_recording:
            self._pending_stop_result = result
            self._log(
                "auto-stop completed "
                f"(reason=silence_timeout, duration={result.duration_seconds:.2f}s, "
                f"chunks={result.chunk_count}, samples={result.audio.size})"
            )
            if self._on_auto_stop is not None:
                try:
                    self._on_auto_stop("silence_timeout")
                except Exception as exc:
                    self._log(
                        "auto-stop callback failed: "
                        f"{type(exc).__name__}: {exc}"
                    )

    def close(self) -> None:
        """Permanently close the stream.  Called during app shutdown."""
        if active_audio_backend() == "pyobjc":
            self._close_pyobjc()
            return
        self._cancel_idle_timer()
        self._cancel_meter_timer()
        self._accepting_audio = False
        if self._max_timer is not None:
            self._max_timer.cancel()
            self._max_timer = None
        with self._stream_lock:
            if self._stream is not None:
                self._teardown_stream_locked(reason="shutdown")
        # Bounded wait — don't hang forever on exit.
        self._teardown_done.wait(timeout=config.STREAM_TEARDOWN_WAIT_SECONDS)
        self._log("recorder closed (shutdown)")

    def _close_pyobjc(self) -> None:
        """Release the AVFoundation recorder and any temporary recording file."""
        self._cancel_idle_timer()
        self._cancel_meter_timer()
        self._accepting_audio = False
        if self._max_timer is not None:
            self._max_timer.cancel()
            self._max_timer = None
        with self._stream_lock:
            recorder = self._pyobjc_recorder
            path = self._pyobjc_recording_path
            self._pyobjc_recorder = None
            self._pyobjc_recording_path = None
            self._stream_device_id = None
        if recorder is not None:
            try:
                recorder.stop()
            except Exception:
                pass
        if path is not None:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
        self._log("recorder closed (shutdown)")
