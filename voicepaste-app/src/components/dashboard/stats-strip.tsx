"use client";

import { useEffect, useState } from "react";

import { fetchStats, type DashboardStats } from "@/lib/api-client";

const EMPTY_STATS: DashboardStats = {
  totalTranscripts: 0,
  completedTranscripts: 0,
  successRate: 0,
  averageDurationSeconds: 0,
};

export function StatsStrip() {
  const [stats, setStats] = useState<DashboardStats>(EMPTY_STATS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadStats() {
      try {
        const nextStats = await fetchStats();
        if (!cancelled) {
          setStats(nextStats);
        }
      } catch {
        if (!cancelled) {
          setStats(EMPTY_STATS);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadStats();
    const intervalId = window.setInterval(loadStats, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  const cards = [
    {
      label: "Total transcripts",
      value: loading ? "..." : stats.totalTranscripts.toLocaleString(),
      detail: "Stored locally",
    },
    {
      label: "Average duration",
      value: loading ? "..." : formatDuration(stats.averageDurationSeconds),
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

function formatDuration(seconds: number) {
  const safeSeconds = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(safeSeconds / 60);
  const remainingSeconds = safeSeconds % 60;

  return `${minutes}m ${remainingSeconds.toString().padStart(2, "0")}s`;
}
