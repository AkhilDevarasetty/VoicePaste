import { ScreenHeader } from "@/components/layout/screen-header";

export function ShortcutLibraryScreen() {
  return (
    <>
      <ScreenHeader
        eyebrow="Voice Shortcuts"
        title="Reusable spoken commands"
        description="This screen is reserved for future voice shortcuts, reusable prompts, and repeated task helpers."
      />

      <section className="fig-panel px-6 py-8 lg:px-8">
        <span className="fig-pill inline-flex border border-black bg-white px-4 py-2 text-[11px] font-medium uppercase tracking-[0.22em] text-black">
          Coming as part of future enhancements
        </span>
      </section>
    </>
  );
}
