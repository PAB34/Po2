import { useEffect, useMemo, useState } from "react";
import { Button, Drawer, StatusBadge } from "../../design-system";
import { useAccountingMatricesV1 } from "./accountingMatrixV1";
import { useInvoiceDecisionsV1 } from "./useInvoiceDecisionsV1";
import { useInvoiceAccountingSnapshotV1, useInvoiceAccountingActionsV1 } from "./useInvoiceAccountingSnapshotsV1";
import { useMatrixContractsV1 } from "../matrices/useMatricesV1";
import type { AccountingMatrixContractV1 } from "../../lib/api";
import type { AccountingMatrixStatus, InvoiceDecision, InvoiceDecisionStatus } from "./invoices.types";

// ---------------------------------------------------------------------------
// Helpers de présentation
// ---------------------------------------------------------------------------
function matrixSupplierKeyword(value: string) {
  const upper = value.toUpperCase();
  if (upper.includes("TOTAL")) return "TOTAL";
  if (upper.includes("DALKIA")) return "DALKIA";
  if (upper.includes("ENGIE")) return "ENGIE";
  if (upper.includes("EDF")) return "EDF";
  return upper;
}

function suggestMatrixContract(invoice: InvoiceDecision | null, contracts: AccountingMatrixContractV1[]) {
  if (!invoice) return null;
  const supplierKey = matrixSupplierKeyword(invoice.supplier);
  const sameSupplier = contracts.filter((c) => matrixSupplierKeyword(c.supplier) === supplierKey);
  const ref = `${invoice.contractLabel ?? ""} ${invoice.invoiceNumber ?? ""}`.toUpperCase();
  const exact = sameSupplier.find((c) => c.contract_code && ref.includes(c.contract_code.toUpperCase()));
  return (exact ?? sameSupplier[0] ?? null)?.id ?? null;
}

function actionError(error: unknown) {
  return error instanceof Error ? error.message : null;
}

function supplierInitials(supplier: string) {
  const upper = supplier.toUpperCase();
  if (upper.includes("TOTAL")) return "TE";
  if (upper.includes("DALKIA")) return "DK";
  if (upper.includes("ENGIE")) return "EN";
  if (upper.includes("EDF")) return "ED";
  if (upper.includes("SPIE")) return "SP";
  return supplier.slice(0, 2).toUpperCase();
}

function invoiceTone(status: InvoiceDecisionStatus) {
  if (status === "conforme") return "ok" as const;
  if (status === "anomalie") return "bad" as const;
  if (status === "transmise") return "info" as const;
  return "warn" as const;
}

function invoiceLabel(status: InvoiceDecisionStatus) {
  return { conforme: "Conforme", anomalie: "Anomalie", decision: "À décider", transmise: "Transmise", archivee: "Archivée" }[status];
}

function matrixTone(status: AccountingMatrixStatus) {
  if (status === "validee") return "ok" as const;
  if (status === "proposee") return "info" as const;
  if (status === "a_completer") return "warn" as const;
  if (status === "a_arbitrer") return "bad" as const;
  return "neutral" as const;
}

function matrixLabel(status: AccountingMatrixStatus) {
  return { validee: "Validée", proposee: "Proposée", a_completer: "À compléter", a_arbitrer: "À arbitrer", non_applicable: "Non applicable" }[status];
}

function snapshotLabel(status?: string) {
  if (status === "proposed") return "Proposition";
  if (status === "validated") return "Validé";
  if (status === "manual_override") return "Corrigé";
  if (status === "exported") return "Exporté";
  return "Aucun snapshot";
}

function formatKpiAmount(value: number) {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value);
}

function sumInvoiceAmounts(rows: InvoiceDecision[]) {
  return rows.reduce((total, invoice) => total + (invoice.amountTtc ?? 0), 0);
}

// ---------------------------------------------------------------------------
// Snapshot comptable : parsing imputation par ligne + exceptions
// ---------------------------------------------------------------------------
type SnapshotImputation = { service?: string | null; function?: string | null; antenna?: string | null; operation?: string | null; nature?: string | null; label?: string | null; allocation_percent?: number; amount_allocated?: number | null };
type SnapshotLine = { line_index: number; line_ref?: string | null; billed_item?: string | null; amount?: number | null; matched: boolean; allocation_total?: number; imputations: SnapshotImputation[] };
type SnapshotPayload = { lines: SnapshotLine[]; exceptions: Array<{ billed_item?: string | null; reason?: string }>; matched_lines: number; total_lines: number };

function parseSnapshotJson(json: string | null | undefined): SnapshotPayload | null {
  if (!json) return null;
  try {
    const parsed = JSON.parse(json);
    if (!parsed || !Array.isArray(parsed.lines)) return null;
    return parsed as SnapshotPayload;
  } catch {
    return null;
  }
}

function parseExceptions(json: string | null | undefined): Array<{ billed_item?: string | null; reason?: string }> {
  if (!json) return [];
  try {
    const parsed = JSON.parse(json);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function eur(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value);
}

function dominantAxes(payload: SnapshotPayload): string[] {
  const natures = new Set<string>();
  for (const line of payload.lines) {
    for (const imp of line.imputations) {
      const key = imp.nature || imp.label || imp.service;
      if (key) natures.add(key);
    }
  }
  return Array.from(natures).slice(0, 4);
}

// ---------------------------------------------------------------------------
// Verdict + décision recommandée (dérivés des vraies données)
// ---------------------------------------------------------------------------
function verdict(invoice: InvoiceDecision, payload: SnapshotPayload | null, exceptionsCount: number) {
  if (invoice.status === "anomalie") return { tone: "bad" as const, text: invoice.issue || "Écart de contrôle à traiter" };
  if (exceptionsCount > 0) return { tone: "warn" as const, text: `${exceptionsCount} exception(s) d'imputation à résoudre` };
  if (payload && payload.total_lines > 0 && payload.matched_lines < payload.total_lines)
    return { tone: "warn" as const, text: `${payload.matched_lines}/${payload.total_lines} lignes imputées` };
  if (invoice.status === "transmise") return { tone: "ok" as const, text: "Facture transmise aux finances" };
  if (invoice.status === "conforme") return { tone: "ok" as const, text: invoice.issue || "Contrôles conformes" };
  return { tone: "warn" as const, text: invoice.issue || "Décision attendue" };
}

function recommendation(invoice: InvoiceDecision, snapshotStatus: string | undefined, exceptionsCount: number) {
  if (invoice.status === "transmise") return "Aucune action : facture déjà transmise aux finances.";
  if (invoice.status === "anomalie") return "Préparer une réclamation fournisseur avant validation.";
  if (exceptionsCount > 0) return "Résoudre les exceptions d'imputation avant de valider.";
  if (snapshotStatus === "validated") return "Snapshot validé : prêt pour l'export finances.";
  if (snapshotStatus === "proposed") return "Vérifier l'imputation proposée puis valider.";
  return "Appliquer la matrice comptable pour proposer l'imputation.";
}

const invoiceWorkflowSteps = [
  { label: "Importer", detail: "Export fournisseur ou lot annuel" },
  { label: "Dédoublonner", detail: "Nouvelles vs déjà traitées" },
  { label: "Contrôler", detail: "BPU, TURPE, taxes, périodes" },
  { label: "Imputer", detail: "Matrice comptable versionnée" },
  { label: "Décider", detail: "Valider, réclamer ou exporter" },
  { label: "Exporter", detail: "Transmission finances figée" },
] as const;

export function InvoicesDecisionPageV1() {
  const [query, setQuery] = useState("");
  const [supplierFilter, setSupplierFilter] = useState("all");
  const [matrixFilter, setMatrixFilter] = useState("all");
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceDecision | null>(null);
  const { invoices, isFetching, isUsingFallback } = useInvoiceDecisionsV1();
  const { matrices, isUsingFallback: isUsingMatrixFallback } = useAccountingMatricesV1();
  const snapshot = useInvoiceAccountingSnapshotV1(selectedInvoice);
  const actions = useInvoiceAccountingActionsV1(selectedInvoice);
  const { data: matrixContracts = [] } = useMatrixContractsV1();
  const [matrixContractId, setMatrixContractId] = useState<number | null>(null);

  useEffect(() => {
    setMatrixContractId(null);
    actions.apply.reset();
    actions.validate.reset();
    actions.exportFinance.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedInvoice?.stableId]);

  const autoMatchedContractId = useMemo(() => {
    const code = selectedInvoice?.contractCode?.trim().toUpperCase();
    if (!code) return null;
    return matrixContracts.find((c) => c.contract_code?.trim().toUpperCase() === code)?.id ?? null;
  }, [selectedInvoice, matrixContracts]);
  const suggestedContractId = useMemo(() => suggestMatrixContract(selectedInvoice, matrixContracts), [selectedInvoice, matrixContracts]);
  const effectiveContractId = matrixContractId ?? autoMatchedContractId ?? suggestedContractId;
  const effectiveContract = matrixContracts.find((c) => c.id === effectiveContractId) ?? null;
  const isAutoMatched = matrixContractId === null && autoMatchedContractId !== null;

  const suppliers = useMemo(() => Array.from(new Set(invoices.map((i) => i.supplier))).sort(), [invoices]);

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return invoices.filter((invoice) => {
      if (supplierFilter !== "all" && invoice.supplier !== supplierFilter) return false;
      if (matrixFilter !== "all" && invoice.matrixStatus !== matrixFilter) return false;
      if (q && !Object.values(invoice).join(" ").toLowerCase().includes(q)) return false;
      return true;
    });
  }, [query, supplierFilter, matrixFilter, invoices]);

  const kpis = useMemo(() => {
    const nouvelles = invoices.filter((i) => !i.alreadyProcessed);
    const imputees = invoices.filter((i) => i.matrixStatus === "validee");
    const exceptions = invoices.filter((i) => i.status === "anomalie" || i.matrixStatus === "a_completer" || i.matrixStatus === "a_arbitrer");
    const transmises = invoices.filter((i) => i.status === "transmise");
    return {
      nouvelles: { count: nouvelles.length, detail: `${formatKpiAmount(sumInvoiceAmounts(nouvelles))} à instruire` },
      imputees: { count: imputees.length, detail: `sur ${invoices.length} factures` },
      exceptions: { count: exceptions.length, detail: `${formatKpiAmount(sumInvoiceAmounts(exceptions))} à arbitrer` },
      transmises: { count: transmises.length, detail: `${formatKpiAmount(sumInvoiceAmounts(transmises))} ce lot` },
    };
  }, [invoices]);

  const snapshotPayload = parseSnapshotJson(snapshot.data?.snapshot_json);
  const snapshotExceptions = parseExceptions(snapshot.data?.exceptions_json);
  const blockingExceptions = snapshotExceptions.length > 0;
  const currentVerdict = selectedInvoice ? verdict(selectedInvoice, snapshotPayload, snapshotExceptions.length) : null;

  const sourceTone = isUsingFallback ? "warn" : isFetching ? "info" : "ok";
  const sourceLabel = isUsingFallback ? "Démonstration" : isFetching ? "Synchronisation" : "Données API";

  return (
    <div className="po2-page-v1">
      <header className="po2-prototype-page-head">
        <div>
          <span className="po2-eyebrow">Factures & décisions</span>
          <h1>Importer, contrôler, imputer, décider.</h1>
          <p>Une chaîne unique relie la facture à son contrat, sa matrice comptable et la transmission aux finances.</p>
        </div>
        <div className="po2-prototype-actions">
          <Button variant="ghost">Rapports d’import</Button>
          <Button>Importer des factures</Button>
        </div>
      </header>

      <section className="po2-proto-panel po2-proto-flow-panel">
        <div className="po2-proto-flow-batch">
          <div>
            <span className="po2-eyebrow">File de traitement</span>
            <h2>{invoices.length} facture(s) · {filteredRows.length} affichée(s)</h2>
            <p>Agrège les imports ENGIE/EDF, le gaz TotalEnergies et les factures CPE/DALKIA disponibles.</p>
          </div>
          <StatusBadge tone={sourceTone}>{sourceLabel}</StatusBadge>
        </div>
        <div className="po2-proto-invoice-steps">
          {invoiceWorkflowSteps.map((step, index) => (
            <article key={step.label} className={index < 4 ? "done" : "current"}>
              <span>{index + 1}</span>
              <b>{step.label}</b>
              <small>{step.detail}</small>
            </article>
          ))}
        </div>
      </section>

      <div className="po2-proto-kpi-grid">
        <article><span>Nouvelles</span><strong>{kpis.nouvelles.count}</strong><small>{kpis.nouvelles.detail}</small></article>
        <article><span>Imputation complète</span><strong>{kpis.imputees.count}</strong><small>{kpis.imputees.detail}</small></article>
        <article><span>Exceptions comptables</span><strong>{kpis.exceptions.count}</strong><small>{kpis.exceptions.detail}</small></article>
        <article><span>Transmises aux finances</span><strong>{kpis.transmises.count}</strong><small>{kpis.transmises.detail}</small></article>
      </div>

      <section className="po2-proto-panel po2-proto-matrix-overview">
        <div className="po2-proto-panel-head">
          <div>
            <span className="po2-eyebrow">{isUsingMatrixFallback ? "Référentiel contractuel · synthèse transitoire" : "Référentiel contractuel · synthèse API"}</span>
            <h2>Matrices comptables par contrat</h2>
            <p>La facture hérite de la version active ; seules les exceptions sont corrigées par la comptabilité.</p>
          </div>
          <div className="po2-prototype-actions">
            <Button variant="ghost">↓ Exporter XLSX</Button>
          </div>
        </div>
        <div className="po2-proto-matrix-contracts">
          {matrices.map((matrix) => (
            <article key={matrix.id}>
              <div className="po2-proto-matrix-card-top">
                <span className="po2-proto-supplier-logo">{supplierInitials(matrix.supplier)}</span>
                <div>
                  <strong>{matrix.supplier}</strong>
                  <small>{matrix.contract}</small>
                </div>
                <StatusBadge tone={matrix.status === "Active" ? "ok" : matrix.status === "À valider" ? "warn" : "bad"}>{matrix.status}</StatusBadge>
              </div>
              <div className="po2-proto-matrix-stats">
                <span><b>{matrix.coverage}</b> couverture</span>
                <span><b>{matrix.exceptions}</b></span>
              </div>
              <a href="/refonte-v1/matrices">Éditer la matrice →</a>
            </article>
          ))}
        </div>
      </section>

      <div className="po2-proto-toolbar-row">
        <label>
          <span>⌕</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Numéro, fournisseur, site ou marché" />
        </label>
        <select value={supplierFilter} onChange={(e) => setSupplierFilter(e.target.value)} aria-label="Filtrer fournisseur">
          <option value="all">Tous les fournisseurs</option>
          {suppliers.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={matrixFilter} onChange={(e) => setMatrixFilter(e.target.value)} aria-label="Filtrer imputation">
          <option value="all">Toutes les imputations</option>
          <option value="validee">Validée</option>
          <option value="proposee">Proposée</option>
          <option value="a_completer">À compléter</option>
          <option value="a_arbitrer">À arbitrer</option>
        </select>
      </div>

      <section className="po2-proto-panel po2-proto-table-panel">
        <table>
          <thead>
            <tr>
              <th>Fournisseur / facture</th>
              <th>Site</th>
              <th>Marché</th>
              <th>Montant TTC</th>
              <th>Émission</th>
              <th>Matrice</th>
              <th>Décision</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((invoice) => (
              <tr key={invoice.stableId} className={invoice.stableId === selectedInvoice?.stableId ? "active" : ""} onClick={() => setSelectedInvoice(invoice)}>
                <td>
                  <div className="po2-proto-supplier">
                    <span className="po2-proto-supplier-logo">{supplierInitials(invoice.supplier)}</span>
                    <span><b>{invoice.supplier}</b><small>{invoice.invoiceNumber}</small></span>
                  </div>
                </td>
                <td>{invoice.siteDetail ? <span><b>{invoice.siteLabel}</b><small className="po2-muted-line">{invoice.siteDetail}</small></span> : invoice.siteLabel}</td>
                <td>{invoice.marketLabel ?? invoice.contractLabel}</td>
                <td><strong>{invoice.amountTtcLabel}</strong></td>
                <td>{invoice.issuedAt ?? "—"}</td>
                <td><StatusBadge tone={matrixTone(invoice.matrixStatus)}>{matrixLabel(invoice.matrixStatus)}</StatusBadge></td>
                <td><StatusBadge tone={invoiceTone(invoice.status)}>{invoiceLabel(invoice.status)}</StatusBadge></td>
                <td className="po2-proto-open-cell">Ouvrir →</td>
              </tr>
            ))}
            {filteredRows.length === 0 ? (
              <tr><td colSpan={8} className="po2-muted-line">Aucune facture ne correspond aux filtres.</td></tr>
            ) : null}
          </tbody>
        </table>
      </section>

      <Drawer
        open={Boolean(selectedInvoice)}
        title={selectedInvoice ? selectedInvoice.supplier + " · " + selectedInvoice.invoiceNumber : "Facture"}
        eyebrow="Dossier facture"
        description={selectedInvoice ? selectedInvoice.siteLabel + " · " + (selectedInvoice.marketLabel ?? selectedInvoice.contractLabel) : undefined}
        onClose={() => setSelectedInvoice(null)}
      >
        {selectedInvoice ? (
          <div className="po2-proto-dossier">
            <div className="po2-proto-dossier-kpis">
              <div><span>Montant TTC</span><b>{selectedInvoice.amountTtcLabel}</b></div>
              <div><span>Échéance</span><b>{selectedInvoice.dueAt ?? "À définir"}</b></div>
              <div><span>Statut</span><b>{invoiceLabel(selectedInvoice.status)}</b></div>
            </div>

            {currentVerdict ? (
              <div className="po2-proto-verdict" style={currentVerdict.tone === "bad" ? { background: "#f4d4d4" } : currentVerdict.tone === "warn" ? { background: "#f6e7c8" } : undefined}>
                <span style={currentVerdict.tone === "bad" ? { background: "#d3584f" } : currentVerdict.tone === "warn" ? { background: "#d9a13a" } : undefined}>{currentVerdict.tone === "bad" ? "!" : currentVerdict.tone === "warn" ? "•" : "✓"}</span>
                <p><b>Verdict :</b> {currentVerdict.text}</p>
              </div>
            ) : null}

            <h3>Trace de contrôle</h3>
            <div className="po2-proto-control-list">
              {selectedInvoice.proofs.length > 0 ? selectedInvoice.proofs.map((proof) => (
                <article key={proof.label + "-" + proof.method}>
                  <StatusBadge tone={proof.status === "bad" ? "bad" : proof.status === "warn" ? "warn" : proof.status === "ok" ? "ok" : "info"}>{proof.status.toUpperCase()}</StatusBadge>
                  <div><strong>{proof.label}</strong><small>{proof.method}{proof.reference ? " · réf. " + proof.reference : ""}</small></div>
                </article>
              )) : (
                <article>
                  <StatusBadge tone="info">INFO</StatusBadge>
                  <div><strong>Trace à construire</strong><small>Le contrôle fournira les preuves ligne par ligne.</small></div>
                </article>
              )}
            </div>

            <h3>Imputation proposée</h3>
            {selectedInvoice.source === "mock" ? (
              <p className="po2-muted-line">Facture de démonstration : imputation simulée.</p>
            ) : snapshotPayload ? (
              <>
                <div className="po2-proto-accounting-grid">
                  <article><span>Lignes imputées</span><strong>{snapshotPayload.matched_lines}/{snapshotPayload.total_lines}</strong></article>
                  <article><span>Exceptions</span><strong>{snapshotExceptions.length || "Aucune"}</strong></article>
                  {dominantAxes(snapshotPayload).map((axis, i) => (
                    <article key={axis + i}><span>Nature {i + 1}</span><strong>{axis}</strong></article>
                  ))}
                </div>
                {snapshotExceptions.length > 0 ? (
                  <div className="po2-proto-control-list" style={{ marginTop: ".55rem" }}>
                    {snapshotExceptions.slice(0, 4).map((ex, i) => (
                      <article key={i}>
                        <StatusBadge tone="bad">EXCEPT.</StatusBadge>
                        <div><strong>{ex.billed_item ?? "Ligne"}</strong><small>{ex.reason ?? "Exception"}</small></div>
                      </article>
                    ))}
                  </div>
                ) : null}
                <details style={{ marginTop: ".6rem" }}>
                  <summary style={{ cursor: "pointer", fontWeight: 700, fontSize: ".82rem" }}>Détail ligne par ligne ({snapshotPayload.lines.length})</summary>
                  <div className="po2-proto-control-list" style={{ marginTop: ".5rem" }}>
                    {snapshotPayload.lines.map((line) => (
                      <article key={line.line_index} style={{ gridTemplateColumns: "1fr" }}>
                        <div>
                          <strong>{line.billed_item ?? "Ligne " + (line.line_index + 1)} · {eur(line.amount)}</strong>
                          {line.imputations.length > 0 ? line.imputations.map((imp, i) => (
                            <small key={i}>
                              {[imp.nature, imp.service, imp.function, imp.antenna, imp.operation].filter(Boolean).join(" · ") || imp.label || "Axes non précisés"}
                              {imp.allocation_percent != null ? ` — ${imp.allocation_percent}% (${eur(imp.amount_allocated)})` : ""}
                            </small>
                          )) : <small className="po2-muted-line">Non imputée</small>}
                        </div>
                      </article>
                    ))}
                  </div>
                </details>
              </>
            ) : (
              <p className="po2-muted-line">Pas encore imputée. Appliquez la matrice ci-dessous.</p>
            )}

            <div className="po2-proto-decision-box">
              <span>Décision recommandée</span>
              <strong>{recommendation(selectedInvoice, snapshot.data?.status, snapshotExceptions.length)}</strong>
            </div>

            {selectedInvoice.source !== "mock" ? (
              <div className="po2-invoice-actions" style={{ marginTop: ".85rem" }}>
                {isAutoMatched ? (
                  <p className="po2-muted-line">Matrice liée automatiquement au contrat {effectiveContract?.contract_code ?? selectedInvoice.contractCode} · {effectiveContract?.supplier ?? "DALKIA"}</p>
                ) : (
                  <label className="po2-invoice-actions__field">
                    <span>{selectedInvoice.contractCode ? `Contrat ${selectedInvoice.contractCode} non reconnu — choisir une matrice` : "Matrice contrat"}</span>
                    <select value={effectiveContractId ?? ""} onChange={(event) => setMatrixContractId(event.target.value ? Number(event.target.value) : null)}>
                      <option value="">— choisir une matrice —</option>
                      {matrixContracts.map((contract) => (
                        <option key={contract.id} value={contract.id}>{contract.supplier} · {contract.contract_code ?? contract.contract_label ?? "#" + contract.id}</option>
                      ))}
                    </select>
                  </label>
                )}
              </div>
            ) : null}

            <div className="po2-proto-action-stack">
              {selectedInvoice.source !== "mock" ? (
                <>
                  <Button onClick={() => effectiveContractId && actions.apply.mutate({ matrix_contract_id: effectiveContractId })} disabled={!effectiveContractId || actions.apply.isPending}>
                    {actions.apply.isPending ? "Application…" : snapshotPayload ? "Réappliquer la matrice" : "Appliquer la matrice"}
                  </Button>
                  <Button variant="secondary" onClick={() => actions.validate.mutate()} disabled={snapshot.data?.status !== "proposed" || blockingExceptions || actions.validate.isPending}>
                    {actions.validate.isPending ? "Validation…" : "Valider l’imputation"}
                  </Button>
                  <Button variant="secondary" onClick={() => actions.exportFinance.mutate()} disabled={!(snapshot.data?.status === "validated" || snapshot.data?.status === "manual_override") || actions.exportFinance.isPending}>
                    {actions.exportFinance.isPending ? "Transmission…" : "Exporter aux finances"}
                  </Button>
                </>
              ) : null}
              <Button variant="danger" disabled title="Génération du courrier de réclamation à venir">Préparer une réclamation (à venir)</Button>
              <Button variant="ghost" disabled title="Correction manuelle d'imputation à venir">Corriger l’imputation (à venir)</Button>
              <Button variant="ghost" disabled title="Demande de correction de la matrice à venir">Demander correction matrice (à venir)</Button>
            </div>

            {actionError(actions.apply.error) ? <p className="po2-action-error">Application : {actionError(actions.apply.error)}</p> : null}
            {actionError(actions.validate.error) ? <p className="po2-action-error">Validation : {actionError(actions.validate.error)}</p> : null}
            {actionError(actions.exportFinance.error) ? <p className="po2-action-error">Export : {actionError(actions.exportFinance.error)}</p> : null}
            {actions.exportFinance.isSuccess ? <p className="po2-muted-line">Transmise aux finances ✓</p> : null}

            <h3>Historique</h3>
            <div className="po2-proto-control-list">
              {selectedInvoice.issuedAt ? <article><StatusBadge tone="info">IMPORT</StatusBadge><div><strong>Facture importée</strong><small>Émise le {selectedInvoice.issuedAt}</small></div></article> : null}
              {snapshot.data?.status ? <article><StatusBadge tone="info">MATRICE</StatusBadge><div><strong>Snapshot {snapshotLabel(snapshot.data.status).toLowerCase()}</strong><small>{snapshot.data.matrix_version_id ? "Version matrice #" + snapshot.data.matrix_version_id : "—"}</small></div></article> : null}
              {snapshot.data?.validated_at ? <article><StatusBadge tone="ok">VALIDÉ</StatusBadge><div><strong>Imputation validée</strong><small>{snapshot.data.validated_at}</small></div></article> : null}
              {snapshot.data?.exported_at ? <article><StatusBadge tone="ok">FINANCE</StatusBadge><div><strong>Transmis aux finances</strong><small>{snapshot.data.exported_at}</small></div></article> : null}
            </div>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
