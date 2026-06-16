import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  analyzeEnergyInvoiceImport,
  deleteEnergyInvoiceImport,
  deleteAllEnergyInvoiceImports,
  fetchEnergyInvoiceBatch,
  fetchEnergyInvoiceBatches,
  fetchEnergyInvoiceImports,
  fetchEnergyInvoiceMonthlyConsumption,
  fetchTurpeVersions,
  uploadEnergyInvoiceBatch,
  uploadEngieXlsxExport,
  uploadEdfCsvExport,
} from "../lib/api";
import type { EnergyInvoiceImport, EnergyInvoiceMonthlyConsumptionPoint } from "../lib/api";
import { InvoiceSupplierReport } from "../components/InvoiceSupplierReport";
import EnergieAccountingMatrix from "../components/EnergieAccountingMatrix";
import { InvoicePeriodTimeline } from "../components/InvoicePeriodTimeline";
import type { TimelineGroup, TimelineItem } from "../components/InvoicePeriodTimeline";
import {
  INVOICE_ISSUE_FAMILY_ORDER,
  INVOICE_ISSUE_FAMILY_LABEL,
  INVOICE_KNOWN_ISSUE_CODES,
  invoiceIssueFamily,
} from "../lib/invoiceIssues";
import type { InvoiceControlIssue, InvoiceIssueFamily } from "../lib/invoiceIssues";
import { useAuth } from "../providers/AuthProvider";

const IMPORT_STATUS_LABEL: Record<string, string> = {
  imported: "Importee",
  duplicate: "Doublon",
  error: "Erreur",
};

const ANALYSIS_STATUS_LABEL: Record<string, string> = {
  pending: "Analyse a venir",
  parsed: "Lue",
  partial: "Partielle",
  failed: "Echec",
};

const CONTROL_STATUS_LABEL: Record<string, string> = {
  valid: "Valide",
  review: "A controler",
  invalid: "Invalide",
  not_checked: "Non controlee",
};

const DECISION_STATUS_LABEL: Record<string, string> = {
  to_review: "A verifier",
  approved: "Validee",
  rejected: "Refusee",
  dispute_sent: "Contestation envoyee",
};

const BATCH_ITEM_STATUS_LABEL: Record<string, string> = {
  imported: "Importee",
  duplicate: "Doublon",
  ignored: "Ignore",
  error: "Erreur",
};

const CONTROL_FILTER_OPTIONS = [
  { value: "valid", label: "Valides" },
  { value: "review", label: "A controler" },
  { value: "invalid", label: "Invalides" },
  { value: "not_checked", label: "Non controlees" },
];

const DECISION_FILTER_OPTIONS = [
  { value: "to_review", label: "A verifier" },
  { value: "approved", label: "Validees" },
  { value: "rejected", label: "Refusees" },
  { value: "dispute_sent", label: "Contestation envoyee" },
];

const MONTH_LABELS_SHORT = ["Jan", "Fev", "Mar", "Avr", "Mai", "Juin", "Juil", "Aout", "Sep", "Oct", "Nov", "Dec"];

type MultiFilterOption<T extends string> = {
  value: T;
  label: string;
  title?: string;
};

function formatDate(value: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function formatShortDate(value: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(new Date(value));
}

function formatCurrency(value: number | null) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value);
}

function formatKwh(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-";
  return `${Math.round(value).toLocaleString("fr-FR")} kWh`;
}

export type SupplierKey = "ENGIE" | "EDF" | "TOTALENERGIES";

// Reflet du registre back (services/supplier_registry.py) : qui facture quoi.
// Le distributeur (ENEDIS / GRDF) est une reference de controle, pas un payeur.
const SUPPLIER_CATALOG: {
  key: SupplierKey;
  label: string;
  energyLabel: string;
  distributor: string;
  scope: string;
  supported: boolean;
}[] = [
  { key: "ENGIE", label: "ENGIE", energyLabel: "Electricite", distributor: "ENEDIS", scope: "Batiments ville", supported: true },
  { key: "EDF", label: "EDF", energyLabel: "Electricite", distributor: "ENEDIS", scope: "Eclairage public", supported: true },
  { key: "TOTALENERGIES", label: "TotalEnergies", energyLabel: "Gaz", distributor: "GRDF", scope: "Gaz batiments", supported: false },
];

function supplierKeyOf(invoiceImport: EnergyInvoiceImport): SupplierKey | null {
  const value = (invoiceImport.supplier_guess ?? "").toUpperCase();
  if (value.includes("ENGIE")) return "ENGIE";
  if (value.includes("EDF") || value.includes("ELECTRICITE DE FRANCE")) return "EDF";
  if (value.includes("TOTAL")) return "TOTALENERGIES";
  return null;
}

function formatCount(value: number | null | undefined, unit: string) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-";
  return `${Math.round(value).toLocaleString("fr-FR")} ${unit}`;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

function statusBadge(invoiceImport: EnergyInvoiceImport) {
  const statusClass =
    invoiceImport.status === "error"
      ? "badge-red"
      : invoiceImport.analysis_status === "failed"
        ? "badge-red"
        : invoiceImport.analysis_status === "pending"
          ? "badge-blue"
          : "badge-green";
  return (
    <span className={`badge ${statusClass}`}>
      {ANALYSIS_STATUS_LABEL[invoiceImport.analysis_status] ?? invoiceImport.analysis_status}
    </span>
  );
}

function controlBadge(invoiceImport: EnergyInvoiceImport) {
  const statusClass =
    invoiceImport.control_status === "invalid"
      ? "badge-red"
      : invoiceImport.control_status === "review"
        ? "badge-orange"
        : invoiceImport.control_status === "valid"
          ? "badge-green"
          : "badge-gray";

  return (
    <span className={`badge ${statusClass}`}>
      {CONTROL_STATUS_LABEL[invoiceImport.control_status] ?? invoiceImport.control_status}
    </span>
  );
}

function decisionBadge(invoiceImport: EnergyInvoiceImport) {
  const statusClass =
    invoiceImport.decision_status === "approved"
      ? "badge-green"
      : invoiceImport.decision_status === "rejected"
        ? "badge-red"
        : invoiceImport.decision_status === "dispute_sent"
          ? "badge-blue"
          : "badge-gray";

  return (
    <span className={`badge ${statusClass}`}>
      {DECISION_STATUS_LABEL[invoiceImport.decision_status] ?? invoiceImport.decision_status}
    </span>
  );
}

function batchItemBadge(status: string) {
  const statusClass =
    status === "error" ? "badge-red" : status === "duplicate" ? "badge-orange" : status === "imported" ? "badge-green" : "badge-gray";
  return <span className={`badge ${statusClass}`}>{BATCH_ITEM_STATUS_LABEL[status] ?? status}</span>;
}

function invoiceIssueFamilies(issues: InvoiceControlIssue[]) {
  return Array.from(new Set(issues.map(invoiceIssueFamily)));
}

// Comparateur de tri colonne par colonne. Retourne -1/0/+1 (ordre ascendant).
function compareInvoiceColumn(
  a: EnergyInvoiceImport,
  b: EnergyInvoiceImport,
  column: "fichier" | "facture" | "regroupement" | "titulaire" | "montant" | "controle" | "decision" | "import",
): number {
  function cmpStr(x: string | null | undefined, y: string | null | undefined): number {
    const xs = (x ?? "").toLowerCase();
    const ys = (y ?? "").toLowerCase();
    if (xs === ys) return 0;
    // Les valeurs vides en fin
    if (!xs) return 1;
    if (!ys) return -1;
    return xs.localeCompare(ys, "fr");
  }
  function cmpNum(x: number | null | undefined, y: number | null | undefined): number {
    const xv = x ?? Number.NEGATIVE_INFINITY;
    const yv = y ?? Number.NEGATIVE_INFINITY;
    return xv - yv;
  }
  function cmpDate(x: string | null | undefined, y: string | null | undefined): number {
    // ISO strings se comparent bien lexicographiquement
    return cmpStr(x, y);
  }
  switch (column) {
    case "fichier":
      return cmpStr(a.original_filename, b.original_filename);
    case "facture":
      // Tri principal sur invoice_number, fallback date facture
      return cmpStr(a.invoice_number, b.invoice_number) || cmpDate(a.invoice_date, b.invoice_date);
    case "regroupement":
      return cmpStr(a.regroupement, b.regroupement);
    case "titulaire":
      return cmpStr(a.contract_holder, b.contract_holder);
    case "montant":
      return cmpNum(a.total_ttc, b.total_ttc);
    case "controle":
      // Tri par statut puis par nb erreurs décroissant
      return cmpStr(a.control_status, b.control_status) || cmpNum(b.control_errors_count, a.control_errors_count);
    case "decision":
      return cmpStr(a.decision_status, b.decision_status);
    case "import":
      return cmpDate(a.created_at, b.created_at);
    default:
      return 0;
  }
}

function invoiceIssueCodes(issues: InvoiceControlIssue[]) {
  return Array.from(new Set(issues.map((issue) => issue.code))).filter(Boolean);
}

function filterFacetValues(invoiceImport: EnergyInvoiceImport, key: keyof EnergyInvoiceImport["filter_facets"]) {
  return invoiceImport.filter_facets?.[key] ?? [];
}

function hasAnyFacetValue(invoiceImport: EnergyInvoiceImport, key: keyof EnergyInvoiceImport["filter_facets"], selected: string[]) {
  if (selected.length === 0) return true;
  const values = filterFacetValues(invoiceImport, key);
  return values.some((value) => selected.includes(value));
}

function collectFacetOptions(imports: EnergyInvoiceImport[], key: keyof EnergyInvoiceImport["filter_facets"]) {
  return Array.from(new Set(imports.flatMap((invoiceImport) => filterFacetValues(invoiceImport, key)))).sort((a, b) =>
    a.localeCompare(b, "fr"),
  );
}

function controlIssueTags(invoiceImport: EnergyInvoiceImport) {
  const families = invoiceIssueFamilies(invoiceImport.control_issues);
  const codes = invoiceIssueCodes(invoiceImport.control_issues);

  if (families.length === 0) return null;

  return (
    <div className="invoice-issue-tags">
      {families.map((family) => (
        <span key={family} className="invoice-issue-family-tag">
          {INVOICE_ISSUE_FAMILY_LABEL[family]}
        </span>
      ))}
      {codes.slice(0, 3).map((code) => {
        const sample = invoiceImport.control_issues.find((issue) => issue.code === code);
        return (
          <span key={code} className="invoice-issue-code-tag" title={sample?.message ?? code}>
            {code}
          </span>
        );
      })}
      {codes.length > 3 && <span className="invoice-issue-code-tag">+{codes.length - 3}</span>}
    </div>
  );
}

function toggleSelection<T extends string>(values: T[], value: T) {
  return values.includes(value) ? values.filter((current) => current !== value) : [...values, value];
}

function InvoiceMultiFilter<T extends string>({
  label,
  allLabel,
  options,
  values,
  onChange,
}: {
  label: string;
  allLabel: string;
  options: MultiFilterOption<T>[];
  values: T[];
  onChange: (values: T[]) => void;
}) {
  const selectedLabels = options.filter((option) => values.includes(option.value)).map((option) => option.label);
  const summary =
    values.length === 0
      ? allLabel
      : selectedLabels.length === 1
        ? selectedLabels[0]
        : `${selectedLabels.length} selections`;

  return (
    <div className="invoice-multi-filter">
      <span className="field-label">{label}</span>
      <details>
        <summary className="form-input">
          <span>{summary}</span>
        </summary>
        <div className="invoice-multi-filter-menu">
          <button type="button" className="btn-secondary btn-compact" onClick={() => onChange([])}>
            {allLabel}
          </button>
          {options.length === 0 && <span className="cell-empty">Aucune option</span>}
          {options.map((option) => (
            <label key={option.value} title={option.title}>
              <input
                type="checkbox"
                checked={values.includes(option.value)}
                onChange={() => onChange(toggleSelection(values, option.value))}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      </details>
    </div>
  );
}

type FluidKey = "elec" | "gaz" | "eau";
type ControlStep = "data" | "control" | "report" | "liaison";

// Onglet de selection du fluide (Electricite / Gaz / Eau). Gaz et Eau sont
// presents mais "a integrer" tant que les parsers ne sont pas developpes.
function FluidTab({
  active,
  soon,
  onClick,
  children,
}: {
  active: boolean;
  soon?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      className={`fluid-tab${active ? " fluid-tab--active" : ""}`}
      onClick={onClick}
    >
      {children}
      {soon && <span className="badge badge-gray">A integrer</span>}
    </button>
  );
}

// Onglet d'etape du parcours : Donnees & import -> Controle -> Rapport -> Liaison finance.
function StepTab({
  active,
  index,
  onClick,
  children,
}: {
  active: boolean;
  index: number;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      className={`step-tab${active ? " step-tab--active" : ""}`}
      onClick={onClick}
    >
      <span className="step-tab-index">{index}</span>
      <span>{children}</span>
    </button>
  );
}

export function EnergieInvoicesPage({ supplierFilter }: { supplierFilter?: SupplierKey } = {}) {
  const { token } = useAuth();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const xlsxInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadSummary, setUploadSummary] = useState<string | null>(null);
  const [xlsxFile, setXlsxFile] = useState<File | null>(null);
  const [xlsxSummary, setXlsxSummary] = useState<string | null>(null);
  const [xlsxForceUpdate, setXlsxForceUpdate] = useState(false);
  const edfInputRef = useRef<HTMLInputElement | null>(null);
  const [edfFile, setEdfFile] = useState<File | null>(null);
  const [edfSummary, setEdfSummary] = useState<string | null>(null);
  const [edfForceUpdate, setEdfForceUpdate] = useState(false);
  const [deleteAllSummary, setDeleteAllSummary] = useState<string | null>(null);

  // Tri du tableau factures : { column, direction }. Cycle clic : asc → desc → none.
  type SortColumn = "fichier" | "facture" | "regroupement" | "titulaire" | "montant" | "controle" | "decision" | "import";
  type SortDir = "asc" | "desc";
  const [sortColumn, setSortColumn] = useState<SortColumn | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  function toggleSort(column: SortColumn) {
    if (sortColumn !== column) {
      setSortColumn(column);
      setSortDir("asc");
    } else if (sortDir === "asc") {
      setSortDir("desc");
    } else {
      setSortColumn(null);
      setSortDir("asc");
    }
  }

  function sortIndicator(column: SortColumn): string {
    if (sortColumn !== column) return " ⇅";
    return sortDir === "asc" ? " ↑" : " ↓";
  }
  const [selectedBatchId, setSelectedBatchId] = useState<number | null>(null);
  const [invoiceSearch, setInvoiceSearch] = useState("");
  const [controlFilters, setControlFilters] = useState<string[]>([]);
  const [decisionFilters, setDecisionFilters] = useState<string[]>([]);
  const [regroupementFilters, setRegroupementFilters] = useState<string[]>([]);
  const [contractHolderFilters, setContractHolderFilters] = useState<string[]>([]);
  const [invoiceMonthFilters, setInvoiceMonthFilters] = useState<string[]>([]);
  const [prmFilters, setPrmFilters] = useState<string[]>([]);
  const [ficFilters, setFicFilters] = useState<string[]>([]);
  const [siteFilters, setSiteFilters] = useState<string[]>([]);
  const [siteCityFilters, setSiteCityFilters] = useState<string[]>([]);
  const [segmentFilters, setSegmentFilters] = useState<string[]>([]);
  const [tariffCodeFilters, setTariffCodeFilters] = useState<string[]>([]);
  const [tariffOptionLabelFilters, setTariffOptionLabelFilters] = useState<string[]>([]);
  const [documentTypeFilters, setDocumentTypeFilters] = useState<string[]>([]);
  const [issueFamilyFilters, setIssueFamilyFilters] = useState<InvoiceIssueFamily[]>([]);
  const [issueCodeFilters, setIssueCodeFilters] = useState<string[]>([]);
  const [isSupplierReportOpen, setIsSupplierReportOpen] = useState(false);
  const [isTimelineOpen, setIsTimelineOpen] = useState(false);
  const [isAccountingOpen, setIsAccountingOpen] = useState(false);

  // Fluide affiche (multi-fluides ready) et etape du parcours de controle.
  const [fluid, setFluid] = useState<FluidKey>("elec");
  const [step, setStep] = useState<ControlStep>("data");

  function resetInvoiceFilters() {
    setControlFilters([]);
    setDecisionFilters([]);
    setRegroupementFilters([]);
    setContractHolderFilters([]);
    setInvoiceMonthFilters([]);
    setPrmFilters([]);
    setFicFilters([]);
    setSiteFilters([]);
    setSiteCityFilters([]);
    setSegmentFilters([]);
    setTariffCodeFilters([]);
    setTariffOptionLabelFilters([]);
    setDocumentTypeFilters([]);
    setIssueFamilyFilters([]);
    setIssueCodeFilters([]);
    setInvoiceSearch("");
  }

  const importsQuery = useQuery({
    queryKey: ["energy-invoice-imports"],
    queryFn: () => fetchEnergyInvoiceImports(token!),
    enabled: !!token,
    refetchInterval: 10000,
  });

  const turpeVersionsQuery = useQuery({
    queryKey: ["turpe-versions"],
    queryFn: () => fetchTurpeVersions(token!),
    enabled: !!token,
  });

  const batchesQuery = useQuery({
    queryKey: ["energy-invoice-batches"],
    queryFn: () => fetchEnergyInvoiceBatches(token!),
    enabled: !!token,
    refetchInterval: 5000,
  });

  const batchDetailQuery = useQuery({
    queryKey: ["energy-invoice-batch", selectedBatchId],
    queryFn: () => fetchEnergyInvoiceBatch(token!, selectedBatchId as number),
    enabled: !!token && selectedBatchId !== null,
  });

  const currentYear = new Date().getFullYear();
  const monthlyConsumptionQuery = useQuery({
    queryKey: [
      "energy-invoice-monthly-consumption",
      currentYear,
      invoiceSearch,
      controlFilters,
      decisionFilters,
      regroupementFilters,
      contractHolderFilters,
      invoiceMonthFilters,
      prmFilters,
      ficFilters,
      siteFilters,
      siteCityFilters,
      segmentFilters,
      tariffCodeFilters,
      tariffOptionLabelFilters,
      documentTypeFilters,
      issueFamilyFilters,
      issueCodeFilters,
    ],
    queryFn: () =>
      fetchEnergyInvoiceMonthlyConsumption(token!, currentYear, {
        search: invoiceSearch,
        controlStatuses: controlFilters,
        decisionStatuses: decisionFilters,
        regroupements: regroupementFilters,
        contractHolders: contractHolderFilters,
        invoiceMonths: invoiceMonthFilters,
        prmIds: prmFilters,
        ficNumbers: ficFilters,
        siteNames: siteFilters,
        siteCities: siteCityFilters,
        segments: segmentFilters,
        tariffCodes: tariffCodeFilters,
        tariffOptionLabels: tariffOptionLabelFilters,
        documentTypes: documentTypeFilters,
        issueFamilies: issueFamilyFilters,
        issueCodes: issueCodeFilters,
      }),
    enabled: !!token,
  });

  const allImports = importsQuery.data ?? [];
  const imports = supplierFilter
    ? allImports.filter((invoiceImport) => supplierKeyOf(invoiceImport) === supplierFilter)
    : allImports;
  // Mode "dédié" : embarqué sous l'onglet d'un fournisseur (ex. ENGIE) dans /factures.
  // On masque le décor multi-fournisseurs (bandeau marché, onglets fluide, cartes
  // fournisseurs) pour ne garder que le parcours de contrôle du fournisseur ciblé.
  const focused = Boolean(supplierFilter);
  const supplierSummary = useMemo(() => {
    const acc: Record<string, { count: number; total: number }> = {};
    for (const invoiceImport of imports) {
      const key = supplierKeyOf(invoiceImport);
      if (!key) continue;
      const entry = acc[key] ?? { count: 0, total: 0 };
      entry.count += 1;
      entry.total += invoiceImport.total_ttc ?? 0;
      acc[key] = entry;
    }
    return acc;
  }, [imports]);
  const batches = batchesQuery.data ?? [];
  const xlsxBatches = batches.filter((batch) => batch.source === "engie_xlsx_export");
  const activeTurpeVersion = turpeVersionsQuery.data?.[0];
  const regroupements = useMemo(
    () =>
      Array.from(
        new Set(
          imports
            .map((invoiceImport) => invoiceImport.regroupement)
            .filter((regroupement): regroupement is string => Boolean(regroupement)),
        ),
      ).sort(),
    [imports],
  );
  const contractHolders = useMemo(
    () =>
      Array.from(
        new Set(
          imports
            .map((invoiceImport) => invoiceImport.contract_holder)
            .filter((contractHolder): contractHolder is string => Boolean(contractHolder)),
        ),
      ).sort((a, b) => a.localeCompare(b, "fr")),
    [imports],
  );
  const invoiceMonths = useMemo(() => collectFacetOptions(imports, "invoice_months"), [imports]);
  const prmIds = useMemo(() => collectFacetOptions(imports, "prm_ids"), [imports]);
  const ficNumbers = useMemo(() => collectFacetOptions(imports, "fic_numbers"), [imports]);
  const siteNames = useMemo(() => collectFacetOptions(imports, "site_names"), [imports]);
  const siteCities = useMemo(() => collectFacetOptions(imports, "site_cities"), [imports]);
  const segments = useMemo(() => collectFacetOptions(imports, "segments"), [imports]);
  const tariffCodes = useMemo(() => collectFacetOptions(imports, "tariff_codes"), [imports]);
  const tariffOptionLabels = useMemo(() => collectFacetOptions(imports, "tariff_option_labels"), [imports]);
  const documentTypes = useMemo(() => collectFacetOptions(imports, "document_types"), [imports]);
  const issueFamilies = INVOICE_ISSUE_FAMILY_ORDER;
  const issueCodes = useMemo(() => {
    const options = new Map<string, { code: string; family: InvoiceIssueFamily; message: string; label?: string }>();
    for (const knownIssue of INVOICE_KNOWN_ISSUE_CODES) {
      if (issueFamilyFilters.length > 0 && !issueFamilyFilters.includes(knownIssue.family)) continue;
      options.set(knownIssue.code, knownIssue);
    }
    for (const invoiceImport of imports) {
      for (const issue of invoiceImport.control_issues) {
        const family = invoiceIssueFamily(issue);
        if (issueFamilyFilters.length > 0 && !issueFamilyFilters.includes(family)) continue;
        if (!options.has(issue.code)) {
          options.set(issue.code, { code: issue.code, family, message: issue.message });
        }
      }
    }
    return Array.from(options.values()).sort(
      (a, b) =>
        INVOICE_ISSUE_FAMILY_LABEL[a.family].localeCompare(INVOICE_ISSUE_FAMILY_LABEL[b.family], "fr") ||
        a.code.localeCompare(b.code, "fr"),
    );
  }, [imports, issueFamilyFilters]);
  const filteredImports = useMemo(() => {
    const search = invoiceSearch.trim().toLowerCase();
    return imports.filter((invoiceImport) => {
      if (controlFilters.length > 0 && !controlFilters.includes(invoiceImport.control_status)) return false;
      if (decisionFilters.length > 0 && !decisionFilters.includes(invoiceImport.decision_status)) return false;
      if (regroupementFilters.length > 0 && (!invoiceImport.regroupement || !regroupementFilters.includes(invoiceImport.regroupement))) return false;
      if (
        contractHolderFilters.length > 0 &&
        (!invoiceImport.contract_holder || !contractHolderFilters.includes(invoiceImport.contract_holder))
      ) {
        return false;
      }
      if (!hasAnyFacetValue(invoiceImport, "invoice_months", invoiceMonthFilters)) return false;
      if (!hasAnyFacetValue(invoiceImport, "prm_ids", prmFilters)) return false;
      if (!hasAnyFacetValue(invoiceImport, "fic_numbers", ficFilters)) return false;
      if (!hasAnyFacetValue(invoiceImport, "site_names", siteFilters)) return false;
      if (!hasAnyFacetValue(invoiceImport, "site_cities", siteCityFilters)) return false;
      if (!hasAnyFacetValue(invoiceImport, "segments", segmentFilters)) return false;
      if (!hasAnyFacetValue(invoiceImport, "tariff_codes", tariffCodeFilters)) return false;
      if (!hasAnyFacetValue(invoiceImport, "tariff_option_labels", tariffOptionLabelFilters)) return false;
      if (!hasAnyFacetValue(invoiceImport, "document_types", documentTypeFilters)) return false;
      if (
        issueFamilyFilters.length > 0 &&
        !invoiceImport.control_issues.some((issue) => issueFamilyFilters.includes(invoiceIssueFamily(issue)))
      ) {
        return false;
      }
      if (issueCodeFilters.length > 0 && !invoiceImport.control_issues.some((issue) => issueCodeFilters.includes(issue.code))) return false;
      if (!search) return true;
      return [
        invoiceImport.original_filename,
        invoiceImport.invoice_number,
        invoiceImport.regroupement,
        invoiceImport.contract_holder,
        invoiceImport.supplier_guess,
        ...filterFacetValues(invoiceImport, "prm_ids"),
        ...filterFacetValues(invoiceImport, "fic_numbers"),
        ...filterFacetValues(invoiceImport, "site_names"),
        ...filterFacetValues(invoiceImport, "site_cities"),
        ...filterFacetValues(invoiceImport, "segments"),
        ...filterFacetValues(invoiceImport, "tariff_codes"),
        ...filterFacetValues(invoiceImport, "tariff_option_labels"),
      ]
        .filter(Boolean)
        .some((value) => value?.toLowerCase().includes(search));
    });
  }, [
    contractHolderFilters,
    controlFilters,
    decisionFilters,
    documentTypeFilters,
    ficFilters,
    imports,
    invoiceMonthFilters,
    invoiceSearch,
    issueCodeFilters,
    issueFamilyFilters,
    prmFilters,
    regroupementFilters,
    segmentFilters,
    siteCityFilters,
    siteFilters,
    tariffCodeFilters,
    tariffOptionLabelFilters,
  ]);
  // Tri appliqué après filtrage. Si aucune colonne sélectionnée, on garde l'ordre naturel (created_at desc).
  const sortedImports = useMemo(() => {
    if (sortColumn === null) return filteredImports;
    const direction = sortDir === "asc" ? 1 : -1;
    const list = [...filteredImports];
    list.sort((a, b) => {
      const cmp = compareInvoiceColumn(a, b, sortColumn);
      return cmp * direction;
    });
    return list;
  }, [filteredImports, sortColumn, sortDir]);

  const monthlyConsumptionChartData = useMemo(() => {
    const points = monthlyConsumptionQuery.data?.months ?? [];
    return points.map((point: EnergyInvoiceMonthlyConsumptionPoint) => {
      const monthIndex = Number(point.month.slice(5, 7)) - 1;
      const hasPotentialGap = point.invoice_count === 0 && (point.enedis_kwh ?? 0) > 0;
      return {
        ...point,
        label: MONTH_LABELS_SHORT[monthIndex] ?? point.month,
        enedis_kwh: point.enedis_kwh ?? undefined,
        hasPotentialGap,
      };
    });
  }, [monthlyConsumptionQuery.data]);
  const potentialGapMonths = useMemo(
    () => monthlyConsumptionChartData.filter((point) => point.hasPotentialGap),
    [monthlyConsumptionChartData],
  );

  // Construction des groupes timeline depuis les factures filtrées : 1 barre par facture,
  // groupée par regroupement (fallback titulaire/"Non regroupe"). Les factures avec
  // anomalies Periode sont marquées isIssue=true pour mise en évidence visuelle.
  const periodTimelineGroups = useMemo<TimelineGroup[]>(() => {
    const groupsMap = new Map<string, { subLabel: string | null; items: TimelineItem[] }>();
    for (const invoiceImport of filteredImports) {
      if (!invoiceImport.period_start || !invoiceImport.period_end) continue;
      const groupName =
        invoiceImport.regroupement?.trim() ||
        invoiceImport.contract_holder?.trim() ||
        "Non regroupe";
      const subLabel = invoiceImport.contract_holder?.trim() ?? null;
      const entry = groupsMap.get(groupName) ?? { subLabel, items: [] };
      const hasPeriodIssue = invoiceImport.control_issues.some(
        (issue) => invoiceIssueFamily(issue) === "periods",
      );
      const ref = invoiceImport.invoice_number ?? invoiceImport.original_filename;
      entry.items.push({
        rowKey: ref,
        rowLabel: ref,
        rowSubLabel: invoiceImport.regroupement?.trim() ?? null,
        startISO: invoiceImport.period_start,
        endISO: invoiceImport.period_end,
        isIssue: hasPeriodIssue,
        tooltip: `${ref} - ${invoiceImport.period_start} → ${invoiceImport.period_end}${hasPeriodIssue ? " (anomalie periode)" : ""}`,
      });
      groupsMap.set(groupName, entry);
    }
    return Array.from(groupsMap.entries())
      .map(([name, { subLabel, items }]) => ({ name, subLabel, items }))
      .sort((a, b) => a.name.localeCompare(b.name, "fr"));
  }, [filteredImports]);

  const supplierReportImports = useMemo(
    () =>
      filteredImports.filter((invoiceImport) =>
        invoiceImport.control_issues.some((issue) => {
          const family = invoiceIssueFamily(issue);
          if (issueFamilyFilters.length > 0 && !issueFamilyFilters.includes(family)) return false;
          if (issueCodeFilters.length > 0 && !issueCodeFilters.includes(issue.code)) return false;
          return true;
        }),
      ),
    [filteredImports, issueCodeFilters, issueFamilyFilters],
  );
  const stats = useMemo(() => {
    const invalid = imports.filter((i) => i.control_status === "invalid").length;
    const review = imports.filter((i) => i.control_status === "review" || i.analysis_status === "pending").length;
    const valid = imports.filter((i) => i.control_status === "valid").length;
    const decisionsToReview = imports.filter((i) => i.decision_status === "to_review").length;
    return { total: imports.length, invalid, review, valid, decisionsToReview };
  }, [imports]);
  const filteredStats = useMemo(() => {
    const totalTtc = filteredImports.reduce((sum, invoiceImport) => sum + (invoiceImport.total_ttc ?? 0), 0);
    const invalid = filteredImports.filter((i) => i.control_status === "invalid").length;
    const warnings = filteredImports.reduce((sum, invoiceImport) => sum + invoiceImport.control_warnings_count, 0);
    const errors = filteredImports.reduce((sum, invoiceImport) => sum + invoiceImport.control_errors_count, 0);
    return { totalTtc, invalid, warnings, errors };
  }, [filteredImports]);
  const activeFilterCount =
    controlFilters.length +
    decisionFilters.length +
    regroupementFilters.length +
    contractHolderFilters.length +
    invoiceMonthFilters.length +
    prmFilters.length +
    ficFilters.length +
    siteFilters.length +
    siteCityFilters.length +
    segmentFilters.length +
    tariffCodeFilters.length +
    tariffOptionLabelFilters.length +
    documentTypeFilters.length +
    issueFamilyFilters.length +
    issueCodeFilters.length +
    (invoiceSearch.trim() ? 1 : 0);

  useEffect(() => {
    if (selectedBatchId === null && batches[0]) {
      setSelectedBatchId(batches[0].id);
    }
  }, [batches, selectedBatchId]);

  const selectedBatchDetail = batchDetailQuery.data;

  const uploadMut = useMutation({
    mutationFn: (files: File[]) => uploadEnergyInvoiceBatch(token!, files),
    onSuccess: (batch) => {
      setUploadSummary(
        `${batch.imported_count} facture(s) importee(s), ${batch.duplicate_count} doublon(s), ${batch.error_count} erreur(s), ${batch.ignored_count} fichier(s) ignore(s).`,
      );
      setSelectedBatchId(batch.id);
      setSelectedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
      qc.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
      qc.invalidateQueries({ queryKey: ["energy-invoice-batches"] });
      qc.invalidateQueries({ queryKey: ["energy-invoice-monthly-consumption"] });
      qc.setQueryData(["energy-invoice-batch", batch.id], batch);
    },
  });

  const xlsxUploadMut = useMutation({
    mutationFn: (args: { file: File; forceUpdate: boolean }) =>
      uploadEngieXlsxExport(token!, args.file, { forceUpdate: args.forceUpdate }),
    onSuccess: (batch) => {
      setXlsxSummary(`Analyse XLSX lancee en arriere-plan (lot #${batch.id}). Les factures apparaitront automatiquement.`);
      setXlsxFile(null);
      setXlsxForceUpdate(false);
      if (xlsxInputRef.current) xlsxInputRef.current.value = "";
      setSelectedBatchId(batch.id);
      qc.setQueryData(["energy-invoice-batch", batch.id], batch);
      qc.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
      qc.invalidateQueries({ queryKey: ["energy-invoice-batches"] });
      qc.invalidateQueries({ queryKey: ["energy-invoice-monthly-consumption"] });
    },
  });

  const edfUploadMut = useMutation({
    mutationFn: (args: { file: File; forceUpdate: boolean }) =>
      uploadEdfCsvExport(token!, args.file, { forceUpdate: args.forceUpdate }),
    onSuccess: (batch) => {
      setEdfSummary(`Analyse CSV EDF lancee en arriere-plan (lot #${batch.id}). Les factures apparaitront automatiquement.`);
      setEdfFile(null);
      setEdfForceUpdate(false);
      if (edfInputRef.current) edfInputRef.current.value = "";
      setSelectedBatchId(batch.id);
      qc.setQueryData(["energy-invoice-batch", batch.id], batch);
      qc.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
      qc.invalidateQueries({ queryKey: ["energy-invoice-batches"] });
      qc.invalidateQueries({ queryKey: ["energy-invoice-monthly-consumption"] });
    },
  });

  const analyzeMut = useMutation({
    mutationFn: (invoiceImport: EnergyInvoiceImport) => analyzeEnergyInvoiceImport(token!, invoiceImport.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
      qc.invalidateQueries({ queryKey: ["energy-invoice-monthly-consumption"] });
    },
  });

  const bulkAnalyzeMut = useMutation({
    mutationFn: async (invoiceImports: EnergyInvoiceImport[]) => {
      for (const invoiceImport of invoiceImports) {
        await analyzeEnergyInvoiceImport(token!, invoiceImport.id);
      }
      return invoiceImports.length;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
      qc.invalidateQueries({ queryKey: ["energy-invoice-monthly-consumption"] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: (invoiceImport: EnergyInvoiceImport) => deleteEnergyInvoiceImport(token!, invoiceImport.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
      qc.invalidateQueries({ queryKey: ["energy-invoice-monthly-consumption"] });
    },
  });

  const deleteAllMut = useMutation({
    mutationFn: () => deleteAllEnergyInvoiceImports(token!),
    onSuccess: (result) => {
      setDeleteAllSummary(
        `${result.deleted} facture(s) supprimée(s), ${result.files_removed} fichier(s) supprimé(s) du disque (${result.files_kept} conservé(s) ou inaccessible(s)).`,
      );
      qc.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
      qc.invalidateQueries({ queryKey: ["energy-invoice-batches"] });
      qc.invalidateQueries({ queryKey: ["energy-invoice-monthly-consumption"] });
    },
  });

  function handleDeleteAll() {
    if (filteredImports.length === 0 && imports.length === 0) {
      window.alert("Aucune facture à supprimer.");
      return;
    }
    const typed = window.prompt(
      `⚠️ Vous êtes sur le point de supprimer DÉFINITIVEMENT TOUTES les ${imports.length} factures importées (et les fichiers associés). ` +
        `Cette action est IRRÉVERSIBLE.\n\nPour confirmer, tapez exactement : SUPPRIMER`,
    );
    if (typed === "SUPPRIMER") {
      deleteAllMut.mutate();
    } else if (typed !== null) {
      window.alert("Confirmation incorrecte : aucune suppression effectuée.");
    }
  }

  return (
    <div className="page">
      {!focused && (
        <div className="page-header">
          <div>
            <h2>Controle des factures fournisseurs</h2>
            <p className="page-subtitle">
              Marche Herault Energie - batiments hors CPE. Verifier chaque facture selon les modalites
              contractuelles (BPU, TURPE), produire un rapport fournisseur, puis la fiche de liaison comptable
              vers le service finance.
            </p>
          </div>
        </div>
      )}

      {!focused && (
        <div className="market-banner">
          <div className="market-banner-item market-banner-item--active">
            <span className="market-banner-tag">Marche en cours</span>
            <strong>Fournisseurs · Herault Energie</strong>
            <span>EDF · ENGIE · TotalEnergies - batiments hors CPE</span>
          </div>
          <Link to="/cpe" className="market-banner-item market-banner-item--link">
            <span className="market-banner-tag">Autre marche</span>
            <strong>CPE DALKIA →</strong>
            <span>P1 gaz, P2, P3 - batiments dans le CPE</span>
          </Link>
        </div>
      )}

      <details className="invoice-sources" hidden={focused}>
        <summary>Comment ca marche - sources de donnees et livrables</summary>
        <div className="invoice-sources-grid">
          <div>
            <strong>Donnees en entree</strong>
            <ul>
              <li>Factures fournisseur (export XLSX ENGIE, CSV EDF)</li>
              <li>Referentiel de prix BPU (<Link to="/energie/bpu">Prix et TURPE</Link>)</li>
              <li>Referentiel TURPE (acheminement)</li>
              <li>Releves distributeur ENEDIS / GRDF (controle des quantites)</li>
            </ul>
          </div>
          <div>
            <strong>Controle</strong>
            <ul>
              <li>Prix facture vs BPU contractuel</li>
              <li>Acheminement vs TURPE</li>
              <li>Quantites vs releves distributeur</li>
              <li>Coherence des periodes facturees</li>
            </ul>
          </div>
          <div>
            <strong>Livrables</strong>
            <ul>
              <li>Decision par facture (valider / contester)</li>
              <li>Rapport fournisseur (points a clarifier)</li>
              <li>Fiche de liaison Excel → service finance (matrice comptable)</li>
            </ul>
          </div>
        </div>
      </details>

      {!focused && (
        <div className="fluid-tabs" role="tablist" aria-label="Fluide">
          <FluidTab active={fluid === "elec"} onClick={() => setFluid("elec")}>Electricite</FluidTab>
          <FluidTab active={fluid === "gaz"} soon onClick={() => setFluid("gaz")}>Gaz</FluidTab>
          <FluidTab active={fluid === "eau"} soon onClick={() => setFluid("eau")}>Eau</FluidTab>
        </div>
      )}

      {!focused && fluid !== "elec" && (
        <section className="invoice-placeholder">
          <h3>{fluid === "gaz" ? "Gaz - a integrer" : "Eau - a integrer"}</h3>
          <p>
            {fluid === "gaz"
              ? "Le controle des factures gaz TotalEnergies (compteurs PCE, distributeur GRDF) s'appuiera sur le BPU gaz lot 7 Herault Energie. Le parser facture gaz et le rapprochement PCE restent a developper."
              : "Le controle des factures d'eau SUEZ (consommation + tarif) est prevu dans une prochaine iteration."}
          </p>
          <p className="page-subtitle">
            Cette page est concue pour accueillir les trois fluides. Le parcours sera identique : Donnees &amp; import →
            Controle contractuel → Rapport → Liaison finance.
          </p>
        </section>
      )}

      {fluid === "elec" && (
        <>
      <div className="kpi-row">
        <div className="kpi-card">
          <span className="kpi-label">Factures importees</span>
          <span className="kpi-value">{stats.total}</span>
        </div>
        <div className="kpi-card kpi-card--info">
          <span className="kpi-label">A controler</span>
          <span className="kpi-value">{stats.review}</span>
        </div>
        <div className="kpi-card kpi-card--alert">
          <span className="kpi-label">Invalides</span>
          <span className="kpi-value">{stats.invalid}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Valides</span>
          <span className="kpi-value">{stats.valid}</span>
        </div>
        <div className="kpi-card kpi-card--info">
          <span className="kpi-label">Decisions a rendre</span>
          <span className="kpi-value">{stats.decisionsToReview}</span>
        </div>
      </div>

      <div className="step-tabs" role="tablist" aria-label="Etapes du controle">
        <StepTab active={step === "data"} index={1} onClick={() => setStep("data")}>Donnees &amp; import</StepTab>
        <StepTab active={step === "control"} index={2} onClick={() => setStep("control")}>Controle contractuel</StepTab>
        <StepTab active={step === "report"} index={3} onClick={() => setStep("report")}>Rapport fournisseur</StepTab>
        <StepTab active={step === "liaison"} index={4} onClick={() => setStep("liaison")}>Liaison finance</StepTab>
      </div>

      {step === "data" && (
      <>
      {!focused && (
      <section className="invoice-supplier-strip">
        <div className="invoice-supplier-strip-head">
          <h3>Fournisseurs d'energie</h3>
          <span>Le distributeur (ENEDIS / GRDF) sert de reference de controle, pas de payeur.</span>
        </div>
        <div className="invoice-supplier-cards">
          {SUPPLIER_CATALOG.map((supplier) => {
            const summary = supplierSummary[supplier.key];
            const count = summary?.count ?? 0;
            return (
              <div
                key={supplier.key}
                className={`invoice-supplier-card${supplier.supported ? "" : " invoice-supplier-card--soon"}`}
              >
                <div className="invoice-supplier-card-top">
                  <strong>{supplier.label}</strong>
                  <span className={`badge ${supplier.supported ? "badge-green" : "badge-gray"}`}>
                    {supplier.supported ? "Actif" : "A integrer"}
                  </span>
                </div>
                <span className="invoice-supplier-meta">
                  {supplier.energyLabel} · {supplier.distributor} · {supplier.scope}
                </span>
                <div className="invoice-supplier-figures">
                  <span>{count} facture{count !== 1 ? "s" : ""}</span>
                  {summary && summary.total > 0 && <strong>{formatCurrency(summary.total)} TTC</strong>}
                </div>
              </div>
            );
          })}
        </div>
      </section>
      )}

      <section className="invoice-consumption-panel">
        <header className="invoice-consumption-header">
          <div>
            <p className="field-label">Controle conso : facture fournisseur vs releve distributeur</p>
            <h3>Facture vs releve ENEDIS - {currentYear}</h3>
            <span>Janvier a decembre, avec les filtres facture actifs.</span>
          </div>
          {monthlyConsumptionQuery.data && (
            <div className="invoice-consumption-kpis">
              <div>
                <strong>{formatKwh(monthlyConsumptionQuery.data.billed_total_kwh)}</strong>
                <span>ENGIE facture</span>
              </div>
              <div>
                <strong>{formatKwh(monthlyConsumptionQuery.data.enedis_total_kwh)}</strong>
                <span>ENEDIS releve</span>
              </div>
              <div>
                <strong>{formatKwh(monthlyConsumptionQuery.data.delta_total_kwh)}</strong>
                <span>Ecart facture - releve</span>
              </div>
              <div>
                <strong>{monthlyConsumptionQuery.data.invoice_count.toLocaleString("fr-FR")}</strong>
                <span>Factures retenues</span>
              </div>
            </div>
          )}
        </header>
        {monthlyConsumptionQuery.isLoading && <p className="loading-text">Chargement du suivi mensuel...</p>}
        {monthlyConsumptionQuery.isError && <p className="error-text">{(monthlyConsumptionQuery.error as Error).message}</p>}
        {monthlyConsumptionQuery.data && (
          <>
            <div className="invoice-consumption-chart">
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={monthlyConsumptionChartData} margin={{ top: 12, right: 18, bottom: 8, left: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.22)" />
                  <XAxis dataKey="label" tick={{ fill: "#cbd5e1", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis
                    yAxisId="kwh"
                    tick={{ fill: "#cbd5e1", fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                    width={84}
                    tickFormatter={(value) => `${Math.round(Number(value) / 1000).toLocaleString("fr-FR")} MWh`}
                  />
                  <YAxis
                    yAxisId="count"
                    orientation="right"
                    allowDecimals={false}
                    tick={{ fill: "#fbbf24", fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                    width={48}
                  />
                  <Tooltip
                    formatter={(value, name) => [
                      name === "invoice_count"
                        ? formatCount(Number(value), "facture(s)")
                        : name === "billed_prm_count"
                          ? formatCount(Number(value), "PRM")
                          : formatKwh(Number(value)),
                      name === "billed_kwh"
                        ? "ENGIE facture"
                        : name === "enedis_kwh"
                          ? "ENEDIS releve"
                          : name === "invoice_count"
                            ? "Factures"
                            : name === "billed_prm_count"
                              ? "PRM factures"
                              : String(name),
                    ]}
                    labelFormatter={(label, payload) => {
                      const point = payload?.[0]?.payload;
                      return `Mois : ${label}${point?.hasPotentialGap ? " - trou potentiel" : ""}`;
                    }}
                    contentStyle={{ background: "#0f172a", border: "1px solid rgba(148, 163, 184, 0.28)", borderRadius: 8 }}
                    labelStyle={{ color: "#e2e8f0" }}
                  />
                  <Legend wrapperStyle={{ color: "#cbd5e1", fontSize: 12 }} />
                  <Bar yAxisId="kwh" dataKey="billed_kwh" name="ENGIE facture" fill="#2563eb" radius={[3, 3, 0, 0]} />
                  <Line
                    yAxisId="kwh"
                    type="monotone"
                    dataKey="enedis_kwh"
                    name="ENEDIS releve"
                    stroke="#22c55e"
                    strokeWidth={3}
                    dot={{ r: 3 }}
                    connectNulls={false}
                  />
                  <Line
                    yAxisId="count"
                    type="monotone"
                    dataKey="invoice_count"
                    name="Factures"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    connectNulls={false}
                  />
                  <Line
                    yAxisId="count"
                    type="monotone"
                    dataKey="billed_prm_count"
                    name="PRM factures"
                    stroke="#fbbf24"
                    strokeDasharray="5 4"
                    strokeWidth={2}
                    dot={{ r: 2 }}
                    connectNulls={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="invoice-consumption-legend" aria-label="Legende du graphique de facturation">
              <span><strong>ENGIE facture</strong> : kWh factures par ENGIE, repartis au prorata des jours couverts.</span>
              <span><strong>ENEDIS releve</strong> : kWh releves par ENEDIS sur les PRM identifies.</span>
              <span><strong>Factures</strong> : nombre de bordereaux ENGIE retenus par mois.</span>
              <span><strong>PRM factures</strong> : nombre de compteurs distincts presents dans les factures du mois.</span>
            </div>
            {potentialGapMonths.length > 0 && (
              <div className="invoice-consumption-alert">
                <strong>Trou potentiel</strong>
                <span>
                  {potentialGapMonths.map((point) => point.label).join(", ")} : releves ENEDIS presents, mais aucune facture
                  rattachee au mois avec les filtres actifs.
                </span>
              </div>
            )}
            <p className="invoice-consumption-note">
              Factures : consommation repartie au prorata des jours couverts par chaque periode. ENEDIS :
              donnees journalieres disponibles sur {monthlyConsumptionQuery.data.enedis_prm_count} PRM sur{" "}
              {monthlyConsumptionQuery.data.prm_count} PRM identifies dans les factures retenues. Les courbes "Factures" et
              "PRM factures" aident a reperer une baisse de couverture ou un mois absent.
            </p>
          </>
        )}
      </section>

      {/*
        Pipeline PDF désactivé côté UI depuis le passage à l'import XLSX (mai 2026).
        Le code backend reste en place pour conserver l'accès aux factures historiques
        importées en PDF, mais on n'expose plus l'upload PDF/ZIP ni la section Lots
        d'import. Les nouveaux imports se font exclusivement via l'export XLSX ENGIE
        ci-dessous.
      */}

      <section className="invoice-upload-panel">
        <div>
          <p className="field-label">Import export ENGIE (XLSX)</p>
          <p className="invoice-upload-copy">
            Dépose le fichier <strong>MesFactures_*.xlsx</strong> exporté depuis l'espace ENGIE Entreprise.
            Chaque bordereau du fichier devient une facture importée séparément, avec analyse BPU/TURPE/périodes.
            Par défaut, les bordereaux déjà en base sont conservés tels quels (ta décision et ton historique sont préservés).
            Les bordereaux XLSX bloqués en erreur parser sont réparés automatiquement au réimport.
          </p>
        </div>
        <div className="invoice-upload-actions">
          <input
            ref={xlsxInputRef}
            type="file"
            accept=".xlsx,.xlsm"
            onChange={(e) => setXlsxFile(e.target.files?.[0] ?? null)}
            className="form-input"
          />
          <button
            type="button"
            className="btn-primary"
            disabled={xlsxFile === null || xlsxUploadMut.isPending}
            onClick={() => xlsxFile && xlsxUploadMut.mutate({ file: xlsxFile, forceUpdate: xlsxForceUpdate })}
          >
            {xlsxUploadMut.isPending
              ? (xlsxForceUpdate ? "Mise à jour en cours..." : "Analyse en cours...")
              : (xlsxForceUpdate ? "Importer et mettre à jour" : "Importer le XLSX")}
          </button>
        </div>
        <label className="invoice-upload-checkbox" title="Re-analyse les bordereaux déjà présents en base avec les données du nouveau fichier. La décision utilisateur (validée/contestée/à vérifier) est préservée.">
          <input
            type="checkbox"
            checked={xlsxForceUpdate}
            onChange={(e) => setXlsxForceUpdate(e.target.checked)}
          />
          <span>Forcer la mise à jour de tous les bordereaux déjà importés <em>(préserve les décisions utilisateur)</em></span>
        </label>
        {xlsxFile && (
          <p className="invoice-upload-selection">Fichier sélectionné : {xlsxFile.name}</p>
        )}
        {xlsxSummary && <p className="sync-result-ok">{xlsxSummary}</p>}
        {xlsxUploadMut.isError && <p className="error-text">{(xlsxUploadMut.error as Error).message}</p>}

        <div className="invoice-upload-divider" />
        <div>
          <p className="field-label">EDF — eclairage public (electricite)</p>
          <p className="page-subtitle">
            Depose l'export <strong>CSV</strong> de facturation EDF (un fichier = plusieurs factures).
          </p>
        </div>
        <div className="invoice-upload-actions">
          <input
            ref={edfInputRef}
            type="file"
            accept=".csv"
            onChange={(e) => setEdfFile(e.target.files?.[0] ?? null)}
            className="form-input"
          />
          <button
            type="button"
            className="btn-primary"
            disabled={edfFile === null || edfUploadMut.isPending}
            onClick={() => edfFile && edfUploadMut.mutate({ file: edfFile, forceUpdate: edfForceUpdate })}
          >
            {edfUploadMut.isPending
              ? (edfForceUpdate ? "Mise à jour en cours..." : "Analyse en cours...")
              : (edfForceUpdate ? "Importer et mettre à jour" : "Importer le CSV EDF")}
          </button>
        </div>
        <label className="invoice-upload-checkbox" title="Re-analyse les factures EDF déjà présentes avec les données du nouveau fichier. La décision utilisateur est préservée.">
          <input
            type="checkbox"
            checked={edfForceUpdate}
            onChange={(e) => setEdfForceUpdate(e.target.checked)}
          />
          <span>Forcer la mise à jour des factures EDF déjà importées <em>(préserve les décisions utilisateur)</em></span>
        </label>
        {edfFile && <p className="invoice-upload-selection">Fichier sélectionné : {edfFile.name}</p>}
        {edfSummary && <p className="sync-result-ok">{edfSummary}</p>}
        {edfUploadMut.isError && <p className="error-text">{(edfUploadMut.error as Error).message}</p>}
      </section>

      {/* Section "Lots d'import" désactivée depuis le passage XLSX-only (mai 2026).
          Conservée en code pour pouvoir réafficher l'historique des dépôts PDF si besoin. */}
      {xlsxBatches.length > 0 && (
      <details className="invoice-detail-section invoice-batch-disclosure">
        <summary className="invoice-batch-summary">
          <div>
            <h3>Traitements XLSX</h3>
            <p className="page-subtitle">Suivi des analyses lancees depuis les exports ENGIE.</p>
          </div>
          <span>{xlsxBatches.length} traitement{xlsxBatches.length > 1 ? "s" : ""}</span>
        </summary>
        {batchesQuery.isLoading && <p className="loading-text">Chargement des lots...</p>}
        {batchesQuery.isError && <p className="error-text">{(batchesQuery.error as Error).message}</p>}
        {xlsxBatches.length > 0 && (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Lot</th>
                  <th>Fichiers</th>
                  <th>Importees</th>
                  <th>Doublons</th>
                  <th>Erreurs / ignores</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {xlsxBatches.slice(0, 8).map((batch) => (
                  <tr key={batch.id}>
                    <td>
                      <div className="invoice-file-cell">
                        <strong>Lot #{batch.id}</strong>
                        <span>{formatDate(batch.created_at)}</span>
                      </div>
                    </td>
                    <td>{batch.file_count}</td>
                    <td>{batch.imported_count}</td>
                    <td>{batch.duplicate_count}</td>
                    <td>{batch.error_count} erreur(s), {batch.ignored_count} ignore(s)</td>
                    <td>
                      <button type="button" className="btn-secondary btn-compact" onClick={() => setSelectedBatchId(batch.id)}>
                        Voir le lot
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!batchesQuery.isLoading && xlsxBatches.length === 0 && <p className="cell-empty">Aucun traitement XLSX.</p>}

        {batchDetailQuery.isLoading && <p className="loading-text">Chargement du lot selectionne...</p>}
        {selectedBatchDetail && (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Fichier</th>
                  <th>Archive</th>
                  <th>Resultat</th>
                  <th>Message</th>
                  <th>Facture</th>
                </tr>
              </thead>
              <tbody>
                {(selectedBatchDetail?.items ?? []).map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="invoice-file-cell">
                        <strong>{item.original_filename}</strong>
                        <span>{item.file_size_bytes !== null ? formatSize(item.file_size_bytes) : "-"}</span>
                      </div>
                    </td>
                    <td>{item.archive_filename ?? "-"}</td>
                    <td>{batchItemBadge(item.status)}</td>
                    <td>{item.message ?? "-"}</td>
                    <td>
                      {item.invoice_import_id ? (
                        <Link to={`/factures/${item.invoice_import_id}`} className="btn-secondary btn-compact">
                          Detail
                        </Link>
                      ) : (
                        "-"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </details>
      )}

      </>
      )}

      {step === "control" && (
      <>
      <section className="invoice-control-workbench">
        <div className="invoice-control-workbench-header">
          <div>
            <p className="field-label">Controle factures</p>
            <h3>Piloter les validations finance</h3>
            <span>
              {sortedImports.length} facture{sortedImports.length > 1 ? "s" : ""} affichee{sortedImports.length > 1 ? "s" : ""}
              {" "}sur {imports.length} importee{imports.length > 1 ? "s" : ""} · {formatCurrency(filteredStats.totalTtc)} TTC
            </span>
          </div>
          <div className="invoice-control-workbench-kpis">
            <span><strong>{filteredStats.invalid}</strong> invalides</span>
            <span><strong>{filteredStats.errors}</strong> erreurs</span>
            <span><strong>{filteredStats.warnings}</strong> alertes</span>
            <span><strong>{supplierReportImports.length}</strong> lignes rapport</span>
          </div>
        </div>

        <div className="invoice-control-toolbar">
          <label className="invoice-control-search">
            <span className="field-label">Recherche</span>
            <input
              type="search"
              className="form-input"
              value={invoiceSearch}
              onChange={(e) => setInvoiceSearch(e.target.value)}
              placeholder="Facture, site, titulaire, PRM..."
            />
          </label>
          <button
            type="button"
            className="btn-secondary btn-compact"
            onClick={() => {
              setControlFilters(["review"]);
              setDecisionFilters([]);
            }}
          >
            A controler
          </button>
          <button
            type="button"
            className="btn-secondary btn-compact"
            onClick={() => {
              setControlFilters(["invalid"]);
              setDecisionFilters([]);
            }}
          >
            En erreur
          </button>
          <button
            type="button"
            className="btn-secondary btn-compact"
            onClick={() => {
              setControlFilters([]);
              setDecisionFilters(["to_review"]);
            }}
          >
            Decisions a rendre
          </button>
          <button
            type="button"
            className="btn-secondary btn-compact"
            onClick={resetInvoiceFilters}
            disabled={activeFilterCount === 0}
          >
            Reinitialiser{activeFilterCount > 0 ? ` (${activeFilterCount})` : ""}
          </button>
          <button
            type="button"
            className="btn-primary btn-compact"
            disabled={bulkAnalyzeMut.isPending || sortedImports.length === 0}
            onClick={() => bulkAnalyzeMut.mutate(sortedImports)}
          >
            {bulkAnalyzeMut.isPending ? "Controle en cours..." : "Lancer le controle global"}
          </button>
          <button
            type="button"
            className="btn-secondary btn-compact"
            disabled={supplierReportImports.length === 0}
            onClick={() => setStep("report")}
          >
            Aller au rapport
          </button>
          <button
            type="button"
            className="btn-secondary btn-compact"
            onClick={() => setStep("liaison")}
          >
            Aller a la liaison finance
          </button>
        </div>

        <details className="invoice-advanced-filters">
          <summary>
            <span>Filtres avances</span>
            <strong>{activeFilterCount === 0 ? "aucun filtre actif" : `${activeFilterCount} filtre${activeFilterCount > 1 ? "s" : ""} actif${activeFilterCount > 1 ? "s" : ""}`}</strong>
          </summary>
          <div className="form-grid">
          <InvoiceMultiFilter
            label="Controle"
            allLabel="Tous"
            options={CONTROL_FILTER_OPTIONS}
            values={controlFilters}
            onChange={setControlFilters}
          />
          <InvoiceMultiFilter
            label="Decision"
            allLabel="Toutes"
            options={DECISION_FILTER_OPTIONS}
            values={decisionFilters}
            onChange={setDecisionFilters}
          />
          <InvoiceMultiFilter
            label="Regroupement"
            allLabel="Tous"
            options={regroupements.map((regroupement) => ({ value: regroupement, label: regroupement }))}
            values={regroupementFilters}
            onChange={setRegroupementFilters}
          />
          <InvoiceMultiFilter
            label="Titulaire"
            allLabel="Tous"
            options={contractHolders.map((contractHolder) => ({ value: contractHolder, label: contractHolder }))}
            values={contractHolderFilters}
            onChange={setContractHolderFilters}
          />
          <InvoiceMultiFilter
            label="Mois facture"
            allLabel="Tous"
            options={invoiceMonths.map((month) => ({ value: month, label: month }))}
            values={invoiceMonthFilters}
            onChange={setInvoiceMonthFilters}
          />
          <InvoiceMultiFilter
            label="Segment"
            allLabel="Tous"
            options={segments.map((segment) => ({ value: segment, label: segment }))}
            values={segmentFilters}
            onChange={setSegmentFilters}
          />
          <InvoiceMultiFilter
            label="Version tarifaire"
            allLabel="Toutes"
            options={tariffCodes.map((tariffCode) => ({ value: tariffCode, label: tariffCode }))}
            values={tariffCodeFilters}
            onChange={setTariffCodeFilters}
          />
          <InvoiceMultiFilter
            label="Libelle tarifaire"
            allLabel="Tous"
            options={tariffOptionLabels.map((label) => ({ value: label, label }))}
            values={tariffOptionLabelFilters}
            onChange={setTariffOptionLabelFilters}
          />
          <InvoiceMultiFilter
            label="PRM/PCE"
            allLabel="Tous"
            options={prmIds.map((prm) => ({ value: prm, label: prm }))}
            values={prmFilters}
            onChange={setPrmFilters}
          />
          <InvoiceMultiFilter
            label="FIC"
            allLabel="Tous"
            options={ficNumbers.map((fic) => ({ value: fic, label: fic }))}
            values={ficFilters}
            onChange={setFicFilters}
          />
          <InvoiceMultiFilter
            label="Site"
            allLabel="Tous"
            options={siteNames.map((siteName) => ({ value: siteName, label: siteName }))}
            values={siteFilters}
            onChange={setSiteFilters}
          />
          <InvoiceMultiFilter
            label="Commune"
            allLabel="Toutes"
            options={siteCities.map((city) => ({ value: city, label: city }))}
            values={siteCityFilters}
            onChange={setSiteCityFilters}
          />
          <InvoiceMultiFilter
            label="Type document"
            allLabel="Tous"
            options={documentTypes.map((documentType) => ({ value: documentType, label: documentType }))}
            values={documentTypeFilters}
            onChange={setDocumentTypeFilters}
          />
          <InvoiceMultiFilter
            label="Categorie de probleme"
            allLabel="Toutes"
            options={issueFamilies.map((family) => ({ value: family, label: INVOICE_ISSUE_FAMILY_LABEL[family] }))}
            values={issueFamilyFilters}
            onChange={(families) => {
              setIssueFamilyFilters(families);
              setIssueCodeFilters([]);
            }}
          />
          <InvoiceMultiFilter
            label="Type de probleme"
            allLabel="Tous"
            options={issueCodes.map((issue) => ({
              value: issue.code,
              label: `${INVOICE_ISSUE_FAMILY_LABEL[issue.family]} : ${issue.label ?? issue.code}`,
              title: issue.message,
            }))}
            values={issueCodeFilters}
            onChange={setIssueCodeFilters}
          />
          </div>
        </details>
      </section>

      </>
      )}

      {step === "data" && activeTurpeVersion && (
        <section className="turpe-reference-panel">
          <div className="turpe-reference-main">
            <p className="field-label">Referentiel TURPE</p>
            <strong>{activeTurpeVersion.label}</strong>
            <span>
              Valide du {formatShortDate(activeTurpeVersion.valid_from)} au{" "}
              {formatShortDate(activeTurpeVersion.valid_to)}
            </span>
          </div>
          <div className="turpe-reference-meta">
            <span>Prochaine mise a jour attendue : {formatShortDate(activeTurpeVersion.next_expected_update)}</span>
            <a href={activeTurpeVersion.source_url} target="_blank" rel="noreferrer" className="secondary-link">
              Source Enedis
            </a>
          </div>
        </section>
      )}

      {importsQuery.isLoading && <p className="loading-text">Chargement des imports...</p>}
      {importsQuery.isError && <p className="error-text">{(importsQuery.error as Error).message}</p>}

      {step === "control" && (
      <>
      <section className="invoice-timeline-panel">
        <header className="invoice-timeline-panel-header">
          <div>
            <strong>Frise des periodes facturees</strong>
            <span>
              {periodTimelineGroups.length} regroupement{periodTimelineGroups.length > 1 ? "s" : ""} ·
              {" "}{periodTimelineGroups.reduce((sum, g) => sum + g.items.length, 0)} facture{periodTimelineGroups.reduce((sum, g) => sum + g.items.length, 0) > 1 ? "s" : ""} sur la fenetre filtree
            </span>
          </div>
          <button
            type="button"
            className="btn-secondary btn-compact"
            onClick={() => setIsTimelineOpen((value) => !value)}
          >
            {isTimelineOpen ? "Masquer" : "Afficher"}
          </button>
        </header>
        {isTimelineOpen && (
          <InvoicePeriodTimeline groups={periodTimelineGroups} />
        )}
      </section>

      <div className="invoice-table-toolbar">
        <div>
          <strong>{sortedImports.length} facture{sortedImports.length > 1 ? "s" : ""}</strong>
          {sortedImports.length !== imports.length && (
            <span className="text-muted"> (sur {imports.length} importée{imports.length > 1 ? "s" : ""})</span>
          )}
          {sortColumn && (
            <span className="text-muted"> · trié par {sortColumn} {sortDir === "asc" ? "↑" : "↓"}</span>
          )}
        </div>
        <div className="invoice-action-cell">
          {deleteAllSummary && <span className="sync-result-ok">{deleteAllSummary}</span>}
          <button
            type="button"
            className="btn-danger btn-compact"
            disabled={deleteAllMut.isPending || imports.length === 0}
            onClick={handleDeleteAll}
          >
            {deleteAllMut.isPending ? "Suppression en cours..." : "Tout supprimer"}
          </button>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="data-table invoice-sortable-table">
          <thead>
            <tr>
              <th onClick={() => toggleSort("fichier")} className="sortable">Fichier{sortIndicator("fichier")}</th>
              <th onClick={() => toggleSort("facture")} className="sortable">Facture{sortIndicator("facture")}</th>
              <th onClick={() => toggleSort("regroupement")} className="sortable">Regroupement{sortIndicator("regroupement")}</th>
              <th onClick={() => toggleSort("titulaire")} className="sortable">Titulaire{sortIndicator("titulaire")}</th>
              <th onClick={() => toggleSort("montant")} className="sortable">Montant{sortIndicator("montant")}</th>
              <th onClick={() => toggleSort("controle")} className="sortable">Controle{sortIndicator("controle")}</th>
              <th onClick={() => toggleSort("decision")} className="sortable">Decision{sortIndicator("decision")}</th>
              <th onClick={() => toggleSort("import")} className="sortable">Import{sortIndicator("import")}</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {sortedImports.map((invoiceImport) => (
              <tr key={invoiceImport.id}>
                <td>
                  <div className="invoice-file-cell">
                    <strong>{invoiceImport.original_filename}</strong>
                    <span>{invoiceImport.supplier_guess ?? "-"} | {formatSize(invoiceImport.file_size_bytes)} | {invoiceImport.sha256.slice(0, 12)}</span>
                  </div>
                </td>
                <td>
                  <div className="invoice-file-cell">
                    <strong>{invoiceImport.invoice_number ?? "-"}</strong>
                    <span>{formatShortDate(invoiceImport.invoice_date)}</span>
                  </div>
                </td>
                <td>{invoiceImport.regroupement ?? "-"}</td>
                <td>{invoiceImport.contract_holder ?? "-"}</td>
                <td>
                  <div className="invoice-file-cell">
                    <strong>{formatCurrency(invoiceImport.total_ttc)}</strong>
                    <span>
                      {invoiceImport.site_count ?? 0} PRM |{" "}
                      {invoiceImport.total_consumption_kwh !== null
                        ? `${Math.round(invoiceImport.total_consumption_kwh).toLocaleString("fr-FR")} kWh`
                        : "-"}
                    </span>
                  </div>
                </td>
                <td>
                  <div className="invoice-control-cell">
                    {controlBadge(invoiceImport)}
                    <span>
                      {invoiceImport.control_errors_count} erreur(s), {invoiceImport.control_warnings_count} alerte(s)
                    </span>
                    {controlIssueTags(invoiceImport)}
                    {invoiceImport.control_issues[0] && <small>{invoiceImport.control_issues[0].message}</small>}
                  </div>
                </td>
                <td>
                  <div className="invoice-control-cell">
                    {decisionBadge(invoiceImport)}
                    {invoiceImport.decision_updated_at && <small>{formatDate(invoiceImport.decision_updated_at)}</small>}
                  </div>
                </td>
                <td>{formatDate(invoiceImport.created_at)}</td>
                <td>
                  <div className="invoice-action-cell">
                    {statusBadge(invoiceImport)}
                    <span className="badge badge-gray">{IMPORT_STATUS_LABEL[invoiceImport.status] ?? invoiceImport.source}</span>
                    <button
                      type="button"
                      className="btn-secondary btn-compact"
                      disabled={analyzeMut.isPending}
                      onClick={() => analyzeMut.mutate(invoiceImport)}
                    >
                      {invoiceImport.analysis_status === "pending" || invoiceImport.analysis_status === "failed"
                        ? "Analyser"
                        : "Relancer"}
                    </button>
                    <Link to={`/factures/${invoiceImport.id}`} className="btn-secondary btn-compact">
                      Detail
                    </Link>
                    <button
                      type="button"
                      className="btn-danger btn-compact"
                      disabled={deleteMut.isPending}
                      onClick={() => {
                        if (window.confirm(`Supprimer la facture "${invoiceImport.original_filename}" ? Cette action est irréversible.`)) {
                          deleteMut.mutate(invoiceImport);
                        }
                      }}
                    >
                      Supprimer
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!importsQuery.isLoading && sortedImports.length === 0 && (
              <tr>
                <td colSpan={9} className="cell-empty">Aucune facture ne correspond aux filtres.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      </>
      )}

      {step === "report" && (
        <section className="invoice-step-panel">
          <div className="invoice-step-panel-head">
            <div>
              <p className="field-label">Etape 3 - Rapport fournisseur</p>
              <h3>Construire le rapport a transmettre au fournisseur</h3>
              <span>
                Le rapport reprend les points a clarifier (ecarts de prix BPU, periodes, TURPE) sur le perimetre
                filtre a l'etape Controle. {supplierReportImports.length} facture{supplierReportImports.length > 1 ? "s" : ""} retenue{supplierReportImports.length > 1 ? "s" : ""}.
              </span>
            </div>
            <button
              type="button"
              className="btn-primary"
              disabled={supplierReportImports.length === 0}
              onClick={() => setIsSupplierReportOpen(true)}
            >
              Editer le rapport fournisseur
            </button>
          </div>
          <p className="invoice-step-hint">
            Affinez d'abord le perimetre a l'etape{" "}
            <button type="button" className="btn-secondary btn-compact" onClick={() => setStep("control")}>
              Controle contractuel
            </button>{" "}
            (filtres, factures a contester), puis revenez ici.
          </p>
        </section>
      )}

      {step === "liaison" && (
        <section className="invoice-step-panel">
          <div className="invoice-step-panel-head">
            <div>
              <p className="field-label">Etape 4 - Liaison finance comptable</p>
              <h3>Generer la fiche de liaison vers le service finance</h3>
              <span>
                La matrice comptable associe chaque site (PRM) et chaque poste de facture a une nature comptable.
                Elle alimente l'export Excel de liaison transmis au service finance.
              </span>
            </div>
            <button type="button" className="btn-primary" onClick={() => setIsAccountingOpen(true)}>
              Ouvrir la matrice comptable
            </button>
          </div>
          <p className="invoice-step-hint">
            <strong>{imports.filter((i) => i.finance_exported_at).length}</strong> / {imports.length} facture
            {imports.length > 1 ? "s" : ""} transmise{imports.length > 1 ? "s" : ""} au service finance.
            L'export de la fiche de liaison (par facture) horodate la transmission ; il s'ouvre depuis le detail
            de chaque facture, et la matrice (codification sites + postes) dans une fenetre dediee.
          </p>
        </section>
      )}
        </>
      )}

      {isSupplierReportOpen && (
        <InvoiceSupplierReport
          invoiceImports={supplierReportImports}
          filters={{
            search: invoiceSearch,
            controls: controlFilters,
            decisions: decisionFilters,
            regroupements: regroupementFilters,
            contractHolders: contractHolderFilters,
            invoiceMonths: invoiceMonthFilters,
            prmIds: prmFilters,
            ficNumbers: ficFilters,
            siteNames: siteFilters,
            siteCities: siteCityFilters,
            segments: segmentFilters,
            tariffCodes: tariffCodeFilters,
            tariffOptionLabels: tariffOptionLabelFilters,
            documentTypes: documentTypeFilters,
            issueFamilies: issueFamilyFilters,
            issueCodes: issueCodeFilters,
          }}
          onClose={() => setIsSupplierReportOpen(false)}
          token={token}
        />
      )}

      {isAccountingOpen && <EnergieAccountingMatrix onClose={() => setIsAccountingOpen(false)} />}
    </div>
  );
}
