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
import { GET } from "@/app/api/transcripts/route";

import {
  cleanupTempDir,
  initSchema,
  makeTempDbDir,
  seedTranscripts,
  type SeedTranscript,
} from "../helpers/db-helpers";

const ORIGINAL_DB_DIR = process.env.VOICEPASTE_DB_DIR;

function makeRequest(qs = "") {
  return new Request(`http://localhost/api/transcripts${qs ? `?${qs}` : ""}`);
}

function transcript(overrides: Partial<SeedTranscript> = {}): SeedTranscript {
  const defaults: SeedTranscript = {
    id: "id-1",
    created_at: "2026-04-24T10:00:00.000Z",
    status: "completed",
    raw_text: "raw",
    final_text: "final",
    duration_seconds: 5,
    transcription_latency_ms: 800,
    enhancement_latency_ms: 0,
    target_app: "Notes",
    error_message: null,
  };
  return { ...defaults, ...overrides };
}

describe("GET /api/transcripts", () => {
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

  it("returns an empty array when the database file does not exist", async () => {
    const response = await GET(makeRequest());
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual([]);
  });

  it("returns rows ordered by created_at DESC and mapped to camelCase", async () => {
    initSchema(dbDir);
    seedTranscripts(dbDir, [
      transcript({ id: "old", created_at: "2026-04-22T10:00:00.000Z" }),
      transcript({ id: "new", created_at: "2026-04-24T10:00:00.000Z" }),
    ]);

    const response = await GET(makeRequest());
    expect(response.status).toBe(200);
    const body = (await response.json()) as Array<{ id: string; createdAt: string }>;

    expect(body.map((row) => row.id)).toEqual(["new", "old"]);
    expect(body[0]).toMatchObject({
      id: "new",
      createdAt: "2026-04-24T10:00:00.000Z",
      status: "completed",
      rawText: "raw",
      finalText: "final",
      durationSeconds: 5,
      transcriptionLatencyMs: 800,
      enhancementLatencyMs: 0,
      targetApp: "Notes",
      errorMessage: null,
    });
  });

  it("respects the limit query param", async () => {
    initSchema(dbDir);
    seedTranscripts(dbDir, [
      transcript({ id: "a", created_at: "2026-04-24T10:00:00.000Z" }),
      transcript({ id: "b", created_at: "2026-04-23T10:00:00.000Z" }),
      transcript({ id: "c", created_at: "2026-04-22T10:00:00.000Z" }),
    ]);

    const response = await GET(makeRequest("limit=2"));
    const body = (await response.json()) as Array<{ id: string }>;
    expect(body.map((row) => row.id)).toEqual(["a", "b"]);
  });

  it("respects the offset query param", async () => {
    initSchema(dbDir);
    seedTranscripts(dbDir, [
      transcript({ id: "a", created_at: "2026-04-24T10:00:00.000Z" }),
      transcript({ id: "b", created_at: "2026-04-23T10:00:00.000Z" }),
      transcript({ id: "c", created_at: "2026-04-22T10:00:00.000Z" }),
    ]);

    const response = await GET(makeRequest("limit=10&offset=1"));
    const body = (await response.json()) as Array<{ id: string }>;
    expect(body.map((row) => row.id)).toEqual(["b", "c"]);
  });

  it("falls back to defaults when limit/offset are non-numeric", async () => {
    initSchema(dbDir);
    seedTranscripts(dbDir, [transcript({ id: "x" })]);

    const response = await GET(makeRequest("limit=abc&offset=def"));
    expect(response.status).toBe(200);
    expect(await response.json()).toHaveLength(1);
  });

  it("clamps limit and offset to their max bounds without error", async () => {
    initSchema(dbDir);
    seedTranscripts(dbDir, [transcript({ id: "x" })]);

    const response = await GET(makeRequest("limit=999999&offset=999999"));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual([]);
  });

  it("clamps negative limit/offset to their min bounds", async () => {
    initSchema(dbDir);
    seedTranscripts(dbDir, [
      transcript({ id: "a", created_at: "2026-04-24T10:00:00.000Z" }),
    ]);

    const response = await GET(makeRequest("limit=-5&offset=-10"));
    expect(response.status).toBe(200);
    const body = (await response.json()) as unknown[];
    expect(body).toHaveLength(1);
  });

  it("returns 500 when schema_version is older than EXPECTED_SCHEMA_VERSION", async () => {
    initSchema(dbDir, EXPECTED_SCHEMA_VERSION - 1);
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    const response = await GET(makeRequest());
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({
      error: "Unable to load transcripts from SQLite.",
    });
    expect(consoleError).toHaveBeenCalled();
  });

  it("rejects seeding a row with an invalid status (CHECK constraint mirrors prod)", () => {
    initSchema(dbDir);
    expect(() =>
      seedTranscripts(dbDir, [
        // @ts-expect-error intentionally bypassing the type to prove the DB rejects it.
        transcript({ id: "bad", status: "in_progress" }),
      ]),
    ).toThrow(/CHECK constraint failed|status/i);
  });

  it("returns rows with null fields when the columns are NULL", async () => {
    initSchema(dbDir);
    seedTranscripts(dbDir, [
      transcript({
        id: "nulls",
        raw_text: null,
        final_text: null,
        duration_seconds: null,
        transcription_latency_ms: null,
        enhancement_latency_ms: null,
        target_app: null,
        error_message: "boom",
        status: "failed",
      }),
    ]);

    const response = await GET(makeRequest());
    const body = (await response.json()) as Array<Record<string, unknown>>;
    expect(body[0]).toMatchObject({
      rawText: null,
      finalText: null,
      durationSeconds: null,
      transcriptionLatencyMs: null,
      enhancementLatencyMs: null,
      targetApp: null,
      errorMessage: "boom",
      status: "failed",
    });
  });
});
