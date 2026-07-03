import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, DataTable, KpiCard } from "../../design-system";
import type { MarketVariablePointV1, MarketVariableSeriesV1 } from "../../lib/api";
import { useMarketIndicesVariablesV1 } from "./useMarketIndicesVariablesV1";

const FAMILY_LABELS: Record<string, string> = {
  dalkia: "DALKIA - indices et coefficients",
  gaz: "Gaz - PEG fourniture",
  elec: "Electricite - TURPE",
};

const FAMILY_DETAILS: Record<string, string> = {
  dalkia: "ICHT-IME, FSD2, BT40 et coefficients observes P2/P3",
  gaz: "Prix PEG mensuel consomme par le moteur gaz existant",
  elec: "Evolution moyenne HTA-BT et indice cumule TURPE",
};

const COLORS = ["#2563eb", "#16a34a", "#dc2626", "#7c3aed", "#ea580c", "#0891b2"];

type ChartRow = { period: string } & Record<string, number | string | null>;
type TableRow = MarketVariablePointV1 & { code: string; label: string; unit: string; family: string };

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Une erreur est survenue.";
}

function formatValue(value: number, unit: string) {
  if (unit === "EUR/MWh") return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} EUR/MWh`;
  if (unit === "%") return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 2 })}%`;
  if (unit === "coefficient") return value.toFixed(4);
  return value.toLocaleString("fr-FR", { maximumFractionDigits: 3 });
}

function groupByFamily(series: MarketVariableSeriesV1[]) {
  return series.reduce<Record<string, MarketVariableSeriesV1[]>>((acc, item) => {
    acc[item.family] = [...(acc[item.family] ?? []), item];
    return acc;
  }, {});
}

function chartRows(series: MarketVariableSeriesV1[]): ChartRow[] {
  const rows = new Map<string, ChartRow>();
  for (const item of series) {
    for (const point of item.points) {
      const row = rows.get(point.period) ?? { period: point.period };
      row[item.code] = point.value;
      rows.set(point.period, row);
    }
  }
  return [...rows.values()].sort((a, b) => String(a.period).localeCompare(String(b.period)));
}

function tableRows(series: MarketVariableSeriesV1[], family: string): TableRow[] {
  return series
    .flatMap((item) => item.points.map((point) => ({ ...point, code: item.code, label: item.label, unit: item.unit, family })))
    .sort((a, b) => `${a.period}-${a.label}`.localeCompare(`${b.period}-${b.label}`));
}

type IndicesVariablesV1Props = {
  /** Familles à afficher (dalkia, gaz, elec). Si absent, toutes. */
  families?: string[];
  /** Masque l'en-tête de page quand le composant est embarqué dans un sous-onglet. */
  embedded?: boolean;
};

export function IndicesVariablesV1({ families: familyFilter, embedded = false }: IndicesVariablesV1Props = {}) {
  const currentYear = new Date().getFullYear();
  const [yearFrom, setYearFrom] = useState(currentYear - 1);
  const [yearTo, setYearTo] = useState(currentYear);
  const query = useMarketIndicesVariablesV1(yearFrom, yearTo);

  const filterSet = familyFilter ? new Set(familyFilter) : null;
  const series = useMemo(
    () => (query.data?.series ?? []).filter((s) => (filterSet ? filterSet.has(s.family) : true)),
    [query.data, filterSet],
  );
  const data = query.data ? { ...query.data, series } : undefined;

  const families = useMemo(() => groupByFamily(series), [series]);
  const familyEntries = Object.entries(families).sort(([a], [b]) => a.localeCompare(b));
  const pointsCount = series.reduce((sum, item) => sum + item.points.length, 0);

  return (
    <div className="po2-page-v1">
      {embedded ? null : (
        <header className="po2-page-v1__head">
          <span className="po2-eyebrow">Marches - indices et variables</span>
          <h1>Suivi des indices et variables de prix</h1>
          <p>
            Vue transverse des donnees qui alimentent les revisions : indices DALKIA, coefficient observe des factures,
            PEG gaz et evolution TURPE. Lecture seule : les ecrans de reference restent les sources de saisie.
          </p>
        </header>
      )}

      <Card title="Periode" eyebrow="visualisation lecture seule">
        <div className="po2-matrix-import-form">
          <label>
            <span>De</span>
            <input
              type="number"
              value={yearFrom}
              onChange={(event) => setYearFrom(Number(event.currentTarget.value) || currentYear - 1)}
            />
          </label>
          <label>
            <span>A</span>
            <input
              type="number"
              value={yearTo}
              onChange={(event) => setYearTo(Number(event.currentTarget.value) || currentYear)}
            />
          </label>
        </div>
      </Card>

      {query.isError ? (
        <Card eyebrow="erreur">
          <p className="po2-muted-line">Indices indisponibles : {errorMessage(query.error)}</p>
        </Card>
      ) : null}
      {query.isFetching && !data ? <p className="po2-muted-line">Chargement des indices et variables...</p> : null}

      {data ? (
        <>
          <div className="po2-kpi-grid">
            <KpiCard label="Familles" value={String(familyEntries.length)} detail="DALKIA, gaz, electricite" />
            <KpiCard label="Series" value={String(data.series.length)} detail={`${data.year_from} - ${data.year_to}`} />
            <KpiCard label="Points" value={String(pointsCount)} detail="valeurs normalisees" />
          </div>

          {familyEntries.length === 0 ? (
            <Card eyebrow="aucune donnee">
              <p className="po2-muted-line">Aucune valeur disponible sur la periode selectionnee.</p>
            </Card>
          ) : null}

          {familyEntries.map(([family, familySeries]) => {
            const rows = chartRows(familySeries);
            const table = tableRows(familySeries, family);
            return (
              <Card key={family} title={FAMILY_LABELS[family] ?? family} eyebrow={FAMILY_DETAILS[family] ?? "source existante"}>
                {rows.length > 0 ? (
                  <div style={{ width: "100%", height: 320 }}>
                    <ResponsiveContainer>
                      <LineChart data={rows} margin={{ top: 12, right: 20, bottom: 8, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="period" minTickGap={16} />
                        <YAxis width={72} />
                        <Tooltip />
                        {familySeries.map((item, index) => (
                          <Line
                            key={item.code}
                            type="monotone"
                            dataKey={item.code}
                            name={`${item.label} (${item.unit})`}
                            stroke={COLORS[index % COLORS.length]}
                            strokeWidth={2}
                            dot={{ r: 3 }}
                            connectNulls
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="po2-muted-line">Aucune valeur tracee pour cette famille.</p>
                )}
                <DataTable
                  rows={table}
                  getRowKey={(row) => `${row.code}-${row.period}`}
                  columns={[
                    { key: "period", header: "Periode", render: (row) => row.period },
                    { key: "variable", header: "Variable", render: (row) => row.label },
                    { key: "value", header: "Valeur", render: (row) => formatValue(row.value, row.unit) },
                    { key: "source", header: "Source", render: (row) => row.source ?? "-" },
                  ]}
                />
              </Card>
            );
          })}
        </>
      ) : null}
    </div>
  );
}