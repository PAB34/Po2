import { useMemo, useState } from "react";
import {
  CartesianGrid,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import type { PrmPowerRecommendation } from "../lib/api";

/**
 * Carte de calibrage des abonnements electriques.
 *
 * Une seule visualisation qui croise tous les criteres du moteur de
 * preconisations (services/power_recommendations.py) :
 *   - X  : taux d'utilisation = pic / puissance souscrite (le critere central)
 *   - Y  : metrique reglable (puissance souscrite, conso annuelle, impact €)
 *   - taille de bulle : volume reglable (conso, puissance, impact)
 *   - couleur : type de recommandation (hausse / baisse / maintien / donnees insuff.)
 *   - bandes de fond : les 4 zones de calibrage (seuils 40 / 80 / 95 %)
 */

const ACTION_COLORS: Record<string, string> = {
  increase: "#ef4444",
  decrease: "#38bdf8",
  maintain: "#22c55e",
  insufficient_data: "#94a3b8",
};

const ACTION_LABELS: Record<string, string> = {
  increase: "Hausse conseillee",
  decrease: "Baisse possible",
  maintain: "Maintien",
  insufficient_data: "Donnees insuff.",
};

type YMetric = "subscribed" | "consumption" | "impact";
type SizeMetric = "consumption" | "subscribed" | "impact";

const Y_METRICS: Record<YMetric, { label: string; unit: string }> = {
  subscribed: { label: "Puissance souscrite", unit: "kVA" },
  consumption: { label: "Conso annuelle", unit: "MWh" },
  impact: { label: "Impact annuel estime", unit: "€" },
};

const SIZE_METRICS: Record<SizeMetric, string> = {
  consumption: "Conso annuelle",
  subscribed: "Puissance souscrite",
  impact: "Impact annuel (valeur abs.)",
};

type Point = {
  prm: string;
  name: string;
  contractor: string;
  x: number;
  y: number;
  z: number;
  action: string;
  confidence: string;
  ratio: number;
  subscribed: number | null;
  peak: number | null;
  recommended: number | null;
  consumption: number | null;
  impact: number | null;
};

function yValue(item: PrmPowerRecommendation, metric: YMetric): number | null {
  if (metric === "subscribed") return item.subscribed_power_kva;
  if (metric === "consumption") {
    return item.annual_consumption_kwh === null ? null : item.annual_consumption_kwh / 1000;
  }
  return item.economic_estimate.available ? item.economic_estimate.annual_amount_eur : null;
}

function sizeValue(item: PrmPowerRecommendation, metric: SizeMetric): number {
  if (metric === "subscribed") return item.subscribed_power_kva ?? 0;
  if (metric === "impact") {
    return item.economic_estimate.available ? Math.abs(item.economic_estimate.annual_amount_eur ?? 0) : 0;
  }
  return item.annual_consumption_kwh ?? 0;
}

function fmtKva(v: number | null) {
  return v === null ? "-" : `${v.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} kVA`;
}

function fmtKwh(v: number | null) {
  if (v === null) return "-";
  if (v >= 1000) return `${(v / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} MWh`;
  return `${v.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} kWh`;
}

function fmtEur(v: number | null) {
  return v === null ? "-" : new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(v);
}

function CalibrationTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: Point }> }) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0].payload;
  return (
    <div className="calibration-tooltip">
      <strong>{p.name}</strong>
      <span className="calibration-tooltip-sub">
        {p.prm} · {p.contractor}
      </span>
      <span className="badge" style={{ background: `${ACTION_COLORS[p.action]}26`, color: ACTION_COLORS[p.action] }}>
        {ACTION_LABELS[p.action] ?? p.action}
      </span>
      <div className="calibration-tooltip-rows">
        <div>
          <span>Taux d'utilisation</span>
          <strong>{p.ratio.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %</strong>
        </div>
        <div>
          <span>Souscrit / pic</span>
          <strong>
            {fmtKva(p.subscribed)} · {fmtKva(p.peak)}
          </strong>
        </div>
        <div>
          <span>Recommande</span>
          <strong>{fmtKva(p.recommended)}</strong>
        </div>
        <div>
          <span>Conso annuelle</span>
          <strong>{fmtKwh(p.consumption)}</strong>
        </div>
        <div>
          <span>Impact / an</span>
          <strong>{p.impact === null ? "Non chiffre" : fmtEur(p.impact)}</strong>
        </div>
        <div>
          <span>Confiance</span>
          <strong>{p.confidence}</strong>
        </div>
      </div>
      <span className="calibration-tooltip-hint">Cliquer pour ouvrir le detail du PRM</span>
    </div>
  );
}

type Props = {
  recommendations: PrmPowerRecommendation[];
  onSelect?: (prmId: string) => void;
};

export function PowerCalibrationChart({ recommendations, onSelect }: Props) {
  const [yMetric, setYMetric] = useState<YMetric>("subscribed");
  const [sizeMetric, setSizeMetric] = useState<SizeMetric>("consumption");

  const { points, unplaced } = useMemo(() => {
    const placed: Point[] = [];
    let skipped = 0;
    for (const item of recommendations) {
      const y = yValue(item, yMetric);
      if (item.current_ratio_percent === null || y === null) {
        skipped += 1;
        continue;
      }
      placed.push({
        prm: item.usage_point_id,
        name: item.name,
        contractor: item.contractor ?? "Fournisseur inconnu",
        x: item.current_ratio_percent,
        y,
        z: sizeValue(item, sizeMetric),
        action: item.action,
        confidence: item.confidence,
        ratio: item.current_ratio_percent,
        subscribed: item.subscribed_power_kva,
        peak: item.peak_kva,
        recommended: item.recommended_power_kva,
        consumption: item.annual_consumption_kwh,
        impact: item.economic_estimate.available ? item.economic_estimate.annual_amount_eur : null,
      });
    }
    return { points: placed, unplaced: skipped };
  }, [recommendations, yMetric, sizeMetric]);

  const groups = useMemo(() => {
    const order = ["increase", "decrease", "maintain", "insufficient_data"];
    return order
      .map((action) => ({ action, data: points.filter((p) => p.action === action) }))
      .filter((g) => g.data.length > 0);
  }, [points]);

  const xMax = useMemo(() => Math.max(120, ...points.map((p) => p.x)), [points]);
  const yUnit = Y_METRICS[yMetric].unit;

  return (
    <section className="calibration-panel">
      <div className="calibration-header">
        <div>
          <h3>Carte de calibrage des abonnements</h3>
          <p>
            Chaque bulle est un PRM. Position horizontale = taux d'utilisation (pic / souscrit), couleur =
            recommandation, taille = volume. Les bandes rappellent les zones du moteur (seuils 40 / 80 / 95 %).
          </p>
        </div>
        <div className="calibration-controls">
          <label>
            Axe vertical
            <select value={yMetric} onChange={(e) => setYMetric(e.target.value as YMetric)} className="filter-select">
              {(Object.keys(Y_METRICS) as YMetric[]).map((key) => (
                <option key={key} value={key}>
                  {Y_METRICS[key].label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Taille des bulles
            <select
              value={sizeMetric}
              onChange={(e) => setSizeMetric(e.target.value as SizeMetric)}
              className="filter-select"
            >
              {(Object.keys(SIZE_METRICS) as SizeMetric[]).map((key) => (
                <option key={key} value={key}>
                  {SIZE_METRICS[key]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="calibration-legend">
        {groups.map((g) => (
          <span key={g.action} className="calibration-legend-item">
            <span className="calibration-legend-dot" style={{ background: ACTION_COLORS[g.action] }} />
            {ACTION_LABELS[g.action]} ({g.data.length})
          </span>
        ))}
        {unplaced > 0 && (
          <span className="calibration-legend-item calibration-legend-item--muted">
            {unplaced} PRM non positionnable{unplaced > 1 ? "s" : ""} (donnee manquante)
          </span>
        )}
      </div>

      {points.length === 0 ? (
        <p className="cell-empty">Aucun PRM positionnable avec les filtres actuels.</p>
      ) : (
        <ResponsiveContainer width="100%" height={380}>
          <ScatterChart margin={{ top: 12, right: 24, bottom: 28, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />

            {/* Zones de calibrage (alignees sur _status_from_ratio) */}
            <ReferenceArea x1={0} x2={40} fill="rgba(56,189,248,0.07)" stroke="none" ifOverflow="hidden" />
            <ReferenceArea x1={40} x2={80} fill="rgba(34,197,94,0.07)" stroke="none" ifOverflow="hidden" />
            <ReferenceArea x1={80} x2={95} fill="rgba(245,158,11,0.09)" stroke="none" ifOverflow="hidden" />
            <ReferenceArea x1={95} x2={xMax} fill="rgba(239,68,68,0.10)" stroke="none" ifOverflow="hidden" />
            <ReferenceLine
              x={100}
              stroke="rgba(239,68,68,0.55)"
              strokeDasharray="4 4"
              label={{ value: "pic = souscrit", position: "top", fontSize: 10, fill: "#fca5a5" }}
            />

            <XAxis
              type="number"
              dataKey="x"
              name="Taux d'utilisation"
              unit=" %"
              domain={[0, Math.ceil(xMax / 10) * 10]}
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              label={{
                value: "Taux d'utilisation (pic / souscrit)",
                position: "insideBottom",
                offset: -16,
                fontSize: 11,
                fill: "#64748b",
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name={Y_METRICS[yMetric].label}
              unit={` ${yUnit}`}
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              width={72}
              label={{
                value: `${Y_METRICS[yMetric].label} (${yUnit})`,
                angle: -90,
                position: "insideLeft",
                offset: 6,
                style: { fontSize: 11, fill: "#64748b", textAnchor: "middle" },
              }}
            />
            <ZAxis type="number" dataKey="z" range={[50, 620]} name={SIZE_METRICS[sizeMetric]} />

            <Tooltip cursor={{ strokeDasharray: "3 3" }} content={<CalibrationTooltip />} />

            {groups.map((g) => (
              <Scatter
                key={g.action}
                name={ACTION_LABELS[g.action]}
                data={g.data}
                fill={ACTION_COLORS[g.action]}
                fillOpacity={0.62}
                stroke={ACTION_COLORS[g.action]}
                strokeWidth={1}
                isAnimationActive={false}
                onClick={(payload: { prm?: string }) => {
                  if (onSelect && payload?.prm) onSelect(payload.prm);
                }}
                style={{ cursor: onSelect ? "pointer" : "default" }}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}
