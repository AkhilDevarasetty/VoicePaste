import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchSettings,
  fetchStats,
  fetchTranscripts,
  updateSettings,
} from "@/lib/api-client";

type MockResponseInit = {
  ok?: boolean;
  status?: number;
  json?: unknown;
  jsonError?: Error;
};

function mockResponse({ ok = true, status = 200, json, jsonError }: MockResponseInit) {
  return {
    ok,
    status,
    json: vi.fn(async () => {
      if (jsonError) {
        throw jsonError;
      }
      return json;
    }),
  };
}

describe("api-client", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  describe("fetchTranscripts", () => {
    it("uses default limit/offset and no-store cache", async () => {
      fetchMock.mockResolvedValueOnce(mockResponse({ json: [] }));

      const rows = await fetchTranscripts();

      expect(rows).toEqual([]);
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/transcripts?limit=50&offset=0",
        { cache: "no-store" },
      );
    });

    it("forwards custom pagination parameters", async () => {
      fetchMock.mockResolvedValueOnce(mockResponse({ json: [] }));

      await fetchTranscripts(20, 100);

      expect(fetchMock).toHaveBeenCalledWith(
        "/api/transcripts?limit=20&offset=100",
        { cache: "no-store" },
      );
    });

    it("returns parsed JSON for a successful response", async () => {
      const payload = [
        {
          id: "abc",
          createdAt: "2026-01-01T00:00:00Z",
          status: "completed",
          rawText: "raw",
          finalText: "final",
          durationSeconds: 5,
          transcriptionLatencyMs: 100,
          enhancementLatencyMs: 0,
          targetApp: "Notes",
          errorMessage: null,
        },
      ];
      fetchMock.mockResolvedValueOnce(mockResponse({ json: payload }));

      await expect(fetchTranscripts()).resolves.toEqual(payload);
    });

    it("throws server-provided error message on non-ok response", async () => {
      fetchMock.mockResolvedValueOnce(
        mockResponse({ ok: false, status: 500, json: { error: "boom" } }),
      );

      await expect(fetchTranscripts()).rejects.toThrow("boom");
    });

    it("falls back to default error message when body is not JSON", async () => {
      fetchMock.mockResolvedValueOnce(
        mockResponse({
          ok: false,
          status: 500,
          jsonError: new Error("not json"),
        }),
      );

      await expect(fetchTranscripts()).rejects.toThrow(
        "Failed to load transcripts.",
      );
    });

    it("falls back to default message when error body has no error field", async () => {
      fetchMock.mockResolvedValueOnce(
        mockResponse({ ok: false, status: 500, json: { message: "nope" } }),
      );

      await expect(fetchTranscripts()).rejects.toThrow(
        "Failed to load transcripts.",
      );
    });

    it("propagates network failures", async () => {
      fetchMock.mockRejectedValueOnce(new Error("offline"));
      await expect(fetchTranscripts()).rejects.toThrow("offline");
    });
  });

  describe("fetchStats", () => {
    it("returns parsed dashboard stats", async () => {
      const payload = {
        totalTranscripts: 4,
        completedTranscripts: 3,
        successRate: 75,
        averageDurationSeconds: 12.5,
      };
      fetchMock.mockResolvedValueOnce(mockResponse({ json: payload }));

      await expect(fetchStats()).resolves.toEqual(payload);
      expect(fetchMock).toHaveBeenCalledWith("/api/stats", { cache: "no-store" });
    });

    it("throws default message on non-ok with empty body", async () => {
      fetchMock.mockResolvedValueOnce(
        mockResponse({ ok: false, status: 500, json: {} }),
      );
      await expect(fetchStats()).rejects.toThrow(
        "Failed to load dashboard stats.",
      );
    });
  });

  describe("fetchSettings", () => {
    it("returns settings JSON for a 200 response", async () => {
      fetchMock.mockResolvedValueOnce(
        mockResponse({ json: { readabilityMode: "openai" } }),
      );

      await expect(fetchSettings()).resolves.toEqual({
        readabilityMode: "openai",
      });
      expect(fetchMock).toHaveBeenCalledWith("/api/settings", {
        cache: "no-store",
      });
    });

    it("throws server error message when database is unavailable", async () => {
      fetchMock.mockResolvedValueOnce(
        mockResponse({
          ok: false,
          status: 503,
          json: { error: "VoicePaste database is not available yet." },
        }),
      );

      await expect(fetchSettings()).rejects.toThrow(
        "VoicePaste database is not available yet.",
      );
    });
  });

  describe("updateSettings", () => {
    it("POSTs JSON body and returns parsed response", async () => {
      fetchMock.mockResolvedValueOnce(
        mockResponse({ json: { readabilityMode: "openai" } }),
      );

      const result = await updateSettings({ readabilityMode: "openai" });

      expect(result).toEqual({ readabilityMode: "openai" });
      expect(fetchMock).toHaveBeenCalledWith("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ readabilityMode: "openai" }),
      });
    });

    it("throws on validation error from server", async () => {
      fetchMock.mockResolvedValueOnce(
        mockResponse({
          ok: false,
          status: 400,
          json: { error: "readabilityMode must be either 'off' or 'openai'." },
        }),
      );

      await expect(
        // @ts-expect-error testing invalid input is intentional
        updateSettings({ readabilityMode: "bogus" }),
      ).rejects.toThrow(/'off' or 'openai'/);
    });

    it("falls back to default error message when body is malformed", async () => {
      fetchMock.mockResolvedValueOnce(
        mockResponse({
          ok: false,
          status: 500,
          jsonError: new Error("malformed"),
        }),
      );

      await expect(
        updateSettings({ readabilityMode: "off" }),
      ).rejects.toThrow("Failed to update settings.");
    });
  });
});
