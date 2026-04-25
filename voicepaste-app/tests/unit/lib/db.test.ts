import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  assertSchemaCompatible,
  databaseExists,
  EXPECTED_SCHEMA_VERSION,
  openVoicePasteDatabase,
  resolveVoicePasteDbPath,
} from "@/lib/db";

import {
  cleanupTempDir,
  initSchema,
  makeTempDbDir,
} from "../../integration/helpers/db-helpers";

const ORIGINAL_DB_DIR = process.env.VOICEPASTE_DB_DIR;

function restoreDbDir() {
  if (ORIGINAL_DB_DIR === undefined) {
    delete process.env.VOICEPASTE_DB_DIR;
  } else {
    process.env.VOICEPASTE_DB_DIR = ORIGINAL_DB_DIR;
  }
}

describe("resolveVoicePasteDbPath", () => {
  beforeEach(() => {
    delete process.env.VOICEPASTE_DB_DIR;
  });

  afterEach(restoreDbDir);

  it("uses VOICEPASTE_DB_DIR override when set", () => {
    process.env.VOICEPASTE_DB_DIR = "/tmp/override";
    expect(resolveVoicePasteDbPath()).toBe("/tmp/override/voicepaste.db");
  });

  it("falls back to the macOS Application Support path when env var is unset", () => {
    delete process.env.VOICEPASTE_DB_DIR;
    expect(resolveVoicePasteDbPath()).toBe(
      path.join(
        os.homedir(),
        "Library",
        "Application Support",
        "VoicePaste",
        "voicepaste.db",
      ),
    );
  });
});

describe("databaseExists", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = makeTempDbDir();
    process.env.VOICEPASTE_DB_DIR = tempDir;
  });

  afterEach(() => {
    cleanupTempDir(tempDir);
    restoreDbDir();
  });

  it("returns false when the database file is missing", () => {
    expect(databaseExists()).toBe(false);
  });

  it("returns true after the database file is created", () => {
    initSchema(tempDir);
    expect(fs.existsSync(path.join(tempDir, "voicepaste.db"))).toBe(true);
    expect(databaseExists()).toBe(true);
  });
});

describe("openVoicePasteDatabase", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = makeTempDbDir();
    process.env.VOICEPASTE_DB_DIR = tempDir;
    initSchema(tempDir);
  });

  afterEach(() => {
    cleanupTempDir(tempDir);
    restoreDbDir();
  });

  it("opens the resolved database with the given options", () => {
    const db = openVoicePasteDatabase({ readonly: true, fileMustExist: true });
    try {
      expect(db.readonly).toBe(true);
    } finally {
      db.close();
    }
  });
});

describe("assertSchemaCompatible", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = makeTempDbDir();
    process.env.VOICEPASTE_DB_DIR = tempDir;
  });

  afterEach(() => {
    cleanupTempDir(tempDir);
    restoreDbDir();
  });

  it("succeeds when schema_version equals the production EXPECTED_SCHEMA_VERSION", () => {
    initSchema(tempDir, EXPECTED_SCHEMA_VERSION);
    const db = openVoicePasteDatabase({ readonly: true, fileMustExist: true });
    try {
      expect(() => assertSchemaCompatible(db)).not.toThrow();
    } finally {
      db.close();
    }
  });

  it("throws when schema_version is older than expected", () => {
    initSchema(tempDir, EXPECTED_SCHEMA_VERSION - 1);
    const db = openVoicePasteDatabase({ readonly: true, fileMustExist: true });
    try {
      expect(() => assertSchemaCompatible(db)).toThrow(
        new RegExp(`v${EXPECTED_SCHEMA_VERSION}.*v${EXPECTED_SCHEMA_VERSION - 1}`),
      );
    } finally {
      db.close();
    }
  });

  it("throws when schema_version table is empty", () => {
    initSchema(tempDir, null);
    const db = openVoicePasteDatabase({ readonly: true, fileMustExist: true });
    try {
      expect(() => assertSchemaCompatible(db)).toThrow(
        new RegExp(`v${EXPECTED_SCHEMA_VERSION}.*v0`),
      );
    } finally {
      db.close();
    }
  });
});
