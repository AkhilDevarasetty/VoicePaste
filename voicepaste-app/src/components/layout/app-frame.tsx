import type { ReactNode } from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";

type AppFrameProps = {
  children: ReactNode;
  currentPath: "/" | "/voice-shortcuts" | "/settings";
};

export function AppFrame({ children, currentPath }: AppFrameProps) {
  return (
    <main className="h-screen overflow-hidden bg-[var(--background)] text-[var(--foreground)]">
      <div className="flex h-full overflow-hidden">
        <AppSidebar currentPath={currentPath} />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-[linear-gradient(180deg,rgba(255,255,255,0.56),rgba(255,255,255,0.82))]">
          <div className="flex flex-1 flex-col gap-8 overflow-y-auto px-6 py-7 lg:px-10 lg:py-8">
            {children}
          </div>
        </div>
      </div>
    </main>
  );
}
