import { ScreenHeader } from "@/components/layout/screen-header";
import { SettingsPanel } from "@/components/dashboard/settings-panel";

export function SettingsScreen() {
  return (
    <>
      <ScreenHeader
        eyebrow="Settings"
        title="Settings"
        description="Manage cloud enhancement and privacy-sensitive behavior from one focused screen while the dashboard stays dedicated to live activity and transcript review."
      />
      <div className="max-w-4xl space-y-6">
        <section className="border-y border-[var(--border-soft)] py-5">
          <p className="text-sm leading-7 text-[var(--text-muted)]">
            Audio remains local. Even when cloud enhancement is enabled, only transcript
            text is sent for cleanup, and the original transcript still proceeds if
            enhancement fails.
          </p>
        </section>
        <SettingsPanel />
      </div>
    </>
  );
}
