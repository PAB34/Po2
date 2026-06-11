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
import React, { useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../providers/AuthProvider";

const apiBaseUrl = import.meta.env.VITE_API_URL ?? "/api";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

type RecapSummary = {
  bilan_marche_ht: Record<string, number | null>;
  by_year: Record<string, { p1_total_ht: number | null; p2_total_ht: number | null; p3_total_ht: number | null }>;
  facteur_co2_gaz: number | null;
  facteur_co2_elec: number | null;
};

type ImportPreview = {
  lot: number;
  filename: string;
  nb_sites: number;
  nb_p2p3_rows: number;
  nb_cibles_rows: number;
  nb_p1_gaz_rows: number;
  nb_ape_rows: number;
  nb_recap_rows: number;
  recap_summary: RecapSummary;
  classified: ClassifiedData;
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

type ClassifiedData = {
  years: string[];
  p2p3: { code_site: string; nom_batiment: string; by_year: Record<string, { p2: number | null; p3: number | null }> }[];
  cibles_gaz: { code_site: string; ref_globale: number | null; dju: number | null; by_year: Record<string, number | null> }[];
  cibles_elec: { code_site: string; ref_globale: number | null; dju: number | null; by_year: Record<string, number | null> }[];
  p1_gaz: { code_site: string; pce: string | null; type_tarif: string | null; prix_unitaire_ht: number | null; by_year: Record<string, number | null> }[];
  p1_tarifs: {
    type_tarif: string; p0_fournisseur: number | null; ref_peg: number | null; terme_acheminement: number | null;
    obligation_cee: number | null; ticgn: number | null; marge_exploitant_pct: number | null; prix_unitaire_ht: number | null;
    coef_a: number | null; coef_b: number | null; coef_c: number | null; coef_d: number | null; coef_e: number | null;
  }[];
  bpu: {
    categorie: string; famille: string | null; code: string | null; libelle: string | null;
    specificite: string | null; unite: string | null; cout_unitaire: number | null;
    cout_nuit: number | null; cout_samedi: number | null; cout_dimanche: number | null;
    coefficient: number | null; coefficient_max: number | null;
  }[];
  ape: {
    code_site: string; nom_batiment: string | null; description_ape: string | null;
    annee_achevement: number | null; montant_ape_ht: number | null; cee_eur: number | null;
    gain_energetique_mwhpci: number | null; annee_engagement_nouvelle_cible: number | null; emission_co2_evitee: number | null;
  }[];
  recap_engagement: Record<string, Record<string, number | null>>;
  recap_redevances: Record<string, Record<string, number | null>>;
  recap_travaux: { categorie: string; metric: string; value: number | null; unit: string | null }[];
  recap_bilan: { poste: string; metric: string; value: number | null; unit: string | null }[];
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
  nb_recap_rows: number;
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

type SyncP1Result = {
  ok: boolean;
  reason?: string;
  message: string;
  contract_code?: string;
  updated?: number[];
  created?: number[];
  amounts_by_year?: Record<string, number>;
};

async function syncCpeSites(token: string): Promise<{ created: number; updated: number; total: number }> {
  const resp = await fetch(`${apiBaseUrl}/cpe/dalkia-ref/sync-cpe-sites`, {
    method: "POST",
    headers: { ...buildAuthHeaders(token), "Content-Type": "application/json" },
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail ?? `Erreur ${resp.status}`);
  }
  return resp.json() as Promise<{ created: number; updated: number; total: number }>;
}

// ── DPGF P1 révisé (livrable séparé, lignée d'import propre) ─────────────────

type DpgfP1Preview = {
  lot: number;
  filename: string;
  nb_lines: number;
  nb_sites: Record<string, number>;
  totals: Record<string, Record<string, number>>; // {level: {year: total}}
  warnings: string[];
};

type DpgfP1Import = {
  id: number;
  lot: number;
  filename: string;
  import_date: string;
  nb_lines: number;
  is_active: boolean;
  notes: string | null;
};

const DPGF_LEVEL_LABELS: Record<string, string> = {
  contrat: "P1 gaz contrat",
  rev_temp: "P1 gaz Rév Temp",
  rev_temp_prix: "P1 gaz Rév T° & prix",
};

async function previewDpgfP1(token: string, file: File, lot: number): Promise<DpgfP1Preview> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("lot", String(lot));
  const resp = await fetch(`${apiBaseUrl}/cpe/dalkia-ref/dpgf-p1/preview`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: fd,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail ?? `Erreur ${resp.status}`);
  }
  return resp.json() as Promise<DpgfP1Preview>;
}

async function confirmDpgfP1(token: string, file: File, lot: number): Promise<DpgfP1Import> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("lot", String(lot));
  const resp = await fetch(`${apiBaseUrl}/cpe/dalkia-ref/dpgf-p1/confirm`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: fd,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail ?? `Erreur ${resp.status}`);
  }
  return resp.json() as Promise<DpgfP1Import>;
}

async function fetchDpgfP1Imports(token: string): Promise<DpgfP1Import[]> {
  const resp = await fetch(`${apiBaseUrl}/cpe/dalkia-ref/dpgf-p1/imports`, {
    headers: { ...buildAuthHeaders(token), "Content-Type": "application/json" },
  });
  if (!resp.ok) throw new Error(`Erreur ${resp.status}`);
  return resp.json() as Promise<DpgfP1Import[]>;
}

// ── État en vigueur + journal du marché ──────────────────────────────────────

type ActiveSummary = {
  has_data: boolean;
  lot: number;
  ref_year: number;
  import_id: number | null;
  filename: string | null;
  import_date: string | null;
  nb_sites: number | null;
  nb_ape: number | null;
  p1_gaz_ref_year_ht: number | null;
  p1_elec_ref_year_ht: number | null;
  p2_ref_year_ht: number | null;
  p3_ref_year_ht: number | null;
  marche_total_ht: number | null;
};

async function fetchActiveSummary(token: string, lot: number): Promise<ActiveSummary> {
  const resp = await fetch(`${apiBaseUrl}/cpe/dalkia-ref/active-summary?lot=${lot}`, {
    headers: { ...buildAuthHeaders(token), "Content-Type": "application/json" },
  });
  if (!resp.ok) throw new Error(`Erreur ${resp.status}`);
  return resp.json() as Promise<ActiveSummary>;
}

async function fetchAllImports(token: string): Promise<ImportBatch[]> {
  const resp = await fetch(`${apiBaseUrl}/cpe/dalkia-ref/imports/all`, {
    headers: { ...buildAuthHeaders(token), "Content-Type": "application/json" },
  });
  if (!resp.ok) throw new Error(`Erreur ${resp.status}`);
  return resp.json() as Promise<ImportBatch[]>;
}

async function fetchAllDpgfImports(token: string): Promise<DpgfP1Import[]> {
  const resp = await fetch(`${apiBaseUrl}/cpe/dalkia-ref/dpgf-p1/imports/all`, {
    headers: { ...buildAuthHeaders(token), "Content-Type": "application/json" },
  });
  if (!resp.ok) throw new Error(`Erreur ${resp.status}`);
  return resp.json() as Promise<DpgfP1Import[]>;
}

// Entrée unifiée du journal (maître ou DPGF), triée par date.
type JournalEntry = {
  key: string;
  kind: "base" | "avenant" | "dpgf";
  lot: number;
  title: string;
  filename: string;
  date: string;
  is_active: boolean;
  detail: string;
};

async function syncP1Reference(token: string, importId: number): Promise<SyncP1Result> {
  const resp = await fetch(`${apiBaseUrl}/cpe/dalkia-ref/imports/${importId}/sync-p1-reference`, {
    method: "POST",
    headers: { ...buildAuthHeaders(token), "Content-Type": "application/json" },
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail ?? `Erreur ${resp.status}`);
  }
  return resp.json() as Promise<SyncP1Result>;
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
  const [syncP1Result, setSyncP1Result] = useState<{ id: number; res: SyncP1Result } | null>(null);
  const [sitesMsg, setSitesMsg] = useState<string | null>(null);

  // Dossier de marché : lot affiché + filtre du journal
  const [dossierLot, setDossierLot] = useState<1 | 2>(1);
  const [journalFilter, setJournalFilter] = useState<"tous" | "avenant" | "dpgf">("tous");

  // DPGF P1 révisé (import séparé)
  const dpgfFileInputRef = useRef<HTMLInputElement | null>(null);
  const [dpgfFile, setDpgfFile] = useState<File | null>(null);
  const [dpgfLot, setDpgfLot] = useState<1 | 2>(1);
  const [dpgfPreview, setDpgfPreview] = useState<DpgfP1Preview | null>(null);
  const [dpgfError, setDpgfError] = useState<string | null>(null);

  const syncSitesMutation = useMutation({
    mutationFn: () => syncCpeSites(token as string),
    onSuccess: (r) => setSitesMsg(`✓ ${r.total} sites CPE synchronisés (${r.created} créés, ${r.updated} mis à jour).`),
    onError: (err: unknown) => setSitesMsg(`⚠ ${err instanceof Error ? err.message : "Erreur"}`),
  });

  const syncP1Mutation = useMutation({
    mutationFn: (importId: number) => syncP1Reference(token as string, importId),
    onSuccess: (res, importId) => setSyncP1Result({ id: importId, res }),
    onError: (err: unknown, importId) =>
      setSyncP1Result({
        id: importId,
        res: { ok: false, message: err instanceof Error ? err.message : "Erreur de synchronisation" },
      }),
  });

  const importsQuery = useQuery({
    queryKey: ["cpe-dalkia-imports", token],
    queryFn: () => fetchImports(token as string),
    enabled: Boolean(token),
  });

  const summaryQuery = useQuery({
    queryKey: ["cpe-dalkia-active-summary", token, dossierLot],
    queryFn: () => fetchActiveSummary(token as string, dossierLot),
    enabled: Boolean(token),
  });

  const allImportsQuery = useQuery({
    queryKey: ["cpe-dalkia-imports-all", token],
    queryFn: () => fetchAllImports(token as string),
    enabled: Boolean(token),
  });

  const allDpgfQuery = useQuery({
    queryKey: ["cpe-dpgf-p1-imports-all", token],
    queryFn: () => fetchAllDpgfImports(token as string),
    enabled: Boolean(token),
  });

  const dpgfImportsQuery = useQuery({
    queryKey: ["cpe-dpgf-p1-imports", token],
    queryFn: () => fetchDpgfP1Imports(token as string),
    enabled: Boolean(token),
  });

  const dpgfPreviewMutation = useMutation({
    mutationFn: () => previewDpgfP1(token as string, dpgfFile as File, dpgfLot),
    onSuccess: (data) => {
      setDpgfPreview(data);
      setDpgfError(null);
    },
    onError: (err: unknown) => {
      setDpgfError(err instanceof Error ? err.message : "Erreur d'analyse");
      setDpgfPreview(null);
    },
  });

  const dpgfConfirmMutation = useMutation({
    mutationFn: () => confirmDpgfP1(token as string, dpgfFile as File, dpgfLot),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cpe-dpgf-p1-imports"] });
      queryClient.invalidateQueries({ queryKey: ["cpe-dpgf-p1-imports-all"] });
      setDpgfPreview(null);
      setDpgfFile(null);
      if (dpgfFileInputRef.current) dpgfFileInputRef.current.value = "";
    },
    onError: (err: unknown) => {
      setDpgfError(err instanceof Error ? err.message : "Erreur d'import");
    },
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
      queryClient.invalidateQueries({ queryKey: ["cpe-dalkia-imports-all"] });
      queryClient.invalidateQueries({ queryKey: ["cpe-dalkia-active-summary"] });
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

  return (
    <section className="panel stack-lg">
      {/* ── Header ── */}
      <div className="panel-header">
        <div>
          <p className="eyebrow">CPE DALKIA</p>
          <h2>Marché CPE DALKIA — dossier contractuel</h2>
          <p>
            L'état du marché en vigueur, le journal de tous les actes (offre finale, avenants,
            DPGF P1), et les imports. Ces données servent de référence aux contrôles, au suivi
            marché et à la performance.
          </p>
        </div>
        <Link className="secondary-link" to="/cpe">
          ← Retour CPE
        </Link>
      </div>

      {/* ── 1 · État du marché en vigueur ── */}
      {(() => {
        const s = summaryQuery.data;
        const lotLabel = dossierLot === 1 ? "Lot 1 — bâtiments" : "Lot 2 — piscines";
        return (
          <div className="section-block">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 8 }}>
              <h3 style={{ margin: 0 }}>1 · État du marché en vigueur</h3>
              <div style={{ display: "inline-flex", border: "1px solid #d1d5db", borderRadius: 8, overflow: "hidden" }}>
                {([1, 2] as const).map((l) => (
                  <button
                    key={l}
                    type="button"
                    onClick={() => setDossierLot(l)}
                    style={{
                      padding: "5px 14px", fontSize: 13, border: "none", cursor: "pointer",
                      background: dossierLot === l ? "#2563eb" : "white",
                      color: dossierLot === l ? "white" : "#374151",
                    }}
                  >
                    Lot {l}
                  </button>
                ))}
              </div>
            </div>
            {!s || !s.has_data ? (
              <p style={{ color: "#9ca3af", fontSize: 13 }}>
                Aucun référentiel actif pour le {lotLabel}. Importe le fichier maître dans le journal ci-dessous.
              </p>
            ) : (
              <>
                <p style={{ margin: "0 0 12px", fontSize: 12, color: "#6b7280" }}>
                  {lotLabel} · {s.filename} · en vigueur depuis le{" "}
                  {s.import_date ? new Date(s.import_date).toLocaleDateString("fr-FR") : "—"} · lu par les contrôles, le suivi marché et la performance.
                </p>
                <div className="detail-grid">
                  <div className="detail-card"><span>Sites</span><strong>{s.nb_sites ?? "—"}</strong></div>
                  <div className="detail-card"><span>Marché 8 ans</span><strong>{formatEur(s.marche_total_ht)}</strong></div>
                  <div className="detail-card"><span>P1 gaz {s.ref_year}</span><strong>{formatEur(s.p1_gaz_ref_year_ht)}</strong></div>
                  {s.p1_elec_ref_year_ht ? (
                    <div className="detail-card"><span>P1 élec {s.ref_year}</span><strong>{formatEur(s.p1_elec_ref_year_ht)}</strong></div>
                  ) : null}
                  <div className="detail-card"><span>P2 {s.ref_year}</span><strong>{formatEur(s.p2_ref_year_ht)}</strong></div>
                  <div className="detail-card"><span>P3 {s.ref_year}</span><strong>{formatEur(s.p3_ref_year_ht)}</strong></div>
                  <div className="detail-card"><span>Travaux APE</span><strong>{s.nb_ape ?? "—"}</strong></div>
                </div>
                {s.import_id ? (
                  <div style={{ marginTop: 12 }}>
                    <button type="button" className="secondary-button" onClick={() => setViewImportId(s.import_id)}>
                      Explorer les sites du référentiel
                    </button>
                  </div>
                ) : null}
              </>
            )}
          </div>
        );
      })()}

      {/* ── 2 · Journal du marché ── */}
      {(() => {
        const masterAll = allImportsQuery.data ?? [];
        const dpgfAll = allDpgfQuery.data ?? [];
        const lotMasters = masterAll
          .filter((i) => i.lot === dossierLot)
          .sort((a, b) => new Date(a.import_date).getTime() - new Date(b.import_date).getTime());
        const baseId = lotMasters[0]?.id;
        let entries: JournalEntry[] = [
          ...lotMasters.map((i) => ({
            key: `m${i.id}`,
            kind: (i.id === baseId ? "base" : "avenant") as JournalEntry["kind"],
            lot: i.lot,
            title: i.id === baseId ? "Offre finale (base)" : "Avenant — mise à jour du marché",
            filename: i.filename,
            date: i.import_date,
            is_active: i.is_active,
            detail: `${i.nb_sites} sites · P2/P3 ${i.nb_p2p3_rows} · APE ${i.nb_ape_rows}`,
          })),
          ...dpgfAll
            .filter((i) => i.lot === dossierLot)
            .map((i) => ({
              key: `d${i.id}`,
              kind: "dpgf" as JournalEntry["kind"],
              lot: i.lot,
              title: "DPGF P1 — révision de prix",
              filename: i.filename,
              date: i.import_date,
              is_active: i.is_active,
              detail: `${i.nb_lines} lignes (3 niveaux)`,
            })),
        ];
        entries = entries
          .filter((e) =>
            journalFilter === "tous"
              ? true
              : journalFilter === "avenant"
                ? e.kind === "base" || e.kind === "avenant"
                : e.kind === "dpgf",
          )
          .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

        const KIND_BADGE: Record<JournalEntry["kind"], { label: string; color: string; bg: string }> = {
          base: { label: "base", color: "#6b7280", bg: "#f3f4f6" },
          avenant: { label: "avenant", color: "#92400e", bg: "#fef3c7" },
          dpgf: { label: "DPGF", color: "#1d4ed8", bg: "#eff6ff" },
        };

        return (
          <div className="section-block">
            <h3 style={{ margin: "0 0 4px" }}>2 · Journal du marché</h3>
            <p style={{ margin: "0 0 10px", fontSize: 13, color: "#6b7280" }}>
              Tous les actes contractuels (Lot {dossierLot}), du plus récent au plus ancien. Les versions remplacées sont conservées pour l'audit.
            </p>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
              {(["tous", "avenant", "dpgf"] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setJournalFilter(f)}
                  style={{
                    padding: "4px 12px", fontSize: 12, borderRadius: 8, cursor: "pointer",
                    border: journalFilter === f ? "none" : "1px solid #e5e7eb",
                    background: journalFilter === f ? "#2563eb" : "white",
                    color: journalFilter === f ? "white" : "#6b7280",
                  }}
                >
                  {f === "tous" ? "Tous" : f === "avenant" ? "Avenants & base" : "DPGF P1"}
                </button>
              ))}
            </div>
            {entries.length === 0 ? (
              <p style={{ color: "#9ca3af", fontSize: 13 }}>Aucun acte pour ce filtre. Importe un fichier ci-dessous.</p>
            ) : (
              <div>
                {entries.map((e) => {
                  const badge = KIND_BADGE[e.kind];
                  return (
                    <div key={e.key} style={{ display: "flex", gap: 12, alignItems: "flex-start", padding: "10px 0", borderTop: "1px solid #f3f4f6", opacity: e.is_active || e.kind === "base" ? 1 : 0.6 }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 14, fontWeight: 600 }}>{e.title}</span>
                          <span style={{ fontSize: 11, padding: "2px 7px", borderRadius: 6, background: badge.bg, color: badge.color }}>{badge.label}</span>
                          {e.is_active ? (
                            <span style={{ fontSize: 11, padding: "2px 7px", borderRadius: 6, background: "#dcfce7", color: "#15803d" }}>en vigueur</span>
                          ) : e.kind !== "base" ? (
                            <span style={{ fontSize: 11, padding: "2px 7px", borderRadius: 6, background: "#f3f4f6", color: "#6b7280" }}>remplacé (conservé)</span>
                          ) : null}
                        </div>
                        <div style={{ fontSize: 12, color: "#6b7280", margin: "3px 0 0" }}>
                          {new Date(e.date).toLocaleDateString("fr-FR")} · {e.filename} · {e.detail}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })()}

      {/* ── Action : initialiser les sites CPE depuis le référentiel ── */}
      <div className="section-block" style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <button
          type="button"
          className="secondary-button"
          disabled={syncSitesMutation.isPending}
          onClick={() => syncSitesMutation.mutate()}
          title="Crée/met à jour les sites CPE (bilan, NB par année) depuis le référentiel DALKIA actif"
        >
          {syncSitesMutation.isPending ? "Synchronisation..." : "Initialiser / mettre à jour les sites CPE"}
        </button>
        <span style={{ fontSize: 12, color: sitesMsg?.startsWith("✓") ? "#15803d" : "#b45309" }}>
          {sitesMsg ?? "Alimente le volet performance (bilan /cpe) à partir de l'import DALKIA actif."}
        </span>
      </div>

      {/* ── Formulaire d'import (fichier maître) ── */}
      <div className="section-block">
        <div className="section-heading">
          <h3>Importer un fichier maître (offre finale / avenant)</h3>
          <p>
            Fichier Excel DALKIA complet (.xlsx/.xlsm) — remplace le référentiel du lot et devient
            l'état en vigueur (l'ancienne version est conservée au journal). Onglets parsés : P2/P3,
            cibles GAZ/ELEC, P1 gaz, P1 élec (Lot 2), travaux APE, RECAP.
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

      {/* ── Import DPGF P1 révisé (livrable séparé après OS) ── */}
      <div className="section-block">
        <div className="section-heading">
          <h3>Importer un DPGF P1 révisé (après OS)</h3>
          <p>
            Chemin <strong>séparé</strong> du fichier maître. Quand DALKIA livre un{" "}
            <code>P1 - DPGF LOT x …xlsx</code> suite à un OS impactant le prix gaz, importe-le ici :
            seul le P1 révisé du lot est mis à jour (3 niveaux : contrat / Rév Temp / Rév T° &amp; prix).
            Cela <strong>ne modifie pas</strong> le référentiel maître (P2/P3/APE/cibles/RECAP) ni le
            « prévu P1 » du suivi marché (qui reste au niveau contrat).
          </p>
        </div>

        {/* Statut des DPGF P1 actifs */}
        <div className="detail-grid">
          {[1, 2].map((l) => {
            const active = (dpgfImportsQuery.data ?? []).find((i) => i.lot === l && i.is_active);
            return (
              <div className="detail-card" key={l}>
                <span>DPGF P1 actif — Lot {l}</span>
                <strong>
                  {active
                    ? `${active.nb_lines} lignes · ${active.filename} · ${new Date(active.import_date).toLocaleDateString("fr-FR")}`
                    : "Aucun DPGF P1 importé"}
                </strong>
              </div>
            );
          })}
        </div>

        <form
          className="form"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (dpgfFile) dpgfPreviewMutation.mutate();
          }}
        >
          <div className="form-grid">
            <label className="field">
              <span>Lot</span>
              <select
                value={dpgfLot}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                  setDpgfLot(Number(e.target.value) as 1 | 2);
                  setDpgfPreview(null);
                }}
              >
                <option value={1}>Lot 1 — Écoles, sport (L1)</option>
                <option value={2}>Lot 2 — Piscines (L2)</option>
              </select>
            </label>
            <label className="field">
              <span>Fichier DPGF P1 (.xlsx)</span>
              <input
                ref={dpgfFileInputRef}
                type="file"
                accept=".xlsx,.xlsm"
                onChange={(e: ChangeEvent<HTMLInputElement>) => {
                  setDpgfFile(e.target.files?.[0] ?? null);
                  setDpgfPreview(null);
                  setDpgfError(null);
                }}
              />
            </label>
          </div>
          {dpgfError ? <p className="error-text">{dpgfError}</p> : null}
          {dpgfConfirmMutation.isSuccess ? (
            <p className="success-text">✓ DPGF P1 Lot {dpgfLot} importé. Le P1 révisé est mis à jour.</p>
          ) : null}
          <div className="form-actions">
            <button type="submit" className="secondary-button" disabled={!dpgfFile || dpgfPreviewMutation.isPending}>
              {dpgfPreviewMutation.isPending ? "Analyse en cours..." : "Analyser le DPGF P1"}
            </button>
          </div>
        </form>

        {/* Aperçu : totaux par niveau × année */}
        {dpgfPreview ? (
          <>
            <div className="section-heading" style={{ marginTop: 12 }}>
              <h4>Aperçu — {dpgfPreview.filename}</h4>
              <p>
                {dpgfPreview.nb_lines} lignes parsées. Vérifie les totaux avant de confirmer.
              </p>
            </div>
            {dpgfPreview.warnings.length > 0 ? (
              <ul className="error-text" style={{ fontSize: 12 }}>
                {dpgfPreview.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            ) : null}
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.3)" }}>
                    <th style={{ textAlign: "left", padding: "6px 12px" }}>Niveau P1</th>
                    {Object.keys(dpgfPreview.totals.contrat ?? dpgfPreview.totals[Object.keys(dpgfPreview.totals)[0]] ?? {})
                      .sort()
                      .map((y) => (
                        <th key={y} style={{ textAlign: "right", padding: "6px 12px" }}>
                          {y}
                        </th>
                      ))}
                  </tr>
                </thead>
                <tbody>
                  {["contrat", "rev_temp", "rev_temp_prix"].map((level) => {
                    const byYear = dpgfPreview.totals[level];
                    if (!byYear) return null;
                    const years = Object.keys(byYear).sort();
                    return (
                      <tr key={level} style={{ borderBottom: "1px solid rgba(148,163,184,0.1)" }}>
                        <td style={{ padding: "6px 12px", fontWeight: 600 }}>{DPGF_LEVEL_LABELS[level]}</td>
                        {years.map((y) => (
                          <td key={y} style={{ textAlign: "right", padding: "6px 12px" }}>
                            {formatEur(byYear[y])}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="form-actions" style={{ marginTop: 12 }}>
              <button
                type="button"
                className="primary-button"
                disabled={dpgfConfirmMutation.isPending}
                onClick={() => dpgfConfirmMutation.mutate()}
              >
                {dpgfConfirmMutation.isPending ? "Import en cours..." : "Confirmer l'import du DPGF P1"}
              </button>
            </div>
          </>
        ) : null}
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
              <span>Lignes RECAP financier</span>
              <strong>{preview.nb_recap_rows}</strong>
            </div>
            <div className="detail-card">
              <span>Périodes détectées</span>
              <strong>{preview.period_labels.length} ({preview.period_labels[0]} → {preview.period_labels[preview.period_labels.length - 1]})</strong>
            </div>
          </div>

          {/* Récapitulatif financier global (RECAP MARCHE) */}
          {preview.recap_summary && Object.keys(preview.recap_summary.bilan_marche_ht ?? {}).length > 0 ? (
            <>
              <div className="section-heading" style={{ marginTop: 16 }}>
                <h4>Bilan financier du marché (RECAP MARCHE) — sur toute la durée</h4>
              </div>
              <div className="detail-grid">
                {Object.entries(preview.recap_summary.bilan_marche_ht).map(([cat, val]) => (
                  <div className="detail-card" key={cat}>
                    <span>{cat}</span>
                    <strong style={cat === "TOTAL" ? { color: "#1d4ed8" } : undefined}>{formatEur(val)} HT</strong>
                  </div>
                ))}
              </div>

              <div className="section-heading" style={{ marginTop: 16 }}>
                <h4>Redevances annuelles P1 / P2 / P3 (€ HT)</h4>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.3)" }}>
                      <th style={{ textAlign: "left", padding: "6px 12px" }}>Année</th>
                      <th style={{ textAlign: "right", padding: "6px 12px" }}>P1 gaz</th>
                      <th style={{ textAlign: "right", padding: "6px 12px" }}>P2 maintenance</th>
                      <th style={{ textAlign: "right", padding: "6px 12px" }}>P3 travaux</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(preview.recap_summary.by_year).map(([year, d]) => (
                      <tr key={year} style={{ borderBottom: "1px solid rgba(148,163,184,0.1)" }}>
                        <td style={{ padding: "5px 12px", fontWeight: 600 }}>{year}</td>
                        <td style={{ padding: "5px 12px", textAlign: "right" }}>{formatEur(d.p1_total_ht)}</td>
                        <td style={{ padding: "5px 12px", textAlign: "right" }}>{formatEur(d.p2_total_ht)}</td>
                        <td style={{ padding: "5px 12px", textAlign: "right" }}>{formatEur(d.p3_total_ht)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {preview.recap_summary.facteur_co2_gaz != null ? (
                <p style={{ fontSize: 12, color: "#94a3b8", marginTop: 8 }}>
                  Facteurs CO₂ contractuels — gaz : {preview.recap_summary.facteur_co2_gaz} T/MWh · élec : {preview.recap_summary.facteur_co2_elec} T/MWh
                </p>
              ) : null}
            </>
          ) : null}

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

          {/* Aperçu complet classifié */}
          {preview.classified ? <ClassifiedPreview data={preview.classified} /> : null}

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
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={syncP1Mutation.isPending}
                    onClick={() => syncP1Mutation.mutate(imp.id)}
                    title="Met à jour la référence d'acompte P1 gaz (contrôle de factures) depuis le RECAP de cet import"
                  >
                    {syncP1Mutation.isPending && syncP1Mutation.variables === imp.id
                      ? "Synchronisation..."
                      : "Synchroniser la réf. P1"}
                  </button>
                </div>
              ) : null}
              {syncP1Result && syncP1Result.id === imp.id ? (
                <p
                  style={{
                    fontSize: 12,
                    marginTop: 8,
                    color: syncP1Result.res.ok ? "#15803d" : "#b45309",
                  }}
                >
                  {syncP1Result.res.ok ? "✓ " : "⚠ "}
                  {syncP1Result.res.message}
                  {syncP1Result.res.ok && syncP1Result.res.amounts_by_year ? (
                    <>
                      {" "}
                      ({Object.entries(syncP1Result.res.amounts_by_year)
                        .map(([y, v]) => `${y}: ${Number(v).toLocaleString("fr-FR")} €`)
                        .join(" · ")})
                    </>
                  ) : null}
                </p>
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

// ─────────────────────────────────────────────────────────────────────────────
// Aperçu complet classifié (onglets par catégorie)
// ─────────────────────────────────────────────────────────────────────────────

type ClassifiedTab = "p2p3" | "cibles_gaz" | "cibles_elec" | "p1_gaz" | "bpu" | "ape" | "recap";

function ClassifiedPreview({ data }: { data: ClassifiedData }) {
  const [tab, setTab] = useState<ClassifiedTab>("p2p3");
  const years = data.years;

  const tabs: { key: ClassifiedTab; label: string; count: number }[] = [
    { key: "p2p3", label: "P2 / P3", count: data.p2p3.length },
    { key: "cibles_gaz", label: "Cibles GAZ", count: data.cibles_gaz.length },
    { key: "cibles_elec", label: "Cibles ELEC", count: data.cibles_elec.length },
    { key: "p1_gaz", label: "P1 gaz", count: data.p1_gaz.length },
    { key: "bpu", label: "BPU travaux", count: data.bpu?.length ?? 0 },
    { key: "ape", label: "Travaux APE", count: data.ape.length },
    { key: "recap", label: "RECAP financier", count: data.recap_bilan.length },
  ];

  const th: React.CSSProperties = { textAlign: "right", padding: "5px 8px", whiteSpace: "nowrap", background: "#0f172a" };
  const thL: React.CSSProperties = { textAlign: "left", padding: "5px 8px", whiteSpace: "nowrap", background: "#0f172a" };
  const td: React.CSSProperties = { textAlign: "right", padding: "4px 8px", whiteSpace: "nowrap" };
  const tdL: React.CSSProperties = { textAlign: "left", padding: "4px 8px" };
  const trB = { borderBottom: "1px solid rgba(148,163,184,0.1)" };

  return (
    <div className="section-block" style={{ marginTop: 20 }}>
      <div className="section-heading">
        <h4>Aperçu complet — toutes les données parsées</h4>
        <p style={{ fontSize: 12, color: "#94a3b8" }}>Vérifier l'exhaustivité avant de confirmer l'import.</p>
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            className={`secondary-button${tab === t.key ? "" : ""}`}
            style={tab === t.key ? { background: "rgba(59,130,246,0.2)", borderColor: "#3b82f6" } : {}}
            onClick={() => setTab(t.key)}
          >
            {t.label} <span style={{ opacity: 0.6, fontSize: 11 }}>({t.count})</span>
          </button>
        ))}
      </div>

      <div style={{ overflowX: "auto", maxHeight: 460, overflowY: "auto", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 8 }}>
        {/* ── P2 / P3 ── */}
        {tab === "p2p3" && (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead style={{ position: "sticky", top: 0 }}>
              <tr style={trB}>
                <th style={thL}>Site</th>
                {years.map((y) => <th key={"p2" + y} style={th}>P2 {y}</th>)}
                {years.map((y) => <th key={"p3" + y} style={th}>P3 {y}</th>)}
              </tr>
            </thead>
            <tbody>
              {data.p2p3.map((s) => (
                <tr key={s.code_site} style={trB}>
                  <td style={tdL}><strong>{s.code_site}</strong> <span style={{ color: "#94a3b8" }}>{s.nom_batiment}</span></td>
                  {years.map((y) => <td key={"p2" + y} style={td}>{formatEur(s.by_year[y]?.p2)}</td>)}
                  {years.map((y) => <td key={"p3" + y} style={td}>{formatEur(s.by_year[y]?.p3)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* ── Cibles GAZ / ELEC ── */}
        {(tab === "cibles_gaz" || tab === "cibles_elec") && (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead style={{ position: "sticky", top: 0 }}>
              <tr style={trB}>
                <th style={thL}>Site</th>
                <th style={th}>Réf. globale</th>
                <th style={th}>DJU</th>
                {years.map((y) => <th key={y} style={th}>{y}</th>)}
              </tr>
            </thead>
            <tbody>
              {(tab === "cibles_gaz" ? data.cibles_gaz : data.cibles_elec).map((s) => (
                <tr key={s.code_site} style={trB}>
                  <td style={tdL}><strong>{s.code_site}</strong></td>
                  <td style={td}>{formatMwh(s.ref_globale)}</td>
                  <td style={td}>{s.dju ?? "—"}</td>
                  {years.map((y) => <td key={y} style={td}>{formatMwh(s.by_year[y])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* ── P1 gaz ── */}
        {tab === "p1_gaz" && (
          <div>
            {data.p1_tarifs && data.p1_tarifs.length > 0 ? (
              <div style={{ padding: 12 }}>
                <h4 style={{ margin: "0 0 8px", fontSize: 13, color: "#e2e8f0" }}>
                  Composants de prix & coefficients de révision Pu (Annexe 6)
                </h4>
                <p style={{ fontSize: 11, color: "#94a3b8", margin: "0 0 8px" }}>
                  Pu_GAZ = Pu₀ × (a + b·PEG/PEG₀ + c·TVD/TVD₀ + d·CEE/CEE₀ + e·TICGN/TICGN₀) — somme a+b+c+d+e = 1.
                </p>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, marginBottom: 12 }}>
                  <thead><tr style={trB}>
                    <th style={thL}>Tarif</th>
                    <th style={th}>P0 fourn.</th><th style={th}>PEG</th><th style={th}>Achemin.</th>
                    <th style={th}>CEE</th><th style={th}>TICGN</th><th style={th}>Marge %</th>
                    <th style={th}>Pu₀ (€/MWhPCS)</th>
                    <th style={th}>a</th><th style={th}>b</th><th style={th}>c</th><th style={th}>d</th><th style={th}>e</th>
                  </tr></thead>
                  <tbody>
                    {data.p1_tarifs.map((t) => (
                      <tr key={t.type_tarif} style={trB}>
                        <td style={tdL}><strong>{t.type_tarif}</strong></td>
                        <td style={td}>{t.p0_fournisseur ?? "—"}</td>
                        <td style={td}>{t.ref_peg ?? "—"}</td>
                        <td style={td}>{t.terme_acheminement ?? "—"}</td>
                        <td style={td}>{t.obligation_cee ?? "—"}</td>
                        <td style={td}>{t.ticgn ?? "—"}</td>
                        <td style={td}>{t.marge_exploitant_pct != null ? (t.marge_exploitant_pct * 100).toFixed(2) : "—"}</td>
                        <td style={td}><strong>{t.prix_unitaire_ht ?? "—"}</strong></td>
                        <td style={td}>{t.coef_a?.toFixed(5) ?? "—"}</td>
                        <td style={td}>{t.coef_b?.toFixed(5) ?? "—"}</td>
                        <td style={td}>{t.coef_c?.toFixed(5) ?? "—"}</td>
                        <td style={td}>{t.coef_d?.toFixed(5) ?? "—"}</td>
                        <td style={td}>{t.coef_e?.toFixed(5) ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead style={{ position: "sticky", top: 0 }}>
                <tr style={trB}>
                  <th style={thL}>Site</th>
                  <th style={thL}>PCE</th>
                  <th style={th}>Tarif</th>
                  <th style={th}>Pu (€/MWh)</th>
                  {years.map((y) => <th key={y} style={th}>P10 {y}</th>)}
                </tr>
              </thead>
              <tbody>
                {data.p1_gaz.map((s) => (
                  <tr key={s.code_site} style={trB}>
                    <td style={tdL}><strong>{s.code_site}</strong></td>
                    <td style={{ ...tdL, fontFamily: "monospace", fontSize: 11 }}>{s.pce ?? "—"}</td>
                    <td style={td}>{s.type_tarif ?? "—"}</td>
                    <td style={td}>{s.prix_unitaire_ht ?? "—"}</td>
                    {years.map((y) => <td key={y} style={td}>{formatEur(s.by_year[y])}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── BPU travaux P3 (Annexe 7) ── */}
        {tab === "bpu" && (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead style={{ position: "sticky", top: 0 }}>
              <tr style={trB}>
                <th style={thL}>Catégorie</th>
                <th style={thL}>Code</th>
                <th style={thL}>Libellé</th>
                <th style={thL}>Spécificité / famille</th>
                <th style={th}>Coût unitaire</th>
                <th style={thL}>Unité</th>
                <th style={th}>Nuit</th>
                <th style={th}>Sam/Dim</th>
                <th style={th}>Coef (max)</th>
              </tr>
            </thead>
            <tbody>
              {(data.bpu ?? []).map((r, i) => (
                <tr key={i} style={trB}>
                  <td style={tdL}>
                    <span style={{ fontSize: 10, fontWeight: 700, color: r.categorie === "prestation" ? "#16a34a" : r.categorie === "taux_horaire" ? "#2563eb" : "#b45309" }}>
                      {r.categorie === "prestation" ? "PRESTA" : r.categorie === "taux_horaire" ? "TAUX/h" : "COEF"}
                    </span>
                  </td>
                  <td style={{ ...tdL, fontFamily: "monospace", fontSize: 11 }}>{r.code ?? "—"}</td>
                  <td style={{ ...tdL, maxWidth: 240, whiteSpace: "normal", color: "#cbd5e1" }}>{r.libelle ?? "—"}</td>
                  <td style={{ ...tdL, maxWidth: 180, whiteSpace: "normal", color: "#94a3b8", fontSize: 11 }}>{r.specificite ?? r.famille ?? "—"}</td>
                  <td style={td}>{r.cout_unitaire != null ? r.cout_unitaire.toLocaleString("fr-FR") : "—"}</td>
                  <td style={{ ...tdL, fontSize: 11 }}>{r.unite ?? "—"}</td>
                  <td style={td}>{r.cout_nuit ?? "—"}</td>
                  <td style={td}>{r.cout_samedi != null ? `${r.cout_samedi}/${r.cout_dimanche ?? "—"}` : "—"}</td>
                  <td style={td}>{r.coefficient != null ? `${r.coefficient}${r.coefficient_max != null ? ` (${r.coefficient_max})` : ""}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* ── Travaux APE ── */}
        {tab === "ape" && (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead style={{ position: "sticky", top: 0 }}>
              <tr style={trB}>
                <th style={thL}>Site</th>
                <th style={thL}>Description</th>
                <th style={th}>Année</th>
                <th style={th}>Montant HT</th>
                <th style={th}>CEE €</th>
                <th style={th}>Gain MWh</th>
                <th style={th}>CO₂ t/an</th>
              </tr>
            </thead>
            <tbody>
              {data.ape.map((r, i) => (
                <tr key={i} style={trB}>
                  <td style={tdL}><strong>{r.code_site}</strong></td>
                  <td style={{ ...tdL, maxWidth: 280, whiteSpace: "normal", color: "#cbd5e1" }}>{r.description_ape ?? "—"}</td>
                  <td style={td}>{r.annee_achevement ?? "—"}</td>
                  <td style={td}>{formatEur(r.montant_ape_ht)}</td>
                  <td style={td}>{formatEur(r.cee_eur)}</td>
                  <td style={td}>{r.gain_energetique_mwhpci != null ? r.gain_energetique_mwhpci.toLocaleString("fr-FR", { maximumFractionDigits: 1 }) : "—"}</td>
                  <td style={td}>{r.emission_co2_evitee ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* ── RECAP financier ── */}
        {tab === "recap" && (
          <div style={{ padding: 12 }}>
            <h4 style={{ margin: "0 0 8px", fontSize: 13, color: "#e2e8f0" }}>Engagements de consommation (MWh PCI)</h4>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, marginBottom: 16 }}>
              <thead><tr style={trB}><th style={thL}>Métrique</th>{years.map((y) => <th key={y} style={th}>{y}</th>)}</tr></thead>
              <tbody>
                {Object.entries(data.recap_engagement).map(([metric, byYear]) => (
                  <tr key={metric} style={trB}>
                    <td style={tdL}>{metric}</td>
                    {years.map((y) => <td key={y} style={td}>{(byYear as Record<string, number | null>)[y] != null ? Number((byYear as Record<string, number | null>)[y]).toLocaleString("fr-FR", { maximumFractionDigits: 1 }) : "—"}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>

            <h4 style={{ margin: "0 0 8px", fontSize: 13, color: "#e2e8f0" }}>Redevances annuelles (€ HT)</h4>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, marginBottom: 16 }}>
              <thead><tr style={trB}><th style={thL}>Poste</th>{years.map((y) => <th key={y} style={th}>{y}</th>)}</tr></thead>
              <tbody>
                {Object.entries(data.recap_redevances).map(([metric, byYear]) => (
                  <tr key={metric} style={trB}>
                    <td style={tdL}>{metric}</td>
                    {years.map((y) => <td key={y} style={td}>{formatEur((byYear as Record<string, number | null>)[y])}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>

            <h4 style={{ margin: "0 0 8px", fontSize: 13, color: "#e2e8f0" }}>Bilan sur la durée du marché</h4>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead><tr style={trB}><th style={thL}>Poste</th><th style={th}>Montant HT</th><th style={thL}>Unité</th></tr></thead>
              <tbody>
                {data.recap_bilan.map((r, i) => (
                  <tr key={i} style={trB}>
                    <td style={tdL}>{r.poste}</td>
                    <td style={td}>{formatEur(r.value)}</td>
                    <td style={tdL}>{r.unit ?? "€ HT"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
