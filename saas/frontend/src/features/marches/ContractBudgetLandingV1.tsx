import { useState } from "react";
import { Card, DataTable, KpiCard, StatusBadge } from "../../design-system";
import type { ContractBudgetPosteV1 } from "../../lib/api";
import { useContractBudgetLandingV1 } from "./useContractBudgetV1";

function eur(value: number) {
  return value.toLocaleString("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Une erreur est survenue.";
}

// Écart réalisé − budget : négatif en cours d'année est normal (facturation étalée).
function ecartTone(poste: ContractBudgetPosteV1) {
  if (poste.budget_contractuel <= 0) return "warn" as const;
  if (poste.ecart_realise_vs_budget > 0) return "bad" as const; // dépassement du contractuel
  return "ok" as const;
}

const LANDING_METHOD_LABEL: Record<string, string> = {
  contractuel_revise: "contractuel révisé",
  contractuel_fixe: "contractuel (sans révision)",
  prorata: "pro-rata (budget inconnu)",
  nul: "—",
};

export function ContractBudgetLandingV1() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [lot, setLot] = useState<number | null>(null);

  const landing = useContractBudgetLandingV1(year, lot);
  const data = landing.data;

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">Marchés - atterrissage budget contractuel</span>
        <h1>Budget contractuel vs réalisé, par poste (CPE DALKIA)</h1>
        <p>
          Le budget de référence n'est pas une saisie prévisionnelle Ville mais le montant
          <strong> contractuel</strong> (prévu DPGF DALKIA) <strong>révisé</strong> par le coefficient de
          révision trimestriel : par poste (P1 / P2 / P3 / P3.4), on compare au réalisé (factures CPE) et on
          projette l'atterrissage. À ne pas confondre avec l'intéressement (moteur DJU).
        </p>
      </header>

      <Card title="Périmètre" eyebrow="année et lot contractuel">
        <div className="po2-matrix-import-form">
          <label>
            <span>Année</span>
            <input
              type="number"
              value={year}
              onChange={(event) => setYear(Number(event.currentTarget.value) || currentYear)}
            />
          </label>
          <label>
            <span>Lot</span>
            <select value={lot ?? ""} onChange={(event) => setLot(event.currentTarget.value ? Number(event.currentTarget.value) : null)}>
              <option value="">Les deux lots (cumulé)</option>
              <option value="1">Lot 1</option>
              <option value="2">Lot 2 (piscines)</option>
            </select>
          </label>
        </div>
        {data && data.contract_codes.length > 0 ? (
          <p className="po2-muted-line">Contrats : {data.contract_codes.join(", ")}</p>
        ) : null}
      </Card>

      {landing.isError ? (
        <Card eyebrow="erreur">
          <p className="po2-muted-line">Atterrissage indisponible : {errorMessage(landing.error)}</p>
        </Card>
      ) : null}
      {landing.isFetching && !data ? <p className="po2-muted-line">Chargement de l'atterrissage {year}...</p> : null}

      {data ? (
        <>
          <div className="po2-kpi-grid">
            <KpiCard label="Budget base (DPGF)" value={eur(data.totals.budget_base)} detail={`${year} - avant révision`} />
            <KpiCard
              label="Budget contractuel révisé"
              value={eur(data.totals.budget_contractuel)}
              tone={data.totals.budget_contractuel > data.totals.budget_base ? "info" : "neutral"}
              detail={`+ ${eur(data.totals.budget_contractuel - data.totals.budget_base)} de révision`}
            />
            <KpiCard label="Réalisé (factures CPE)" value={eur(data.totals.realise)} detail={`${data.year_progress_percent.toFixed(0)}% de l'année écoulée`} />
            <KpiCard label="Atterrissage" value={eur(data.totals.atterrissage)} detail="projection fin d'année (révisée)" />
            <KpiCard
              label="Reste à facturer"
              value={eur(data.totals.reste_a_facturer)}
              tone={data.totals.reste_a_facturer > 0 ? "good" : "danger"}
              detail="budget révisé - réalisé"
            />
          </div>

          <Card title="Par poste" eyebrow="budget contractuel vs réalisé vs atterrissage">
            {data.postes.length === 0 ? (
              <p className="po2-muted-line">Aucun poste pour {year} : vérifie les références DPGF et les factures CPE.</p>
            ) : (
              <DataTable
                rows={data.postes}
                getRowKey={(p) => p.poste}
                columns={[
                  { key: "poste", header: "Poste", render: (p) => <strong>{p.label}</strong> },
                  { key: "base", header: "Budget base (DPGF)", render: (p) => eur(p.budget_base) },
                  {
                    key: "coef",
                    header: "Coef. révision",
                    render: (p) => (p.coefficient_revision !== 1 ? p.coefficient_revision.toFixed(4) : "—"),
                  },
                  { key: "budget", header: "Budget révisé", render: (p) => <strong>{eur(p.budget_contractuel)}</strong> },
                  { key: "realise", header: "Réalisé", render: (p) => eur(p.realise) },
                  { key: "landing", header: "Atterrissage", render: (p) => eur(p.atterrissage) },
                  { key: "reste", header: "Reste à facturer", render: (p) => eur(p.reste_a_facturer) },
                  {
                    key: "ecart",
                    header: "Écart réalisé/budget",
                    render: (p) => <StatusBadge tone={ecartTone(p)}>{eur(p.ecart_realise_vs_budget)}</StatusBadge>,
                  },
                  {
                    key: "taux",
                    header: "Taux fact.",
                    render: (p) => (p.taux_facturation != null ? `${(p.taux_facturation * 100).toFixed(0)}%` : "-"),
                  },
                  { key: "method", header: "Méthode", render: (p) => LANDING_METHOD_LABEL[p.landing_method] ?? p.landing_method },
                ]}
              />
            )}
            <p className="po2-muted-line">{data.source_note}</p>
          </Card>

          <Card title="Projection par opération comptable" eyebrow="axe matrice (hybride)">
            {data.by_operation.length === 0 ? (
              <p className="po2-muted-line">{data.projection_note}</p>
            ) : (
              <>
                <DataTable
                  rows={data.by_operation}
                  getRowKey={(r) => r.operation_number}
                  columns={[
                    { key: "operation", header: "Opération", render: (r) => <strong>{r.operation_number}</strong> },
                    { key: "postes", header: "Postes", render: (r) => r.postes.join(", ") },
                    { key: "budget", header: "Budget contractuel", render: (r) => eur(r.budget_contractuel) },
                    { key: "realise", header: "Réalisé", render: (r) => eur(r.realise) },
                    { key: "landing", header: "Atterrissage", render: (r) => eur(r.atterrissage) },
                  ]}
                />
                <p className="po2-muted-line">{data.projection_note}</p>
              </>
            )}
          </Card>
        </>
      ) : null}
    </div>
  );
}
