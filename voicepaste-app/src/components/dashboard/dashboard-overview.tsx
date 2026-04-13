import { LiveStatusPanel } from "@/components/dashboard/live-status-panel";
import { StatsStrip } from "@/components/dashboard/stats-strip";
import { TranscriptHistory } from "@/components/dashboard/transcript-history";
import { ScreenHeader } from "@/components/layout/screen-header";

export function DashboardOverview() {
  return (
    <>
      <ScreenHeader
        eyebrow="Dashboard"
        title="Transcript history, ready to work from."
        description="Review the latest captures, retry edge cases, and keep the home view focused on live status and recent transcript output."
      />
      <LiveStatusPanel />
      <StatsStrip />
      <TranscriptHistory />
    </>
  );
}
