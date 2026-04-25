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
import { GET } from "@/app/api/stats/route";

import {
  cleanupTempDir,
  initSchema,
  makeTempDbDir,
  seedTranscripts,
} from "../helpers/db-helpers";

const ORIGINAL_DB_DIR = process.env.VOICEPASTE_DB_DIR;

describe("GET /api/stats", () => {
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

  it("returns zeroed stats when the database file does not exist", async () => {
    const response = await GET();
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      totalTranscripts: 0,
      completedTranscripts: 0,
      successRate: 0,
      averageDurationSeconds: 0,
    });
  });

  it("returns zeroed stats when the database is empty", async () => {
    initSchema(dbDir);
    const response = await GET();
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      totalTranscripts: 0,
      completedTranscripts: 0,
      successRate: 0,
      averageDurationSeconds: 0,
    });
  });

  it("computes total/completed/success rate and average duration", async () => {
    initSchema(dbDir);
    seedTranscripts(dbDir, [
      {
        id: "a",
        created_at: "2026-04-24T10:00:00.000Z",
        status: "completed",
        duration_seconds: 10,
      },
      {
        id: "b",
        created_at: "2026-04-24T10:00:01.000Z",
        status: "completed",
        duration_seconds: 20,
      },
      {
        id: "c",
        created_at: "2026-04-24T10:00:02.000Z",
        status: "failed",
        duration_seconds: 30,
        error_message: "boom",
      },
      {
        id: "d",
        created_at: "2026-04-24T10:00:03.000Z",
        status: "paste_failed",
        duration_seconds: 40,
        error_message: "no perms",
      },
    ]);

    const response = await GET();
    const body = (await response.json()) as {
      totalTranscripts: number;
      completedTranscripts: number;
      successRate: number;
      averageDurationSeconds: number;
    };

    expect(body.totalTranscripts).toBe(4);
    expect(body.completedTranscripts).toBe(2);
    expect(body.successRate).toBeCloseTo(50, 5);
    expect(body.averageDurationSeconds).toBeCloseTo(15, 5);
  });

  it("excludes failed/paste_failed durations from the average", async () => {
    initSchema(dbDir);
    seedTranscripts(dbDir, [
      {
        id: "a",
        created_at: "2026-04-24T10:00:00.000Z",
        status: "completed",
        duration_seconds: 8,
      },
      {
        id: "b",
        created_at: "2026-04-24T10:00:01.000Z",
        status: "failed",
        duration_seconds: 1000,
        error_message: "x",
      },
    ]);

    const response = await GET();
    const body = (await response.json()) as { averageDurationSeconds: number };
    expect(body.averageDurationSeconds).toBeCloseTo(8, 5);
  });

  it("returns 500 when schema is older than EXPECTED_SCHEMA_VERSION", async () => {
    initSchema(dbDir, EXPECTED_SCHEMA_VERSION - 1);
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    const response = await GET();
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({
      error: "Unable to load dashboard stats from SQLite.",
    });
    expect(consoleError).toHaveBeenCalled();
  });
});
