"""Microphone capture through AVFoundation via PyObjC."""

import os
import tempfile
import threading
import time
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

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

import config


def describe_default_input_device() -> str:
    """Return a human-readable summary of the current default input device."""
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
    """Return a stable identifier for the current default microphone."""
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
    """Open AVFoundation briefly to trigger permissions and validate input."""
    current_device = _default_input_device_id()
    fd, path_str = tempfile.mkstemp(prefix="voicepaste-pyobjc-probe-", suffix=".wav")
    os.close(fd)
    path = Path(path_str)
    recorder = None
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
        _cleanup_recording_artifacts(recorder, path)


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
            "AVFoundation/CoreAudio PyObjC bindings are not installed."
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


def _cleanup_recording_artifacts(recorder: object, path: Optional[Path]) -> None:
    """Best-effort cleanup for a recorder instance and its temporary WAV file."""
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


def _sleep_native(seconds: float) -> None:
    """Wait while letting Foundation-backed APIs process queued work."""
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
    """Capture mono float32 audio through AVFoundation-backed AVAudioRecorder."""

    def __init__(
        self,
        logger: Optional[Callable[[str], None]] = None,
        on_auto_stop: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialize a recorder with no active recording."""
        self._logger = logger
        self._on_auto_stop = on_auto_stop
        self._stream_lock = threading.Lock()
        self._recording_lock = threading.Lock()
        self._pyobjc_recorder = None
        self._pyobjc_recording_path: Optional[Path] = None
        self._stream_device_id: Optional[tuple] = None
        self._accepting_audio = False
        self._started_at: Optional[datetime] = None
        self._last_stop_reason: Optional[str] = None
        self._pending_stop_result: Optional[RecordingResult] = None
        self._session_kind: str = "hold"
        self._speech_detected: bool = False
        self._silence_started_at: Optional[float] = None
        self._max_timer: Optional[threading.Timer] = None
        self._meter_timer: Optional[threading.Timer] = None
        self._meter_timer_lock = threading.Lock()
        self._metering_enabled: bool = False

    def _log(self, message: str) -> None:
        """Emit a debug log line when a logger callback is available."""
        if self._logger is not None:
            self._logger(f"[recorder] {message}")

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
                f"falling back to max-duration/manual stop only: {type(exc).__name__}: {exc}"
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
            self._log(f"hands-free speech detected (power={power_db:.1f}dB)")
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

    def start(self, session_kind: str = "hold") -> None:
        """Begin capturing audio. Idempotent if already recording."""
        self._start_pyobjc(session_kind=session_kind)

    def _start_pyobjc(self, session_kind: str = "hold") -> None:
        """Begin capturing audio through AVFoundation-backed AVAudioRecorder."""
        self._cancel_meter_timer()
        with self._recording_lock:
            if self._started_at is not None:
                return
            self._pending_stop_result = None
            self._session_kind = session_kind
            self._speech_detected = False
            self._silence_started_at = None

        current_device = _default_input_device_id()
        fd, path_str = tempfile.mkstemp(prefix="voicepaste-recording-", suffix=".wav")
        os.close(fd)
        path = Path(path_str)
        recorder = None
        started = False
        try:
            recorder = _create_pyobjc_recorder(path)
            try:
                started = recorder.record()
            except Exception as exc:
                raise RuntimeError(
                    "AVAudioRecorder.record() raised unexpectedly. "
                    "Check microphone permission for the host app."
                ) from exc
            if not started:
                raise RuntimeError(
                    "AVAudioRecorder failed to start. "
                    "Check microphone permission for the host app."
                )
            started_at = datetime.now()
            with self._stream_lock:
                self._pyobjc_recorder = recorder
                self._pyobjc_recording_path = path
                self._stream_device_id = current_device
            with self._recording_lock:
                self._started_at = started_at
                self._accepting_audio = True
            self._max_timer = threading.Timer(config.MAX_DURATION, self._handle_timeout)
            self._max_timer.daemon = True
            self._max_timer.start()
        except Exception:
            if self._max_timer is not None:
                self._max_timer.cancel()
                self._max_timer = None
            with self._stream_lock:
                self._pyobjc_recorder = None
                self._pyobjc_recording_path = None
                self._stream_device_id = None
            with self._recording_lock:
                self._accepting_audio = False
                self._started_at = None
                self._session_kind = "hold"
                self._speech_detected = False
                self._silence_started_at = None
            _cleanup_recording_artifacts(recorder, path)
            raise

        if session_kind == "hands_free":
            self._enable_hands_free_metering(recorder)

        self._log(
            "recording started "
            f"(backend=pyobjc, started_at={started_at}, "
            f"sample_rate={config.SAMPLE_RATE}, max_duration={config.MAX_DURATION}s, "
            f"session_kind={session_kind})"
        )

    def enable_hands_free_mode(self) -> bool:
        """Convert an active recording session into hands-free mode."""
        with self._recording_lock:
            if not self._accepting_audio or self._started_at is None:
                self._log("hands-free conversion ignored because no recording is active")
                return False
            if self._session_kind == "hands_free":
                self._log("hands-free conversion ignored because session is already hands-free")
                return True
            self._session_kind = "hands_free"
            self._speech_detected = False
            self._silence_started_at = None

        with self._stream_lock:
            recorder = self._pyobjc_recorder
        if recorder is None:
            self._log(
                "hands-free conversion failed because the PyObjC recorder is unavailable"
            )
            return False

        self._enable_hands_free_metering(recorder)
        self._log("recording session converted to hands-free mode")
        return True

    def stop(self, reason: str = "manual") -> RecordingResult:
        """Stop AVFoundation recording and return the recorded waveform."""
        stopped_at = datetime.now()
        self._cancel_meter_timer()
        with self._recording_lock:
            started_at = self._started_at
            previous_stop_reason = self._last_stop_reason
            was_recording = started_at is not None
            self._accepting_audio = False
            self._started_at = None
            self._session_kind = "hold"
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
            with self._recording_lock:
                pending_result = self._pending_stop_result
                self._pending_stop_result = None
            if pending_result is not None:
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
                _cleanup_recording_artifacts(None, path)
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

        with self._recording_lock:
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
            with self._recording_lock:
                self._pending_stop_result = result
            self._log(
                "auto-stop completed "
                f"(reason=max_duration, duration={result.duration_seconds:.2f}s, "
                f"chunks={result.chunk_count}, samples={result.audio.size})"
            )
            self._notify_auto_stop("max_duration")

    def _handle_silence_timeout(self) -> None:
        """Auto-stop hands-free recording when post-speech silence is too long."""
        self._log(
            "hands-free silence timeout fired "
            f"after {config.HANDS_FREE_SILENCE_SECONDS:.1f}s"
        )
        result = self.stop(reason="silence_timeout")
        if result.was_recording:
            with self._recording_lock:
                self._pending_stop_result = result
            self._log(
                "auto-stop completed "
                f"(reason=silence_timeout, duration={result.duration_seconds:.2f}s, "
                f"chunks={result.chunk_count}, samples={result.audio.size})"
            )
            self._notify_auto_stop("silence_timeout")

    def _notify_auto_stop(self, reason: str) -> None:
        """Invoke the app-level auto-stop callback."""
        if self._on_auto_stop is None:
            return
        try:
            self._on_auto_stop(reason)
        except Exception as exc:
            self._log(
                "auto-stop callback failed: "
                f"{type(exc).__name__}: {exc}"
            )

    def close(self) -> None:
        """Release the AVFoundation recorder and temporary recording file."""
        self._cancel_meter_timer()
        with self._recording_lock:
            self._accepting_audio = False
            self._started_at = None
            self._session_kind = "hold"
            self._speech_detected = False
            self._silence_started_at = None
        if self._max_timer is not None:
            self._max_timer.cancel()
            self._max_timer = None
        with self._stream_lock:
            recorder = self._pyobjc_recorder
            path = self._pyobjc_recording_path
            self._pyobjc_recorder = None
            self._pyobjc_recording_path = None
            self._stream_device_id = None
        _cleanup_recording_artifacts(recorder, path)
        self._log("recorder closed (shutdown)")
