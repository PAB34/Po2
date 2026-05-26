import type { EnergyInvoiceImport } from "./api";

export type InvoiceControlIssue = EnergyInvoiceImport["control_issues"][number];

export type InvoiceIssueFamily =
  | "bpu"
  | "turpe"
  | "taxes"
  | "periods"
  | "consumption"
  | "power"
  | "document"
  | "other";

export const INVOICE_ISSUE_FAMILY_LABEL: Record<InvoiceIssueFamily, string> = {
  bpu: "Prix contractuels",
  turpe: "Acheminement / TURPE",
  taxes: "Taxes et TVA",
  periods: "Periodes",
  consumption: "Consommation",
  power: "Puissance",
  document: "Identite facture",
  other: "Autres controles",
};

export const INVOICE_ISSUE_FAMILY_ORDER: InvoiceIssueFamily[] = [
  "bpu",
  "turpe",
  "consumption",
  "periods",
  "power",
  "taxes",
  "document",
  "other",
];

export const INVOICE_ISSUE_FAMILY_DETAIL: Record<InvoiceIssueFamily, string> = {
  bpu: "Prix, poste ou option tarifaire incoherent avec le BPU.",
  turpe: "Controle des composantes d'acheminement : ecart TURPE calcule ou limite de verification.",
  taxes: "Total HT, TVA ou TTC a rapprocher avec les lignes facturees.",
  periods: "Periode absente, trou ou chevauchement potentiel.",
  consumption: "Ecart ou manque de donnees ENEDIS sur la periode facturee.",
  power: "Puissance a verifier : depassement, ecart ou donnee manquante.",
  document: "Reference, perimetre ou donnees d'identification a verifier.",
  other: "Point technique a examiner dans le detail des controles.",
};

export const INVOICE_KNOWN_ISSUE_CODES: Array<{
  code: string;
  family: InvoiceIssueFamily;
  label: string;
  message: string;
}> = [
  {
    code: "BPU_PRICE_MISMATCH",
    family: "bpu",
    label: "Ecart prix facture / BPU",
    message: "Prix unitaire facture different du prix contractuel BPU, avec recalcul de l'ecart dans le rapport.",
  },
  {
    code: "BPU_TARIFF_POSTE_INCONSISTENCY",
    family: "bpu",
    label: "Incoherence tarif/poste BPU",
    message: "Le prix facture correspond a une autre ligne BPU que celle attendue pour le tarif et le poste.",
  },
  {
    code: "BPU_REFERENCE_MISSING",
    family: "bpu",
    label: "Reference BPU manquante",
    message: "Aucune ligne BPU n'a pu etre associee au tarif/poste facture.",
  },
  {
    code: "BPU_PRICE_MISSING",
    family: "bpu",
    label: "Prix BPU manquant",
    message: "La ligne BPU existe, mais le prix du composant controle n'est pas renseigne.",
  },
];

export function invoiceIssueFamily(issue: InvoiceControlIssue): InvoiceIssueFamily {
  const code = issue.code ?? "";
  if (code.startsWith("BPU_")) return "bpu";
  if (code.startsWith("TURPE_")) return "turpe";
  if (code.includes("CONSUMPTION") || code.startsWith("ENEDIS_CONSUMPTION") || code.startsWith("LOAD_CURVE_CONSUMPTION")) {
    return "consumption";
  }
  if (code.includes("POWER") || code.startsWith("SUBSCRIBED_POWER")) return "power";
  if (code.includes("VAT") || code.includes("TAX") || code === "HT_TOTAL_MISMATCH" || code === "INVOICE_VAT_TOTAL_MISMATCH") {
    return "taxes";
  }
  if (code.includes("PERIOD")) return "periods";
  if (
    code.includes("PRM") ||
    code.includes("SUPPLIER") ||
    code.includes("MARKET") ||
    code.includes("REGROUPEMENT") ||
    code.includes("INVOICE") ||
    code.includes("CHORUS") ||
    code.includes("DOCUMENT")
  ) {
    return "document";
  }
  return "other";
}

const TURPE_SUPPLIER_ISSUE_CODES = new Set([
  "TURPE_AMOUNT_MISMATCH",
  "TURPE_UNIT_PRICE_MISMATCH",
  "TURPE_TOTAL_MISMATCH",
]);

const INTERNAL_CONTROL_LIMIT_CODES = new Set([
  "BPU_CONFIG_MISSING",
  "BPU_LINES_MISSING",
  "BPU_REFERENCE_MISSING",
  "BPU_PRICE_MISSING",
  "CONSUMPTION_REFERENCE_MISSING",
  "DUPLICATE_INVOICE_NUMBER",
  "ENEDIS_CONSUMPTION_MISSING",
  "ENEDIS_CONSUMPTION_PARTIAL",
  "ENEDIS_POWER_MISSING",
  "LOAD_CURVE_CONSUMPTION_PARTIAL",
  "LOAD_CURVE_POWER_PARTIAL",
  "NO_SITE_FOUND",
  "PARSER_FAILED",
  "PERIOD_MISSING",
  "POWER_REFERENCE_MISSING",
  "SUBSCRIBED_POWER_MISSING",
  "TAX_TOTALS_MISSING",
  "UNKNOWN_PRM",
]);

export function isSupplierReportIssue(issue: InvoiceControlIssue) {
  return !isInternalControlLimit(issue);
}

export function isInternalControlLimit(issue: InvoiceControlIssue) {
  if (invoiceIssueFamily(issue) === "turpe") return !TURPE_SUPPLIER_ISSUE_CODES.has(issue.code);
  return INTERNAL_CONTROL_LIMIT_CODES.has(issue.code);
}
