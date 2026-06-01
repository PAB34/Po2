/**
 * Page d'import du référentiel contractuel DALKIA CPE.
 *
 * Workflow :
 * 1. Sélectionner le fichier Excel (L1 ou L2) + indiquer le lot
 * 2. Cliquer "Analyser" → appel /preview → affichage du rapport de contrôle
 * 3. Valider → appel /confirm → import en base, les données de référence sont mises à jour
 *
 * Les données importées servent de référence pour le contrôle des factures :
 * - Montants P2/P3 par site × période
 * - Cibles de consommation GAZ et ELEC par site × période
 * - P1 fourniture gaz par site × période
 * - Travaux APE par site
 */
import { useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../providers/AuthProvider";

const apiBaseUrl = import.meta.env.VITE_API_URL ?? "/api";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

type ImportPreview = {
  lot: number;
  filename: string;
  nb_sites: number;
  nb_p2p3_rows: number;
  nb_cibles_rows: number;
  nb_p1_gaz_rows: number;
  nb_ape_rows: number;
  period_labels: string[];
  sample_sites: {
    code_site: string;
    nom_batiment: string;
    lot: number;
    p2_total_2026: number | null;
    p3_total_2026: number | null;
    qt_gaz_cible_2026: number | null;
  }[];
  warnings: string[];
};

type ImportBatch = {
  id: number;
  lot: number;
  filename: string;
  import_date: string;
  nb_sites: number;
  nb_p2p3_rows: number;
  nb_cibles_rows: number;
  nb_p1_gaz_rows: number;
  nb_ape_rows: number;
  is_active: boolean;
  notes: string | null;
};

type SiteRow = {
  code_site: string;
  nom_batiment: string;
  entite: string | null;
  lot: number;
  lot_label: string | null;
};

// ─────────────────────────────────────────────────────────────────────────────
// API helpers (pas dans api.ts car multipart FormData spécifique)
// ─────────────────────────────────────────────────────────────────────────────

function buildAuthHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

async function previewDalkiaImport(token: string, file: File, lot: number): Promise<ImportPreview> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("lot", String(lot));
  const resp = await fetch(`${apiBaseUrl}/cpe/dalkia-ref/preview`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: fd,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail ?? `Erreur ${resp.status}`);
  }
  return resp.json() as Promise<ImportPreview>;
}

async function confirmDalkiaImport(token: string, file: File, lot: number): Promise<ImportBatch> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("lot", String(lot));
  const resp = await fetch(`${apiBaseUrl}/cpe/dalkia-ref/confirm`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: fd,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail ?? `Erreur ${resp.status}`);
  }
  return resp.json() as Promise<ImportBatch>;
}

async function fetchImports(token: string): Promise<ImportBatch[]> {
  const resp = await fetch(`${apiBaseUrl}/cpe/dalkia-ref/imports`, {
    headers: { ...buildAuthHeaders(token), "Content-Type": "application/json" },
  });
  if (!resp.ok) throw new Error(`Erreur ${resp.status}`);
  return resp.json() as Promise<ImportBatch[]>;
}

async function fetchImportSites(token: string, importId: number): Promise<SiteRow[]> {
  const resp = await fetch(`${apiBaseUrl}/cpe/dalkia-ref/imports/${importId}/sites`, {
    headers: { ...buildAuthHeaders(token), "Content-Type": "application/json" },
  });
  if (!resp.ok) throw new Error(`Erreur ${resp.status}`);
  return resp.json() as Promise<SiteRow[]>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Composant principal
// ─────────────────────────────────────────────────────────────────────────────

function formatEur(v: number | null | undefined) {
  if (v == null) return "—";
  return v.toLocaleString("fr-FR", { maximumFractionDigits: 0 }) + " €";
}

function formatMwh(v: number | null | undefined) {
  if (v == null) return "—";
  return v.toLocaleString("fr-FR", { maximumFractionDigits: 1 }) + " MWh";
}

export function CpeDalkiaImportPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [lot, setLot] = useState<1 | 2>(1);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [viewImportId, setViewImportId] = useState<number | null>(null);

  const importsQuery = useQuery({
    queryKey: ["cpe-dalkia-imports", token],
    queryFn: () => fetchImports(token as string),
    enabled: Boolean(token),
  });

  const sitesQuery = useQuery({
    queryKey: ["cpe-dalkia-sites", viewImportId, token],
    queryFn: () => fetchImportSites(token as string, viewImportId as number),
    enabled: Boolean(token) && viewImportId !== null,
  });

  const previewMutation = useMutation({
    mutationFn: () => previewDalkiaImport(token as string, selectedFile as File, lot),
    onSuccess: (data) => {
      setPreview(data);
      setPreviewError(null);
    },
    onError: (err: unknown) => {
      setPreviewError(err instanceof Error ? err.message : "Erreur d'analyse");
      setPreview(null);
    },
  });

  const confirmMutation = useMutation({
    mutationFn: () => confirmDalkiaImport(token as string, selectedFile as File, lot),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cpe-dalkia-imports"] });
      setPreview(null);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    onError: (err: unknown) => {
      setPreviewError(err instanceof Error ? err.message : "Erreur d'import");
    },
  });

  if (!token) {
    return (
      <section className="panel stack-lg">
        <h2>Import référentiel DALKIA</h2>
        <p>Connecte-toi pour accéder à cette page.</p>
      </section>
    );
  }

  const imports = importsQuery.data ?? [];
  const activeL1 = imports.find((i) => i.lot === 1 && i.is_active);
  const activeL2 = imports.find((i) => i.lot === 2 && i.is_active);

  return (
    <section className="panel stack-lg">
      {/* ── Header ── */}
      <div className="panel-header">
        <div>
          <p className="eyebrow">CPE DALKIA</p>
          <h2>Import du référentiel contractuel</h2>
          <p>
            Importe les fichiers DALKIA (Lot 1 / Lot 2) pour mettre à jour les données de
            référence : P2, P3, cibles GAZ/ELEC, P1 fourniture gaz, travaux APE. Ces données
            servent de base de contrôle des factures.
          </p>
        </div>
        <Link className="secondary-link" to="/cpe">
          ← Retour CPE
        </Link>
      </div>

      {/* ── Statut des imports actifs ── */}
      <div className="detail-grid">
        <div className="detail-card">
          <span>Référentiel actif — Lot 1 (écoles / sport)</span>
          <strong>
            {activeL1
              ? `${activeL1.nb_sites} sites · importé le ${new Date(activeL1.import_date).toLocaleDateString("fr-FR")}`
              : "Aucun import"}
          </strong>
        </div>
        <div className="detail-card">
          <span>Référentiel actif — Lot 2 (piscines)</span>
          <strong>
            {activeL2
              ? `${activeL2.nb_sites} sites · importé le ${new Date(activeL2.import_date).toLocaleDateString("fr-FR")}`
              : "Aucun import"}
          </strong>
        </div>
      </div>

      {/* ── Formulaire d'import ── */}
      <div className="section-block">
        <div className="section-heading">
          <h3>1. Sélectionner le fichier</h3>
          <p>
            Fichier Excel DALKIA (format .xlsx ou .xlsm) — les deux onglets principaux sont
            parsés : Annexe 3.1 P2, Annexe 4 P3, Annexe 5.1 Cibles GAZ, Annexe 5.2 Cibles ELEC,
            Annexe 6 P1 GAZ, Annexe 2bis Travaux APE.
          </p>
        </div>
        <form
          className="form"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (selectedFile) previewMutation.mutate();
          }}
        >
          <div className="form-grid">
            <label className="field">
              <span>Lot</span>
              <select value={lot} onChange={(e: ChangeEvent<HTMLSelectElement>) => setLot(Number(e.target.value) as 1 | 2)}>
                <option value={1}>Lot 1 — Écoles, sport (L1)</option>
                <option value={2}>Lot 2 — Piscines (L2)</option>
              </select>
            </label>
            <label className="field">
              <span>Fichier Excel DALKIA</span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xlsm"
                onChange={(e: ChangeEvent<HTMLInputElement>) => {
                  setSelectedFile(e.target.files?.[0] ?? null);
                  setPreview(null);
                  setPreviewError(null);
                }}
              />
            </label>
          </div>
          {previewError ? <p className="error-text">{previewError}</p> : null}
          {confirmMutation.isSuccess ? (
            <p className="success-text">
              ✓ Référentiel Lot {lot} importé avec succès. Les données de contrôle sont mises à jour.
            </p>
          ) : null}
          <div className="form-actions">
            <button type="submit" className="secondary-button" disabled={!selectedFile || previewMutation.isPending}>
              {previewMutation.isPending ? "Analyse en cours..." : "2. Analyser le fichier"}
            </button>
          </div>
        </form>
      </div>

      {/* ── Rapport d'analyse (preview) ── */}
      {preview ? (
        <div className="section-block">
          <div className="section-heading">
            <h3>Rapport de contrôle — {preview.filename}</h3>
            <p>Vérifie ces données avant de confirmer l'import.</p>
          </div>

          {/* Compteurs */}
          <div className="detail-grid">
            <div className="detail-card">
              <span>Sites parsés</span>
              <strong>{preview.nb_sites}</strong>
            </div>
            <div className="detail-card">
              <span>Lignes P2 / P3</span>
              <strong>{preview.nb_p2p3_rows}</strong>
            </div>
            <div className="detail-card">
              <span>Cibles GAZ + ELEC</span>
              <strong>{preview.nb_cibles_rows}</strong>
            </div>
            <div className="detail-card">
              <span>Lignes P1 gaz</span>
              <strong>{preview.nb_p1_gaz_rows}</strong>
            </div>
            <div className="detail-card">
              <span>Travaux APE</span>
              <strong>{preview.nb_ape_rows}</strong>
            </div>
            <div className="detail-card">
              <span>Périodes détectées</span>
              <strong>{preview.period_labels.length} ({preview.period_labels[0]} → {preview.period_labels[preview.period_labels.length - 1]})</strong>
            </div>
          </div>

          {/* Avertissements */}
          {preview.warnings.length > 0 ? (
            <div className="info-banner" style={{ borderColor: "#f59e0b", background: "rgba(245,158,11,0.1)" }}>
              <strong>⚠ {preview.warnings.length} avertissement(s) de parsing</strong>
              <ul style={{ paddingLeft: 20, marginTop: 8, maxHeight: 120, overflowY: "auto" }}>
                {preview.warnings.map((w, i) => (
                  <li key={i} style={{ fontSize: 13 }}>{w}</li>
                ))}
              </ul>
              <p style={{ fontSize: 12, marginTop: 4, color: "#9ca3af" }}>
                Les avertissements sont habituellement des lignes spéciales (PV, récapitulatifs) — vérifier si les totaux sont cohérents.
              </p>
            </div>
          ) : (
            <p className="success-text">✓ Aucun avertissement — parsing propre.</p>
          )}

          {/* Aperçu des premiers sites */}
          <div className="section-heading" style={{ marginTop: 16 }}>
            <h4>Aperçu — {preview.sample_sites.length} premiers sites (données 2026)</h4>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.3)" }}>
                  <th style={{ textAlign: "left", padding: "6px 12px" }}>Code site</th>
                  <th style={{ textAlign: "left", padding: "6px 12px" }}>Bâtiment</th>
                  <th style={{ textAlign: "right", padding: "6px 12px" }}>P2 total 2026</th>
                  <th style={{ textAlign: "right", padding: "6px 12px" }}>P3 total 2026</th>
                  <th style={{ textAlign: "right", padding: "6px 12px" }}>Cible gaz 2026</th>
                </tr>
              </thead>
              <tbody>
                {preview.sample_sites.map((site) => (
                  <tr key={site.code_site} style={{ borderBottom: "1px solid rgba(148,163,184,0.1)" }}>
                    <td style={{ padding: "5px 12px", fontFamily: "monospace", fontWeight: 600 }}>{site.code_site}</td>
                    <td style={{ padding: "5px 12px", color: "#94a3b8" }}>{site.nom_batiment}</td>
                    <td style={{ padding: "5px 12px", textAlign: "right" }}>{formatEur(site.p2_total_2026)}</td>
                    <td style={{ padding: "5px 12px", textAlign: "right" }}>{formatEur(site.p3_total_2026)}</td>
                    <td style={{ padding: "5px 12px", textAlign: "right" }}>{formatMwh(site.qt_gaz_cible_2026)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Boutons de confirmation */}
          <div className="form-actions" style={{ marginTop: 16 }}>
            <button
              type="button"
              onClick={() => confirmMutation.mutate()}
              disabled={confirmMutation.isPending}
            >
              {confirmMutation.isPending
                ? "Import en cours..."
                : `3. Confirmer l'import Lot ${preview.lot} (${preview.nb_sites} sites)`}
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => setPreview(null)}
            >
              Annuler
            </button>
          </div>
          {confirmMutation.isError ? (
            <p className="error-text">
              {confirmMutation.error instanceof Error ? confirmMutation.error.message : "Erreur lors de l'import"}
            </p>
          ) : null}
        </div>
      ) : null}

      {/* ── Historique des imports ── */}
      <div className="section-block">
        <div className="section-heading">
          <h3>Historique des imports</h3>
          <p>Seul le dernier import de chaque lot est actif (référentiel courant).</p>
        </div>
        {importsQuery.isLoading ? <p>Chargement...</p> : null}
        {imports.length === 0 && !importsQuery.isLoading ? (
          <p style={{ color: "#94a3b8" }}>Aucun import enregistré.</p>
        ) : null}
        <div className="resource-list">
          {imports.map((imp) => (
            <article key={imp.id} className={`resource-card${imp.is_active ? "" : " resource-card-inactive"}`}>
              <div className="resource-card-header">
                <div>
                  <h3>
                    Lot {imp.lot} — {imp.filename}
                    {imp.is_active ? <span style={{ color: "#15803d", marginLeft: 8, fontSize: 12 }}>● Actif</span> : null}
                  </h3>
                  <p>{new Date(imp.import_date).toLocaleString("fr-FR")}</p>
                </div>
              </div>
              <dl className="resource-metadata">
                <div><dt>Sites</dt><dd>{imp.nb_sites}</dd></div>
                <div><dt>P2/P3</dt><dd>{imp.nb_p2p3_rows} lignes</dd></div>
                <div><dt>Cibles énergie</dt><dd>{imp.nb_cibles_rows} lignes</dd></div>
                <div><dt>P1 gaz</dt><dd>{imp.nb_p1_gaz_rows} lignes</dd></div>
                <div><dt>APE</dt><dd>{imp.nb_ape_rows} lignes</dd></div>
              </dl>
              {imp.notes ? <p style={{ color: "#f59e0b", fontSize: 12 }}>⚠ {imp.notes}</p> : null}
              {imp.is_active ? (
                <div className="resource-card-actions">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => setViewImportId(viewImportId === imp.id ? null : imp.id)}
                  >
                    {viewImportId === imp.id ? "Masquer les sites" : "Voir les sites"}
                  </button>
                </div>
              ) : null}
              {viewImportId === imp.id ? (
                <div style={{ marginTop: 12 }}>
                  {sitesQuery.isLoading ? <p>Chargement des sites...</p> : null}
                  {(sitesQuery.data ?? []).length > 0 ? (
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                        <thead>
                          <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.2)" }}>
                            <th style={{ textAlign: "left", padding: "4px 8px" }}>Code site</th>
                            <th style={{ textAlign: "left", padding: "4px 8px" }}>Bâtiment</th>
                            <th style={{ textAlign: "left", padding: "4px 8px" }}>Entité</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(sitesQuery.data ?? []).map((s) => (
                            <tr key={s.code_site} style={{ borderBottom: "1px solid rgba(148,163,184,0.08)" }}>
                              <td style={{ padding: "3px 8px", fontFamily: "monospace" }}>{s.code_site}</td>
                              <td style={{ padding: "3px 8px", color: "#cbd5e1" }}>{s.nom_batiment}</td>
                              <td style={{ padding: "3px 8px", color: "#6b7280" }}>{s.entite ?? "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
