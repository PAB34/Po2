import { useEffect, useMemo, useState } from "react";
import type {
  EnergyInvoiceImport,
  EnergyInvoiceImportDetail,
} from "../lib/api";
import { fetchEnergyInvoiceImport } from "../lib/api";
import {
  INVOICE_ISSUE_FAMILY_DETAIL,
  INVOICE_ISSUE_FAMILY_LABEL,
  invoiceIssueFamily,
  isInternalControlLimit,
} from "../lib/invoiceIssues";
import type { InvoiceIssueFamily } from "../lib/invoiceIssues";
import { InvoicePeriodTimeline } from "./InvoicePeriodTimeline";
import type { TimelineGroup, TimelineItem } from "./InvoicePeriodTimeline";

const CONTROL_FILTER_LABEL: Record<string, string> = {
  all: "Tous",
  valid: "Valides",
  review: "A controler",
  invalid: "Invalides",
  not_checked: "Non controlees",
};

const DECISION_FILTER_LABEL: Record<string, string> = {
  all: "Toutes",
  to_review: "A verifier",
  approved: "Validees",
  rejected: "Refusees",
  dispute_sent: "Contestation envoyee",
};

type InvoiceSupplierReportFilters = {
  search: string;
  controls: string[];
  decisions: string[];
  regroupements: string[];
  contractHolders: string[];
  invoiceMonths: string[];
  prmIds: string[];
  ficNumbers: string[];
  siteNames: string[];
  siteCities: string[];
  segments: string[];
  tariffCodes: string[];
  tariffOptionLabels: string[];
  documentTypes: string[];
  issueFamilies: InvoiceIssueFamily[];
  issueCodes: string[];
};

type IssueGroup = {
  family: InvoiceIssueFamily;
  codes: Set<string>;
  invoiceIds: Set<number>;
  scopes: Set<string>;
  count: number;
};

type PeriodIssueRow = {
  invoiceRef: string;
  code: string;
  message: string;
  scope: string;
  kind: "gap" | "overlap" | "other";
};

// Structures persistées par le backend dans control_report.bpu.mismatches_detail
// (cf. _record_bpu_mismatch / _record_bpu_tariff_poste_inconsistency dans
// saas/backend/app/services/invoice_analysis.py). Aucun parsing de message ni heuristique.

type BpuPriceMismatch = {
  type: "price_mismatch";
  scope: string | null;
  site_prm_id: string | null;
  site_fic_number: string | null;
  line_index: number;
  line_label: string | null;
  line_normalized_component: string | null;
  line_poste: string | null;
  invoice_price_eur_mwh: number;
  bpu_price_eur_mwh: number;
  delta_eur_mwh: number;
  quantity: number | null;
  quantity_unit: string | null;
  quantity_mwh: number | null;
  delta_total_eur_ht: number | null;
  bpu_reference: string;
  source: "historical" | "configured";
};

type BpuTariffPosteInconsistencyLine = {
  line_index: number;
  line_label: string | null;
  line_normalized_component: string | null;
  line_poste: string | null;
  invoice_unit_price_eur_mwh: number;
  invoice_amount_ht: number | null;
  quantity: number | null;
  quantity_unit: string | null;
  quantity_mwh: number | null;
};

type BpuTariffPosteInconsistency = {
  type: "tariff_poste_inconsistency";
  scope: string | null;
  site_prm_id: string | null;
  site_fic_number: string | null;
  expected_bpu_reference: string;
  expected_bpu_price_eur_mwh: number;
  invoice_postes_used: string[];
  matching_bpu_lines: string[];
  lines_count: number;
  lines: BpuTariffPosteInconsistencyLine[];
  total_quantity_mwh: number | null;
  total_amount_invoice_ht: number;
  total_amount_if_expected_ht: number | null;
  delta_total_eur_ht: number | null;
  source: "configured";
};

type BpuMismatchDetail = BpuPriceMismatch | BpuTariffPosteInconsistency;

type Props = {
  invoiceImports: EnergyInvoiceImport[];
  filters: InvoiceSupplierReportFilters;
  onClose: () => void;
  token: string | null;
};

function formatShortDate(value: string | null | undefined) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(new Date(value));
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value);
}

function formatGeneratedAt() {
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeStyle: "short" }).format(new Date());
}

function invoiceReference(invoiceImport: EnergyInvoiceImport) {
  return invoiceImport.invoice_number ?? invoiceImport.original_filename;
}

// Extrait le PRM (1re partie avant " / ") d'un scope d'issue.
// Ex : "24309117128642 / FIC 630000534222 / 2026-03-05 - 2026-04-04" → "24309117128642"
function extractPrm(scope: string | null | undefined): string | null {
  if (!scope) return null;
  const first = scope.split(" / ")[0]?.trim();
  if (!first) return null;
  if (/^\d{10,18}$/.test(first)) return first;
  return null;
}

function filteredIssues(invoiceImport: EnergyInvoiceImport, filters: InvoiceSupplierReportFilters) {
  return invoiceImport.control_issues.filter((issue) => {
    const family = invoiceIssueFamily(issue);
    if (filters.issueFamilies.length > 0 && !filters.issueFamilies.includes(family)) return false;
    if (filters.issueCodes.length > 0 && !filters.issueCodes.includes(issue.code)) return false;
    return true;
  });
}

function selectedIssues(invoiceImport: EnergyInvoiceImport, filters: InvoiceSupplierReportFilters) {
  return filteredIssues(invoiceImport, filters);
}

function excludedInternalIssues(invoiceImport: EnergyInvoiceImport, filters: InvoiceSupplierReportFilters) {
  return filteredIssues(invoiceImport, filters).filter(isInternalControlLimit);
}

function activeFilters(filters: InvoiceSupplierReportFilters) {
  const values: string[] = [];
  const search = filters.search.trim();
  if (search) values.push(`Recherche : ${search}`);
  if (filters.controls.length > 0) {
    values.push(`Controle : ${filters.controls.map((value) => CONTROL_FILTER_LABEL[value] ?? value).join(", ")}`);
  }
  if (filters.decisions.length > 0) {
    values.push(`Decision : ${filters.decisions.map((value) => DECISION_FILTER_LABEL[value] ?? value).join(", ")}`);
  }
  if (filters.regroupements.length > 0) values.push(`Regroupement : ${filters.regroupements.join(", ")}`);
  if (filters.contractHolders.length > 0) values.push(`Titulaire : ${filters.contractHolders.join(", ")}`);
  if (filters.invoiceMonths.length > 0) values.push(`Mois facture : ${filters.invoiceMonths.join(", ")}`);
  if (filters.prmIds.length > 0) values.push(`PRM/PCE : ${filters.prmIds.join(", ")}`);
  if (filters.ficNumbers.length > 0) values.push(`FIC : ${filters.ficNumbers.join(", ")}`);
  if (filters.siteNames.length > 0) values.push(`Site : ${filters.siteNames.join(", ")}`);
  if (filters.siteCities.length > 0) values.push(`Commune : ${filters.siteCities.join(", ")}`);
  if (filters.segments.length > 0) values.push(`Segment : ${filters.segments.join(", ")}`);
  if (filters.tariffCodes.length > 0) values.push(`Tarif : ${filters.tariffCodes.join(", ")}`);
  if (filters.tariffOptionLabels.length > 0) values.push(`Libelle tarifaire : ${filters.tariffOptionLabels.join(", ")}`);
  if (filters.documentTypes.length > 0) values.push(`Document : ${filters.documentTypes.join(", ")}`);
  if (filters.issueFamilies.length > 0) {
    values.push(`Categorie : ${filters.issueFamilies.map((family) => INVOICE_ISSUE_FAMILY_LABEL[family]).join(", ")}`);
  }
  if (filters.issueCodes.length > 0) values.push(`Type : ${filters.issueCodes.join(", ")}`);
  return values;
}

// Agrège les issues PAR FAMILLE — un seul bloc par catégorie listant tous les codes/scopes.
function groupIssuesByFamily(
  invoiceImports: EnergyInvoiceImport[],
  filters: InvoiceSupplierReportFilters,
  selectIssues: typeof selectedIssues = selectedIssues,
) {
  const groups = new Map<InvoiceIssueFamily, IssueGroup>();

  for (const invoiceImport of invoiceImports) {
    for (const issue of selectIssues(invoiceImport, filters)) {
      const family = invoiceIssueFamily(issue);
      const group = groups.get(family) ?? {
        family,
        codes: new Set<string>(),
        invoiceIds: new Set<number>(),
        scopes: new Set<string>(),
        count: 0,
      };
      group.count += 1;
      group.codes.add(issue.code);
      group.invoiceIds.add(invoiceImport.id);
      if (issue.scope) group.scopes.add(issue.scope);
      groups.set(family, group);
    }
  }

  return Array.from(groups.values()).sort(
    (a, b) =>
      INVOICE_ISSUE_FAMILY_LABEL[a.family].localeCompare(INVOICE_ISSUE_FAMILY_LABEL[b.family], "fr"),
  );
}

// Lit les mismatches détaillés persistés par le backend.
// Si l'analyse est antérieure à l'enrichissement → retourne null (le frontend affichera une note).
function extractMismatchesDetail(detail: EnergyInvoiceImportDetail | undefined): BpuMismatchDetail[] | null {
  if (!detail?.control_report) return null;
  const bpu = detail.control_report.bpu;
  if (!bpu || typeof bpu !== "object") return null;
  const list = (bpu as Record<string, unknown>).mismatches_detail;
  if (!Array.isArray(list)) return null;
  return list as BpuMismatchDetail[];
}

function shouldShowBpuMismatch(detail: BpuMismatchDetail, filters: InvoiceSupplierReportFilters) {
  if (filters.issueCodes.length === 0) return true;
  const code = detail.type === "tariff_poste_inconsistency" ? "BPU_TARIFF_POSTE_INCONSISTENCY" : "BPU_PRICE_MISMATCH";
  return filters.issueCodes.includes(code);
}

function prmListForInvoice(
  invoiceImport: EnergyInvoiceImport,
  filters: InvoiceSupplierReportFilters,
): string[] {
  const set = new Set<string>();
  for (const issue of selectedIssues(invoiceImport, filters)) {
    const prm = extractPrm(issue.scope);
    if (prm) set.add(prm);
  }
  return Array.from(set).sort();
}

function familiesForInvoice(
  invoiceImport: EnergyInvoiceImport,
  filters: InvoiceSupplierReportFilters,
): InvoiceIssueFamily[] {
  return Array.from(new Set(selectedIssues(invoiceImport, filters).map((issue) => invoiceIssueFamily(issue))));
}

function uniqueIssueScopesForFamily(
  invoiceImports: EnergyInvoiceImport[],
  family: InvoiceIssueFamily,
  filters: InvoiceSupplierReportFilters,
): string[] {
  const set = new Set<string>();
  for (const invoiceImport of invoiceImports) {
    for (const issue of selectedIssues(invoiceImport, filters)) {
      if (invoiceIssueFamily(issue) === family && issue.scope) set.add(issue.scope);
    }
  }
  return Array.from(set).sort();
}

function periodIssueRows(invoiceImports: EnergyInvoiceImport[], filters: InvoiceSupplierReportFilters): PeriodIssueRow[] {
  const rows: PeriodIssueRow[] = [];
  for (const invoiceImport of invoiceImports) {
    for (const issue of selectedIssues(invoiceImport, filters)) {
      if (invoiceIssueFamily(issue) !== "periods" || !issue.scope) continue;
      rows.push({
        invoiceRef: invoiceReference(invoiceImport),
        code: issue.code,
        message: issue.message,
        scope: issue.scope,
        kind: issue.code === "PERIOD_OVERLAP" ? "overlap" : issue.code === "PERIOD_GAP" ? "gap" : "other",
      });
    }
  }
  return rows.sort((a, b) => a.scope.localeCompare(b.scope, "fr") || a.invoiceRef.localeCompare(b.invoiceRef, "fr"));
}

function periodIssueKindLabel(kind: PeriodIssueRow["kind"]) {
  if (kind === "overlap") return "Chevauchement : risque de double facturation sur les memes jours.";
  if (kind === "gap") return "Trou : jours potentiellement non factures entre deux periodes.";
  return "Periode a verifier : date manquante ou incoherence detectee.";
}

// Parse un scope d'issue Periode au format "PRM / FIC nnnn / YYYY-MM-DD - YYYY-MM-DD"
// → {prm, fic, period_start, period_end}. Retourne null si le format ne match pas.
function parseScopeWithPeriod(scope: string): {
  prm: string | null;
  fic: string | null;
  startISO: string;
  endISO: string;
} | null {
  // Match : ... / YYYY-MM-DD - YYYY-MM-DD à la fin
  const dateMatch = scope.match(/(\d{4}-\d{2}-\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})\s*$/);
  if (!dateMatch) return null;
  const startISO = dateMatch[1];
  const endISO = dateMatch[2];
  const prefix = scope.slice(0, dateMatch.index).trim().replace(/\/\s*$/, "").trim();
  // Prefix peut être "PRM / FIC nnnn" ou seulement "PRM" ou seulement "FIC nnnn"
  const parts = prefix.split(/\s*\/\s*/);
  let prm: string | null = null;
  let fic: string | null = null;
  for (const part of parts) {
    if (/^\d{10,18}$/.test(part)) prm = part;
    else {
      const ficMatch = part.match(/FIC\s+(\d+)/i);
      if (ficMatch) fic = ficMatch[1];
    }
  }
  return { prm, fic, startISO, endISO };
}

// Construit les groupes timeline à partir des issues Périodes d'une liste de factures.
// Groupé par regroupement de la facture (fallback : titulaire / "Non regroupe").
function buildPeriodTimelineGroups(
  invoiceImports: EnergyInvoiceImport[],
  filters: InvoiceSupplierReportFilters,
): TimelineGroup[] {
  const groupsMap = new Map<string, { subLabel: string | null; items: TimelineItem[] }>();

  for (const invoiceImport of invoiceImports) {
    const issues = selectedIssues(invoiceImport, filters).filter(
      (issue) => invoiceIssueFamily(issue) === "periods",
    );
    if (issues.length === 0) continue;
    const groupName =
      invoiceImport.regroupement?.trim() ||
      invoiceImport.contract_holder?.trim() ||
      "Non regroupe";
    const subLabel = invoiceImport.contract_holder?.trim() ?? null;
    const groupEntry = groupsMap.get(groupName) ?? { subLabel, items: [] };
    for (const issue of issues) {
      if (!issue.scope) continue;
      const parsed = parseScopeWithPeriod(issue.scope);
      if (!parsed) continue;
      const rowKey = parsed.prm ?? parsed.fic ?? issue.scope;
      const rowLabel = parsed.prm
        ? `PRM ${parsed.prm}`
        : parsed.fic
          ? `FIC ${parsed.fic}`
          : issue.scope;
      const rowSubLabel = parsed.prm && parsed.fic ? `FIC ${parsed.fic}` : null;
      const issueKind = issue.code === "PERIOD_OVERLAP" ? "overlap" : issue.code === "PERIOD_GAP" ? "gap" : "other";
      groupEntry.items.push({
        rowKey,
        rowLabel,
        rowSubLabel,
        startISO: parsed.startISO,
        endISO: parsed.endISO,
        isIssue: true,
        issueKind,
        tooltip: `${invoiceReference(invoiceImport)} - ${issue.code} - ${parsed.startISO} → ${parsed.endISO}`,
      });
    }
    if (groupEntry.items.length > 0) {
      groupsMap.set(groupName, groupEntry);
    }
  }

  return Array.from(groupsMap.entries())
    .map(([name, { subLabel, items }]) => ({ name, subLabel, items }))
    .sort((a, b) => a.name.localeCompare(b.name, "fr"));
}

export function InvoiceSupplierReport({ invoiceImports, filters, onClose, token }: Props) {
  const suppliers = useMemo(
    () =>
      Array.from(
        new Set(
          invoiceImports
            .map((invoiceImport) => invoiceImport.supplier_guess)
            .filter((supplier): supplier is string => Boolean(supplier)),
        ),
      ),
    [invoiceImports],
  );
  const issueGroups = useMemo(() => groupIssuesByFamily(invoiceImports, filters), [filters, invoiceImports]);
  const excludedInternalGroups = useMemo(
    () => groupIssuesByFamily(invoiceImports, filters, excludedInternalIssues),
    [filters, invoiceImports],
  );
  const reportInvoiceImports = useMemo(
    () => invoiceImports.filter((invoiceImport) => selectedIssues(invoiceImport, filters).length > 0),
    [filters, invoiceImports],
  );
  const filtersSummary = useMemo(() => activeFilters(filters), [filters]);
  const periodTimelineGroups = useMemo(
    () => buildPeriodTimelineGroups(invoiceImports, filters),
    [invoiceImports, filters],
  );
  const periodRows = useMemo(() => periodIssueRows(invoiceImports, filters), [invoiceImports, filters]);
  const periodSummary = useMemo(
    () => ({
      overlap: periodRows.filter((row) => row.kind === "overlap").length,
      gap: periodRows.filter((row) => row.kind === "gap").length,
      other: periodRows.filter((row) => row.kind === "other").length,
    }),
    [periodRows],
  );
  const totalTtc = reportInvoiceImports.reduce((total, invoiceImport) => total + (invoiceImport.total_ttc ?? 0), 0);
  const errorCount = reportInvoiceImports.reduce(
    (total, invoiceImport) =>
      total +
      selectedIssues(invoiceImport, filters).filter((issue) => issue.severity === "error").length,
    0,
  );
  const warningCount = reportInvoiceImports.reduce(
    (total, invoiceImport) =>
      total +
      selectedIssues(invoiceImport, filters).filter((issue) => issue.severity === "warning").length,
    0,
  );
  const defaultRecipient = suppliers.length === 1 ? suppliers[0] : "Fournisseur d'energie";
  const excludedInternalIssueCount = excludedInternalGroups.reduce((total, group) => total + group.count, 0);

  const [senderName, setSenderName] = useState("Collectivite");
  const [recipientName, setRecipientName] = useState(defaultRecipient);
  const [subject, setSubject] = useState("Demande d'explications sur des points de controle de factures energie");
  const [context, setContext] = useState(
    "Dans le cadre de notre revue des factures d'energie, plusieurs points ont ete identifies par nos controles. Ils sont transmis pour clarification : ils peuvent correspondre a une anomalie de facturation, a une donnee contractuelle manquante ou a une mauvaise interpretation de notre part.",
  );
  const [request, setRequest] = useState(
    "Merci de nous confirmer, pour chaque point liste ci-dessous, la regle de facturation appliquee, les donnees contractuelles ou reglementaires qui la justifient et, le cas echeant, la correction ou la piece explicative a prendre en compte.",
  );

  // ── Fetch détails des factures concernées par BPU pour récupérer mismatches_detail ──
  const bpuInvoiceImports = useMemo(
    () =>
      reportInvoiceImports.filter((invoiceImport) =>
        selectedIssues(invoiceImport, filters).some(
          (issue) => invoiceIssueFamily(issue) === "bpu",
        ),
      ),
    [filters, reportInvoiceImports],
  );
  const [detailsByImportId, setDetailsByImportId] = useState<Record<number, EnergyInvoiceImportDetail>>({});
  const [bpuLoading, setBpuLoading] = useState(false);
  const [bpuError, setBpuError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || bpuInvoiceImports.length === 0) return;
    const toFetch = bpuInvoiceImports.filter((imp) => !(imp.id in detailsByImportId));
    if (toFetch.length === 0) return;
    let cancelled = false;
    setBpuLoading(true);
    setBpuError(null);
    Promise.all(toFetch.map((imp) => fetchEnergyInvoiceImport(token, imp.id)))
      .then((details) => {
        if (cancelled) return;
        setDetailsByImportId((prev) => {
          const next = { ...prev };
          details.forEach((d) => {
            next[d.id] = d;
          });
          return next;
        });
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setBpuError(`Recalcul BPU partiel : impossible de charger ${toFetch.length} facture(s). ${err.message}`);
      })
      .finally(() => {
        if (!cancelled) setBpuLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [bpuInvoiceImports, detailsByImportId, token]);

  // Construit deux listes distinctes : écarts de prix unitaire (par ligne) et incohérences
  // tarif/poste (agrégées par groupe). Plus invitation à relancer pour les analyses obsolètes.
  const bpuView = useMemo(() => {
    type WithInvoice = { invoiceId: number; invoiceRef: string };
    const priceMismatches: Array<BpuPriceMismatch & WithInvoice> = [];
    const inconsistencies: Array<BpuTariffPosteInconsistency & WithInvoice> = [];
    const staleInvoices: Array<{ id: number; ref: string }> = [];
    for (const invoiceImport of bpuInvoiceImports) {
      const detail = detailsByImportId[invoiceImport.id];
      if (detail === undefined) continue;
      const mismatches = extractMismatchesDetail(detail);
      if (mismatches === null) {
        staleInvoices.push({ id: invoiceImport.id, ref: invoiceReference(invoiceImport) });
        continue;
      }
      const ref = invoiceReference(invoiceImport);
      for (const m of mismatches) {
        if (!shouldShowBpuMismatch(m, filters)) continue;
        // Fallback : les analyses très anciennes peuvent ne pas avoir le champ "type"
        const mtype = (m as BpuMismatchDetail).type ?? "price_mismatch";
        if (mtype === "tariff_poste_inconsistency") {
          inconsistencies.push({ ...(m as BpuTariffPosteInconsistency), invoiceId: invoiceImport.id, invoiceRef: ref });
        } else {
          priceMismatches.push({ ...(m as BpuPriceMismatch), invoiceId: invoiceImport.id, invoiceRef: ref });
        }
      }
    }
    return { priceMismatches, inconsistencies, staleInvoices };
  }, [bpuInvoiceImports, detailsByImportId, filters]);

  const bpuPriceTotalEur = useMemo(
    () => bpuView.priceMismatches.reduce((sum, d) => sum + (d.delta_total_eur_ht ?? 0), 0),
    [bpuView.priceMismatches],
  );
  const bpuInconsistencyTotalEur = useMemo(
    () => bpuView.inconsistencies.reduce((sum, d) => sum + (d.delta_total_eur_ht ?? 0), 0),
    [bpuView.inconsistencies],
  );
  const bpuTotalEstimatedEur = bpuPriceTotalEur + bpuInconsistencyTotalEur;
  const bpuPriceLinesWithoutQuantity = bpuView.priceMismatches.filter((d) => d.quantity_mwh == null).length;
  const bpuInconsistencyWithoutQuantity = bpuView.inconsistencies.filter((d) => d.delta_total_eur_ht == null).length;
  const hasBpuSection = bpuInvoiceImports.length > 0;

  return (
    <div className="invoice-report-backdrop" role="dialog" aria-modal="true" aria-label="Rapport fournisseur factures">
      <section className="invoice-report-panel">
        <header className="invoice-report-toolbar invoice-report-no-print">
          <div>
            <p className="field-label">Rapport fournisseur</p>
            <strong>{reportInvoiceImports.length} facture{reportInvoiceImports.length > 1 ? "s" : ""} avec points a clarifier</strong>
          </div>
          <div className="invoice-action-cell">
            <button type="button" className="btn-secondary btn-compact" onClick={() => window.print()}>
              Imprimer / PDF
            </button>
            <button type="button" className="btn-secondary btn-compact" onClick={onClose}>
              Fermer
            </button>
          </div>
        </header>

        <div className="invoice-report-print-area">
          <div className="invoice-report-editor invoice-report-no-print">
            <label>
              <span className="field-label">Emetteur</span>
              <input className="form-input" value={senderName} onChange={(event) => setSenderName(event.target.value)} />
            </label>
            <label>
              <span className="field-label">Destinataire</span>
              <input className="form-input" value={recipientName} onChange={(event) => setRecipientName(event.target.value)} />
            </label>
            <label className="invoice-report-editor-wide">
              <span className="field-label">Objet</span>
              <input className="form-input" value={subject} onChange={(event) => setSubject(event.target.value)} />
            </label>
            <label className="invoice-report-editor-wide">
              <span className="field-label">Contexte</span>
              <textarea className="form-input" rows={3} value={context} onChange={(event) => setContext(event.target.value)} />
            </label>
            <label className="invoice-report-editor-wide">
              <span className="field-label">Demande</span>
              <textarea className="form-input" rows={3} value={request} onChange={(event) => setRequest(event.target.value)} />
            </label>
            {excludedInternalGroups.length > 0 && (
              <aside className="invoice-report-internal-note">
                <strong>
                  {excludedInternalIssueCount} point{excludedInternalIssueCount > 1 ? "s" : ""} sans chiffrage direct
                </strong>
                <p>
                  Ces points suivent les filtres appliques mais ne produisent pas toujours un ecart financier direct :
                  reference BPU ou ENEDIS absente, controle partiel ou perimetre local incomplet.
                </p>
                <span>
                  {Array.from(new Set(excludedInternalGroups.flatMap((group) => Array.from(group.codes)))).join(", ")}
                </span>
              </aside>
            )}
            {hasBpuSection && bpuView.staleInvoices.length > 0 && (
              <aside className="invoice-report-internal-note invoice-report-warning">
                <strong>
                  {bpuView.staleInvoices.length} facture{bpuView.staleInvoices.length > 1 ? "s" : ""} sans chiffrage BPU enrichi
                </strong>
                <p>
                  Ces factures ont ete analysees avant l'ajout du detail mismatch BPU dans le moteur. Relance
                  l'analyse depuis la page detail facture pour obtenir l'estimation chiffree.
                </p>
                <span>{bpuView.staleInvoices.map((s) => s.ref).join(", ")}</span>
              </aside>
            )}
          </div>

          <article className="invoice-supplier-report">
            <header className="invoice-supplier-report-header">
              <p>{senderName || "Collectivite"}</p>
              <h1>{subject || "Rapport de revue des factures energie"}</h1>
              <div className="invoice-supplier-report-meta">
                <span>Destinataire : {recipientName || "Fournisseur d'energie"}</span>
                <span>Edition : {formatGeneratedAt()}</span>
              </div>
            </header>

            <section>
              <h2>Objet de la demande</h2>
              <p>{context}</p>
              <p>{request}</p>
            </section>

            <section>
              <h2>Perimetre retenu</h2>
              <div className="invoice-report-kpis">
                <div>
                  <strong>{reportInvoiceImports.length}</strong>
                  <span>Factures concernees</span>
                </div>
                <div>
                  <strong>{issueGroups.length}</strong>
                  <span>Categories de points</span>
                </div>
                <div>
                  <strong>{errorCount}</strong>
                  <span>Erreurs detectees</span>
                </div>
                <div>
                  <strong>{warningCount}</strong>
                  <span>Alertes detectees</span>
                </div>
                <div>
                  <strong>{formatCurrency(totalTtc)}</strong>
                  <span>TTC facture selectionne</span>
                </div>
              </div>
              <div className="invoice-report-filter-list">
                {(filtersSummary.length > 0 ? filtersSummary : ["Aucun filtre restrictif hors presence de points de controle"]).map((filter) => (
                  <span key={filter}>{filter}</span>
                ))}
              </div>
            </section>

            <section>
              <h2>Points soumis a clarification</h2>
              {issueGroups.length === 0 ? (
                <p>Aucun point de controle ne correspond aux filtres appliques.</p>
              ) : (
                <div className="invoice-report-issue-cards">
                  {issueGroups.map((group) => {
                    const scopes = uniqueIssueScopesForFamily(invoiceImports, group.family, filters);
                    const prmCount = new Set(scopes.map(extractPrm).filter(Boolean) as string[]).size;
                    return (
                      <div key={group.family} className="invoice-report-issue-card">
                        <div className="invoice-report-issue-head">
                          <strong>{INVOICE_ISSUE_FAMILY_LABEL[group.family]}</strong>
                          <div className="invoice-report-issue-counts">
                            <span>
                              <em>{group.invoiceIds.size}</em> facture{group.invoiceIds.size > 1 ? "s" : ""}
                            </span>
                            <span>
                              <em>{prmCount}</em> compteur{prmCount > 1 ? "s" : ""}
                            </span>
                            <span>
                              <em>{group.count}</em> signalement{group.count > 1 ? "s" : ""}
                            </span>
                          </div>
                        </div>
                        <p className="invoice-report-point-detail">{INVOICE_ISSUE_FAMILY_DETAIL[group.family]}</p>
                        <p className="invoice-report-issue-codes">
                          <span className="field-label">Codes de controle :</span>{" "}
                          {Array.from(group.codes).sort().join(", ")}
                        </p>
                        {scopes.length > 0 && (
                          <details className="invoice-report-scopes" open>
                            <summary>Perimetre detaille ({scopes.length} occurrence{scopes.length > 1 ? "s" : ""})</summary>
                            <ul className="invoice-report-scopes-list">
                              {scopes.map((scope) => (
                                <li key={scope}>{scope}</li>
                              ))}
                            </ul>
                          </details>
                        )}
                        {group.family === "periods" && periodTimelineGroups.length > 0 && (
                          <div className="invoice-timeline-section">
                            <h3>Visualisation des periodes facturees</h3>
                            <div className="invoice-period-summary">
                              <span><strong>{periodSummary.overlap}</strong> chevauchement{periodSummary.overlap > 1 ? "s" : ""}</span>
                              <span><strong>{periodSummary.gap}</strong> trou{periodSummary.gap > 1 ? "s" : ""}</span>
                              <span><strong>{periodSummary.other}</strong> autre{periodSummary.other > 1 ? "s" : ""} periode{periodSummary.other > 1 ? "s" : ""} a verifier</span>
                            </div>
                            <InvoicePeriodTimeline groups={periodTimelineGroups} compact labelWidth={190} />
                            {periodRows.length > 0 && (
                              <table className="invoice-period-issues-table">
                                <thead>
                                  <tr>
                                    <th>Facture</th>
                                    <th>Probleme</th>
                                    <th>Periode / compteur</th>
                                    <th>A lire</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {periodRows.slice(0, 16).map((row) => (
                                    <tr key={`${row.invoiceRef}-${row.code}-${row.scope}`}>
                                      <td>{row.invoiceRef}</td>
                                      <td>{row.code}</td>
                                      <td>{row.scope}</td>
                                      <td>{periodIssueKindLabel(row.kind)}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {hasBpuSection && (
              <section>
                <h2>Estimation impact des ecarts BPU</h2>
                <p className="invoice-report-point-detail">
                  Deux types d'ecarts sont chiffres par le moteur d'analyse : les ecarts de prix unitaire (le prix
                  facture differe du prix BPU attendu pour le meme couple tarif/poste) et les incoherences
                  tarif/poste (la facture applique les bons prix mais sur les mauvais postes, ce qui change la
                  facturation totale par rapport au couple contractuel). Le total cumule represente l'impact
                  financier estime sur le perimetre retenu.
                </p>
                {bpuLoading && <p>Chargement des details factures...</p>}
                {bpuError && <p className="invoice-report-warning">{bpuError}</p>}
                {!bpuLoading &&
                  bpuView.priceMismatches.length === 0 &&
                  bpuView.inconsistencies.length === 0 &&
                  bpuView.staleInvoices.length === 0 && (
                    <p>
                      Aucun ecart BPU chiffrable ligne par ligne sur les factures retenues. Les points BPU non
                      chiffrables restent listes dans la section des points soumis a clarification.
                    </p>
                  )}
                {bpuView.staleInvoices.length > 0 && (
                  <p className="invoice-report-warning">
                    {bpuView.staleInvoices.length} facture{bpuView.staleInvoices.length > 1 ? "s" : ""} sans
                    chiffrage disponible : analyse anterieure a l'enrichissement (relancer l'analyse pour obtenir
                    le detail).
                  </p>
                )}

                {bpuView.priceMismatches.length > 0 && (
                  <>
                    <h3 className="invoice-report-subsection">Ecarts de prix unitaire ({bpuView.priceMismatches.length})</h3>
                    <table className="invoice-report-bpu-table">
                      <thead>
                        <tr>
                          <th>Facture / PRM</th>
                          <th>Ligne facturee</th>
                          <th>Reference BPU</th>
                          <th>Prix facture</th>
                          <th>Prix BPU</th>
                          <th>Delta</th>
                          <th>Quantite</th>
                          <th>Ecart estime HT</th>
                        </tr>
                      </thead>
                      <tbody>
                        {bpuView.priceMismatches.map((d, idx) => (
                          <tr key={`pm-${d.invoiceId}-${d.line_index}-${idx}`}>
                            <td>
                              <strong>{d.invoiceRef}</strong>
                              <span>{d.site_prm_id ?? d.scope ?? "-"}</span>
                            </td>
                            <td>
                              <strong>{d.line_label || d.line_normalized_component || `Ligne #${d.line_index}`}</strong>
                              <span>
                                {d.line_poste ? `Poste ${d.line_poste}` : null}
                                {d.line_normalized_component && d.line_poste ? " — " : null}
                                {d.line_normalized_component ?? null}
                              </span>
                            </td>
                            <td>
                              <strong>{d.bpu_reference}</strong>
                              <span>{d.source === "historical" ? "BPU historique" : "BPU configure"}</span>
                            </td>
                            <td>{d.invoice_price_eur_mwh.toFixed(2)} EUR/MWh</td>
                            <td>{d.bpu_price_eur_mwh.toFixed(2)} EUR/MWh</td>
                            <td className={d.delta_eur_mwh > 0 ? "invoice-report-delta-over" : "invoice-report-delta-under"}>
                              {d.delta_eur_mwh > 0 ? "+" : ""}
                              {d.delta_eur_mwh.toFixed(2)} EUR/MWh
                            </td>
                            <td>
                              {d.quantity_mwh != null
                                ? `${d.quantity_mwh.toFixed(3)} MWh`
                                : d.quantity != null && d.quantity_unit
                                  ? `${d.quantity} ${d.quantity_unit} (non convertie)`
                                  : "non renseignee"}
                            </td>
                            <td
                              className={
                                d.delta_total_eur_ht != null && d.delta_total_eur_ht > 0
                                  ? "invoice-report-delta-over"
                                  : "invoice-report-delta-under"
                              }
                            >
                              {d.delta_total_eur_ht != null ? formatCurrency(d.delta_total_eur_ht) : "-"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr>
                          <td colSpan={7}>
                            <strong>Sous-total ecarts de prix</strong>
                            {bpuPriceLinesWithoutQuantity > 0 && (
                              <span>
                                {" "}({bpuPriceLinesWithoutQuantity} ligne{bpuPriceLinesWithoutQuantity > 1 ? "s" : ""} sans quantite convertible)
                              </span>
                            )}
                          </td>
                          <td className={bpuPriceTotalEur > 0 ? "invoice-report-delta-over" : "invoice-report-delta-under"}>
                            <strong>{formatCurrency(bpuPriceTotalEur)}</strong>
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </>
                )}

                {bpuView.inconsistencies.length > 0 && (
                  <>
                    <h3 className="invoice-report-subsection">
                      Incoherences tarif / poste ({bpuView.inconsistencies.length})
                    </h3>
                    <p className="invoice-report-point-detail">
                      Pour chaque groupe : la facture applique des postes (HCH, HPH...) cumules avec leurs prix
                      respectifs, alors que le BPU contractuel attendrait le couple tarif / poste indique. Le
                      delta est la difference entre le total facture et ce que la collectivite aurait paye au
                      couple BPU attendu.
                    </p>
                    <table className="invoice-report-bpu-table">
                      <thead>
                        <tr>
                          <th>Facture / PRM</th>
                          <th>BPU attendu</th>
                          <th>Postes facture</th>
                          <th>Quantite totale</th>
                          <th>Total facture HT</th>
                          <th>Si BPU attendu</th>
                          <th>Ecart estime HT</th>
                        </tr>
                      </thead>
                      <tbody>
                        {bpuView.inconsistencies.map((d, idx) => (
                          <tr key={`ti-${d.invoiceId}-${idx}`}>
                            <td>
                              <strong>{d.invoiceRef}</strong>
                              <span>{d.site_prm_id ?? d.scope ?? "-"}</span>
                            </td>
                            <td>
                              <strong>{d.expected_bpu_reference}</strong>
                              <span>{d.expected_bpu_price_eur_mwh.toFixed(2)} EUR/MWh</span>
                            </td>
                            <td>
                              <strong>{d.invoice_postes_used.join(", ") || "-"}</strong>
                              <span>
                                {d.matching_bpu_lines.length > 0
                                  ? `Prix coh. avec ${d.matching_bpu_lines.join(", ")}`
                                  : null}
                              </span>
                            </td>
                            <td>{d.total_quantity_mwh != null ? `${d.total_quantity_mwh.toFixed(3)} MWh` : "n.c."}</td>
                            <td>{formatCurrency(d.total_amount_invoice_ht)}</td>
                            <td>
                              {d.total_amount_if_expected_ht != null
                                ? formatCurrency(d.total_amount_if_expected_ht)
                                : "n.c."}
                            </td>
                            <td
                              className={
                                d.delta_total_eur_ht != null && d.delta_total_eur_ht > 0
                                  ? "invoice-report-delta-over"
                                  : "invoice-report-delta-under"
                              }
                            >
                              {d.delta_total_eur_ht != null ? formatCurrency(d.delta_total_eur_ht) : "n.c."}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr>
                          <td colSpan={6}>
                            <strong>Sous-total incoherences tarif / poste</strong>
                            {bpuInconsistencyWithoutQuantity > 0 && (
                              <span>
                                {" "}({bpuInconsistencyWithoutQuantity} groupe{bpuInconsistencyWithoutQuantity > 1 ? "s" : ""} sans chiffrage)
                              </span>
                            )}
                          </td>
                          <td
                            className={
                              bpuInconsistencyTotalEur > 0
                                ? "invoice-report-delta-over"
                                : "invoice-report-delta-under"
                            }
                          >
                            <strong>{formatCurrency(bpuInconsistencyTotalEur)}</strong>
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </>
                )}

                {(bpuView.priceMismatches.length > 0 || bpuView.inconsistencies.length > 0) && (
                  <p className="invoice-report-bpu-grand-total">
                    <strong>Total ecart estime HT cumule :</strong>{" "}
                    <span
                      className={
                        bpuTotalEstimatedEur > 0 ? "invoice-report-delta-over" : "invoice-report-delta-under"
                      }
                    >
                      {formatCurrency(bpuTotalEstimatedEur)}
                    </span>
                  </p>
                )}
              </section>
            )}

            <section>
              <h2>Factures concernees</h2>
              <table>
                <thead>
                  <tr>
                    <th>Facture</th>
                    <th>Periode</th>
                    <th>Titulaire / Regroupement</th>
                    <th>PRM impactes</th>
                    <th>Categories</th>
                  </tr>
                </thead>
                <tbody>
                  {reportInvoiceImports.map((invoiceImport) => {
                    const prms = prmListForInvoice(invoiceImport, filters);
                    const families = familiesForInvoice(invoiceImport, filters);
                    return (
                      <tr key={invoiceImport.id}>
                        <td>
                          <strong>{invoiceReference(invoiceImport)}</strong>
                          <span>{formatShortDate(invoiceImport.invoice_date)}</span>
                        </td>
                        <td>
                          {formatShortDate(invoiceImport.period_start)} au {formatShortDate(invoiceImport.period_end)}
                        </td>
                        <td>
                          <strong>{invoiceImport.contract_holder ?? "-"}</strong>
                          <span>{invoiceImport.regroupement ?? "-"}</span>
                        </td>
                        <td>
                          {prms.length === 0 ? (
                            <span>-</span>
                          ) : (
                            <ul className="invoice-report-prm-list">
                              {prms.map((prm) => (
                                <li key={prm}>{prm}</li>
                              ))}
                            </ul>
                          )}
                        </td>
                        <td>
                          {families.map((family) => INVOICE_ISSUE_FAMILY_LABEL[family]).join(", ")}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </section>

            <footer>
              Ce rapport rassemble des points de controle a expliquer. Il ne vaut pas, a lui seul, constat definitif
              d'erreur de facturation sans retour fournisseur et verification des pieces contractuelles associees.
              {hasBpuSection && (
                <>
                  {" "}
                  Les ecarts BPU chiffres sont produits par le moteur d'analyse (rattachement ligne/BPU exact) et
                  doivent etre rapproches des pieces contractuelles applicables a la periode (lots BPU, options
                  tarifaires, dates d'effet).
                </>
              )}
            </footer>
          </article>
        </div>
      </section>
    </div>
  );
}
