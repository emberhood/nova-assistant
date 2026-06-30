const COLORS = {
  text: "var(--nova-text)",
  green: "var(--nova-green)",
  red: "var(--nova-red)",
  accent: "var(--nova-cyan)",
  accent2: "var(--nova-violet)",
} as const;

interface InfoRowProps {
  label: string;
  value: string;
  valueColor?: keyof typeof COLORS;
}

export default function InfoRow({ label, value, valueColor = "text" }: InfoRowProps) {
  return (
    <div className="flex w-[200px] items-center justify-between rounded-md border border-nova-border bg-nova-cyan/[0.04] px-2.5 py-1.5">
      <span className="font-heading text-[10px] uppercase tracking-[0.12em] text-nova-text-dim">{label}</span>
      <span
        className="font-heading text-[11px] font-semibold tracking-[0.08em]"
        style={{ color: COLORS[valueColor] }}
      >
        {value}
      </span>
    </div>
  );
}
