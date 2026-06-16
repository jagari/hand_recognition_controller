type StatusPillProps = {
  label: string;
  tone?: "blue" | "green" | "orange" | "red" | "neutral";
};

export function StatusPill({ label, tone = "neutral" }: StatusPillProps) {
  return <span className={`status-pill status-pill--${tone}`}>{label}</span>;
}
