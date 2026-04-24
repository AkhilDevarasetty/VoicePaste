import { VoicePasteMark } from "@/components/ui/icons";

type AppLogoProps = {
  collapsed?: boolean;
};

export function AppLogo({ collapsed = false }: AppLogoProps) {
  if (collapsed) {
    return (
      <div className="flex justify-center">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center text-black">
          <VoicePasteMark className="h-8 w-8" />
        </div>
      </div>
    );
  }

  return (
    <div className="inline-grid grid-cols-[2.35rem_auto] items-end gap-x-0">
      <div className="-mb-0.5 flex h-[2.45rem] w-[2.35rem] shrink-0 items-end justify-center text-black">
        <VoicePasteMark className="h-[2.1rem] w-[2.1rem]" />
      </div>
      <span className="-ml-0.5 fig-display block whitespace-nowrap text-[1.85rem] leading-none tracking-[-0.06em] text-black">
        oicePaste
      </span>
      <div className="col-start-2 flex justify-end pt-1 pr-1">
        <span className="fig-pill inline-flex border border-black/18 px-2 py-0.5 text-[9px] font-medium uppercase tracking-[0.2em] text-black/72">
          Beta
        </span>
      </div>
    </div>
  );
}
