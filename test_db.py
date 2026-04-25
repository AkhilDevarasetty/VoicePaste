from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

import config
import db


def test_init_creates_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "voicepaste.db"

    db.init_db(db_path)

    with db._connect(db_path) as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {"transcripts", "settings", "schema_version"}.issubset(tables)


def test_init_seeds_settings(tmp_path: Path) -> None:
    db_path = tmp_path / "voicepaste.db"

    db.init_db(db_path)

    assert db.get_setting(db_path, "readability_mode", "missing") == config.READABILITY_MODE


def test_init_seeds_schema_version(tmp_path: Path) -> None:
    db_path = tmp_path / "voicepaste.db"

    db.init_db(db_path)

    with db._connect(db_path) as conn:
        row = conn.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()

    assert row["version"] == db.EXPECTED_SCHEMA_VERSION


def test_insert_and_read_transcript(tmp_path: Path) -> None:
    db_path = tmp_path / "voicepaste.db"
    db.init_db(db_path)
    transcript = _transcript(status="completed")

    db.insert_transcript(db_path, transcript)

    rows = db.get_transcripts(db_path, limit=10, offset=0)
    assert len(rows) == 1
    assert rows[0]["id"] == transcript["id"]
    assert rows[0]["final_text"] == transcript["final_text"]
    assert rows[0]["target_app"] == transcript["target_app"]


def test_settings_read_write(tmp_path: Path) -> None:
    db_path = tmp_path / "voicepaste.db"
    db.init_db(db_path)

    db.set_setting(db_path, "readability_mode", "off")

    assert db.get_setting(db_path, "readability_mode", "missing") == "off"


def test_settings_validation_rejects_invalid(tmp_path: Path) -> None:
    db_path = tmp_path / "voicepaste.db"
    db.init_db(db_path)

    with pytest.raises(ValueError):
        db.set_setting(db_path, "readability_mode", "invalid")


def test_insert_transcript_rejects_invalid_status(tmp_path: Path) -> None:
    db_path = tmp_path / "voicepaste.db"
    db.init_db(db_path)

    with pytest.raises(ValueError):
        db.insert_transcript(db_path, _transcript(status="invalid"))


def test_concurrent_access(tmp_path: Path) -> None:
    db_path = tmp_path / "voicepaste.db"
    db.init_db(db_path)
    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def worker(index: int) -> None:
        try:
            barrier.wait()
            db.insert_transcript(
                db_path,
                _transcript(
                    status="completed",
                    duration=5.0 + index,
                    final_text=f"Transcript {index}",
                ),
            )
        except Exception as exc:  # pragma: no cover - failure capture path
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(db.get_transcripts(db_path, limit=10, offset=0)) == 2


def _transcript(
    *,
    status: str,
    duration: float | None = 12.5,
    final_text: str = "Final transcript",
) -> dict[str, object]:
    return {
        "id": uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "raw_text": "Raw transcript",
        "final_text": final_text,
        "duration_seconds": duration,
        "transcription_latency_ms": 850,
        "enhancement_latency_ms": 0,
        "target_app": "Notes",
        "error_message": None if status == "completed" else "Something failed",
    }
