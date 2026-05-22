import { useEffect, useMemo, useState } from "react";
import type {
  EnergyInvoiceImport,
  EnergyInvoiceImportDetail,
  EnergyInvoiceLine,
  EnergyInvoiceSite,
} from "../lib/api";
import { fetchEnergyInvoiceImport } from "../lib/api";
import {
  INVOICE_ISSUE_FAMILY_DETAIL,
  INVOICE_ISSUE_FAMILY_LABEL,
  invoiceIssueFamily,
  isInternalControlLimit,
  isSupplierReportIssue,
} from "../lib/invoiceIssues";
import type { InvoiceIssueFamily } from "../lib/invoiceIssues";

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
  // On garde uniquement si ça ressemble à un PRM (14 chiffres pour ENEDIS)
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
  return filteredIssues(invoiceImport, filters).filter(isSupplierReportIssue);
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
  if (filters.issueFamilies.length > 0) {
    values.push(`Categorie : ${filters.issueFamilies.map((family) => INVOICE_ISSUE_FAMILY_LABEL[family]).join(", ")}`);
  }
  if (filters.issueCodes.length > 0) values.push(`Type : ${filters.issueCodes.join(", ")}`);
  return values;
}

// Agrège les issues PAR FAMILLE (pas par code) pour éviter le bruit.
// Un seul bloc "Prix contractuels" listant tous les codes (BPU_PRICE_MISMATCH, BPU_TARIFF_POSTE_INCONSISTENCY...)
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

// ── Recalcul BPU ─────────────────────────────────────────────────────────────
// Pour chaque message BPU_PRICE_MISMATCH, parse prix facturé et prix BPU (€/MWh),
// puis multiplie par la quantité de la ligne facture correspondante.

type BpuDeltaLine = {
  invoiceId: number;
  invoiceRef: string;
  scope: string | null;
  prm: string | null;
  invoicePriceEurMwh: number;
  bpuPriceEurMwh: number;
  deltaEurMwh: number;
  quantityMwh: number | null;
  deltaTotalEur: number | null;
  postLabel: string;
  matchedLineLabel: string | null;
};

const BPU_PRICE_REGEX =
  /Prix facture\s+([\d.,]+)\s*EUR\/MWh\s+different du BPU\s+(?:historique\s+)?([\d.,]+)\s*EUR\/MWh(?:[^.]*?pour\s+([^.\s][^.]*?))?[.\s(]/i;

function parseNumber(value: string): number {
  return Number(value.replace(",", "."));
}

function quantityToMwh(line: EnergyInvoiceLine): number | null {
  if (line.quantity == null) return null;
  const unit = (line.quantity_unit || "").toLowerCase();
  if (unit.includes("mwh")) return line.quantity;
  if (unit.includes("kwh")) return line.quantity / 1000;
  // Si pas d'unité explicite mais prix en €/MWh et amount existe, on peut déduire
  return null;
}

function findMatchingInvoiceLine(
  site: EnergyInvoiceSite,
  invoicePriceEurMwh: number,
): EnergyInvoiceLine | null {
  const lines = site.invoice_lines || [];
  // Priorité aux lignes énergie (composant normalisé contenant "ENERGIE" ou "MOLECULE")
  const energyLines = lines.filter((line) => {
    const comp = (line.normalized_component || "").toUpperCase();
    return comp.includes("ENERGIE") || comp.includes("MOLECULE") || comp.includes("ABONNEMENT") === false;
  });
  // Cherche celle dont unit_price_ht * 1000 ≈ invoicePriceEurMwh (tolérance 0.5)
  for (const line of energyLines) {
    if (line.unit_price_ht == null) continue;
    const linePriceMwh = line.unit_price_ht * 1000;
    if (Math.abs(linePriceMwh - invoicePriceEurMwh) < 0.5) return line;
  }
  // Fallback : 1re ligne énergie
  return energyLines[0] ?? null;
}

function siteMatchesScope(site: EnergyInvoiceSite, scope: string | null): boolean {
  if (!scope) return false;
  const prm = extractPrm(scope);
  if (prm && site.prm_id === prm) return true;
  // Fallback : FIC dans le scope
  const ficMatch = scope.match(/FIC\s+(\d+)/i);
  if (ficMatch && site.fic_number === ficMatch[1]) return true;
  return false;
}

function computeBpuDeltas(
  invoiceImport: EnergyInvoiceImport,
  detail: EnergyInvoiceImportDetail | undefined,
): BpuDeltaLine[] {
  const results: BpuDeltaLine[] = [];
  const sites = detail?.analysis_result?.sites || [];
  const bpuIssues = invoiceImport.control_issues.filter(
    (issue) => issue.code === "BPU_PRICE_MISMATCH",
  );
  for (const issue of bpuIssues) {
    const match = issue.message.match(BPU_PRICE_REGEX);
    if (!match) continue;
    const invoicePrice = parseNumber(match[1]);
    const bpuPrice = parseNumber(match[2]);
    const postLabel = (match[3] || "").trim().replace(/\.$/, "") || "(non précisé)";
    const deltaEurMwh = invoicePrice - bpuPrice;

    let quantityMwh: number | null = null;
    let matchedLineLabel: string | null = null;
    if (detail) {
      const site = sites.find((s) => siteMatchesScope(s, issue.scope));
      if (site) {
        const line = findMatchingInvoiceLine(site, invoicePrice);
        if (line) {
          quantityMwh = quantityToMwh(line);
          matchedLineLabel = line.label || line.normalized_component || null;
        }
      }
    }
    const deltaTotalEur = quantityMwh != null ? deltaEurMwh * quantityMwh : null;
    results.push({
      invoiceId: invoiceImport.id,
      invoiceRef: invoiceReference(invoiceImport),
      scope: issue.scope,
      prm: extractPrm(issue.scope),
      invoicePriceEurMwh: invoicePrice,
      bpuPriceEurMwh: bpuPrice,
      deltaEurMwh,
      quantityMwh,
      deltaTotalEur,
      postLabel,
      matchedLineLabel,
    });
  }
  return results;
}

// ── Extraction PRM par facture pour la colonne "Factures concernées" ──────────

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

  // ── Fetch détails des factures concernées par BPU pour le recalcul ─────────
  const bpuInvoiceImports = useMemo(
    () =>
      reportInvoiceImports.filter((invoiceImport) =>
        selectedIssues(invoiceImport, filters).some(
          (issue) => issue.code === "BPU_PRICE_MISMATCH",
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

  // Calcule les écarts BPU consolidés
  const bpuDeltas = useMemo(() => {
    const all: BpuDeltaLine[] = [];
    for (const invoiceImport of bpuInvoiceImports) {
      const detail = detailsByImportId[invoiceImport.id];
      all.push(...computeBpuDeltas(invoiceImport, detail));
    }
    return all;
  }, [bpuInvoiceImports, detailsByImportId]);

  const bpuTotalEstimatedEur = useMemo(
    () => bpuDeltas.reduce((sum, d) => sum + (d.deltaTotalEur ?? 0), 0),
    [bpuDeltas],
  );
  const bpuLinesWithoutQuantity = bpuDeltas.filter((d) => d.quantityMwh == null).length;
  const hasBpuSection = bpuDeltas.length > 0;

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
                  {excludedInternalIssueCount} limite{excludedInternalIssueCount > 1 ? "s" : ""} de controle exclue
                  {excludedInternalIssueCount > 1 ? "s" : ""}
                </strong>
                <p>
                  Ces points restent internes : reference BPU ou ENEDIS absente, controle partiel ou perimetre local
                  incomplet, sans ecart fournisseur demontre.
                </p>
                <span>
                  {Array.from(new Set(excludedInternalGroups.flatMap((group) => Array.from(group.codes)))).join(", ")}
                </span>
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
                <p>Aucun ecart fournisseur retenu avec les filtres appliques.</p>
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
                  Calcul indicatif base sur le delta (prix facture &minus; prix BPU contractuel) multiplie
                  par la quantite energie de la ligne facture correspondante. A consolider avec le fournisseur.
                </p>
                {bpuLoading && <p>Chargement des details factures...</p>}
                {bpuError && <p className="invoice-report-warning">{bpuError}</p>}
                <table className="invoice-report-bpu-table">
                  <thead>
                    <tr>
                      <th>Facture / PRM</th>
                      <th>Poste</th>
                      <th>Prix facture</th>
                      <th>Prix BPU</th>
                      <th>Delta</th>
                      <th>Quantite</th>
                      <th>Ecart estime HT</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bpuDeltas.map((delta, idx) => (
                      <tr key={`${delta.invoiceId}-${idx}`}>
                        <td>
                          <strong>{delta.invoiceRef}</strong>
                          <span>{delta.prm ?? delta.scope ?? "-"}</span>
                        </td>
                        <td>{delta.postLabel}</td>
                        <td>{delta.invoicePriceEurMwh.toFixed(2)} EUR/MWh</td>
                        <td>{delta.bpuPriceEurMwh.toFixed(2)} EUR/MWh</td>
                        <td className={delta.deltaEurMwh > 0 ? "invoice-report-delta-over" : "invoice-report-delta-under"}>
                          {delta.deltaEurMwh > 0 ? "+" : ""}
                          {delta.deltaEurMwh.toFixed(2)} EUR/MWh
                        </td>
                        <td>{delta.quantityMwh != null ? `${delta.quantityMwh.toFixed(3)} MWh` : "non rattachee"}</td>
                        <td className={delta.deltaTotalEur != null && delta.deltaTotalEur > 0 ? "invoice-report-delta-over" : "invoice-report-delta-under"}>
                          {delta.deltaTotalEur != null ? formatCurrency(delta.deltaTotalEur) : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan={6}>
                        <strong>Total ecart estime HT</strong>
                        {bpuLinesWithoutQuantity > 0 && (
                          <span> ({bpuLinesWithoutQuantity} ligne{bpuLinesWithoutQuantity > 1 ? "s" : ""} sans quantite rattachee)</span>
                        )}
                      </td>
                      <td className={bpuTotalEstimatedEur > 0 ? "invoice-report-delta-over" : "invoice-report-delta-under"}>
                        <strong>{formatCurrency(bpuTotalEstimatedEur)}</strong>
                      </td>
                    </tr>
                  </tfoot>
                </table>
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
                  Les ecarts BPU chiffres sont indicatifs et doivent etre rapproches des pieces contractuelles
                  applicables a la periode (lots BPU, options tarifaires, dates d'effet).
                </>
              )}
            </footer>
          </article>
        </div>
      </section>
    </div>
  );
}
