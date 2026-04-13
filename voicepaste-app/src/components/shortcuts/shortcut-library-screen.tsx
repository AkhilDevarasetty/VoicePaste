import { ScreenHeader } from "@/components/layout/screen-header";

export function ShortcutLibraryScreen() {
  return (
    <>
      <ScreenHeader
        eyebrow="Voice Shortcuts"
        title="Voice Shortcuts"
        description="Save space here for the future shortcuts experience. This screen will eventually hold reusable spoken commands and repeated task helpers."
      />

      <section className="border-y border-[var(--border-soft)] py-6">
        <span className="inline-flex rounded-full bg-[rgba(221,232,238,0.72)] px-3 py-1 text-xs font-medium uppercase tracking-[0.12em] text-[var(--accent)]">
          Coming as part of future enhancements
        </span>
      </section>
    </>
  );
}
