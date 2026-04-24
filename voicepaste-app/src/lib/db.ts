import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import BetterSqlite3 from "better-sqlite3";

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
