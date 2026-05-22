import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CpeBilanAnnuel,
  CpeSiteBilanItem,
  calculerCpeBilan,
  fetchCpeBilan,
  fetchCpeDju,
  importCpeCsv,
  upsertCpePrixGaz,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

const CURRENT_YEAR = new Date().getFullYear();
const MOIS_LABELS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"];

const TYPE_LABEL: Record<string, string> = {
  interessement: "Intéressement",
  penalite: "Pénalité",
  equilibre: "Équilibre",
  insuffisant: "—",
};
const TYPE_CLASS: Record<string, string> = {
  interessement: "badge-green",
  penalite: "badge-red",
  equilibre: "badge-gray",
  insuffisant: "badge-gray",
};
const STATUT_CLASS: Record<string, string> = {
  partiel: "badge-orange",
  calcule: "badge-blue",
  valide: "badge-green",
  conteste: "badge-red",
};
const CATEGORIE_LABEL: Record<string, string> = {
  ENS: "Enseignement",
  SPORT: "Sport",
  BAM: "Administratif",
  CULT: "Culture",
  CCAS: "CCAS",
};

function fmt(val: number | null | undefined, decimals = 1): string {
  if (val == null) return "—";
  return val.toFixed(decimals).replace(".", ",");
}
function fmtEur(val: number | null | undefined): string {
  if (val == null) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(val);
}

export default function CpeDalkiaPage() {
  const { token } = useAuth();
  const qc = useQueryClient();
  const [annee, setAnnee] = useState(CURRENT_YEAR);
  const [filterCat, setFilterCat] = useState<string>("tous");
  const [showPuForm, setShowPuForm] = useState(false);
  const [puInput, setPuInput] = useState("");
  const [importMsg, setImportMsg] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const bilanQ = useQuery({
    queryKey: ["cpe-bilan", annee],
    queryFn: () => fetchCpeBilan(token!, annee),
    enabled: !!token,
  });

  const djuQ = useQuery({
    queryKey: ["cpe-dju", annee],
    queryFn: () => fetchCpeDju(token!, annee),
    enabled: !!token,
  });

  const calculerM = useMutation({
    mutationFn: () => calculerCpeBilan(token!, annee),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cpe-bilan", annee] }),
  });

  const puM = useMutation({
    mutationFn: (pu: number) => upsertCpePrixGaz(token!, { annee, pu_eur_mwh_pci: pu }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cpe-bilan", annee] });
      setShowPuForm(false);
      setPuInput("");
    },
  });

  const importM = useMutation({
    mutationFn: (file: File) => importCpeCsv(token!, file),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["cpe-bilan", annee] });
      setImportMsg(
        `Import terminé : ${res.nb_inseres} insérés, ${res.nb_mis_a_jour} mis à jour, ${res.nb_erreurs} erreurs.` +
          (res.sites_inconnus.length > 0 ? ` Sites inconnus : ${res.sites_inconnus.join(", ")}.` : "") +
          (res.erreurs.length > 0 ? ` Premières erreurs : ${res.erreurs.slice(0, 3).join(" | ")}` : "")
      );
    },
  });

  const bilan: CpeBilanAnnuel | undefined = bilanQ.data;
  const dju = djuQ.data;

  // prix_tarifs depuis le bilan (T1/T2/T3 pré-chargés par OS N°3)
  const prixTarifs = bilan?.prix_tarifs ?? {};
  const prixT2 = prixTarifs["T2"] ?? null;

  const filteredSites: CpeSiteBilanItem[] =
    bilan?.sites.filter((s) => filterCat === "tous" || s.site.categorie === filterCat) ?? [];

  const categories = ["tous", "ENS", "SPORT", "BAM", "CULT", "CCAS"];

  return (
    <div style={{ maxWidth: 1200 }}>
      {/* ── En-tête ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        <div style={{ flex: 1 }}>
          <h2 style={{ margin: 0 }}>CPE DALKIA — Bilan énergétique</h2>
          <p style={{ margin: "4px 0 0", color: "#6b7280", fontSize: 14 }}>
            Contrat de Performance Énergétique — Lot 1 Bâtiments communaux — Ville de Sète
          </p>
        </div>
        <select
          value={annee}
          onChange={(e) => setAnnee(Number(e.target.value))}
          style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #d1d5db" }}
        >
          {[2026, 2027, 2028, 2029, 2030].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* ── Cartes KPI ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        <KpiCard
          label="DJU réels"
          value={dju ? `${fmt(dju.dju_total, 0)} DJU` : "—"}
          sub={`Réf. contractuelle : 1 426 DJU`}
          color={dju && dju.dju_total < 1426 ? "#f97316" : "#16a34a"}
        />
        <KpiCard
          label="Prix gaz (OS N°3)"
          value={prixT2 ? `T2 : ${fmt(prixT2, 2)} €/MWhPCI` : "Non renseigné"}
          sub={
            Object.keys(prixTarifs).length > 0
              ? `T1 : ${fmt(prixTarifs["T1"], 2)} • T3 : ${fmt(prixTarifs["T3"], 2)} €/MWhPCI`
              : "Lancer seed_cpe_prix_gaz.py"
          }
          color={prixT2 ? "#2563eb" : "#9ca3af"}
          action={
            <button
              type="button"
              className="secondary-button"
              style={{ fontSize: 12, padding: "2px 8px" }}
              onClick={() => setShowPuForm(true)}
            >
              Saisie manuelle
            </button>
          }
        />
        <KpiCard
          label="Intéressement potentiel"
          value={bilan ? fmtEur(bilan.total_interessement_ht) : "—"}
          sub={`${bilan?.nb_sites_complets ?? 0} / ${bilan?.nb_sites_actifs ?? 0} sites complets`}
          color="#16a34a"
        />
        <KpiCard
          label="Pénalités potentielles"
          value={bilan ? fmtEur(bilan.total_penalite_ht) : "—"}
          sub={
            bilan && bilan.solde_ht > 0
              ? `Solde net : ${fmtEur(bilan.solde_ht)} (faveur Ville)`
              : bilan && bilan.solde_ht < 0
              ? `Solde net : ${fmtEur(Math.abs(bilan.solde_ht))} (à charge Ville)`
              : "Solde : équilibré"
          }
          color="#ef4444"
        />
      </div>

      {/* ── Formulaire Prix gaz (saisie manuelle post-2030 ou correction) ── */}
      {showPuForm && (
        <div className="card" style={{ marginBottom: 16, padding: 16, background: "#f0f9ff" }}>
          <strong>Saisie manuelle du prix gaz {annee}</strong>
          <p style={{ fontSize: 13, color: "#6b7280", margin: "4px 0 12px" }}>
            Pour 2026-2030 : prix fixe OS N°3 — utiliser <code>seed_cpe_prix_gaz.py</code> plutôt que ce formulaire.
            Pour 2031+ : issu du décompte définitif P1 DALKIA (15/02/N+1). Valeur en €/MWhPCI.
          </p>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="number"
              step="0.01"
              placeholder="Pu €/MWhPCI"
              value={puInput}
              onChange={(e) => setPuInput(e.target.value)}
              style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db", width: 160 }}
            />
            <button
              type="button"
              className="primary-button"
              disabled={!puInput || puM.isPending}
              onClick={() => puM.mutate(parseFloat(puInput.replace(",", ".")))}
            >
              Enregistrer (global)
            </button>
            <button type="button" className="secondary-button" onClick={() => setShowPuForm(false)}>
              Annuler
            </button>
          </div>
        </div>
      )}

      {/* ── Actions ── */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center" }}>
        <button
          type="button"
          className="primary-button"
          onClick={() => calculerM.mutate()}
          disabled={calculerM.isPending}
        >
          {calculerM.isPending ? "Calcul en cours…" : "Recalculer le bilan"}
        </button>

        <button
          type="button"
          className="secondary-button"
          onClick={() => fileRef.current?.click()}
          disabled={importM.isPending}
        >
          {importM.isPending ? "Import en cours…" : "Importer CSV DALKIA"}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.txt"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) {
              setImportMsg(null);
              importM.mutate(f);
            }
            e.target.value = "";
          }}
        />

        <Link to="/cpe/releves" className="secondary-button" style={{ textDecoration: "none" }}>
          Saisie manuelle
        </Link>

        {importMsg && (
          <span style={{ fontSize: 13, color: importM.isError ? "#ef4444" : "#16a34a" }}>{importMsg}</span>
        )}
      </div>

      {/* ── Filtre catégorie ── */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {categories.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setFilterCat(c)}
            style={{
              padding: "4px 12px",
              borderRadius: 20,
              border: "1px solid",
              borderColor: filterCat === c ? "#2563eb" : "#d1d5db",
              background: filterCat === c ? "#2563eb" : "white",
              color: filterCat === c ? "white" : "#374151",
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            {c === "tous" ? "Tous" : CATEGORIE_LABEL[c] ?? c}
          </button>
        ))}
      </div>

      {/* ── Tableau des sites ── */}
      {bilanQ.isLoading ? (
        <p>Chargement…</p>
      ) : bilanQ.isError ? (
        <p style={{ color: "#ef4444" }}>Erreur de chargement. Vérifiez que la base est migrée.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f9fafb", borderBottom: "2px solid #e5e7eb" }}>
                <th style={thStyle}>Code</th>
                <th style={thStyle}>Site</th>
                <th style={{ ...thStyle, textAlign: "center" }}>Tarif</th>
                <th style={thStyle}>NB (MWhPCI)</th>
                <th style={thStyle}>N'B corrigé</th>
                <th style={thStyle}>NC réel</th>
                <th style={thStyle}>Écart</th>
                <th style={thStyle}>Résultat</th>
                <th style={thStyle}>Montant HT</th>
                <th style={thStyle}>Mois</th>
                <th style={thStyle}>Statut</th>
              </tr>
            </thead>
            <tbody>
              {filteredSites.length === 0 ? (
                <tr>
                  <td colSpan={11} style={{ textAlign: "center", padding: 32, color: "#9ca3af" }}>
                    Aucun site. Lancez le seed des sites CPE (scripts/seed_cpe_sites.py).
                  </td>
                </tr>
              ) : (
                filteredSites.map((item) => (
                  <SiteRow key={item.site.id} item={item} />
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Totaux ── */}
      {bilan && filteredSites.length > 0 && (
        <div style={{ marginTop: 16, display: "flex", gap: 24, fontSize: 14, color: "#374151" }}>
          <span>
            Sites affichés : <strong>{filteredSites.length}</strong>
          </span>
          <span>
            Intéressement filtré :{" "}
            <strong style={{ color: "#16a34a" }}>
              {fmtEur(filteredSites.reduce((s, i) => s + (i.type_resultat === "interessement" ? (i.montant_ht ?? 0) : 0), 0))}
            </strong>
          </span>
          <span>
            Pénalités filtrées :{" "}
            <strong style={{ color: "#ef4444" }}>
              {fmtEur(filteredSites.reduce((s, i) => s + (i.type_resultat === "penalite" ? (i.montant_ht ?? 0) : 0), 0))}
            </strong>
          </span>
        </div>
      )}

      {/* ── Note DJU ── */}
      {dju && (
        <div style={{ marginTop: 24, padding: 12, background: "#f9fafb", borderRadius: 8, fontSize: 12, color: "#6b7280" }}>
          <strong>DJU {annee} :</strong> {fmt(dju.dju_total, 0)} DJU chauffage base 18°C (méthode COSTIC, Open-Meteo) •{" "}
          {dju.nb_jours} jours collectés • Référence contractuelle : 1 426 DJU (Montpellier 1981-2010)
          {dju.dju_total < 1426 ? (
            <span style={{ color: "#f97316" }}> → Hiver doux : N'B sera inférieur à NB</span>
          ) : (
            <span style={{ color: "#16a34a" }}> → Hiver rigoureux : N'B sera supérieur à NB</span>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sous-composants ───────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  sub,
  color,
  action,
}: {
  label: string;
  value: string;
  sub: string;
  color: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <p style={{ margin: 0, fontSize: 12, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {label}
      </p>
      <p style={{ margin: "6px 0 4px", fontSize: 20, fontWeight: 700, color }}>{value}</p>
      <p style={{ margin: 0, fontSize: 12, color: "#9ca3af" }}>{sub}</p>
      {action && <div style={{ marginTop: 8 }}>{action}</div>}
    </div>
  );
}

function SiteRow({ item }: { item: CpeSiteBilanItem }) {
  const ecartPct = item.ecart != null && item.n_prime_b ? (item.ecart / item.n_prime_b) * 100 : null;

  return (
    <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
      <td style={tdStyle}>
        <code style={{ fontSize: 11, color: "#6b7280" }}>{item.site.code_site}</code>
      </td>
      <td style={{ ...tdStyle, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        <Link to={`/cpe/sites/${item.site.id}`} style={{ color: "#2563eb", textDecoration: "none" }}>
          {item.site.nom_site}
        </Link>
      </td>
      <td style={{ ...tdStyle, textAlign: "center" }}>
        {item.site.tarif ? (
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              padding: "2px 6px",
              borderRadius: 4,
              background: item.site.tarif === "T1" ? "#fef3c7" : item.site.tarif === "T3" ? "#f0fdf4" : "#eff6ff",
              color: item.site.tarif === "T1" ? "#92400e" : item.site.tarif === "T3" ? "#166534" : "#1d4ed8",
            }}
          >
            {item.site.tarif}
          </span>
        ) : (
          <span style={{ color: "#9ca3af", fontSize: 11 }}>—</span>
        )}
      </td>
      <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(item.site.nb_mwh_pci)}</td>
      <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(item.n_prime_b)}</td>
      <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(item.nc_cumul)}</td>
      <td style={{ ...tdStyle, textAlign: "right" }}>
        {item.ecart != null ? (
          <span style={{ color: item.ecart > 0 ? "#16a34a" : "#ef4444", fontWeight: 600 }}>
            {item.ecart > 0 ? "+" : ""}
            {fmt(item.ecart)} ({ecartPct != null ? `${ecartPct > 0 ? "+" : ""}${fmt(ecartPct, 0)}%` : "—"})
          </span>
        ) : (
          "—"
        )}
      </td>
      <td style={tdStyle}>
        {item.type_resultat ? (
          <span className={`badge ${TYPE_CLASS[item.type_resultat] ?? "badge-gray"}`}>
            {TYPE_LABEL[item.type_resultat] ?? item.type_resultat}
          </span>
        ) : (
          <span className="badge badge-gray">Incomplet</span>
        )}
      </td>
      <td style={{ ...tdStyle, textAlign: "right", fontWeight: item.montant_ht ? 600 : 400 }}>
        {item.montant_ht != null ? (
          <span style={{ color: item.type_resultat === "interessement" ? "#16a34a" : "#ef4444" }}>
            {fmtEur(item.montant_ht)}
          </span>
        ) : (
          "—"
        )}
      </td>
      <td style={{ ...tdStyle, textAlign: "center" }}>
        <span style={{ color: item.nb_mois_releves < 12 ? "#f97316" : "#16a34a" }}>
          {item.nb_mois_releves}/12
        </span>
      </td>
      <td style={tdStyle}>
        <span className={`badge ${STATUT_CLASS[item.statut] ?? "badge-gray"}`}>{item.statut}</span>
      </td>
    </tr>
  );
}

const thStyle: React.CSSProperties = {
  padding: "10px 12px",
  textAlign: "left",
  fontSize: 12,
  fontWeight: 600,
  color: "#6b7280",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const tdStyle: React.CSSProperties = {
  padding: "10px 12px",
  verticalAlign: "middle",
};
