import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import BetterSqlite3 from "better-sqlite3";

import { EXPECTED_SCHEMA_VERSION } from "@/lib/db";

/**
 * Mirror of the production schema in `db.py`. Kept in lockstep so the
 * integration suite catches drift in CHECK constraints, primary keys, and
 * required columns — not just the column names the API happens to read.
 */
export const PRODUCTION_SCHEMA_SQL = `
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
`;

export type SeedTranscript = {
  id: string;
  created_at: string;
  status: "completed" | "failed" | "paste_failed";
  raw_text?: string | null;
  final_text?: string | null;
  duration_seconds?: number | null;
  transcription_latency_ms?: number | null;
  enhancement_latency_ms?: number | null;
  target_app?: string | null;
  error_message?: string | null;
};

export function makeTempDbDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "voicepaste-it-"));
}

export function cleanupTempDir(dir: string) {
  fs.rmSync(dir, { recursive: true, force: true });
}

/**
 * Initialise the production schema. By default seeds `schema_version` with the
 * version the production code expects. Pass an explicit version to simulate a
 * mismatch, or `null` to leave the table empty.
 */
export function initSchema(
  dir: string,
  schemaVersion: number | null = EXPECTED_SCHEMA_VERSION,
) {
  const dbPath = path.join(dir, "voicepaste.db");
  const db = new BetterSqlite3(dbPath);
  db.exec(PRODUCTION_SCHEMA_SQL);

  if (schemaVersion !== null) {
    db.prepare(
      "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
    ).run(schemaVersion, new Date().toISOString());
  }

  db.close();
  return dbPath;
}

export function seedTranscripts(dir: string, rows: SeedTranscript[]) {
  const dbPath = path.join(dir, "voicepaste.db");
  const db = new BetterSqlite3(dbPath);
  const stmt = db.prepare(
    `INSERT INTO transcripts (
      id, created_at, status,
      raw_text, final_text,
      duration_seconds, transcription_latency_ms,
      enhancement_latency_ms, target_app, error_message
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  );

  const tx = db.transaction((items: SeedTranscript[]) => {
    for (const row of items) {
      stmt.run(
        row.id,
        row.created_at,
        row.status,
        row.raw_text ?? null,
        row.final_text ?? null,
        row.duration_seconds ?? null,
        row.transcription_latency_ms ?? null,
        row.enhancement_latency_ms ?? null,
        row.target_app ?? null,
        row.error_message ?? null,
      );
    }
  });

  tx(rows);
  db.close();
}

export function seedSetting(
  dir: string,
  key: string,
  value: string,
  updatedAt = new Date().toISOString(),
) {
  const dbPath = path.join(dir, "voicepaste.db");
  const db = new BetterSqlite3(dbPath);
  db.prepare(
    `INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
     ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at`,
  ).run(key, value, updatedAt);
  db.close();
}

export function readSetting(dir: string, key: string): string | undefined {
  const dbPath = path.join(dir, "voicepaste.db");
  const db = new BetterSqlite3(dbPath);
  try {
    const row = db
      .prepare("SELECT value FROM settings WHERE key = ?")
      .get(key) as { value?: string } | undefined;
    return row?.value;
  } finally {
    db.close();
  }
}
