import Link from "next/link";

import { AppLogo } from "@/components/ui/app-logo";
import { ChevronRightIcon, GridIcon, SettingsIcon, SparkIcon } from "@/components/ui/icons";
import { dashboardNavItems } from "@/lib/dashboard-data";

type AppSidebarProps = {
  collapsed: boolean;
  currentPath: "/" | "/voice-shortcuts" | "/settings";
  onToggle: () => void;
};

export function AppSidebar({ collapsed, currentPath, onToggle }: AppSidebarProps) {
  return (
    <aside
      className={`relative hidden h-full shrink-0 flex-col overflow-hidden border-r border-black/10 bg-white py-5 transition-[width,padding] duration-200 lg:flex ${
        collapsed ? "w-[116px] px-3" : "w-[332px] px-5"
      }`}
    >
      <div className="relative">
        <div className={collapsed ? "flex justify-center" : "pr-16"}>
          <AppLogo collapsed={collapsed} />
        </div>
        <button
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={`fig-circle absolute inline-flex h-10 w-10 shrink-0 items-center justify-center border border-black bg-white text-black transition hover:bg-black hover:text-white ${
            collapsed ? "top-0 left-1/2 -translate-x-1/2 rotate-180" : "top-0 right-0"
          }`}
          onClick={onToggle}
          type="button"
        >
          <ChevronRightIcon className="h-4 w-4" />
        </button>
      </div>

      <div className={`flex-1 ${collapsed ? "pt-16" : "pt-8"}`}>
        <div className="space-y-4">
          <nav className="space-y-4">
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
                  aria-label={collapsed ? item.label : undefined}
                  className={`fig-pill flex items-center py-3 transition ${
                    isActive
                      ? "bg-black text-white"
                      : "border border-black/10 bg-white text-black hover:bg-black/[0.03] hover:text-black"
                  } ${collapsed ? "justify-center px-2" : "gap-4 px-5"}`}
                  title={collapsed ? item.label : undefined}
                >
                  <span
                    className={`fig-circle flex h-10 w-10 shrink-0 items-center justify-center ${
                      isActive ? "bg-white/16 text-white" : "fig-glass-dark text-black"
                    }`}
                  >
                    {icon}
                  </span>
                  <div className={`${collapsed ? "hidden" : "block min-w-0 space-y-1"}`}>
                    <p
                      className={`text-[15px] leading-none font-medium tracking-[-0.14px] ${
                        isActive ? "text-white" : "text-black"
                      }`}
                    >
                      {item.label}
                    </p>
                    <p
                      className={`text-xs leading-[1.2] tracking-[-0.08px] ${
                        isActive ? "text-white/72" : "text-soft"
                      }`}
                    >
                      {item.description}
                    </p>
                  </div>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </aside>
  );
}
