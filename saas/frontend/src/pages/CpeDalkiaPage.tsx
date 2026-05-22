import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CpeBilanAnnuel,
  CpeFinanceImportBatch,
  CpeFinanceImportBatchDetail,
  CpeFinanceLine,
  CpeFinancePreview,
  CpeSiteBilanItem,
  calculerCpeBilan,
  fetchCpeBilan,
  fetchCpeDju,
  fetchCpeFinanceImport,
  fetchCpeFinanceImports,
  fetchCpeFinanceLines,
  importCpeCsv,
  importCpeFinanceExport,
  previewCpeFinanceExport,
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

type CpeView = "cockpit" | "performance";

const CPE_WORKSTREAMS = [
  {
    code: "P1",
    title: "Fourniture gaz",
    scope: "Acomptes, decompte definitif, quantites QT, prix unitaire et pieces fournisseur.",
    control: "Comparer les factures DALKIA au tarif contractuel, aux volumes retenus et aux preuves GRDF.",
    status: "Socle a creer",
    statusClass: "badge-orange",
  },
  {
    code: "P2",
    title: "Exploitation et maintenance",
    scope: "P2.1 a P2.4, revision des prix, obligations d'entretien et sensibilisation.",
    control: "Verifier les revisions, les echeances, les livrables et l'effet des objectifs P2.4.",
    status: "Socle a creer",
    statusClass: "badge-orange",
  },
  {
    code: "P3",
    title: "Garantie totale",
    scope: "P3.1 a P3.4, renouvellement, compte P3 et travaux programmes.",
    control: "Suivre les montants factures, le compte P3, les interventions et les penalites associees.",
    status: "Socle a creer",
    statusClass: "badge-orange",
  },
  {
    code: "ENERGIE",
    title: "Performance et consommations",
    scope: "Releves DALKIA, futures donnees GRDF, DJU, cibles NB/N'B/NC.",
    control: "Mesurer les ecarts, l'interessement potentiel et les penalites energetiques.",
    status: "Deja engage",
    statusClass: "badge-green",
  },
] as const;

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
  const [showCsvHelp, setShowCsvHelp] = useState(false);
  const [puInput, setPuInput] = useState("");
  const [importMsg, setImportMsg] = useState<string | null>(null);
  const [financePreview, setFinancePreview] = useState<CpeFinancePreview | null>(null);
  const [selectedFinanceBatchId, setSelectedFinanceBatchId] = useState<number | null>(null);
  const [financeLineStatus, setFinanceLineStatus] = useState<string>("all");
  const [financeLineMarket, setFinanceLineMarket] = useState<string>("all");
  const [financeImportMsg, setFinanceImportMsg] = useState<string | null>(null);
  const [view, setView] = useState<CpeView>("cockpit");
  const fileRef = useRef<HTMLInputElement>(null);
  const financeFileRef = useRef<HTMLInputElement>(null);
  const financeImportFileRef = useRef<HTMLInputElement>(null);

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

  const financeImportsQ = useQuery({
    queryKey: ["cpe-finance-imports"],
    queryFn: () => fetchCpeFinanceImports(token!),
    enabled: !!token,
  });

  const financeBatchQ = useQuery({
    queryKey: ["cpe-finance-import", selectedFinanceBatchId],
    queryFn: () => fetchCpeFinanceImport(token!, selectedFinanceBatchId as number),
    enabled: !!token && selectedFinanceBatchId !== null,
  });

  const financeLinesQ = useQuery({
    queryKey: ["cpe-finance-lines", selectedFinanceBatchId, financeLineStatus, financeLineMarket],
    queryFn: () =>
      fetchCpeFinanceLines(token!, selectedFinanceBatchId as number, {
        siteValidationStatus: financeLineStatus === "all" ? undefined : financeLineStatus,
        market: financeLineMarket === "all" ? undefined : financeLineMarket,
        limit: 100,
      }),
    enabled: !!token && selectedFinanceBatchId !== null,
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

  const financePreviewM = useMutation({
    mutationFn: (file: File) => previewCpeFinanceExport(token!, file),
    onSuccess: setFinancePreview,
  });

  const financeImportM = useMutation({
    mutationFn: (file: File) => importCpeFinanceExport(token!, file),
    onSuccess: (batch) => {
      setSelectedFinanceBatchId(batch.id);
      setFinanceImportMsg(
        `Lot ${batch.id} importe : ${batch.imported_line_count} ligne(s) CPE, ${batch.invoice_count} facture(s).`
      );
      qc.invalidateQueries({ queryKey: ["cpe-finance-imports"] });
      qc.invalidateQueries({ queryKey: ["cpe-finance-import", batch.id] });
      qc.invalidateQueries({ queryKey: ["cpe-finance-lines", batch.id] });
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

  useEffect(() => {
    if (selectedFinanceBatchId === null && financeImportsQ.data?.[0]) {
      setSelectedFinanceBatchId(financeImportsQ.data[0].id);
    }
  }, [financeImportsQ.data, selectedFinanceBatchId]);

  return (
    <div style={{ maxWidth: 1200 }}>
      {/* ── En-tête ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        <div style={{ flex: 1 }}>
          <h2 style={{ margin: 0 }}>CPE DALKIA</h2>
          <p style={{ margin: "4px 0 0", color: "#6b7280", fontSize: 14 }}>
            Pilotage contractuel, consommations et performance energetique du Lot 1
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

      <div
        role="tablist"
        aria-label="Vues CPE"
        style={{ display: "flex", gap: 8, marginBottom: 20, borderBottom: "1px solid #e5e7eb", paddingBottom: 12 }}
      >
        <CpeViewTab active={view === "cockpit"} onClick={() => setView("cockpit")}>
          Cockpit CPE
        </CpeViewTab>
        <CpeViewTab active={view === "performance"} onClick={() => setView("performance")}>
          Performance et consommations
        </CpeViewTab>
      </div>

      {view === "cockpit" && (
        <CpeCockpit
          annee={annee}
          bilan={bilan}
          djuTotal={dju?.dju_total ?? null}
          prixT2={prixT2}
          financePreview={financePreview}
          financePreviewPending={financePreviewM.isPending}
          financePreviewError={financePreviewM.error instanceof Error ? financePreviewM.error.message : null}
          financeFileRef={financeFileRef}
          financeImportFileRef={financeImportFileRef}
          financeImports={financeImportsQ.data ?? []}
          financeImportsPending={financeImportsQ.isLoading}
          selectedFinanceBatchId={selectedFinanceBatchId}
          financeBatch={financeBatchQ.data}
          financeBatchPending={financeBatchQ.isLoading}
          financeLines={financeLinesQ.data ?? []}
          financeLinesPending={financeLinesQ.isLoading}
          financeLineStatus={financeLineStatus}
          financeLineMarket={financeLineMarket}
          financeImportPending={financeImportM.isPending}
          financeImportError={financeImportM.error instanceof Error ? financeImportM.error.message : null}
          financeImportMsg={financeImportMsg}
          onFinanceFile={(file) => financePreviewM.mutate(file)}
          onFinanceImport={(file) => {
            setFinanceImportMsg(null);
            financeImportM.mutate(file);
          }}
          onFinanceBatchChange={setSelectedFinanceBatchId}
          onFinanceLineStatusChange={setFinanceLineStatus}
          onFinanceLineMarketChange={setFinanceLineMarket}
          onOpenPerformance={() => setView("performance")}
        />
      )}

      {view === "performance" && (
        <>
          <div style={{ marginBottom: 16 }}>
            <h3 style={{ margin: "0 0 4px" }}>Performance et consommations</h3>
            <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>
              Suivi des consommations gaz DALKIA, cibles contractuelles et calcul des ecarts energetiques.
            </p>
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

        <div style={{ position: "relative", display: "inline-block" }}>
          <button
            type="button"
            className="secondary-button"
            onClick={() => fileRef.current?.click()}
            disabled={importM.isPending}
            title="Format attendu : fichier CSV DALKIA mensuel (avant le 5e jour ouvrable). Colonnes : code_site ; date_releve ; qt_mwh_pci ; volume_ecs_m3 ; etat_chauffe"
          >
            {importM.isPending ? "Import en cours…" : "Importer CSV DALKIA"}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.txt,.xls,.xlsx"
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
        </div>

        <button
          type="button"
          className="secondary-button"
          onClick={() => setShowCsvHelp((v) => !v)}
          title="Voir le format attendu du fichier CSV"
        >
          ? Format CSV
        </button>

        {importMsg && (
          <span style={{ fontSize: 13, color: importM.isError ? "#ef4444" : "#16a34a" }}>{importMsg}</span>
        )}
      </div>

      {/* ── Aide format CSV ── */}
      {showCsvHelp && (
        <div className="card" style={{ marginBottom: 16, padding: 16, background: "#fffbeb", fontSize: 13 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <strong>Format du fichier CSV DALKIA</strong>
            <button type="button" className="secondary-button" style={{ fontSize: 11, padding: "2px 8px" }} onClick={() => setShowCsvHelp(false)}>✕</button>
          </div>
          <p style={{ margin: "8px 0 4px", color: "#6b7280" }}>
            DALKIA envoie ce fichier avant le <strong>5e jour ouvrable de chaque mois</strong>. Colonnes séparées par <code>;</code> (ou virgule/tabulation — détecté automatiquement) :
          </p>
          <pre style={{ background: "#f9fafb", padding: 10, borderRadius: 6, fontSize: 12, overflow: "auto", margin: "8px 0" }}>
{`code_site;date_releve;qt_mwh_pci;volume_ecs_m3;etat_chauffe
VDS-ENS 02;2026-01-31;11.3;3.2;O
VDS-SPORT 03;2026-01-31;9.8;;O
VDS-BAM 02;2026-01-31;6.1;;N`}
          </pre>
          <ul style={{ margin: "4px 0", paddingLeft: 18, color: "#374151", lineHeight: 1.7 }}>
            <li><code>code_site</code> — obligatoire, ex : <code>VDS-ENS 02</code>, <code>VDS-SPORT 03</code>, <code>CCAS 04</code></li>
            <li><code>qt_mwh_pci</code> — consommation gaz mensuelle en MWhPCI (ou colonnes <code>consommation_gaz</code> / <code>qt</code>)</li>
            <li><code>volume_ecs_m3</code> — volume ECS mensuel en m³ (optionnel)</li>
            <li><code>etat_chauffe</code> — O/N ou 1/0 (optionnel)</li>
            <li><code>date_releve</code> — formats acceptés : <code>2026-01-31</code>, <code>01/2026</code>, <code>2026-01</code> — ou colonnes séparées <code>annee</code> + <code>mois</code></li>
          </ul>
          <p style={{ margin: "8px 0 0", color: "#9ca3af", fontSize: 12 }}>
            Si vous n'avez pas encore reçu de fichier DALKIA, utilisez la saisie manuelle en cliquant sur le nom d'un site dans le tableau ci-dessous.
          </p>
        </div>
      )}

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
        </>
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

function CpeViewTab({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      className={active ? "primary-button" : "secondary-button"}
      onClick={onClick}
      style={{ minHeight: 36 }}
    >
      {children}
    </button>
  );
}

function CpeCockpit({
  annee,
  bilan,
  djuTotal,
  prixT2,
  financePreview,
  financePreviewPending,
  financePreviewError,
  financeFileRef,
  financeImportFileRef,
  financeImports,
  financeImportsPending,
  selectedFinanceBatchId,
  financeBatch,
  financeBatchPending,
  financeLines,
  financeLinesPending,
  financeLineStatus,
  financeLineMarket,
  financeImportPending,
  financeImportError,
  financeImportMsg,
  onFinanceFile,
  onFinanceImport,
  onFinanceBatchChange,
  onFinanceLineStatusChange,
  onFinanceLineMarketChange,
  onOpenPerformance,
}: {
  annee: number;
  bilan: CpeBilanAnnuel | undefined;
  djuTotal: number | null;
  prixT2: number | null;
  financePreview: CpeFinancePreview | null;
  financePreviewPending: boolean;
  financePreviewError: string | null;
  financeFileRef: React.RefObject<HTMLInputElement>;
  financeImportFileRef: React.RefObject<HTMLInputElement>;
  financeImports: CpeFinanceImportBatch[];
  financeImportsPending: boolean;
  selectedFinanceBatchId: number | null;
  financeBatch: CpeFinanceImportBatchDetail | undefined;
  financeBatchPending: boolean;
  financeLines: CpeFinanceLine[];
  financeLinesPending: boolean;
  financeLineStatus: string;
  financeLineMarket: string;
  financeImportPending: boolean;
  financeImportError: string | null;
  financeImportMsg: string | null;
  onFinanceFile: (file: File) => void;
  onFinanceImport: (file: File) => void;
  onFinanceBatchChange: (batchId: number | null) => void;
  onFinanceLineStatusChange: (value: string) => void;
  onFinanceLineMarketChange: (value: string) => void;
  onOpenPerformance: () => void;
}) {
  return (
    <>
      <section style={{ marginBottom: 24 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 16 }}>
          <KpiCard label="Exercice" value={String(annee)} sub="Suivi annuel CPE" color="#111827" />
          <KpiCard
            label="Sites actifs"
            value={String(bilan?.nb_sites_actifs ?? 0)}
            sub={`${bilan?.nb_sites_complets ?? 0} avec une annee complete`}
            color="#2563eb"
          />
          <KpiCard
            label="DJU mesures"
            value={djuTotal == null ? "A verifier" : `${fmt(djuTotal, 0)} DJU`}
            sub="Reference contractuelle : 1 426 DJU"
            color="#0f766e"
          />
          <KpiCard
            label="Prix gaz T2"
            value={prixT2 == null ? "A renseigner" : `${fmt(prixT2, 2)} EUR/MWhPCI`}
            sub="Point d'entree du controle P1"
            color="#9333ea"
          />
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-end", marginBottom: 12 }}>
          <div>
            <h3 style={{ margin: "0 0 4px" }}>Decoupage de controle</h3>
            <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>
              Les postes factures et le controle de performance doivent rester suivis separement.
            </p>
          </div>
          <button type="button" className="secondary-button" onClick={onOpenPerformance}>
            Ouvrir le suivi energie
          </button>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f9fafb", borderBottom: "2px solid #e5e7eb" }}>
                <th style={thStyle}>Poste</th>
                <th style={thStyle}>Perimetre</th>
                <th style={thStyle}>Controle attendu</th>
                <th style={thStyle}>Statut</th>
              </tr>
            </thead>
            <tbody>
              {CPE_WORKSTREAMS.map((item) => (
                <tr key={item.code} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ ...tdStyle, minWidth: 180 }}>
                    <strong>{item.code}</strong>
                    <div style={{ color: "#6b7280", marginTop: 2 }}>{item.title}</div>
                  </td>
                  <td style={{ ...tdStyle, minWidth: 280 }}>{item.scope}</td>
                  <td style={{ ...tdStyle, minWidth: 300 }}>{item.control}</td>
                  <td style={tdStyle}>
                    <span className={`badge ${item.statusClass}`}>{item.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-end", marginBottom: 12 }}>
          <div>
            <h3 style={{ margin: "0 0 4px" }}>Export finances DALKIA</h3>
            <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>
              Apercu du CSV de l'espace client avant de creer le registre de factures CPE.
            </p>
          </div>
          <div>
            <button
              type="button"
              className="primary-button"
              onClick={() => financeFileRef.current?.click()}
              disabled={financePreviewPending}
            >
              {financePreviewPending ? "Analyse..." : "Analyser l'export"}
            </button>
            <input
              ref={financeFileRef}
              type="file"
              accept=".csv,.txt"
              style={{ display: "none" }}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onFinanceFile(file);
                event.target.value = "";
              }}
            />
          </div>
        </div>

        {financePreviewError && <p style={{ color: "#dc2626", margin: "0 0 12px" }}>{financePreviewError}</p>}

        {financePreview && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 16 }}>
              <KpiCard
                label="Lignes export"
                value={financePreview.nb_lignes.toLocaleString("fr-FR")}
                sub={`${financePreview.nb_factures} facture(s), ${financePreview.nb_contrats} contrat(s)`}
                color="#111827"
              />
              <KpiCard
                label="Montant HT export"
                value={fmtEur(financePreview.montant_ht)}
                sub={`${financePreview.nb_lignes_p1_p2_p3} ligne(s) P1/P2/P3`}
                color="#2563eb"
              />
              <KpiCard
                label="Sites CPE detectes"
                value={financePreview.nb_sites_cpe_distincts.toLocaleString("fr-FR")}
                sub={`${financePreview.nb_lignes_code_site_cpe} ligne(s) avec code VDS/CCAS`}
                color="#0f766e"
              />
              <KpiCard
                label="Conso / releves"
                value={`${financePreview.nb_lignes_consommation} / ${financePreview.nb_lignes_index_releve}`}
                sub="Lignes avec consommation / index"
                color="#9333ea"
              />
            </div>

            {financePreview.alertes.length > 0 && (
              <div style={{ marginBottom: 16, padding: 12, background: "#fff7ed", borderRadius: 6, color: "#9a3412", fontSize: 13 }}>
                {financePreview.alertes.map((warning) => (
                  <p key={warning} style={{ margin: "0 0 4px" }}>{warning}</p>
                ))}
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))", gap: 16 }}>
              <FinanceMarketTable title="Marches trouves" rows={financePreview.marches} />
              <FinanceContractTable rows={financePreview.contrats} />
            </div>
          </>
        )}
      </section>

      <section style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-end", marginBottom: 12 }}>
          <div>
            <h3 style={{ margin: "0 0 4px" }}>Lots finances CPE importes</h3>
            <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>
              Le registre conserve uniquement les lignes P1/P2/P3 du contrat DALKIA cible C00190116O.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {financeImports.length > 0 && (
              <select
                value={selectedFinanceBatchId ?? ""}
                onChange={(event) => onFinanceBatchChange(event.target.value ? Number(event.target.value) : null)}
                aria-label="Lot finances DALKIA"
                style={{ padding: "7px 10px", borderRadius: 6, border: "1px solid #d1d5db", minWidth: 210 }}
              >
                {financeImports.map((batch) => (
                  <option key={batch.id} value={batch.id}>
                    Lot {batch.id} - {batch.imported_line_count} lignes - {batch.original_filename}
                  </option>
                ))}
              </select>
            )}
            <button
              type="button"
              className="primary-button"
              onClick={() => financeImportFileRef.current?.click()}
              disabled={financeImportPending}
            >
              {financeImportPending ? "Import..." : "Importer le lot CPE"}
            </button>
            <input
              ref={financeImportFileRef}
              type="file"
              accept=".csv,.txt"
              style={{ display: "none" }}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onFinanceImport(file);
                event.target.value = "";
              }}
            />
          </div>
        </div>

        {financeImportsPending && <p style={{ color: "#6b7280" }}>Chargement des lots finances...</p>}
        {financeImportError && <p style={{ color: "#dc2626", margin: "0 0 12px" }}>{financeImportError}</p>}
        {financeImportMsg && <p style={{ color: "#166534", margin: "0 0 12px" }}>{financeImportMsg}</p>}
        {!financeImportsPending && financeImports.length === 0 && (
          <div className="card" style={{ padding: 16, color: "#4b5563", fontSize: 14 }}>
            Aucun lot importe. Analysez l'export si besoin, puis importez-le pour ouvrir le controle P1.
          </div>
        )}

        {financeBatchPending && <p style={{ color: "#6b7280" }}>Lecture du lot selectionne...</p>}
        {financeBatch && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 16 }}>
              <KpiCard
                label="Lignes retenues"
                value={financeBatch.imported_line_count.toLocaleString("fr-FR")}
                sub={`${financeBatch.ignored_line_count.toLocaleString("fr-FR")} ligne(s) hors contrat ou marche`}
                color="#111827"
              />
              <KpiCard
                label="Factures DALKIA"
                value={financeBatch.invoice_count.toLocaleString("fr-FR")}
                sub={`Contrat ${financeBatch.target_contract_code}`}
                color="#2563eb"
              />
              <KpiCard
                label="Rapprochement auto"
                value={financeBatch.matched_site_line_count.toLocaleString("fr-FR")}
                sub="Lignes rattachees a un site CPE connu"
                color="#0f766e"
              />
              <KpiCard
                label="A identifier"
                value={(financeBatch.unknown_site_line_count + financeBatch.missing_site_code_line_count).toLocaleString("fr-FR")}
                sub={`${financeBatch.unknown_site_line_count} code(s) inconnu(s), ${financeBatch.missing_site_code_line_count} sans code`}
                color="#c2410c"
              />
            </div>

            <FinanceP1Summary summary={financeBatch.p1} />

            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-end", margin: "18px 0 10px" }}>
              <div>
                <h4 style={{ margin: "0 0 4px", fontSize: 15 }}>Rapprochement lignes DALKIA / sites CPE</h4>
                <p style={{ margin: 0, color: "#6b7280", fontSize: 13 }}>
                  Affichage limite aux 100 premieres lignes du filtre courant.
                </p>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <select
                  value={financeLineMarket}
                  onChange={(event) => onFinanceLineMarketChange(event.target.value)}
                  aria-label="Filtre marche finances CPE"
                  style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db" }}
                >
                  <option value="all">Tous postes</option>
                  <option value="P1">P1</option>
                  <option value="P2">P2</option>
                  <option value="P3">P3</option>
                </select>
                <select
                  value={financeLineStatus}
                  onChange={(event) => onFinanceLineStatusChange(event.target.value)}
                  aria-label="Filtre rapprochement sites CPE"
                  style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db" }}
                >
                  <option value="all">Tous statuts</option>
                  <option value="auto_matched">Rattaches</option>
                  <option value="site_unknown">Code inconnu</option>
                  <option value="site_code_missing">Sans code site</option>
                </select>
              </div>
            </div>

            {financeLinesPending ? (
              <p style={{ color: "#6b7280" }}>Chargement des lignes...</p>
            ) : (
              <FinanceLineTable rows={financeLines} />
            )}
          </>
        )}
      </section>

      <section style={{ marginBottom: 16 }}>
        <h3 style={{ margin: "0 0 12px" }}>Prochain socle fonctionnel</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
          <ControlBlock
            title="Factures CPE"
            detail="Importer ou saisir une facture par poste P1, P2 ou P3, son exercice, sa periode et son montant."
          />
          <ControlBlock
            title="Preuves de controle"
            detail="Rattacher revisions d'indices, livrables DALKIA, releves GRDF et calculs de cible au controle."
          />
          <ControlBlock
            title="Ecarts et suites"
            detail="Qualifier l'ecart en clarification, contestation, avoir attendu, penalite ou validation."
          />
        </div>
      </section>
    </>
  );
}

function FinanceMarketTable({ title, rows }: { title: string; rows: CpeFinancePreview["marches"] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>{title}</h4>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
            <th style={thStyle}>Code</th>
            <th style={thStyle}>Lignes</th>
            <th style={thStyle}>Factures</th>
            <th style={thStyle}>HT</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.code} style={{ borderBottom: "1px solid #f3f4f6" }}>
              <td style={tdStyle}>{row.code}</td>
              <td style={{ ...tdStyle, textAlign: "right" }}>{row.nb_lignes.toLocaleString("fr-FR")}</td>
              <td style={{ ...tdStyle, textAlign: "right" }}>{row.nb_factures.toLocaleString("fr-FR")}</td>
              <td style={{ ...tdStyle, textAlign: "right" }}>{fmtEur(row.montant_ht)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FinanceContractTable({ rows }: { rows: CpeFinancePreview["contrats"] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>Contrats trouves</h4>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
            <th style={thStyle}>Contrat</th>
            <th style={thStyle}>Marches</th>
            <th style={thStyle}>Periode</th>
            <th style={thStyle}>Lignes</th>
            <th style={thStyle}>Sites</th>
            <th style={thStyle}>Conso</th>
            <th style={thStyle}>HT</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.code_contrat} style={{ borderBottom: "1px solid #f3f4f6" }}>
              <td style={{ ...tdStyle, minWidth: 140 }}>
                <strong>{row.code_contrat}</strong>
                {row.libelle_contrat && <div style={{ color: "#6b7280" }}>{row.libelle_contrat}</div>}
              </td>
              <td style={tdStyle}>{row.marches.join(", ")}</td>
              <td style={{ ...tdStyle, minWidth: 150 }}>
                {row.periode_debut_min ?? "-"} au {row.periode_fin_max ?? "-"}
              </td>
              <td style={{ ...tdStyle, textAlign: "right" }}>{row.nb_lignes.toLocaleString("fr-FR")}</td>
              <td style={{ ...tdStyle, textAlign: "right" }}>{row.nb_sites_cpe_distincts.toLocaleString("fr-FR")}</td>
              <td style={{ ...tdStyle, textAlign: "right" }}>{row.nb_lignes_consommation.toLocaleString("fr-FR")}</td>
              <td style={{ ...tdStyle, textAlign: "right" }}>{fmtEur(row.montant_ht)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FinanceP1Summary({ summary }: { summary: CpeFinanceImportBatchDetail["p1"] }) {
  const acomptes = summary.types_facture.find((row) => row.code === "AC");
  const decomptes = summary.types_facture.find((row) => row.code === "DE");

  return (
    <div>
      <div style={{ marginBottom: 10 }}>
        <h4 style={{ margin: "0 0 4px", fontSize: 15 }}>Premiere ouverture du controle P1</h4>
        <p style={{ margin: 0, color: "#6b7280", fontSize: 13 }}>
          Acomptes, decomptes, accessoires P1 et preparation du rapprochement GRDF sont lus depuis les lignes persistees.
        </p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 12, marginBottom: 14 }}>
        <KpiCard
          label="P1 HT"
          value={fmtEur(summary.montant_ht)}
          sub={`${summary.nb_lignes} ligne(s), ${summary.nb_factures} facture(s)`}
          color="#111827"
        />
        <KpiCard
          label="Acomptes AC"
          value={fmtEur(acomptes?.montant_ht)}
          sub={`${acomptes?.nb_factures ?? 0} facture(s) detectee(s)`}
          color="#2563eb"
        />
        <KpiCard
          label="Decomptes DE"
          value={fmtEur(decomptes?.montant_ht)}
          sub={`${decomptes?.nb_factures ?? 0} facture(s) detectee(s)`}
          color="#0f766e"
        />
        <KpiCard
          label="Rapprochement GRDF"
          value={`${summary.nb_sites_cpe_avec_pce}/${summary.nb_sites_cpe_rapproches}`}
          sub={`${summary.nb_lignes_consommation} ligne(s) conso, ${summary.nb_lignes_index_releve} ligne(s) index`}
          color="#9333ea"
        />
      </div>
      <div style={{ marginBottom: 12, padding: 12, background: "#f9fafb", borderRadius: 6, color: "#4b5563", fontSize: 13 }}>
        Prix gaz : les tarifs OS N3 du CPE restent le referentiel de controle. Les postes accessoires P1 apparaissent ci-dessous
        et {summary.nb_lignes_site_a_reconcilier} ligne(s) P1 demandent encore un rattachement site avant le controle GRDF.
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))", gap: 16 }}>
        <FinanceMarketTable title="Types de facture P1" rows={summary.types_facture} />
        <FinanceMarketTable title="Postes factures P1" rows={summary.postes_factures} />
      </div>
    </div>
  );
}

function FinanceLineTable({ rows }: { rows: CpeFinanceLine[] }) {
  if (rows.length === 0) {
    return <div className="card" style={{ padding: 16, color: "#6b7280" }}>Aucune ligne pour ce filtre.</div>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
            <th style={thStyle}>Facture</th>
            <th style={thStyle}>Poste</th>
            <th style={thStyle}>Ligne DALKIA</th>
            <th style={thStyle}>Code detecte</th>
            <th style={thStyle}>Site CPE</th>
            <th style={thStyle}>Validation</th>
            <th style={thStyle}>HT</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
              <td style={{ ...tdStyle, minWidth: 132 }}>
                <strong>{row.invoice.invoice_number}</strong>
                <div style={{ color: "#6b7280" }}>{row.invoice.invoice_type ?? "-"}</div>
              </td>
              <td style={tdStyle}>
                <strong>{row.market}</strong>
                <div style={{ color: "#6b7280" }}>{row.billed_item ?? "-"}</div>
              </td>
              <td style={{ ...tdStyle, minWidth: 260 }}>
                <div>{row.sold_service ?? "-"}</div>
                <div style={{ color: "#6b7280", marginTop: 2 }}>{row.prestation_detail ?? "-"}</div>
              </td>
              <td style={tdStyle}>{row.detected_site_code ?? "-"}</td>
              <td style={{ ...tdStyle, minWidth: 170 }}>
                {row.cpe_site ? (
                  <>
                    <strong>{row.cpe_site.code_site}</strong>
                    <div style={{ color: "#6b7280" }}>{row.cpe_site.nom_site}</div>
                  </>
                ) : (
                  "-"
                )}
              </td>
              <td style={tdStyle}>
                <span className={`badge ${financeLineStatusClass(row.site_validation_status)}`}>
                  {financeLineStatusLabel(row.site_validation_status)}
                </span>
              </td>
              <td style={{ ...tdStyle, textAlign: "right", whiteSpace: "nowrap" }}>{fmtEur(row.amount_ht)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function financeLineStatusLabel(status: string): string {
  if (status === "auto_matched") return "Rattache auto";
  if (status === "site_unknown") return "Code inconnu";
  if (status === "site_code_missing") return "Sans code";
  return status;
}

function financeLineStatusClass(status: string): string {
  if (status === "auto_matched") return "badge-green";
  if (status === "site_unknown") return "badge-orange";
  return "badge-red";
}

function ControlBlock({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="card" style={{ padding: 16, minHeight: 118 }}>
      <h4 style={{ margin: "0 0 8px", fontSize: 15 }}>{title}</h4>
      <p style={{ margin: 0, color: "#4b5563", fontSize: 13, lineHeight: 1.5 }}>{detail}</p>
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
