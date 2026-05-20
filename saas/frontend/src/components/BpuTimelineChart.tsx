import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { BpuFormula, BpuTimelinePoint } from "../lib/api";

type Props = {
  points: BpuTimelinePoint[];
  formula?: BpuFormula;
  includeTotal?: boolean;
};

/**
 * Couleurs par composante de la formule de tarification.
 *
 * Aligné avec /energie/preconisations :
 *   PU_total = PU_fourniture + PU_capacité + PU_CEE + PU_GO
 */
const COMPONENT_COLORS: Record<string, string> = {
  fourniture: "#2563eb",   // bleu — la plus grosse part, marché de gros
  capacite: "#f59e0b",     // orange — réglementaire RTE
  cee: "#10b981",          // vert — obligation CEE
  go: "#a855f7",           // violet — option renouvelable
  renouvelable: "#a855f7", // alias
  total: "#0f172a",        // noir slate — somme
};

const COMPONENT_LABELS: Record<string, string> = {
  fourniture: "Fourniture",
  capacite: "Capacité",
  cee: "CEE",
  go: "Garanties d'Origine",
  renouvelable: "GO / Renouvelable",
  total: "PU Total",
};

type AggregatedRow = {
  year: number;
  // Une clé par série : "supplier_lot_component"
  [seriesKey: string]: number | string | null;
};

/**
 * Aggrège les points reçus en lignes prêtes pour Recharts.
 *
 * Approche : on groupe par year, on moyenne les prix pour chaque
 * (composante, supplier, lot) — utile quand un BPU contient plusieurs
 * segments/postes que l'utilisateur n'a pas filtrés. On affiche toujours
 * 4 séries (une par composante) + optionnellement la somme PU_total.
 */
function buildSeries(points: BpuTimelinePoint[], includeTotal: boolean): {
  data: AggregatedRow[];
  seriesKeys: { key: string; label: string; color: string; component: string }[];
} {
  if (points.length === 0) {
    return { data: [], seriesKeys: [] };
  }

  // 1. Group by year × component
  type Acc = { sum: number; count: number };
  const byYearComponent: Map<number, Map<string, Acc>> = new Map();
  const componentsSeen = new Set<string>();

  for (const p of points) {
    const v = p.price_value_eur_per_mwh ?? p.price_value;
    if (v == null || Number.isNaN(Number(v))) continue;
    componentsSeen.add(p.component_type);
    const yearMap = byYearComponent.get(p.valid_year) ?? new Map<string, Acc>();
    const acc = yearMap.get(p.component_type) ?? { sum: 0, count: 0 };
    acc.sum += Number(v);
    acc.count += 1;
    yearMap.set(p.component_type, acc);
    byYearComponent.set(p.valid_year, yearMap);
  }

  // 2. Build rows sorted by year
  const years = Array.from(byYearComponent.keys()).sort((a, b) => a - b);
  const data: AggregatedRow[] = years.map((year) => {
    const yearMap = byYearComponent.get(year)!;
    const row: AggregatedRow = { year };
    let total = 0;
    let hasAny = false;
    for (const [component, acc] of yearMap) {
      const avg = acc.count > 0 ? acc.sum / acc.count : null;
      row[component] = avg;
      if (avg != null) {
        total += avg;
        hasAny = true;
      }
    }
    if (includeTotal && hasAny) {
      row.total = total;
    }
    return row;
  });

  // 3. Build series metadata (ordre canonique de la formule)
  const canonicalOrder = ["fourniture", "capacite", "cee", "go", "renouvelable"];
  const seriesKeys = canonicalOrder
    .filter((c) => componentsSeen.has(c))
    .map((c) => ({
      key: c,
      label: COMPONENT_LABELS[c] ?? c,
      color: COMPONENT_COLORS[c] ?? "#6b7280",
      component: c,
    }));
  if (includeTotal) {
    seriesKeys.push({
      key: "total",
      label: COMPONENT_LABELS.total,
      color: COMPONENT_COLORS.total,
      component: "total",
    });
  }

  return { data, seriesKeys };
}

// Fourniture et total ont des ordres de grandeur ~10-30× plus élevés que capacité/CEE/GO.
// On les sépare sur deux axes Y indépendants quand les deux groupes sont présents.
const LARGE_SERIES = new Set(["fourniture", "total"]);
const SMALL_SERIES = new Set(["capacite", "cee", "go", "renouvelable"]);

export default function BpuTimelineChart({ points, formula, includeTotal = true }: Props) {
  const { data, seriesKeys } = useMemo(
    () => buildSeries(points, includeTotal),
    [points, includeTotal],
  );

  const hasLarge = seriesKeys.some((s) => LARGE_SERIES.has(s.component));
  const hasSmall = seriesKeys.some((s) => SMALL_SERIES.has(s.component));
  const useDualAxis = hasLarge && hasSmall;

  if (points.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-400">
        Aucun point de prix sur ce filtre. Vérifiez qu'au moins un BPU a été importé
        et que les filtres ne sont pas trop restrictifs.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {formula && (
        <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
          <span className="font-mono font-medium">{formula.expression}</span>
          <span className="ml-2 text-slate-400">(unité cible : {formula.unit_target})</span>
        </div>
      )}

      {useDualAxis && (
        <div style={{ fontSize: "0.78rem", color: "#94a3b8", display: "flex", gap: 16, paddingLeft: 4 }}>
          <span>
            <span style={{ display: "inline-block", width: 10, height: 2, background: "#2563eb", marginRight: 4, verticalAlign: "middle" }} />
            Axe gauche : Fourniture / Total (€/MWh)
          </span>
          <span>
            <span style={{ display: "inline-block", width: 10, height: 2, background: "#f59e0b", marginRight: 4, verticalAlign: "middle" }} />
            Axe droit : Capacité · CEE · GO (€/MWh — échelle indépendante)
          </span>
        </div>
      )}

      <ResponsiveContainer width="100%" height={340}>
        <LineChart data={data} margin={{ top: 8, right: useDualAxis ? 80 : 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.25)" />
          <XAxis dataKey="year" tick={{ fontSize: 11 }} />

          {/* Axe gauche — fourniture / total (ou axe unique si pas de double) */}
          <YAxis
            yAxisId="large"
            orientation="left"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => `${v.toFixed(0)}`}
            unit=" €/MWh"
            width={90}
          />

          {/* Axe droit — composantes accessoires, uniquement si double axe */}
          {useDualAxis && (
            <YAxis
              yAxisId="small"
              orientation="right"
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              tickFormatter={(v: number) => `${v.toFixed(1)}`}
              unit=" €/MWh"
              width={72}
              label={{
                value: "accessoires →",
                angle: 90,
                position: "insideRight",
                offset: 12,
                style: { fontSize: 10, fill: "#64748b" },
              }}
            />
          )}

          <Tooltip
            formatter={(value: number | string, name: string) => {
              if (typeof value === "number") {
                return [`${value.toFixed(2)} €/MWh`, name];
              }
              return [value, name];
            }}
            contentStyle={{
              backgroundColor: "rgba(15,23,42,0.95)",
              border: "1px solid rgba(148,163,184,0.3)",
              color: "#f1f5f9",
              fontSize: "12px",
            }}
          />
          <Legend wrapperStyle={{ fontSize: "12px" }} />

          {seriesKeys.map((s) => {
            const axisId = useDualAxis
              ? LARGE_SERIES.has(s.component) ? "large" : "small"
              : "large";
            return (
              <Line
                key={s.key}
                yAxisId={axisId}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stroke={s.color}
                strokeWidth={s.key === "total" ? 3 : 2}
                strokeDasharray={useDualAxis && SMALL_SERIES.has(s.component) ? "5 3" : undefined}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                connectNulls
                isAnimationActive={false}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
