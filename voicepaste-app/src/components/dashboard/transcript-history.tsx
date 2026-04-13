import { CopyIcon, RetryIcon, TrashIcon } from "@/components/ui/icons";
import { StatusBadge } from "@/components/ui/status-badge";
import { transcriptRows } from "@/lib/dashboard-data";

const toneMap = {
  completed: "success",
  transcribing: "accent",
  attention: "warning",
  failed: "danger",
} as const;

export function TranscriptHistory() {
  return (
    <section className="flex min-h-[620px] flex-col border-y border-[var(--border-soft)]">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border-soft)] px-1 py-5 lg:px-0">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--text-soft)]">
            Transcript history
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em]">
            Recent voice events
          </h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-full bg-[rgba(79,105,121,0.1)] px-4 py-2 text-sm font-medium text-[var(--accent)]"
            type="button"
          >
            All
          </button>
          <button
            className="rounded-full bg-[rgba(255,255,255,0.84)] px-4 py-2 text-sm font-medium text-[var(--text-muted)]"
            type="button"
          >
            Completed
          </button>
          <button
            className="rounded-full bg-[rgba(255,255,255,0.84)] px-4 py-2 text-sm font-medium text-[var(--text-muted)]"
            type="button"
          >
            Needs review
          </button>
        </div>
      </div>

      <div className="overflow-x-auto pr-5 lg:pr-6">
        <table className="min-w-full border-separate border-spacing-0">
          <thead>
            <tr className="text-left">
              <th className="px-5 py-4 text-xs font-medium uppercase tracking-[0.16em] text-[var(--text-soft)] lg:px-1">
                Time
              </th>
              <th className="px-5 py-4 text-xs font-medium uppercase tracking-[0.16em] text-[var(--text-soft)]">
                Transcript
              </th>
              <th className="px-5 py-4 text-xs font-medium uppercase tracking-[0.16em] text-[var(--text-soft)]">
                Duration
              </th>
              <th className="px-5 py-4 text-xs font-medium uppercase tracking-[0.16em] text-[var(--text-soft)]">
                Status
              </th>
              <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-[0.16em] text-[var(--text-soft)] lg:px-1">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {transcriptRows.map((row, index) => (
              <tr
                key={row.id}
                className={index % 2 === 0 ? "bg-white/56" : "bg-[rgba(246,247,245,0.72)]"}
              >
                <td className="border-t border-[var(--border-soft)] px-5 py-5 align-top lg:px-1">
                  <div className="space-y-1">
                    <p className="text-sm font-medium">{row.time}</p>
                    <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-soft)]">
                      {row.date}
                    </p>
                  </div>
                </td>
                <td className="border-t border-[var(--border-soft)] px-5 py-5 align-top">
                  <div className="space-y-2">
                    <p className="max-w-3xl text-[15px] leading-7 text-[var(--foreground)]">
                      {row.preview}
                    </p>
                    <p className="text-sm text-[var(--text-muted)]">{row.context}</p>
                  </div>
                </td>
                <td className="border-t border-[var(--border-soft)] px-5 py-5 align-top text-sm text-[var(--text-muted)]">
                  {row.duration}
                </td>
                <td className="border-t border-[var(--border-soft)] px-5 py-5 align-top">
                  <StatusBadge label={row.statusLabel} tone={toneMap[row.status]} />
                </td>
                <td className="border-t border-[var(--border-soft)] px-5 py-5 align-top lg:px-1">
                  <div className="flex items-center justify-start gap-2">
                    <RowAction icon={<CopyIcon />} label="Copy" />
                    <RowAction icon={<RetryIcon />} label="Retry" />
                    <RowAction icon={<TrashIcon />} label="Delete" destructive={row.status === "failed"} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

type RowActionProps = {
  destructive?: boolean;
  icon: React.ReactNode;
  label: string;
};

function RowAction({ destructive = false, icon, label }: RowActionProps) {
  return (
    <button
      aria-label={label}
      className={`inline-flex h-10 w-10 items-center justify-center rounded-2xl border transition ${
        destructive
          ? "border-[rgba(160,87,85,0.18)] bg-[rgba(246,228,225,0.78)] text-[var(--danger)] hover:bg-[rgba(246,228,225,0.95)]"
          : "border-[var(--border-soft)] bg-white/78 text-[var(--text-muted)] hover:border-[var(--border-strong)] hover:bg-white hover:text-[var(--foreground)]"
      }`}
      type="button"
    >
      {icon}
    </button>
  );
}
