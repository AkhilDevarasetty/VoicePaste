import { AppFrame } from "@/components/layout/app-frame";
import { SettingsScreen } from "@/components/settings/settings-screen";

export default function SettingsPage() {
  return (
    <AppFrame currentPath="/settings">
      <SettingsScreen />
    </AppFrame>
  );
}
