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
  prevision: "prévision (pas encore de facture)",
};

// Écart atterrissage − prévision de référence : positif = au-dessus du repère.
function ecartTone(point: GasBudgetRevisePointV1) {
  if (point.prevision_reference <= 0) return "warn" as const;
  if (point.ecart_atterrissage_vs_prevision > 0) return "bad" as const;
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
        <span className="po2-eyebrow">Gaz TotalEnergies - atterrissage fixe / variable</span>
        <h1>Atterrissage gaz, par point de comptage</h1>
        <p>
          Marché Ville <strong>sans budget contractuel</strong> : le chiffre utile est l'<strong>atterrissage</strong>
          {" "}(réalisé à date + reste de l'année projeté). Chaque facture est décomposée en part fixe (abonnement,
          acheminement fixe, CTA) et part variable (conso × prix). Le reste de l'année est estimé par la conso
          attendue (corrigée du climat, DJU Sète) × prix de référence (fourniture révisée PEG). La
          {" "}<strong>« prévision de référence »</strong> (conso N-1 recalée) sert seulement de repère, ce n'est pas un
          budget. Lecture seule.
        </p>
      </header>

      <Card title="Période" eyebrow="année de l'atterrissage">
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
          <p className="po2-muted-line">Atterrissage indisponible : {errorMessage(query.error)}</p>
        </Card>
      ) : null}
      {query.isFetching && !data ? <p className="po2-muted-line">Chargement de l'atterrissage {year}...</p> : null}

      {data ? (
        <>
          <div className="po2-kpi-grid">
            <KpiCard label="Atterrissage" value={eur(data.totals.atterrissage)} detail={`${year} · réalisé + reste projeté`} />
            <KpiCard label="Réalisé à date" value={eur(data.totals.realise)} detail={`fixe ${eur(data.totals.realise_fixe)} · variable ${eur(data.totals.realise_variable)}`} />
            <KpiCard label="Prévision de référence" value={eur(data.totals.prevision_reference)} tone="neutral" detail="repère N-1 recalé (pas un budget)" />
            <KpiCard
              label="Écart / référence"
              value={eur(data.totals.ecart_atterrissage_vs_prevision)}
              tone={data.totals.ecart_atterrissage_vs_prevision > 0 ? "danger" : "good"}
              detail="atterrissage - prévision"
            />
          </div>

          <Card title="Par PCE" eyebrow="réalisé (fixe/variable) + reste projeté = atterrissage">
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
                    sortValue: (p) => p.nom_site ?? p.pce,
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
                    key: "realise",
                    header: "Réalisé à date",
                    sortValue: (p) => p.realise,
                    render: (p) => (
                      <div>
                        <strong>{eur(p.realise)}</strong>
                        <div className="po2-muted-line" style={{ fontSize: "0.72em", opacity: 0.7 }}>
                          fixe {eur(p.realise_fixe)} · var. {eur(p.realise_variable)} · {p.months_covered} mois
                        </div>
                      </div>
                    ),
                  },
                  {
                    key: "reste",
                    header: "Conso attendue an",
                    sortValue: (p) => p.conso_attendue_kwh,
                    render: (p) => (
                      <div>
                        {kwh(p.conso_attendue_kwh)}
                        {p.climate_ratio !== 1 || p.peg_ratio !== 1 ? (
                          <div className="po2-muted-line" style={{ fontSize: "0.72em", opacity: 0.7 }}>
                            climat ×{p.climate_ratio.toFixed(2)} · PEG ×{p.peg_ratio.toFixed(2)}
                          </div>
                        ) : null}
                      </div>
                    ),
                  },
                  { key: "atterrissage", header: "Atterrissage", sortValue: (p) => p.atterrissage, render: (p) => <strong>{eur(p.atterrissage)}</strong> },
                  { key: "prevision", header: "Prévision réf.", sortValue: (p) => p.prevision_reference, render: (p) => eur(p.prevision_reference) },
                  {
                    key: "ecart",
                    header: "Écart / réf.",
                    sortValue: (p) => p.ecart_atterrissage_vs_prevision,
                    render: (p) => <StatusBadge tone={ecartTone(p)}>{eur(p.ecart_atterrissage_vs_prevision)}</StatusBadge>,
                  },
                  { key: "method", header: "Méthode", sortValue: (p) => LANDING_METHOD_LABEL[p.landing_method] ?? p.landing_method, render: (p) => LANDING_METHOD_LABEL[p.landing_method] ?? p.landing_method },
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
