import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  fetchEnergyInvoiceImport,
  updateEnergyInvoiceDecision,
} from "../lib/api";
import type {
  EnergyInvoiceDecisionPayload,
  EnergyInvoiceImport,
  EnergyInvoiceLine,
  EnergyInvoiceSite,
} from "../lib/api";
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
      </div>

      <section className="invoice-detail-section">
        <div className="section-title-row">
          <h3>Controles</h3>
          <span>
            BPU {formatNumber(recordNumber(bpuSummary, "checked_lines"))} ligne(s) | TURPE{" "}
            {formatNumber(recordNumber(turpeSummary, "checked_components"))} composante(s)
          </span>
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
