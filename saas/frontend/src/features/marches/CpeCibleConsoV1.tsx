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

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">DALKIA CPE - cible consommation</span>
        <h1>Cible conso & intéressement (gaz), par site</h1>
        <p>
          Calque comparatif <strong>cible vs réalisé</strong> sur les sites CPE DALKIA : consommation cible
          contractuelle (<strong>NB</strong>), recalée du climat (<strong>N'B projeté</strong>), face à la
          consommation projetée de fin d'année (<strong>NC projeté</strong>). L'écart déclenche un
          <strong> intéressement</strong> (conso sous la cible) ou une <strong>pénalité</strong> (au-dessus),
          projetés via la formule contractuelle. Projection pro-rata DJU depuis le réalisé à date — indicatif.
          Lecture seule. <em>Cible élec (IPMVP) : incrément suivant.</em>
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
            {data.nb_sites_projetes} sites projetés · DJU projeté annuel {data.dju_projete_annuel.toLocaleString("fr-FR")} /
            réf. {data.dju_reference.toLocaleString("fr-FR")} · méthode {data.dju_method}
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
          <div className="po2-kpi-grid">
            <KpiCard label="Net projeté" value={eur(data.net_projete)} detail="intéressement − pénalité" tone={data.net_projete > 0 ? "danger" : "good"} />
            <KpiCard label="Intéressement projeté" value={eur(data.total_interessement_projete)} detail="conso sous la cible" tone="neutral" />
            <KpiCard label="Pénalité projetée" value={eur(data.total_penalite_projete)} detail="conso au-dessus de la cible" tone="neutral" />
            <KpiCard label="Sites projetés" value={String(data.nb_sites_projetes)} detail={`${annee} · fin T${trimestre}`} tone="neutral" />
          </div>

          <Card title="Par site" eyebrow="cible (NB / N'B) vs conso projetée (NC) → intéressement / pénalité">
            {data.items.length === 0 ? (
              <p className="po2-muted-line">
                Aucun site projetable sur {annee} (T{trimestre}) : relevés ou cibles NB manquants.
              </p>
            ) : (
              <DataTable
                rows={data.items}
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
                          {r.statut ? ` · ${r.statut}` : ""}
                        </div>
                      </div>
                    ),
                  },
                  { key: "nb", header: "NB (cible)", sortValue: (r) => r.nb_exercice, render: (r) => mwh(r.nb_exercice) },
                  { key: "nprimeb", header: "N'B projeté", sortValue: (r) => r.n_prime_b_projete, render: (r) => mwh(r.n_prime_b_projete) },
                  { key: "nc", header: "NC projeté", sortValue: (r) => r.nc_projete, render: (r) => mwh(r.nc_projete) },
                  { key: "ecart", header: "Écart (N'B−NC)", sortValue: (r) => r.ecart_projete, render: (r) => mwh(r.ecart_projete) },
                  {
                    key: "type",
                    header: "Type",
                    sortValue: (r) => r.type_resultat,
                    render: (r) => <StatusBadge tone={resultTone(r.type_resultat)}>{RESULT_LABEL[r.type_resultat ?? ""] ?? "—"}</StatusBadge>,
                  },
                  { key: "montant", header: "Montant projeté", sortValue: (r) => r.montant_ht_projete, render: (r) => <strong>{eur(r.montant_ht_projete)}</strong> },
                ]}
              />
            )}
            <p className="po2-muted-line">
              Projection pro-rata DJU (extrapolation climatique) depuis le réalisé jusqu'à fin T{trimestre}.
              Modèle pur-DJU indicatif — à caler sur le tableau DALKIA. Intéressement = facture DALKIA à la
              collectivité ; pénalité = avoir en faveur de la collectivité.
            </p>
          </Card>
        </>
      ) : null}
    </div>
  );
}
