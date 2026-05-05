import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { EnergyInvoiceImport, fetchEnergyInvoiceImports, uploadEnergyInvoiceImport } from "../lib/api";
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

function formatDate(value: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
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

  const imports = importsQuery.data ?? [];
  const stats = useMemo(() => {
    const pending = imports.filter((i) => i.analysis_status === "pending").length;
    const suppliers = new Set(imports.map((i) => i.supplier_guess).filter(Boolean)).size;
    return { total: imports.length, pending, suppliers };
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
          <span className="kpi-label">En attente d'analyse</span>
          <span className="kpi-value">{stats.pending}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Fournisseurs detectes</span>
          <span className="kpi-value">{stats.suppliers}</span>
        </div>
      </div>

      <section className="invoice-upload-panel">
        <div>
          <p className="field-label">Depot manuel</p>
          <p className="invoice-upload-copy">
            Depose ici les factures telechargees depuis les espaces clients. Cette premiere version stocke les fichiers
            et prepare leur analyse automatique.
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

      {importsQuery.isLoading && <p className="loading-text">Chargement des imports...</p>}
      {importsQuery.isError && <p className="error-text">{(importsQuery.error as Error).message}</p>}

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Fichier</th>
              <th>Fournisseur</th>
              <th>Taille</th>
              <th>Import</th>
              <th>Statut</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {imports.map((invoiceImport) => (
              <tr key={invoiceImport.id}>
                <td>
                  <div className="invoice-file-cell">
                    <strong>{invoiceImport.original_filename}</strong>
                    <span>{invoiceImport.sha256.slice(0, 12)}</span>
                  </div>
                </td>
                <td>{invoiceImport.supplier_guess ?? "-"}</td>
                <td>{formatSize(invoiceImport.file_size_bytes)}</td>
                <td>{formatDate(invoiceImport.created_at)}</td>
                <td>{statusBadge(invoiceImport)}</td>
                <td>
                  <span className="badge badge-gray">{IMPORT_STATUS_LABEL[invoiceImport.status] ?? invoiceImport.source}</span>
                </td>
              </tr>
            ))}
            {!importsQuery.isLoading && imports.length === 0 && (
              <tr>
                <td colSpan={6} className="cell-empty">Aucune facture importee</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
