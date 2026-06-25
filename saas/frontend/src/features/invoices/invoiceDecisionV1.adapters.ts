import type { CpeFinanceInvoice, EnergyInvoiceImport, GasInvoice } from "../../lib/api";
import type { AccountingMatrixV1Status, InvoiceDecisionV1, InvoiceDecisionV1Status, InvoiceProofV1 } from "./invoiceDecisionV1.types";

function eur(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value);
}
function decisionStatusFromEnergy(invoice: EnergyInvoiceImport): InvoiceDecisionV1Status {
  if (invoice.finance_exported_at) return "transmise";
  if (invoice.decision_status === "approved") return "conforme";
  if (invoice.decision_status === "rejected" || invoice.decision_status === "dispute_sent") return "anomalie";
  if (invoice.control_errors_count > 0) return "anomalie";
  return "decision";
}
function matrixStatusFromEnergy(invoice: EnergyInvoiceImport): AccountingMatrixV1Status {
  if (invoice.finance_exported_at) return "validee";
  if (invoice.control_errors_count > 0) return "a_completer";
  if (invoice.control_warnings_count > 0) return "proposee";
  return "validee";
}
function gasStatus(status: string): InvoiceDecisionV1Status {
  if (status === "valid") return "conforme";
  if (status === "invalid") return "anomalie";
  return "decision";
}
function cpeStatus(invoice: CpeFinanceInvoice): InvoiceDecisionV1Status {
  if (invoice.finance_exported_at) return "transmise";
  if (invoice.status === "validated" || invoice.status === "approved") return "conforme";
  if (invoice.status === "rejected" || invoice.status === "blocked") return "anomalie";
  return "decision";
}
function safeProofsFromJson(json: string | null | undefined): InvoiceProofV1[] {
  if (!json) return [];
  try {
    const rows = JSON.parse(json) as Array<{ label?: string; method?: string; reference?: string; source?: string; verdict?: string }>;
    return rows.map((row) => ({ label: row.label ?? "Contrôle", method: row.method ?? "Méthode non précisée", reference: row.reference, source: row.source, status: row.verdict === "invalid" ? "bad" : row.verdict === "review" ? "warn" : row.verdict === "ok" ? "ok" : "info" }));
  } catch {
    return [];
  }
}
export function adaptEnergyInvoiceImportToDecisionV1(invoice: EnergyInvoiceImport): InvoiceDecisionV1 {
  const supplier = invoice.supplier_guess || invoice.contract_holder || "Fournisseur énergie";
  const invoiceNumber = invoice.invoice_number || `import-${invoice.id}`;
  const issue = invoice.control_issues?.[0]?.message || (invoice.control_errors_count > 0 ? "Écart de contrôle à analyser" : "Contrôles à valider");
  return { stableId: `energy:${invoice.id}`, source: "energy-import", sourceId: invoice.id, supplier, invoiceNumber, siteLabel: invoice.filter_facets?.site_names?.[0] || invoice.regroupement || "Portefeuille énergie", contractLabel: invoice.regroupement || invoice.energy_type || "Marché énergie", amountTtc: invoice.total_ttc, amountTtcLabel: eur(invoice.total_ttc), issuedAt: invoice.invoice_date, dueAt: null, status: decisionStatusFromEnergy(invoice), matrixStatus: matrixStatusFromEnergy(invoice), issue, alreadyProcessed: Boolean(invoice.finance_exported_at || invoice.decision_updated_at), snapshotVersionLabel: invoice.finance_exported_at ? "Snapshot transmis finances" : "Version active à appliquer", proofs: (invoice.control_issues || []).slice(0, 4).map((item) => ({ label: item.code, method: item.message, status: item.severity === "error" ? "bad" : item.severity === "warning" ? "warn" : "info", source: item.scope })) };
}
export function adaptGasInvoiceToDecisionV1(invoice: GasInvoice): InvoiceDecisionV1 {
  const proofs = safeProofsFromJson(invoice.control_detail_json);
  return { stableId: `gas:${invoice.id}`, source: "gas-totalenergies", sourceId: invoice.id, supplier: "TotalEnergies", invoiceNumber: invoice.num_facture, siteLabel: invoice.nom_site || invoice.lib_regroupement || invoice.pce, contractLabel: `Gaz · ${invoice.tarif_acheminement || "Lot 7"}`, amountTtc: invoice.total_ttc, amountTtcLabel: eur(invoice.total_ttc), issuedAt: invoice.date_comptable, dueAt: invoice.date_echeance, status: gasStatus(invoice.control_status), matrixStatus: invoice.control_status === "valid" ? "validee" : "a_completer", issue: proofs.find((proof) => proof.status === "bad" || proof.status === "warn")?.method || "Contrôle gaz à valider", proofs, alreadyProcessed: invoice.decision_status !== "to_review", snapshotVersionLabel: "Référentiels gaz datés" };
}
export function adaptCpeFinanceInvoiceToDecisionV1(invoice: CpeFinanceInvoice): InvoiceDecisionV1 {
  return { stableId: `cpe:${invoice.id}`, source: "cpe-dalkia", sourceId: invoice.id, supplier: invoice.supplier || "DALKIA", invoiceNumber: invoice.invoice_number, siteLabel: invoice.customer_name || invoice.recipient_reference_1 || "Portefeuille CPE", contractLabel: invoice.contract_label || invoice.markets || "CPE DALKIA", amountTtc: null, amountTtcLabel: `${eur(invoice.total_ht)} HT`, issuedAt: invoice.invoice_date, dueAt: invoice.due_date, status: cpeStatus(invoice), matrixStatus: invoice.evidence_status ? "proposee" : "a_arbitrer", issue: invoice.notes || invoice.billed_items || "Facture CPE à instruire", alreadyProcessed: Boolean(invoice.finance_exported_at), snapshotVersionLabel: invoice.contract_code, proofs: [{ label: "Référence contrat", method: invoice.contract_label || invoice.contract_code || "Contrat à confirmer", status: invoice.contract_code ? "ok" : "warn" }, { label: "Pièce justificative", method: invoice.evidence_status || "Preuve à joindre", status: invoice.evidence_status ? "ok" : "warn" }] };
}
