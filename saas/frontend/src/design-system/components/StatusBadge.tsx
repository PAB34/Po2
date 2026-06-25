type StatusTone = "ok" | "warn" | "bad" | "info" | "neutral";
type StatusBadgeProps = { children: string; tone?: StatusTone; };

export function StatusBadge({ children, tone = "neutral" }: StatusBadgeProps) {
  return <span className={["po2-status", "po2-status--" + tone].join(" ")}>{children}</span>;
}
