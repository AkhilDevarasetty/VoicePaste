import { SettingsPanel } from "@/components/dashboard/settings-panel";
import { ScreenHeader } from "@/components/layout/screen-header";

export function SettingsScreen() {
  return (
    <>
      <ScreenHeader
        eyebrow="Settings"
        title="System preferences"
        description="Manage transcript cleanup behavior and keep the operational dashboard focused on recent output and target-app visibility."
      />
      <div className="max-w-4xl space-y-6">
        <section className="fig-panel px-6 py-6 lg:px-8">
          <p className="text-[1rem] leading-[1.45] tracking-[-0.14px] text-muted">
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
