import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatsStrip } from "@/components/dashboard/stats-strip";
import type { DashboardStats } from "@/lib/api-client";

const baseStats: DashboardStats = {
  totalTranscripts: 12345,
  completedTranscripts: 10000,
  successRate: 81.0,
  averageDurationSeconds: 125,
};

describe("StatsStrip", () => {
  it("renders three stat cards with their labels", () => {
    render(<StatsStrip loading={false} stats={baseStats} />);
    expect(screen.getByText("Total transcripts")).toBeInTheDocument();
    expect(screen.getByText("Average duration")).toBeInTheDocument();
    expect(screen.getByText("Success rate")).toBeInTheDocument();
  });

  it("formats the total count with locale separators", () => {
    render(<StatsStrip loading={false} stats={baseStats} />);
    expect(
      screen.getByText((12345).toLocaleString()),
    ).toBeInTheDocument();
  });

  it("formats average duration as Xm YYs", () => {
    render(<StatsStrip loading={false} stats={baseStats} />);
    expect(screen.getByText("2m 05s")).toBeInTheDocument();
  });

  it("formats success rate to one decimal", () => {
    render(<StatsStrip loading={false} stats={baseStats} />);
    expect(screen.getByText("81.0%")).toBeInTheDocument();
  });

  it("shows the completed/total detail line", () => {
    render(<StatsStrip loading={false} stats={baseStats} />);
    expect(screen.getByText("10000/12345 completed")).toBeInTheDocument();
  });

  it("shows ellipsis placeholders while loading", () => {
    render(<StatsStrip loading={true} stats={baseStats} />);
    expect(screen.getAllByText("...")).toHaveLength(3);
  });

  it("renders zero-state correctly when no transcripts exist", () => {
    render(
      <StatsStrip
        loading={false}
        stats={{
          totalTranscripts: 0,
          completedTranscripts: 0,
          successRate: 0,
          averageDurationSeconds: 0,
        }}
      />,
    );

    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("0m 00s")).toBeInTheDocument();
    expect(screen.getByText("0.0%")).toBeInTheDocument();
    expect(screen.getByText("0/0 completed")).toBeInTheDocument();
  });
});
