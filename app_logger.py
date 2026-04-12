"""Persistent session logging for VoicePaste."""

from __future__ import annotations

import threading
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import config


@dataclass(frozen=True)
class LogSession:
    """Metadata describing the current log file on disk."""

    started_at: datetime
    log_path: Path


def _log_directory(project_root: Path) -> Path:
    """Return the directory where VoicePaste stores session logs."""
    return project_root / config.LOG_DIRECTORY_NAME


def _log_filename(started_at: datetime) -> str:
    """Build the session log filename from the configured prefix and timestamp."""
    return (
        f"{config.LOG_FILE_PREFIX}-"
        f"{started_at.strftime(config.LOG_FILE_TIME_FORMAT)}"
        f"{config.LOG_FILE_EXTENSION}"
    )


def _log_glob_pattern() -> str:
    """Return the glob pattern used to enumerate VoicePaste log files."""
    return f"{config.LOG_FILE_PREFIX}-*{config.LOG_FILE_EXTENSION}"


class SessionLogger:
    """Write VoicePaste session logs to both stdout and a persistent file."""

    def __init__(self, project_root: Path) -> None:
        """Create a session log file inside the configured log directory."""
        started_at = datetime.now()
        self._directory = _log_directory(project_root)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._session = LogSession(
            started_at=started_at,
            log_path=self._directory / _log_filename(started_at),
        )
        self._lock = threading.Lock()
        self._append("INFO", f"Session started at {started_at.isoformat(timespec='seconds')}")
        removed_count = self._cleanup_old_logs()
        if removed_count > 0:
            self._append(
                "INFO",
                f"Removed {removed_count} old log file(s) based on retention policy",
            )

    @property
    def log_path(self) -> Path:
        """Return the absolute path to the active session log file."""
        return self._session.log_path

    def debug(
        self,
        message: str,
        *,
        sensitive: bool = False,
        summary: str | None = None,
    ) -> None:
        """Print and persist a timestamped debug line."""
        self._write("DEBUG", message, sensitive=sensitive, summary=summary, debug_echo=True)

    def info(
        self,
        message: str,
        *,
        sensitive: bool = False,
        summary: str | None = None,
    ) -> None:
        """Print and persist a user-facing informational message."""
        self._write("INFO", message, sensitive=sensitive, summary=summary)

    def warning(
        self,
        message: str,
        *,
        sensitive: bool = False,
        summary: str | None = None,
    ) -> None:
        """Print and persist a warning message."""
        self._write("WARNING", message, sensitive=sensitive, summary=summary)

    def error(
        self,
        message: str,
        *,
        sensitive: bool = False,
        summary: str | None = None,
    ) -> None:
        """Print and persist an error message."""
        self._write("ERROR", message, sensitive=sensitive, summary=summary)

    def exception(
        self,
        message: str,
        exc: BaseException,
        *,
        sensitive: bool = False,
        summary: str | None = None,
    ) -> None:
        """Print an exception summary and persist the traceback to the log file."""
        console_message = f"{message}: {exc}"
        self._write("ERROR", console_message, sensitive=sensitive, summary=summary)
        if not config.LOG_TRACEBACKS:
            return
        traceback_text = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ).rstrip()
        if traceback_text:
            self._append("ERROR", traceback_text)

    def transcript(self, text: str) -> None:
        """Print the transcript while redacting it from the log file by default."""
        chars = len(text)
        words = len(text.split())
        self.info(
            f"\U0001f4dd {text}",
            sensitive=True,
            summary=f"\U0001f4dd transcript ready (chars={chars}, words={words})",
        )

    def _timestamp(self) -> str:
        """Return the configured timestamp string truncated to milliseconds."""
        return datetime.now().strftime(config.LOG_TIME_FORMAT)[:-3]

    def _cleanup_old_logs(self) -> int:
        """Delete old log files according to the configured retention policy."""
        removed_count = 0
        cutoff = self._session.started_at - timedelta(days=config.LOG_RETENTION_DAYS)
        log_paths = sorted(
            self._directory.glob(_log_glob_pattern()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        kept_paths: list[Path] = []
        for path in log_paths:
            if path == self._session.log_path:
                kept_paths.append(path)
                continue
            try:
                modified_at = datetime.fromtimestamp(path.stat().st_mtime)
            except OSError:
                kept_paths.append(path)
                continue
            if modified_at < cutoff:
                try:
                    path.unlink()
                    removed_count += 1
                except OSError:
                    kept_paths.append(path)
                continue
            kept_paths.append(path)
        if config.LOG_MAX_FILES <= 0:
            return removed_count
        for path in kept_paths[config.LOG_MAX_FILES :]:
            if path == self._session.log_path:
                continue
            try:
                path.unlink()
                removed_count += 1
            except OSError:
                continue
        return removed_count

    def _write(
        self,
        level: str,
        message: str,
        *,
        sensitive: bool = False,
        summary: str | None = None,
        debug_echo: bool = False,
    ) -> None:
        """Print to the terminal and persist the sanitized message to the log file."""
        timestamp = self._timestamp()
        if debug_echo:
            print(f"[{timestamp}] {message}")
        else:
            print(message)
        self._append(
            level,
            self._persisted_message(message, sensitive=sensitive, summary=summary),
            timestamp=timestamp,
        )

    def _persisted_message(
        self,
        message: str,
        *,
        sensitive: bool,
        summary: str | None,
    ) -> str:
        """Return the message variant that should be written to the log file."""
        if not sensitive or config.LOG_SENSITIVE_CONTENT:
            return message
        if summary is not None:
            return summary
        return "[redacted sensitive content]"

    def _append(
        self,
        level: str,
        message: str,
        timestamp: str | None = None,
    ) -> None:
        """Append the provided message to the session log file."""
        log_timestamp = timestamp or self._timestamp()
        lines = message.splitlines() or [""]
        with self._lock:
            with self._session.log_path.open(
                "a",
                encoding=config.LOG_FILE_ENCODING,
            ) as log_file:
                for line in lines:
                    log_file.write(f"[{log_timestamp}] [{level}] {line}\n")
