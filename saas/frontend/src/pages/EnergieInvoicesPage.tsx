import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  analyzeEnergyInvoiceImport,
  deleteEnergyInvoiceImport,
  fetchEnergyInvoiceBatch,
  fetchEnergyInvoiceBatches,
  fetchEnergyInvoiceImports,
  fetchTurpeVersions,
  uploadEnergyInvoiceBatch,
} from "../lib/api";
import type { EnergyInvoiceImport } from "../lib/api";
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

export function EnergieInvoicesPage() {
  const { token } = useAuth();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadSummary, setUploadSummary] = useState<string | null>(null);
  const [selectedBatchId, setSelectedBatchId] = useState<number | null>(null);
  const [invoiceSearch, setInvoiceSearch] = useState("");
  const [controlFilter, setControlFilter] = useState("all");
  const [decisionFilter, setDecisionFilter] = useState("all");
  const [regroupementFilter, setRegroupementFilter] = useState("all");
  const [contractHolderFilter, setContractHolderFilter] = useState("all");
  const [issueFamilyFilter, setIssueFamilyFilter] = useState<InvoiceIssueFamily | "all">("all");
  const [issueCodeFilter, setIssueCodeFilter] = useState("all");

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
        if (issueFamilyFilter !== "all" && family !== issueFamilyFilter) continue;
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
  }, [imports, issueFamilyFilter]);
  const filteredImports = useMemo(() => {
    const search = invoiceSearch.trim().toLowerCase();
    return imports.filter((invoiceImport) => {
      if (controlFilter !== "all" && invoiceImport.control_status !== controlFilter) return false;
      if (decisionFilter !== "all" && invoiceImport.decision_status !== decisionFilter) return false;
      if (regroupementFilter !== "all" && invoiceImport.regroupement !== regroupementFilter) return false;
      if (contractHolderFilter !== "all" && invoiceImport.contract_holder !== contractHolderFilter) return false;
      if (
        issueFamilyFilter !== "all" &&
        !invoiceImport.control_issues.some((issue) => invoiceIssueFamily(issue) === issueFamilyFilter)
      ) {
        return false;
      }
      if (issueCodeFilter !== "all" && !invoiceImport.control_issues.some((issue) => issue.code === issueCodeFilter)) return false;
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
    contractHolderFilter,
    controlFilter,
    decisionFilter,
    imports,
    invoiceSearch,
    issueCodeFilter,
    issueFamilyFilter,
    regroupementFilter,
  ]);
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

      <section className="invoice-upload-panel">
        <div>
          <p className="field-label">Depot manuel</p>
          <p className="invoice-upload-copy">
            Depose les PDF ENGIE telecharges depuis les espaces clients ou une archive ZIP de PDF. Le lot reste trace
            avec ses factures importees, ses doublons et ses erreurs.
          </p>
        </div>
        <div className="invoice-upload-actions">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.zip"
            onChange={(e) => setSelectedFiles(Array.from(e.target.files ?? []))}
            className="form-input"
          />
          <button
            type="button"
            className="btn-primary"
            disabled={selectedFiles.length === 0 || uploadMut.isPending}
            onClick={() => uploadMut.mutate(selectedFiles)}
          >
            {uploadMut.isPending ? "Import en cours..." : "Importer"}
          </button>
        </div>
        {selectedFiles.length > 0 && (
          <p className="invoice-upload-selection">
            {selectedFiles.length} fichier{selectedFiles.length > 1 ? "s" : ""} selectionne
            {selectedFiles.length > 1 ? "s" : ""}
          </p>
        )}
        {uploadSummary && <p className="sync-result-ok">{uploadSummary}</p>}
        {uploadMut.isError && <p className="error-text">{(uploadMut.error as Error).message}</p>}
      </section>

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
        {batchDetailQuery.data && (
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
                {batchDetailQuery.data.items.map((item) => (
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

      <section className="invoice-detail-section">
        <h3>Filtrer les factures</h3>
        <div className="invoice-action-cell">
          <button
            type="button"
            className="btn-secondary btn-compact"
            onClick={() => {
              setControlFilter("review");
              setDecisionFilter("all");
            }}
          >
            A controler
          </button>
          <button
            type="button"
            className="btn-secondary btn-compact"
            onClick={() => {
              setControlFilter("invalid");
              setDecisionFilter("all");
            }}
          >
            En erreur
          </button>
          <button
            type="button"
            className="btn-secondary btn-compact"
            onClick={() => {
              setControlFilter("all");
              setDecisionFilter("to_review");
            }}
          >
            Decisions a rendre
          </button>
          <button
            type="button"
            className="btn-secondary btn-compact"
            onClick={() => {
              setControlFilter("all");
              setDecisionFilter("all");
              setRegroupementFilter("all");
              setContractHolderFilter("all");
              setIssueFamilyFilter("all");
              setIssueCodeFilter("all");
              setInvoiceSearch("");
            }}
          >
            Reinitialiser
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
          <label>
            <span className="field-label">Controle</span>
            <select className="form-input" value={controlFilter} onChange={(e) => setControlFilter(e.target.value)}>
              <option value="all">Tous</option>
              <option value="valid">Valides</option>
              <option value="review">A controler</option>
              <option value="invalid">Invalides</option>
              <option value="not_checked">Non controlees</option>
            </select>
          </label>
          <label>
            <span className="field-label">Decision</span>
            <select className="form-input" value={decisionFilter} onChange={(e) => setDecisionFilter(e.target.value)}>
              <option value="all">Toutes</option>
              <option value="to_review">A verifier</option>
              <option value="approved">Validees</option>
              <option value="rejected">Refusees</option>
              <option value="dispute_sent">Contestation envoyee</option>
            </select>
          </label>
          <label>
            <span className="field-label">Regroupement</span>
            <select className="form-input" value={regroupementFilter} onChange={(e) => setRegroupementFilter(e.target.value)}>
              <option value="all">Tous</option>
              {regroupements.map((regroupement) => (
                <option key={regroupement} value={regroupement}>
                  {regroupement}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="field-label">Titulaire</span>
            <select className="form-input" value={contractHolderFilter} onChange={(e) => setContractHolderFilter(e.target.value)}>
              <option value="all">Tous</option>
              {contractHolders.map((contractHolder) => (
                <option key={contractHolder} value={contractHolder}>
                  {contractHolder}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="field-label">Categorie de probleme</span>
            <select
              className="form-input"
              value={issueFamilyFilter}
              onChange={(e) => {
                setIssueFamilyFilter(e.target.value as InvoiceIssueFamily | "all");
                setIssueCodeFilter("all");
              }}
            >
              <option value="all">Toutes</option>
              {issueFamilies.map((family) => (
                <option key={family} value={family}>
                  {INVOICE_ISSUE_FAMILY_LABEL[family]}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="field-label">Type de probleme</span>
            <select className="form-input" value={issueCodeFilter} onChange={(e) => setIssueCodeFilter(e.target.value)}>
              <option value="all">Tous</option>
              {issueCodes.map((issue) => (
                <option key={issue.code} value={issue.code} title={issue.message}>
                  {INVOICE_ISSUE_FAMILY_LABEL[issue.family]} : {issue.code}
                </option>
              ))}
            </select>
          </label>
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

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Fichier</th>
              <th>Facture</th>
              <th>Regroupement</th>
              <th>Titulaire</th>
              <th>Montant</th>
              <th>Controle</th>
              <th>Decision</th>
              <th>Import</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredImports.map((invoiceImport) => (
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
            {!importsQuery.isLoading && filteredImports.length === 0 && (
              <tr>
                <td colSpan={9} className="cell-empty">Aucune facture ne correspond aux filtres.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
