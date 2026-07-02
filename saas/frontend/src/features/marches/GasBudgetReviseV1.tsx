import { useState } from "react";
import { Card, DataTable, KpiCard, StatusBadge } from "../../design-system";
import type { GasBudgetRevisePointV1 } from "../../lib/api";
import { useGasBudgetReviseV1 } from "./useGasBudgetReviseV1";

function eur(value: number) {
  return value.toLocaleString("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
}

function kwh(value: number) {
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} kWh`;
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Une erreur est survenue.";
}

const LANDING_METHOD_LABEL: Record<string, string> = {
  dju: "réalisé + reste (DJU)",
  prorata: "réalisé + reste (pro-rata)",
  realise_complet: "réalisé (année close)",
  budget_revise: "budget révisé (pas de réalisé)",
};

// Écart atterrissage − budget : positif = dépassement du budget révisé.
function ecartTone(point: GasBudgetRevisePointV1) {
  if (point.budget_revise <= 0) return "warn" as const;
  if (point.ecart_atterrissage_vs_budget > 0) return "bad" as const;
  return "ok" as const;
}

export function GasBudgetReviseV1() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const query = useGasBudgetReviseV1(year);
  const data = query.data;

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">Marchés - budget révisé gaz (fixe / variable)</span>
        <h1>Budget révisé gaz, par point de comptage</h1>
        <p>
          Reconstitution <strong>fixe / variable</strong> par PCE (marché gaz TotalEnergies) : la part fixe
          (abonnement, acheminement fixe, CTA) et la part variable (<strong>conso attendue × prix de
          référence</strong>) sont calculées à partir des factures. La conso attendue est l'historique N-1
          corrigé du climat (DJU Sète) ; la fourniture est révisée par le PEG. On compare au réalisé et on
          projette l'atterrissage. Lecture seule.
        </p>
      </header>

      <Card title="Période" eyebrow="année de reconstitution">
        <div className="po2-matrix-import-form">
          <label>
            <span>Année</span>
            <input
              type="number"
              value={year}
              onChange={(event) => setYear(Number(event.currentTarget.value) || currentYear)}
            />
          </label>
        </div>
        {data ? (
          <p className="po2-muted-line">
            {data.pce_count} PCE · PEG {data.peg_available ? "appliqué" : "indisponible (prix tenu)"} · DJU{" "}
            {data.dju_available ? "appliqué" : "indisponible (conso tenue)"}
          </p>
        ) : null}
      </Card>

      {query.isError ? (
        <Card eyebrow="erreur">
          <p className="po2-muted-line">Budget révisé indisponible : {errorMessage(query.error)}</p>
        </Card>
      ) : null}
      {query.isFetching && !data ? <p className="po2-muted-line">Chargement du budget révisé {year}...</p> : null}

      {data ? (
        <>
          <div className="po2-kpi-grid">
            <KpiCard label="Budget révisé" value={eur(data.totals.budget_revise)} detail={`${year} · ${data.pce_count} PCE`} />
            <KpiCard label="dont part fixe" value={eur(data.totals.fixe_budget)} tone="neutral" detail="abo, ATRD/ATRT fixe, CTA" />
            <KpiCard label="dont part variable" value={eur(data.totals.variable_budget)} tone="info" detail="conso attendue × prix réf." />
            <KpiCard label="Réalisé à date" value={eur(data.totals.realise)} detail="factures gaz de l'année" />
            <KpiCard label="Atterrissage" value={eur(data.totals.atterrissage)} detail="réalisé + reste projeté" />
            <KpiCard
              label="Écart / budget"
              value={eur(data.totals.ecart_atterrissage_vs_budget)}
              tone={data.totals.ecart_atterrissage_vs_budget > 0 ? "danger" : "good"}
              detail="atterrissage - budget révisé"
            />
          </div>

          <Card title="Par PCE" eyebrow="fixe + variable = budget révisé, vs réalisé et atterrissage">
            {data.points.length === 0 ? (
              <p className="po2-muted-line">Aucune facture gaz sur {year - 1}/{year} : importe d'abord les factures TotalEnergies.</p>
            ) : (
              <DataTable
                rows={data.points}
                getRowKey={(p) => p.pce}
                columns={[
                  {
                    key: "pce",
                    header: "PCE / site",
                    render: (p) => (
                      <div>
                        <strong>{p.nom_site ?? p.pce}</strong>
                        <div className="po2-muted-line" style={{ fontSize: "0.72em", opacity: 0.7 }}>
                          {p.pce}
                          {!p.has_history ? " · sans historique N-1" : ""}
                        </div>
                      </div>
                    ),
                  },
                  {
                    key: "conso",
                    header: "Conso attendue",
                    render: (p) => (
                      <div>
                        {kwh(p.conso_attendue_kwh)}
                        {p.climate_ratio !== 1 ? (
                          <div className="po2-muted-line" style={{ fontSize: "0.72em", opacity: 0.7 }}>
                            climat ×{p.climate_ratio.toFixed(2)} · PEG ×{p.peg_ratio.toFixed(2)}
                          </div>
                        ) : null}
                      </div>
                    ),
                  },
                  { key: "fixe", header: "Part fixe", render: (p) => eur(p.fixe_budget) },
                  { key: "variable", header: "Part variable", render: (p) => eur(p.variable_budget) },
                  { key: "budget", header: "Budget révisé", render: (p) => <strong>{eur(p.budget_revise)}</strong> },
                  { key: "realise", header: "Réalisé", render: (p) => eur(p.realise) },
                  { key: "landing", header: "Atterrissage", render: (p) => eur(p.atterrissage) },
                  {
                    key: "ecart",
                    header: "Écart / budget",
                    render: (p) => <StatusBadge tone={ecartTone(p)}>{eur(p.ecart_atterrissage_vs_budget)}</StatusBadge>,
                  },
                  { key: "method", header: "Méthode", render: (p) => LANDING_METHOD_LABEL[p.landing_method] ?? p.landing_method },
                ]}
              />
            )}
            <p className="po2-muted-line">{data.source_note}</p>
          </Card>
        </>
      ) : null}
    </div>
  );
}
