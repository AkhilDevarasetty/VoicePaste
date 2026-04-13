import { SparkIcon } from "@/components/ui/icons";
import { StatusBadge } from "@/components/ui/status-badge";

export function LiveStatusPanel() {
  return (
    <section className="border-y border-[var(--border-soft)] py-6">
      <div className="grid gap-6 lg:grid-cols-[1.45fr_0.75fr]">
        <div className="relative overflow-hidden border border-[var(--border-soft)] bg-[linear-gradient(135deg,rgba(88,110,124,0.95),rgba(109,132,146,0.9)_38%,rgba(229,220,201,0.92)_100%)] p-6 text-white">
          <div className="absolute inset-y-0 right-0 w-1/2 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.2),transparent_54%)]" />
          <div className="relative z-10 max-w-xl">
            <StatusBadge label="System Idle" tone="accent" />
            <h2 className="mt-4 text-2xl font-semibold tracking-[-0.03em] lg:text-[2rem]">
              The voice workspace is ready when you are.
            </h2>
            <p className="mt-3 max-w-lg text-sm leading-6 text-white/82 lg:text-base">
              Keep capturing from the menu bar while this dashboard becomes your clean review surface for transcripts, retries, and reusable shortcuts.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                className="inline-flex items-center justify-center rounded-2xl bg-white px-4 py-3 text-sm font-semibold text-[var(--accent)] transition hover:bg-white/90"
                type="button"
              >
                Start New Recording
              </button>
              <button
                className="inline-flex items-center gap-2 rounded-2xl border border-white/22 bg-white/10 px-4 py-3 text-sm font-medium text-white/92 transition hover:bg-white/16"
                type="button"
              >
                <SparkIcon className="h-4 w-4" />
                Review recent changes
              </button>
            </div>
          </div>
        </div>

        <div className="border border-[var(--border-soft)] bg-[rgba(244,247,248,0.76)] p-5 lg:p-6">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--text-soft)]">
            Live Signal
          </p>
          <div className="mt-4 flex items-center gap-3">
            <span className="relative inline-flex h-3 w-3 rounded-full bg-[var(--success)]">
              <span className="absolute inset-0 rounded-full bg-[var(--success)] opacity-35 blur-[3px]" />
            </span>
            <p className="text-lg font-semibold">Ready for next capture</p>
          </div>
          <div className="mt-6 grid gap-3">
            <div className="border border-[var(--border-soft)] bg-white/78 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-soft)]">Current mode</p>
              <p className="mt-1 font-medium">Idle</p>
            </div>
            <div className="border border-[var(--border-soft)] bg-white/78 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-soft)]">Last activity</p>
              <p className="mt-1 font-medium">Transcript completed 42 seconds ago</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
