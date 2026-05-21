import { useMemo, useState } from "react";
import type { EnergyInvoiceImport } from "../lib/api";
import {
  INVOICE_ISSUE_FAMILY_LABEL,
  invoiceIssueFamily,
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
  code: string;
  family: InvoiceIssueFamily;
  severity: string;
  message: string;
  invoiceIds: Set<number>;
  invoiceNumbers: Set<string>;
  count: number;
};

type Props = {
  invoiceImports: EnergyInvoiceImport[];
  filters: InvoiceSupplierReportFilters;
  onClose: () => void;
};

function formatShortDate(value: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(new Date(value));
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value);
}

function formatGeneratedAt() {
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeStyle: "short" }).format(new Date());
}

function issueSeverityLabel(severity: string) {
  return severity === "error" ? "Erreur" : severity === "warning" ? "Alerte" : severity;
}

function invoiceReference(invoiceImport: EnergyInvoiceImport) {
  return invoiceImport.invoice_number ?? invoiceImport.original_filename;
}

function selectedIssues(invoiceImport: EnergyInvoiceImport, filters: InvoiceSupplierReportFilters) {
  return invoiceImport.control_issues.filter((issue) => {
    const family = invoiceIssueFamily(issue);
    if (filters.issueFamilies.length > 0 && !filters.issueFamilies.includes(family)) return false;
    if (filters.issueCodes.length > 0 && !filters.issueCodes.includes(issue.code)) return false;
    return true;
  });
}

function issueSummary(invoiceImport: EnergyInvoiceImport, filters: InvoiceSupplierReportFilters) {
  const families = Array.from(new Set(selectedIssues(invoiceImport, filters).map((issue) => invoiceIssueFamily(issue))));
  return families.map((family) => INVOICE_ISSUE_FAMILY_LABEL[family]).join(", ");
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

function groupIssues(invoiceImports: EnergyInvoiceImport[], filters: InvoiceSupplierReportFilters) {
  const groups = new Map<string, IssueGroup>();

  for (const invoiceImport of invoiceImports) {
    for (const issue of selectedIssues(invoiceImport, filters)) {
      const family = invoiceIssueFamily(issue);
      const key = `${family}:${issue.code}`;
      const group = groups.get(key) ?? {
        code: issue.code,
        family,
        severity: issue.severity,
        message: issue.message,
        invoiceIds: new Set<number>(),
        invoiceNumbers: new Set<string>(),
        count: 0,
      };
      group.count += 1;
      group.invoiceIds.add(invoiceImport.id);
      group.invoiceNumbers.add(invoiceReference(invoiceImport));
      if (group.severity !== "error" && issue.severity === "error") {
        group.severity = issue.severity;
      }
      groups.set(key, group);
    }
  }

  return Array.from(groups.values()).sort(
    (a, b) =>
      INVOICE_ISSUE_FAMILY_LABEL[a.family].localeCompare(INVOICE_ISSUE_FAMILY_LABEL[b.family], "fr") ||
      b.invoiceIds.size - a.invoiceIds.size ||
      a.code.localeCompare(b.code, "fr"),
  );
}

export function InvoiceSupplierReport({ invoiceImports, filters, onClose }: Props) {
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
  const issueGroups = useMemo(() => groupIssues(invoiceImports, filters), [filters, invoiceImports]);
  const filtersSummary = useMemo(() => activeFilters(filters), [filters]);
  const totalTtc = invoiceImports.reduce((total, invoiceImport) => total + (invoiceImport.total_ttc ?? 0), 0);
  const errorCount = invoiceImports.reduce(
    (total, invoiceImport) => total + selectedIssues(invoiceImport, filters).filter((issue) => issue.severity === "error").length,
    0,
  );
  const warningCount = invoiceImports.reduce(
    (total, invoiceImport) => total + selectedIssues(invoiceImport, filters).filter((issue) => issue.severity === "warning").length,
    0,
  );
  const defaultRecipient = suppliers.length === 1 ? suppliers[0] : "Fournisseur d'energie";
  const [senderName, setSenderName] = useState("Collectivite");
  const [recipientName, setRecipientName] = useState(defaultRecipient);
  const [subject, setSubject] = useState("Demande d'explications sur des points de controle de factures energie");
  const [context, setContext] = useState(
    "Dans le cadre de notre revue des factures d'energie, plusieurs points ont ete identifies par nos controles. Ils sont transmis pour clarification : ils peuvent correspondre a une anomalie de facturation, a une donnee contractuelle manquante ou a une mauvaise interpretation de notre part.",
  );
  const [request, setRequest] = useState(
    "Merci de nous confirmer, pour chaque point liste ci-dessous, la regle de facturation appliquee, les donnees contractuelles ou reglementaires qui la justifient et, le cas echeant, la correction ou la piece explicative a prendre en compte.",
  );

  return (
    <div className="invoice-report-backdrop" role="dialog" aria-modal="true" aria-label="Rapport fournisseur factures">
      <section className="invoice-report-panel">
        <header className="invoice-report-toolbar invoice-report-no-print">
          <div>
            <p className="field-label">Rapport fournisseur</p>
            <strong>{invoiceImports.length} facture{invoiceImports.length > 1 ? "s" : ""} avec points a clarifier</strong>
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
                  <strong>{invoiceImports.length}</strong>
                  <span>Factures concernees</span>
                </div>
                <div>
                  <strong>{issueGroups.length}</strong>
                  <span>Types de points</span>
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
              <table>
                <thead>
                  <tr>
                    <th>Point</th>
                    <th>Niveau</th>
                    <th>Factures</th>
                    <th>Signalements</th>
                  </tr>
                </thead>
                <tbody>
                  {issueGroups.map((issue) => (
                    <tr key={`${issue.family}:${issue.code}`}>
                      <td>
                        <strong>{INVOICE_ISSUE_FAMILY_LABEL[issue.family]}</strong>
                        <span>{issue.message}</span>
                        <small>{issue.code}</small>
                      </td>
                      <td>{issueSeverityLabel(issue.severity)}</td>
                      <td>
                        <strong>{issue.invoiceIds.size}</strong>
                        <small>{Array.from(issue.invoiceNumbers).slice(0, 4).join(", ")}{issue.invoiceNumbers.size > 4 ? "..." : ""}</small>
                      </td>
                      <td>{issue.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section>
              <h2>Factures concernees</h2>
              <table>
                <thead>
                  <tr>
                    <th>Facture</th>
                    <th>Periode</th>
                    <th>Titulaire</th>
                    <th>Regroupement</th>
                    <th>Points a clarifier</th>
                  </tr>
                </thead>
                <tbody>
                  {invoiceImports.map((invoiceImport) => (
                    <tr key={invoiceImport.id}>
                      <td>
                        <strong>{invoiceReference(invoiceImport)}</strong>
                        <span>{formatShortDate(invoiceImport.invoice_date)}</span>
                      </td>
                      <td>
                        {formatShortDate(invoiceImport.period_start)} au {formatShortDate(invoiceImport.period_end)}
                      </td>
                      <td>{invoiceImport.contract_holder ?? "-"}</td>
                      <td>{invoiceImport.regroupement ?? "-"}</td>
                      <td>{issueSummary(invoiceImport, filters)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <footer>
              Ce rapport rassemble des points de controle a expliquer. Il ne vaut pas, a lui seul, constat definitif
              d'erreur de facturation sans retour fournisseur et verification des pieces contractuelles associees.
            </footer>
          </article>
        </div>
      </section>
    </div>
  );
}
