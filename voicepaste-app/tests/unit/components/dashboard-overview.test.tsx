import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardOverview } from "@/components/dashboard/dashboard-overview";

describe("DashboardOverview", () => {
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

  it("renders the header, stats strip, and history together", async () => {
    fetchMock.mockImplementation((input: string) => {
      if (input.startsWith("/api/transcripts")) {
        return Promise.resolve(jsonResponse([]));
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

    render(<DashboardOverview />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Recent voice events" }),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText("Total transcripts")).toBeInTheDocument(),
    );
  });
});
