import type { ReactNode } from "react";

type IconButtonProps = {
  label: string;
  icon: ReactNode;
};

export function IconButton({ label, icon }: IconButtonProps) {
  return (
    <button
      aria-label={label}
      className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border-soft)] bg-white/78 text-[var(--text-muted)] transition hover:border-[var(--border-strong)] hover:bg-white hover:text-[var(--foreground)]"
      type="button"
    >
      {icon}
    </button>
  );
}
