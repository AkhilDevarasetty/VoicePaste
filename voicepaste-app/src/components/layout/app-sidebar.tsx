import Link from "next/link";

import { AppLogo } from "@/components/ui/app-logo";
import { GridIcon, SettingsIcon, SparkIcon } from "@/components/ui/icons";
import { dashboardNavItems } from "@/lib/dashboard-data";

type AppSidebarProps = {
  currentPath: "/" | "/voice-shortcuts" | "/settings";
};

export function AppSidebar({ currentPath }: AppSidebarProps) {
  return (
    <aside className="hidden h-full w-[288px] shrink-0 flex-col overflow-hidden border-r border-[var(--border-soft)] bg-[rgba(243,246,247,0.72)] px-5 py-6 lg:flex">
      <div className="space-y-8">
        <AppLogo />
        <nav className="space-y-2">
          {dashboardNavItems.map((item) => {
            const isActive = item.href === currentPath;
            const icon =
              item.icon === "dashboard" ? (
                <GridIcon />
              ) : item.icon === "shortcuts" ? (
                <SparkIcon />
              ) : (
                <SettingsIcon />
              );

            return (
              <Link
                key={item.label}
                href={item.href}
                className={`flex items-center gap-3 border-l-2 px-4 py-3 transition ${
                  isActive
                    ? "border-[var(--accent)] bg-[rgba(255,255,255,0.68)] text-[var(--foreground)]"
                    : "border-transparent text-[var(--text-muted)] hover:bg-white/50 hover:text-[var(--foreground)]"
                }`}
              >
                <span
                  className={`flex h-10 w-10 items-center justify-center ${
                    isActive ? "bg-[rgba(79,105,121,0.08)] text-[var(--accent)]" : "bg-transparent"
                  }`}
                >
                  {icon}
                </span>
                <div className="space-y-0.5">
                  <p className="text-sm font-medium">{item.label}</p>
                  <p className="text-xs text-[var(--text-soft)]">{item.description}</p>
                </div>
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
