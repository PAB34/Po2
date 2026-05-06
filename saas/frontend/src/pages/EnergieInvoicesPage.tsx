import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  analyzeEnergyInvoiceImport,
  fetchEnergyInvoiceImports,
  fetchTurpeVersions,
  uploadEnergyInvoiceImport,
} from "../lib/api";
import type { EnergyInvoiceImport } from "../lib/api";
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

export function EnergieInvoicesPage() {
  const { token } = useAuth();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadSummary, setUploadSummary] = useState<string | null>(null);

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

  const imports = importsQuery.data ?? [];
  const activeTurpeVersion = turpeVersionsQuery.data?.[0];
  const stats = useMemo(() => {
    const invalid = imports.filter((i) => i.control_status === "invalid").length;
    const review = imports.filter((i) => i.control_status === "review" || i.analysis_status === "pending").length;
    const valid = imports.filter((i) => i.control_status === "valid").length;
    return { total: imports.length, invalid, review, valid };
  }, [imports]);

  const uploadMut = useMutation({
    mutationFn: async (files: File[]) => {
      const results = [];
      for (const file of files) {
        results.push(await uploadEnergyInvoiceImport(token!, file));
      }
      return results;
    },
    onSuccess: (results) => {
      const duplicates = results.filter((r) => r.is_duplicate).length;
      const created = results.length - duplicates;
      setUploadSummary(`${created} facture(s) importee(s), ${duplicates} doublon(s).`);
      setSelectedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
      qc.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
    },
  });

  const analyzeMut = useMutation({
    mutationFn: (invoiceImport: EnergyInvoiceImport) => analyzeEnergyInvoiceImport(token!, invoiceImport.id),
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
            Depose ici les factures telechargees depuis les espaces clients. Cette premiere version stocke les fichiers
            et lance le controle automatique ENGIE lorsqu'un PDF est reconnu.
          </p>
        </div>
        <div className="invoice-upload-actions">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.xml,.csv,.txt,.xlsx,.xls,.zip"
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
              <th>Montant</th>
              <th>Controle</th>
              <th>Import</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {imports.map((invoiceImport) => (
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
                    {invoiceImport.control_issues[0] && <small>{invoiceImport.control_issues[0].message}</small>}
                  </div>
                </td>
                <td>{formatDate(invoiceImport.created_at)}</td>
                <td>
                  <div className="invoice-action-cell">
                    {statusBadge(invoiceImport)}
                    <span className="badge badge-gray">{IMPORT_STATUS_LABEL[invoiceImport.status] ?? invoiceImport.source}</span>
                    {(invoiceImport.analysis_status === "pending" || invoiceImport.analysis_status === "failed") && (
                      <button
                        type="button"
                        className="btn-secondary btn-compact"
                        disabled={analyzeMut.isPending}
                        onClick={() => analyzeMut.mutate(invoiceImport)}
                      >
                        Analyser
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {!importsQuery.isLoading && imports.length === 0 && (
              <tr>
                <td colSpan={7} className="cell-empty">Aucune facture importee</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
