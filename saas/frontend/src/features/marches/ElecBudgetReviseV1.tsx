import { useState, type ReactNode } from "react";
import { Card, DataTable, KpiCard, SegmentControl, StatusBadge } from "../../design-system";
import type { EngieBudgetReviseAggregateV1, EngieBudgetRevisePointV1 } from "../../lib/api";
import { useElecBudgetReviseV1, type ElecSupplier } from "./useElecBudgetReviseV1";

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
  mensuel: "réalisé + reste (conso mensuelle)",
  realise_complet: "réalisé (année close)",
  prevision: "prévision (pas encore de facture)",
};

const CONSO_METHOD_LABEL: Record<string, string> = {
  thermo: "ENEDIS + DJU (thermosensible)",
  enedis_flat: "ENEDIS N-1 (tenu)",
  no_enedis: "sans ENEDIS (kWh facturés N-1)",
  photoperiod: "ENEDIS N-1 + photopériode",
  photoperiod_n1: "N-1 factures + photopériode",
};

type SupplierConfig = {
  eyebrow: string;
  title: string;
  intro: ReactNode;
  showDalkiaOverlay: boolean;
};

const CONFIG: Record<ElecSupplier, SupplierConfig> = {
  ENGIE: {
    eyebrow: "ENGIE électricité - atterrissage fixe / variable",
    title: "Atterrissage électricité ENGIE, par point de livraison (PRM)",
    showDalkiaOverlay: true,
    intro: (
      <>
        Marché de fourniture (tous les PRM facturés ENGIE). Le chiffre utile est l'
        <strong>atterrissage</strong> (réalisé à date + reste de l'année projeté). Chaque facture est
        décomposée en part <strong>fixe</strong> (gestion, comptage, soutirage fixe, CTA, abonnement) et
        part <strong>variable</strong> (conso × prix). La conso attendue vient d'ENEDIS, corrigée du climat
        sur la seule part thermosensible (chauffage/clim), et les prix de référence sont révisés par le BPU
        (fourniture) et le TURPE (acheminement). La <strong>« prévision de référence »</strong> (conso N-1
        recalée) est un repère, pas un budget. Lecture seule.
      </>
    ),
  },
  EDF: {
    eyebrow: "EDF éclairage public - atterrissage fixe / variable",
    title: "Atterrissage éclairage public EDF, par point de livraison (PRM)",
    showDalkiaOverlay: false,
    intro: (
      <>
        Marché de fourniture EDF (éclairage public + petits sites). Le chiffre utile est l'
        <strong>atterrissage</strong> (réalisé à date + reste de l'année projeté). Chaque facture est
        décomposée en part <strong>fixe</strong> (acheminement fixe, CTA, abonnement) et part{" "}
        <strong>variable</strong> (conso × prix). L'éclairage public n'étant <strong>pas thermosensible</strong>,
        la conso attendue reconduit le N-1 et se répartit sur l'année selon la <strong>photopériode</strong>
        {" "}(heures de nuit, plus l'hiver). Prix de référence révisés par le BPU (fourniture) et le TURPE
        (acheminement). La <strong>« prévision de référence »</strong> est un repère, pas un budget. Lecture seule.
      </>
    ),
  },
};

// Écart atterrissage − prévision de référence : positif = au-dessus du repère.
function ecartTone(point: EngieBudgetRevisePointV1) {
  if (point.prevision_reference <= 0) return "warn" as const;
  if (point.ecart_atterrissage_vs_prevision > 0) return "bad" as const;
  return "ok" as const;
}

type Maille = "regroupement" | "prm";

function aggregateColumns() {
  return [
    { key: "label", header: "Regroupement", render: (r: EngieBudgetReviseAggregateV1) => (
        <div>
          <strong>{r.label}</strong>
          <div className="po2-muted-line" style={{ fontSize: "0.72em", opacity: 0.7 }}>{r.prm_count} PRM</div>
        </div>
      ), sortValue: (r: EngieBudgetReviseAggregateV1) => r.label },
    { key: "prevision", header: "Prévision réf.", render: (r: EngieBudgetReviseAggregateV1) => eur(r.prevision_reference), sortValue: (r: EngieBudgetReviseAggregateV1) => r.prevision_reference },
    { key: "realise", header: "Réalisé à date", render: (r: EngieBudgetReviseAggregateV1) => eur(r.realise), sortValue: (r: EngieBudgetReviseAggregateV1) => r.realise },
    { key: "atterrissage", header: "Atterrissage", render: (r: EngieBudgetReviseAggregateV1) => <strong>{eur(r.atterrissage)}</strong>, sortValue: (r: EngieBudgetReviseAggregateV1) => r.atterrissage },
  ];
}

export function ElecBudgetReviseV1({ supplier }: { supplier: ElecSupplier }) {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [maille, setMaille] = useState<Maille>("regroupement");
  const query = useElecBudgetReviseV1(supplier, year);
  const data = query.data;
  const cfg = CONFIG[supplier];

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">{cfg.eyebrow}</span>
        <h1>{cfg.title}</h1>
        <p>{cfg.intro}</p>
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
            {data.prm_count} PRM · ENEDIS {data.enedis_available ? "appliqué" : "indisponible (conso tenue)"} ·
            {" "}BPU {data.bpu_available ? "appliqué" : "tenu (N-1)"} · TURPE{" "}
            {data.turpe_available ? "appliqué" : "tenu (N-1)"}
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
          {data.anomaly_prm_count > 0 ? (
            <Card eyebrow="fiabilité des données">
              <p className="po2-muted-line">
                ⚠ <strong>{data.anomaly_prm_count} PRM</strong> présentent une anomalie d'import (poste
                « soutirage variable » facturé à un prix unitaire aberrant). Le montant est <strong>corrigé</strong>
                {" "}(reconstitué sur la valeur mal placée) et le PRM est <strong>signalé</strong> dans le détail
                Bâtiment/PRM. À réimporter après correction du parser pour lever le signalement.
              </p>
            </Card>
          ) : null}

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

          {cfg.showDalkiaOverlay ? (
            <Card title="Cible DALKIA" eyebrow="prochain incrément — calque comparatif">
              <p className="po2-muted-line">
                À venir : pour les sites sous cible DALKIA (conso objectif, intéressement/pénalités — y compris
                sans P1 fourniture), un calque comparera la <strong>conso cible</strong> à la conso attendue et au
                réalisé. Ça ne change pas le calcul du coût ci-dessous (prévisionnel neutre sur tous les PRM).
              </p>
            </Card>
          ) : null}

          <Card
            title="Atterrissage"
            eyebrow="réalisé (fixe/variable) + reste projeté"
            action={
              <SegmentControl
                value={maille}
                options={[
                  { value: "regroupement", label: "Regroupement" },
                  { value: "prm", label: "Bâtiment/PRM" },
                ]}
                onChange={setMaille}
              />
            }
          >
            {data.points.length === 0 ? (
              <p className="po2-muted-line">
                Aucune facture {supplier} sur {year - 1}/{year} : importe d'abord les factures {supplier}.
              </p>
            ) : maille === "regroupement" ? (
              <DataTable
                rows={data.regroupements}
                getRowKey={(r) => String(r.key ?? "non-regroupe")}
                columns={aggregateColumns()}
              />
            ) : (
              <DataTable
                rows={data.points}
                getRowKey={(p) => p.prm}
                columns={[
                  {
                    key: "prm",
                    header: "Bâtiment / PRM",
                    sortValue: (p) => p.building_name ?? p.site_name ?? p.prm,
                    render: (p) => (
                      <div>
                        <strong>{p.building_name ?? p.site_name ?? p.prm}</strong>
                        <div className="po2-muted-line" style={{ fontSize: "0.72em", opacity: 0.7 }}>
                          {p.prm}
                          {p.segment ? ` · ${p.segment}` : ""}
                          {p.regroupement ? ` · ${p.regroupement}` : ""}
                          {p.building_id === null ? " · non rattaché" : ""}
                          {p.has_anomaly ? " · ⚠ anomalie import" : ""}
                          {!p.has_history ? " · sans historique" : ""}
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
                    key: "conso",
                    header: "Conso attendue an",
                    sortValue: (p) => p.conso_attendue_kwh,
                    render: (p) => (
                      <div>
                        {kwh(p.conso_attendue_kwh)}
                        <div className="po2-muted-line" style={{ fontSize: "0.72em", opacity: 0.7 }}>
                          {CONSO_METHOD_LABEL[p.conso_method] ?? p.conso_method}
                          {p.thermo_share > 0 ? ` · thermo ${Math.round(p.thermo_share * 100)} %` : ""}
                        </div>
                      </div>
                    ),
                  },
                  {
                    key: "prix",
                    header: "Prix réf.",
                    sortValue: (p) => p.pu_variable_eur_kwh,
                    render: (p) => (
                      <div>
                        {p.pu_variable_eur_kwh.toLocaleString("fr-FR", { maximumFractionDigits: 4 })} €/kWh
                        {p.bpu_ratio !== 1 || p.turpe_ratio !== 1 ? (
                          <div className="po2-muted-line" style={{ fontSize: "0.72em", opacity: 0.7 }}>
                            BPU ×{p.bpu_ratio.toFixed(2)} · TURPE ×{p.turpe_ratio.toFixed(2)}
                          </div>
                        ) : (
                          <div className="po2-muted-line" style={{ fontSize: "0.72em", opacity: 0.7 }}>tenu N-1</div>
                        )}
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
                  { key: "method", header: "Méthode", sortValue: (p) => p.landing_method, render: (p) => LANDING_METHOD_LABEL[p.landing_method] ?? p.landing_method },
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
