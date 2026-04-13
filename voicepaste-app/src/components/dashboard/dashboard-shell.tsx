import { AppSidebar } from "@/components/dashboard/app-sidebar";
import { DashboardHeader } from "@/components/dashboard/dashboard-header";
import { LiveStatusPanel } from "@/components/dashboard/live-status-panel";
import { StatsStrip } from "@/components/dashboard/stats-strip";
import { TranscriptHistory } from "@/components/dashboard/transcript-history";

export function DashboardShell() {
  return (
    <main className="min-h-screen px-5 py-5 text-[var(--foreground)] lg:px-6">
      <div className="glass-panel mx-auto flex min-h-[calc(100vh-2.5rem)] max-w-[1580px] overflow-hidden rounded-[32px]">
        <AppSidebar />
        <div className="flex min-w-0 flex-1 flex-col bg-[linear-gradient(180deg,rgba(255,255,255,0.58),rgba(255,255,255,0.78))]">
          <DashboardHeader />
          <div className="flex flex-1 flex-col gap-6 px-5 pb-6 lg:px-8">
            <LiveStatusPanel />
            <StatsStrip />
            <TranscriptHistory />
          </div>
        </div>
      </div>
    </main>
  );
}
