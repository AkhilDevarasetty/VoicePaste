import type { ReactNode } from "react";

type ScreenHeaderProps = {
  title: string;
  description?: string;
  actions?: ReactNode;
};

export function ScreenHeader({
  title,
  description,
  actions,
}: ScreenHeaderProps) {
  return (
    <header className="fig-panel">
      <div aria-hidden="true" className="fig-gradient-showcase h-2 w-full" />
      <div className="flex flex-wrap items-start justify-between gap-5 px-6 py-5 lg:px-8 lg:py-5">
        <div className="max-w-3xl">
          <h1 className="fig-display text-[2.25rem] leading-[1.04] tracking-[-0.08em] text-black lg:text-[2.85rem]">
            {title}
          </h1>
          {description ? (
            <p className="fig-body-light mt-3 max-w-2xl text-[0.98rem] leading-[1.42] text-muted lg:text-[1.04rem]">
              {description}
            </p>
          ) : null}
        </div>
        {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
      </div>
    </header>
  );
}
