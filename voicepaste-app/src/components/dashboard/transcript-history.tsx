"use client";

import { useEffect, useRef, useState } from "react";

import { CheckIcon, CopyIcon } from "@/components/ui/icons";
import { StatusBadge } from "@/components/ui/status-badge";
import { type Transcript } from "@/lib/api-client";
import { formatShortDuration } from "@/lib/format";

const toneMap = {
  completed: { label: "Completed", tone: "success" as const },
  failed: { label: "Failed", tone: "danger" as const },
  paste_failed: { label: "Paste failed", tone: "warning" as const },
};

type TranscriptFilter = "all" | "completed" | "failed";

type TranscriptHistoryProps = {
  error: string | null;
  loading: boolean;
  rows: Transcript[];
};

export function TranscriptHistory({
  error,
  loading,
  rows,
}: TranscriptHistoryProps) {
  const [filter, setFilter] = useState<TranscriptFilter>("all");

  const visibleRows =
    filter === "all"
      ? rows
      : rows.filter((row) =>
          filter === "completed"
            ? row.status === "completed"
            : row.status === "failed" || row.status === "paste_failed",
        );

  return (
    <section className="fig-panel overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-black/10 px-6 py-4 lg:px-8">
        <div>
          <p className="fig-mono-label text-[11px] text-soft">Transcript history</p>
          <h2 className="fig-display mt-2.5 text-[1.9rem] leading-[1.02] tracking-[-0.06em] text-black lg:text-[2rem]">
            Recent voice events
          </h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <FilterPill
            active={filter === "all"}
            label="All"
            onClick={() => setFilter("all")}
          />
          <FilterPill
            active={filter === "completed"}
            label="Completed"
            onClick={() => setFilter("completed")}
          />
          <FilterPill
            active={filter === "failed"}
            label="Failed"
            onClick={() => setFilter("failed")}
          />
        </div>
      </div>

      {error && rows.length > 0 ? (
        <div className="border-b border-black/8 px-6 py-3 text-sm tracking-[-0.12px] text-muted lg:px-8">
          {error}
        </div>
      ) : null}

      <div className="desktop-scroll max-h-[48vh] overflow-auto pr-1 lg:max-h-[56vh]">
        <div className="min-w-full pb-10">
          <table className="min-w-full border-separate border-spacing-0">
            <thead>
              <tr className="text-left">
                <th className="fig-mono-label sticky top-0 z-10 border-b border-black/10 bg-white px-6 py-3.5 text-[11px] text-soft lg:px-8">
                  Time
                </th>
                <th className="fig-mono-label sticky top-0 z-10 border-b border-black/10 bg-white px-6 py-3.5 text-[11px] text-soft">
                  Transcript
                </th>
                <th className="fig-mono-label sticky top-0 z-10 border-b border-black/10 bg-white px-6 py-3.5 text-[11px] text-soft">
                  Duration
                </th>
                <th className="fig-mono-label sticky top-0 z-10 border-b border-black/10 bg-white px-6 py-3.5 text-[11px] text-soft">
                  Status
                </th>
                <th className="fig-mono-label sticky top-0 z-10 border-b border-black/10 bg-white px-6 py-3.5 text-[11px] text-soft lg:px-8">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? <LoadingRows /> : null}
              {!loading && error && rows.length === 0 ? <ErrorRow message={error} /> : null}
              {!loading && visibleRows.length === 0 && !(error && rows.length === 0) ? (
                <EmptyRow filter={filter} />
              ) : null}
              {!loading && visibleRows.length > 0
                ? visibleRows.map((row) => <TranscriptRow key={row.id} row={row} />)
                : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function FilterPill({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className={`fig-pill px-4 py-2 text-[15px] font-medium tracking-[-0.14px] ${
        active
          ? "bg-black text-white"
          : "border border-black/10 bg-white text-black"
      }`}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}

function TranscriptRow({ row }: { row: Transcript }) {
  const createdAt = new Date(row.createdAt);
  const preview = row.finalText ?? row.rawText ?? "Transcript unavailable.";
  const copyText = row.finalText?.trim() || row.rawText?.trim() || null;
  const meta = toneMap[row.status];
  const [copied, setCopied] = useState(false);
  const resetTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (resetTimeoutRef.current !== null) {
        window.clearTimeout(resetTimeoutRef.current);
      }
    };
  }, []);

  async function handleCopy() {
    if (!copyText) {
      return;
    }

    try {
      await navigator.clipboard.writeText(copyText);
      setCopied(true);
      if (resetTimeoutRef.current !== null) {
        window.clearTimeout(resetTimeoutRef.current);
      }
      resetTimeoutRef.current = window.setTimeout(() => {
        setCopied(false);
      }, 1600);
    } catch (copyError) {
      console.error("Unable to copy transcript text.", copyError);
    }
  }

  return (
    <tr className="bg-white">
      <td className="border-b border-black/8 px-6 py-5 align-top lg:px-8">
        <div className="space-y-1">
          <p className="text-[15px] font-medium tracking-[-0.14px] text-black">
            {formatTime(createdAt)}
          </p>
          <p className="fig-mono-label text-[10px] text-soft">{formatDayLabel(createdAt)}</p>
        </div>
      </td>
      <td className="border-b border-black/8 px-6 py-5 align-top">
        <div className="space-y-1.5">
          <p
            className="max-w-3xl text-[15px] leading-[1.42] tracking-[-0.14px] text-black lg:text-[16px]"
            title={preview}
          >
            {preview}
          </p>
          <p className="text-sm leading-[1.45] tracking-[-0.12px] text-muted">
            {buildContextLine(row)}
          </p>
        </div>
      </td>
      <td className="border-b border-black/8 px-6 py-5 align-top text-sm tracking-[-0.12px] text-muted">
        {formatShortDuration(row.durationSeconds)}
      </td>
      <td className="border-b border-black/8 px-6 py-5 align-top">
        <StatusBadge label={meta.label} tone={meta.tone} />
      </td>
      <td className="border-b border-black/8 px-6 py-5 align-top lg:px-8">
        <div className="flex flex-col items-start gap-1.5">
          <button
            aria-label={copied ? "Transcript copied" : "Copy transcript"}
            className="fig-circle inline-flex h-10 w-10 items-center justify-center border border-black/10 bg-white text-black transition hover:bg-black/[0.03] disabled:cursor-not-allowed disabled:border-black/6 disabled:text-black/24 disabled:hover:bg-white"
            disabled={!copyText}
            onClick={handleCopy}
            title={
              !copyText
                ? "Transcript text unavailable"
                : copied
                  ? "Copied"
                  : "Copy transcript"
            }
            type="button"
          >
            {copied ? <CheckIcon /> : <CopyIcon />}
          </button>
          <span className="fig-mono-label min-h-[12px] text-[10px] text-soft">
            {copied ? "Copied" : !copyText ? "Unavailable" : ""}
          </span>
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
        <div className="h-10 w-10 animate-pulse rounded-full bg-black/6" />
      </td>
    </tr>
  ));
}

function EmptyRow({ filter }: { filter: TranscriptFilter }) {
  const message =
    filter === "all"
      ? "No transcriptions yet. Hold Right Option to record."
      : filter === "completed"
        ? "No completed transcriptions yet."
        : "No failed transcriptions yet.";

  return (
    <tr>
      <td className="px-6 py-16 text-center text-sm tracking-[-0.12px] text-muted" colSpan={5}>
        {message}
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
