import { Fragment, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  CpeAccountingSiteMapping,
  CpeAccountingNatureRule,
  CpeBilanAnnuel,
  CpeConsoSynthese,
  CpeContractReference,
  CpeFinanceControlReport,
  CpeFinanceImportBatch,
  CpeFinanceImportResult,
  CpeFinanceInvoice,
  CpeInvoiceEvidence,
  CpeFinancePreview,
  CpeAccountingImportResult,
  CpeRevisionIndex,
  CpeRevisionObservation,
  CpeSiteBilanItem,
  calculerCpeBilan,
  createCpeAccountingNatureRule,
  createCpeAccountingSiteMapping,
  createCpeContractReference,
  deleteCpeContractReference,
  deleteCpeFinanceHistory,
  deleteCpeAccountingNatureRule,
  fetchCpeBilan,
  fetchCpeAtterrissage,
  type CpeAtterrissage,
  type CpeAtterrissageItem,
  fetchCpeElecPerformance,
  type CpeElecPerf,
  type CpeElecPerfItem,
  fetchCpeP24Objective,
  type CpeP24Objective,
  fetchCpeConsoSynthese,
  fetchCpeAccountingNatureRules,
  fetchCpeAccountingSiteMappings,
  fetchCpeContractReferences,
  fetchCpeDju,
  fetchCpeFinanceBatches,
  fetchCpeRevisionIndices,
  fetchCpeRevisionObservations,
  fetchCpeRevisionEvidences,
  fetchCpeFinanceInvoices,
  fetchCpeFinanceControlReport,
  importCpeCsv,
  importCpeAccountingCodification,
  importCpeFinanceExport,
  applyCpeInvoiceEvidenceDeclaredIndices,
  previewCpeFinanceExport,
  recalculateAllCpeFinanceControls,
  deleteCpeAccountingSiteMapping,
  downloadCpeFinanceInvoiceLiaison,
  downloadCpeFinanceControlReport,
  fetchCpeMarketTracking,
  downloadCpeMarketTracking,
  type CpeMarketTrackingCell,
  type CpeMarketTrackingTotal,
  type CpeMarketTrackingPoste,
  type CpeP1Dpgf,
  type CpeMarketTrackingQuarters,
  type CpeDju,
  importCpeP3Devis,
  fetchCpeP3Devis,
  fetchCpeP3Atterrissage,
  type CpeP3Atterrissage,
  updateCpeAccountingNatureRule,
  updateCpeAccountingSiteMapping,
  updateCpeContractReference,
  updateCpeFinanceInvoice,
  upsertCpeRevisionIndex,
  uploadCpeInvoiceEvidencePdf,
  uploadCpeRevisionEvidencePdf,
  upsertCpePrixGaz,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

const CURRENT_YEAR = new Date().getFullYear();
const MARKET_COLORS: Record<string, string> = {
  P1: "#2563eb",
  P2: "#0f766e",
  P3: "#7c3aed",
  AUTRE: "#6b7280",
};
const STATUS_COLORS: Record<string, string> = {
  a_controler: "#f59e0b",
  valide: "#16a34a",
  refuse: "#dc2626",
  conteste: "#2563eb",
  autre: "#6b7280",
};

const TYPE_LABEL: Record<string, string> = {
  interessement: "Intéressement",
  penalite: "Pénalité",
  equilibre: "Équilibre",
  insuffisant: "—",
};
const CONTROL_TYPE_LABELS: Record<string, string> = {
  revision_p2: "Revision P2",
  revision_p3: "Revision P3/P3.4",
  p2_4_objectives: "Objectif P2.4",
  accounting_nature: "Nature comptable",
  accounting_site: "Rattachement site finance",
  invoice_type: "Type de facture",
  invoice_total_ht: "Total HT facture",
  invoice_period: "Periode facture",
  invoice_timeline: "Calendrier edition et echeance",
  p1_gaz_acompte_dpgf: "Acompte P1 vs DPGF",
};
const REVISION_INDEX_CODE_OPTIONS: Array<{ code: string; label: string }> = [
  { code: "ICHT_IME", label: "ICHT-IME (trimestriel)" },
  { code: "FSD2", label: "FSD2 (trimestriel)" },
  { code: "BT40", label: "BT40 (trimestriel)" },
  { code: "ICHT_IME0", label: "ICHT-IME0 (base contrat)" },
  { code: "FSD20", label: "FSD20 (base contrat)" },
  { code: "BT400", label: "BT400 (base contrat)" },
  { code: "P1_CPB0_T1", label: "P1 CPB0 T1 (reference)" },
  { code: "P1_CPB0_T2", label: "P1 CPB0 T2 (reference)" },
  { code: "P1_CPB0_T3", label: "P1 CPB0 T3 (reference)" },
  { code: "P1_TVD0_T1", label: "P1 TVD0 T1 (reference)" },
  { code: "P1_TVD0_T2", label: "P1 TVD0 T2 (reference)" },
  { code: "P1_TVD0_T3", label: "P1 TVD0 T3 (reference)" },
  { code: "P1_CEE0", label: "P1 CEE0 (reference)" },
  { code: "P1_TICGN0", label: "P1 TICGN0 (reference)" },
  { code: "P1_PEG0", label: "P1 PEG0 (reference a renseigner)" },
  { code: "P1_PUGAZ0", label: "P1 PUGAZ0 (reference a renseigner)" },
];

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
type CpeFinanceSection = "imports" | "sites" | "rules" | "references" | "indices" | "invoices" | "p3-devis" | "controls";
type QueueInvoice = CpeFinanceControlReport["invoices"][number];
type QueueSortKey =
  | "invoice_number"
  | "contract"
  | "invoice_type"
  | "recipient_ref"
  | "market"
  | "billed_items"
  | "total_ht"
  | "ok"
  | "error"
  | "blocked"
  | "families"
  | "due_date"
  | "invoice_status";

const CPE_FINANCE_SECTIONS: Array<{ id: CpeFinanceSection; label: string; detail: string }> = [
  { id: "imports", label: "Imports", detail: "Codification et exports finance" },
  { id: "sites", label: "Sites", detail: "VDS, CCAS et rattachements" },
  { id: "rules", label: "Matrice", detail: "Contrat, poste, nature" },
  { id: "references", label: "Références", detail: "DPGF, formules, tolérances" },
  { id: "indices", label: "Formules et indices", detail: "Révisions, preuves PDF et sources" },
  { id: "invoices", label: "Factures", detail: "Suivi marché : prévu vs reçu" },
  { id: "p3-devis", label: "Factures petits travaux P3", detail: "Devis P3/P6 et atterrissage" },
  { id: "controls", label: "Contrôle factures", detail: "Audit global et anomalies" },
];

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
function fmtDate(val: string | null | undefined): string {
  if (!val) return "—";
  const parsed = new Date(val);
  return Number.isNaN(parsed.getTime()) ? val : parsed.toLocaleDateString("fr-FR");
}
function fmtPct(val: number | null | undefined): string {
  if (val == null) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "percent", maximumFractionDigits: 1 }).format(val);
}
function tauxClass(taux: number | null | undefined): string {
  if (taux == null) return "badge-gray";
  if (taux >= 0.9 && taux <= 1.1) return "badge-green";
  if (taux >= 0.7 && taux <= 1.3) return "badge-orange";
  return "badge-red";
}
const MARKET_YEAR_OPTIONS = [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033];
function deadlineLabel(status: string | null | undefined): string {
  if (status === "transmis_finances") return "Transmise finances";
  if (status === "echeance_depassee") return "Échéance dépassée";
  if (status === "urgent") return "À valider sous 7 j";
  if (status === "a_anticiper") return "À anticiper";
  if (status === "echeance_absente") return "Échéance absente";
  return "Dans les temps";
}
function deadlineClass(status: string | null | undefined): string {
  if (status === "transmis_finances") return "badge-green";
  if (status === "echeance_depassee") return "badge-red";
  if (status === "urgent" || status === "a_anticiper" || status === "echeance_absente") return "badge-orange";
  return "badge-blue";
}

export default function CpeDalkiaPage() {
  const { token } = useAuth();
  const qc = useQueryClient();
  const [annee, setAnnee] = useState(CURRENT_YEAR);
  const [filterCat, setFilterCat] = useState<string>("tous");
  const [trimestre, setTrimestre] = useState<number>(2);
  const [showPuForm, setShowPuForm] = useState(false);
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

  const consoSyntheseQ = useQuery({
    queryKey: ["cpe-conso-synthese", annee],
    queryFn: () => fetchCpeConsoSynthese(token!, annee),
    enabled: !!token && view === "performance",
  });

  const atterrissageQ = useQuery({
    queryKey: ["cpe-atterrissage", annee, trimestre],
    queryFn: () => fetchCpeAtterrissage(token!, annee, trimestre),
    enabled: !!token && view === "performance",
  });

  const elecPerfQ = useQuery({
    queryKey: ["cpe-elec-performance", annee],
    queryFn: () => fetchCpeElecPerformance(token!, annee),
    enabled: !!token && view === "performance",
  });

  const p24Q = useQuery({
    queryKey: ["cpe-p24-objective", annee],
    queryFn: () => fetchCpeP24Objective(token!, annee),
    enabled: !!token && view === "performance",
  });

  const accountingRulesQ = useQuery({
    queryKey: ["cpe-accounting-nature-rules"],
    queryFn: () => fetchCpeAccountingNatureRules(token!),
    enabled: !!token && view === "finance",
  });

  const contractReferencesQ = useQuery({
    queryKey: ["cpe-contract-references"],
    queryFn: () => fetchCpeContractReferences(token!),
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
    queryKey: ["cpe-revision-indices"],
    queryFn: () => fetchCpeRevisionIndices(token!),
    enabled: !!token && view === "finance",
  });

  const financeControlReportQ = useQuery({
    queryKey: ["cpe-finance-control-report"],
    queryFn: () => fetchCpeFinanceControlReport(token!),
    enabled: !!token && view === "finance",
  });

  const revisionObservationsQ = useQuery({
    queryKey: ["cpe-revision-observations"],
    queryFn: () => fetchCpeRevisionObservations(token!),
    enabled: !!token && view === "finance",
  });

  const revisionEvidencesQ = useQuery({
    queryKey: ["cpe-revision-evidences"],
    queryFn: () => fetchCpeRevisionEvidences(token!),
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
      qc.invalidateQueries({ queryKey: ["cpe-conso-synthese", annee] });
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
      qc.invalidateQueries({ queryKey: ["cpe-revision-observations"] });
    },
  });

  const deleteFinanceHistoryM = useMutation({
    mutationFn: () => deleteCpeFinanceHistory(token!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cpe-finance-batches"] });
      qc.invalidateQueries({ queryKey: ["cpe-finance-invoices"] });
      qc.invalidateQueries({ queryKey: ["cpe-revision-observations"] });
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

  const saveContractReferenceM = useMutation({
    mutationFn: (
      payload: Partial<CpeContractReference> & {
        id?: number;
        contract_code: string;
        reference_kind: string;
        year: number;
        market: string;
        billed_item: string;
      },
    ) =>
      payload.id
        ? updateCpeContractReference(token!, payload.id, payload)
        : createCpeContractReference(token!, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cpe-contract-references"] }),
  });

  const deleteContractReferenceM = useMutation({
    mutationFn: (id: number) => deleteCpeContractReference(token!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cpe-contract-references"] }),
  });

  const updateFinanceInvoiceM = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => updateCpeFinanceInvoice(token!, id, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cpe-finance-invoices"] });
      qc.invalidateQueries({ queryKey: ["cpe-finance-control-report"] });
    },
  });

  const upsertRevisionIndexM = useMutation({
    mutationFn: (payload: { index_code: string; year: number; quarter: number; value: number; source?: string | null; verification_status?: string; evidence_id?: number | null; notes?: string | null }) =>
      upsertCpeRevisionIndex(token!, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cpe-revision-indices"] });
      qc.invalidateQueries({ queryKey: ["cpe-revision-observations"] });
    },
  });

  const recalculateAllControlsM = useMutation({
    mutationFn: () => recalculateAllCpeFinanceControls(token!),
    onSuccess: (report) => {
      qc.setQueryData(["cpe-finance-control-report"], report);
      qc.invalidateQueries({ queryKey: ["cpe-finance-invoices"] });
    },
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
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cpe-finance-invoices"] });
      qc.invalidateQueries({ queryKey: ["cpe-finance-control-report"] });
    },
  });

  const exportGlobalControlReportM = useMutation({
    mutationFn: async () => {
      const blob = await downloadCpeFinanceControlReport(token!);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `rapport-controle-global-cpe-${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    },
  });

  const uploadEvidencePdfM = useMutation({
    mutationFn: ({ invoiceId, file }: { invoiceId: number; file: File }) => uploadCpeInvoiceEvidencePdf(token!, invoiceId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cpe-finance-invoices"] });
      qc.invalidateQueries({ queryKey: ["cpe-revision-evidences"] });
    },
  });

  const uploadRevisionEvidencePdfM = useMutation({
    mutationFn: (file: File) => uploadCpeRevisionEvidencePdf(token!, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cpe-finance-invoices"] });
      qc.invalidateQueries({ queryKey: ["cpe-revision-evidences"] });
    },
  });

  const applyEvidenceIndicesM = useMutation({
    mutationFn: (evidenceId: number) => applyCpeInvoiceEvidenceDeclaredIndices(token!, evidenceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cpe-revision-indices"] });
      qc.invalidateQueries({ queryKey: ["cpe-revision-observations"] });
      qc.invalidateQueries({ queryKey: ["cpe-revision-evidences"] });
    },
  });

  const bilan: CpeBilanAnnuel | undefined = bilanQ.data;
  const dju = djuQ.data;
  const djuReference = dju?.reference_dju ?? 1426;
  const djuProfileLabel = dju?.profile_label ?? "DALKIA contractuel";
  const djuStationLabel = dju?.station_label ?? "Montpellier";
  const djuReferencePeriod = dju?.reference_period ?? "1981-2010";
  const djuSourceWarning = Boolean(dju?.contractual && dju.compliant_source === false);
  const consoSynthese = consoSyntheseQ.data;

  // prix_tarifs depuis le bilan (T1/T2/T3 pré-chargés par OS N°3)
  const prixTarifs = bilan?.prix_tarifs ?? {};
  const prixT2 = prixTarifs["T2"] ?? null;

  const filteredSites: CpeSiteBilanItem[] =
    bilan?.sites.filter((s) => filterCat === "tous" || s.site.categorie === filterCat) ?? [];

  const categories = ["tous", "ENS", "SPORT", "BAM", "CULT", "CCAS"];

  return (
    <div style={{ width: "100%" }}>
      {/* ── En-tête ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        <div style={{ flex: 1 }}>
          <h2 style={{ margin: 0 }}>CPE DALKIA</h2>
          <p style={{ margin: "4px 0 0", color: "#6b7280", fontSize: 14 }}>
            Pilotage contractuel, consommations et performance energetique du Lot 1
          </p>
        </div>
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
          contractReferences={contractReferencesQ.data ?? []}
          batches={financeBatchesQ.data ?? []}
          invoices={financeInvoicesQ.data ?? []}
          indices={revisionIndicesQ.data ?? []}
          revisionObservations={revisionObservationsQ.data ?? []}
          revisionEvidences={revisionEvidencesQ.data ?? []}
          controlReport={recalculateAllControlsM.data ?? financeControlReportQ.data ?? null}
          loading={siteMappingsQ.isLoading || accountingRulesQ.isLoading || contractReferencesQ.isLoading || financeBatchesQ.isLoading}
          codificationImportPending={codificationImportM.isPending}
          codificationImportResult={codificationImportM.data ?? null}
          codificationImportError={codificationImportM.error instanceof Error ? codificationImportM.error.message : null}
          financeImportPending={financeImportM.isPending}
          financeImportResult={financeImportM.data ?? null}
          financeImportError={financeImportM.error instanceof Error ? financeImportM.error.message : null}
          deleteHistoryPending={deleteFinanceHistoryM.isPending}
          deleteHistoryResult={deleteFinanceHistoryM.data ?? null}
          deleteHistoryError={deleteFinanceHistoryM.error instanceof Error ? deleteFinanceHistoryM.error.message : null}
          saveSiteMappingPending={saveSiteMappingM.isPending}
          deleteSiteMappingPending={deleteSiteMappingM.isPending}
          saveNatureRulePending={saveNatureRuleM.isPending}
          deleteNatureRulePending={deleteNatureRuleM.isPending}
          saveContractReferencePending={saveContractReferenceM.isPending}
          deleteContractReferencePending={deleteContractReferenceM.isPending}
          invoiceActionPending={updateFinanceInvoiceM.isPending || exportLiaisonM.isPending || uploadEvidencePdfM.isPending || uploadRevisionEvidencePdfM.isPending || applyEvidenceIndicesM.isPending}
          indexSavePending={upsertRevisionIndexM.isPending}
          controlsPending={recalculateAllControlsM.isPending}
          onCodificationFile={(file) => codificationImportM.mutate(file)}
          onFinanceImportFile={(file) => financeImportM.mutate(file)}
          onDeleteHistory={() => deleteFinanceHistoryM.mutate()}
          onSaveSiteMapping={(payload) => saveSiteMappingM.mutate(payload)}
          onDeleteSiteMapping={(id) => deleteSiteMappingM.mutate(id)}
          onSaveNatureRule={(payload) => saveNatureRuleM.mutate(payload)}
          onDeleteNatureRule={(id) => deleteNatureRuleM.mutate(id)}
          onSaveContractReference={(payload) => saveContractReferenceM.mutate(payload)}
          onDeleteContractReference={(id) => deleteContractReferenceM.mutate(id)}
          onInvoiceStatus={(id, nextStatus) => updateFinanceInvoiceM.mutate({ id, status: nextStatus })}
          onExportLiaison={(invoice) => exportLiaisonM.mutate(invoice)}
          onUploadEvidencePdf={(invoiceId, file) => uploadEvidencePdfM.mutate({ invoiceId, file })}
          onUploadRevisionEvidencePdf={(file) => uploadRevisionEvidencePdfM.mutate(file)}
          onApplyEvidenceIndices={(evidenceId) => applyEvidenceIndicesM.mutate(evidenceId)}
          onSaveIndex={(payload) => upsertRevisionIndexM.mutate(payload)}
          onRecalculateAllControls={() => recalculateAllControlsM.mutate()}
          onExportGlobalControlReport={() => exportGlobalControlReportM.mutate()}
          exportGlobalControlReportPending={exportGlobalControlReportM.isPending}
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
          sub={`Ref. ${djuProfileLabel} : ${fmt(djuReference, 0)} DJU`}
          color={dju && dju.dju_total < djuReference ? "#f97316" : "#16a34a"}
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
      <CpeConsoSynthesePanel
        synthese={consoSynthese}
        isLoading={consoSyntheseQ.isLoading}
        isError={consoSyntheseQ.isError}
      />

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
            title="Importer l'export DALKIA consommation detaillee"
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

      {/* ── Intitulé : intéressement = gaz ── */}
      <div style={{ marginBottom: 8 }}>
        <h4 style={{ margin: "0 0 2px", fontSize: 15 }}>
          Intéressement énergétique — <span style={{ color: "#b45309" }}>Gaz (chauffage + ECS)</span>
        </h4>
        <p style={{ margin: 0, color: "#6b7280", fontSize: 12 }}>
          L'intéressement € porte sur le gaz uniquement (CCTPM §11). L'électricité est suivie plus bas
          (cible vs réel, hors intéressement).
        </p>
      </div>

      {/* ── Légende des colonnes ── */}
      <details style={{ marginBottom: 16, border: "1px solid #e5e7eb", borderRadius: 8, padding: "8px 12px", background: "#fbfcfe" }}>
        <summary style={{ cursor: "pointer", fontWeight: 600, fontSize: 13, color: "#374151" }}>
          Comprendre le tableau — définition des colonnes et nature du calcul
        </summary>
        <div style={{ marginTop: 10, fontSize: 12.5, color: "#374151", lineHeight: 1.55 }}>
          <p style={{ margin: "0 0 10px" }}>
            Ce tableau est le <strong>bilan d'intéressement énergétique annuel</strong> du marché CPE, calculé sur les
            données <strong>cumulées depuis le 1ᵉʳ janvier</strong> de l'année sélectionnée. En cours d'année (ex. après
            le T1 ou le T2), les valeurs sont <strong>partielles</strong> : elles reflètent le cumul à date, pas une
            projection de fin d'année. Le résultat ne devient <strong>ferme</strong> qu'avec 12 mois de relevés (statut
            <em> calculé</em>). C'est la différence avec un « atterrissage » trimestriel, qui projette la fin d'année —
            voir la note sous le tableau.
          </p>
          <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 14px", margin: 0 }}>
            <dt style={{ fontWeight: 700 }}>Tarif</dt>
            <dd style={{ margin: 0 }}>Tarif gaz contractuel du site (T1–T4, OS prix gaz). Détermine le prix unitaire Pu (€/MWh) du calcul.</dd>

            <dt style={{ fontWeight: 700 }}>NB année (MWhPCI)</dt>
            <dd style={{ margin: 0 }}>
              Consommation <strong>cible</strong> contractuelle de l'année (objectif), en MWh PCI. Badge{" "}
              <strong style={{ color: "#16a34a" }}>DLK</strong> = cible DALKIA importée pour l'année (révisée après travaux APE) ;{" "}
              <strong style={{ color: "#f97316" }}>SITE</strong> = valeur de secours du site (alignement code site à vérifier).
            </dd>

            <dt style={{ fontWeight: 700 }}>N'B corrigé</dt>
            <dd style={{ margin: 0 }}>
              Cible recalée du climat réel : <strong>N'B = NB × (DJU réels / {fmt(djuReference, 0)})</strong>. Un hiver plus froid (DJU élevés)
              relève la cible ; un hiver doux l'abaisse. C'est la cible « juste » à comparer au réel.
            </dd>

            <dt style={{ fontWeight: 700 }}>NC réel</dt>
            <dd style={{ margin: 0 }}>
              Consommation <strong>réellement mesurée</strong> (cumul), nette de l'eau chaude sanitaire :{" "}
              <strong>NC = QT − (m × qECS)</strong>. C'est la conso chauffage du site.
            </dd>

            <dt style={{ fontWeight: 700 }}>Écart</dt>
            <dd style={{ margin: 0 }}>
              <strong>N'B − NC</strong>. <span style={{ color: "#16a34a", fontWeight: 600 }}>Positif (vert)</span> = on consomme
              moins que la cible recalée → bonne performance.{" "}
              <span style={{ color: "#ef4444", fontWeight: 600 }}>Négatif (rouge)</span> = surconsommation. Le % = écart / N'B.
            </dd>

            <dt style={{ fontWeight: 700 }}>Résultat</dt>
            <dd style={{ margin: 0 }}>
              Qualification de l'écart : <strong>Intéressement</strong> (gain partagé, DALKIA facture la collectivité),{" "}
              <strong>Pénalité</strong> (DALKIA émet un avoir), équilibre, ou incomplet.
            </dd>

            <dt style={{ fontWeight: 700 }}>Montant HT</dt>
            <dd style={{ margin: 0 }}>
              Valorisation € de l'écart. Intéressement = <strong>½ × min(écart ; 15 % × N'B) × Pu</strong> (plafonné à 15 % de
              N'B). Pénalité = <strong>|écart| × Pu</strong> (100 %, sans plafond).
            </dd>

            <dt style={{ fontWeight: 700 }}>Mois</dt>
            <dd style={{ margin: 0 }}>
              Nombre de mois de relevés de consommation disponibles sur l'année (<strong>x/12</strong>). Moins de 12 = cumul
              partiel → résultat non définitif.
            </dd>

            <dt style={{ fontWeight: 700 }}>Statut</dt>
            <dd style={{ margin: 0 }}>
              <strong>calculé</strong> = 12 mois de relevés + prix + DJU disponibles (résultat ferme, compté dans les totaux) ;{" "}
              <strong>partiel</strong> = données incomplètes (résultat indicatif, exclu des totaux).
            </dd>
          </dl>
        </div>
      </details>

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
                <th style={thStyle}>NB année (MWhPCI)</th>
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
          <strong>DJU {annee} :</strong> {fmt(dju.dju_total, 0)} DJU chauffage base 18°C •{" "}
          {dju.nb_jours} jours collectés • Profil : {djuProfileLabel} • Source attendue : {djuStationLabel} /{" "}
          {dju.source_label ?? dju.source} • Référence : {fmt(djuReference, 0)} DJU ({djuReferencePeriod})
          {dju.dju_total < djuReference ? (
            <span style={{ color: "#f97316" }}> → Hiver doux : N'B sera inférieur à NB</span>
          ) : (
            <span style={{ color: "#16a34a" }}> → Hiver rigoureux : N'B sera supérieur à NB</span>
          )}
          {djuSourceWarning && (
            <p style={{ margin: "8px 0 0", color: "#b45309", fontWeight: 600 }}>
              Attention : ce profil est contractuel, mais la source actuellement calculee est indicative ({dju.source}).
              Avant usage opposable DALKIA, il faut brancher la station/source contractuelle Montpellier / METEOCLIM COSTIC.
            </p>
          )}
          {dju.notes && <p style={{ margin: "6px 0 0" }}>{dju.notes}</p>}
        </div>
      )}

      {/* ── Atterrissage trimestriel ── */}
      <AtterrissageCard
        data={atterrissageQ.data}
        isLoading={atterrissageQ.isLoading}
        annee={annee}
        trimestre={trimestre}
        setTrimestre={setTrimestre}
      />

      {/* ── Suivi performance électrique (hors intéressement) ── */}
      <ElecPerformanceCard data={elecPerfQ.data} isLoading={elecPerfQ.isLoading} annee={annee} />

      {/* ── Indicateur P2.4 (objectif global gaz+élec) ── */}
      <P24ObjectiveCard data={p24Q.data} isLoading={p24Q.isLoading} />
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

function MarketTrackingMatrix({
  title,
  subtitle,
  years,
  postes,
  totalsByYear,
  grandTotal,
  yearFrom,
  yearTo,
  p1Dpgf,
  quartersBilled,
  installmentsPerYear = 4,
}: {
  title: string;
  subtitle?: string;
  years: number[];
  postes: CpeMarketTrackingPoste[];
  totalsByYear: CpeMarketTrackingCell[];
  grandTotal: CpeMarketTrackingTotal;
  yearFrom: number;
  yearTo: number;
  p1Dpgf?: CpeP1Dpgf;
  quartersBilled?: CpeMarketTrackingQuarters[];
  installmentsPerYear?: number;
}) {
  const quartersByYear = new Map((quartersBilled ?? []).map((q) => [q.year, q] as [number, CpeMarketTrackingQuarters]));
  const chartData = postes.map((p) => ({
    poste: p.label,
    "Prévu": p.total.prevu,
    "Reçu": p.total.recu,
    "Taux": p.total.taux != null ? Math.round(p.total.taux * 1000) / 10 : null,
  }));
  return (
    <>
      <div className="kpi-grid">
        <KpiCard label="Enveloppe (prévu)" value={fmtEur(grandTotal.prevu)} sub={`${title} · ${yearFrom}–${yearTo}`} color="#1d4ed8" />
        <KpiCard label="Reçu (facturé)" value={fmtEur(grandTotal.recu)} sub="Factures DALKIA" color="#0f766e" />
        <KpiCard label="Écart reçu − prévu" value={fmtEur(grandTotal.ecart)} sub={grandTotal.ecart > 0 ? "Au-dessus du marché" : "Sous le marché"} color={grandTotal.ecart > 0 ? "#dc2626" : "#16a34a"} />
        <KpiCard label="Taux de réalisation" value={fmtPct(grandTotal.taux)} sub="Reçu / prévu" color="#7c3aed" />
      </div>

      <div className="card" style={{ padding: 12 }}>
        <h4 style={{ margin: "0 0 4px", fontSize: 14 }}>{title} — prévu vs reçu par poste ({yearFrom}–{yearTo})</h4>
        {subtitle && <p style={{ margin: "0 0 8px", color: "#6b7280", fontSize: 12 }}>{subtitle}</p>}
        <div style={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="poste" tick={{ fontSize: 11 }} interval={0} angle={-12} textAnchor="end" height={70} />
              <YAxis yAxisId="left" tickFormatter={(v) => `${Math.round(Number(v) / 1000).toLocaleString("fr-FR")} k€`} />
              <YAxis yAxisId="right" orientation="right" tickFormatter={(v) => `${v} %`} domain={[0, "auto"]} />
              <Tooltip formatter={(value, name) => (String(name).startsWith("Taux") ? (value == null ? "—" : `${Number(value).toFixed(1)} %`) : fmtEur(Number(value)))} />
              <Legend />
              <Bar yAxisId="left" dataKey="Prévu" fill="#94a3b8" />
              <Bar yAxisId="left" dataKey="Reçu" fill="#1d4ed8" />
              <Line yAxisId="right" type="monotone" dataKey="Taux" name="Taux (%)" stroke="#dc2626" strokeWidth={2} dot={{ r: 3 }} connectNulls />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card" style={{ padding: 12, overflowX: "auto" }}>
        <h4 style={{ margin: "0 0 4px", fontSize: 14 }}>Matrice poste × année — {title}</h4>
        <p style={{ margin: "0 0 8px", color: "#6b7280", fontSize: 12 }}>
          Chaque colonne = une <strong>année</strong>. <strong>Prévu</strong> = enveloppe contractuelle{" "}
          <strong>annuelle</strong> (DPGF). <strong>Reçu</strong> = cumul des <strong>acomptes trimestriels</strong>{" "}
          déjà facturés. Le <strong>Taux</strong> n'atteint 100 % qu'en fin d'exercice : voir la ligne
          « Trimestres facturés » pour savoir combien d'acomptes (sur {installmentsPerYear}) sont déjà reçus.
        </p>
        <table style={{ borderCollapse: "collapse", fontSize: 12, minWidth: 900 }}>
          <thead>
            <tr style={{ background: "#f9fafb" }}>
              <th rowSpan={2} style={{ ...thStyle, position: "sticky", left: 0, background: "#f9fafb" }}>Poste</th>
              {years.map((y) => (
                <th key={y} colSpan={4} style={{ ...thStyle, textAlign: "center", borderLeft: "1px solid #e5e7eb" }}>{y}</th>
              ))}
              <th colSpan={4} style={{ ...thStyle, textAlign: "center", borderLeft: "2px solid #cbd5e1", background: "#eef2ff" }}>Total {yearFrom}–{yearTo}</th>
            </tr>
            <tr style={{ background: "#f9fafb" }}>
              {years.map((y) => (
                <Fragment key={y}>
                  <th style={{ ...thStyle, textAlign: "right", borderLeft: "1px solid #e5e7eb" }}>Prévu</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Reçu</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Écart</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Taux</th>
                </Fragment>
              ))}
              <th style={{ ...thStyle, textAlign: "right", borderLeft: "2px solid #cbd5e1" }}>Prévu</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Reçu</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Écart</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Taux</th>
            </tr>
          </thead>
          <tbody>
            {quartersBilled && quartersBilled.length > 0 && (
              <tr style={{ borderTop: "1px solid #f3f4f6", background: "#fafafa" }}>
                <td style={{ ...tdStyle, fontStyle: "italic", color: "#6b7280", position: "sticky", left: 0, background: "#fafafa" }}>
                  Trimestres facturés
                </td>
                {years.map((y) => {
                  const q = quartersByYear.get(y);
                  const billed = q?.billed ?? 0;
                  const expected = q?.expected ?? installmentsPerYear;
                  const complete = billed >= expected;
                  return (
                    <td
                      key={y}
                      colSpan={4}
                      style={{
                        ...tdStyle,
                        textAlign: "center",
                        borderLeft: "1px solid #e5e7eb",
                        fontStyle: "italic",
                        color: billed === 0 ? "#9ca3af" : complete ? "#166534" : "#b45309",
                      }}
                    >
                      {billed}/{expected} trim.
                    </td>
                  );
                })}
                <td colSpan={4} style={{ ...tdStyle, borderLeft: "2px solid #cbd5e1" }} />
              </tr>
            )}
            {postes.map((p) => (
              <tr key={p.poste} style={{ borderTop: "1px solid #f3f4f6" }}>
                <td style={{ ...tdStyle, fontWeight: 600, position: "sticky", left: 0, background: "#fff" }}>{p.label}</td>
                {p.by_year.map((c) => (
                  <Fragment key={c.year}>
                    <td style={{ ...tdStyle, textAlign: "right", borderLeft: "1px solid #f3f4f6", color: "#6b7280" }}>{fmtEur(c.prevu)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmtEur(c.recu)}</td>
                    <td style={{ ...tdStyle, textAlign: "right", color: c.ecart > 0 ? "#b91c1c" : "#166534" }}>{fmtEur(c.ecart)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}><span className={`badge ${tauxClass(c.taux)}`}>{fmtPct(c.taux)}</span></td>
                  </Fragment>
                ))}
                <td style={{ ...tdStyle, textAlign: "right", borderLeft: "2px solid #cbd5e1", color: "#6b7280" }}>{fmtEur(p.total.prevu)}</td>
                <td style={{ ...tdStyle, textAlign: "right" }}>{fmtEur(p.total.recu)}</td>
                <td style={{ ...tdStyle, textAlign: "right", color: p.total.ecart > 0 ? "#b91c1c" : "#166534" }}>{fmtEur(p.total.ecart)}</td>
                <td style={{ ...tdStyle, textAlign: "right" }}><span className={`badge ${tauxClass(p.total.taux)}`}>{fmtPct(p.total.taux)}</span></td>
              </tr>
            ))}
            <tr style={{ borderTop: "2px solid #cbd5e1", background: "#f8fafc", fontWeight: 700 }}>
              <td style={{ ...tdStyle, position: "sticky", left: 0, background: "#f8fafc" }}>TOTAL</td>
              {totalsByYear.map((c) => (
                <Fragment key={c.year}>
                  <td style={{ ...tdStyle, textAlign: "right", borderLeft: "1px solid #e5e7eb" }}>{fmtEur(c.prevu)}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{fmtEur(c.recu)}</td>
                  <td style={{ ...tdStyle, textAlign: "right", color: c.ecart > 0 ? "#b91c1c" : "#166534" }}>{fmtEur(c.ecart)}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{fmtPct(c.taux)}</td>
                </Fragment>
              ))}
              <td style={{ ...tdStyle, textAlign: "right", borderLeft: "2px solid #cbd5e1" }}>{fmtEur(grandTotal.prevu)}</td>
              <td style={{ ...tdStyle, textAlign: "right" }}>{fmtEur(grandTotal.recu)}</td>
              <td style={{ ...tdStyle, textAlign: "right", color: grandTotal.ecart > 0 ? "#b91c1c" : "#166534" }}>{fmtEur(grandTotal.ecart)}</td>
              <td style={{ ...tdStyle, textAlign: "right" }}>{fmtPct(grandTotal.taux)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {p1Dpgf && p1Dpgf.has_data && (
        <div className="card" style={{ padding: 12, overflowX: "auto" }}>
          <h4 style={{ margin: "0 0 4px", fontSize: 14 }}>P1 gaz révisé (DPGF après OS) — {title}</h4>
          <p style={{ margin: "0 0 8px", color: "#6b7280", fontSize: 12 }}>
            Niveaux de révision issus du DPGF P1 (livrable séparé). <strong>Informatif</strong> : le « prévu P1 »
            de la matrice ci-dessus reste au niveau <em>contrat</em>. Tant qu'aucune révision n'est facturée,
            la base d'acompte retenue est « Rév Temp ».
          </p>
          <table style={{ borderCollapse: "collapse", fontSize: 12, minWidth: 700 }}>
            <thead>
              <tr style={{ background: "#f9fafb" }}>
                <th style={{ ...thStyle, position: "sticky", left: 0, background: "#f9fafb" }}>Niveau P1</th>
                {years.map((y) => (
                  <th key={y} style={{ ...thStyle, textAlign: "right", borderLeft: "1px solid #e5e7eb" }}>{y}</th>
                ))}
                <th style={{ ...thStyle, textAlign: "right", borderLeft: "2px solid #cbd5e1", background: "#eef2ff" }}>
                  Total {yearFrom}–{yearTo}
                </th>
              </tr>
            </thead>
            <tbody>
              {p1Dpgf.levels.map((lv) => {
                const byYear = new Map(lv.by_year.map((c) => [c.year, c.total] as [number, number]));
                const isContrat = lv.level === "contrat";
                return (
                  <tr key={lv.level} style={{ borderTop: "1px solid #f3f4f6" }}>
                    <td style={{ ...tdStyle, fontWeight: 600, position: "sticky", left: 0, background: "#fff" }}>
                      {lv.label}
                      {isContrat && <span style={{ color: "#6b7280", fontWeight: 400 }}> (= prévu P1)</span>}
                    </td>
                    {years.map((y) => (
                      <td key={y} style={{ ...tdStyle, textAlign: "right", borderLeft: "1px solid #f3f4f6", color: isContrat ? "#6b7280" : undefined }}>
                        {fmtEur(byYear.get(y) ?? 0)}
                      </td>
                    ))}
                    <td style={{ ...tdStyle, textAlign: "right", borderLeft: "2px solid #cbd5e1", fontWeight: 600 }}>
                      {fmtEur(lv.total)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function DjuBand({ dju }: { dju: CpeDju }) {
  // Couleur selon la rigueur : hiver plus froid que la réf (ratio>1) = orange/rouge ; plus doux = bleu.
  const ratioColor = (ratio: number | null) => {
    if (ratio == null) return "#6b7280";
    if (ratio >= 1.05) return "#b45309"; // hiver sensiblement plus rigoureux
    if (ratio <= 0.95) return "#1d4ed8"; // hiver plus doux
    return "#166534"; // proche de la référence
  };
  return (
    <div className="card" style={{ padding: 12, overflowX: "auto" }}>
      <h4 style={{ margin: "0 0 4px", fontSize: 14 }}>Rigueur climatique (DJU chauffage base 18 °C)</h4>
      <p style={{ margin: "0 0 8px", color: "#6b7280", fontSize: 12 }}>
        <strong>Informatif</strong> : compare les DJU réels de Sète à la référence contractuelle de{" "}
        <strong>{Math.round(dju.reference)} DJU</strong>. N'entre pas dans les montants ci-dessus, mais aide à
        lire un P1 reçu élevé (un hiver plus rigoureux → plus de consommation gaz). Source : {dju.source}.
      </p>
      <table style={{ borderCollapse: "collapse", fontSize: 12, minWidth: 600 }}>
        <thead>
          <tr style={{ background: "#f9fafb" }}>
            <th style={{ ...thStyle, position: "sticky", left: 0, background: "#f9fafb" }}>Année</th>
            {dju.by_year.map((d) => (
              <th key={d.year} style={{ ...thStyle, textAlign: "right", borderLeft: "1px solid #e5e7eb" }}>
                {d.year}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr style={{ borderTop: "1px solid #f3f4f6" }}>
            <td style={{ ...tdStyle, fontWeight: 600, position: "sticky", left: 0, background: "#fff" }}>DJU réel</td>
            {dju.by_year.map((d) => (
              <td key={d.year} style={{ ...tdStyle, textAlign: "right", borderLeft: "1px solid #f3f4f6" }}>
                {d.dju_real == null ? "—" : Math.round(d.dju_real).toLocaleString("fr-FR")}
                {d.dju_real != null && !d.complete ? <span style={{ color: "#9ca3af" }}> *</span> : null}
              </td>
            ))}
          </tr>
          <tr style={{ borderTop: "1px solid #f3f4f6" }}>
            <td style={{ ...tdStyle, fontWeight: 600, position: "sticky", left: 0, background: "#fff" }}>vs réf. {Math.round(dju.reference)}</td>
            {dju.by_year.map((d) => (
              <td key={d.year} style={{ ...tdStyle, textAlign: "right", borderLeft: "1px solid #f3f4f6", color: ratioColor(d.ratio), fontWeight: 600 }}>
                {d.ratio == null ? "—" : `${d.ratio >= 1 ? "+" : ""}${Math.round((d.ratio - 1) * 100)} %`}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
      {dju.by_year.some((d) => d.dju_real != null && !d.complete) ? (
        <p style={{ margin: "6px 0 0", color: "#9ca3af", fontSize: 11 }}>* année incomplète (moins de 12 mois de données) — ratio indicatif.</p>
      ) : null}
    </div>
  );
}

function AtterrissageCard({
  data,
  isLoading,
  annee,
  trimestre,
  setTrimestre,
}: {
  data: CpeAtterrissage | undefined;
  isLoading: boolean;
  annee: number;
  trimestre: number;
  setTrimestre: (t: number) => void;
}) {
  const TRIMESTRES = [
    { t: 1, label: "T1 (jan–mars)" },
    { t: 2, label: "T2 (→ juin)" },
    { t: 3, label: "T3 (→ sept)" },
    { t: 4, label: "T4 (année)" },
  ];
  const items: CpeAtterrissageItem[] = (data?.items ?? []).filter((i) => i.statut === "projete");
  return (
    <div className="card" style={{ marginTop: 24, padding: 12 }}>
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <h4 style={{ margin: "0 0 2px", fontSize: 14 }}>Atterrissage de fin d'année (projection {annee})</h4>
          <p style={{ margin: 0, color: "#6b7280", fontSize: 12 }}>
            Où atterrit-on au 31/12 vu le réalisé à date ? Projection <strong>pro-rata DJU</strong> (extrapolation
            climatique du réalisé, pas un pro-rata temporel). Pour les réunions trimestrielles DALKIA.
          </p>
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          {TRIMESTRES.map(({ t, label }) => (
            <button
              key={t}
              type="button"
              onClick={() => setTrimestre(t)}
              style={{
                padding: "4px 10px",
                borderRadius: 6,
                border: "1px solid",
                borderColor: trimestre === t ? "#2563eb" : "#d1d5db",
                background: trimestre === t ? "#2563eb" : "white",
                color: trimestre === t ? "white" : "#374151",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <p style={{ marginTop: 12 }}>Chargement…</p>
      ) : !data || !data.has_data ? (
        <p style={{ marginTop: 12, color: "#9ca3af", fontSize: 13 }}>
          Projection indisponible pour ce trimestre : il faut des relevés de consommation à date, un prix gaz et des
          DJU réels. (Importez le CSV DALKIA et vérifiez la synchro DJU.)
        </p>
      ) : (
        <>
          <div className="kpi-grid" style={{ marginTop: 12 }}>
            <KpiCard label="Intéressement projeté 31/12" value={fmtEur(data.total_interessement_projete)} sub={`${data.nb_sites_projetes} sites projetés`} color="#16a34a" />
            <KpiCard label="Pénalité projetée 31/12" value={fmtEur(data.total_penalite_projete)} sub="Avoir DALKIA" color="#ef4444" />
            <KpiCard label="Net projeté" value={fmtEur(data.net_projete)} sub={data.net_projete >= 0 ? "En faveur de DALKIA" : "En faveur de la Ville"} color={data.net_projete >= 0 ? "#16a34a" : "#ef4444"} />
            <KpiCard label="DJU projeté annuel" value={`${Math.round(data.dju_projete_annuel)} / ${Math.round(data.dju_reference)}`} sub={`réel ${Math.round(data.dju_reel_ecoule)} + normal ${Math.round(data.dju_normal_restant)}`} color="#2563eb" />
          </div>

          <p style={{ margin: "10px 0", color: "#6b7280", fontSize: 12 }}>
            Méthode : NC projeté = NC réalisé × (DJU projeté annuel / DJU réel à date) ; N'B projeté = NB × (DJU projeté
            / {Math.round(data.dju_reference)}). DJU des mois restants estimés par le profil climatique{" "}
            {data.dju_method === "fallback_reference" ? (
              <strong style={{ color: "#f97316" }}>de secours (référence/12 — pas d'historique DJU, projection dégradée)</strong>
            ) : (
              "normal (moyenne historique Open-Meteo)"
            )}
            . À caler sur la méthode DALKIA à réception de leur tableau.
          </p>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "2px solid #e5e7eb" }}>
                  <th style={thStyle}>Code</th>
                  <th style={thStyle}>Site</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>NB</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>N'B projeté</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>NC réalisé (à date)</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>NC projeté 31/12</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Écart projeté</th>
                  <th style={thStyle}>Résultat</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Montant projeté</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.site_id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={tdStyle}><code style={{ fontSize: 11, color: "#6b7280" }}>{it.code_site}</code></td>
                    <td style={{ ...tdStyle, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.nom_site}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(it.nb_exercice)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(it.n_prime_b_projete)}</td>
                    <td style={{ ...tdStyle, textAlign: "right", color: "#6b7280" }}>{fmt(it.nc_realise)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(it.nc_projete)}</td>
                    <td style={{ ...tdStyle, textAlign: "right", color: (it.ecart_projete ?? 0) >= 0 ? "#16a34a" : "#ef4444", fontWeight: 600 }}>
                      {it.ecart_projete == null ? "—" : `${it.ecart_projete > 0 ? "+" : ""}${fmt(it.ecart_projete)}`}
                    </td>
                    <td style={tdStyle}>
                      <span className={`badge ${TYPE_CLASS[it.type_resultat ?? ""] ?? "badge-gray"}`}>
                        {TYPE_LABEL[it.type_resultat ?? ""] ?? "—"}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right", fontWeight: 600, color: it.type_resultat === "interessement" ? "#16a34a" : it.type_resultat === "penalite" ? "#ef4444" : "#374151" }}>
                      {it.montant_ht_projete == null ? "—" : fmtEur(it.montant_ht_projete)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function P24ObjectiveCard({ data, isLoading }: { data: CpeP24Objective | undefined; isLoading: boolean }) {
  if (isLoading) {
    return <div className="card" style={{ marginTop: 24, padding: 12 }}><p>Chargement…</p></div>;
  }
  if (!data || !data.has_data) {
    return null; // pas de données -> pas d'indicateur
  }
  const atteint = data.objectif_atteint;
  return (
    <div className="card" style={{ marginTop: 24, padding: 12, borderLeft: `4px solid ${atteint ? "#16a34a" : "#dc2626"}` }}>
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <h4 style={{ margin: "0 0 2px", fontSize: 14 }}>
            Redevance P2.4 — objectif d'économie d'énergie global{" "}
            <span className={`badge ${atteint ? "badge-green" : "badge-red"}`}>
              {atteint ? "Atteint → 100 %" : "Non atteint → 50 %"}{data.complet ? "" : " (provisoire)"}
            </span>
          </h4>
          <p style={{ margin: 0, color: "#6b7280", fontSize: 12 }}>
            Conso réelle globale (gaz + élec) vs cible globale, gaz et élec ramenés à la période écoulée. Si la cible
            est tenue, P2.4 facturé à 100 % ; sinon 50 % (CCTPM §11.3).{" "}
            {data.complet ? "" : "⚠️ Cumul à date — verdict provisoire, définitif au décompte de fin d'exercice."}
            {data.elec_sites < data.elec_sites_avec_cible ? ` ⚠️ Couverture élec partielle (${data.elec_sites}/${data.elec_sites_avec_cible} sites avec conso) — le volet élec est sous-représenté.` : ""}
          </p>
        </div>
      </div>
      <div className="kpi-grid" style={{ marginTop: 10 }}>
        <KpiCard
          label="Économie vs cible (global)"
          value={`${data.economie_mwh >= 0 ? "+" : ""}${fmt(data.economie_mwh, 1)} MWh`}
          sub={data.economie_pct != null ? `${data.economie_pct >= 0 ? "+" : ""}${fmt(data.economie_pct * 100, 1)} %` : "—"}
          color={data.economie_mwh >= 0 ? "#16a34a" : "#dc2626"}
        />
        <KpiCard label="P2.4 contractuel (année)" value={fmtEur(data.p24_montant_ht)} sub="redevance pleine" color="#1d4ed8" />
        <KpiCard label="P2.4 facturable" value={fmtEur(data.p24_facturable_ht)} sub={`taux ${Math.round(data.p24_taux * 100)} %`} color={atteint ? "#16a34a" : "#dc2626"} />
        <KpiCard label="Montant à risque" value={fmtEur(data.p24_a_risque_ht)} sub="perdu si objectif manqué" color="#b45309" />
      </div>
      <div style={{ marginTop: 8, fontSize: 12, color: "#6b7280" }}>
        Détail : cible globale <strong>{fmt(data.global_cible_mwh, 1)} MWh</strong> (gaz {fmt(data.gas_cible_mwh, 1)} + élec {fmt(data.elec_cible_mwh, 1)}){" "}
        · réel <strong>{fmt(data.global_reel_mwh, 1)} MWh</strong> (gaz {fmt(data.gas_reel_mwh, 1)} + élec {fmt(data.elec_reel_mwh, 1)}){" "}
        · {data.gas_sites} sites gaz, {data.elec_sites} sites élec.
      </div>
    </div>
  );
}

function ElecPerformanceCard({ data, isLoading, annee }: { data: CpeElecPerf | undefined; isLoading: boolean; annee: number }) {
  // On affiche tous les sites qui ont une cible (suivi + sans conso), pour rendre la couverture visible.
  const items: CpeElecPerfItem[] = (data?.items ?? []).filter((i) => i.statut === "suivi" || i.statut === "sans_conso");
  const sansConso = (data?.nb_avec_cible ?? 0) - (data?.nb_suivis ?? 0);
  return (
    <div className="card" style={{ marginTop: 24, padding: 12 }}>
      <h4 style={{ margin: "0 0 2px", fontSize: 14 }}>Électricité — engagement (cible vs réel, {annee})</h4>
      <p style={{ margin: "0 0 8px", color: "#6b7280", fontSize: 12 }}>
        Suivi des consommations électriques par rapport aux cibles contractuelles (Annexe 5.2).{" "}
        <strong>Hors intéressement</strong> : l'électricité n'a pas d'intéressement € (CCTPM §11) — elle est vérifiée
        via le protocole <strong>IPMVP option B</strong> et pèse sur l'<strong>objectif global</strong> qui conditionne
        la redevance <strong>P2.4</strong> (100 % / 50 %). L'écart est calculé contre la cible{" "}
        <strong>au prorata des mois disponibles</strong> (sinon un cumul partiel paraît très sous la cible annuelle).
      </p>
      {data && data.has_data && sansConso > 0 ? (
        <p style={{ margin: "0 0 8px", padding: "6px 10px", background: "#fff7ed", borderRadius: 6, color: "#9a3412", fontSize: 12 }}>
          ⚠️ Couverture partielle : <strong>{data.nb_suivis}</strong> site(s) avec conso élec relevée sur{" "}
          <strong>{data.nb_avec_cible}</strong> ayant une cible. {sansConso} site(s) sans relevé élec (import conso
          incomplet) — listés ci-dessous avec conso « — ».
        </p>
      ) : null}
      {isLoading ? (
        <p>Chargement…</p>
      ) : !data || !data.has_data ? (
        <p style={{ color: "#9ca3af", fontSize: 13 }}>
          Aucun suivi élec disponible : il faut des cibles élec (import DALKIA Annexe 5.2) et des relevés de
          consommation électrique pour l'année.
        </p>
      ) : (
        <>
          <div className="kpi-grid">
            <KpiCard label="Cible élec au prorata" value={`${fmt(data.total_cible_periode_mwh, 1)} MWh`} sub={`${data.nb_suivis}/${data.nb_avec_cible} sites suivis · cible an. ${fmt(data.total_cible_mwh, 0)}`} color="#1d4ed8" />
            <KpiCard label="Conso élec réelle (cumul)" value={`${fmt(data.total_conso_mwh, 1)} MWh`} sub="à date" color="#0f766e" />
            <KpiCard
              label="Écart vs cible au prorata"
              value={`${data.total_ecart_mwh > 0 ? "+" : ""}${fmt(data.total_ecart_mwh, 1)} MWh`}
              sub={data.total_ecart_pct != null ? `${data.total_ecart_pct > 0 ? "+" : ""}${fmt(data.total_ecart_pct * 100, 0)} %` : "—"}
              color={data.total_ecart_mwh > 0 ? "#dc2626" : "#16a34a"}
            />
          </div>
          <div style={{ overflowX: "auto", marginTop: 8 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "2px solid #e5e7eb" }}>
                  <th style={thStyle}>Code</th>
                  <th style={thStyle}>Site</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Cible an. (MWh)</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Cible prorata</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Conso réelle</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Écart (vs prorata)</th>
                  <th style={{ ...thStyle, textAlign: "center" }}>Mois</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => {
                  const sansConso = it.statut === "sans_conso";
                  return (
                  <tr key={it.site_id} style={{ borderBottom: "1px solid #f3f4f6", background: sansConso ? "#fffdf7" : undefined }}>
                    <td style={tdStyle}><code style={{ fontSize: 11, color: "#6b7280" }}>{it.code_site}</code></td>
                    <td style={{ ...tdStyle, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.nom_site}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {fmt(it.cible_mwh, 1)}
                      <span title={it.cible_source === "dalkia" ? "Cible DALKIA (Annexe 5.2)" : "Valeur de secours du site"} style={{ marginLeft: 4, fontSize: 9, fontWeight: 700, color: it.cible_source === "dalkia" ? "#16a34a" : "#f97316", cursor: "help" }}>
                        {it.cible_source === "dalkia" ? "DLK" : "SITE"}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right", color: "#6b7280" }}>{fmt(it.cible_periode_mwh, 1)}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {sansConso ? <span style={{ color: "#f97316" }} title="Aucun relevé de conso élec importé pour ce site">— (pas de relevé)</span> : fmt(it.conso_reelle_mwh, 1)}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right", color: (it.ecart_mwh ?? 0) > 0 ? "#ef4444" : "#16a34a", fontWeight: 600 }}>
                      {it.ecart_mwh == null ? "—" : `${it.ecart_mwh > 0 ? "+" : ""}${fmt(it.ecart_mwh, 1)}`}
                      {it.ecart_pct != null ? ` (${it.ecart_pct > 0 ? "+" : ""}${fmt(it.ecart_pct * 100, 0)}%)` : ""}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "center", color: it.nb_mois < 12 ? "#f97316" : "#16a34a" }}>{it.nb_mois}/12</td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function P3AtterrissageChart({ data }: { data: CpeP3Atterrissage }) {
  const chartData = [
    { name: "Provision P3", Montant: data.provision_total },
    { name: "Engagé (devis)", Montant: data.engage_total },
  ];
  return (
    <div className="card" style={{ padding: 12 }}>
      <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>Atterrissage P3 {data.year} — engagé (devis) vs provision</h4>
      <div className="kpi-grid">
        <KpiCard label="Provision P3 (année)" value={fmtEur(data.provision_total)} sub={`P3 ${fmtEur(data.provision_p3)} + P3.4 ${fmtEur(data.provision_p3_4)}`} color="#1d4ed8" />
        <KpiCard label="Engagé (devis P3)" value={fmtEur(data.engage_total)} sub={`${data.devis_count} devis du périmètre`} color="#0f766e" />
        <KpiCard label="Reste provision" value={fmtEur(data.reste_provision)} sub={data.reste_provision < 0 ? "Dépassement" : "Disponible"} color={data.reste_provision < 0 ? "#dc2626" : "#16a34a"} />
        <KpiCard label="Taux d'engagement" value={data.taux_engagement != null ? fmtPct(data.taux_engagement) : "—"} sub="Engagé / provision" color="#7c3aed" />
      </div>
      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={(v) => `${Math.round(Number(v) / 1000).toLocaleString("fr-FR")} k€`} />
            <Tooltip formatter={(v) => fmtEur(Number(v))} />
            <Bar dataKey="Montant" fill="#1d4ed8" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      {data.by_etat.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, marginTop: 8 }}>
          <thead>
            <tr style={{ background: "#f9fafb" }}>
              <th style={{ ...thStyle, textAlign: "left" }}>État des devis</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Nombre</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Montant HT</th>
            </tr>
          </thead>
          <tbody>
            {data.by_etat.map((b) => (
              <tr key={b.etat} style={{ borderTop: "1px solid #f3f4f6" }}>
                <td style={tdStyle}>{b.etat}</td>
                <td style={{ ...tdStyle, textAlign: "right" }}>{b.count}</td>
                <td style={{ ...tdStyle, textAlign: "right" }}>{fmtEur(b.montant_ht)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function CpeConsoSynthesePanel({
  synthese,
  isLoading,
  isError,
}: {
  synthese: CpeConsoSynthese | undefined;
  isLoading: boolean;
  isError: boolean;
}) {
  const fluidLabel: Record<string, string> = {
    GAZ: "Gaz",
    ELEC: "Electricite",
    CHALEUR: "Chaleur",
    ECS: "ECS",
    EAU: "Eau",
  };
  const unknownSites = synthese?.sites_inconnus.slice(0, 6) ?? [];
  const missingSites = synthese?.sites_sans_conso.slice(0, 6) ?? [];

  return (
    <div className="card" style={{ marginBottom: 16, padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", marginBottom: 12 }}>
        <div>
          <h4 style={{ margin: "0 0 4px", fontSize: 15 }}>Synthese consommations multi-fluides</h4>
          <p style={{ margin: 0, color: "#6b7280", fontSize: 13 }}>
            Export DALKIA detaille consolide par fluide, site et mois.
          </p>
        </div>
        <div style={{ textAlign: "right", fontSize: 13, color: "#374151" }}>
          <strong>{synthese ? `${synthese.nb_sites_couverts} / ${synthese.nb_sites_actifs}` : "-"}</strong>
          <div style={{ color: "#9ca3af" }}>sites couverts</div>
        </div>
      </div>

      {isLoading ? (
        <p style={{ margin: 0, color: "#6b7280", fontSize: 13 }}>Chargement des consommations...</p>
      ) : isError ? (
        <p style={{ margin: 0, color: "#ef4444", fontSize: 13 }}>Synthese indisponible. Verifiez que la migration 0040 est appliquee.</p>
      ) : !synthese || synthese.fluides.length === 0 ? (
        <p style={{ margin: 0, color: "#9ca3af", fontSize: 13 }}>
          Aucune consommation multi-fluides importee pour l'annee selectionnee.
        </p>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10, marginBottom: 14 }}>
            {synthese.fluides.map((fluide) => (
              <div key={fluide.fluide} style={{ border: "1px solid #e5e7eb", borderRadius: 6, padding: 10 }}>
                <div style={{ fontSize: 12, color: "#6b7280" }}>{fluidLabel[fluide.fluide] ?? fluide.fluide}</div>
                <div style={{ fontWeight: 700, color: "#111827", marginTop: 4 }}>
                  {fmt(fluide.total, fluide.unite === "m3" ? 0 : 1)} {fluide.unite}
                </div>
                <div style={{ color: "#9ca3af", fontSize: 12, marginTop: 2 }}>
                  {fluide.nb_sites} sites - {fluide.nb_mois} mois
                  {fluide.nb_estimes > 0 ? ` - ${fluide.nb_estimes} estimes` : ""}
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12 }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>
                Codes DALKIA non rattaches ({synthese.nb_sites_inconnus})
              </div>
              {unknownSites.length === 0 ? (
                <p style={{ margin: 0, color: "#16a34a", fontSize: 13 }}>Aucun code non rattache sur cette annee.</p>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <tbody>
                    {unknownSites.map((site) => (
                      <tr key={site.code_site} style={{ borderTop: "1px solid #f3f4f6" }}>
                        <td style={{ padding: "6px 4px", fontWeight: 600 }}>{site.code_site}</td>
                        <td style={{ padding: "6px 4px", color: "#6b7280" }}>{site.fluides.join(", ")}</td>
                        <td style={{ padding: "6px 4px", textAlign: "right", color: "#9ca3af" }}>{site.nb_mois} mois</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>
                Sites actifs sans consommation ({synthese.nb_sites_sans_conso})
              </div>
              {missingSites.length === 0 ? (
                <p style={{ margin: 0, color: "#16a34a", fontSize: 13 }}>Tous les sites actifs ont au moins une consommation.</p>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <tbody>
                    {missingSites.map((site) => (
                      <tr key={site.site_id} style={{ borderTop: "1px solid #f3f4f6" }}>
                        <td style={{ padding: "6px 4px", fontWeight: 600 }}>
                          <Link to={`/cpe/sites/${site.site_id}`} style={{ color: "#2563eb", textDecoration: "none" }}>
                            {site.code_site}
                          </Link>
                        </td>
                        <td style={{ padding: "6px 4px", color: "#6b7280" }}>{site.nom_site}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </>
      )}
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

const EMPTY_CONTRACT_REFERENCE = {
  contract_code: "",
  contract_label: "",
  reference_kind: "cpe_contract_scope",
  year: CURRENT_YEAR,
  market: "SCOPE",
  billed_item: "",
  annual_amount_ht: "",
  expected_amount_ht: "",
  installment_count: "",
  expected_period_months: "",
  included_billed_items: "",
  formula: "",
  tolerance_pct: "",
  tolerance_eur: "",
  notes: "",
  active: true,
};

function CpeFinanceReference({
  annee,
  codificationFileRef,
  financeImportFileRef,
  siteMappings,
  natureRules,
  contractReferences,
  batches,
  invoices,
  indices,
  revisionObservations,
  revisionEvidences,
  controlReport,
  loading,
  codificationImportPending,
  codificationImportResult,
  codificationImportError,
  financeImportPending,
  financeImportResult,
  financeImportError,
  deleteHistoryPending,
  deleteHistoryResult,
  deleteHistoryError,
  saveSiteMappingPending,
  deleteSiteMappingPending,
  saveNatureRulePending,
  deleteNatureRulePending,
  saveContractReferencePending,
  deleteContractReferencePending,
  invoiceActionPending,
  indexSavePending,
  controlsPending,
  onCodificationFile,
  onFinanceImportFile,
  onDeleteHistory,
  onSaveSiteMapping,
  onDeleteSiteMapping,
  onSaveNatureRule,
  onDeleteNatureRule,
  onSaveContractReference,
  onDeleteContractReference,
  onInvoiceStatus,
  onExportLiaison,
  onUploadEvidencePdf,
  onUploadRevisionEvidencePdf,
  onApplyEvidenceIndices,
  onSaveIndex,
  onRecalculateAllControls,
  onExportGlobalControlReport,
  exportGlobalControlReportPending,
}: {
  annee: number;
  codificationFileRef: React.RefObject<HTMLInputElement>;
  financeImportFileRef: React.RefObject<HTMLInputElement>;
  siteMappings: CpeAccountingSiteMapping[];
  natureRules: CpeAccountingNatureRule[];
  contractReferences: CpeContractReference[];
  batches: CpeFinanceImportBatch[];
  invoices: CpeFinanceInvoice[];
  indices: CpeRevisionIndex[];
  revisionObservations: CpeRevisionObservation[];
  revisionEvidences: CpeInvoiceEvidence[];
  controlReport: CpeFinanceControlReport | null;
  loading: boolean;
  codificationImportPending: boolean;
  codificationImportResult: CpeAccountingImportResult | null;
  codificationImportError: string | null;
  financeImportPending: boolean;
  financeImportResult: CpeFinanceImportResult | null;
  financeImportError: string | null;
  deleteHistoryPending: boolean;
  deleteHistoryResult: { batches_deleted: number; invoices_deleted: number; lines_deleted: number; controls_deleted: number } | null;
  deleteHistoryError: string | null;
  saveSiteMappingPending: boolean;
  deleteSiteMappingPending: boolean;
  saveNatureRulePending: boolean;
  deleteNatureRulePending: boolean;
  saveContractReferencePending: boolean;
  deleteContractReferencePending: boolean;
  invoiceActionPending: boolean;
  indexSavePending: boolean;
  controlsPending: boolean;
  onCodificationFile: (file: File) => void;
  onFinanceImportFile: (file: File) => void;
  onDeleteHistory: () => void;
  onSaveSiteMapping: (payload: Partial<CpeAccountingSiteMapping> & { id?: number; code_site: string; site_name: string }) => void;
  onDeleteSiteMapping: (id: number) => void;
  onSaveNatureRule: (
    payload: Partial<CpeAccountingNatureRule> & { id?: number; market: string; billed_item: string; accounting_nature: string },
  ) => void;
  onDeleteNatureRule: (id: number) => void;
  onSaveContractReference: (
    payload: Partial<CpeContractReference> & { id?: number; contract_code: string; reference_kind: string; year: number; market: string; billed_item: string },
  ) => void;
  onDeleteContractReference: (id: number) => void;
  onInvoiceStatus: (id: number, nextStatus: string) => void;
  onExportLiaison: (invoice: CpeFinanceInvoice) => void;
  onUploadEvidencePdf: (invoiceId: number, file: File) => void;
  onUploadRevisionEvidencePdf: (file: File) => void;
  onApplyEvidenceIndices: (evidenceId: number) => void;
  onSaveIndex: (payload: { index_code: string; year: number; quarter: number; value: number; source?: string | null; verification_status?: string; evidence_id?: number | null; notes?: string | null }) => void;
  onRecalculateAllControls: () => void;
  onExportGlobalControlReport: () => void;
  exportGlobalControlReportPending: boolean;
}) {
  const [draft, setDraft] = useState(EMPTY_SITE_MAPPING);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [ruleDraft, setRuleDraft] = useState(EMPTY_NATURE_RULE);
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);
  const [referenceDraft, setReferenceDraft] = useState(EMPTY_CONTRACT_REFERENCE);
  const [editingReferenceId, setEditingReferenceId] = useState<number | null>(null);
  const [section, setSection] = useState<CpeFinanceSection>("imports");
  const [evidenceInvoiceId, setEvidenceInvoiceId] = useState<number | null>(null);
  const [queueSort, setQueueSort] = useState<{ key: QueueSortKey; dir: "asc" | "desc" }>({ key: "error", dir: "desc" });
  const { token: financeToken } = useAuth();
  const [marketYearFrom, setMarketYearFrom] = useState(2026);
  const [marketYearTo, setMarketYearTo] = useState(2030);
  const [marketExportPending, setMarketExportPending] = useState(false);
  const marketTrackingQ = useQuery({
    queryKey: ["cpe-market-tracking", marketYearFrom, marketYearTo],
    queryFn: () => fetchCpeMarketTracking(financeToken!, marketYearFrom, marketYearTo),
    enabled: !!financeToken && section === "invoices",
  });
  const marketTracking = marketTrackingQ.data ?? null;
  const onExportMarketTracking = async () => {
    if (!financeToken) return;
    setMarketExportPending(true);
    try {
      const blob = await downloadCpeMarketTracking(financeToken, marketYearFrom, marketYearTo);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `suivi-marche-cpe-${marketYearFrom}-${marketYearTo}.xlsx`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } finally {
      setMarketExportPending(false);
    }
  };
  const evidencePdfRef = useRef<HTMLInputElement>(null);
  const revisionEvidencePdfRef = useRef<HTMLInputElement>(null);
  const p3DevisFileRef = useRef<HTMLInputElement>(null);
  const financeQc = useQueryClient();
  const p3DevisQ = useQuery({
    queryKey: ["cpe-p3-devis"],
    queryFn: () => fetchCpeP3Devis(financeToken!, true),
    enabled: !!financeToken && section === "p3-devis",
  });
  const p3AtterrissageQ = useQuery({
    queryKey: ["cpe-p3-atterrissage", marketYearFrom],
    queryFn: () => fetchCpeP3Atterrissage(financeToken!, marketYearFrom),
    enabled: !!financeToken && (section === "p3-devis" || section === "invoices"),
  });
  const [p3ImportMsg, setP3ImportMsg] = useState<string | null>(null);
  const importP3DevisM = useMutation({
    mutationFn: (file: File) => importCpeP3Devis(financeToken!, file),
    onSuccess: (res) => {
      setP3ImportMsg(`Devis importés : ${res.in_scope} dans le périmètre (Commune), ${res.out_of_scope} hors périmètre ignorés.`);
      financeQc.invalidateQueries({ queryKey: ["cpe-p3-devis"] });
      financeQc.invalidateQueries({ queryKey: ["cpe-p3-atterrissage"] });
    },
    onError: (err) => setP3ImportMsg(err instanceof Error ? err.message : "Erreur d'import des devis."),
  });
  const p3Devis = p3DevisQ.data ?? [];
  const p3Atterrissage = p3AtterrissageQ.data ?? null;
  const [siteFilter, setSiteFilter] = useState("");
  const [ruleFilter, setRuleFilter] = useState("");
  const [referenceFilter, setReferenceFilter] = useState("");
  const [indexDraft, setIndexDraft] = useState({
    index_code: "ICHT_IME",
    year: annee,
    quarter: 1,
    value: "",
    source: "Saisie Po2",
    verification_status: "to_verify",
    evidence_id: null as number | null,
    notes: "",
  });
  const invoiceById = useMemo(() => new Map(invoices.map((invoice) => [invoice.id, invoice])), [invoices]);
  const sortedQueueInvoices = useMemo(() => {
    const rows = controlReport?.invoices ? [...controlReport.invoices] : [];
    const { key, dir } = queueSort;
    const mul = dir === "asc" ? 1 : -1;
    const accessor: Record<QueueSortKey, (row: QueueInvoice) => string | number> = {
      invoice_number: (row) => row.invoice_number,
      contract: (row) => row.contract_label ?? row.contract_code ?? "",
      invoice_type: (row) => row.invoice_type ?? "",
      recipient_ref: (row) => row.recipient_ref ?? "",
      market: (row) => row.market ?? "",
      billed_items: (row) => row.billed_items ?? "",
      total_ht: (row) => row.total_ht ?? 0,
      ok: (row) => row.ok,
      error: (row) => row.error,
      blocked: (row) => row.blocked,
      families: (row) => row.control_types.join(", "),
      due_date: (row) => (row.due_in_days == null ? Number.POSITIVE_INFINITY : row.due_in_days),
      invoice_status: (row) => row.invoice_status,
    };
    const get = accessor[key];
    rows.sort((a, b) => {
      const va = get(a);
      const vb = get(b);
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * mul;
      return String(va).localeCompare(String(vb), "fr", { numeric: true }) * mul;
    });
    return rows;
  }, [controlReport, queueSort]);
  const toggleQueueSort = (key: QueueSortKey) =>
    setQueueSort((prev) => (prev.key === key ? { key, dir: prev.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }));
  const queueSortIndicator = (key: QueueSortKey) =>
    queueSort.key === key ? (queueSort.dir === "asc" ? " ▲" : " ▼") : "";
  const controlStatusChartData = useMemo(
    () =>
      controlReport
        ? [
            { label: "Factures conformes", value: controlReport.invoices_ok, color: "#16a34a" },
            { label: "Avec écarts", value: controlReport.invoices_with_errors, color: "#dc2626" },
            { label: "Bloquées", value: controlReport.invoices_blocked, color: "#f59e0b" },
          ]
        : [],
    [controlReport],
  );
  const controlTypeChartData = useMemo(
    () =>
      (controlReport?.control_types ?? [])
        .filter((item) => item.error > 0 || item.blocked > 0)
        .map((item) => ({
          type: CONTROL_TYPE_LABELS[item.control_type] ?? item.control_type,
          error: item.error,
          blocked: item.blocked,
        }))
        .sort((left, right) => right.error + right.blocked - (left.error + left.blocked)),
    [controlReport],
  );
  const visibleSiteMappings = siteMappings
    .filter((mapping) => {
      const haystack = [
        mapping.code_site,
        mapping.site_name,
        mapping.family,
        mapping.manager,
        mapping.service_code,
        mapping.service_label,
        mapping.function_code,
        mapping.function_label,
        mapping.antenna_code,
        mapping.antenna_label,
        mapping.operation_code,
        mapping.operation_label,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(siteFilter.trim().toLowerCase());
    })
    .slice(0, 220);
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
  const visibleReferences = contractReferences
    .filter((reference) => {
      const haystack = [
        reference.contract_code,
        reference.contract_label,
        reference.reference_kind,
        reference.year,
        reference.market,
        reference.billed_item,
        reference.included_billed_items,
        reference.notes,
      ]
        .filter((value) => value != null)
        .join(" ")
        .toLowerCase();
      return haystack.includes(referenceFilter.trim().toLowerCase());
    })
    .slice(0, 120);
  const sortedIndices = useMemo(
    () =>
      [...indices].sort((left, right) => {
        if (left.year !== right.year) return right.year - left.year;
        if (left.quarter !== right.quarter) return right.quarter - left.quarter;
        return left.index_code.localeCompare(right.index_code, "fr");
      }),
    [indices],
  );

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

  const startReferenceEdit = (reference: CpeContractReference) => {
    setEditingReferenceId(reference.id);
    setReferenceDraft({
      contract_code: reference.contract_code,
      contract_label: reference.contract_label ?? "",
      reference_kind: reference.reference_kind,
      year: reference.year,
      market: reference.market,
      billed_item: reference.billed_item,
      annual_amount_ht: reference.annual_amount_ht?.toString() ?? "",
      expected_amount_ht: reference.expected_amount_ht?.toString() ?? "",
      installment_count: reference.installment_count?.toString() ?? "",
      expected_period_months: reference.expected_period_months ?? "",
      included_billed_items: reference.included_billed_items ?? "",
      formula: reference.formula ?? "",
      tolerance_pct: reference.tolerance_pct?.toString() ?? "",
      tolerance_eur: reference.tolerance_eur?.toString() ?? "",
      notes: reference.notes ?? "",
      active: reference.active,
    });
  };

  const resetReferenceDraft = () => {
    setEditingReferenceId(null);
    setReferenceDraft(EMPTY_CONTRACT_REFERENCE);
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

  const submitReferenceDraft = () => {
    if (!referenceDraft.contract_code.trim() || !referenceDraft.reference_kind.trim() || !referenceDraft.year || !referenceDraft.market.trim() || !referenceDraft.billed_item.trim()) return;
    const numberOrNull = (value: string | number | null | undefined) => {
      if (value === null || value === undefined || value === "") return null;
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    };
    onSaveContractReference({
      ...(editingReferenceId ? { id: editingReferenceId } : {}),
      contract_code: referenceDraft.contract_code.trim().toUpperCase(),
      contract_label: referenceDraft.contract_label.trim() || null,
      reference_kind: referenceDraft.reference_kind.trim().toLowerCase(),
      year: Number(referenceDraft.year),
      market: referenceDraft.market.trim().toUpperCase(),
      billed_item: referenceDraft.billed_item.trim().toUpperCase(),
      annual_amount_ht: numberOrNull(referenceDraft.annual_amount_ht),
      expected_amount_ht: numberOrNull(referenceDraft.expected_amount_ht),
      installment_count: numberOrNull(referenceDraft.installment_count),
      expected_period_months: referenceDraft.expected_period_months.trim() || null,
      included_billed_items: referenceDraft.included_billed_items.trim() || null,
      formula: referenceDraft.formula.trim() || null,
      tolerance_pct: numberOrNull(referenceDraft.tolerance_pct),
      tolerance_eur: numberOrNull(referenceDraft.tolerance_eur),
      notes: referenceDraft.notes.trim() || null,
      active: referenceDraft.active,
    });
    resetReferenceDraft();
  };

  return (
    <>
      <section style={{ marginBottom: 24 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16 }}>
          <KpiCard label="Sites codifies" value={String(siteMappings.length)} sub="Lignes du referentiel finance" color="#2563eb" />
          <KpiCard label="Regles nature" value={String(natureRules.length)} sub="Poste facture vers nature" color="#0f766e" />
          <KpiCard label="References contrat" value={String(contractReferences.length)} sub="DPGF, formules et tolerances" color="#7c3aed" />
          <KpiCard label="Indices revision" value={String(indices.length)} sub="References de base + valeurs trimestrielles (toutes annees)" color="#b45309" />
          <KpiCard label="Lots importes" value={String(batches.length)} sub={`${invoices.length} facture(s) archivees`} color="#9333ea" />
          <KpiCard
            label="Dernier lot"
            value={batches[0] ? fmtEur(batches[0].total_ht) : "Aucun"}
            sub={batches[0] ? `${batches[0].line_count} ligne(s), ${batches[0].invoice_count} facture(s)` : "Import finances a lancer"}
            color="#111827"
          />
        </div>
      </section>

      <nav
        aria-label="Navigation referentiel finance CPE"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
          gap: 10,
          marginBottom: 24,
        }}
      >
        {CPE_FINANCE_SECTIONS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={section === item.id ? "primary-button" : "secondary-button"}
            onClick={() => setSection(item.id)}
            style={{ display: "grid", gap: 2, justifyItems: "start", minHeight: 58, textAlign: "left" }}
          >
            <span>{item.label}</span>
            <span style={{ fontSize: 12, fontWeight: 400, opacity: 0.72 }}>{item.detail}</span>
          </button>
        ))}
      </nav>

      {section === "imports" && (
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
            <button type="button" className="secondary-button" onClick={() => p3DevisFileRef.current?.click()} disabled={importP3DevisM.isPending}>
              {importP3DevisM.isPending ? "Import..." : "Importer devis P3"}
            </button>
            <input
              ref={p3DevisFileRef}
              type="file"
              accept=".csv"
              style={{ display: "none" }}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) importP3DevisM.mutate(file);
                event.target.value = "";
              }}
            />
          </div>
        </div>
        {p3ImportMsg && (
          <p style={{ color: "#166534", fontSize: 13, margin: "12px 0 0" }}>{p3ImportMsg}</p>
        )}
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
      )}

      {section === "indices" && (
      <section className="card" style={{ padding: 16, marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <h3 style={{ margin: "0 0 4px" }}>Formules contractuelles et indices de revision</h3>
            <p style={{ margin: 0, color: "#6b7280", fontSize: 13 }}>
              Centralise les regles P1, P2, P3, les coefficients observes et les preuves PDF DALKIA.
            </p>
          </div>
          <button type="button" className="primary-button" onClick={() => revisionEvidencePdfRef.current?.click()} disabled={invoiceActionPending}>
            Importer PDF justificatif
          </button>
          <input
            ref={revisionEvidencePdfRef}
            type="file"
            accept=".pdf,application/pdf"
            style={{ display: "none" }}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) onUploadRevisionEvidencePdf(file);
              event.target.value = "";
            }}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 10, marginBottom: 18 }}>
          {[
            ["P1 gaz", "P1 = QT x Pugaz", "PEG, TVD, CEE, TICGN et OS gaz applicables."],
            ["P2", "P2 = P20 x (0,15 + 0,70 x ICHT-IME / ICHT-IME0 + 0,15 x FSD2 / FSD20)", "Formule commune P2. Taux horaires BPU revises comme le P2."],
            ["P3", "P3 = P30 x (0,15 + 0,30 x ICHT-IME / ICHT-IME0 + 0,55 x BT40 / BT400)", "Formule commune P3.1 a P3.4 confirmee apres mise au point."],
            ["Regles associees", "P2.4, BPU et compte P3", "P2.4 annuel a 100% ou 50%. Coefficients materiels et sous-traitance BPU fixes."],
          ].map(([title, formula, detail]) => (
            <div key={title} style={{ border: "1px solid #e5e7eb", borderRadius: 6, padding: 12, background: "#f9fafb" }}>
              <strong style={{ display: "block", marginBottom: 6 }}>{title}</strong>
              <div style={{ color: "#1f2937", fontSize: 12, marginBottom: 6 }}>{formula}</div>
              <div style={{ color: "#6b7280", fontSize: 12 }}>{detail}</div>
            </div>
          ))}
        </div>

        {revisionObservations.length > 0 && (
          <div style={{ marginBottom: 18 }}>
            <h3 style={{ margin: "0 0 4px" }}>Coefficients observes dans les factures DALKIA</h3>
            <p style={{ margin: "0 0 10px", color: "#6b7280", fontSize: 13 }}>
              Ces coefficients sont deduits des prix de base et revises importes. Ils servent d'alerte et de preuve de rapprochement,
              mais ne remplacent pas la validation des indices depuis une source officielle ou la facture PDF.
            </p>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                    <th style={thStyle}>Poste</th>
                    <th style={thStyle}>Periode</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Facteur DALKIA</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Facteur indices valides</th>
                    <th style={thStyle}>Statut</th>
                    <th style={thStyle}>Factures sources</th>
                  </tr>
                </thead>
                <tbody>
                  {revisionObservations.map((observation) => (
                    <tr
                      key={`${observation.market}-${observation.year}-${observation.quarter}-${observation.observed_factor}`}
                      style={{ borderBottom: "1px solid #f3f4f6" }}
                    >
                      <td style={tdStyle}>{observation.market}</td>
                      <td style={tdStyle}>{observation.year} T{observation.quarter}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(observation.observed_factor, 6)}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>
                        {observation.expected_factor == null ? "-" : fmt(observation.expected_factor, 6)}
                      </td>
                      <td style={tdStyle}>
                        <span
                          className={
                            observation.status === "matches_validated"
                              ? "badge-green"
                              : observation.status === "conflict"
                                ? "badge-red"
                                : "badge-orange"
                          }
                          title={observation.message}
                        >
                          {observation.status === "matches_validated"
                            ? "Rapproche"
                            : observation.status === "conflict"
                              ? "A verifier"
                              : "Nouveau"}
                        </span>
                      </td>
                      <td style={tdStyle} title={observation.invoice_numbers.join(", ")}>
                        {observation.invoice_numbers.slice(0, 3).join(", ")}
                        {observation.invoice_numbers.length > 3 ? ` +${observation.invoice_numbers.length - 3}` : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        <div style={{ marginBottom: 18 }}>
          <h3 style={{ margin: "0 0 4px" }}>Pieces justificatives de revision</h3>
          <p style={{ margin: "0 0 10px", color: "#6b7280", fontSize: 13 }}>
            Les valeurs extraites restent declarees par DALKIA jusqu'a verification explicite depuis une source officielle.
          </p>
          {revisionEvidences.length === 0 ? (
            <span style={{ color: "#9ca3af", fontSize: 13 }}>Aucun justificatif importe.</span>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                    <th style={thStyle}>Document</th>
                    <th style={thStyle}>Facture detectee</th>
                    <th style={thStyle}>Revision</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Coefficient</th>
                    <th style={thStyle}>Indices declares</th>
                    <th style={thStyle}>Statut</th>
                    <th style={thStyle}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {revisionEvidences.map((evidence) => (
                    <tr key={evidence.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                      <td style={tdStyle}>{evidence.original_filename}</td>
                      <td style={tdStyle}>{evidence.declared_invoice_number ?? "-"}</td>
                      <td style={tdStyle}>{evidence.revision_date ?? "-"}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>{evidence.declared_factor == null ? "-" : fmt(evidence.declared_factor, 6)}</td>
                      <td style={tdStyle}>
                        {[
                          evidence.declared_icht_ime == null ? null : `ICHT-IME ${fmt(evidence.declared_icht_ime, 3)}`,
                          evidence.declared_fsd2 == null ? null : `FSD2 ${fmt(evidence.declared_fsd2, 3)}`,
                          evidence.declared_bt40 == null ? null : `BT40 ${fmt(evidence.declared_bt40, 3)}`,
                        ].filter(Boolean).join(" / ") || "-"}
                      </td>
                      <td style={tdStyle}><span className="badge-orange">Declare DALKIA - a verifier</span></td>
                      <td style={tdStyle}>
                        <button type="button" className="secondary-button" style={{ fontSize: 12, padding: "3px 8px" }} onClick={() => onApplyEvidenceIndices(evidence.id)} disabled={invoiceActionPending}>
                          Appliquer les indices declares
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", marginBottom: 12 }}>
          <div>
            <h3 style={{ margin: "0 0 4px" }}>Indices et references de base (P1 / P2 / P3)</h3>
            <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>
              Saisie unique de toutes les valeurs de revision: bases contractuelles et indices trimestriels multi-annees.
            </p>
          </div>
          <div style={{ display: "grid", gap: 8, justifyItems: "end" }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
            <select
              value={indexDraft.index_code}
              onChange={(event) => setIndexDraft({ ...indexDraft, index_code: event.target.value })}
              style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db" }}
            >
              {REVISION_INDEX_CODE_OPTIONS.map((option) => (
                <option key={option.code} value={option.code}>{option.label}</option>
              ))}
            </select>
            <input
              type="number"
              step="1"
              value={indexDraft.year}
              onChange={(event) => setIndexDraft({ ...indexDraft, year: Number(event.target.value) || CURRENT_YEAR })}
              placeholder="Annee"
              style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db", width: 90 }}
            />
            <select
              value={indexDraft.quarter}
              onChange={(event) => setIndexDraft({ ...indexDraft, quarter: Number(event.target.value) })}
              style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db" }}
            >
              <option value={0}>Base / ref</option>
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
                  year: Number(indexDraft.year),
                  quarter: indexDraft.quarter,
                  value: Number(indexDraft.value),
                  source: indexDraft.source,
                  verification_status: indexDraft.verification_status,
                  evidence_id: indexDraft.evidence_id,
                  notes: indexDraft.notes || null,
                });
                setIndexDraft({ ...indexDraft, value: "", evidence_id: null, notes: "" });
              }}
            >
              Enregistrer indice
            </button>
          </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
              <input
                value={indexDraft.source}
                onChange={(event) => setIndexDraft({ ...indexDraft, source: event.target.value })}
                placeholder="Source"
                style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db", width: 210 }}
              />
              <select
                value={indexDraft.verification_status}
                onChange={(event) => setIndexDraft({ ...indexDraft, verification_status: event.target.value })}
                style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db" }}
              >
                <option value="to_verify">A verifier</option>
                <option value="declared_to_verify">Declare DALKIA - a verifier</option>
                <option value="official_verified">Officiel verifie</option>
              </select>
              <input
                value={indexDraft.notes}
                onChange={(event) => setIndexDraft({ ...indexDraft, notes: event.target.value })}
                placeholder="Notes (optionnel)"
                style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db", width: 320 }}
              />
            </div>
          </div>
        </div>
        <div style={{ overflowX: "auto" }}>
          {sortedIndices.length === 0 ? (
            <span style={{ color: "#9ca3af", fontSize: 13 }}>Aucun indice saisi.</span>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                  <th style={thStyle}>Code</th>
                  <th style={thStyle}>Annee</th>
                  <th style={thStyle}>Periode</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Valeur</th>
                  <th style={thStyle}>Source</th>
                  <th style={thStyle}>Verification</th>
                  <th style={thStyle}>Notes</th>
                  <th style={thStyle}>Action</th>
                </tr>
              </thead>
              <tbody>
                {sortedIndices.map((item) => (
                  <tr key={item.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>{item.index_code}</td>
                    <td style={tdStyle}>{item.year}</td>
                    <td style={tdStyle}>{item.quarter === 0 ? "Base / ref" : `T${item.quarter}`}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(item.value, 4)}</td>
                    <td style={tdStyle}>{item.source ?? "-"}</td>
                    <td style={tdStyle}>
                      <span className={item.verification_status === "official_verified" ? "badge-green" : "badge-orange"}>
                        {item.verification_status === "official_verified"
                          ? "Officiel verifie"
                          : item.verification_status === "declared_to_verify"
                            ? "Declare DALKIA - a verifier"
                            : "A verifier"}
                      </span>
                    </td>
                    <td style={tdStyle}>{item.notes ?? "-"}</td>
                    <td style={tdStyle}>
                      <button
                        type="button"
                        className="secondary-button"
                        style={{ fontSize: 12, padding: "3px 8px" }}
                        onClick={() =>
                          setIndexDraft({
                            index_code: item.index_code,
                            year: item.year,
                            quarter: item.quarter,
                            value: String(item.value),
                            source: item.source ?? "Saisie Po2",
                            verification_status: item.verification_status,
                            evidence_id: item.evidence_id,
                            notes: item.notes ?? "",
                          })
                        }
                      >
                        Editer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
      )}

      {section === "references" && (
      <section className="card" style={{ padding: 16, marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", marginBottom: 12 }}>
          <div>
            <h3 style={{ margin: "0 0 4px" }}>References contractuelles de controle</h3>
            <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>
              Montants DPGF, formules, postes inclus et tolerances utilises par les controles de factures.
            </p>
          </div>
          <input
            value={referenceFilter}
            onChange={(event) => setReferenceFilter(event.target.value)}
            placeholder="Filtrer contrat, annee, poste..."
            style={{ padding: "7px 9px", borderRadius: 6, border: "1px solid #d1d5db", minWidth: 260 }}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "minmax(300px, 0.8fr) minmax(620px, 1.6fr)", gap: 16 }}>
          <div>
            <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>{editingReferenceId ? "Modifier une reference" : "Ajouter une reference"}</h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <FinanceInput label="Code contrat" value={referenceDraft.contract_code} onChange={(value) => setReferenceDraft({ ...referenceDraft, contract_code: value })} />
              <FinanceInput label="Annee" value={String(referenceDraft.year)} onChange={(value) => setReferenceDraft({ ...referenceDraft, year: Number(value) || CURRENT_YEAR })} />
              <FinanceInput label="Libelle contrat" value={referenceDraft.contract_label} onChange={(value) => setReferenceDraft({ ...referenceDraft, contract_label: value })} wide />
              <FinanceInput label="Type reference" value={referenceDraft.reference_kind} onChange={(value) => setReferenceDraft({ ...referenceDraft, reference_kind: value })} />
              <FinanceInput label="Marche" value={referenceDraft.market} onChange={(value) => setReferenceDraft({ ...referenceDraft, market: value })} />
              <FinanceInput label="Poste reference" value={referenceDraft.billed_item} onChange={(value) => setReferenceDraft({ ...referenceDraft, billed_item: value })} />
              <FinanceInput label="Montant annuel HT" value={referenceDraft.annual_amount_ht} onChange={(value) => setReferenceDraft({ ...referenceDraft, annual_amount_ht: value })} />
              <FinanceInput label="Montant attendu HT" value={referenceDraft.expected_amount_ht} onChange={(value) => setReferenceDraft({ ...referenceDraft, expected_amount_ht: value })} />
              <FinanceInput label="Nb acomptes" value={referenceDraft.installment_count} onChange={(value) => setReferenceDraft({ ...referenceDraft, installment_count: value })} />
              <FinanceInput label="Mois attendus" value={referenceDraft.expected_period_months} onChange={(value) => setReferenceDraft({ ...referenceDraft, expected_period_months: value })} />
              <FinanceInput label="Tolerance %" value={referenceDraft.tolerance_pct} onChange={(value) => setReferenceDraft({ ...referenceDraft, tolerance_pct: value })} />
              <FinanceInput label="Tolerance EUR" value={referenceDraft.tolerance_eur} onChange={(value) => setReferenceDraft({ ...referenceDraft, tolerance_eur: value })} />
              <FinanceInput label="Postes inclus JSON ou CSV" value={referenceDraft.included_billed_items} onChange={(value) => setReferenceDraft({ ...referenceDraft, included_billed_items: value })} wide />
              <FinanceInput label="Formule" value={referenceDraft.formula} onChange={(value) => setReferenceDraft({ ...referenceDraft, formula: value })} wide />
              <FinanceInput label="Notes" value={referenceDraft.notes} onChange={(value) => setReferenceDraft({ ...referenceDraft, notes: value })} wide />
              <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 12, color: "#6b7280" }}>
                <input
                  type="checkbox"
                  checked={referenceDraft.active}
                  onChange={(event) => setReferenceDraft({ ...referenceDraft, active: event.target.checked })}
                />
                Active
              </label>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button
                type="button"
                className="primary-button"
                disabled={saveContractReferencePending || !referenceDraft.contract_code || !referenceDraft.reference_kind || !referenceDraft.market || !referenceDraft.billed_item}
                onClick={submitReferenceDraft}
              >
                {editingReferenceId ? "Enregistrer" : "Ajouter"}
              </button>
              {editingReferenceId && (
                <button type="button" className="secondary-button" onClick={resetReferenceDraft}>
                  Annuler
                </button>
              )}
            </div>
          </div>

          <div style={{ overflowX: "auto", width: "100%" }}>
            <table style={{ width: "100%", minWidth: 1180, borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                  <th style={thStyle}>Contrat</th>
                  <th style={thStyle}>Controle</th>
                  <th style={thStyle}>Montants</th>
                  <th style={thStyle}>Postes inclus</th>
                  <th style={thStyle}>Tolerance</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleReferences.map((reference) => (
                  <tr key={reference.id} style={{ borderBottom: "1px solid #f3f4f6", opacity: reference.active ? 1 : 0.55 }}>
                    <td style={tdStyle}>
                      <code>{reference.contract_code}</code>
                      <div style={{ color: "#6b7280" }}>{reference.contract_label}</div>
                    </td>
                    <td style={tdStyle}>
                      {reference.reference_kind}
                      <div style={{ color: "#6b7280" }}>{reference.year} / {reference.market} / {reference.billed_item}</div>
                    </td>
                    <td style={tdStyle}>
                      Annuel : {fmtEur(reference.annual_amount_ht)}
                      <div style={{ color: "#6b7280" }}>
                        Attendu : {fmtEur(reference.expected_amount_ht ?? (reference.annual_amount_ht != null && reference.installment_count ? reference.annual_amount_ht / reference.installment_count : null))}
                      </div>
                    </td>
                    <td style={{ ...tdStyle, minWidth: 230 }}>{reference.included_billed_items ?? "-"}</td>
                    <td style={tdStyle}>
                      {reference.tolerance_pct != null ? `${(reference.tolerance_pct * 100).toLocaleString("fr-FR")} %` : "-"}
                      <div style={{ color: "#6b7280" }}>{fmtEur(reference.tolerance_eur)}</div>
                    </td>
                    <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>
                      <button type="button" className="secondary-button" style={{ fontSize: 12, padding: "4px 8px" }} onClick={() => startReferenceEdit(reference)}>
                        Modifier
                      </button>{" "}
                      <button
                        type="button"
                        className="secondary-button"
                        style={{ fontSize: 12, padding: "4px 8px", color: "#b91c1c" }}
                        disabled={deleteContractReferencePending}
                        onClick={() => onDeleteContractReference(reference.id)}
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
                {visibleReferences.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ ...tdStyle, textAlign: "center", color: "#9ca3af" }}>
                      Aucune reference contractuelle.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
      )}

      {section === "sites" && (
      <section style={{ display: "grid", gridTemplateColumns: "1fr", gap: 16, marginBottom: 24 }}>
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

        <div className="card" style={{ padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", marginBottom: 12 }}>
            <div>
              <h3 style={{ margin: "0 0 4px" }}>Sites de codification</h3>
              <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>
                Correspondance entre les codes DALKIA, les sites Ville/CCAS et les axes analytiques finances.
              </p>
            </div>
            <input
              value={siteFilter}
              onChange={(event) => setSiteFilter(event.target.value)}
              placeholder="Filtrer site, code, service..."
              style={{ padding: "7px 9px", borderRadius: 6, border: "1px solid #d1d5db", minWidth: 260 }}
            />
          </div>
          <div style={{ overflowX: "auto", width: "100%" }}>
          {loading ? (
            <p>Chargement...</p>
          ) : (
            <table style={{ width: "100%", minWidth: 1500, borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                  <th style={thStyle}>Code</th>
                  <th style={thStyle}>Site</th>
                  <th style={thStyle}>Famille</th>
                  <th style={thStyle}>Gestionnaire</th>
                  <th style={thStyle}>Service</th>
                  <th style={thStyle}>Libelle service</th>
                  <th style={thStyle}>Fonction</th>
                  <th style={thStyle}>Libelle fonction</th>
                  <th style={thStyle}>Antenne</th>
                  <th style={thStyle}>Operation</th>
                  <th style={thStyle}>Actif</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleSiteMappings.map((mapping) => (
                  <tr key={mapping.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={tdStyle}><code>{mapping.code_site}</code></td>
                    <td style={{ ...tdStyle, minWidth: 240 }}>{mapping.site_name}</td>
                    <td style={tdStyle}>{mapping.family ?? "-"}</td>
                    <td style={tdStyle}>{mapping.manager ?? "-"}</td>
                    <td style={tdStyle}>{mapping.service_code ?? "-"}</td>
                    <td style={{ ...tdStyle, minWidth: 180 }}>{mapping.service_label ?? "-"}</td>
                    <td style={tdStyle}>{mapping.function_code ?? "-"}</td>
                    <td style={{ ...tdStyle, minWidth: 180 }}>{mapping.function_label ?? "-"}</td>
                    <td style={tdStyle}>{mapping.antenna_code ?? "-"}</td>
                    <td style={tdStyle}>{mapping.operation_code ?? "-"}</td>
                    <td style={tdStyle}>{mapping.active ? "Oui" : "Non"}</td>
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
                {visibleSiteMappings.length === 0 && (
                  <tr>
                    <td colSpan={12} style={{ ...tdStyle, textAlign: "center", color: "#9ca3af" }}>
                      Aucun site de codification.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
          </div>
          {siteMappings.length > visibleSiteMappings.length && (
            <p style={{ margin: "8px 0 0", color: "#6b7280", fontSize: 12 }}>
              {visibleSiteMappings.length} site(s) affiche(s) sur {siteMappings.length}. Utilise le filtre pour cibler une ligne.
            </p>
          )}
        </div>
      </section>
      )}

      {section === "rules" && (
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
          <div style={{ overflowX: "auto", width: "100%" }}>
            <table style={{ width: "100%", minWidth: 1180, borderCollapse: "collapse", fontSize: 12 }}>
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
      )}

      {section === "invoices" && (
      <section style={{ display: "grid", gridTemplateColumns: "1fr", gap: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div>
            <h3 style={{ margin: "0 0 4px", fontSize: 16 }}>Suivi du marché — prévu (DPGF) vs reçu</h3>
            <p style={{ margin: 0, color: "#6b7280", fontSize: 13 }}>
              Comparaison par poste P1/P2/P3 (dont P2.4 et P3.4) entre les enveloppes contractuelles du marché et les montants facturés DALKIA reçus.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <label style={{ fontSize: 12, color: "#4b5563" }}>De&nbsp;
              <select value={marketYearFrom} onChange={(e) => setMarketYearFrom(Number(e.target.value))} style={{ padding: "5px 7px", borderRadius: 6, border: "1px solid #d1d5db" }}>
                {MARKET_YEAR_OPTIONS.map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </label>
            <label style={{ fontSize: 12, color: "#4b5563" }}>à&nbsp;
              <select value={marketYearTo} onChange={(e) => setMarketYearTo(Number(e.target.value))} style={{ padding: "5px 7px", borderRadius: 6, border: "1px solid #d1d5db" }}>
                {MARKET_YEAR_OPTIONS.map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </label>
            <button type="button" className="secondary-button" disabled={marketExportPending || !marketTracking?.has_reference} onClick={onExportMarketTracking}>
              {marketExportPending ? "Export..." : "Exporter XLSX"}
            </button>
          </div>
        </div>

        {marketTrackingQ.isLoading && <div className="card" style={{ padding: 18, color: "#6b7280" }}>Chargement du suivi marché…</div>}

        {marketTracking && !marketTracking.has_reference && (
          <div className="card" style={{ padding: 18, color: "#92400e", background: "#fffbeb", border: "1px solid #fde68a" }}>
            Aucune enveloppe contractuelle trouvée pour cette plage. Importez le référentiel DALKIA (DPGF Lot 1 / Lot 2) dans « Imports » pour alimenter le prévu.
          </div>
        )}

        {marketTracking && marketTracking.has_reference && (
          <>
            <MarketTrackingMatrix
              title="Ensemble du marché"
              subtitle={`Prévu P1 : ${marketTracking.p1_source}. P2/P3/P2.4/P3.4 : référentiel DPGF par site agrégé. Reçu : factures DALKIA du périmètre CPE Ville.`}
              years={marketTracking.years}
              postes={marketTracking.postes}
              totalsByYear={marketTracking.totals_by_year}
              grandTotal={marketTracking.grand_total}
              yearFrom={marketYearFrom}
              yearTo={marketYearTo}
              p1Dpgf={marketTracking.p1_dpgf}
              quartersBilled={marketTracking.quarters_billed}
              installmentsPerYear={marketTracking.installments_per_year}
            />
            {marketTracking.dju && marketTracking.dju.has_data && <DjuBand dju={marketTracking.dju} />}
            {marketTracking.by_lot.map((lot) => (
              <MarketTrackingMatrix
                key={lot.lot}
                title={lot.label}
                subtitle={`Contrat ${lot.contract_codes.join(", ")} — prévu DPGF Lot ${lot.lot} vs reçu factures du lot.`}
                years={marketTracking.years}
                postes={lot.postes}
                totalsByYear={lot.totals_by_year}
                grandTotal={lot.grand_total}
                yearFrom={marketYearFrom}
                yearTo={marketYearTo}
                p1Dpgf={lot.p1_dpgf}
                quartersBilled={lot.quarters_billed}
                installmentsPerYear={marketTracking.installments_per_year}
              />
            ))}
            {p3Atterrissage && p3Atterrissage.has_provision && <P3AtterrissageChart data={p3Atterrissage} />}
          </>
        )}
      </section>
      )}

      {section === "p3-devis" && (
      <section style={{ display: "grid", gridTemplateColumns: "1fr", gap: 16 }}>
        <div>
          <h3 style={{ margin: "0 0 4px", fontSize: 16 }}>Factures petits travaux P3 (devis P6)</h3>
          <p style={{ margin: 0, color: "#6b7280", fontSize: 13 }}>
            Devis de petits travaux P3 importés depuis l'espace client DALKIA (périmètre COMMUNE DE SETE). Importez‑les via « Imports » → « Importer devis P3 ».
          </p>
        </div>
        {p3AtterrissageQ.isLoading && <div className="card" style={{ padding: 18, color: "#6b7280" }}>Chargement…</div>}
        {p3Atterrissage && <P3AtterrissageChart data={p3Atterrissage} />}
        <div className="card" style={{ padding: 12, overflowX: "auto" }}>
          <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>Devis du périmètre ({p3Devis.length})</h4>
          {p3Devis.length === 0 ? (
            <p style={{ color: "#6b7280", fontSize: 13, margin: 0 }}>Aucun devis importé. Utilisez « Importer devis P3 » dans la section Imports.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, minWidth: 900 }}>
              <thead>
                <tr style={{ background: "#f9fafb" }}>
                  <th style={{ ...thStyle, textAlign: "left" }}>Date</th>
                  <th style={{ ...thStyle, textAlign: "left" }}>Numéro</th>
                  <th style={{ ...thStyle, textAlign: "left" }}>Site</th>
                  <th style={{ ...thStyle, textAlign: "left" }}>Libellé</th>
                  <th style={{ ...thStyle, textAlign: "left" }}>Domaine</th>
                  <th style={{ ...thStyle, textAlign: "left" }}>État</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Montant HT</th>
                </tr>
              </thead>
              <tbody>
                {p3Devis.map((d) => (
                  <tr key={d.id} style={{ borderTop: "1px solid #f3f4f6" }}>
                    <td style={tdStyle}>{d.devis_date ?? "—"}</td>
                    <td style={tdStyle}>{d.numero}</td>
                    <td style={tdStyle}>{d.site_code ?? "—"}</td>
                    <td style={tdStyle}>{d.libelle ?? "—"}</td>
                    <td style={tdStyle}>{d.domaine ?? "—"}</td>
                    <td style={tdStyle}>{d.etat ?? "—"}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmtEur(d.montant_ht)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
      )}

      {section === "controls" && (
      <section style={{ display: "grid", gridTemplateColumns: "1fr", gap: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div>
            <h4 style={{ margin: "0 0 4px", fontSize: 15 }}>Contrôle global des factures CPE Ville</h4>
            <p style={{ margin: 0, color: "#6b7280", fontSize: 13 }}>
              Recalcule les contrôles contractuels, comptables et documentaires sur toutes les factures des contrats actifs CPE Ville.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" className="primary-button" onClick={onRecalculateAllControls} disabled={controlsPending}>
              {controlsPending ? "Contrôle en cours..." : "Lancer le contrôle global"}
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={onExportGlobalControlReport}
              disabled={controlsPending || exportGlobalControlReportPending}
            >
              {exportGlobalControlReportPending ? "Préparation du rapport..." : "Éditer le rapport"}
            </button>
          </div>
        </div>

        {controlReport ? (
          <>
            <div className="kpi-grid">
              <KpiCard label="Factures analysées" value={String(controlReport.invoice_count)} sub={`${fmtEur(controlReport.total_ht)} HT contrôlés`} color="#1d4ed8" />
              <KpiCard label="Factures conformes" value={String(controlReport.invoices_ok)} sub={`${controlReport.controls_ok} contrôle(s) OK`} color="#16a34a" />
              <KpiCard label="Factures avec écarts" value={String(controlReport.invoices_with_errors)} sub={`${controlReport.controls_error} écart(s) à examiner`} color="#dc2626" />
              <KpiCard label="Factures bloquées" value={String(controlReport.invoices_blocked)} sub={`${controlReport.controls_blocked} donnée(s) manquante(s)`} color="#b45309" />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 420px), 1fr))", gap: 12 }}>
              <div className="card" style={{ padding: 12 }}>
                <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>Qualité du portefeuille contrôlé</h4>
                <div style={{ height: 280 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Tooltip formatter={(value) => `${Number(value).toLocaleString("fr-FR")} facture(s)`} />
                      <Legend />
                      <Pie data={controlStatusChartData} dataKey="value" nameKey="label" outerRadius={90} label>
                        {controlStatusChartData.map((entry) => <Cell key={entry.label} fill={entry.color} />)}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="card" style={{ padding: 12 }}>
                <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>Anomalies par famille de contrôle</h4>
                <div style={{ height: 280 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={controlTypeChartData} layout="vertical" margin={{ left: 28, right: 14 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" allowDecimals={false} />
                      <YAxis type="category" dataKey="type" width={170} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="error" name="Écarts" stackId="issues" fill="#dc2626" />
                      <Bar dataKey="blocked" name="Bloqués" stackId="issues" fill="#f59e0b" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="card" style={{ padding: 12, overflowX: "auto" }}>
              <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>File de traitement priorisée</h4>
              <input
                ref={evidencePdfRef}
                type="file"
                accept=".pdf,application/pdf"
                style={{ display: "none" }}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file && evidenceInvoiceId != null) onUploadEvidencePdf(evidenceInvoiceId, file);
                  event.target.value = "";
                }}
              />
              <table style={{ width: "100%", minWidth: 1700, borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                    <th style={sortableThStyle} onClick={() => toggleQueueSort("invoice_number")}>Facture{queueSortIndicator("invoice_number")}</th>
                    <th style={sortableThStyle} onClick={() => toggleQueueSort("contract")}>Contrat{queueSortIndicator("contract")}</th>
                    <th style={sortableThStyle} onClick={() => toggleQueueSort("invoice_type")}>Type{queueSortIndicator("invoice_type")}</th>
                    <th style={sortableThStyle} onClick={() => toggleQueueSort("recipient_ref")}>Destinataire{queueSortIndicator("recipient_ref")}</th>
                    <th style={sortableThStyle} onClick={() => toggleQueueSort("market")}>Marché{queueSortIndicator("market")}</th>
                    <th style={sortableThStyle} onClick={() => toggleQueueSort("billed_items")}>Postes factures{queueSortIndicator("billed_items")}</th>
                    <th style={{ ...sortableThStyle, textAlign: "right" }} onClick={() => toggleQueueSort("total_ht")}>HT{queueSortIndicator("total_ht")}</th>
                    <th style={{ ...sortableThStyle, textAlign: "right" }} onClick={() => toggleQueueSort("ok")}>OK{queueSortIndicator("ok")}</th>
                    <th style={{ ...sortableThStyle, textAlign: "right" }} onClick={() => toggleQueueSort("error")}>Écarts{queueSortIndicator("error")}</th>
                    <th style={{ ...sortableThStyle, textAlign: "right" }} onClick={() => toggleQueueSort("blocked")}>Bloqués{queueSortIndicator("blocked")}</th>
                    <th style={sortableThStyle} onClick={() => toggleQueueSort("families")}>Familles à traiter{queueSortIndicator("families")}</th>
                    <th style={sortableThStyle} onClick={() => toggleQueueSort("due_date")}>Échéance{queueSortIndicator("due_date")}</th>
                    <th style={sortableThStyle} onClick={() => toggleQueueSort("invoice_status")}>Décision{queueSortIndicator("invoice_status")}</th>
                    <th style={thStyle}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedQueueInvoices.map((invoice) => {
                    const fullInvoice = invoiceById.get(invoice.invoice_id);
                    return (
                    <tr key={invoice.invoice_id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                      <td style={tdStyle}>{invoice.invoice_number}</td>
                      <td style={tdStyle}>{invoice.contract_label ?? invoice.contract_code ?? "-"}</td>
                      <td style={tdStyle}>{invoice.invoice_type ?? "-"}</td>
                      <td style={tdStyle}>{invoice.recipient_ref ?? "-"}</td>
                      <td style={tdStyle}>{invoice.market ?? "-"}</td>
                      <td style={tdStyle}>{invoice.billed_items ?? "-"}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>{fmtEur(invoice.total_ht)}</td>
                      <td style={{ ...tdStyle, textAlign: "right", color: "#166534" }}>{invoice.ok}</td>
                      <td style={{ ...tdStyle, textAlign: "right", color: "#b91c1c", fontWeight: invoice.error ? 700 : 400 }}>{invoice.error}</td>
                      <td style={{ ...tdStyle, textAlign: "right", color: "#b45309", fontWeight: invoice.blocked ? 700 : 400 }}>{invoice.blocked}</td>
                      <td style={tdStyle}>{invoice.control_types.map((type) => CONTROL_TYPE_LABELS[type] ?? type).join(", ") || "Aucune anomalie"}</td>
                      <td style={tdStyle}>
                        <div>{fmtDate(invoice.due_date)}</div>
                        <span className={`badge ${deadlineClass(invoice.deadline_status)}`}>{deadlineLabel(invoice.deadline_status)}</span>
                      </td>
                      <td style={tdStyle}>
                        {fullInvoice && (
                          <select
                            value={fullInvoice.status}
                            disabled={invoiceActionPending}
                            onChange={(event) => onInvoiceStatus(fullInvoice.id, event.target.value)}
                            style={{ padding: "4px 6px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 12 }}
                          >
                            <option value="a_controler">A controler</option>
                            <option value="valide">Valide</option>
                            <option value="refuse">Refuse</option>
                            <option value="conteste">Conteste</option>
                          </select>
                        )}
                      </td>
                      <td style={tdStyle}>
                        {fullInvoice && (
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", minWidth: 220 }}>
                            <button type="button" className="secondary-button" style={{ fontSize: 12, padding: "4px 8px" }} disabled={invoiceActionPending} onClick={() => onExportLiaison(fullInvoice)}>
                              Exporter XLSX finance
                            </button>
                            <button
                              type="button"
                              className="secondary-button"
                              style={{ fontSize: 12, padding: "4px 8px" }}
                              disabled={invoiceActionPending}
                              onClick={() => {
                                setEvidenceInvoiceId(fullInvoice.id);
                                evidencePdfRef.current?.click();
                              }}
                            >
                              {fullInvoice.evidence_id ? "Remplacer PDF" : "Importer PDF"}
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  )})}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="card" style={{ padding: 18, color: "#6b7280", fontSize: 13 }}>
            Aucun rapport consolidé disponible. Lance le contrôle global pour créer l’état de référence du portefeuille CPE Ville.
          </div>
        )}
      </section>
      )}
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
      <td style={{ ...tdStyle, textAlign: "right" }}>
        {fmt(item.nb_exercice)}
        {item.nb_source === "dalkia" ? (
          <span
            title="NB issu de la cible DALKIA importée pour cette année (révisée après travaux APE)"
            style={{ marginLeft: 4, fontSize: 9, fontWeight: 700, color: "#16a34a", cursor: "help" }}
          >
            DLK
          </span>
        ) : (
          <span
            title="Valeur de secours du site (aucune cible DALKIA pour cette année). Vérifier l'alignement du code site entre cpe_sites et l'import DALKIA."
            style={{ marginLeft: 4, fontSize: 9, fontWeight: 700, color: "#f97316", cursor: "help" }}
          >
            SITE
          </span>
        )}
      </td>
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

const sortableThStyle: React.CSSProperties = {
  padding: "10px 12px",
  textAlign: "left",
  fontSize: 12,
  fontWeight: 600,
  color: "#6b7280",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  cursor: "pointer",
  userSelect: "none",
  whiteSpace: "nowrap",
};

const tableSortButtonStyle: React.CSSProperties = {
  appearance: "none",
  border: 0,
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
  font: "inherit",
  letterSpacing: "inherit",
  padding: 0,
  textTransform: "inherit",
};

const tdStyle: React.CSSProperties = {
  padding: "10px 12px",
  verticalAlign: "middle",
};
