"""SQLite persistence for VoicePaste transcripts and settings."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import config

VALID_SETTINGS: dict[str, set[str]] = {
    "readability_mode": {"off", "openai"},
}
VALID_TRANSCRIPT_STATUSES = ("completed", "failed", "paste_failed")
EXPECTED_SCHEMA_VERSION = 2


@contextmanager
def _connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a short-lived SQLite connection configured for concurrent access."""
    conn = sqlite3.connect(str(db_path), timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Path) -> None:
    """Create the SQLite database, schema, and seeded settings if needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS transcripts (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('completed', 'failed', 'paste_failed')),
                raw_text TEXT,
                final_text TEXT,
                duration_seconds REAL,
                transcription_latency_ms INTEGER,
                enhancement_latency_ms INTEGER,
                target_app TEXT,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_transcripts_created_at
            ON transcripts(created_at DESC);
            """
        )
        _seed_settings(conn)
        _seed_schema_version(conn)


def insert_transcript(db_path: Path, transcript: dict[str, Any]) -> None:
    """Insert one persisted transcript event."""
    status = str(transcript["status"])
    if status not in VALID_TRANSCRIPT_STATUSES:
        raise ValueError(
            f"Invalid transcript status {status!r}. Allowed: {list(VALID_TRANSCRIPT_STATUSES)!r}"
        )

    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO transcripts (
                id,
                created_at,
                status,
                raw_text,
                final_text,
                duration_seconds,
                transcription_latency_ms,
                enhancement_latency_ms,
                target_app,
                error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transcript["id"],
                transcript["created_at"],
                status,
                transcript.get("raw_text"),
                transcript.get("final_text"),
                transcript.get("duration_seconds"),
                transcript.get("transcription_latency_ms"),
                transcript.get("enhancement_latency_ms"),
                transcript.get("target_app"),
                transcript.get("error_message"),
            ),
        )
        conn.commit()


def get_transcripts(db_path: Path, limit: int, offset: int) -> list[dict[str, Any]]:
    """Return paginated transcript history ordered newest first."""
    safe_limit = max(1, min(limit, 500))
    safe_offset = max(0, offset)
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                created_at,
                status,
                raw_text,
                final_text,
                duration_seconds,
                transcription_latency_ms,
                enhancement_latency_ms,
                target_app,
                error_message
            FROM transcripts
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (safe_limit, safe_offset),
        ).fetchall()
    return [dict(row) for row in rows]


def get_setting(db_path: Path, key: str, default: str) -> str:
    """Return one setting value or the provided default when missing."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
        ).fetchone()
    if row is None:
        return default
    return str(row["value"])


def set_setting(db_path: Path, key: str, value: str) -> None:
    """Validate and persist one setting value."""
    allowed = VALID_SETTINGS.get(key)
    if allowed is not None and value not in allowed:
        raise ValueError(f"Invalid value {value!r} for {key!r}. Allowed: {sorted(allowed)!r}")

    now = _utcnow_iso()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, now),
        )
        conn.commit()


def _seed_settings(conn: sqlite3.Connection) -> None:
    """Seed default mutable settings from config.py on first run only."""
    row = conn.execute("SELECT COUNT(*) AS count FROM settings").fetchone()
    if int(row["count"]) > 0:
        return

    now = _utcnow_iso()
    conn.execute(
        "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        ("readability_mode", config.READABILITY_MODE, now),
    )
    conn.commit()


def _seed_schema_version(conn: sqlite3.Connection) -> None:
    """Seed the current schema version on first init."""
    row = conn.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()
    if row["version"] is not None:
        return
    conn.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
        (EXPECTED_SCHEMA_VERSION, _utcnow_iso()),
    )
    conn.commit()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
