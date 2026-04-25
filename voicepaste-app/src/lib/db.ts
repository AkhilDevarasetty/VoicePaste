import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import BetterSqlite3 from "better-sqlite3";

export const EXPECTED_SCHEMA_VERSION = 2;

export function resolveVoicePasteDbPath() {
  const dbDirectory =
    process.env.VOICEPASTE_DB_DIR ??
    path.join(os.homedir(), "Library", "Application Support", "VoicePaste");

  return path.join(dbDirectory, "voicepaste.db");
}

export function databaseExists() {
  return fs.existsSync(resolveVoicePasteDbPath());
}

export function openVoicePasteDatabase(
  options?: BetterSqlite3.Options,
) {
  return new BetterSqlite3(resolveVoicePasteDbPath(), options);
}

export function assertSchemaCompatible(db: BetterSqlite3.Database) {
  const row = db
    .prepare("SELECT MAX(version) AS version FROM schema_version")
    .get() as { version?: number } | undefined;

  const version = Number(row?.version ?? 0);
  if (version !== EXPECTED_SCHEMA_VERSION) {
    throw new Error(
      `VoicePaste database schema mismatch. Expected v${EXPECTED_SCHEMA_VERSION}, found v${version}.`,
    );
  }
}
