import type { ReactNode } from "react";

type KpiTone = "neutral" | "good" | "warning" | "danger" | "info";
type KpiCardProps = { label: string; value: string; detail?: string; trend?: string; tone?: KpiTone; icon?: ReactNode; };

export function KpiCard({ label, value, detail, trend, tone = "neutral", icon }: KpiCardProps) {
  return (
    <article className={["po2-kpi", "po2-kpi--" + tone].join(" ")}>
      <div className="po2-kpi__top"><span>{label}</span>{icon ? <span className="po2-kpi__icon">{icon}</span> : null}</div>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
      {trend ? <em>{trend}</em> : null}
    </article>
  );
}
