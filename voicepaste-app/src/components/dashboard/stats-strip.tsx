"use client";

import { type DashboardStats } from "@/lib/api-client";
import { formatLongDuration } from "@/lib/format";

type StatsStripProps = {
  loading: boolean;
  stats: DashboardStats;
};

export function StatsStrip({ loading, stats }: StatsStripProps) {
  const cards = [
    {
      label: "Total transcripts",
      value: loading ? "..." : stats.totalTranscripts.toLocaleString(),
      detail: "Stored locally",
    },
    {
      label: "Average duration",
      value: loading ? "..." : formatLongDuration(stats.averageDurationSeconds),
      detail: "Completed sessions",
    },
    {
      label: "Success rate",
      value: loading ? "..." : `${stats.successRate.toFixed(1)}%`,
      detail: `${stats.completedTranscripts}/${stats.totalTranscripts} completed`,
    },
  ];

  return (
    <section className="grid gap-3 md:grid-cols-3">
      {cards.map((stat) => (
        <article key={stat.label} className="fig-panel px-5 py-4">
          <p className="fig-mono-label text-[11px] text-soft">{stat.label}</p>
          <p className="mt-3 text-[1.78rem] font-semibold leading-none tracking-[-0.08em] text-black lg:text-[1.92rem]">
            {stat.value}
          </p>
          <p className="mt-2 text-sm tracking-[-0.12px] text-muted">{stat.detail}</p>
        </article>
      ))}
    </section>
  );
}
