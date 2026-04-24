import { StatsStrip } from "@/components/dashboard/stats-strip";
import { TranscriptHistory } from "@/components/dashboard/transcript-history";
import { ScreenHeader } from "@/components/layout/screen-header";

export function DashboardOverview() {
  return (
    <>
      <ScreenHeader
        eyebrow="Dashboard"
        title="Recent transcripts, ready to move."
        description="Review completed captures, track target apps, and keep the dashboard focused on fast operational visibility rather than extra chrome."
      />
      <StatsStrip />
      <TranscriptHistory />
    </>
  );
}
