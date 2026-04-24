"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { CopyIcon, RetryIcon, TrashIcon } from "@/components/ui/icons";
import { StatusBadge } from "@/components/ui/status-badge";
import { fetchTranscripts, type Transcript } from "@/lib/api-client";

const toneMap = {
  completed: { label: "Completed", tone: "success" as const },
  failed: { label: "Failed", tone: "danger" as const },
  paste_failed: { label: "Paste failed", tone: "warning" as const },
};

export function TranscriptHistory() {
  const [rows, setRows] = useState<Transcript[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadTranscripts() {
      try {
        const nextRows = await fetchTranscripts();
        if (!cancelled) {
          setRows(nextRows);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setRows([]);
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load transcripts.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadTranscripts();
    const intervalId = window.setInterval(loadTranscripts, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  return (
    <section className="fig-panel overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-black/10 px-6 py-5 lg:px-8">
        <div>
          <p className="fig-mono-label text-[11px] text-soft">Transcript history</p>
          <h2 className="fig-display mt-3 text-[2.15rem] leading-[1.02] tracking-[-0.06em] text-black">
            Recent voice events
          </h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="fig-pill bg-black px-4 py-2.5 text-[15px] font-medium tracking-[-0.14px] text-white" type="button">
            All
          </button>
          <button className="fig-pill border border-black/10 bg-white px-4 py-2.5 text-[15px] font-medium tracking-[-0.14px] text-black" disabled type="button">
            Completed
          </button>
          <button className="fig-pill border border-black/10 bg-white px-4 py-2.5 text-[15px] font-medium tracking-[-0.14px] text-black" disabled type="button">
            Failed
          </button>
        </div>
      </div>

      <div className="desktop-scroll max-h-[46vh] overflow-auto pr-1 pb-5 lg:max-h-[54vh]">
        <table className="min-w-full border-separate border-spacing-0">
          <thead>
            <tr className="text-left">
              <th className="fig-mono-label sticky top-0 z-10 border-b border-black/10 bg-white px-6 py-4 text-[11px] text-soft lg:px-8">
                Time
              </th>
              <th className="fig-mono-label sticky top-0 z-10 border-b border-black/10 bg-white px-6 py-4 text-[11px] text-soft">
                Transcript
              </th>
              <th className="fig-mono-label sticky top-0 z-10 border-b border-black/10 bg-white px-6 py-4 text-[11px] text-soft">
                Duration
              </th>
              <th className="fig-mono-label sticky top-0 z-10 border-b border-black/10 bg-white px-6 py-4 text-[11px] text-soft">
                Status
              </th>
              <th className="fig-mono-label sticky top-0 z-10 border-b border-black/10 bg-white px-6 py-4 text-[11px] text-soft lg:px-8">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? <LoadingRows /> : null}
            {!loading && error ? <ErrorRow message={error} /> : null}
            {!loading && !error && rows.length === 0 ? <EmptyRow /> : null}
            {!loading && !error
              ? rows.map((row) => <TranscriptRow key={row.id} row={row} />)
              : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TranscriptRow({ row }: { row: Transcript }) {
  const createdAt = new Date(row.createdAt);
  const preview = row.finalText ?? row.rawText ?? "Transcript unavailable.";
  const meta = toneMap[row.status];

  return (
    <tr className="bg-white">
      <td className="border-b border-black/8 px-6 py-6 align-top lg:px-8">
        <div className="space-y-1">
          <p className="text-[15px] font-medium tracking-[-0.14px] text-black">{formatTime(createdAt)}</p>
          <p className="fig-mono-label text-[10px] text-soft">{formatDayLabel(createdAt)}</p>
        </div>
      </td>
      <td className="border-b border-black/8 px-6 py-6 align-top">
        <div className="space-y-2">
          <p className="max-w-3xl text-[16px] leading-[1.45] tracking-[-0.14px] text-black">
            {preview}
          </p>
          <p className="text-sm leading-[1.45] tracking-[-0.12px] text-muted">{buildContextLine(row)}</p>
        </div>
      </td>
      <td className="border-b border-black/8 px-6 py-6 align-top text-sm tracking-[-0.12px] text-muted">
        {formatDuration(row.durationSeconds)}
      </td>
      <td className="border-b border-black/8 px-6 py-6 align-top">
        <StatusBadge label={meta.label} tone={meta.tone} />
      </td>
      <td className="border-b border-black/8 px-6 py-6 align-top lg:px-8">
        <div className="flex items-center gap-2">
          <RowAction icon={<CopyIcon />} label="Copy" />
          <RowAction icon={<RetryIcon />} label="Retry" />
          <RowAction icon={<TrashIcon />} label="Delete" />
        </div>
      </td>
    </tr>
  );
}

function LoadingRows() {
  return Array.from({ length: 4 }, (_, index) => (
    <tr key={`loading-${index}`} className="bg-white">
      <td className="border-b border-black/8 px-6 py-6 align-top lg:px-8">
        <div className="h-16 w-20 animate-pulse rounded-md bg-black/6" />
      </td>
      <td className="border-b border-black/8 px-6 py-6 align-top">
        <div className="space-y-3">
          <div className="h-5 w-full max-w-3xl animate-pulse rounded-full bg-black/6" />
          <div className="h-4 w-64 animate-pulse rounded-full bg-black/6" />
        </div>
      </td>
      <td className="border-b border-black/8 px-6 py-6 align-top">
        <div className="h-5 w-16 animate-pulse rounded-full bg-black/6" />
      </td>
      <td className="border-b border-black/8 px-6 py-6 align-top">
        <div className="h-8 w-32 animate-pulse rounded-full bg-black/6" />
      </td>
      <td className="border-b border-black/8 px-6 py-6 align-top lg:px-8">
        <div className="flex gap-2">
          <div className="h-10 w-10 animate-pulse rounded-full bg-black/6" />
          <div className="h-10 w-10 animate-pulse rounded-full bg-black/6" />
          <div className="h-10 w-10 animate-pulse rounded-full bg-black/6" />
        </div>
      </td>
    </tr>
  ));
}

function EmptyRow() {
  return (
    <tr>
      <td className="px-6 py-16 text-center text-sm tracking-[-0.12px] text-muted" colSpan={5}>
        No transcriptions yet. Hold Right Option to record.
      </td>
    </tr>
  );
}

function ErrorRow({ message }: { message: string }) {
  return (
    <tr>
      <td className="px-6 py-16 text-center text-sm tracking-[-0.12px] text-black" colSpan={5}>
        {message}
      </td>
    </tr>
  );
}

type RowActionProps = {
  icon: ReactNode;
  label: string;
};

function RowAction({ icon, label }: RowActionProps) {
  return (
    <button
      aria-label={`${label} (coming later)`}
      className="fig-circle inline-flex h-10 w-10 cursor-not-allowed items-center justify-center border border-black/10 bg-white text-black opacity-60"
      disabled
      type="button"
    >
      {icon}
    </button>
  );
}

function buildContextLine(row: Transcript) {
  if (row.status === "completed") {
    if (row.targetApp) {
      return `Target app: ${row.targetApp}`;
    }
    return "Completed and stored locally.";
  }

  if (row.status === "paste_failed") {
    return row.errorMessage
      ? `Paste failed: ${row.errorMessage}`
      : "Paste failed after transcription.";
  }

  return row.errorMessage
    ? `Processing failed: ${row.errorMessage}`
    : "Transcript could not be completed.";
}

function formatDuration(durationSeconds: number | null) {
  if (durationSeconds === null || Number.isNaN(durationSeconds)) {
    return "—";
  }

  const safeSeconds = Math.max(0, Math.round(durationSeconds));
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;

  return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
}

function formatTime(date: Date) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function formatDayLabel(date: Date) {
  const now = new Date();
  if (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  ) {
    return "Today";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(date);
}
