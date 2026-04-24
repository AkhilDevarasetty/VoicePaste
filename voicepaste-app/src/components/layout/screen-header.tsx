import type { ReactNode } from "react";

type ScreenHeaderProps = {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
};

export function ScreenHeader({
  eyebrow,
  title,
  description,
  actions,
}: ScreenHeaderProps) {
  return (
    <header className="fig-panel">
      <div className="fig-gradient-showcase h-2 w-full" />
      <div className="flex flex-wrap items-start justify-between gap-6 px-6 py-6 lg:px-8 lg:py-7">
        <div className="max-w-3xl">
          <p className="fig-mono-label text-[11px] text-soft">{eyebrow}</p>
          <h1 className="fig-display mt-3 text-[2.9rem] leading-[1.06] tracking-[-0.08em] text-black lg:text-[4rem]">
            {title}
          </h1>
          {description ? (
            <p className="fig-body-light mt-4 max-w-2xl text-[1.02rem] leading-[1.45] text-muted lg:text-[1.12rem]">
              {description}
            </p>
          ) : null}
        </div>
        {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
      </div>
    </header>
  );
}
