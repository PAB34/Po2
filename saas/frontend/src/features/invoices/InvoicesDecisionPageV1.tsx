import { useMemo, useState, type ChangeEvent } from "react";
import { Button, Drawer, StatusBadge } from "../../design-system";
import { useCpeFinanceQueueV1, useCpeInvoiceDetailV1, useCpeInvoiceActionsV1, useSupplierContactsV1 } from "./useCpeFinanceQueueV1";
import type { CpeFinanceControl, CpeFinanceControlReport, CpeFinanceLine, EnergyInvoiceImport, SupplierContact, SupplierContactInput } from "../../lib/api";

type CpeQueueInvoice = CpeFinanceControlReport["invoices"][number];
type UnifiedStatus = "todo" | "valid" | "refused" | "disputed";
type UnifiedRow = {
  key: string;
  source: "cpe" | "energy";
  rowId: number;
  invoiceNumber: string;
  supplier: string;
  type: string;
  client: string;
  marche: string;
  perimetre: string;
  total: number;
  ok: number;
  error: number;
  anomaly: number;
  explained: number;
  info: number;
  blocked: number;
  status: UnifiedStatus;
  processed: boolean;
  month: number | null;
  year: number | null;
  periodStart: string | null;
  periodEnd: string | null;
  issues: { severity: string; code: string; message: string; scope: string | null }[];
};

/** Regroupe des anomalies par message et compte les occurrences. */
function aggregateIssues(issues: { severity: string; message: string; code: string }[]) {
  const map = new Map<string, { message: string; severity: string; code: string; count: number }>();
  for (const it of issues) {
    const key = (it.message || it.code || "Anomalie").trim();
    const cur = map.get(key);
    if (cur) cur.count += 1;
    else map.set(key, { message: key, severity: it.severity || "warning", code: it.code, count: 1 });
  }
  return Array.from(map.values()).sort((a, b) => b.count - a.count);
}

function issueTone(severity: string) {
  if (severity === "error" || severity === "blocking") return "bad" as const;
  return "warn" as const;
}

/** Codes énergie « non contrôlables » : référence/donnée manquante côté plateforme
 *  ou rapprochement à une donnée externe (ENEDIS, PRM, BPU), pas une anomalie de
 *  facturation. Comptés en « Bloqués », pas en « Écarts ».
 *  Les vrais écarts restent HORS de ce set : BPU_PRICE_MISMATCH,
 *  BPU_TARIFF_POSTE_INCONSISTENCY, TOTAL_TTC_MISMATCH, LINE_AMOUNT_MISMATCH,
 *  VAT_*, HT_TOTAL_MISMATCH, PERIOD_INVALID, DUPLICATE_INVOICE_NUMBER,
 *  SUPPLIER_UNKNOWN, NO_SITE_FOUND, MISSING_INVOICE_NUMBER, MISSING_TOTAL_TTC. */
const NON_CONTROLABLE_CODES = new Set([
  // Identité / périmètre : donnée absente ou PRM hors référentiel (typique EDF)
  "MISSING_INVOICE_DATE",
  "MISSING_MARKET_REFERENCE", "MARKET_REFERENCE_MISMATCH",
  "MISSING_PRM", "UNKNOWN_PRM", "SUPPLIER_CONTRACT_MISMATCH",
  // BPU : prix de référence absent (l'écart de prix réel reste contrôlé séparément)
  "BPU_CONFIG_MISSING", "BPU_LINES_MISSING",
  "BPU_REFERENCE_MISSING", "BPU_PRICE_MISSING", "BPU_FIXED_CHARGE_MISMATCH",
  // Taxes : totaux incomplets (les écarts TVA/HT chiffrés restent en écart)
  "TAX_TOTALS_MISSING",
  // Périodes : continuité / historique (PERIOD_INVALID = fin avant début reste un écart)
  "PERIOD_MISSING", 
  // Consommation : rapprochement ENEDIS / courbe de charge (donnée externe)
  "ENEDIS_CONSUMPTION_MISSING", "CONSUMPTION_REFERENCE_MISSING",
    "LOAD_CURVE_CONSUMPTION_PARTIAL", "ENEDIS_CONSUMPTION_PARTIAL",
  // Puissance : rapprochement ENEDIS / courbe de charge (donnée externe)
  "POWER_REFERENCE_MISSING", "SUBSCRIBED_POWER_MISSING", "SUBSCRIBED_POWER_CONTRACT_MISMATCH",
  "POWER_OVERRUN", "POWER_LOAD_CURVE_MISMATCH", "POWER_LOAD_CURVE_OVERRUN",
  "LOAD_CURVE_POWER_PARTIAL", "POWER_ENEDIS_MISMATCH", "POWER_ENEDIS_OVERRUN", "ENEDIS_POWER_MISSING",
]);
function isNonControlable(code: string) {
  return NON_CONTROLABLE_CODES.has(code);
}

const ANOMALY_CODES = new Set([
  "PERIOD_GAP", "PERIOD_OVERLAP", "DOUBLE_BILLING_PERIOD",
  "POWER_OVERRUN_BILLED",
]);
const EXPLAINED_CODES = new Set(["PERIOD_OVERLAP_EXPLAINED"]);
/** Codes « informatifs » : visibles pour information mais jamais bloquants et sans
 *  impact sur la décision (écart conso vs ENEDIS/courbe de charge, regroupement absent). */
const INFORMATIVE_CODES = new Set([
  "CONSUMPTION_ENEDIS_MISMATCH", "CONSUMPTION_LOAD_CURVE_MISMATCH", "MISSING_REGROUPEMENT",
]);
function isInformativeIssue(issue: { severity: string; code: string }) {
  return issue.severity === "info" || INFORMATIVE_CODES.has(issue.code);
}

/** Libellés courts par type de problème, pour le filtre « par typologie ». */
const PROBLEM_TYPE_LABELS: Record<string, string> = {
  CONSUMPTION_ENEDIS_MISMATCH: "Écart conso ENEDIS",
  CONSUMPTION_LOAD_CURVE_MISMATCH: "Écart conso courbe de charge",
  MISSING_REGROUPEMENT: "Regroupement absent",
  DOUBLE_BILLING_PERIOD: "Double facturation",
  PERIOD_GAP: "Trou de facturation",
  PERIOD_OVERLAP: "Chevauchement de période",
  PERIOD_INVALID: "Période incohérente",
  DUPLICATE_EXPORT_OR_REISSUE: "Doublon export / réédition",
  DUPLICATE_INVOICE_NUMBER: "Numéro de facture en doublon",
  FIXED_CHARGE_PERIOD_NOT_APPLICABLE: "Ligne fixe sans conso",
  SUPPLIER_SWITCH_GAP_EXPLAINED: "Transition fournisseur",
  PERIOD_OVERLAP_EXPLAINED: "Chevauchement expliqué",
  BPU_PRICE_MISMATCH: "Écart prix BPU",
  BPU_TARIFF_POSTE_INCONSISTENCY: "Incohérence poste/tarif BPU",
  TOTAL_TTC_MISMATCH: "Écart total TTC",
  LINE_AMOUNT_MISMATCH: "Écart montant de ligne",
  HT_TOTAL_MISMATCH: "Écart total HT",
  SUPPLIER_UNKNOWN: "Fournisseur inconnu",
  NO_SITE_FOUND: "Aucun point de livraison",
  UNKNOWN_PRM: "PRM hors référentiel",
  SUPPLIER_CONTRACT_MISMATCH: "PRM rattaché à un autre fournisseur",
};
function problemTypeLabel(code: string) {
  return PROBLEM_TYPE_LABELS[code] ?? code.replace(/_/g, " ").toLowerCase();
}
/** Codes masqués sur la page Factures : le contrôle reste calculé côté backend
 *  (réutilisable plus tard dans la section Fluides) mais n'est pas affiché ni
 *  compté ici. Dépassement de puissance = pénalité réelle, pas un contrôle de
 *  facturation à trancher par la comptable. */
const HIDDEN_ENERGY_CODES = new Set(["POWER_OVERRUN_BILLED"]);
function isHiddenIssue(issue: { code: string }) {
  return HIDDEN_ENERGY_CODES.has(issue.code);
}
function isAnomalyIssue(issue: { severity: string; code: string }) {
  return issue.severity === "anomaly" || ANOMALY_CODES.has(issue.code);
}
function isExplainedIssue(issue: { severity: string; code: string }) {
  return issue.severity === "explained" || EXPLAINED_CODES.has(issue.code);
}

// ---------------------------------------------------------------------------
// Statuts unifiés (CPE et énergie ont des codes différents)
// ---------------------------------------------------------------------------
const UNIFIED_OPTIONS: { value: UnifiedStatus; label: string }[] = [
  { value: "todo", label: "À contrôler" },
  { value: "valid", label: "Validée" },
  { value: "refused", label: "Refusée" },
  { value: "disputed", label: "Contestée" },
];
const CPE_TO_UNIFIED: Record<string, UnifiedStatus> = { a_controler: "todo", valide: "valid", refuse: "refused", conteste: "disputed" };
const UNIFIED_TO_CPE: Record<UnifiedStatus, string> = { todo: "a_controler", valid: "valide", refused: "refuse", disputed: "conteste" };
const ENERGY_TO_UNIFIED: Record<string, UnifiedStatus> = { to_review: "todo", approved: "valid", rejected: "refused", dispute_sent: "disputed" };
const UNIFIED_TO_ENERGY: Record<UnifiedStatus, "to_review" | "approved" | "rejected" | "dispute_sent"> = { todo: "to_review", valid: "approved", refused: "rejected", disputed: "dispute_sent" };

const CONTROL_TYPE_LABELS: Record<string, string> = {
  coherence: "Cohérence", fourniture: "Fourniture", acheminement: "Acheminement", taxes: "Taxes",
  p1: "P1 gaz", p1_quantite: "P1 quantité", p1_prix: "P1 prix", revision: "Révision",
  documentaire: "Documentaire", comptable: "Comptable", echeance: "Échéance",
};
function controlTypeLabel(type: string) { return CONTROL_TYPE_LABELS[type] ?? type.replace(/_/g, " "); }

/** Court message d'explication par type d'écart (CPE control_type + codes énergie). */
const ECART_EXPLAIN: Record<string, string> = {
  // CPE / DALKIA
  invoice_total_ht: "Le total de la facture ne correspond pas à la somme de ses lignes.",
  invoice_period: "La période facturée est incohérente (fin avant début).",
  invoice_timeline: "Les dates d'édition / échéance sont incohérentes avec la période.",
  p1_gaz_pu_os3: "Le prix unitaire P1 gaz diffère du prix OS N°3 attendu.",
  p1_gaz_acompte_dpgf: "L'acompte P1 gaz ne correspond pas au DPGF de référence.",
  p2p3_base_dpgf: "Le montant P2/P3 s'écarte de l'enveloppe contractuelle DPGF.",
  revision_p2: "L'indice de révision P2 ne correspond pas aux indices validés.",
  revision_p3: "L'indice de révision P3 ne correspond pas aux indices validés.",
  p2_4_objectives: "L'intéressement P2.4 ne respecte pas les objectifs contractuels.",
  invoice_type: "Type de facture absent : impossible de qualifier acompte / avoir / régularisation.",
  accounting_nature: "Aucune règle de matrice ne couvre cette ligne : imputation comptable impossible.",
  accounting_site: "Le site détecté n'est pas rattaché à la matrice de codification.",
  // Énergie (codes)
  SUPPLIER_UNKNOWN: "Le fournisseur de la facture n'est pas reconnu par le moteur de contrôle.",
  MISSING_INVOICE_NUMBER: "Numéro de facture absent.",
  MISSING_INVOICE_DATE: "Date de facture absente.",
  MISSING_TOTAL_TTC: "Montant TTC global absent.",
  MISSING_REGROUPEMENT: "Le regroupement (compte / CCC) est absent.",
  MISSING_MARKET_REFERENCE: "Référence de marché absente.",
  MARKET_REFERENCE_MISMATCH: "La référence de marché ne correspond pas au marché en cours.",
  DUPLICATE_INVOICE_NUMBER: "Ce numéro de facture a déjà été importé (doublon).",
  NO_SITE_FOUND: "Aucun point de livraison (PRM / PCE) détecté dans la facture.",
  MISSING_PRM: "Le point de livraison (PRM) est absent sur un site.",
  UNKNOWN_PRM: "Le PRM facturé est inconnu du référentiel énergie (normal hors périmètre ENEDIS chargé).",
  SUPPLIER_CONTRACT_MISMATCH: "Le PRM est rattaché à un autre fournisseur dans le référentiel ENEDIS.",
  BPU_REFERENCE_MISSING: "Aucune ligne de bordereau (BPU) ne correspond au tarif/poste facturé.",
  BPU_PRICE_MISSING: "Ligne BPU trouvée mais prix de référence non renseigné.",
  BPU_FIXED_CHARGE_MISMATCH: "Frais fixe facturé différent du BPU (contrôle indicatif).",
  PERIOD_GAP: "Trou de facturation avec la période précédente (information d'historique).",
  PERIOD_OVERLAP: "Chevauchement avec une période déjà facturée (information d'historique).",
  PERIOD_INVALID: "La période facturée est incohérente (fin avant début).",
  PERIOD_MISSING: "Période facturée incomplète : contrôle de fréquence impossible.",
  BPU_CONFIG_MISSING: "Aucun bordereau (BPU) configuré pour ce fournisseur : prix non contrôlables.",
  BPU_LINES_MISSING: "Bordereau présent mais sans ligne exploitable.",
  ENEDIS_CONSUMPTION_MISSING: "Données ENEDIS absentes sur la période : consommation non comparable.",
  CONSUMPTION_REFERENCE_MISSING: "Consommation ou période incomplète : contrôle impossible.",
  POWER_REFERENCE_MISSING: "Référence de puissance absente : contrôle impossible.",
  SUBSCRIBED_POWER_MISSING: "Puissance souscrite absente de la facture.",
  TAX_TOTALS_MISSING: "Totaux HT / TVA / TTC incomplets : contrôle des taxes impossible.",
};
function explainEcart(code: string | undefined) {
  if (code && ECART_EXPLAIN[code]) return ECART_EXPLAIN[code];
  if (code && isNonControlable(code)) return "Donnée de référence absente ou rapprochement externe indisponible : non contrôlable.";
  return "Écart à examiner avec le fournisseur.";
}
/** Libellé métier d'un phénomène expliqué (neutralisé), par code moteur. */
const EXPLAINED_LABELS: Record<string, string> = {
  DUPLICATE_EXPORT_OR_REISSUE: "Doublon exact détecté : réédition / export fournisseur, sans impact de période.",
  SUPPLIER_SWITCH_GAP_EXPLAINED: "Transition fournisseur : trou apparent (EDF → ENGIE), sans manque de facturation.",
  FIXED_CHARGE_PERIOD_NOT_APPLICABLE: "Ligne fixe sans consommation : contrôle de période non applicable.",
  PERIOD_OVERLAP_EXPLAINED: "Chevauchement expliqué par avoir, annulation ou refacturation.",
};
function explainExplained(code: string | undefined) {
  if (code && EXPLAINED_LABELS[code]) return EXPLAINED_LABELS[code];
  return "Régularisation expliquée par avoir, annulation ou refacturation.";
}
/** Construit un brouillon d'e-mail de réclamation à partir des points à signaler. */
function buildClaimDraft(
  row: UnifiedRow,
  contact: SupplierContact | undefined,
  points: string[],
): { to: string; subject: string; body: string } {
  const periode = fmtPeriod(row.periodStart, row.periodEnd);
  const greeting = contact?.contact_name ? `Bonjour ${contact.contact_name},` : "Bonjour,";
  const lines = points.length
    ? points.map((p) => `- ${p}`).join("\n")
    : "- (préciser le motif de la réclamation)";
  const body = [
    greeting,
    "",
    `Nous revenons vers vous au sujet de la facture ${row.invoiceNumber} (${row.supplier}` +
      `${periode ? `, période ${periode}` : ""}, montant ${fmtEur(row.total)}).`,
    "",
    "Points à clarifier :",
    lines,
    "",
    "Pourriez-vous nous apporter les éléments correspondants ou procéder à la régularisation ?",
    "",
    "Cordialement,",
  ].join("\n");
  return {
    to: contact?.email ?? "",
    subject: `Réclamation facture ${row.invoiceNumber} — ${row.supplier}`,
    body,
  };
}
function statusLabel(s: UnifiedStatus) { return UNIFIED_OPTIONS.find((o) => o.value === s)?.label ?? s; }
function statusTone(s: UnifiedStatus) { return s === "valid" ? ("ok" as const) : s === "todo" ? ("warn" as const) : ("bad" as const); }
function fmtEur(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value);
}
function parseMonth(date: string | null | undefined): number | null {
  if (!date) return null;
  const m = date.includes("/") ? Number(date.split("/")[1]) - 1 : Number(date.slice(5, 7)) - 1;
  return m >= 0 && m < 12 ? m : null;
}
function parseYear(date: string | null | undefined): number | null {
  if (!date) return null;
  const y = date.includes("/") ? Number(date.split("/")[2]) : Number(date.slice(0, 4));
  return Number.isFinite(y) && y > 1990 ? y : null;
}
/** Période facturée en mois numériques : « 03/2026 » (ou « 10/2025 → 12/2025 »). */
function fmtMonthYear(month: number, year: number): string {
  return `${String(month + 1).padStart(2, "0")}/${year}`;
}
function fmtPeriod(start: string | null, end: string | null): string | null {
  const ms = parseMonth(start), me = parseMonth(end), ys = parseYear(start), ye = parseYear(end);
  if (ms === null || me === null || ye === null) return null;
  if (ms === me && ys === ye) return fmtMonthYear(ms, ye);
  return `${fmtMonthYear(ms, ys ?? ye)} → ${fmtMonthYear(me, ye)}`;
}
function supplierFromEnergy(inv: EnergyInvoiceImport) {
  return inv.supplier_guess || (inv.source?.toUpperCase().includes("EDF") ? "EDF" : inv.source?.toUpperCase().includes("ENGIE") ? "ENGIE" : "Énergie");
}

const MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"];

// Répartition « état dominant » d'une facture (segments mutuellement exclusifs,
// par priorité décroissante) pour la barre de synthèse du header.
const BAR_SEGMENTS: { key: keyof Distribution; label: string; color: string }[] = [
  { key: "blocked", label: "Bloquées", color: "#b91c1c" },
  { key: "explain", label: "À expliquer", color: "#b45309" },
  { key: "ecart", label: "Écarts", color: "#d9a13a" },
  { key: "explained", label: "Expliquées", color: "#7fb3a8" },
  { key: "info", label: "Informatif", color: "#5b8def" },
  { key: "ok", label: "Sans écart", color: "#74b44a" },
];
type Distribution = { ok: number; explained: number; info: number; ecart: number; explain: number; blocked: number };

const CONTROL_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: "all", label: "Tous les contrôles" },
  { value: "todo", label: "À traiter" },
  { value: "done", label: "Traitées" },
  { value: "ecart", label: "Écarts" },
  { value: "explain", label: "À expliquer" },
  { value: "blocked", label: "Bloquées" },
  { value: "explained", label: "Expliquées" },
  { value: "info", label: "Informatif" },
];
function matchesControl(r: UnifiedRow, f: string) {
  switch (f) {
    case "todo": return !r.processed;
    case "done": return r.processed;
    case "ecart": return r.error > 0;
    case "explain": return r.anomaly > 0;
    case "blocked": return r.blocked > 0;
    case "explained": return r.explained > 0;
    case "info": return r.info > 0;
    default: return true;
  }
}

// Colonnes triables : chaque clé correspond à un champ direct de UnifiedRow.
type SortKey = "invoiceNumber" | "supplier" | "type" | "client" | "marche" | "perimetre"
  | "total" | "ok" | "error" | "anomaly" | "explained" | "info" | "blocked" | "status";
const COLUMNS: { key: SortKey; label: string; align?: "right"; title?: string }[] = [
  { key: "invoiceNumber", label: "Facture" },
  { key: "supplier", label: "Fournisseur" },
  { key: "type", label: "Type" },
  { key: "client", label: "Client" },
  { key: "marche", label: "Marché" },
  { key: "perimetre", label: "Périmètre" },
  { key: "total", label: "Montant", align: "right" },
  { key: "ok", label: "OK", align: "right", title: "Contrôles conformes (moteur DALKIA uniquement)" },
  { key: "error", label: "Écarts", align: "right", title: "Écarts réels de facturation" },
  { key: "anomaly", label: "À expliquer", align: "right", title: "Anomalies non résolues à expliquer au fournisseur" },
  { key: "explained", label: "Expliquées", align: "right", title: "Anomalies neutralisées (avoir, doublon exact, transition fournisseur, ligne fixe)" },
  { key: "info", label: "Informatif", align: "right", title: "Informations non bloquantes (écart conso ENEDIS, regroupement absent)" },
  { key: "blocked", label: "Bloquées", align: "right", title: "Non contrôlable : référence ou donnée manquante" },
  { key: "status", label: "Décision" },
];

export function InvoicesDecisionPageV1() {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [controlFilter, setControlFilter] = useState("all");
  const [problemFilter, setProblemFilter] = useState("all");
  const [supplierFilter, setSupplierFilter] = useState("all");
  const [yearFilter, setYearFilter] = useState<number | null>(null);
  const [monthFilter, setMonthFilter] = useState<number | null>(null);
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 } | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [contactsOpen, setContactsOpen] = useState(false);
  const [claimOpen, setClaimOpen] = useState(false);
  const { report, invoices, energy } = useCpeFinanceQueueV1();
  const { contacts } = useSupplierContactsV1();
  const actions = useCpeInvoiceActionsV1();

  // Date d'émission + période des factures CPE (le rapport de contrôle ne les porte pas)
  const cpeInfoById = useMemo(() => {
    const map = new Map<number, { month: number | null; year: number | null; periodStart: string | null; periodEnd: string | null }>();
    for (const inv of invoices.data ?? [])
      map.set(inv.id, { month: parseMonth(inv.invoice_date), year: parseYear(inv.invoice_date), periodStart: inv.period_start, periodEnd: inv.period_end });
    return map;
  }, [invoices.data]);

  const rows: UnifiedRow[] = useMemo(() => {
    const out: UnifiedRow[] = [];
    for (const r of report.data?.invoices ?? []) {
      const info = cpeInfoById.get(r.invoice_id);
      out.push({
        key: `cpe:${r.invoice_id}`, source: "cpe", rowId: r.invoice_id,
        invoiceNumber: r.invoice_number, supplier: "DALKIA",
        type: r.invoice_type ?? "—", client: r.recipient_ref ?? "—",
        marche: r.contract_code ?? r.contract_label ?? "—", perimetre: r.market ?? "—",
        total: r.total_ht, ok: r.ok, error: r.error, anomaly: 0, explained: 0, info: 0, blocked: r.blocked,
        status: CPE_TO_UNIFIED[r.invoice_status] ?? "todo",
        processed: r.invoice_status === "valide" || Boolean(r.finance_exported_at),
        month: info?.month ?? null, year: info?.year ?? null,
        periodStart: info?.periodStart ?? null, periodEnd: info?.periodEnd ?? null,
        issues: [],
      });
    }
    for (const e of energy.data ?? []) {
      const status = ENERGY_TO_UNIFIED[e.decision_status] ?? "todo";
      const sites = e.site_count ? ` · ${e.site_count} site(s)` : "";
      const docType = e.filter_facets?.document_types?.[0];
      const energyIssues = (e.control_issues ?? []).filter((i) => !isHiddenIssue(i));
      const infoCount = energyIssues.filter((i) => isInformativeIssue(i)).length;
      const explained = energyIssues.filter((i) => isExplainedIssue(i) && !isInformativeIssue(i)).length;
      const anomalies = energyIssues.filter((i) => isAnomalyIssue(i) && !isInformativeIssue(i)).length;
      const nonControlable = energyIssues.filter((i) => isNonControlable(i.code) && !isInformativeIssue(i) && !isAnomalyIssue(i) && !isExplainedIssue(i)).length;
      const realErrors = energyIssues.filter((i) => (i.severity === "error" || i.severity === "blocking") && !isInformativeIssue(i) && !isNonControlable(i.code) && !isAnomalyIssue(i) && !isExplainedIssue(i)).length;
      out.push({
        key: `energy:${e.id}`, source: "energy", rowId: e.id,
        invoiceNumber: e.invoice_number ?? `import-${e.id}`, supplier: supplierFromEnergy(e),
        type: docType ? (docType.toLowerCase().includes("avoir") ? "Avoir" : "Facture") : "Facture",
        client: e.contract_holder ?? "—",
        marche: "Hérault Énergie",
        perimetre: (e.regroupement ?? "Portefeuille") + sites,
        total: e.total_ht ?? e.total_ttc ?? 0, ok: 0, error: realErrors, anomaly: anomalies, explained, info: infoCount, blocked: nonControlable,
        status, processed: status === "valid",
        month: parseMonth(e.invoice_date), year: parseYear(e.invoice_date),
        periodStart: e.period_start, periodEnd: e.period_end,
        issues: energyIssues,
      });
    }
    // Dédoublonnage : un même n° de facture (réimport du même fichier) ne doit
    // apparaître qu'une fois par fournisseur. On garde la 1re occurrence.
    const seen = new Set<string>();
    return out.filter((r) => {
      const k = `${r.source}:${r.invoiceNumber}`;
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });
  }, [report.data, energy.data, cpeInfoById]);

  const selected = rows.find((r) => r.key === selectedKey) ?? null;
  const detail = useCpeInvoiceDetailV1(selected?.source === "cpe" ? selected.rowId : null);

  // Points à signaler dans une réclamation : écarts + anomalies non expliquées.
  const claimPoints = useMemo(() => {
    if (!selected) return [] as string[];
    const issues = selected.source === "cpe"
      ? (detail.controls.data ?? [])
          .filter((c) => c.status === "error")
          .map((c) => ({ severity: "error", message: c.message || controlTypeLabel(c.control_type), code: c.control_type }))
      : selected.issues.filter((i) => !isInformativeIssue(i) && (isAnomalyIssue(i) || (!isNonControlable(i.code) && !isExplainedIssue(i))));
    return aggregateIssues(issues).map((i) => (i.count > 1 ? `${i.message} (${i.count}×)` : i.message));
  }, [selected, detail.controls.data]);

  const suppliers = useMemo(() => Array.from(new Set(rows.map((r) => r.supplier))).sort(), [rows]);
  const editableSuppliers = useMemo(
    () => Array.from(new Set([...rows.map((r) => r.supplier), "DALKIA", "ENGIE", "EDF"])).sort(),
    [rows],
  );
  const contactBySupplier = useMemo(() => {
    const m = new Map<string, SupplierContact>();
    for (const c of contacts.data ?? []) m.set(c.supplier, c);
    return m;
  }, [contacts.data]);

  // Années d'émission disponibles (la plus récente par défaut) — évite de mélanger
  // les années dans le graphe et le filtre par mois.
  const availableYears = useMemo(
    () => Array.from(new Set(rows.map((r) => r.year).filter((y): y is number => y !== null))).sort((a, b) => b - a),
    [rows],
  );
  const effectiveYear = yearFilter ?? availableYears[0] ?? null;

  const monthly = useMemo(() => {
    const data = MONTHS.map(() => ({ traitees: 0, aTraiter: 0 }));
    for (const r of rows) {
      if (effectiveYear !== null && r.year !== effectiveYear) continue;
      if (r.month === null) continue;
      if (r.processed) data[r.month].traitees += 1; else data[r.month].aTraiter += 1;
    }
    const max = Math.max(1, ...data.map((d) => d.traitees + d.aTraiter));
    return { data, max };
  }, [rows, effectiveYear]);

  const kpis = useMemo(() => {
    const traitees = rows.filter((r) => r.processed).length;
    return {
      aTraiter: rows.length - traitees,
      traitees,
      ecarts: rows.filter((r) => r.error > 0).length,
      anomalies: rows.filter((r) => r.anomaly > 0).length,
      expliquees: rows.filter((r) => r.explained > 0).length,
      informatif: rows.filter((r) => r.info > 0).length,
      bloquees: rows.filter((r) => r.blocked > 0).length,
    };
  }, [rows]);

  const totalAmount = useMemo(() => rows.reduce((s, r) => s + (r.total || 0), 0), [rows]);

  const distribution = useMemo<Distribution>(() => {
    const d: Distribution = { ok: 0, explained: 0, info: 0, ecart: 0, explain: 0, blocked: 0 };
    for (const r of rows) {
      if (r.blocked > 0) d.blocked += 1;
      else if (r.error > 0) d.ecart += 1;
      else if (r.anomaly > 0) d.explain += 1;
      else if (r.explained > 0) d.explained += 1;
      else if (r.info > 0) d.info += 1;
      else d.ok += 1;
    }
    return d;
  }, [rows]);

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (statusFilter !== "all" && r.status !== statusFilter) return false;
      if (controlFilter !== "all" && !matchesControl(r, controlFilter)) return false;
      if (problemFilter !== "all" && !r.issues.some((i) => i.code === problemFilter)) return false;
      if (supplierFilter !== "all" && r.supplier !== supplierFilter) return false;
      if (monthFilter !== null && !(r.year === effectiveYear && r.month === monthFilter)) return false;
      if (q && ![r.invoiceNumber, r.marche, r.perimetre, r.client, r.supplier].filter(Boolean).join(" ").toLowerCase().includes(q)) return false;
      return true;
    });
  }, [rows, query, statusFilter, controlFilter, problemFilter, supplierFilter, monthFilter, effectiveYear]);

  // Types de problème réellement présents (pour le filtre par typologie).
  const problemTypeOptions = useMemo(() => {
    const codes = new Set<string>();
    for (const r of rows) for (const i of r.issues) if (i.code) codes.add(i.code);
    return Array.from(codes)
      .map((code) => ({ value: code, label: problemTypeLabel(code) }))
      .sort((a, b) => a.label.localeCompare(b.label, "fr"));
  }, [rows]);

  const sortedRows = useMemo(() => {
    if (!sort) return filteredRows;
    const arr = [...filteredRows];
    arr.sort((a, b) => {
      const va = a[sort.key], vb = b[sort.key];
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * sort.dir;
      return String(va ?? "").localeCompare(String(vb ?? ""), "fr", { numeric: true }) * sort.dir;
    });
    return arr;
  }, [filteredRows, sort]);

  const toggleSort = (key: SortKey) =>
    setSort((s) => (s && s.key === key ? { key, dir: s.dir === 1 ? -1 : 1 } : { key, dir: 1 }));

  const changeStatus = (row: UnifiedRow, value: UnifiedStatus) => {
    if (row.source === "cpe") actions.setStatus.mutate({ invoiceId: row.rowId, status: UNIFIED_TO_CPE[value] });
    else actions.setEnergyStatus.mutate({ importId: row.rowId, decisionStatus: UNIFIED_TO_ENERGY[value] });
  };

  const isLoading = report.isLoading && energy.isLoading;

  return (
    <div className="po2-page-v1">
      <header className="po2-proto-panel po2-fact-head">
        <div className="po2-fact-head__top">
          <div>
            <span className="po2-eyebrow">Factures & décisions</span>
            <h1>Contrôler, décider, transmettre aux finances</h1>
            <p>DALKIA (CPE), ENGIE et EDF dans une file unique — la comptable valide chaque numéro de facture.</p>
          </div>
          <div className="po2-prototype-actions">
            <Button variant="ghost" onClick={() => setContactsOpen(true)}>Contacts fournisseurs</Button>
            <Button
              variant="ghost"
              onClick={() => { if (window.confirm("Supprimer les factures en double (même numéro) ? La plus récente est conservée.")) actions.purgeDuplicates.mutate(); }}
              disabled={actions.purgeDuplicates.isPending}
            >
              {actions.purgeDuplicates.isPending ? "Purge…" : "Purger les doublons"}
            </Button>
            <Button
              variant="ghost"
              onClick={() => { if (window.confirm("Recalculer tous les contrôles (DALKIA + énergie) ? Peut prendre une minute.")) actions.recomputeControls.mutate(); }}
              disabled={actions.recomputeControls.isPending}
            >
              {actions.recomputeControls.isPending ? "Recalcul…" : "Recalculer les contrôles"}
            </Button>
            <Button variant="ghost" disabled title="Import à brancher (upload + parseurs) — chantier séparé">
              Importer des factures
            </Button>
          </div>
        </div>

        <div className="po2-fact-head__kpis">
          <button type="button" className={"po2-fact-kpi" + (controlFilter === "todo" ? " is-active" : "")} onClick={() => setControlFilter(controlFilter === "todo" ? "all" : "todo")}>
            <span>À traiter</span><strong>{kpis.aTraiter}</strong><small>décision à prendre</small>
          </button>
          <button type="button" className={"po2-fact-kpi" + (controlFilter === "done" ? " is-active" : "")} onClick={() => setControlFilter(controlFilter === "done" ? "all" : "done")}>
            <span>Traitées</span><strong>{kpis.traitees}</strong><small>validées / transmises</small>
          </button>
          <button type="button" className={"po2-fact-kpi" + (controlFilter === "ecart" ? " is-active" : "")} onClick={() => setControlFilter(controlFilter === "ecart" ? "all" : "ecart")}>
            <span>Écarts</span><strong>{kpis.ecarts}</strong><small>à examiner</small>
          </button>
          <button type="button" className={"po2-fact-kpi" + (controlFilter === "explain" ? " is-active" : "")} onClick={() => setControlFilter(controlFilter === "explain" ? "all" : "explain")}>
            <span>À expliquer</span><strong>{kpis.anomalies}</strong><small>anomalies non résolues</small>
          </button>
          <button type="button" className={"po2-fact-kpi" + (controlFilter === "blocked" ? " is-active" : "")} onClick={() => setControlFilter(controlFilter === "blocked" ? "all" : "blocked")}>
            <span>Bloquées</span><strong>{kpis.bloquees}</strong><small>donnée manquante</small>
          </button>
          <button type="button" className={"po2-fact-kpi" + (controlFilter === "explained" ? " is-active" : "")} onClick={() => setControlFilter(controlFilter === "explained" ? "all" : "explained")}>
            <span>Expliquées</span><strong>{kpis.expliquees}</strong><small>neutralisées (avoir, doublon…)</small>
          </button>
          <button type="button" className={"po2-fact-kpi" + (controlFilter === "info" ? " is-active" : "")} onClick={() => setControlFilter(controlFilter === "info" ? "all" : "info")}>
            <span>Informatif</span><strong>{kpis.informatif}</strong><small>non bloquant (conso, regroupement)</small>
          </button>
        </div>

        <div className="po2-fact-head__synthese">
          <div className="po2-fact-head__bar" role="img" aria-label="Répartition des factures par état de contrôle">
            {BAR_SEGMENTS.map((seg) => {
              const n = distribution[seg.key];
              if (!n) return null;
              return <span key={seg.key} className="po2-fact-head__seg" style={{ width: `${(n / Math.max(1, rows.length)) * 100}%`, background: seg.color }} title={`${seg.label} : ${n}`} />;
            })}
          </div>
          <div className="po2-fact-head__legend">
            {BAR_SEGMENTS.map((seg) => (
              <span key={seg.key}><i style={{ background: seg.color }} />{seg.label} <b>{distribution[seg.key]}</b></span>
            ))}
            <span className="po2-fact-head__total">{rows.length} factures · {fmtEur(totalAmount)} HT</span>
          </div>
        </div>
      </header>
      {actions.purgeDuplicates.isSuccess ? (
        <p className="po2-muted-line">Purge effectuée : {actions.purgeDuplicates.data?.removed ?? 0} doublon(s) supprimé(s).</p>
      ) : null}
      {actions.purgeDuplicates.isError ? (
        <p className="po2-action-error">Purge : {(actions.purgeDuplicates.error as Error).message}</p>
      ) : null}
      {actions.recomputeControls.isSuccess ? (
        <p className="po2-muted-line">Contrôles recalculés ✓ (énergie : {actions.recomputeControls.data?.reanalyzed ?? 0} facture(s) ré-analysée(s)).</p>
      ) : null}
      {actions.recomputeControls.isError ? (
        <p className="po2-action-error">Recalcul : {(actions.recomputeControls.error as Error).message}</p>
      ) : null}

      <section className="po2-proto-panel" style={{ padding: "1.15rem", marginBottom: "1rem" }}>
        <div className="po2-proto-panel-head">
          <div>
            <span className="po2-eyebrow">Charge annuelle</span>
            <h2>Factures par mois d’émission</h2>
            <p>Vert : déjà traitées (validées ou transmises). Orange : à traiter. Cliquez un mois pour filtrer le tableau.</p>
          </div>
          {availableYears.length > 0 ? (
            <div className="po2-year-switch" role="group" aria-label="Année d’émission">
              {availableYears.map((y) => (
                <button
                  key={y}
                  type="button"
                  className={"po2-year-switch__btn" + (y === effectiveYear ? " is-active" : "")}
                  onClick={() => { setYearFilter(y); setMonthFilter(null); }}
                >
                  {y}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <div className="po2-month-chart">
          {monthly.data.map((d, i) => {
            const total = d.traitees + d.aTraiter;
            const active = monthFilter === i;
            return (
              <button
                key={MONTHS[i]}
                type="button"
                className={"po2-month-chart__col" + (active ? " is-active" : "")}
                title={`${MONTHS[i]} ${effectiveYear ?? ""} : ${d.traitees} traitée(s), ${d.aTraiter} à traiter${total ? " — cliquer pour filtrer" : ""}`}
                onClick={() => setMonthFilter(active ? null : i)}
                aria-pressed={active}
              >
                <div className="po2-month-chart__bar">
                  <div className="po2-month-chart__seg po2-month-chart__seg--todo" style={{ height: `${(d.aTraiter / monthly.max) * 100}%` }} />
                  <div className="po2-month-chart__seg po2-month-chart__seg--done" style={{ height: `${(d.traitees / monthly.max) * 100}%` }} />
                </div>
                <span className="po2-month-chart__count">{total || ""}</span>
                <span className="po2-month-chart__label">{MONTHS[i]}</span>
              </button>
            );
          })}
        </div>
      </section>

      <div className="po2-proto-toolbar-row">
        <label>
          <span>⌕</span>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="N° facture, contrat, marché, destinataire…" />
        </label>
        <select value={supplierFilter} onChange={(e) => setSupplierFilter(e.target.value)} aria-label="Filtrer fournisseur">
          <option value="all">Tous les fournisseurs</option>
          {suppliers.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={controlFilter} onChange={(e) => setControlFilter(e.target.value)} aria-label="Filtrer résultat de contrôle">
          {CONTROL_FILTER_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select value={problemFilter} onChange={(e) => setProblemFilter(e.target.value)} aria-label="Filtrer par type de problème">
          <option value="all">Tous les types de problème</option>
          {problemTypeOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Filtrer décision">
          <option value="all">Toutes les décisions</option>
          {UNIFIED_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        {monthFilter !== null ? (
          <button type="button" className="po2-fact-chipfilter" onClick={() => setMonthFilter(null)} title="Retirer le filtre mois">
            {MONTHS[monthFilter]} {effectiveYear ?? ""} ✕
          </button>
        ) : null}
        <span style={{ marginLeft: "auto", color: "var(--po2-color-muted)", fontSize: ".8rem" }}>{filteredRows.length} / {rows.length} facture(s)</span>
      </div>

      <section className="po2-proto-panel po2-proto-table-panel">
        {isLoading ? (
          <p className="po2-muted-line" style={{ padding: "1rem" }}>Chargement des factures…</p>
        ) : (
          <table>
            <thead>
              <tr>
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    className="po2-th-sortable"
                    style={{ textAlign: col.align }}
                    title={col.title ? `${col.title} · cliquer pour trier` : "Cliquer pour trier"}
                    onClick={() => toggleSort(col.key)}
                    aria-sort={sort?.key === col.key ? (sort.dir === 1 ? "ascending" : "descending") : "none"}
                  >
                    {col.label}
                    <span className="po2-th-sort-ind">{sort?.key === col.key ? (sort.dir === 1 ? " ▲" : " ▼") : ""}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((row) => (
                <tr key={row.key} className={row.key === selectedKey ? "active" : ""} onClick={() => setSelectedKey(row.key)}>
                  <td><div className="po2-proto-supplier"><span className="po2-proto-supplier-logo">{row.supplier.slice(0, 2).toUpperCase()}</span><div><b>{row.invoiceNumber}</b>{fmtPeriod(row.periodStart, row.periodEnd) ? <small title="Période facturée">{fmtPeriod(row.periodStart, row.periodEnd)}</small> : null}</div></div></td>
                  <td>{row.supplier}</td>
                  <td>{row.type}</td>
                  <td>{row.client}</td>
                  <td>{row.marche}</td>
                  <td>{row.perimetre}</td>
                  <td style={{ textAlign: "right" }}><strong>{fmtEur(row.total)}</strong></td>
                  <td style={{ textAlign: "right" }}>
                    {row.source === "cpe"
                      ? <span style={{ color: row.ok ? "#166534" : "var(--po2-color-muted)" }}>{row.ok}</span>
                      : (row.error === 0 && row.anomaly === 0 && row.explained === 0 && row.info === 0 && row.blocked === 0
                          ? <span style={{ color: "#166534", fontWeight: 700 }} title="Aucun écart ni point bloquant">✓</span>
                          : <span style={{ color: "var(--po2-color-muted)" }}>—</span>)}
                  </td>
                  <td style={{ textAlign: "right", color: row.error ? "#b91c1c" : "var(--po2-color-muted)", fontWeight: row.error ? 700 : 400 }}>{row.error || "-"}</td>
                  <td style={{ textAlign: "right", color: row.anomaly ? "#b45309" : "var(--po2-color-muted)", fontWeight: row.anomaly ? 700 : 400 }}>{row.anomaly || "-"}</td>
                  <td style={{ textAlign: "right", color: row.explained ? "#166534" : "var(--po2-color-muted)", fontWeight: row.explained ? 700 : 400 }}>{row.explained || "-"}</td>
                  <td style={{ textAlign: "right", color: row.info ? "#5b8def" : "var(--po2-color-muted)", fontWeight: row.info ? 700 : 400 }}>{row.info || "-"}</td>
                  <td style={{ textAlign: "right", color: row.blocked ? "#b45309" : "var(--po2-color-muted)", fontWeight: row.blocked ? 700 : 400 }}>{row.blocked || "-"}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <select value={row.status} disabled={actions.setStatus.isPending || actions.setEnergyStatus.isPending}
                      onChange={(e) => changeStatus(row, e.target.value as UnifiedStatus)}
                      style={{ padding: "4px 6px", borderRadius: 6, border: "1px solid var(--po2-color-line)", fontSize: ".75rem" }}>
                      {UNIFIED_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
              {filteredRows.length === 0 ? <tr><td colSpan={14} className="po2-muted-line">Aucune facture ne correspond aux filtres.</td></tr> : null}
            </tbody>
          </table>
        )}
      </section>

      <Drawer
        open={Boolean(selected)}
        title={selected ? "Facture " + selected.invoiceNumber : "Facture"}
        eyebrow={selected ? "Dossier facture · " + selected.supplier : "Dossier facture"}
        description={selected ? selected.supplier + " · " + selected.marche + " · " + selected.perimetre : undefined}
        onClose={() => setSelectedKey(null)}
      >
        {selected ? (
          <div className="po2-proto-dossier">
            <div className="po2-proto-dossier-kpis">
              <div><span>Montant</span><b>{fmtEur(selected.total)}</b></div>
              <div>
                <span>Période facturée</span>
                <b>{fmtPeriod(selected.periodStart, selected.periodEnd) ?? "—"}</b>
                {selected.month !== null && selected.year !== null ? <small style={{ display: "block", marginTop: ".2rem", color: "var(--po2-color-muted)", fontSize: ".68rem" }}>émise {fmtMonthYear(selected.month, selected.year)}</small> : null}
              </div>
              <div><span>Contrôles</span><b>{selected.source === "cpe" ? `${selected.ok} OK · ${selected.error} écart · ${selected.blocked} bloqué` : `${selected.error} écart · ${selected.anomaly} à expliquer · ${selected.explained} expliqué · ${selected.info} info · ${selected.blocked} bloqué`}</b></div>
              <div><span>Décision</span><b>{statusLabel(selected.status)}</b></div>
            </div>

            {selected.source === "cpe" ? (
              <>
                <h3>Contrôles par numéro de facture</h3>
                <ControlDecomposition controls={detail.controls.data ?? []} loading={detail.controls.isLoading} />
                <h3>Décomposition comptable (export finance)</h3>
                <LineDecomposition lines={detail.lines.data ?? []} loading={detail.lines.isLoading} />
              </>
            ) : (
              <>
                {(() => {
                  const info = selected.issues.filter((i) => isInformativeIssue(i));
                  const explained = selected.issues.filter((i) => isExplainedIssue(i) && !isInformativeIssue(i));
                  const anomalies = selected.issues.filter((i) => isAnomalyIssue(i) && !isInformativeIssue(i));
                  const reals = selected.issues.filter((i) => !isInformativeIssue(i) && !isNonControlable(i.code) && !isAnomalyIssue(i) && !isExplainedIssue(i));
                  const nc = selected.issues.filter((i) => isNonControlable(i.code) && !isInformativeIssue(i) && !isAnomalyIssue(i) && !isExplainedIssue(i));
                  return (
                    <>
                      <h3>Écarts de contrôle{reals.length ? ` (${reals.length})` : ""}</h3>
                      {reals.length === 0 ? (
                        <p className="po2-muted-line">Aucun écart réel de facturation.</p>
                      ) : (
                        <div className="po2-proto-control-list">
                          {aggregateIssues(reals).map((iss) => (
                            <article key={iss.message}>
                              <StatusBadge tone={issueTone(iss.severity)}>{iss.count > 1 ? `×${iss.count}` : iss.severity === "error" ? "ÉCART" : "ALERTE"}</StatusBadge>
                              <div><strong>{iss.message}</strong><small>{explainEcart(iss.code)}{iss.count > 1 ? ` · ${iss.count} occurrences` : ""}</small></div>
                            </article>
                          ))}
                        </div>
                      )}
                      {anomalies.length > 0 ? (
                        <>
                          <h3>Anomalies à expliquer ({anomalies.length})</h3>
                          <div className="po2-proto-control-list">
                            {aggregateIssues(anomalies).map((iss) => (
                              <article key={iss.message}>
                                <StatusBadge tone="warn">{iss.count > 1 ? `×${iss.count}` : "ANOMALIE"}</StatusBadge>
                                <div><strong>{iss.message}</strong><small>{explainEcart(iss.code)}{iss.count > 1 ? ` · ${iss.count} occurrences` : ""}</small></div>
                              </article>
                            ))}
                          </div>
                        </>
                      ) : null}
                      {explained.length > 0 ? (
                        <>
                          <h3>Éléments expliqués · non bloquants ({explained.length})</h3>
                          <div className="po2-proto-control-list">
                            {aggregateIssues(explained).map((iss) => (
                              <article key={iss.message}>
                                <StatusBadge tone="ok">{iss.count > 1 ? `×${iss.count}` : "EXPLIQUÉ"}</StatusBadge>
                                <div><strong>{iss.message}</strong><small>{explainExplained(iss.code)}{iss.count > 1 ? ` · ${iss.count} occurrences` : ""}</small></div>
                              </article>
                            ))}
                          </div>
                        </>
                      ) : null}
                      {info.length > 0 ? (
                        <>
                          <h3>Informatif · non bloquant ({info.length})</h3>
                          <div className="po2-proto-control-list">
                            {aggregateIssues(info).map((iss) => (
                              <article key={iss.message}>
                                <StatusBadge tone="neutral">{iss.count > 1 ? `×${iss.count}` : "INFO"}</StatusBadge>
                                <div><strong>{iss.message}</strong><small>{explainEcart(iss.code)}{iss.count > 1 ? ` · ${iss.count} occurrences` : ""}</small></div>
                              </article>
                            ))}
                          </div>
                        </>
                      ) : null}
                      {nc.length > 0 ? (
                        <>
                          <h3>Non contrôlable / en attente de donnée ({nc.length})</h3>
                          <div className="po2-proto-control-list">
                            {aggregateIssues(nc).map((iss) => (
                              <article key={iss.message}>
                                <StatusBadge tone="neutral">{iss.count > 1 ? `×${iss.count}` : "N/C"}</StatusBadge>
                                <div><strong>{iss.message}</strong><small>{explainEcart(iss.code)}{iss.count > 1 ? ` · ${iss.count} occurrences` : ""}</small></div>
                              </article>
                            ))}
                          </div>
                        </>
                      ) : null}
                    </>
                  );
                })()}
              </>
            )}

            <div className="po2-proto-decision-box">
              <span>Décision comptable</span>
              <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap", alignItems: "center", marginTop: ".4rem" }}>
                <select value={selected.status} disabled={actions.setStatus.isPending || actions.setEnergyStatus.isPending}
                  onChange={(e) => changeStatus(selected, e.target.value as UnifiedStatus)}
                  style={{ padding: "6px 8px", borderRadius: 8, border: "1px solid var(--po2-color-line)" }}>
                  {UNIFIED_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <StatusBadge tone={statusTone(selected.status)}>{statusLabel(selected.status)}</StatusBadge>
              </div>
            </div>

            <div className="po2-proto-action-stack">
              {selected.source === "cpe" ? (
                <Button onClick={() => actions.exportLiaison.mutate({ invoiceId: selected.rowId, invoiceNumber: selected.invoiceNumber })} disabled={actions.exportLiaison.isPending}>
                  {actions.exportLiaison.isPending ? "Export…" : "Exporter la fiche finance (XLSX)"}
                </Button>
              ) : null}
              <Button variant="danger" onClick={() => setClaimOpen(true)}>Préparer une réclamation</Button>
            </div>
            {actions.setStatus.isError ? <p className="po2-action-error">Décision : {(actions.setStatus.error as Error).message}</p> : null}
            {actions.setEnergyStatus.isError ? <p className="po2-action-error">Décision : {(actions.setEnergyStatus.error as Error).message}</p> : null}
            {actions.exportLiaison.isError ? <p className="po2-action-error">Export : {(actions.exportLiaison.error as Error).message}</p> : null}
          </div>
        ) : null}
      </Drawer>

      <Drawer
        open={contactsOpen}
        title="Contacts fournisseurs"
        eyebrow="Réclamations"
        description="Un contact par fournisseur, réutilisé pour pré-remplir les réclamations."
        onClose={() => setContactsOpen(false)}
      >
        <SupplierContactsEditor suppliers={editableSuppliers} />
      </Drawer>

      {selected ? (
        <ReclamationDrawer
          key={`${selected.key}:${contactBySupplier.get(selected.supplier)?.updated_at ?? "none"}`}
          open={claimOpen}
          onClose={() => setClaimOpen(false)}
          row={selected}
          contact={contactBySupplier.get(selected.supplier)}
          points={claimPoints}
          onOpenContacts={() => { setClaimOpen(false); setContactsOpen(true); }}
        />
      ) : null}
    </div>
  );
}

function SupplierContactsEditor({ suppliers }: { suppliers: string[] }) {
  const { contacts, save } = useSupplierContactsV1();
  const bySupplier = useMemo(() => {
    const m = new Map<string, SupplierContact>();
    for (const c of contacts.data ?? []) m.set(c.supplier, c);
    return m;
  }, [contacts.data]);
  if (contacts.isLoading) return <p className="po2-muted-line">Chargement des contacts…</p>;
  return (
    <div className="po2-contacts-editor">
      {suppliers.map((s) => {
        const c = bySupplier.get(s);
        return (
          <ContactRow
            key={`${s}:${c?.updated_at ?? "new"}`}
            supplier={s}
            contact={c}
            saving={save.isPending}
            onSave={(supplier, payload) => save.mutate({ supplier, payload })}
          />
        );
      })}
      {save.isError ? <p className="po2-action-error">Enregistrement : {(save.error as Error).message}</p> : null}
    </div>
  );
}

function ContactRow({
  supplier, contact, onSave, saving,
}: {
  supplier: string;
  contact: SupplierContact | undefined;
  onSave: (supplier: string, payload: SupplierContactInput) => void;
  saving: boolean;
}) {
  const [form, setForm] = useState<SupplierContactInput>({
    contact_name: contact?.contact_name ?? "",
    email: contact?.email ?? "",
    phone: contact?.phone ?? "",
    role: contact?.role ?? "",
    notes: contact?.notes ?? "",
  });
  const set = (f: keyof SupplierContactInput) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((prev) => ({ ...prev, [f]: e.target.value }));
  return (
    <article className="po2-contact-card">
      <div className="po2-contact-card__head">
        <span className="po2-proto-supplier-logo">{supplier.slice(0, 2).toUpperCase()}</span>
        <strong>{supplier}</strong>
      </div>
      <div className="po2-contact-card__grid">
        <label><span>Nom du contact</span><input value={form.contact_name ?? ""} onChange={set("contact_name")} placeholder="Prénom Nom" /></label>
        <label><span>E-mail</span><input type="email" value={form.email ?? ""} onChange={set("email")} placeholder="contact@fournisseur.fr" /></label>
        <label><span>Téléphone</span><input value={form.phone ?? ""} onChange={set("phone")} placeholder="01 23 45 67 89" /></label>
        <label><span>Rôle / service</span><input value={form.role ?? ""} onChange={set("role")} placeholder="Service clients, gestionnaire…" /></label>
      </div>
      <label className="po2-contact-card__notes"><span>Notes</span><textarea rows={2} value={form.notes ?? ""} onChange={set("notes")} /></label>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <Button onClick={() => onSave(supplier, form)} disabled={saving}>{saving ? "Enregistrement…" : "Enregistrer"}</Button>
      </div>
    </article>
  );
}

function ReclamationDrawer({
  open, onClose, row, contact, points, onOpenContacts,
}: {
  open: boolean;
  onClose: () => void;
  row: UnifiedRow;
  contact: SupplierContact | undefined;
  points: string[];
  onOpenContacts: () => void;
}) {
  const base = useMemo(() => buildClaimDraft(row, contact, points), [row, contact, points]);
  const [to, setTo] = useState(base.to);
  const [subject, setSubject] = useState(base.subject);
  const [body, setBody] = useState(base.body);
  const [copied, setCopied] = useState<string | null>(null);
  const copy = (label: string, text: string) => {
    navigator.clipboard?.writeText(text).then(() => { setCopied(label); setTimeout(() => setCopied(null), 1800); });
  };
  const mailto = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  return (
    <Drawer
      open={open}
      title={`Réclamation · ${row.invoiceNumber}`}
      eyebrow={`Brouillon · ${row.supplier}`}
      description="Message pré-rempli à copier ou ouvrir dans votre messagerie. Aucun envoi automatique."
      onClose={onClose}
    >
      <div className="po2-claim">
        {!contact?.email ? (
          <p className="po2-muted-line">
            Aucun e-mail enregistré pour {row.supplier}.{" "}
            <button type="button" className="po2-linklike" onClick={onOpenContacts}>Renseigner le contact</button>.
          </p>
        ) : null}
        <label className="po2-claim__field"><span>Destinataire</span><input value={to} onChange={(e) => setTo(e.target.value)} placeholder="email du contact" /></label>
        <label className="po2-claim__field"><span>Objet</span><input value={subject} onChange={(e) => setSubject(e.target.value)} /></label>
        <label className="po2-claim__field"><span>Message</span><textarea rows={12} value={body} onChange={(e) => setBody(e.target.value)} /></label>
        <div className="po2-claim__actions">
          <Button onClick={() => copy("Message", body)}>{copied === "Message" ? "Copié ✓" : "Copier le message"}</Button>
          <Button variant="ghost" onClick={() => copy("E-mail", to)} disabled={!to}>{copied === "E-mail" ? "Copié ✓" : "Copier l’e-mail"}</Button>
          <a className="po2-button po2-button--ghost" href={mailto}>Ouvrir dans la messagerie</a>
        </div>
      </div>
    </Drawer>
  );
}

function ControlDecomposition({ controls, loading }: { controls: CpeFinanceControl[]; loading: boolean }) {
  const okCount = controls.filter((c) => c.status === "ok").length;
  const errors = useMemo(
    () => aggregateIssues(controls.filter((c) => c.status === "error").map((c) => ({ severity: "error", message: c.message || controlTypeLabel(c.control_type), code: c.control_type }))),
    [controls],
  );
  const blocked = useMemo(
    () => aggregateIssues(controls.filter((c) => c.status === "blocked").map((c) => ({ severity: "warning", message: c.message || controlTypeLabel(c.control_type), code: c.control_type }))),
    [controls],
  );
  if (loading) return <p className="po2-muted-line">Chargement des contrôles…</p>;
  if (controls.length === 0) return <p className="po2-muted-line">Aucun contrôle enregistré pour cette facture.</p>;
  return (
    <>
      <div className="po2-proto-control-list">
        {errors.length === 0 ? (
          <article><StatusBadge tone="ok">OK</StatusBadge><div><strong>Aucun écart réel</strong><small>{okCount} contrôle(s) conforme(s)</small></div></article>
        ) : errors.map((iss) => (
          <article key={iss.message}>
            <StatusBadge tone="bad">{iss.count > 1 ? `×${iss.count}` : "ÉCART"}</StatusBadge>
            <div><strong>{iss.message}</strong><small>{explainEcart(iss.code)}{iss.count > 1 ? ` · ${iss.count} occurrences` : ""}</small></div>
          </article>
        ))}
      </div>
      {blocked.length > 0 ? (
        <>
          <h3>Non contrôlable / en attente</h3>
          <div className="po2-proto-control-list">
            {blocked.map((iss) => (
              <article key={iss.message}>
                <StatusBadge tone="neutral">{iss.count > 1 ? `×${iss.count}` : "N/C"}</StatusBadge>
                <div><strong>{iss.message}</strong><small>{explainEcart(iss.code)}{iss.count > 1 ? ` · ${iss.count} occurrences` : ""}</small></div>
              </article>
            ))}
          </div>
        </>
      ) : null}
    </>
  );
}

function LineDecomposition({ lines, loading }: { lines: CpeFinanceLine[]; loading: boolean }) {
  if (loading) return <p className="po2-muted-line">Chargement de la décomposition…</p>;
  if (lines.length === 0) return <p className="po2-muted-line">Aucune ligne comptable. La décomposition apparaît après rattachement à la matrice.</p>;
  const total = lines.reduce((s, l) => s + (l.amount_ht ?? 0), 0);
  return (
    <>
      <div className="po2-proto-control-list">
        {lines.slice(0, 12).map((line) => (
          <article key={line.id} style={{ gridTemplateColumns: "1fr auto" }}>
            <div><strong>{line.billed_item ?? line.market ?? "Ligne"} · {fmtEur(line.amount_ht)}</strong>
              <small>{[line.accounting_nature, line.accounting_label, line.service_sold, line.site_code_detected].filter(Boolean).join(" · ") || "Nature comptable à compléter"}</small></div>
            {!line.accounting_nature ? <StatusBadge tone="warn">À compléter</StatusBadge> : <StatusBadge tone="ok">Imputée</StatusBadge>}
          </article>
        ))}
      </div>
      {lines.length > 12 ? <p className="po2-muted-line" style={{ marginTop: ".4rem" }}>+ {lines.length - 12} autre(s) ligne(s)…</p> : null}
      <p className="po2-muted-line" style={{ marginTop: ".4rem" }}>Total décomposé : <strong>{fmtEur(total)}</strong></p>
    </>
  );
}
