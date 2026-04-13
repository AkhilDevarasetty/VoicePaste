import { voiceShortcuts } from "@/lib/dashboard-data";

const tabs = ["All", "Personal", "Shared with team"] as const;

export function ShortcutList() {
  return (
    <section className="soft-card rounded-[30px]">
      <div className="border-b border-[var(--border-soft)] px-5 py-5 lg:px-6">
        <div className="flex flex-wrap items-center gap-6">
          {tabs.map((tab, index) => (
            <button
              key={tab}
              className={`relative pb-3 text-sm font-medium transition ${
                index === 0
                  ? "text-[var(--foreground)]"
                  : "text-[var(--text-muted)] hover:text-[var(--foreground)]"
              }`}
              type="button"
            >
              {tab}
              {index === 0 ? (
                <span className="absolute inset-x-0 bottom-0 h-[2px] rounded-full bg-[var(--foreground)]" />
              ) : null}
            </button>
          ))}
        </div>
      </div>

      <div className="divide-y divide-[var(--border-soft)]">
        {voiceShortcuts.map((shortcut) => (
          <article
            key={shortcut.id}
            className="flex flex-col gap-3 px-5 py-4 lg:flex-row lg:items-center lg:justify-between lg:px-6"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-[var(--foreground)]">
                {shortcut.trigger}
                <span className="mx-2 text-[var(--text-soft)]">→</span>
                <span className="font-normal text-[var(--text-muted)]">{shortcut.output}</span>
              </p>
            </div>
            <span className="w-fit rounded-full bg-[rgba(221,232,238,0.72)] px-3 py-1 text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--accent)]">
              {shortcut.visibility}
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}
