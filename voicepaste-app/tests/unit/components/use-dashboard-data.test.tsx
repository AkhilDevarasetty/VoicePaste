import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useDashboardData } from "@/components/dashboard/use-dashboard-data";
import type { Transcript } from "@/lib/api-client";

function makeTranscript(overrides: Partial<Transcript> = {}): Transcript {
  const defaults: Transcript = {
    id: "id-1",
    createdAt: "2026-04-24T15:00:00Z",
    status: "completed",
    rawText: "raw text",
    finalText: "final text",
    durationSeconds: 12,
    transcriptionLatencyMs: 800,
    enhancementLatencyMs: 200,
    targetApp: "Notes",
    errorMessage: null,
  };
  return { ...defaults, ...overrides };
}

describe("useDashboardData", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  function jsonResponse(payload: unknown, ok = true) {
    return {
      ok,
      status: ok ? 200 : 500,
      json: vi.fn(async () => payload),
    };
  }

  it("starts in loading=true with empty rows and zeroed stats", () => {
    fetchMock.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useDashboardData());
    expect(result.current.loading).toBe(true);
    expect(result.current.rows).toEqual([]);
    expect(result.current.stats.totalTranscripts).toBe(0);
    expect(result.current.transcriptError).toBeNull();
  });

  it("loads full transcript objects and stats on mount", async () => {
    const transcript = makeTranscript({ id: "1", finalText: "hello world" });
    fetchMock.mockImplementation((input: string) => {
      if (input.startsWith("/api/transcripts")) {
        return Promise.resolve(jsonResponse([transcript]));
      }
      return Promise.resolve(
        jsonResponse({
          totalTranscripts: 1,
          completedTranscripts: 1,
          successRate: 100,
          averageDurationSeconds: 4,
        }),
      );
    });

    const { result, unmount } = renderHook(() => useDashboardData());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.rows).toHaveLength(1);
    const [row] = result.current.rows;
    expect(row).toEqual(transcript);
    expect(row.status).toBe("completed");
    expect(row.createdAt).toBe("2026-04-24T15:00:00Z");
    expect(row.finalText).toBe("hello world");
    expect(result.current.stats.totalTranscripts).toBe(1);
    expect(result.current.transcriptError).toBeNull();
    unmount();
  });

  it("captures transcript error message when transcripts fetch fails", async () => {
    fetchMock.mockImplementation((input: string) => {
      if (input.startsWith("/api/transcripts")) {
        return Promise.resolve(jsonResponse({ error: "no db" }, false));
      }
      return Promise.resolve(
        jsonResponse({
          totalTranscripts: 0,
          completedTranscripts: 0,
          successRate: 0,
          averageDurationSeconds: 0,
        }),
      );
    });

    const { result, unmount } = renderHook(() => useDashboardData());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.transcriptError).toBe("no db");
    unmount();
  });

  it("logs but does not surface stats fetch failures", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    fetchMock.mockImplementation((input: string) => {
      if (input.startsWith("/api/transcripts")) {
        return Promise.resolve(jsonResponse([]));
      }
      return Promise.resolve(jsonResponse({ error: "stats down" }, false));
    });

    const { result, unmount } = renderHook(() => useDashboardData());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.transcriptError).toBeNull();
    expect(consoleError).toHaveBeenCalled();
    unmount();
  });

  it("polls every three seconds", async () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    fetchMock.mockResolvedValue(jsonResponse([]));
    const { unmount } = renderHook(() => useDashboardData());

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    fetchMock.mockClear();

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    unmount();
    vi.useRealTimers();
  });

  it("clears the polling interval on unmount", async () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    fetchMock.mockResolvedValue(jsonResponse([]));
    const { unmount } = renderHook(() => useDashboardData());
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    fetchMock.mockClear();

    unmount();
    act(() => {
      vi.advanceTimersByTime(10000);
    });
    expect(fetchMock).not.toHaveBeenCalled();
    vi.useRealTimers();
  });
});
