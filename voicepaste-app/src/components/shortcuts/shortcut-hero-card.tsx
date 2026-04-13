import { PlusIcon } from "@/components/ui/icons";

const heroExamples = [
  {
    label: "“LinkedIn”",
    value: "https://www.linkedin.com/in/john-doe/",
  },
  {
    label: "“Intro email”",
    value: "Hey, would love to find some time to chat later this week.",
  },
  {
    label: "“My calendly link”",
    value: "calendly.com/you/invite-name",
  },
] as const;

export function ShortcutHeroCard() {
  return (
    <section className="relative overflow-hidden rounded-[30px] border border-[rgba(255,255,255,0.08)] bg-[linear-gradient(135deg,rgba(18,27,35,0.98),rgba(41,55,67,0.9)_52%,rgba(110,89,60,0.78))] p-6 text-white shadow-[0_24px_64px_rgba(23,32,40,0.26)] lg:p-7">
      <div className="absolute inset-y-0 right-0 w-[42%] bg-[radial-gradient(circle_at_center,rgba(245,213,164,0.22),transparent_58%)]" />
      <div className="absolute bottom-0 right-0 h-44 w-44 rounded-full bg-[rgba(248,210,163,0.12)] blur-3xl" />

      <div className="relative max-w-3xl">
        <div className="inline-flex rounded-full border border-white/12 bg-white/8 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.16em] text-white/72">
          Upcoming feature demo
        </div>
        <h2 className="mt-4 max-w-2xl text-3xl font-semibold tracking-[-0.04em] lg:text-[2.2rem]">
          The stuff you should not have to re-type.
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-white/72 lg:text-[15px]">
          This upcoming page shows how VoicePaste snippets can turn spoken shortcut names
          into saved text blocks, links, prompts, and reusable replies without repeating
          yourself.
        </p>

        <div className="mt-6 space-y-3">
          {heroExamples.map((item) => (
            <div
              key={item.label}
              className="flex flex-col gap-2 rounded-[22px] bg-white/8 p-3 backdrop-blur-sm md:flex-row md:items-center md:gap-3"
            >
              <div className="rounded-2xl bg-white px-3 py-2 text-sm font-semibold text-[#2d3742]">
                {item.label}
              </div>
              <span className="text-white/44">→</span>
              <div className="min-w-0 rounded-2xl bg-[rgba(255,255,255,0.16)] px-3 py-2 text-sm text-white/84">
                <span className="block truncate">{item.value}</span>
              </div>
            </div>
          ))}
        </div>

        <button
          className="mt-6 inline-flex items-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm font-semibold text-[#25313c] transition hover:bg-white/92"
          type="button"
        >
          <PlusIcon className="h-4 w-4" />
          Add new snippet
        </button>
      </div>
    </section>
  );
}
