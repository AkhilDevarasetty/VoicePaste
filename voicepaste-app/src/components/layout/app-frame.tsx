"use client";

import type { ReactNode } from "react";
import { useState } from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";

type AppFrameProps = {
  children: ReactNode;
  currentPath: "/" | "/voice-shortcuts" | "/settings";
};

export function AppFrame({ children, currentPath }: AppFrameProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <main className="h-screen overflow-hidden bg-white text-black">
      <div className="flex h-full overflow-hidden">
        <AppSidebar
          collapsed={sidebarCollapsed}
          currentPath={currentPath}
          onToggle={() => setSidebarCollapsed((value) => !value)}
        />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
          <div className="desktop-scroll flex min-h-0 flex-1 overflow-y-scroll px-4 py-4 lg:px-6 lg:py-6">
            <div className="mx-auto flex w-full max-w-[1320px] flex-col gap-6">
              {children}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
