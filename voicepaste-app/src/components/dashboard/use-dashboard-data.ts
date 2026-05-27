"use client";

import { useEffect, useState } from "react";

import {
  fetchStats,
  fetchTranscripts,
  type DashboardStats,
  type Transcript,
} from "@/lib/api-client";

const EMPTY_STATS: DashboardStats = {
  totalTranscripts: 0,
  completedTranscripts: 0,
  successRate: 0,
  averageDurationSeconds: 0,
};

type DashboardDataState = {
  rows: Transcript[];
  stats: DashboardStats;
  loading: boolean;
  transcriptError: string | null;
};

export function useDashboardData() {
  const [state, setState] = useState<DashboardDataState>({
    rows: [],
    stats: EMPTY_STATS,
    loading: true,
    transcriptError: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadDashboardData() {
      const [transcriptsResult, statsResult] = await Promise.allSettled([
        fetchTranscripts(),
        fetchStats(),
      ]);

      if (cancelled) {
        return;
      }

      setState((previous) => {
        const nextState: DashboardDataState = {
          rows:
            transcriptsResult.status === "fulfilled"
              ? transcriptsResult.value
              : previous.rows,
          stats:
            statsResult.status === "fulfilled" ? statsResult.value : previous.stats,
          loading: false,
          transcriptError:
            transcriptsResult.status === "rejected"
              ? transcriptsResult.reason instanceof Error
                ? transcriptsResult.reason.message
                : "Unable to load transcripts."
              : null,
        };

        if (statsResult.status === "rejected") {
          console.error(
            "Unable to refresh dashboard stats.",
            statsResult.reason,
          );
        }

        return nextState;
      });
    }

    loadDashboardData();
    const intervalId = window.setInterval(loadDashboardData, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  return state;
}
