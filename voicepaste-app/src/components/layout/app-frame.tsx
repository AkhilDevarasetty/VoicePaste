"use client";

import type { ReactNode } from "react";
import { useState } from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";

type AppFrameProps = {
  children: ReactNode;
  currentPath: "/" | "/voice-shortcuts" | "/settings";
};

export function AppFrame({ children, currentPath }: AppFrameProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }

    return window.localStorage.getItem("voicepaste-sidebar-collapsed") === "true";
  });

  function handleToggle() {
    setSidebarCollapsed((value) => {
      const nextValue = !value;
      window.localStorage.setItem(
        "voicepaste-sidebar-collapsed",
        String(nextValue),
      );
      return nextValue;
    });
  }

  return (
    <main className="h-screen overflow-hidden bg-white text-black">
      <div className="flex h-full overflow-hidden">
        <AppSidebar
          collapsed={sidebarCollapsed}
          currentPath={currentPath}
          onToggle={handleToggle}
        />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
          <div className="desktop-scroll flex min-h-0 flex-1 overflow-y-scroll px-4 py-4 lg:px-5 lg:py-5">
            <div className="mx-auto flex w-full max-w-[1320px] flex-col gap-5">
              {children}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
