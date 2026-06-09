import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  downloadInvoiceLiaison,
  fetchEnergyInvoiceImport,
  fetchInvoiceCodification,
  updateEnergyInvoiceDecision,
} from "../lib/api";
import type {
  EnergyInvoiceDecisionPayload,
  EnergyInvoiceImport,
  EnergyInvoiceLine,
  EnergyInvoiceSite,
} from "../lib/api";
import {
  INVOICE_ISSUE_FAMILY_DETAIL as FAMILY_DETAIL,
  INVOICE_ISSUE_FAMILY_LABEL as FAMILY_LABEL,
  invoiceIssueFamily as issueFamily,
  isInternalControlLimit,
  isSupplierReportIssue,
} from "../lib/invoiceIssues";
import type { InvoiceControlIssue as ControlIssue, InvoiceIssueFamily as IssueFamily } from "../lib/invoiceIssues";
import { useAuth } from "../providers/AuthProvider";

const CONTROL_STATUS_LABEL: Record<string, string> = {
  valid: "Valide",
  review: "A controler",
  invalid: "Invalide",
  not_checked: "Non controlee",
};

const DECISION_STATUS_LABEL: Record<EnergyInvoiceDecisionPayload["decision_status"], string> = {
  to_review: "A verifier",
  approved: "Validee",
  rejected: "Refusee",
  dispute_sent: "Contestation envoyee",
};

const ISSUE_SEVERITY_LABEL: Record<string, string> = {
  error: "Erreur",
  warning: "Alerte",
};

type SummaryTone = "ok" | "warning" | "error";

type HumanSummaryIssueDetail = {
  severity: string;
  message: string;
  scope: string | null;
  count: number;
};

type HumanSummaryItem = {
  title: string;
  detail: string;
  tone: SummaryTone;
  issueDetails?: HumanSummaryIssueDetail[];
  hiddenIssueCount?: number;
};

function formatShortDate(value: string | null | undefined) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(new Date(value));
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value);
}

function formatNumber(value: number | null | undefined, unit = "") {
  if (value === null || value === undefined) return "-";
  return `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 }).format(value)}${unit}`;
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

function decisionBadge(status: string) {
  const statusClass =
    status === "approved"
      ? "badge-green"
      : status === "rejected"
        ? "badge-red"
        : status === "dispute_sent"
          ? "badge-blue"
          : "badge-gray";

  return (
    <span className={`badge ${statusClass}`}>
      {DECISION_STATUS_LABEL[status as EnergyInvoiceDecisionPayload["decision_status"]] ?? status}
    </span>
  );
}

function issueBadge(severity: string) {
  const statusClass = severity === "error" ? "badge-red" : severity === "warning" ? "badge-orange" : "badge-gray";
  return <span className={`badge ${statusClass}`}>{ISSUE_SEVERITY_LABEL[severity] ?? severity}</span>;
}

function recordNumber(record: Record<string, unknown> | undefined, key: string) {
  const value = record?.[key];
  return typeof value === "number" ? value : null;
}

function hasFamilyIssue(issues: ControlIssue[], family: IssueFamily) {
  return issues.some((issue) => issueFamily(issue) === family);
}

function issueCountLabel(count: number, label: string) {
  return `${count} ${label}${count !== 1 ? "s" : ""}`;
}

function networkComponentLabel(component: string | null | undefined) {
  const labels: Record<string, string> = {
    network_counting: "Comptage",
    network_management: "Gestion",
    network_withdrawal: "Soutirage fixe",
    network_variable: "Soutirage variable",
  };
  return labels[component ?? ""] ?? "Autre composante";
}

function severityRank(severity: string) {
  return severity === "error" ? 0 : 1;
}

function buildIssueDetails(issues: ControlIssue[], maxDetails = 6) {
  const grouped = new Map<string, HumanSummaryIssueDetail>();

  for (const issue of issues) {
    const key = `${issue.severity}|${issue.message}|${issue.scope ?? ""}`;
    const current =
      grouped.get(key) ??
      {
        severity: issue.severity,
        message: issue.message,
        scope: issue.scope,
        count: 0,
      };
    current.count += 1;
    grouped.set(key, current);
  }

  const details = Array.from(grouped.values()).sort(
    (a, b) => severityRank(a.severity) - severityRank(b.severity) || b.count - a.count || a.message.localeCompare(b.message, "fr"),
  );
  const visibleDetails = details.slice(0, maxDetails);
  const hiddenIssueCount = details.slice(maxDetails).reduce((total, detail) => total + detail.count, 0);

  return { visibleDetails, hiddenIssueCount };
}

function buildAttentionItems(issues: ControlIssue[]): HumanSummaryItem[] {
  const counts = new Map<IssueFamily, { errors: number; warnings: number }>();
  const groupedIssues = new Map<IssueFamily, ControlIssue[]>();
  for (const issue of issues) {
    const family = issueFamily(issue);
    const current = counts.get(family) ?? { errors: 0, warnings: 0 };
    if (issue.severity === "error") {
      current.errors += 1;
    } else {
      current.warnings += 1;
    }
    counts.set(family, current);
    const familyIssues = groupedIssues.get(family) ?? [];
    familyIssues.push(issue);
    groupedIssues.set(family, familyIssues);
  }

  return Array.from(counts.entries())
    .sort(([, a], [, b]) => b.errors - a.errors || b.warnings - a.warnings)
    .map(([family, count]) => {
      const parts = [
        count.errors > 0 ? issueCountLabel(count.errors, "erreur") : null,
        count.warnings > 0 ? issueCountLabel(count.warnings, "alerte") : null,
      ].filter(Boolean);
      const { visibleDetails, hiddenIssueCount } = buildIssueDetails(groupedIssues.get(family) ?? []);
      return {
        title: FAMILY_LABEL[family],
        detail: `${parts.join(", ")}. ${FAMILY_DETAIL[family]}`,
        tone: count.errors > 0 ? "error" : "warning",
        issueDetails: visibleDetails,
        hiddenIssueCount,
      };
    });
}

function buildOkItems(
  invoiceImport: EnergyInvoiceImport,
  issues: ControlIssue[],
  summaries: {
    bpu?: Record<string, unknown>;
    turpe?: Record<string, unknown>;
    taxes?: Record<string, unknown>;
    periods?: Record<string, unknown>;
    consumption?: Record<string, unknown>;
    power?: Record<string, unknown>;
  },
): HumanSummaryItem[] {
  const okItems: HumanSummaryItem[] = [];

  if (invoiceImport.invoice_number && invoiceImport.invoice_date && invoiceImport.total_ttc !== null && !hasFamilyIssue(issues, "document")) {
    okItems.push({
      title: "Facture identifiee",
      detail: "Numero, date, fournisseur et montant global ont ete lus.",
      tone: "ok",
    });
  }

  const bpuLines = recordNumber(summaries.bpu, "checked_lines");
  if (bpuLines && bpuLines > 0 && !hasFamilyIssue(issues, "bpu")) {
    okItems.push({
      title: "Prix BPU controles",
      detail: `${formatNumber(bpuLines)} ligne(s) rapprochee(s) sans ecart bloquant.`,
      tone: "ok",
    });
  }

  const turpeLines = recordNumber(summaries.turpe, "checked_lines");
  if (turpeLines && turpeLines > 0 && !hasFamilyIssue(issues, "turpe")) {
    okItems.push({
      title: "TURPE controle",
      detail: `${formatNumber(turpeLines)} composante(s) verifiee(s).`,
      tone: "ok",
    });
  }

  const taxSites = recordNumber(summaries.taxes, "checked_sites");
  if (taxSites && taxSites > 0 && !hasFamilyIssue(issues, "taxes")) {
    okItems.push({
      title: "Taxes coherentes",
      detail: `${formatNumber(taxSites)} FIC avec totaux HT, TVA et TTC coherents.`,
      tone: "ok",
    });
  }

  const periodSites = recordNumber(summaries.periods, "checked_sites");
  if (periodSites && periodSites > 0 && !hasFamilyIssue(issues, "periods")) {
    okItems.push({
      title: "Periodes coherentes",
      detail: `${formatNumber(periodSites)} FIC controlees sans trou ni chevauchement detecte.`,
      tone: "ok",
    });
  }

  const consumptionSites = recordNumber(summaries.consumption, "checked_sites");
  if (consumptionSites && consumptionSites > 0 && !hasFamilyIssue(issues, "consumption")) {
    okItems.push({
      title: "Consommation rapprochee",
      detail: `${formatNumber(consumptionSites)} PRM rapproches avec les donnees ENEDIS disponibles.`,
      tone: "ok",
    });
  }

  const powerSites = recordNumber(summaries.power, "checked_sites");
  if (powerSites && powerSites > 0 && !hasFamilyIssue(issues, "power")) {
    okItems.push({
      title: "Puissance rapprochee",
      detail: `${formatNumber(powerSites)} PRM controles sur puissance facturee, contrat ou donnees ENEDIS.`,
      tone: "ok",
    });
  }

  if (okItems.length === 0) {
    okItems.push({
      title: "Extraction disponible",
      detail: "Les donnees principales sont visibles dans les tableaux de detail.",
      tone: "ok",
    });
  }

  return okItems.slice(0, 6);
}

function buildHumanSummary(
  invoiceImport: EnergyInvoiceImport,
  issues: ControlIssue[],
  summaries: {
    bpu?: Record<string, unknown>;
    turpe?: Record<string, unknown>;
    taxes?: Record<string, unknown>;
    periods?: Record<string, unknown>;
    consumption?: Record<string, unknown>;
    power?: Record<string, unknown>;
  },
) {
  const errorCount = issues.filter((issue) => issue.severity === "error").length;
  const warningCount = issues.filter((issue) => issue.severity === "warning").length;
  const tone: SummaryTone = errorCount > 0 ? "error" : warningCount > 0 ? "warning" : "ok";
  const title =
    tone === "error"
      ? "Facture a corriger avant validation"
      : tone === "warning"
        ? "Facture lisible, mais a verifier"
        : "Facture prete a validation";
  const description =
    tone === "error"
      ? `${issueCountLabel(errorCount, "erreur bloquante")} et ${issueCountLabel(warningCount, "alerte")} detectees.`
      : tone === "warning"
        ? `Aucune erreur bloquante, mais ${issueCountLabel(warningCount, "alerte")} a examiner.`
        : "Aucune anomalie detectee sur les controles disponibles.";
  const nextAction =
    tone === "error"
      ? "Action conseillee : ne pas valider la facture tant que les erreurs bloquantes ne sont pas arbitrees."
      : tone === "warning"
        ? "Action conseillee : relire les alertes, puis valider seulement si elles sont justifiees."
        : "Action conseillee : la facture peut etre validee si le contexte metier confirme le perimetre.";

  return {
    tone,
    title,
    description,
    nextAction,
    okItems: buildOkItems(invoiceImport, issues, summaries),
    attentionItems: buildAttentionItems(issues),
  };
}

export function EnergieInvoiceDetailPage() {
  const { token } = useAuth();
  const params = useParams();
  const qc = useQueryClient();
  const invoiceImportId = Number(params.invoiceImportId);
  const [decisionStatus, setDecisionStatus] =
    useState<EnergyInvoiceDecisionPayload["decision_status"]>("to_review");
  const [decisionComment, setDecisionComment] = useState("");

  const invoiceQuery = useQuery({
    queryKey: ["energy-invoice-import", invoiceImportId],
    queryFn: () => fetchEnergyInvoiceImport(token!, invoiceImportId),
    enabled: !!token && Number.isFinite(invoiceImportId),
  });

  const invoiceImport = invoiceQuery.data;
  const sites = invoiceImport?.analysis_result?.sites ?? [];
  const issues = invoiceImport?.control_report?.issues ?? invoiceImport?.control_issues ?? [];
  const bpuSummary = invoiceImport?.control_report?.bpu;
  const turpeSummary = invoiceImport?.control_report?.turpe;
  const taxesSummary = invoiceImport?.control_report?.taxes;
  const periodsSummary = invoiceImport?.control_report?.periods;
  const consumptionSummary = invoiceImport?.control_report?.consumption;
  const powerSummary = invoiceImport?.control_report?.power;
  const humanSummary = invoiceImport
    ? buildHumanSummary(invoiceImport, issues, {
        bpu: bpuSummary,
        turpe: turpeSummary,
        taxes: taxesSummary,
        periods: periodsSummary,
        consumption: consumptionSummary,
        power: powerSummary,
      })
    : null;

  const invoiceLines = useMemo(
    () =>
      sites.flatMap((site) =>
        (site.invoice_lines ?? []).map((line) => ({
          ...line,
          prm_id: site.prm_id,
          fic_number: site.fic_number,
        })),
      ),
    [sites],
  );
  const networkLines = useMemo(() => invoiceLines.filter((line) => line.family === "network"), [invoiceLines]);
  const turpeIssues = useMemo(() => issues.filter((issue) => issueFamily(issue) === "turpe"), [issues]);
  const supplierTurpeIssues = useMemo(() => turpeIssues.filter(isSupplierReportIssue), [turpeIssues]);
  const internalTurpeIssues = useMemo(() => turpeIssues.filter(isInternalControlLimit), [turpeIssues]);

  useEffect(() => {
    if (!invoiceImport) return;
    setDecisionStatus(invoiceImport.decision_status as EnergyInvoiceDecisionPayload["decision_status"]);
    setDecisionComment(invoiceImport.decision_comment ?? "");
  }, [invoiceImport]);

  const decisionMut = useMutation({
    mutationFn: () =>
      updateEnergyInvoiceDecision(token!, invoiceImportId, {
        decision_status: decisionStatus,
        decision_comment: decisionComment,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["energy-invoice-import", invoiceImportId] });
      qc.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
    },
  });

  const codificationQuery = useQuery({
    queryKey: ["energy-invoice-codification", invoiceImportId],
    queryFn: () => fetchInvoiceCodification(token!, invoiceImportId),
    enabled: !!token && Number.isFinite(invoiceImportId),
  });
  const [liaisonError, setLiaisonError] = useState<string | null>(null);

  if (invoiceQuery.isLoading) {
    return (
      <div className="page">
        <p className="loading-text">Chargement de la facture...</p>
      </div>
    );
  }

  if (invoiceQuery.isError || !invoiceImport) {
    return (
      <div className="page">
        <Link to="/energie/factures" className="secondary-link">
          Retour aux factures
        </Link>
        <p className="error-text">{invoiceQuery.isError ? (invoiceQuery.error as Error).message : "Facture introuvable."}</p>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header page-header-row">
        <div>
          <Link to="/energie/factures" className="secondary-link">
            Retour aux factures
          </Link>
          <h2>Facture {invoiceImport.invoice_number ?? invoiceImport.original_filename}</h2>
          <p className="page-subtitle">
            {invoiceImport.supplier_guess ?? "Fournisseur inconnu"} | {invoiceImport.regroupement ?? "Regroupement absent"} |{" "}
            {formatShortDate(invoiceImport.period_start)} - {formatShortDate(invoiceImport.period_end)}
          </p>
        </div>
        <div className="page-header-actions">
          {controlBadge(invoiceImport)}
          {decisionBadge(invoiceImport.decision_status)}
        </div>
      </div>

      <div className="kpi-row">
        <div className="kpi-card">
          <span className="kpi-label">Montant TTC</span>
          <span className="kpi-value">{formatCurrency(invoiceImport.total_ttc)}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Consommation</span>
          <span className="kpi-value">{formatNumber(invoiceImport.total_consumption_kwh, " kWh")}</span>
        </div>
        <div className="kpi-card kpi-card--info">
          <span className="kpi-label">PRM detectes</span>
          <span className="kpi-value">{invoiceImport.site_count ?? sites.length}</span>
        </div>
        <div className={invoiceImport.control_errors_count > 0 ? "kpi-card kpi-card--alert" : "kpi-card"}>
          <span className="kpi-label">Controles</span>
          <span className="kpi-value">
            {invoiceImport.control_errors_count} / {invoiceImport.control_warnings_count}
          </span>
        </div>
      </div>

      <div className="invoice-detail-grid">
        <section className="invoice-detail-section">
          <h3>Identite facture</h3>
          <dl className="detail-list">
            <dt>Fichier</dt>
            <dd>{invoiceImport.original_filename}</dd>
            <dt>Date facture</dt>
            <dd>{formatShortDate(invoiceImport.invoice_date)}</dd>
            <dt>Import</dt>
            <dd>{formatDateTime(invoiceImport.created_at)}</dd>
            <dt>Analyse</dt>
            <dd>{invoiceImport.analysis_status}</dd>
            <dt>SHA</dt>
            <dd className="cell-mono">{invoiceImport.sha256}</dd>
          </dl>
        </section>

        <section className="invoice-detail-section invoice-decision-panel">
          <h3>Decision</h3>
          <label className="field-label" htmlFor="invoice-decision-status">
            Statut
          </label>
          <select
            id="invoice-decision-status"
            className="form-input"
            value={decisionStatus}
            onChange={(e) => setDecisionStatus(e.target.value as EnergyInvoiceDecisionPayload["decision_status"])}
          >
            <option value="to_review">A verifier</option>
            <option value="approved">Validee</option>
            <option value="rejected">Refusee</option>
            <option value="dispute_sent">Contestation envoyee</option>
          </select>
          <label className="field-label" htmlFor="invoice-decision-comment">
            Commentaire
          </label>
          <textarea
            id="invoice-decision-comment"
            className="form-input invoice-decision-comment"
            value={decisionComment}
            onChange={(e) => setDecisionComment(e.target.value)}
          />
          <div className="invoice-decision-footer">
            <span>{invoiceImport.decision_updated_at ? `Mis a jour le ${formatDateTime(invoiceImport.decision_updated_at)}` : "Pas encore arbitree"}</span>
            <button
              type="button"
              className="btn-primary"
              disabled={decisionMut.isPending}
              onClick={() => decisionMut.mutate()}
            >
              {decisionMut.isPending ? "Enregistrement..." : "Enregistrer"}
            </button>
          </div>
          {decisionMut.isError && <p className="error-text">{(decisionMut.error as Error).message}</p>}
        </section>

        <section className="invoice-detail-section">
          <h3>Fiche de liaison finances</h3>
          {codificationQuery.isLoading && <p className="loading-text">Codification…</p>}
          {codificationQuery.data && (
            <>
              <p style={{ fontSize: 13, color: "#475569", margin: "0 0 10px" }}>
                {codificationQuery.data.rows_count} ligne(s) ·{" "}
                {codificationQuery.data.blocked_count > 0 ? (
                  <span style={{ color: "#b45309" }}>
                    {codificationQuery.data.blocked_count} à codifier (PRM ou poste absent de la matrice)
                  </span>
                ) : (
                  <span style={{ color: "#15803d" }}>toutes les lignes sont codifiées</span>
                )}
              </p>
              <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => {
                    setLiaisonError(null);
                    downloadInvoiceLiaison(
                      token!,
                      invoiceImportId,
                      invoiceImport.invoice_number ?? String(invoiceImportId),
                    ).catch((e) => setLiaisonError((e as Error).message));
                  }}
                >
                  Exporter la fiche de liaison (xlsx)
                </button>
                <Link to="/energie/factures" className="btn-secondary btn-compact">
                  Ouvrir la matrice comptable
                </Link>
              </div>
              {liaisonError && <p className="error-text">{liaisonError}</p>}
              <div style={{ overflowX: "auto", border: "1px solid #e2e8f0", borderRadius: 8 }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr>
                      {["PRM", "Site", "Poste", "Montant HT", "Service", "Fonction", "Antenne", "Nature", ""].map((h) => (
                        <th key={h} style={{ textAlign: "left", padding: "5px 8px", background: "#f1f5f9", borderBottom: "1px solid #e2e8f0", whiteSpace: "nowrap" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {codificationQuery.data.rows.slice(0, 200).map((r, i) => (
                      <tr key={i} style={{ background: r.status === "blocked" ? "rgba(251,191,36,0.12)" : undefined }}>
                        <td style={{ padding: "4px 8px", fontFamily: "monospace", whiteSpace: "nowrap" }}>{r.prm_id}</td>
                        <td style={{ padding: "4px 8px" }}>{r.site_name}</td>
                        <td style={{ padding: "4px 8px" }}>{r.poste}</td>
                        <td style={{ padding: "4px 8px", textAlign: "right" }}>{r.amount_ht != null ? r.amount_ht.toFixed(2) : ""}</td>
                        <td style={{ padding: "4px 8px" }}>{r.service_code}</td>
                        <td style={{ padding: "4px 8px" }}>{r.function_code}</td>
                        <td style={{ padding: "4px 8px" }}>{r.antenna_code}</td>
                        <td style={{ padding: "4px 8px" }}>{r.accounting_nature}</td>
                        <td style={{ padding: "4px 8px" }}>{r.status === "blocked" ? "⚠️" : "✓"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      </div>

      {humanSummary && (
        <section className={`invoice-detail-section invoice-human-summary invoice-human-summary--${humanSummary.tone}`}>
          <div className="invoice-human-summary-header">
            <div>
              <h3>Resume simple</h3>
              <p>{humanSummary.title}</p>
              <span>{humanSummary.description}</span>
            </div>
            <span
              className={`badge ${
                humanSummary.tone === "error" ? "badge-red" : humanSummary.tone === "warning" ? "badge-orange" : "badge-green"
              }`}
            >
              {humanSummary.tone === "error" ? "A corriger" : humanSummary.tone === "warning" ? "A verifier" : "OK"}
            </span>
          </div>
          <div className="invoice-human-summary-grid">
            <div className="invoice-human-summary-block">
              <h4>Ce qui va</h4>
              <ul className="invoice-human-summary-list invoice-human-summary-list--ok">
                {humanSummary.okItems.map((item) => (
                  <li key={`${item.title}-${item.detail}`}>
                    <strong>{item.title}</strong>
                    <span>{item.detail}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="invoice-human-summary-block">
              <h4>Ce qui ne va pas ou reste a verifier</h4>
              {humanSummary.attentionItems.length > 0 ? (
                <ul className="invoice-human-summary-list invoice-human-summary-list--attention">
                  {humanSummary.attentionItems.map((item) => (
                    <li key={`${item.title}-${item.detail}`} className={`invoice-human-summary-item--${item.tone}`}>
                      <strong>{item.title}</strong>
                      <span>{item.detail}</span>
                      {item.issueDetails && item.issueDetails.length > 0 && (
                        <div className="invoice-human-summary-detail-list">
                          {item.issueDetails.map((detail, index) => (
                            <div
                              key={`${item.title}-${detail.message}-${detail.scope ?? "document"}-${index}`}
                              className="invoice-human-summary-detail-row"
                            >
                              <b className={`invoice-human-summary-detail-severity invoice-human-summary-detail-severity--${detail.severity}`}>
                                {ISSUE_SEVERITY_LABEL[detail.severity] ?? detail.severity}
                                {detail.count > 1 ? ` x${detail.count}` : ""}
                              </b>
                              <p>{detail.message}</p>
                              {detail.scope && <small>{detail.scope}</small>}
                            </div>
                          ))}
                        </div>
                      )}
                      {item.hiddenIssueCount && item.hiddenIssueCount > 0 ? (
                        <p className="invoice-human-summary-more">
                          {item.hiddenIssueCount} autre{item.hiddenIssueCount !== 1 ? "s" : ""} point
                          {item.hiddenIssueCount !== 1 ? "s" : ""} dans le detail des controles.
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="cell-empty">Aucun point a traiter dans les controles disponibles.</p>
              )}
            </div>
          </div>
          <p className="invoice-human-summary-next">{humanSummary.nextAction}</p>
        </section>
      )}

      <section className="invoice-detail-section">
        <div className="section-title-row">
          <h3>Controles</h3>
        </div>
        <div className="invoice-control-summary-grid">
          <div>
            <strong>BPU</strong>
            <span>{formatNumber(recordNumber(bpuSummary, "checked_lines"))} ligne(s)</span>
          </div>
          <div>
            <strong>TURPE</strong>
            <span>{formatNumber(recordNumber(turpeSummary, "checked_lines"))} composante(s)</span>
          </div>
          <div>
            <strong>Taxes</strong>
            <span>{formatNumber(recordNumber(taxesSummary, "checked_sites"))} FIC</span>
          </div>
          <div>
            <strong>Periodes</strong>
            <span>{formatNumber(recordNumber(periodsSummary, "checked_sites"))} FIC</span>
          </div>
          <div>
            <strong>Conso</strong>
            <span>{formatNumber(recordNumber(consumptionSummary, "checked_sites"))} PRM</span>
          </div>
          <div>
            <strong>Puissance</strong>
            <span>
              {formatNumber(recordNumber(powerSummary, "load_curve_checks"))} CDC /{" "}
              {formatNumber(recordNumber(powerSummary, "max_power_checks"))} max
            </span>
          </div>
        </div>
        {issues.length > 0 ? (
          <div className="invoice-issue-list">
            {issues.map((issue, index) => (
              <div key={`${issue.code}-${issue.scope ?? "document"}-${index}`} className="invoice-issue-row">
                {issueBadge(issue.severity)}
                <div>
                  <strong>{issue.code}</strong>
                  <p>{issue.message}</p>
                  {issue.scope && <span>{issue.scope}</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="cell-empty">Aucune anomalie detectee</p>
        )}
      </section>

      <section className="invoice-detail-section">
        <h3>PRM / FIC</h3>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>FIC</th>
                <th>PRM</th>
                <th>Site</th>
                <th>Periode</th>
                <th>Tarif</th>
                <th>Puissance</th>
                <th>Montant TTC</th>
              </tr>
            </thead>
            <tbody>
              {sites.map((site: EnergyInvoiceSite, index) => (
                <tr key={`${site.fic_number ?? "fic"}-${site.prm_id ?? index}`}>
                  <td>{site.fic_number ?? "-"}</td>
                  <td className="cell-mono">{site.prm_id ?? "-"}</td>
                  <td>
                    <div className="invoice-file-cell">
                      <strong>{site.delivery_site_name ?? site.site_name ?? "-"}</strong>
                      <span>{site.delivery_address ?? "-"}</span>
                    </div>
                  </td>
                  <td>
                    {formatShortDate(site.period_start)} - {formatShortDate(site.period_end)}
                  </td>
                  <td>{site.tariff_option_label ?? site.segment ?? "-"}</td>
                  <td>
                    {formatNumber(site.subscribed_power_kva, " kVA")} / {formatNumber(site.max_reached_power_kva, " kVA")}
                  </td>
                  <td>{formatCurrency(site.total_ttc)}</td>
                </tr>
              ))}
              {sites.length === 0 && (
                <tr>
                  <td colSpan={7} className="cell-empty">Aucun PRM detecte</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="invoice-detail-section">
        <div className="section-title-row invoice-turpe-title">
          <div>
            <h3>Acheminement utilise pour le controle TURPE</h3>
            <p className="page-subtitle">
              Les factures ENGIE portent ces montants en acheminement, avec des composantes de comptage, gestion et
              soutirage.
            </p>
          </div>
          <div className="invoice-issue-tags">
            <span className="invoice-issue-family-tag">{supplierTurpeIssues.length} ecart(s) calcule(s)</span>
            <span className="invoice-issue-code-tag">{internalTurpeIssues.length} limite(s) interne(s)</span>
          </div>
        </div>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>PRM</th>
                <th>Composante</th>
                <th>Poste</th>
                <th>Libelle fournisseur</th>
                <th>Quantite</th>
                <th>PU HT</th>
                <th>Montant HT</th>
              </tr>
            </thead>
            <tbody>
              {networkLines.slice(0, 120).map((line: EnergyInvoiceLine & { prm_id?: string | null; fic_number?: string | null }, index) => (
                <tr key={`${line.prm_id ?? line.fic_number ?? "network"}-${index}`}>
                  <td className="cell-mono">{line.prm_id ?? line.fic_number ?? "-"}</td>
                  <td>{networkComponentLabel(line.normalized_component)}</td>
                  <td>{line.poste ?? "-"}</td>
                  <td>{line.label ?? line.raw_line ?? "-"}</td>
                  <td>{formatNumber(line.quantity, line.quantity_unit ? ` ${line.quantity_unit}` : "")}</td>
                  <td>{line.unit_price_ht !== undefined && line.unit_price_ht !== null ? `${line.unit_price_ht} ${line.unit_price_unit ?? ""}` : "-"}</td>
                  <td>{formatCurrency(line.amount_ht)}</td>
                </tr>
              ))}
              {networkLines.length === 0 && (
                <tr>
                  <td colSpan={7} className="cell-empty">Aucune ligne d'acheminement extraite</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {networkLines.length > 120 && <p className="invoice-lines-note">{networkLines.length - 120} ligne(s) d'acheminement supplementaire(s) non affichee(s).</p>}
      </section>

      <section className="invoice-detail-section">
        <h3>Lignes facture extraites</h3>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>PRM</th>
                <th>Composante</th>
                <th>Poste</th>
                <th>Libelle</th>
                <th>Quantite</th>
                <th>PU HT</th>
                <th>Montant HT</th>
              </tr>
            </thead>
            <tbody>
              {invoiceLines.slice(0, 120).map((line: EnergyInvoiceLine & { prm_id?: string | null; fic_number?: string | null }, index) => (
                <tr key={`${line.prm_id ?? line.fic_number ?? "line"}-${index}`}>
                  <td className="cell-mono">{line.prm_id ?? line.fic_number ?? "-"}</td>
                  <td>{line.normalized_component ?? line.family ?? "-"}</td>
                  <td>{line.poste ?? "-"}</td>
                  <td>{line.label ?? line.raw_line ?? "-"}</td>
                  <td>{formatNumber(line.quantity, line.quantity_unit ? ` ${line.quantity_unit}` : "")}</td>
                  <td>{line.unit_price_ht !== undefined && line.unit_price_ht !== null ? `${line.unit_price_ht} ${line.unit_price_unit ?? ""}` : "-"}</td>
                  <td>{formatCurrency(line.amount_ht)}</td>
                </tr>
              ))}
              {invoiceLines.length === 0 && (
                <tr>
                  <td colSpan={7} className="cell-empty">Aucune ligne exploitable</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {invoiceLines.length > 120 && <p className="invoice-lines-note">{invoiceLines.length - 120} ligne(s) supplementaire(s) non affichee(s).</p>}
      </section>
    </div>
  );
}
