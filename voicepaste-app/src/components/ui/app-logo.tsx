export function AppLogo() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-11 items-center gap-1 border border-[var(--border-soft)] bg-white/72 px-3">
        {[20, 28, 36, 24, 32].map((height, index) => (
          <span
            key={height}
            className="w-[4px] rounded-full bg-[var(--accent)]/90"
            style={{ height, opacity: 0.72 + index * 0.05 }}
          />
        ))}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-2xl font-semibold tracking-tight text-[var(--foreground)]">
          VoicePaste
        </span>
        <span className="shrink-0 border border-[var(--border-strong)] bg-white/85 px-2.5 py-1 text-xs font-medium uppercase tracking-[0.12em] text-[var(--text-muted)]">
          Beta
        </span>
      </div>
    </div>
  );
}
