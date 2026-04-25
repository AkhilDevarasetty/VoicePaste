import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/server", () => ({
  NextResponse: {
    json: (body: unknown, init?: { status?: number }) => ({
      status: init?.status ?? 200,
      headers: { "Content-Type": "application/json" },
      async json() {
        return body;
      },
    }),
  },
}));

import { EXPECTED_SCHEMA_VERSION } from "@/lib/db";
import { GET, POST } from "@/app/api/settings/route";

import {
  cleanupTempDir,
  initSchema,
  makeTempDbDir,
  readSetting,
  seedSetting,
} from "../helpers/db-helpers";

const ORIGINAL_DB_DIR = process.env.VOICEPASTE_DB_DIR;

function jsonRequest(body: unknown) {
  return new Request("http://localhost/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("GET /api/settings", () => {
  let dbDir: string;

  beforeEach(() => {
    dbDir = makeTempDbDir();
    process.env.VOICEPASTE_DB_DIR = dbDir;
  });

  afterEach(() => {
    cleanupTempDir(dbDir);
    if (ORIGINAL_DB_DIR === undefined) {
      delete process.env.VOICEPASTE_DB_DIR;
    } else {
      process.env.VOICEPASTE_DB_DIR = ORIGINAL_DB_DIR;
    }
  });

  it("returns 503 when the database file does not exist", async () => {
    const response = await GET();
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      error: "VoicePaste database is not available yet.",
    });
  });

  it("returns the seeded readability_mode value", async () => {
    initSchema(dbDir);
    seedSetting(dbDir, "readability_mode", "openai");

    const response = await GET();
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ readabilityMode: "openai" });
  });

  it("returns the off readability mode when seeded with off", async () => {
    initSchema(dbDir);
    seedSetting(dbDir, "readability_mode", "off");

    const response = await GET();
    expect(await response.json()).toEqual({ readabilityMode: "off" });
  });

  it("returns 500 when readability_mode setting is missing", async () => {
    initSchema(dbDir);
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    const response = await GET();
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({
      error: "readability_mode is missing from settings.",
    });
    consoleError.mockRestore();
  });

  it("returns 500 when readability_mode setting has an invalid value", async () => {
    initSchema(dbDir);
    seedSetting(dbDir, "readability_mode", "garbage");

    const response = await GET();
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({
      error: "readability_mode is missing from settings.",
    });
  });

  it("returns 500 when schema is incompatible", async () => {
    initSchema(dbDir, EXPECTED_SCHEMA_VERSION + 97);
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    const response = await GET();
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({
      error: "Unable to load settings from SQLite.",
    });
    consoleError.mockRestore();
  });
});

describe("POST /api/settings", () => {
  let dbDir: string;

  beforeEach(() => {
    dbDir = makeTempDbDir();
    process.env.VOICEPASTE_DB_DIR = dbDir;
  });

  afterEach(() => {
    cleanupTempDir(dbDir);
    if (ORIGINAL_DB_DIR === undefined) {
      delete process.env.VOICEPASTE_DB_DIR;
    } else {
      process.env.VOICEPASTE_DB_DIR = ORIGINAL_DB_DIR;
    }
  });

  it("returns 503 when the database file does not exist", async () => {
    const response = await POST(jsonRequest({ readabilityMode: "off" }));
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      error: "VoicePaste database is not available yet.",
    });
  });

  it("returns 400 when readabilityMode is missing", async () => {
    initSchema(dbDir);
    const response = await POST(jsonRequest({}));
    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      error: "readabilityMode must be either 'off' or 'openai'.",
    });
  });

  it("returns 400 when readabilityMode is an invalid value", async () => {
    initSchema(dbDir);
    const response = await POST(jsonRequest({ readabilityMode: "fancy" }));
    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      error: "readabilityMode must be either 'off' or 'openai'.",
    });
  });

  it("inserts the readability_mode value when no row exists yet", async () => {
    initSchema(dbDir);

    const response = await POST(jsonRequest({ readabilityMode: "openai" }));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ readabilityMode: "openai" });
    expect(readSetting(dbDir, "readability_mode")).toBe("openai");
  });

  it("updates the readability_mode value when a row exists already", async () => {
    initSchema(dbDir);
    seedSetting(dbDir, "readability_mode", "off");

    const response = await POST(jsonRequest({ readabilityMode: "openai" }));
    expect(response.status).toBe(200);
    expect(readSetting(dbDir, "readability_mode")).toBe("openai");
  });

  it("accepts the off value as a valid mode", async () => {
    initSchema(dbDir);
    seedSetting(dbDir, "readability_mode", "openai");

    const response = await POST(jsonRequest({ readabilityMode: "off" }));
    expect(response.status).toBe(200);
    expect(readSetting(dbDir, "readability_mode")).toBe("off");
  });

  it("returns 500 when the schema is incompatible", async () => {
    initSchema(dbDir, EXPECTED_SCHEMA_VERSION - 1);
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    const response = await POST(jsonRequest({ readabilityMode: "off" }));
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({
      error: "Unable to update SQLite settings.",
    });
    consoleError.mockRestore();
  });
});
