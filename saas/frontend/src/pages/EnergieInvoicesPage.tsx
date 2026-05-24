import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  analyzeEnergyInvoiceImport,
  deleteEnergyInvoiceImport,
  deleteAllEnergyInvoiceImports,
  fetchEnergyInvoiceBatch,
  fetchEnergyInvoiceBatches,
  fetchEnergyInvoiceImports,
  fetchTurpeVersions,
  uploadEnergyInvoiceBatch,
  uploadEngieXlsxExport,
} from "../lib/api";
import type { EnergyInvoiceImport } from "../lib/api";
import { InvoiceSupplierReport } from "../components/InvoiceSupplierReport";
import { InvoicePeriodTimeline } from "../components/InvoicePeriodTimeline";
import type { TimelineGroup, TimelineItem } from "../components/InvoicePeriodTimeline";
import {
  INVOICE_ISSUE_FAMILY_LABEL,
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

export function EnergieInvoicesPage() {
  const { token } = useAuth();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const xlsxInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadSummary, setUploadSummary] = useState<string | null>(null);
  const [xlsxFile, setXlsxFile] = useState<File | null>(null);
  const [xlsxSummary, setXlsxSummary] = useState<string | null>(null);
  const [xlsxForceUpdate, setXlsxForceUpdate] = useState(false);
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
  const [issueFamilyFilters, setIssueFamilyFilters] = useState<InvoiceIssueFamily[]>([]);
  const [issueCodeFilters, setIssueCodeFilters] = useState<string[]>([]);
  const [isSupplierReportOpen, setIsSupplierReportOpen] = useState(false);
  const [isTimelineOpen, setIsTimelineOpen] = useState(false);

  const importsQuery = useQuery({
    queryKey: ["energy-invoice-imports"],
    queryFn: () => fetchEnergyInvoiceImports(token!),
    enabled: !!token,
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
  });

  const batchDetailQuery = useQuery({
    queryKey: ["energy-invoice-batch", selectedBatchId],
    queryFn: () => fetchEnergyInvoiceBatch(token!, selectedBatchId as number),
    enabled: !!token && selectedBatchId !== null,
  });

  const imports = importsQuery.data ?? [];
  const batches = batchesQuery.data ?? [];
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
  const issueFamilies = useMemo(
    () =>
      Array.from(new Set(imports.flatMap((invoiceImport) => invoiceIssueFamilies(invoiceImport.control_issues)))).sort((a, b) =>
        INVOICE_ISSUE_FAMILY_LABEL[a].localeCompare(INVOICE_ISSUE_FAMILY_LABEL[b], "fr"),
      ),
    [imports],
  );
  const issueCodes = useMemo(() => {
    const options = new Map<string, { code: string; family: InvoiceIssueFamily; message: string }>();
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
      ]
        .filter(Boolean)
        .some((value) => value?.toLowerCase().includes(search));
    });
  }, [
    contractHolderFilters,
    controlFilters,
    decisionFilters,
    imports,
    invoiceSearch,
    issueCodeFilters,
    issueFamilyFilters,
    regroupementFilters,
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
    return { total: imports.length, invalid, review, valid };
  }, [imports]);

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
      qc.setQueryData(["energy-invoice-batch", batch.id], batch);
    },
  });

  const xlsxUploadMut = useMutation({
    mutationFn: (args: { file: File; forceUpdate: boolean }) =>
      uploadEngieXlsxExport(token!, args.file, { forceUpdate: args.forceUpdate }),
    onSuccess: (summary) => {
      const parts = [`${summary.created} facture(s) créée(s)`];
      if (summary.updated > 0) parts.push(`${summary.updated} mise(s) à jour`);
      if (summary.duplicates > 0) parts.push(`${summary.duplicates} doublon(s) skippé(s)`);
      if (summary.errors > 0) parts.push(`${summary.errors} erreur(s)`);
      setXlsxSummary(
        `Export XLSX traité : ${summary.total_bordereaux} bordereau(x) lu(s) — ${parts.join(", ")}.`,
      );
      setXlsxFile(null);
      setXlsxForceUpdate(false);
      if (xlsxInputRef.current) xlsxInputRef.current.value = "";
      qc.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
    },
  });

  const analyzeMut = useMutation({
    mutationFn: (invoiceImport: EnergyInvoiceImport) => analyzeEnergyInvoiceImport(token!, invoiceImport.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: (invoiceImport: EnergyInvoiceImport) => deleteEnergyInvoiceImport(token!, invoiceImport.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
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
      <div className="page-header page-header-row">
        <div>
          <h2>Factures energie</h2>
          <p className="page-subtitle">Import manuel des factures fournisseur avant controle et validation.</p>
        </div>
      </div>

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
      </div>

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
          <span>Forcer la mise à jour des bordereaux déjà importés <em>(préserve les décisions utilisateur)</em></span>
        </label>
        {xlsxFile && (
          <p className="invoice-upload-selection">Fichier sélectionné : {xlsxFile.name}</p>
        )}
        {xlsxSummary && <p className="sync-result-ok">{xlsxSummary}</p>}
        {xlsxUploadMut.isError && <p className="error-text">{(xlsxUploadMut.error as Error).message}</p>}
      </section>

      {/* Section "Lots d'import" désactivée depuis le passage XLSX-only (mai 2026).
          Conservée en code pour pouvoir réafficher l'historique des dépôts PDF si besoin. */}
      {false && (
      <details className="invoice-detail-section invoice-batch-disclosure">
        <summary className="invoice-batch-summary">
          <div>
            <h3>Lots d'import</h3>
            <p className="page-subtitle">Historique des depots manuels avant la connexion API ENGIE.</p>
          </div>
          <span>{batches.length} lot{batches.length > 1 ? "s" : ""}</span>
        </summary>
        {batchesQuery.isLoading && <p className="loading-text">Chargement des lots...</p>}
        {batchesQuery.isError && <p className="error-text">{(batchesQuery.error as Error).message}</p>}
        {batches.length > 0 && (
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
                {batches.slice(0, 8).map((batch) => (
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
        {!batchesQuery.isLoading && batches.length === 0 && <p className="cell-empty">Aucun lot facture importe.</p>}

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
                        <Link to={`/energie/factures/${item.invoice_import_id}`} className="btn-secondary btn-compact">
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

      <section className="invoice-detail-section">
        <h3>Filtrer les factures</h3>
        <div className="invoice-action-cell">
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
            onClick={() => {
              setControlFilters([]);
              setDecisionFilters([]);
              setRegroupementFilters([]);
              setContractHolderFilters([]);
              setIssueFamilyFilters([]);
              setIssueCodeFilters([]);
              setInvoiceSearch("");
            }}
          >
            Reinitialiser
          </button>
          <button
            type="button"
            className="btn-primary btn-compact"
            disabled={supplierReportImports.length === 0}
            onClick={() => setIsSupplierReportOpen(true)}
          >
            Editer rapport
          </button>
        </div>
        <div className="form-grid">
          <label>
            <span className="field-label">Recherche</span>
            <input
              type="search"
              className="form-input"
              value={invoiceSearch}
              onChange={(e) => setInvoiceSearch(e.target.value)}
              placeholder="Facture, fichier, regroupement, titulaire"
            />
          </label>
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
              label: `${INVOICE_ISSUE_FAMILY_LABEL[issue.family]} : ${issue.code}`,
              title: issue.message,
            }))}
            values={issueCodeFilters}
            onChange={setIssueCodeFilters}
          />
        </div>
      </section>

      {activeTurpeVersion && (
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
                    <Link to={`/energie/factures/${invoiceImport.id}`} className="btn-secondary btn-compact">
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

      {isSupplierReportOpen && (
        <InvoiceSupplierReport
          invoiceImports={supplierReportImports}
          filters={{
            search: invoiceSearch,
            controls: controlFilters,
            decisions: decisionFilters,
            regroupements: regroupementFilters,
            contractHolders: contractHolderFilters,
            issueFamilies: issueFamilyFilters,
            issueCodes: issueCodeFilters,
          }}
          onClose={() => setIsSupplierReportOpen(false)}
          token={token}
        />
      )}
    </div>
  );
}
