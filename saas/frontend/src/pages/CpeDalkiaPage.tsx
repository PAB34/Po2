import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CpeAccountingSiteMapping,
  CpeAccountingNatureRule,
  CpeBilanAnnuel,
  CpeFinanceControl,
  CpeFinanceImportBatch,
  CpeFinanceImportResult,
  CpeFinanceInvoice,
  CpeFinancePreview,
  CpeAccountingImportResult,
  CpeRevisionIndex,
  CpeSiteBilanItem,
  calculerCpeBilan,
  createCpeAccountingNatureRule,
  createCpeAccountingSiteMapping,
  deleteCpeAccountingNatureRule,
  fetchCpeBilan,
  fetchCpeAccountingNatureRules,
  fetchCpeAccountingSiteMappings,
  fetchCpeDju,
  fetchCpeFinanceBatches,
  fetchCpeRevisionIndices,
  fetchCpeFinanceInvoices,
  importCpeCsv,
  importCpeAccountingCodification,
  importCpeFinanceExport,
  previewCpeFinanceExport,
  recalculateCpeFinanceControls,
  deleteCpeAccountingSiteMapping,
  downloadCpeFinanceInvoiceLiaison,
  updateCpeAccountingNatureRule,
  updateCpeAccountingSiteMapping,
  updateCpeFinanceInvoice,
  upsertCpeRevisionIndex,
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

type CpeView = "cockpit" | "finance" | "performance";

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
  const [view, setView] = useState<CpeView>("cockpit");
  const fileRef = useRef<HTMLInputElement>(null);
  const financeFileRef = useRef<HTMLInputElement>(null);
  const codificationFileRef = useRef<HTMLInputElement>(null);
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

  const accountingRulesQ = useQuery({
    queryKey: ["cpe-accounting-nature-rules"],
    queryFn: () => fetchCpeAccountingNatureRules(token!),
    enabled: !!token && view === "finance",
  });

  const siteMappingsQ = useQuery({
    queryKey: ["cpe-accounting-site-mappings"],
    queryFn: () => fetchCpeAccountingSiteMappings(token!),
    enabled: !!token && view === "finance",
  });

  const financeBatchesQ = useQuery({
    queryKey: ["cpe-finance-batches"],
    queryFn: () => fetchCpeFinanceBatches(token!),
    enabled: !!token && view === "finance",
  });

  const financeInvoicesQ = useQuery({
    queryKey: ["cpe-finance-invoices"],
    queryFn: () => fetchCpeFinanceInvoices(token!),
    enabled: !!token && view === "finance",
  });

  const revisionIndicesQ = useQuery({
    queryKey: ["cpe-revision-indices", annee],
    queryFn: () => fetchCpeRevisionIndices(token!, annee),
    enabled: !!token && view === "finance",
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

  const codificationImportM = useMutation({
    mutationFn: (file: File) => importCpeAccountingCodification(token!, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cpe-accounting-nature-rules"] });
      qc.invalidateQueries({ queryKey: ["cpe-accounting-site-mappings"] });
    },
  });

  const financeImportM = useMutation({
    mutationFn: (file: File) => importCpeFinanceExport(token!, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cpe-finance-batches"] });
      qc.invalidateQueries({ queryKey: ["cpe-finance-invoices"] });
    },
  });

  const saveSiteMappingM = useMutation({
    mutationFn: (payload: Partial<CpeAccountingSiteMapping> & { id?: number; code_site: string; site_name: string }) =>
      payload.id
        ? updateCpeAccountingSiteMapping(token!, payload.id, payload)
        : createCpeAccountingSiteMapping(token!, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cpe-accounting-site-mappings"] }),
  });

  const deleteSiteMappingM = useMutation({
    mutationFn: (id: number) => deleteCpeAccountingSiteMapping(token!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cpe-accounting-site-mappings"] }),
  });

  const saveNatureRuleM = useMutation({
    mutationFn: (
      payload: Partial<CpeAccountingNatureRule> & {
        id?: number;
        market: string;
        billed_item: string;
        accounting_nature: string;
      },
    ) =>
      payload.id
        ? updateCpeAccountingNatureRule(token!, payload.id, payload)
        : createCpeAccountingNatureRule(token!, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cpe-accounting-nature-rules"] }),
  });

  const deleteNatureRuleM = useMutation({
    mutationFn: (id: number) => deleteCpeAccountingNatureRule(token!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cpe-accounting-nature-rules"] }),
  });

  const updateFinanceInvoiceM = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => updateCpeFinanceInvoice(token!, id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cpe-finance-invoices"] }),
  });

  const upsertRevisionIndexM = useMutation({
    mutationFn: (payload: { index_code: string; year: number; quarter: number; value: number; source?: string | null }) =>
      upsertCpeRevisionIndex(token!, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cpe-revision-indices", annee] }),
  });

  const recalculateControlsM = useMutation({
    mutationFn: (invoiceId: number) => recalculateCpeFinanceControls(token!, invoiceId),
  });

  const exportLiaisonM = useMutation({
    mutationFn: async (invoice: CpeFinanceInvoice) => {
      const blob = await downloadCpeFinanceInvoiceLiaison(token!, invoice.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `fiche-liaison-dalkia-${invoice.invoice_number}.xlsx`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
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
        <CpeViewTab active={view === "finance"} onClick={() => setView("finance")}>
          Referentiel finance
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
          onFinanceFile={(file) => financePreviewM.mutate(file)}
          onOpenPerformance={() => setView("performance")}
        />
      )}

      {view === "finance" && (
        <CpeFinanceReference
          annee={annee}
          codificationFileRef={codificationFileRef}
          financeImportFileRef={financeImportFileRef}
          siteMappings={siteMappingsQ.data ?? []}
          natureRules={accountingRulesQ.data ?? []}
          batches={financeBatchesQ.data ?? []}
          invoices={financeInvoicesQ.data ?? []}
          indices={revisionIndicesQ.data ?? []}
          lastControls={recalculateControlsM.data ?? null}
          loading={siteMappingsQ.isLoading || accountingRulesQ.isLoading || financeBatchesQ.isLoading}
          codificationImportPending={codificationImportM.isPending}
          codificationImportResult={codificationImportM.data ?? null}
          codificationImportError={codificationImportM.error instanceof Error ? codificationImportM.error.message : null}
          financeImportPending={financeImportM.isPending}
          financeImportResult={financeImportM.data ?? null}
          financeImportError={financeImportM.error instanceof Error ? financeImportM.error.message : null}
          saveSiteMappingPending={saveSiteMappingM.isPending}
          deleteSiteMappingPending={deleteSiteMappingM.isPending}
          saveNatureRulePending={saveNatureRuleM.isPending}
          deleteNatureRulePending={deleteNatureRuleM.isPending}
          invoiceActionPending={updateFinanceInvoiceM.isPending || exportLiaisonM.isPending}
          indexSavePending={upsertRevisionIndexM.isPending}
          controlsPending={recalculateControlsM.isPending}
          onCodificationFile={(file) => codificationImportM.mutate(file)}
          onFinanceImportFile={(file) => financeImportM.mutate(file)}
          onSaveSiteMapping={(payload) => saveSiteMappingM.mutate(payload)}
          onDeleteSiteMapping={(id) => deleteSiteMappingM.mutate(id)}
          onSaveNatureRule={(payload) => saveNatureRuleM.mutate(payload)}
          onDeleteNatureRule={(id) => deleteNatureRuleM.mutate(id)}
          onInvoiceStatus={(id, nextStatus) => updateFinanceInvoiceM.mutate({ id, status: nextStatus })}
          onExportLiaison={(invoice) => exportLiaisonM.mutate(invoice)}
          onSaveIndex={(payload) => upsertRevisionIndexM.mutate(payload)}
          onRecalculateControls={(invoiceId) => recalculateControlsM.mutate(invoiceId)}
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
  onFinanceFile,
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
  onFinanceFile: (file: File) => void;
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

const EMPTY_SITE_MAPPING = {
  code_site: "",
  site_name: "",
  family: "",
  manager: "",
  service_code: "",
  service_label: "",
  function_code: "",
  function_label: "",
  antenna_code: "",
  antenna_label: "",
  operation_code: "",
  operation_label: "",
  active: true,
};

const EMPTY_NATURE_RULE = {
  contract_code: "",
  market: "P2",
  service_sold: "",
  billed_item: "",
  frequency: "",
  accounting_nature: "",
  accounting_label: "",
  notes: "",
  active: true,
};

function CpeFinanceReference({
  annee,
  codificationFileRef,
  financeImportFileRef,
  siteMappings,
  natureRules,
  batches,
  invoices,
  indices,
  lastControls,
  loading,
  codificationImportPending,
  codificationImportResult,
  codificationImportError,
  financeImportPending,
  financeImportResult,
  financeImportError,
  saveSiteMappingPending,
  deleteSiteMappingPending,
  saveNatureRulePending,
  deleteNatureRulePending,
  invoiceActionPending,
  indexSavePending,
  controlsPending,
  onCodificationFile,
  onFinanceImportFile,
  onSaveSiteMapping,
  onDeleteSiteMapping,
  onSaveNatureRule,
  onDeleteNatureRule,
  onInvoiceStatus,
  onExportLiaison,
  onSaveIndex,
  onRecalculateControls,
}: {
  annee: number;
  codificationFileRef: React.RefObject<HTMLInputElement>;
  financeImportFileRef: React.RefObject<HTMLInputElement>;
  siteMappings: CpeAccountingSiteMapping[];
  natureRules: CpeAccountingNatureRule[];
  batches: CpeFinanceImportBatch[];
  invoices: CpeFinanceInvoice[];
  indices: CpeRevisionIndex[];
  lastControls: CpeFinanceControl[] | null;
  loading: boolean;
  codificationImportPending: boolean;
  codificationImportResult: CpeAccountingImportResult | null;
  codificationImportError: string | null;
  financeImportPending: boolean;
  financeImportResult: CpeFinanceImportResult | null;
  financeImportError: string | null;
  saveSiteMappingPending: boolean;
  deleteSiteMappingPending: boolean;
  saveNatureRulePending: boolean;
  deleteNatureRulePending: boolean;
  invoiceActionPending: boolean;
  indexSavePending: boolean;
  controlsPending: boolean;
  onCodificationFile: (file: File) => void;
  onFinanceImportFile: (file: File) => void;
  onSaveSiteMapping: (payload: Partial<CpeAccountingSiteMapping> & { id?: number; code_site: string; site_name: string }) => void;
  onDeleteSiteMapping: (id: number) => void;
  onSaveNatureRule: (
    payload: Partial<CpeAccountingNatureRule> & { id?: number; market: string; billed_item: string; accounting_nature: string },
  ) => void;
  onDeleteNatureRule: (id: number) => void;
  onInvoiceStatus: (id: number, nextStatus: string) => void;
  onExportLiaison: (invoice: CpeFinanceInvoice) => void;
  onSaveIndex: (payload: { index_code: string; year: number; quarter: number; value: number; source?: string | null }) => void;
  onRecalculateControls: (invoiceId: number) => void;
}) {
  const [draft, setDraft] = useState(EMPTY_SITE_MAPPING);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [ruleDraft, setRuleDraft] = useState(EMPTY_NATURE_RULE);
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);
  const [ruleFilter, setRuleFilter] = useState("");
  const [indexDraft, setIndexDraft] = useState({ index_code: "ICHT_IME", quarter: 1, value: "", source: "Saisie Po2" });
  const recentInvoices = invoices.slice(0, 8);
  const visibleRules = natureRules
    .filter((rule) => {
      const haystack = [
        rule.contract_code,
        rule.market,
        rule.service_sold,
        rule.billed_item,
        rule.accounting_nature,
        rule.accounting_label,
        rule.notes,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(ruleFilter.trim().toLowerCase());
    })
    .slice(0, 120);
  const controlsSummary = lastControls
    ? {
        ok: lastControls.filter((item) => item.status === "ok").length,
        error: lastControls.filter((item) => item.status === "error").length,
        blocked: lastControls.filter((item) => item.status === "blocked").length,
      }
    : null;

  const startEdit = (mapping: CpeAccountingSiteMapping) => {
    setEditingId(mapping.id);
    setDraft({
      code_site: mapping.code_site,
      site_name: mapping.site_name,
      family: mapping.family ?? "",
      manager: mapping.manager ?? "",
      service_code: mapping.service_code ?? "",
      service_label: mapping.service_label ?? "",
      function_code: mapping.function_code ?? "",
      function_label: mapping.function_label ?? "",
      antenna_code: mapping.antenna_code ?? "",
      antenna_label: mapping.antenna_label ?? "",
      operation_code: mapping.operation_code ?? "",
      operation_label: mapping.operation_label ?? "",
      active: mapping.active,
    });
  };

  const resetDraft = () => {
    setEditingId(null);
    setDraft(EMPTY_SITE_MAPPING);
  };

  const startRuleEdit = (rule: CpeAccountingNatureRule) => {
    setEditingRuleId(rule.id);
    setRuleDraft({
      contract_code: rule.contract_code ?? "",
      market: rule.market,
      service_sold: rule.service_sold ?? "",
      billed_item: rule.billed_item,
      frequency: rule.frequency ?? "",
      accounting_nature: rule.accounting_nature,
      accounting_label: rule.accounting_label ?? "",
      notes: rule.notes ?? "",
      active: rule.active,
    });
  };

  const resetRuleDraft = () => {
    setEditingRuleId(null);
    setRuleDraft(EMPTY_NATURE_RULE);
  };

  const submitDraft = () => {
    if (!draft.code_site.trim() || !draft.site_name.trim()) return;
    onSaveSiteMapping({
      ...(editingId ? { id: editingId } : {}),
      code_site: draft.code_site.trim().toUpperCase(),
      site_name: draft.site_name.trim(),
      family: draft.family || null,
      manager: draft.manager || null,
      service_code: draft.service_code || null,
      service_label: draft.service_label || null,
      function_code: draft.function_code || null,
      function_label: draft.function_label || null,
      antenna_code: draft.antenna_code || null,
      antenna_label: draft.antenna_label || null,
      operation_code: draft.operation_code || null,
      operation_label: draft.operation_label || null,
      active: draft.active,
    });
    resetDraft();
  };

  const submitRuleDraft = () => {
    if (!ruleDraft.market.trim() || !ruleDraft.billed_item.trim() || !ruleDraft.accounting_nature.trim()) return;
    onSaveNatureRule({
      ...(editingRuleId ? { id: editingRuleId } : {}),
      contract_code: ruleDraft.contract_code.trim().toUpperCase() || null,
      market: ruleDraft.market.trim().toUpperCase(),
      service_sold: ruleDraft.service_sold.trim().toUpperCase() || null,
      billed_item: ruleDraft.billed_item.trim().toUpperCase(),
      frequency: ruleDraft.frequency || null,
      accounting_nature: ruleDraft.accounting_nature.trim(),
      accounting_label: ruleDraft.accounting_label || null,
      notes: ruleDraft.notes || null,
      active: ruleDraft.active,
    });
    resetRuleDraft();
  };

  return (
    <>
      <section style={{ marginBottom: 24 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16 }}>
          <KpiCard label="Sites codifies" value={String(siteMappings.length)} sub="Lignes du referentiel finance" color="#2563eb" />
          <KpiCard label="Regles nature" value={String(natureRules.length)} sub="Poste facture vers nature" color="#0f766e" />
          <KpiCard label="Indices revision" value={String(indices.length)} sub={`Exercice ${annee}, ICHT-IME / BT40`} color="#b45309" />
          <KpiCard label="Lots importes" value={String(batches.length)} sub={`${invoices.length} facture(s) archivees`} color="#9333ea" />
          <KpiCard
            label="Dernier lot"
            value={batches[0] ? fmtEur(batches[0].total_ht) : "Aucun"}
            sub={batches[0] ? `${batches[0].line_count} ligne(s), ${batches[0].invoice_count} facture(s)` : "Import finances a lancer"}
            color="#111827"
          />
        </div>
      </section>

      <section className="card" style={{ padding: 16, marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start" }}>
          <div>
            <h3 style={{ margin: "0 0 4px" }}>Initialisation du referentiel</h3>
            <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>
              Importe la matrice de codification DALKIA, puis archive les exports finances XLSX pour preparer les fiches de liaison.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
            <button type="button" className="secondary-button" onClick={() => codificationFileRef.current?.click()} disabled={codificationImportPending}>
              {codificationImportPending ? "Import..." : "Importer codification"}
            </button>
            <input
              ref={codificationFileRef}
              type="file"
              accept=".xlsx"
              style={{ display: "none" }}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onCodificationFile(file);
                event.target.value = "";
              }}
            />
            <button type="button" className="primary-button" onClick={() => financeImportFileRef.current?.click()} disabled={financeImportPending}>
              {financeImportPending ? "Import..." : "Importer export finances"}
            </button>
            <input
              ref={financeImportFileRef}
              type="file"
              accept=".xlsx"
              style={{ display: "none" }}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onFinanceImportFile(file);
                event.target.value = "";
              }}
            />
          </div>
        </div>
        {codificationImportResult && (
          <p style={{ color: "#166534", fontSize: 13, margin: "12px 0 0" }}>
            Codification importee : {codificationImportResult.site_mappings_created} site(s) crees, {codificationImportResult.site_mappings_updated} mis a jour,
            {" "}{codificationImportResult.nature_rules_created} regle(s) creees, {codificationImportResult.nature_rules_updated} mises a jour.
          </p>
        )}
        {financeImportResult && (
          <p style={{ color: "#166534", fontSize: 13, margin: "12px 0 0" }}>
            Export archive : lot #{financeImportResult.batch.id}, {financeImportResult.line_count} ligne(s),
            {" "}{financeImportResult.invoices.length} facture(s), {financeImportResult.matched_accounting_rules} ligne(s) avec nature.
          </p>
        )}
        {[codificationImportError, financeImportError].filter(Boolean).map((message) => (
          <p key={message} style={{ color: "#dc2626", fontSize: 13, margin: "12px 0 0" }}>{message}</p>
        ))}
        {financeImportResult?.warnings.map((warning) => (
          <p key={warning} style={{ color: "#9a3412", fontSize: 13, margin: "8px 0 0" }}>{warning}</p>
        ))}
      </section>

      <section className="card" style={{ padding: 16, marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", marginBottom: 12 }}>
          <div>
            <h3 style={{ margin: "0 0 4px" }}>Indices de revision P2 / P3</h3>
            <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>
              P2 utilise ICHT-IME + FSD2. P3/P3.4 utilise ICHT-IME + BT40.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
            <select
              value={indexDraft.index_code}
              onChange={(event) => setIndexDraft({ ...indexDraft, index_code: event.target.value })}
              style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db" }}
            >
              <option value="ICHT_IME">ICHT-IME</option>
              <option value="BT40">BT40</option>
              <option value="FSD2">FSD2</option>
            </select>
            <select
              value={indexDraft.quarter}
              onChange={(event) => setIndexDraft({ ...indexDraft, quarter: Number(event.target.value) })}
              style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db" }}
            >
              {[1, 2, 3, 4].map((quarter) => (
                <option key={quarter} value={quarter}>T{quarter}</option>
              ))}
            </select>
            <input
              type="number"
              step="0.01"
              value={indexDraft.value}
              onChange={(event) => setIndexDraft({ ...indexDraft, value: event.target.value })}
              placeholder="Valeur"
              style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db", width: 110 }}
            />
            <button
              type="button"
              className="primary-button"
              disabled={indexSavePending || !indexDraft.value}
              onClick={() => {
                onSaveIndex({
                  index_code: indexDraft.index_code,
                  year: annee,
                  quarter: indexDraft.quarter,
                  value: Number(indexDraft.value),
                  source: indexDraft.source,
                });
                setIndexDraft({ ...indexDraft, value: "" });
              }}
            >
              Enregistrer indice
            </button>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {indices.length === 0 ? (
            <span style={{ color: "#9ca3af", fontSize: 13 }}>Aucun indice saisi pour {annee}.</span>
          ) : (
            indices.map((item) => (
              <span key={item.id} className="badge badge-blue">
                {item.index_code} T{item.quarter} : {fmt(item.value, 2)}
              </span>
            ))
          )}
        </div>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "minmax(320px, 0.95fr) minmax(420px, 1.4fr)", gap: 16, marginBottom: 24 }}>
        <div className="card" style={{ padding: 16 }}>
          <h3 style={{ margin: "0 0 12px" }}>{editingId ? "Modifier un site finance" : "Ajouter un site finance"}</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <FinanceInput label="Code site" value={draft.code_site} onChange={(value) => setDraft({ ...draft, code_site: value })} />
            <FinanceInput label="Famille" value={draft.family} onChange={(value) => setDraft({ ...draft, family: value })} />
            <FinanceInput label="Nom du site" value={draft.site_name} onChange={(value) => setDraft({ ...draft, site_name: value })} wide />
            <FinanceInput label="Gestionnaire" value={draft.manager} onChange={(value) => setDraft({ ...draft, manager: value })} />
            <FinanceInput label="Service" value={draft.service_code} onChange={(value) => setDraft({ ...draft, service_code: value })} />
            <FinanceInput label="Libelle service" value={draft.service_label} onChange={(value) => setDraft({ ...draft, service_label: value })} wide />
            <FinanceInput label="Fonction" value={draft.function_code} onChange={(value) => setDraft({ ...draft, function_code: value })} />
            <FinanceInput label="Libelle fonction" value={draft.function_label} onChange={(value) => setDraft({ ...draft, function_label: value })} />
            <FinanceInput label="Antenne" value={draft.antenna_code} onChange={(value) => setDraft({ ...draft, antenna_code: value })} />
            <FinanceInput label="Operation" value={draft.operation_code} onChange={(value) => setDraft({ ...draft, operation_code: value })} />
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button type="button" className="primary-button" disabled={saveSiteMappingPending || !draft.code_site || !draft.site_name} onClick={submitDraft}>
              {editingId ? "Enregistrer" : "Ajouter"}
            </button>
            {editingId && (
              <button type="button" className="secondary-button" onClick={resetDraft}>
                Annuler
              </button>
            )}
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <h3 style={{ margin: "0 0 8px" }}>Sites de codification</h3>
          {loading ? (
            <p>Chargement...</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                  <th style={thStyle}>Code</th>
                  <th style={thStyle}>Site</th>
                  <th style={thStyle}>Service</th>
                  <th style={thStyle}>Fonction</th>
                  <th style={thStyle}>Antenne</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {siteMappings.slice(0, 80).map((mapping) => (
                  <tr key={mapping.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={tdStyle}><code>{mapping.code_site}</code></td>
                    <td style={{ ...tdStyle, minWidth: 220 }}>{mapping.site_name}</td>
                    <td style={tdStyle}>{mapping.service_code ?? "-"}<div style={{ color: "#6b7280" }}>{mapping.service_label}</div></td>
                    <td style={tdStyle}>{mapping.function_code ?? "-"}<div style={{ color: "#6b7280" }}>{mapping.function_label}</div></td>
                    <td style={tdStyle}>{mapping.antenna_code ?? "-"}</td>
                    <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>
                      <button type="button" className="secondary-button" style={{ fontSize: 12, padding: "4px 8px" }} onClick={() => startEdit(mapping)}>
                        Modifier
                      </button>{" "}
                      <button
                        type="button"
                        className="secondary-button"
                        style={{ fontSize: 12, padding: "4px 8px", color: "#b91c1c" }}
                        disabled={deleteSiteMappingPending}
                        onClick={() => onDeleteSiteMapping(mapping.id)}
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section className="card" style={{ padding: 16, marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", marginBottom: 12 }}>
          <div>
            <h3 style={{ margin: "0 0 4px" }}>Matrice de codification DALKIA</h3>
            <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>
              Rattachement par code contrat, poste facture et nature comptable pour les exports finances.
            </p>
          </div>
          <input
            value={ruleFilter}
            onChange={(event) => setRuleFilter(event.target.value)}
            placeholder="Filtrer contrat, poste, nature..."
            style={{ padding: "7px 9px", borderRadius: 6, border: "1px solid #d1d5db", minWidth: 260 }}
          />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "minmax(260px, 0.7fr) minmax(520px, 1.6fr)", gap: 16 }}>
          <div>
            <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>{editingRuleId ? "Modifier une regle" : "Ajouter une regle"}</h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <FinanceInput label="Code contrat" value={ruleDraft.contract_code} onChange={(value) => setRuleDraft({ ...ruleDraft, contract_code: value })} />
              <FinanceInput label="Marche" value={ruleDraft.market} onChange={(value) => setRuleDraft({ ...ruleDraft, market: value })} />
              <FinanceInput label="Poste facture" value={ruleDraft.billed_item} onChange={(value) => setRuleDraft({ ...ruleDraft, billed_item: value })} />
              <FinanceInput label="Service vendu" value={ruleDraft.service_sold} onChange={(value) => setRuleDraft({ ...ruleDraft, service_sold: value })} />
              <FinanceInput label="Nature" value={ruleDraft.accounting_nature} onChange={(value) => setRuleDraft({ ...ruleDraft, accounting_nature: value })} />
              <FinanceInput label="Libelle nature" value={ruleDraft.accounting_label} onChange={(value) => setRuleDraft({ ...ruleDraft, accounting_label: value })} />
              <FinanceInput label="Nb lignes / frequence" value={ruleDraft.frequency} onChange={(value) => setRuleDraft({ ...ruleDraft, frequency: value })} />
              <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 12, color: "#6b7280", alignSelf: "end" }}>
                <input
                  type="checkbox"
                  checked={ruleDraft.active}
                  onChange={(event) => setRuleDraft({ ...ruleDraft, active: event.target.checked })}
                />
                Active
              </label>
              <FinanceInput label="Notes / statut DALKIA" value={ruleDraft.notes} onChange={(value) => setRuleDraft({ ...ruleDraft, notes: value })} wide />
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button
                type="button"
                className="primary-button"
                disabled={saveNatureRulePending || !ruleDraft.market || !ruleDraft.billed_item || !ruleDraft.accounting_nature}
                onClick={submitRuleDraft}
              >
                {editingRuleId ? "Enregistrer" : "Ajouter"}
              </button>
              {editingRuleId && (
                <button type="button" className="secondary-button" onClick={resetRuleDraft}>
                  Annuler
                </button>
              )}
            </div>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                  <th style={thStyle}>Contrat</th>
                  <th style={thStyle}>Marche</th>
                  <th style={thStyle}>Poste</th>
                  <th style={thStyle}>Nature</th>
                  <th style={thStyle}>Statut / notes</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleRules.map((rule) => (
                  <tr key={rule.id} style={{ borderBottom: "1px solid #f3f4f6", opacity: rule.active ? 1 : 0.55 }}>
                    <td style={tdStyle}><code>{rule.contract_code ?? "*"}</code></td>
                    <td style={tdStyle}>{rule.market}<div style={{ color: "#6b7280" }}>{rule.service_sold}</div></td>
                    <td style={tdStyle}>{rule.billed_item}<div style={{ color: "#6b7280" }}>{rule.frequency ? `${rule.frequency} ligne(s)` : ""}</div></td>
                    <td style={tdStyle}>{rule.accounting_nature}<div style={{ color: "#6b7280" }}>{rule.accounting_label}</div></td>
                    <td style={{ ...tdStyle, minWidth: 240 }}>{rule.notes ?? "-"}</td>
                    <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>
                      <button type="button" className="secondary-button" style={{ fontSize: 12, padding: "4px 8px" }} onClick={() => startRuleEdit(rule)}>
                        Modifier
                      </button>{" "}
                      <button
                        type="button"
                        className="secondary-button"
                        style={{ fontSize: 12, padding: "4px 8px", color: "#b91c1c" }}
                        disabled={deleteNatureRulePending}
                        onClick={() => onDeleteNatureRule(rule.id)}
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
                {visibleRules.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ ...tdStyle, textAlign: "center", color: "#9ca3af" }}>
                      Aucune regle de codification.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            {natureRules.length > visibleRules.length && (
              <p style={{ margin: "8px 0 0", color: "#6b7280", fontSize: 12 }}>
                {visibleRules.length} regle(s) affichee(s) sur {natureRules.length}. Utilise le filtre pour cibler une ligne.
              </p>
            )}
          </div>
        </div>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "1fr", gap: 16 }}>
        <div style={{ overflowX: "auto" }}>
          <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>Factures archivees recentes</h4>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                <th style={thStyle}>Facture</th>
                <th style={thStyle}>Contrat</th>
                <th style={thStyle}>Periode</th>
                <th style={thStyle}>HT</th>
                  <th style={thStyle}>Statut</th>
                  <th style={thStyle}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {recentInvoices.map((invoice) => (
                <tr key={invoice.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={tdStyle}>{invoice.invoice_number}</td>
                  <td style={tdStyle}>{invoice.contract_code ?? "-"}</td>
                  <td style={tdStyle}>{invoice.period_start ?? "-"} au {invoice.period_end ?? "-"}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{fmtEur(invoice.total_ht)}</td>
                  <td style={tdStyle}>
                    <select
                      value={invoice.status}
                      disabled={invoiceActionPending}
                      onChange={(event) => onInvoiceStatus(invoice.id, event.target.value)}
                      style={{ padding: "4px 6px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 12 }}
                    >
                      <option value="a_controler">A controler</option>
                      <option value="valide">Valide</option>
                      <option value="refuse">Refuse</option>
                      <option value="conteste">Conteste</option>
                    </select>
                  </td>
                  <td style={tdStyle}>
                    <button
                      type="button"
                      className="secondary-button"
                      style={{ fontSize: 12, padding: "4px 8px" }}
                      disabled={invoiceActionPending}
                      onClick={() => onExportLiaison(invoice)}
                    >
                      Export XLSX
                    </button>
                    {" "}
                    <button
                      type="button"
                      className="secondary-button"
                      style={{ fontSize: 12, padding: "4px 8px" }}
                      disabled={controlsPending}
                      onClick={() => onRecalculateControls(invoice.id)}
                    >
                      Controle facture
                    </button>
                  </td>
                </tr>
              ))}
              {recentInvoices.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ ...tdStyle, textAlign: "center", color: "#9ca3af" }}>
                    Aucun export finances importe.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          {controlsSummary && (
            <div style={{ marginTop: 10, padding: 10, borderRadius: 6, background: "#f9fafb", fontSize: 13 }}>
              Dernier controle facture : <strong>{controlsSummary.ok}</strong> OK,{" "}
              <strong style={{ color: "#dc2626" }}>{controlsSummary.error}</strong> ecart(s),{" "}
              <strong style={{ color: "#b45309" }}>{controlsSummary.blocked}</strong> bloque(s).
              {lastControls?.slice(0, 3).map((control) => (
                <p key={control.id} style={{ margin: "6px 0 0", color: control.status === "error" ? "#dc2626" : "#6b7280" }}>
                  {control.message}
                </p>
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  );
}

function FinanceInput({
  label,
  value,
  wide,
  onChange,
}: {
  label: string;
  value: string;
  wide?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label style={{ display: "grid", gap: 4, gridColumn: wide ? "1 / -1" : undefined, fontSize: 12, color: "#6b7280" }}>
      {label}
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        style={{ padding: "7px 9px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 13, color: "#111827" }}
      />
    </label>
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
