type Tone = "accent" | "success" | "warning" | "danger";

const toneClasses: Record<Tone, string> = {
  accent: "bg-black text-white border-black",
  success: "bg-black text-white border-black",
  warning: "bg-white text-black border-black",
  danger: "bg-white text-black border-black",
};

type StatusBadgeProps = {
  label: string;
  tone: Tone;
};

export function StatusBadge({ label, tone }: StatusBadgeProps) {
  return (
    <span
      className={`fig-pill inline-flex items-center gap-2 border px-3.5 py-2 text-[11px] font-medium uppercase tracking-[0.22em] ${toneClasses[tone]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}
