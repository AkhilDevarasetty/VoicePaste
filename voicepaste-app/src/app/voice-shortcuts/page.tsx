import { ShortcutLibraryScreen } from "@/components/shortcuts/shortcut-library-screen";
import { AppFrame } from "@/components/layout/app-frame";

export default function VoiceShortcutsPage() {
  return (
    <AppFrame currentPath="/voice-shortcuts">
      <ShortcutLibraryScreen />
    </AppFrame>
  );
}
