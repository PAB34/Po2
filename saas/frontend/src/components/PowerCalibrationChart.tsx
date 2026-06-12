import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PrmPowerRecommendation } from "../lib/api";

/**
 * Repartition du parc d'abonnements electriques par tranche de taux
 * d'utilisation (pic / puissance souscrite).
 *
 * Lecture immediate : chaque barre = un nombre de PRM, la couleur rappelle la
 * zone de calibrage du moteur (services/power_recommendations.py, seuils
 * 40 / 80 / 95 %). Les PRM extremes (taux > 100 %) sont regroupes dans une
 * seule barre "Depassement" pour ne pas ecraser l'echelle.
 */

type Bucket = {
  key: string;
  label: string;
  zone: string;
  color: string;
  test: (ratio: number) => boolean;
};

const BUCKETS: Bucket[] = [
  { key: "sur", label: "< 40 %", zone: "Sur-souscrit", color: "#38bdf8", test: (r) => r < 40 },
  { key: "bien", label: "40 – 80 %", zone: "Bien calibre", color: "#22c55e", test: (r) => r >= 40 && r < 80 },
  { key: "proche", label: "80 – 95 %", zone: "Proche du seuil", color: "#f97316", test: (r) => r >= 80 && r < 95 },
  { key: "limite", label: "95 – 100 %", zone: "Sous-dimensionne", color: "#fb7185", test: (r) => r >= 95 && r <= 100 },
  { key: "depass", label: "> 100 %", zone: "Depassement (penalites)", color: "#ef4444", test: (r) => r > 100 },
];

type Row = {
  key: string;
  label: string;
  zone: string;
  color: string;
  count: number;
  subscribedKva: number;
  consumptionMwh: number;
};

type Props = {
  recommendations: PrmPowerRecommendation[];
  // Conserve pour compat. avec l'appelant ; non utilise par l'histogramme.
  onSelect?: (prmId: string) => void;
};

function CalibrationTooltip({
  active,
  payload,
  total,
}: {
  active?: boolean;
  payload?: Array<{ payload: Row }>;
  total: number;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const row = payload[0].payload;
  const share = total > 0 ? (row.count / total) * 100 : 0;
  return (
    <div className="calibration-tooltip">
      <strong>{row.zone}</strong>
      <span className="calibration-tooltip-sub">Taux d'utilisation {row.label}</span>
      <div className="calibration-tooltip-rows">
        <div>
          <span>Nombre de PRM</span>
          <strong>{row.count.toLocaleString("fr-FR")}</strong>
        </div>
        <div>
          <span>Part du parc</span>
          <strong>{share.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %</strong>
        </div>
        <div>
          <span>Puissance souscrite</span>
          <strong>{row.subscribedKva.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} kVA</strong>
        </div>
        <div>
          <span>Conso annuelle</span>
          <strong>{row.consumptionMwh.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} MWh</strong>
        </div>
      </div>
    </div>
  );
}

export function PowerCalibrationChart({ recommendations }: Props) {
  const { rows, positioned, unplaced } = useMemo(() => {
    const acc: Record<string, Row> = {};
    for (const b of BUCKETS) {
      acc[b.key] = {
        key: b.key,
        label: b.label,
        zone: b.zone,
        color: b.color,
        count: 0,
        subscribedKva: 0,
        consumptionMwh: 0,
      };
    }
    let placed = 0;
    let skipped = 0;
    for (const item of recommendations) {
      const ratio = item.current_ratio_percent;
      if (ratio === null) {
        skipped += 1;
        continue;
      }
      const bucket = BUCKETS.find((b) => b.test(ratio));
      if (!bucket) {
        skipped += 1;
        continue;
      }
      const row = acc[bucket.key];
      row.count += 1;
      row.subscribedKva += item.subscribed_power_kva ?? 0;
      row.consumptionMwh += (item.annual_consumption_kwh ?? 0) / 1000;
      placed += 1;
    }
    return { rows: BUCKETS.map((b) => acc[b.key]), positioned: placed, unplaced: skipped };
  }, [recommendations]);

  const maxCount = Math.max(1, ...rows.map((r) => r.count));

  return (
    <section className="calibration-panel">
      <div className="calibration-header">
        <div>
          <h3>Repartition des abonnements par calibrage</h3>
          <p>
            Chaque barre regroupe les PRM selon leur taux d'utilisation (pic / puissance souscrite). La
            couleur indique la zone : du sur-souscrit (a gauche) au depassement de puissance (a droite).
          </p>
        </div>
      </div>

      <div className="calibration-legend">
        {rows.map((row) => (
          <span key={row.key} className="calibration-legend-item">
            <span className="calibration-legend-dot" style={{ background: row.color }} />
            {row.zone} ({row.count})
          </span>
        ))}
        {unplaced > 0 && (
          <span className="calibration-legend-item calibration-legend-item--muted">
            {unplaced} PRM sans taux d'utilisation (donnee manquante)
          </span>
        )}
      </div>

      {positioned === 0 ? (
        <p className="cell-empty">Aucun PRM avec un taux d'utilisation exploitable.</p>
      ) : (
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={rows} margin={{ top: 24, right: 16, bottom: 28, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(148,163,184,0.18)" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 12, fill: "#cbd5e1" }}
              tickLine={false}
              axisLine={{ stroke: "rgba(148,163,184,0.3)" }}
              label={{
                value: "Taux d'utilisation (pic / souscrit)",
                position: "insideBottom",
                offset: -16,
                fontSize: 11,
                fill: "#64748b",
              }}
            />
            <YAxis
              allowDecimals={false}
              domain={[0, Math.ceil(maxCount * 1.15)]}
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              tickLine={false}
              axisLine={false}
              width={40}
              label={{
                value: "Nombre de PRM",
                angle: -90,
                position: "insideLeft",
                offset: 12,
                style: { fontSize: 11, fill: "#64748b", textAnchor: "middle" },
              }}
            />
            <Tooltip
              cursor={{ fill: "rgba(148,163,184,0.08)" }}
              content={<CalibrationTooltip total={positioned} />}
            />
            <Bar dataKey="count" radius={[6, 6, 0, 0]} isAnimationActive={false} maxBarSize={96}>
              {rows.map((row) => (
                <Cell key={row.key} fill={row.color} />
              ))}
              <LabelList
                dataKey="count"
                position="top"
                formatter={(value: number | string) => (Number(value) > 0 ? Number(value).toLocaleString("fr-FR") : "")}
                style={{ fill: "#e2e8f0", fontSize: 12, fontWeight: 600 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}
