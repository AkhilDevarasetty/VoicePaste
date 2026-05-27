import { SettingsPanel } from "@/components/dashboard/settings-panel";
import { ScreenHeader } from "@/components/layout/screen-header";

export function SettingsScreen() {
  return (
    <>
      <ScreenHeader
        title="Settings"
        description="Manage VoicePaste behavior here. More settings will be added over time."
      />
      <div className="max-w-4xl">
        <SettingsPanel />
      </div>
    </>
  );
}
