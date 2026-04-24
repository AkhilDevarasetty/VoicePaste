import { StatsStrip } from "@/components/dashboard/stats-strip";
import { TranscriptHistory } from "@/components/dashboard/transcript-history";
import { ScreenHeader } from "@/components/layout/screen-header";

export function DashboardOverview() {
  return (
    <>
      <ScreenHeader
        title="Dashboard"
        description="Review recent captures and track target apps from one operational view."
      />
      <StatsStrip />
      <TranscriptHistory />
    </>
  );
}
