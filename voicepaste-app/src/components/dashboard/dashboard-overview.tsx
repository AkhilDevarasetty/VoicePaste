"use client";

import { StatsStrip } from "@/components/dashboard/stats-strip";
import { TranscriptHistory } from "@/components/dashboard/transcript-history";
import { useDashboardData } from "@/components/dashboard/use-dashboard-data";
import { ScreenHeader } from "@/components/layout/screen-header";

export function DashboardOverview() {
  const { rows, stats, loading, transcriptError } = useDashboardData();

  return (
    <>
      <ScreenHeader
        title="Dashboard"
        description="Review recent captures and track target apps from one operational view."
      />
      <StatsStrip loading={loading} stats={stats} />
      <TranscriptHistory error={transcriptError} loading={loading} rows={rows} />
    </>
  );
}
