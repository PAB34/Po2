import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import BpuEditableTable from "../components/BpuEditableTable";
import BpuTimelineChart from "../components/BpuTimelineChart";
import { useAuth } from "../providers/AuthProvider";
import {
  fetchBpuDocuments,
  fetchBpuFormula,
  fetchBpuTimeline,
  fetchBpuTurpeEvolution,
  triggerBpuImport,
  triggerBpuXlsxImport,
  type BpuDocumentSummary,
  type BpuFormula,
  type BpuImportResponse,
  type BpuXlsxImportResponse,
  type BpuTurpeEvolutionPoint,
  type BpuTimelineFilters,
  type BpuTimelinePoint,
} from "../lib/api";

const STATUS_BADGE: Record<string, { label: string; color: string }> = {
  ok:          { label: "OK texte",  color: "#4ade80" },
  ocr_ok:      { label: "OK OCR",    color: "#60a5fa" },
  ocr_review:  { label: "À revoir",  color: "#fbbf24" },
  manual:      { label: "Manuel",    color: "#94a3b8" },
  pending:     { label: "En attente",color: "#94a3b8" },
  error:       { label: "Erreur",    color: "#f87171" },
};

function uniq<T extends string | number>(values: (T | null | undefined)[]): T[] {
  const set = new Set<T>();
  for (const v of values) { if (v != null) set.add(v); }
  return Array.from(set).sort((a, b) => String(a).localeCompare(String(b)));
}

type TabKey = "timeline" | "turpe" | "perspective" | "documents" | "edition";

const TABS: { key: TabKey; label: string }[] = [
  { key: "timeline",  label: "Timeline" },
  { key: "turpe",     label: "TURPE" },
  { key: "perspective", label: "Perspective" },
  { key: "documents", label: "Documents & Import" },
  { key: "edition",   label: "Édition tableau" },
];

export default function EnergieBpuPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabKey>("timeline");

  const [chartFilters, setChartFilters] = useState<BpuTimelineFilters>({
    segment_code: "C4",
    period_code: "HPH",
  });
  const [docSupplier, setDocSupplier] = useState("");
  const [docYear,     setDocYear]     = useState("");
  const [docLot,      setDocLot]      = useState("");
  const [docStatus,   setDocStatus]   = useState("");

  const formulaQuery = useQuery<BpuFormula>({
    queryKey: ["bpu", "formula"],
    queryFn: () => fetchBpuFormula(token ?? ""),
    enabled: !!token,
  });
  const docsQuery = useQuery<BpuDocumentSummary[]>({
    queryKey: ["bpu", "documents", docSupplier, docYear, docLot, docStatus],
    queryFn: () => fetchBpuDocuments(token ?? "", {
      supplier: docSupplier || undefined,
      valid_year: docYear ? Number(docYear) : undefined,
      lot_number: docLot ? Number(docLot) : undefined,
      extraction_status: docStatus || undefined,
    }),
    enabled: !!token,
  });
  const timelineQuery = useQuery<BpuTimelinePoint[]>({
    queryKey: ["bpu", "timeline", chartFilters],
    queryFn: () => fetchBpuTimeline(token ?? "", chartFilters),
    enabled: !!token,
  });
  const turpeQuery = useQuery<BpuTurpeEvolutionPoint[]>({
    queryKey: ["bpu", "turpe-evolution"],
    queryFn: () => fetchBpuTurpeEvolution(token ?? ""),
    enabled: !!token,
  });
  const importMutation = useMutation<BpuImportResponse, Error, { force: boolean }>({
    mutationFn: ({ force }) => triggerBpuImport(token ?? "", { force, enable_ocr: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bpu"] }),
  });
  const xlsxImportMutation = useMutation<BpuXlsxImportResponse, Error, { force: boolean }>({
    mutationFn: ({ force }) => triggerBpuXlsxImport(token ?? "", { force }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bpu"] }),
  });

  const segmentChoices = useMemo(() => formulaQuery.data?.segments ?? [], [formulaQuery.data]);
  const periodChoices  = useMemo(() => formulaQuery.data?.periods ?? [],  [formulaQuery.data]);
  const supplierOpts   = useMemo(() => uniq((docsQuery.data ?? []).map(d => d.supplier)),   [docsQuery.data]);
  const yearOpts       = useMemo(() => uniq((docsQuery.data ?? []).map(d => d.valid_year)), [docsQuery.data]);

  const stats = useMemo(() => {
    const docs = docsQuery.data ?? [];
    const byStatus: Record<string, number> = {};
    for (const d of docs) byStatus[d.extraction_status] = (byStatus[d.extraction_status] ?? 0) + 1;
    return { total: docs.length, byStatus };
  }, [docsQuery.data]);

  if (!token) {
    return <div style={{ padding: 32, color: "#94a3b8" }}>Connectez-vous pour accéder aux BPU.</div>;
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "24px 20px" }}>

      {/* ── En-tête ───────────────────────────────────────────────────── */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: "0.78rem", color: "#64748b", marginBottom: 6 }}>
          <Link to="/energie" style={{ color: "#60a5fa", textDecoration: "none" }}>Énergie</Link>
          <span style={{ margin: "0 6px", color: "#475569" }}>›</span>
          <span>Historique des BPU</span>
        </div>
        <h1 style={{ fontSize: "1.4rem", fontWeight: 600, margin: 0, lineHeight: 1.3 }}>
          Bordereaux de Prix Unitaires
        </h1>
        <p style={{ fontSize: "0.83rem", color: "#64748b", marginTop: 4, maxWidth: 620 }}>
          Évolution des composantes de la formule de tarification sur les marchés Hérault Énergies (2021–2026).
        </p>
      </div>

      {/* ── Onglets ───────────────────────────────────────────────────── */}
      <div style={{ borderBottom: "1px solid rgba(148,163,184,0.25)", marginBottom: 24, display: "flex", gap: 0 }}>
        {TABS.map(tab => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: "8px 16px",
              fontSize: "0.85rem",
              fontWeight: activeTab === tab.key ? 600 : 400,
              color: activeTab === tab.key ? "#60a5fa" : "#64748b",
              background: "none",
              border: "none",
              borderBottom: activeTab === tab.key ? "2px solid #3b82f6" : "2px solid transparent",
              cursor: "pointer",
              marginBottom: -1,
              transition: "color 0.15s",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ════════════════════════════════════════════════════════════════
          Onglet TIMELINE
      ════════════════════════════════════════════════════════════════ */}
      {activeTab === "timeline" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

          {/* Barre de filtres */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end", padding: "12px 16px", background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 10 }}>
            <FilterSelect
              label="Segment"
              value={chartFilters.segment_code ?? ""}
              onChange={v => setChartFilters(f => ({ ...f, segment_code: v || undefined }))}
              options={[{ value: "", label: "Tous" }, ...segmentChoices.map(s => ({ value: s.code, label: `${s.code} — ${s.label}` }))]}
            />
            <FilterSelect
              label="Poste"
              value={chartFilters.period_code ?? ""}
              onChange={v => setChartFilters(f => ({ ...f, period_code: v || undefined }))}
              options={[{ value: "", label: "Tous" }, ...periodChoices.map(p => ({ value: p.code, label: `${p.code} — ${p.label}` }))]}
            />
            <FilterSelect
              label="Fournisseur"
              value={chartFilters.supplier ?? ""}
              onChange={v => setChartFilters(f => ({ ...f, supplier: v || undefined }))}
              options={[{ value: "", label: "Tous" }, { value: "EDF", label: "EDF" }, { value: "ENGIE", label: "ENGIE" }, { value: "TOTALENERGIES", label: "TotalEnergies" }]}
            />
            <FilterSelect
              label="Lot"
              value={chartFilters.lot_number?.toString() ?? ""}
              onChange={v => setChartFilters(f => ({ ...f, lot_number: v ? Number(v) : undefined }))}
              options={[{ value: "", label: "Tous" }, { value: "1", label: "Lot 1" }, { value: "2", label: "Lot 2" }, { value: "3", label: "Lot 3" }, { value: "7", label: "Lot 7 gaz" }]}
            />
          </div>

          {/* Graphique */}
          <div style={{ background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 10, padding: "20px 16px" }}>
            {timelineQuery.isLoading ? (
              <div style={{ height: 340, display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", fontSize: "0.85rem" }}>
                Chargement…
              </div>
            ) : timelineQuery.isError ? (
              <ErrorBanner message={(timelineQuery.error as Error).message} />
            ) : (
              <BpuTimelineChart
                points={timelineQuery.data ?? []}
                formula={formulaQuery.data}
                includeTotal
              />
            )}
          </div>

          {/* Formule */}
          {formulaQuery.data && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", padding: "10px 14px", background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 8 }}>
              <span style={{ fontSize: "0.78rem", color: "#475569" }}>Formule :</span>
              <code style={{ fontSize: "0.83rem", color: "#93c5fd", background: "rgba(59,130,246,0.12)", padding: "2px 10px", borderRadius: 4, border: "1px solid rgba(59,130,246,0.2)" }}>
                {formulaQuery.data.expression}
              </code>
            </div>
          )}

          {/* Définitions des composantes */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 10 }}>
            {[
              {
                code: "fourniture", label: "Fourniture", color: "#2563eb",
                desc: "Prix du marché de gros de l'électricité, fixé à la signature du marché.",
                example: "Ex. : ENGIE 2023, Lot 1 — 142 €/MWh en HPH (le poste le plus lourd de la facture).",
              },
              {
                code: "capacite", label: "Capacité", color: "#f59e0b",
                desc: "Mécanisme de capacité réglementé par RTE pour garantir l'équilibre offre/demande en hiver.",
                example: "Ex. : ~4–8 €/MWh selon les années ; indexé sur le prix des certificats de capacité RTE, très volatile en hiver froid.",
              },
              {
                code: "cee", label: "CEE", color: "#10b981",
                desc: "Obligation légale de financement des Certificats d'Économies d'Énergie.",
                example: "Ex. : ~1–3 €/MWh ; répercuté par le fournisseur sur tous les postes tarifaires.",
              },
              {
                code: "go", label: "Garanties d'Origine", color: "#a855f7",
                desc: "Option contractuelle pour attester l'origine renouvelable de l'électricité fournie.",
                example: "Ex. : 0,5–1,5 €/MWh en option « électricité verte » ; absent si le marché ne prévoit pas cette clause.",
              },
            ].map(({ code, label, desc, example, color }) => (
              <div key={code} style={{ padding: "12px 14px", background: "rgba(15,23,42,0.4)", border: `1px solid rgba(148,163,184,0.12)`, borderLeftColor: color, borderLeftWidth: 3, borderLeftStyle: "solid", borderRadius: 8 }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 6 }}>
                  <code style={{ fontSize: "0.85rem", fontWeight: 700, color: "#e2e8f0" }}>{code}</code>
                  <span style={{ fontSize: "0.75rem", color: "#475569" }}>=</span>
                  <span style={{ fontSize: "0.85rem", fontWeight: 600, color: color }}>{label}</span>
                </div>
                <p style={{ fontSize: "0.75rem", color: "#94a3b8", margin: "0 0 6px", lineHeight: 1.5 }}>{desc}</p>
                <p style={{ fontSize: "0.73rem", color: "#475569", margin: 0, lineHeight: 1.5, fontStyle: "italic" }}>{example}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════
          Onglet TURPE
      ════════════════════════════════════════════════════════════════ */}
      {activeTab === "turpe" && (
        <TurpeSection
          points={turpeQuery.data ?? []}
          isLoading={turpeQuery.isLoading}
          error={turpeQuery.error as Error | null}
        />
      )}

      {/* ════════════════════════════════════════════════════════════════
          Onglet PERSPECTIVE (projection tarifaire)
      ════════════════════════════════════════════════════════════════ */}
      {activeTab === "perspective" && (
        <PerspectiveSection points={timelineQuery.data ?? []} segment={chartFilters.segment_code} period={chartFilters.period_code} />
      )}

      {/* ════════════════════════════════════════════════════════════════
          Onglet DOCUMENTS & IMPORT
      ════════════════════════════════════════════════════════════════ */}
      {activeTab === "documents" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

          {/* Stats */}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {[
              { label: "BPU stockés",   value: stats.total,                                                    color: "#94a3b8" },
              { label: "OK texte",      value: stats.byStatus.ok ?? 0,                                         color: "#4ade80" },
              { label: "OK OCR",        value: stats.byStatus.ocr_ok ?? 0,                                     color: "#60a5fa" },
              { label: "À revoir",      value: (stats.byStatus.ocr_review ?? 0) + (stats.byStatus.error ?? 0), color: "#fbbf24" },
            ].map(s => (
              <div key={s.label} style={{ padding: "10px 18px", background: "rgba(15,23,42,0.4)", border: `1px solid ${s.color}33`, borderRadius: 8, textAlign: "center", minWidth: 90 }}>
                <div style={{ fontSize: "1.6rem", fontWeight: 700, color: s.color, lineHeight: 1 }}>{s.value}</div>
                <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: 3 }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Filtres + tableau */}
          <div style={{ background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 10, padding: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 12, marginBottom: 16 }}>
              <div>
                <h2 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>Documents BPU importés</h2>
                <p style={{ fontSize: "0.78rem", color: "#64748b", margin: "3px 0 0" }}>Un BPU = un PDF source identifié par fournisseur × année × marché × lot × avenant.</p>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                <FilterSelect label="Fournisseur" value={docSupplier} onChange={setDocSupplier}
                  options={[{ value: "", label: "Tous" }, ...supplierOpts.map(s => ({ value: s, label: s }))]} />
                <FilterSelect label="Année" value={docYear} onChange={setDocYear}
                  options={[{ value: "", label: "Toutes" }, ...yearOpts.map(y => ({ value: String(y), label: String(y) }))]} />
                <FilterSelect label="Lot" value={docLot} onChange={setDocLot}
                  options={[{ value: "", label: "Tous" }, { value: "1", label: "Lot 1" }, { value: "2", label: "Lot 2" }, { value: "3", label: "Lot 3" }]} />
                <FilterSelect label="Statut" value={docStatus} onChange={setDocStatus}
                  options={[{ value: "", label: "Tous" }, { value: "ok", label: "OK texte" }, { value: "ocr_ok", label: "OK OCR" }, { value: "ocr_review", label: "À revoir" }, { value: "error", label: "Erreur" }]} />
              </div>
            </div>

            {docsQuery.isLoading ? (
              <div style={{ padding: "32px 0", textAlign: "center", color: "#64748b", fontSize: "0.85rem" }}>Chargement…</div>
            ) : docsQuery.isError ? (
              <ErrorBanner message={(docsQuery.error as Error).message} />
            ) : (docsQuery.data ?? []).length === 0 ? (
              <div style={{ padding: "32px 0", textAlign: "center", color: "#64748b", fontSize: "0.85rem" }}>
                Aucun BPU importé.
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.83rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.2)" }}>
                      {["Fournisseur", "Année", "MS", "Lot", "Avenant", "Statut", "Confiance", "Fichier"].map(h => (
                        <th key={h} style={{ textAlign: "left", padding: "6px 10px", fontSize: "0.72rem", textTransform: "uppercase", color: "#475569", fontWeight: 600 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(docsQuery.data ?? []).map(d => {
                      const badge = STATUS_BADGE[d.extraction_status] ?? { label: d.extraction_status, color: "#94a3b8" };
                      return (
                        <tr key={d.id} style={{ borderBottom: "1px solid rgba(148,163,184,0.1)" }}>
                          <td style={{ padding: "7px 10px", fontWeight: 600 }}>{d.supplier}</td>
                          <td style={{ padding: "7px 10px" }}>{d.valid_year}</td>
                          <td style={{ padding: "7px 10px", color: "#64748b" }}>{d.market_subsequent ?? "—"}</td>
                          <td style={{ padding: "7px 10px" }}>{d.lot_number}</td>
                          <td style={{ padding: "7px 10px", color: "#64748b" }}>
                            {d.amendment_number != null ? `Avenant ${d.amendment_number}` : d.amendment_label ?? "—"}
                          </td>
                          <td style={{ padding: "7px 10px" }}>
                            <span style={{ fontSize: "0.73rem", padding: "2px 7px", borderRadius: 10, background: `${badge.color}22`, color: badge.color, border: `1px solid ${badge.color}44`, whiteSpace: "nowrap" }}>
                              {badge.label}
                            </span>
                          </td>
                          <td style={{ padding: "7px 10px", color: "#64748b" }}>
                            {d.extraction_confidence != null ? `${(Number(d.extraction_confidence) * 100).toFixed(0)} %` : "—"}
                          </td>
                          <td style={{ padding: "7px 10px", color: "#475569", fontSize: "0.75rem", maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={d.pdf_filename}>
                            {d.pdf_filename}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Import xlsx — SOURCE DE VÉRITÉ (recommandé) */}
          <div style={{ background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.3)", borderRadius: 10, padding: "16px" }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 4px" }}>
              Importer le fichier de référence (xlsx) <span style={{ fontSize: "0.7rem", color: "#4ade80", fontWeight: 600 }}>· recommandé</span>
            </h2>
            <p style={{ fontSize: "0.78rem", color: "#64748b", margin: "0 0 14px", maxWidth: 580 }}>
              Charge <code style={{ color: "#86efac" }}>extraction_tarifs_electricite_BPU.xlsx</code> — l'extraction
              manuelle <strong>validée et auditée</strong> (source de vérité, confiance 1.0). À privilégier :
              les prix sont exacts, contrairement à la ré-ingestion PDF/OCR ci-dessous.
            </p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <button
                type="button"
                onClick={() => xlsxImportMutation.mutate({ force: true })}
                disabled={xlsxImportMutation.isPending}
                style={{ padding: "7px 16px", background: "#16a34a", color: "#fff", border: "none", borderRadius: 7, fontSize: "0.85rem", fontWeight: 500, cursor: "pointer", opacity: xlsxImportMutation.isPending ? 0.6 : 1 }}
              >
                {xlsxImportMutation.isPending ? "Import en cours…" : "Importer le fichier de référence"}
              </button>
              {xlsxImportMutation.data && (
                <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                  <span style={{ color: "#4ade80" }}>{xlsxImportMutation.data.documents} docs</span> ·{" "}
                  {xlsxImportMutation.data.components} prix · {xlsxImportMutation.data.charges} surcoûts
                  {xlsxImportMutation.data.errors > 0 && (
                    <span style={{ color: "#f87171" }}> · {xlsxImportMutation.data.errors} erreurs</span>
                  )}
                </span>
              )}
            </div>
            {xlsxImportMutation.isError && (
              <ErrorBanner message={(xlsxImportMutation.error as Error).message} style={{ marginTop: 12 }} />
            )}
          </div>

          {/* Import admin — PDF/OCR (avancé, secondaire) */}
          <div style={{ background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 10, padding: "16px", opacity: 0.85 }}>
            <h2 style={{ fontSize: "0.95rem", fontWeight: 600, margin: "0 0 4px", color: "#94a3b8" }}>
              Avancé · ré-ingestion PDF/OCR côté serveur
            </h2>
            <p style={{ fontSize: "0.78rem", color: "#64748b", margin: "0 0 14px", maxWidth: 580 }}>
              Re-parse les PDF du répertoire <code style={{ color: "#93c5fd" }}>saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/</code> (textuels directs, scans via OCR).
              <strong style={{ color: "#fbbf24" }}> Ne reprend pas les corrections du xlsx</strong> et peut réintroduire des imprécisions d'OCR — n'utiliser que pour un nouveau PDF non encore saisi dans le fichier de référence.
            </p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => importMutation.mutate({ force: false })}
                disabled={importMutation.isPending}
                style={{ padding: "7px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 7, fontSize: "0.85rem", fontWeight: 500, cursor: "pointer", opacity: importMutation.isPending ? 0.6 : 1 }}
              >
                {importMutation.isPending ? "Import en cours…" : "Importer depuis le serveur"}
              </button>
              <button
                type="button"
                onClick={() => importMutation.mutate({ force: true })}
                disabled={importMutation.isPending}
                style={{ padding: "7px 16px", background: "transparent", color: "#94a3b8", border: "1px solid rgba(148,163,184,0.3)", borderRadius: 7, fontSize: "0.85rem", cursor: "pointer", opacity: importMutation.isPending ? 0.6 : 1 }}
              >
                Forcer le remplacement
              </button>
            </div>

            {importMutation.isError && (
              <ErrorBanner message={(importMutation.error as Error).message} style={{ marginTop: 12 }} />
            )}
            {importMutation.data && (
              <div style={{ marginTop: 12, padding: "10px 14px", background: "rgba(51,65,85,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 8, fontSize: "0.82rem" }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Résultat</div>
                <div style={{ color: "#94a3b8" }}>
                  {importMutation.data.total} fichiers · <span style={{ color: "#4ade80" }}>{importMutation.data.succeeded} OK</span> ·{" "}
                  <span style={{ color: "#f87171" }}>{importMutation.data.failed} erreurs</span> · {importMutation.data.skipped} skippés
                </div>
                <details style={{ marginTop: 8, cursor: "pointer" }}>
                  <summary style={{ color: "#64748b", fontSize: "0.78rem" }}>Détails par fichier</summary>
                  <ul style={{ marginTop: 6, paddingLeft: 0, listStyle: "none", fontFamily: "monospace", fontSize: "0.75rem", display: "flex", flexDirection: "column", gap: 2 }}>
                    {importMutation.data.results.map(r => (
                      <li key={r.filename} style={{ color: r.status === "error" ? "#f87171" : "#64748b" }}>
                        [{r.status}] {r.filename}
                        {r.segments_count > 0 && ` — ${r.segments_count} seg, ${r.components_count} prix`}
                        {r.error && <span style={{ color: "#f87171" }}> · {r.error}</span>}
                      </li>
                    ))}
                  </ul>
                </details>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════
          Onglet ÉDITION TABLEAU
      ════════════════════════════════════════════════════════════════ */}
      {activeTab === "edition" && (
        <div style={{ background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 10, padding: "16px" }}>
          <div style={{ marginBottom: 12 }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>Édition des prix unitaires</h2>
            <p style={{ fontSize: "0.78rem", color: "#64748b", margin: "3px 0 0" }}>
              Cliquez une cellule pour modifier, puis « Enregistrer » pour persister en BDD. Modifications non sauvegardées surlignées en orange.
            </p>
          </div>
          <BpuEditableTable />
        </div>
      )}
    </div>
  );
}

// ─── Sous-composant PERSPECTIVE (projection tarifaire fourniture) ───────────

function PerspectiveSection({ points, segment, period }: { points: BpuTimelinePoint[]; segment?: string; period?: string }) {
  const model = useMemo(() => {
    const byYear = new Map<number, Map<string, { sum: number; n: number }>>();
    for (const p of points) {
      if (p.price_value_eur_per_mwh == null || p.valid_year == null) continue;
      if (!byYear.has(p.valid_year)) byYear.set(p.valid_year, new Map());
      const comps = byYear.get(p.valid_year)!;
      const cur = comps.get(p.component_type) ?? { sum: 0, n: 0 };
      cur.sum += Number(p.price_value_eur_per_mwh);
      cur.n += 1;
      comps.set(p.component_type, cur);
    }
    const hist = Array.from(byYear.entries())
      .map(([year, comps]) => {
        let total = 0;
        comps.forEach((v) => { total += v.n ? v.sum / v.n : 0; });
        return { year, total };
      })
      .filter((r) => r.total > 0)
      .sort((a, b) => a.year - b.year);
    if (hist.length < 2) return null;
    const xs = hist.map((r) => r.year);
    const ys = hist.map((r) => r.total);
    const n = xs.length;
    const mx = xs.reduce((a, b) => a + b, 0) / n;
    const my = ys.reduce((a, b) => a + b, 0) / n;
    let num = 0;
    let den = 0;
    for (let i = 0; i < n; i++) { num += (xs[i] - mx) * (ys[i] - my); den += (xs[i] - mx) ** 2; }
    const slope = den ? num / den : 0;
    const intercept = my - slope * mx;
    const f = (y: number) => Math.max(0, intercept + slope * y);
    const lastYear = hist[hist.length - 1].year;
    const projYears = Array.from({ length: 10 }, (_u, i) => lastYear + i + 1);
    const round1 = (v: number) => Math.round(v * 10) / 10;
    const rows = [
      ...hist.map((r) => ({ label: String(r.year), hist: round1(r.total) as number | null, proj: (r.year === lastYear ? round1(r.total) : null) as number | null })),
      ...projYears.map((y) => ({ label: String(y), hist: null as number | null, proj: round1(f(y)) as number | null })),
    ];
    const table = [
      ...hist.map((r) => ({ year: r.year, mwh: r.total, proj: false })),
      ...projYears.map((y) => ({ year: y, mwh: f(y), proj: true })),
    ];
    const g = (dy: number) => (f(lastYear) > 0 ? ((f(lastYear + dy) - f(lastYear)) / f(lastYear)) * 100 : null);
    return { rows, table, lastYear, histFrom: hist[0].year, cur: f(lastYear), p5: f(lastYear + 5), p10: f(lastYear + 10), g5: g(5), g10: g(10) };
  }, [points]);

  if (!model) {
    return <div style={{ padding: 24, color: "#94a3b8" }}>Pas assez d'historique BPU pour projeter (changez le segment/poste dans l'onglet Timeline).</div>;
  }
  const pctTxt = (v: number | null) => (v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(1)} %`);
  const eurKwh = (mwh: number) => (mwh / 1000).toFixed(3);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ fontSize: "0.83rem", color: "#64748b" }}>
        Projection tendancielle du <b style={{ color: "#e2e8f0" }}>prix de fourniture (HTT)</b> = fourniture + capacité + CEE + GO,
        régression linéaire sur l'historique {model.histFrom}–{model.lastYear}
        {segment ? ` · segment ${segment}${period ? ` / ${period}` : ""}` : ""}.
        <br />⚠️ Hors réseau (TURPE, cf. onglet dédié) et hors taxes — l'assemblage TTC est l'étape suivante.
      </div>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {[
          { k: `Actuel (${model.lastYear})`, v: `${model.cur.toFixed(1)} €/MWh`, s: `${eurKwh(model.cur)} €/kWh HTT` },
          { k: "Projection +5 ans", v: `${model.p5.toFixed(1)} €/MWh`, s: `${pctTxt(model.g5)} · ${eurKwh(model.p5)} €/kWh` },
          { k: "Projection +10 ans", v: `${model.p10.toFixed(1)} €/MWh`, s: `${pctTxt(model.g10)} · ${eurKwh(model.p10)} €/kWh` },
        ].map((c) => (
          <div key={c.k} style={{ flex: "1 1 180px", padding: "12px 16px", background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 10 }}>
            <div style={{ fontSize: "0.72rem", color: "#64748b" }}>{c.k}</div>
            <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e2e8f0" }}>{c.v}</div>
            <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>{c.s}</div>
          </div>
        ))}
      </div>

      <div style={{ height: 300, background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 10, padding: "12px 8px 4px" }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={model.rows} margin={{ top: 8, right: 16, left: -6, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#94a3b8" }} />
            <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} width={64} unit=" €/MWh" domain={["auto", "auto"]} />
            <Tooltip formatter={(v: number) => [`${v.toLocaleString("fr-FR")} €/MWh`, ""]} labelFormatter={(l) => `Année ${l}`} contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8 }} />
            <ReferenceLine x={String(model.lastYear)} stroke="#475569" strokeDasharray="4 4" />
            <Line dataKey="hist" name="Historique" stroke="#60a5fa" strokeWidth={3} dot connectNulls={false} />
            <Line dataKey="proj" name="Projection" stroke="#a78bfa" strokeWidth={2} strokeDasharray="6 5" dot={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.25)", color: "#94a3b8" }}>
              <th style={{ textAlign: "left", padding: "7px 10px" }}>Année</th>
              <th style={{ textAlign: "right", padding: "7px 10px" }}>€/MWh HTT</th>
              <th style={{ textAlign: "right", padding: "7px 10px" }}>€/kWh HTT</th>
              <th style={{ textAlign: "right", padding: "7px 10px" }}>Évolution</th>
              <th style={{ textAlign: "left", padding: "7px 10px" }}>Type</th>
            </tr>
          </thead>
          <tbody>
            {model.table.map((r, i) => {
              const prev = i > 0 ? model.table[i - 1].mwh : null;
              const evo = prev && prev > 0 ? ((r.mwh - prev) / prev) * 100 : null;
              return (
                <tr key={r.year} style={{ borderBottom: "1px solid rgba(148,163,184,0.1)", color: r.proj ? "#a78bfa" : "#e2e8f0" }}>
                  <td style={{ padding: "6px 10px" }}>{r.year}</td>
                  <td style={{ padding: "6px 10px", textAlign: "right" }}>{r.mwh.toFixed(1)}</td>
                  <td style={{ padding: "6px 10px", textAlign: "right" }}>{eurKwh(r.mwh)}</td>
                  <td style={{ padding: "6px 10px", textAlign: "right", color: evo == null ? "#64748b" : evo >= 0 ? "#f87171" : "#4ade80" }}>{evo == null ? "—" : `${evo >= 0 ? "+" : ""}${evo.toFixed(1)} %`}</td>
                  <td style={{ padding: "6px 10px" }}>{r.proj ? "Projeté" : "Réel"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Sous-composant TURPE ───────────────────────────────────────────────────

function TurpeSection({ points, isLoading, error }: { points: BpuTurpeEvolutionPoint[]; isLoading: boolean; error: Error | null }) {
  const chartData = useMemo(() =>
    points.map(p => ({
      ...p,
      dateLabel: p.effective_date.slice(0, 7),
      cumulative_index: Number(p.cumulative_index),
      evolution_percent: Number(p.evolution_percent),
    })),
  [points]);
  const latest = points[points.length - 1];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* ── 1. Définition TURPE ──────────────────────────────────────── */}
      <div style={{ background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 10, padding: "20px 24px" }}>
        <h2 style={{ fontSize: "1rem", fontWeight: 700, margin: "0 0 8px", color: "#e2e8f0" }}>Qu'est-ce que le TURPE ?</h2>
        <p style={{ fontSize: "0.85rem", color: "#94a3b8", margin: 0, lineHeight: 1.7, maxWidth: 720 }}>
          Le <strong style={{ color: "#22d3ee" }}>TURPE</strong> (Tarif d'Utilisation des Réseaux Publics d'Électricité) est le tarif
          réglementé fixé par la <strong style={{ color: "#e2e8f0" }}>CRE</strong> (Commission de Régulation de l'Énergie) pour
          l'accès au réseau de transport (<strong style={{ color: "#e2e8f0" }}>RTE</strong>) et de distribution
          (<strong style={{ color: "#e2e8f0" }}>Enedis / ELD</strong>). Il couvre l'acheminement de l'électricité des sites de
          production jusqu'aux bâtiments, et s'applique à tous les consommateurs indépendamment du fournisseur choisi.
          Le TURPE est révisé périodiquement par délibération CRE et répercuté à l'identique par tous les fournisseurs
          sur la facture finale.
        </p>
      </div>

      {/* ── 2. Impact sur la facture ─────────────────────────────────── */}
      <div style={{ background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 10, padding: "20px 24px" }}>
        <h2 style={{ fontSize: "1rem", fontWeight: 700, margin: "0 0 6px", color: "#e2e8f0" }}>Poids du TURPE dans la facture électricité</h2>
        <p style={{ fontSize: "0.83rem", color: "#64748b", margin: "0 0 18px", lineHeight: 1.6 }}>
          Sur une facture HTA typique, le TURPE représente <strong style={{ color: "#22d3ee" }}>environ 20–25 %</strong> du montant
          hors taxes. Il s'additionne aux composantes du BPU (fourniture, capacité, CEE, GO) et aux taxes réglementaires.
          Les valeurs ci-dessous sont <em>indicatives</em> pour un segment C4/HTB en 2024–2025.
        </p>

        {/* Barre empilée horizontale */}
        {(() => {
          const segments = [
            { label: "Fourniture",       pct: 52, color: "#2563eb" },
            { label: "Capacité/CEE/GO",  pct:  8, color: "#f59e0b" },
            { label: "TURPE",            pct: 23, color: "#22d3ee" },
            { label: "Taxes (TICFE+CTA)",pct: 17, color: "#64748b" },
          ];
          return (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {/* Barre */}
              <div style={{ display: "flex", height: 36, borderRadius: 8, overflow: "hidden", gap: 2 }}>
                {segments.map(s => (
                  <div
                    key={s.label}
                    style={{ flex: s.pct, background: s.color, display: "flex", alignItems: "center", justifyContent: "center", transition: "flex 0.3s" }}
                    title={`${s.label} — ${s.pct} %`}
                  >
                    {s.pct >= 10 && (
                      <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#fff", textShadow: "0 1px 2px rgba(0,0,0,0.5)" }}>
                        {s.pct} %
                      </span>
                    )}
                  </div>
                ))}
              </div>
              {/* Légende */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 14 }}>
                {segments.map(s => (
                  <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.78rem", color: "#94a3b8" }}>
                    <span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 3, background: s.color, flexShrink: 0 }} />
                    <strong style={{ color: s.color }}>{s.pct} %</strong>
                    {s.label}
                  </div>
                ))}
              </div>
              <p style={{ fontSize: "0.75rem", color: "#334155", margin: 0, borderTop: "1px solid rgba(148,163,184,0.1)", paddingTop: 10 }}>
                Note : hors TVA (20 % appliquée sur le total HT). TICFE = Taxe Intérieure sur la Consommation Finale d'Électricité · CTA = Contribution Tarifaire d'Acheminement.
                Les hausses TURPE décidées par la CRE depuis 2021 ont renchéri la part réseau de <strong style={{ color: "#22d3ee" }}>+{
                  points.length > 0
                    ? `${(Number(points[points.length - 1].cumulative_index) - 100).toFixed(0)} pts`
                    : "~+30 pts"
                }</strong> (base 100 = août 2021).
              </p>
            </div>
          );
        })()}
      </div>

      {/* ── 3. Graphique évolution ───────────────────────────────────── */}
      <div style={{ background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 10, padding: "20px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 16 }}>
          <div>
            <h2 style={{ fontSize: "1rem", fontWeight: 700, margin: 0, color: "#e2e8f0" }}>Évolution du TURPE HTA-BT</h2>
            <p style={{ fontSize: "0.83rem", color: "#64748b", margin: "4px 0 0", maxWidth: 520 }}>
              Indice base 100 au 1er août 2021 (entrée en vigueur TURPE 6). Chaque point correspond à une délibération CRE publiée.
            </p>
          </div>
          {latest && (
            <div style={{ padding: "8px 14px", background: "rgba(51,65,85,0.5)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 8, textAlign: "right", fontSize: "0.82rem" }}>
              <div style={{ color: "#64748b", fontSize: "0.72rem" }}>Dernier point CRE</div>
              <div style={{ fontWeight: 600, color: "#e2e8f0" }}>{latest.family}</div>
              <div style={{ color: "#22d3ee", fontWeight: 700 }}>Indice {Number(latest.cumulative_index).toFixed(1)}</div>
              <div style={{ color: "#64748b", fontSize: "0.72rem" }}>{formatDateFr(latest.effective_date)}</div>
            </div>
          )}
        </div>

        {isLoading ? (
          <div style={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", fontSize: "0.85rem" }}>Chargement…</div>
        ) : error ? (
          <ErrorBanner message={error.message} />
        ) : points.length === 0 ? (
          <div style={{ padding: "32px 0", textAlign: "center", color: "#64748b" }}>Aucun historique TURPE.</div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
              <XAxis dataKey="dateLabel" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} width={60} domain={["dataMin - 2", "dataMax + 2"]} />
              <Tooltip
                formatter={(value: number | string, name: string) =>
                  typeof value === "number" && name === "Indice TURPE"
                    ? [`${value.toFixed(2)} (base 100 = août 2021)`, name]
                    : [value, name]
                }
                labelFormatter={(_, payload) => {
                  const row = payload?.[0]?.payload as BpuTurpeEvolutionPoint | undefined;
                  return row ? `${row.event_label} — ${formatDateFr(row.effective_date)}` : "";
                }}
                contentStyle={{ backgroundColor: "rgba(15,23,42,0.95)", border: "1px solid rgba(148,163,184,0.3)", color: "#f1f5f9", fontSize: "12px" }}
              />
              <ReferenceLine y={100} stroke="rgba(100,116,139,0.4)" strokeDasharray="4 4" label={{ value: "Base 2021", position: "insideTopLeft", fontSize: 10, fill: "#475569" }} />
              <Line type="monotone" dataKey="cumulative_index" name="Indice TURPE" stroke="#22d3ee" strokeWidth={3} dot={{ r: 4, fill: "#22d3ee" }} activeDot={{ r: 6 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── 4. Tableau CRE ───────────────────────────────────────────── */}
      <div style={{ background: "rgba(15,23,42,0.4)", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 10, padding: "16px 24px" }}>
        <h2 style={{ fontSize: "1rem", fontWeight: 700, margin: "0 0 14px", color: "#e2e8f0" }}>Points CRE retenus</h2>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.83rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.2)" }}>
                {["Date", "Version", "Évolution", "Indice", "Source", "Note"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "6px 10px", fontSize: "0.72rem", textTransform: "uppercase", color: "#475569", fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {points.map(p => (
                <tr key={`${p.family}-${p.effective_date}`} style={{ borderBottom: "1px solid rgba(148,163,184,0.08)" }}>
                  <td style={{ padding: "7px 10px", color: "#94a3b8" }}>{formatDateFr(p.effective_date)}</td>
                  <td style={{ padding: "7px 10px" }}>
                    <div style={{ fontWeight: 600 }}>{p.family}</div>
                    <div style={{ fontSize: "0.73rem", color: "#64748b" }}>{p.event_label}</div>
                  </td>
                  <td style={{ padding: "7px 10px", fontWeight: 600, color: Number(p.evolution_percent) >= 0 ? "#f87171" : "#4ade80" }}>
                    {Number(p.evolution_percent) >= 0 ? "+" : ""}{Number(p.evolution_percent).toFixed(2)} %
                  </td>
                  <td style={{ padding: "7px 10px" }}>{Number(p.cumulative_index).toFixed(2)}</td>
                  <td style={{ padding: "7px 10px" }}>
                    <a href={p.source_url} target="_blank" rel="noreferrer" style={{ color: "#60a5fa", textDecoration: "none" }}>
                      {p.source_label}
                    </a>
                  </td>
                  <td style={{ padding: "7px 10px", color: "#64748b", fontSize: "0.78rem", maxWidth: 300 }}>{p.notes ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Utilitaires UI ─────────────────────────────────────────────────────────

function FilterSelect({ label, value, onChange, options }: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 3, fontSize: "0.75rem", color: "#64748b" }}>
      <span style={{ fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</span>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{ padding: "5px 8px", fontSize: "0.82rem", background: "rgba(15,23,42,0.7)", border: "1px solid rgba(148,163,184,0.25)", borderRadius: 6, color: "#e2e8f0", minWidth: 130, cursor: "pointer" }}
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}

function ErrorBanner({ message, style: extraStyle }: { message: string; style?: React.CSSProperties }) {
  return (
    <div style={{ padding: "10px 14px", background: "rgba(220,38,38,0.12)", border: "1px solid rgba(220,38,38,0.3)", borderRadius: 8, color: "#fca5a5", fontSize: "0.83rem", ...extraStyle }}>
      {message}
    </div>
  );
}

function formatDateFr(value: string) {
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(value));
}
