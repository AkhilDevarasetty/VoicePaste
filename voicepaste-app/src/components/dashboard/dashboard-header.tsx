import { IconButton } from "@/components/ui/icon-button";
import { GridIcon, MicrophoneIcon, SettingsIcon, SparkIcon } from "@/components/ui/icons";

export function DashboardHeader() {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 px-5 py-5 lg:px-8 lg:py-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--text-soft)]">
          Dashboard
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] lg:text-4xl">
          Transcript history, ready to work from.
        </h1>
      </div>
      <div className="flex items-center gap-2">
        <IconButton label="Overview" icon={<GridIcon className="h-[17px] w-[17px]" />} />
        <IconButton label="Recordings" icon={<MicrophoneIcon className="h-[17px] w-[17px]" />} />
        <IconButton label="Automations" icon={<SparkIcon className="h-[17px] w-[17px]" />} />
        <IconButton label="Settings" icon={<SettingsIcon className="h-[17px] w-[17px]" />} />
      </div>
    </header>
  );
}
