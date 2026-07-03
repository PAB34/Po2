import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, DataTable, KpiCard, StatusBadge } from "../../design-system";
import { fetchCpeAtterrissage, type CpeAtterrissageItem } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

function eur(value: number | null | undefined) {
  if (value == null) return "—";
  return value.toLocaleString("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
}

function mwh(value: number | null | undefined) {
  if (value == null) return "—";
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} MWh`;
}

function pct(part: number | null | undefined, total: number | null | undefined) {
  if (part == null || !total) return "—";
  return `${Math.round((part / total) * 100)} %`;
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Une erreur est survenue.";
}

const RESULT_LABEL: Record<string, string> = {
  interessement: "Intéressement",
  penalite: "Pénalité",
  equilibre: "Équilibre",
  insuffisant: "Données insuffisantes",
};

// Intéressement = DALKIA facture la collectivité (conso sous la cible) ; pénalité = avoir en faveur
// de la collectivité (conso au-dessus). On colore côté « impact collectivité ».
function resultTone(type: string | null) {
  if (type === "penalite") return "ok" as const;
  if (type === "interessement") return "warn" as const;
  return "neutral" as const;
}

function currentQuarter() {
  return Math.floor(new Date().getMonth() / 3) + 1;
}

export function CpeCibleConsoV1() {
  const { token } = useAuth();
  const currentYear = new Date().getFullYear();
  const [annee, setAnnee] = useState(currentYear);
  const [trimestre, setTrimestre] = useState(currentQuarter());

  const query = useQuery({
    queryKey: ["cpe-atterrissage", annee, trimestre],
    enabled: Boolean(token),
    queryFn: () => fetchCpeAtterrissage(token!, annee, trimestre),
  });
  const data = query.data;

  const items = data?.items ?? [];
  const totalCible = items.reduce((s, i) => s + (i.nb_exercice ?? 0), 0);
  const totalRealise = items.reduce((s, i) => s + (i.nc_realise ?? 0), 0);
  const projectionAvailable = (data?.nb_sites_projetes ?? 0) > 0;

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">DALKIA CPE - cible consommation</span>
        <h1>Cible conso & intéressement (gaz), par site</h1>
        <p>
          Calque comparatif <strong>cible vs réalisé</strong> sur les sites CPE DALKIA : consommation cible
          contractuelle (<strong>NB</strong>) face à la consommation <strong>réalisée à date</strong>
          {" "}(<strong>NC</strong>). Quand les DJU DALKIA sont disponibles, on projette la fin d'année
          (N'B / NC projetés) et l'<strong>intéressement</strong> (conso sous la cible) ou la
          {" "}<strong>pénalité</strong> (au-dessus). Lecture seule. <em>Cible élec (IPMVP) : incrément suivant.</em>
        </p>
      </header>

      <Card title="Période" eyebrow="année + trimestre écoulé">
        <div className="po2-matrix-import-form" style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          <label>
            <span>Année</span>
            <input type="number" value={annee} onChange={(e) => setAnnee(Number(e.currentTarget.value) || currentYear)} />
          </label>
          <label>
            <span>Trimestre réalisé</span>
            <select value={trimestre} onChange={(e) => setTrimestre(Number(e.currentTarget.value))}>
              <option value={1}>T1</option>
              <option value={2}>T2</option>
              <option value={3}>T3</option>
              <option value={4}>T4</option>
            </select>
          </label>
        </div>
        {data ? (
          <p className="po2-muted-line">
            {items.length} sites · {projectionAvailable ? `${data.nb_sites_projetes} projetés` : "projection indisponible"}
            {" · "}DJU projeté {data.dju_projete_annuel.toLocaleString("fr-FR")} / réf. {data.dju_reference.toLocaleString("fr-FR")}
          </p>
        ) : null}
      </Card>

      {query.isError ? (
        <Card eyebrow="erreur">
          <p className="po2-muted-line">Calque indisponible : {errorMessage(query.error)}</p>
        </Card>
      ) : null}
      {query.isFetching && !data ? <p className="po2-muted-line">Chargement du calque {annee}...</p> : null}

      {data ? (
        <>
          {!projectionAvailable && items.length > 0 ? (
            <Card eyebrow="projection indisponible">
              <p className="po2-muted-line">
                ⚠ L'intéressement/pénalité <strong>projeté</strong> n'est pas calculable sur cet environnement :
                les <strong>DJU DALKIA</strong> (Montpellier) ne sont pas chargés (données climatiques absentes).
                Le tableau montre la <strong>cible NB</strong> et la <strong>conso réalisée à date</strong> ; les
                colonnes projetées s'afficheront dès que les DJU seront disponibles.
              </p>
            </Card>
          ) : null}

          <div className="po2-kpi-grid">
            <KpiCard label="Cible totale (NB)" value={mwh(totalCible)} detail={`${items.length} sites · ${annee}`} tone="neutral" />
            <KpiCard label="Réalisé à date (NC)" value={mwh(totalRealise)} detail={`fin T${trimestre} · ${pct(totalRealise, totalCible)} de la cible`} tone="neutral" />
            <KpiCard
              label="Net intéressement projeté"
              value={projectionAvailable ? eur(data.net_projete) : "—"}
              detail={projectionAvailable ? "intéressement − pénalité" : "DJU DALKIA requis"}
              tone={projectionAvailable ? (data.net_projete > 0 ? "danger" : "good") : "neutral"}
            />
            <KpiCard label="Pénalité projetée" value={projectionAvailable ? eur(data.total_penalite_projete) : "—"} detail="conso au-dessus cible" tone="neutral" />
          </div>

          <Card title="Par site" eyebrow="cible NB vs conso réalisée (NC) → projection intéressement / pénalité">
            {items.length === 0 ? (
              <p className="po2-muted-line">
                Aucun site sur {annee} : relevés de conso ou cibles NB manquants pour cet exercice.
              </p>
            ) : (
              <DataTable
                rows={items}
                getRowKey={(r: CpeAtterrissageItem) => r.site_id}
                columns={[
                  {
                    key: "site",
                    header: "Site",
                    sortValue: (r) => r.nom_site ?? r.code_site,
                    render: (r) => (
                      <div>
                        <strong>{r.nom_site ?? r.code_site}</strong>
                        <div className="po2-muted-line" style={{ fontSize: "0.72em", opacity: 0.7 }}>
                          {r.code_site}
                          {r.tarif ? ` · ${r.tarif}` : ""}
                          {r.mois_realises ? ` · ${r.mois_realises} mois` : ""}
                        </div>
                      </div>
                    ),
                  },
                  { key: "nb", header: "Cible NB (an)", sortValue: (r) => r.nb_exercice, render: (r) => mwh(r.nb_exercice) },
                  { key: "nc", header: "Réalisé à date (NC)", sortValue: (r) => r.nc_realise, render: (r) => mwh(r.nc_realise) },
                  { key: "pct", header: "% cible", sortValue: (r) => (r.nb_exercice ? (r.nc_realise ?? 0) / r.nb_exercice : -1), render: (r) => pct(r.nc_realise, r.nb_exercice) },
                  { key: "nprimeb", header: "N'B projeté", sortValue: (r) => r.n_prime_b_projete, render: (r) => mwh(r.n_prime_b_projete) },
                  { key: "ncp", header: "NC projeté", sortValue: (r) => r.nc_projete, render: (r) => mwh(r.nc_projete) },
                  {
                    key: "type",
                    header: "Projection",
                    sortValue: (r) => r.type_resultat,
                    render: (r) =>
                      r.type_resultat ? (
                        <StatusBadge tone={resultTone(r.type_resultat)}>{RESULT_LABEL[r.type_resultat] ?? "—"}</StatusBadge>
                      ) : (
                        <span className="po2-muted-line" style={{ fontSize: "0.8em", opacity: 0.6 }}>—</span>
                      ),
                  },
                  { key: "montant", header: "Montant projeté", sortValue: (r) => r.montant_ht_projete, render: (r) => <strong>{eur(r.montant_ht_projete)}</strong> },
                ]}
              />
            )}
            <p className="po2-muted-line">
              NB = cible annuelle contractuelle ; NC = conso constatée. Projection (colonnes N'B / NC projetés,
              intéressement) : pro-rata DJU (extrapolation climatique) depuis le réalisé jusqu'à fin T{trimestre},
              modèle pur-DJU indicatif. Intéressement = facture DALKIA à la collectivité ; pénalité = avoir en sa faveur.
            </p>
          </Card>
        </>
      ) : null}
    </div>
  );
}
