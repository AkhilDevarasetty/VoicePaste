import { AppLogo } from "@/components/ui/app-logo";
import { GridIcon, ListIcon, MicrophoneIcon, SettingsIcon, SparkIcon } from "@/components/ui/icons";
import { dashboardNavItems } from "@/lib/dashboard-data";

export function AppSidebar() {
  return (
    <aside className="surface-muted hidden w-[280px] shrink-0 flex-col justify-between p-5 lg:flex">
      <div className="space-y-8">
        <AppLogo />
        <nav className="space-y-2">
          {dashboardNavItems.map((item) => {
            const icon =
              item.icon === "dashboard" ? (
                <GridIcon />
              ) : item.icon === "transcripts" ? (
                <ListIcon />
              ) : item.icon === "recording" ? (
                <MicrophoneIcon />
              ) : item.icon === "automation" ? (
                <SparkIcon />
              ) : (
                <SettingsIcon />
              );

            return (
              <div
                key={item.label}
                className={`flex items-center gap-3 rounded-2xl px-4 py-3.5 transition ${
                  item.active
                    ? "bg-white text-[var(--foreground)] shadow-[0_8px_24px_rgba(80,102,115,0.08)]"
                    : "text-[var(--text-muted)] hover:bg-white/70 hover:text-[var(--foreground)]"
                }`}
              >
                <span
                  className={`flex h-10 w-10 items-center justify-center rounded-2xl ${
                    item.active ? "bg-[rgba(79,105,121,0.12)] text-[var(--accent)]" : "bg-white/65"
                  }`}
                >
                  {icon}
                </span>
                <div className="space-y-0.5">
                  <p className="text-sm font-medium">{item.label}</p>
                  <p className="text-xs text-[var(--text-soft)]">{item.description}</p>
                </div>
              </div>
            );
          })}
        </nav>
      </div>

      <div className="space-y-4">
        <div className="soft-card rounded-[28px] p-5">
          <div className="mb-4 inline-flex rounded-full bg-[rgba(234,224,204,0.65)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-[var(--warning)]">
            Pro Trial
          </div>
          <h2 className="text-xl font-semibold tracking-tight">Voice workflows, without friction.</h2>
          <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
            Unlock transcript search, automation history, and longer recording sessions when you are ready.
          </p>
          <button
            className="mt-5 inline-flex items-center justify-center rounded-2xl bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-white transition hover:brightness-105"
            type="button"
          >
            Explore Pro
          </button>
        </div>
        <p className="px-1 text-xs uppercase tracking-[0.16em] text-[var(--text-soft)]">
          VoicePaste dashboard v1
        </p>
      </div>
    </aside>
  );
}
