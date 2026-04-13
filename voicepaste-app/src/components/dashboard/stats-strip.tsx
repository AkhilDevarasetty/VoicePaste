import { dashboardStats } from "@/lib/dashboard-data";

export function StatsStrip() {
  return (
    <section className="grid gap-4 md:grid-cols-3">
      {dashboardStats.map((stat) => (
        <article
          key={stat.label}
          className={`soft-card rounded-[24px] p-5 ${
            stat.tint === "accent"
              ? "bg-[linear-gradient(180deg,rgba(207,230,243,0.68),rgba(255,255,255,0.94))]"
              : stat.tint === "success"
                ? "bg-[linear-gradient(180deg,rgba(228,241,234,0.82),rgba(255,255,255,0.94))]"
                : "bg-[linear-gradient(180deg,rgba(245,235,217,0.82),rgba(255,255,255,0.94))]"
          }`}
        >
          <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-soft)]">{stat.label}</p>
          <div className="mt-4 flex items-end justify-between gap-3">
            <div>
              <p className="text-3xl font-semibold tracking-[-0.04em]">{stat.value}</p>
              <p className="mt-2 text-sm text-[var(--text-muted)]">{stat.detail}</p>
            </div>
            <span
              className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${
                stat.tint === "accent"
                  ? "bg-white/76 text-accent"
                  : stat.tint === "success"
                    ? "bg-white/76 text-success"
                    : "bg-white/76 text-warning"
              }`}
            >
              {stat.change}
            </span>
          </div>
        </article>
      ))}
    </section>
  );
}
