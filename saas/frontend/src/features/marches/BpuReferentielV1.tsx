import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Card, DataTable, Drawer, SegmentControl, StatusBadge } from "../../design-system";
import BpuEditableTable from "../../components/BpuEditableTable";
import BpuTimelineChart from "../../components/BpuTimelineChart";
import { useAuth } from "../../providers/AuthProvider";
import {
  fetchBpuDocument,
  fetchBpuDocuments,
  fetchBpuFormula,
  fetchBpuTimeline,
  triggerBpuImport,
  triggerBpuXlsxImport,
  type BpuDocumentSummary,
  type BpuFormula,
  type BpuImportResponse,
  type BpuTimelineFilters,
  type BpuTimelinePoint,
  type BpuXlsxImportResponse,
} from "../../lib/api";

// Vue référentiel BPU Hérault Énergies — refonte DS V1.
// Décisions : docs/refonte-v1/referentiel-bpu-ux-decisions.md
//   - 2 sous-onglets : Consultation (prix applicables) / Évolution (graphe).
//   - TURPE retiré, camembert facture supprimé, pédagogie en infobulle, admin replié « Gérer ».

type View = "consultation" | "evolution";

const STATUS_TONE: Record<string, "ok" | "warn" | "bad" | "info" | "neutral"> = {
  ok: "ok", ocr_ok: "info", ocr_review: "warn", manual: "neutral", pending: "neutral", error: "bad",
};
const STATUS_LABEL: Record<string, string> = {
  ok: "OK texte", ocr_ok: "OK OCR", ocr_review: "À revoir", manual: "Manuel", pending: "En attente", error: "Erreur",
};

// Pédagogie en infobulle (title) — plus de gros blocs pleine page.
const COMPONENT_DEFS: Record<string, string> = {
  fourniture: "Fourniture — prix du marché de gros de l'électricité, fixé à la signature du marché.",
  capacite: "Capacité — mécanisme RTE garantissant l'équilibre offre/demande en hiver.",
  cee: "CEE — Certificats d'Économies d'Énergie (obligation légale répercutée par le fournisseur).",
  go: "GO — Garanties d'Origine (option attestant l'électricité renouvelable).",
};

function errorMessage(e: unknown) {
  return e instanceof Error ? e.message : "Une erreur est survenue.";
}
function priceMwh(v: number | null | undefined) {
  if (v == null) return "—";
  return v.toLocaleString("fr-FR", { maximumFractionDigits: 2 }) + " €/MWh";
}
function amendmentLabel(d: BpuDocumentSummary) {
  return d.amendment_number != null ? `Avenant ${d.amendment_number}` : d.amendment_label ?? "—";
}

export function BpuReferentielV1() {
  const { token, user, isLoading } = useAuth();
  const [view, setView] = useState<View>("consultation");
  const [manage, setManage] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // Filtres consultation
  const [fSupplier, setFSupplier] = useState("");
  const [fYear, setFYear] = useState("");
  const [fLot, setFLot] = useState("");
  const [fStatus, setFStatus] = useState("");

  // Filtres évolution
  const [chart, setChart] = useState<BpuTimelineFilters>({ segment_code: "C4", period_code: "HPH" });

  const authReady = !!token && !!user;
  const formulaQ = useQuery<BpuFormula>({ queryKey: ["bpu", "formula"], enabled: authReady, queryFn: () => fetchBpuFormula(token ?? "") });
  const docsQ = useQuery<BpuDocumentSummary[]>({
    queryKey: ["bpu", "documents", fSupplier, fYear, fLot, fStatus],
    enabled: authReady,
    queryFn: () => fetchBpuDocuments(token ?? "", {
      supplier: fSupplier || undefined,
      valid_year: fYear ? Number(fYear) : undefined,
      lot_number: fLot ? Number(fLot) : undefined,
      extraction_status: fStatus || undefined,
    }),
  });
  const timelineQ = useQuery<BpuTimelinePoint[]>({ queryKey: ["bpu", "timeline", chart], enabled: authReady && view === "evolution", queryFn: () => fetchBpuTimeline(token ?? "", chart) });

  const supplierOpts = useMemo(() => Array.from(new Set((docsQ.data ?? []).map((d) => d.supplier))).sort(), [docsQ.data]);
  const yearOpts = useMemo(() => Array.from(new Set((docsQ.data ?? []).map((d) => d.valid_year))).sort(), [docsQ.data]);
  const segChoices = formulaQ.data?.segments ?? [];
  const perChoices = formulaQ.data?.periods ?? [];

  if (isLoading) return <p className="po2-muted-line">Validation de la session...</p>;
  if (!authReady) return <p className="po2-muted-line">Connecte-toi pour acceder aux BPU.</p>;

  return (
    <div className="po2-page-v1">
      {/* Barre : sous-onglets + action Gérer */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: "1rem" }}>
        <div>
          <span className="po2-eyebrow" style={{ display: "block", marginBottom: 8 }}>BPU — Hérault Énergies (EDF · ENGIE · TotalEnergies)</span>
          <SegmentControl
            value={view}
            options={[
              { value: "consultation", label: "Consultation (prix applicables)" },
              { value: "evolution", label: "Évolution" },
            ]}
            onChange={setView}
          />
        </div>
        <Button variant="ghost" onClick={() => setManage(true)}>Gérer (import / édition)</Button>
      </div>

      {view === "consultation" ? (
        <Card title="BPU en vigueur" eyebrow="un BPU = fournisseur × année × lot × avenant">
          <div className="po2-matrix-import-form" style={{ marginBottom: "0.75rem" }}>
            <label><span>Fournisseur</span>
              <select value={fSupplier} onChange={(e) => setFSupplier(e.currentTarget.value)}>
                <option value="">Tous</option>{supplierOpts.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
            <label><span>Année</span>
              <select value={fYear} onChange={(e) => setFYear(e.currentTarget.value)}>
                <option value="">Toutes</option>{yearOpts.map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </label>
            <label><span>Lot</span>
              <select value={fLot} onChange={(e) => setFLot(e.currentTarget.value)}>
                <option value="">Tous</option><option value="1">Lot 1</option><option value="2">Lot 2</option><option value="3">Lot 3</option><option value="7">Lot 7</option>
              </select>
            </label>
            <label><span>Statut</span>
              <select value={fStatus} onChange={(e) => setFStatus(e.currentTarget.value)}>
                <option value="">Tous</option><option value="ok">OK texte</option><option value="ocr_ok">OK OCR</option><option value="ocr_review">À revoir</option><option value="manual">Manuel</option><option value="error">Erreur</option>
              </select>
            </label>
          </div>

          {docsQ.isError ? <p className="po2-muted-line">Indisponible : {errorMessage(docsQ.error)}</p>
            : docsQ.isFetching && !docsQ.data ? <p className="po2-muted-line">Chargement des BPU…</p>
            : (docsQ.data ?? []).length === 0 ? <p className="po2-muted-line">Aucun BPU pour ces filtres.</p>
            : (
              <>
                <p className="po2-muted-line" style={{ marginTop: 0 }}>Clique une ligne pour voir le détail des prix par poste.</p>
                <DataTable<BpuDocumentSummary>
                  rows={docsQ.data ?? []}
                  getRowKey={(r) => r.id}
                  onRowClick={(r) => setSelectedId(r.id)}
                  columns={[
                    { key: "supplier", header: "Fournisseur", render: (r) => r.supplier },
                    { key: "valid_year", header: "Année", render: (r) => String(r.valid_year) },
                    { key: "lot_number", header: "Lot", render: (r) => String(r.lot_number) },
                    { key: "ms", header: "MS", render: (r) => (r.market_subsequent ? `MS${r.market_subsequent}` : "—") },
                    { key: "amendment", header: "Avenant", render: (r) => amendmentLabel(r) },
                    { key: "status", header: "Statut", render: (r) => <StatusBadge tone={STATUS_TONE[r.extraction_status] ?? "neutral"}>{STATUS_LABEL[r.extraction_status] ?? r.extraction_status}</StatusBadge> },
                    { key: "file", header: "Fichier", render: (r) => r.pdf_filename },
                  ]}
                />
              </>
            )}
        </Card>
      ) : (
        <Card title="Évolution des composantes de prix" eyebrow="graphe historique 2021–2026">
          <div className="po2-matrix-import-form" style={{ marginBottom: "0.75rem" }}>
            <label><span>Segment</span>
              <select value={chart.segment_code ?? ""} onChange={(e) => setChart((f) => ({ ...f, segment_code: e.currentTarget.value || undefined }))}>
                <option value="">Tous</option>{segChoices.map((s) => <option key={s.code} value={s.code}>{s.code} — {s.label}</option>)}
              </select>
            </label>
            <label><span>Poste</span>
              <select value={chart.period_code ?? ""} onChange={(e) => setChart((f) => ({ ...f, period_code: e.currentTarget.value || undefined }))}>
                <option value="">Tous</option>{perChoices.map((p) => <option key={p.code} value={p.code}>{p.code} — {p.label}</option>)}
              </select>
            </label>
            <label><span>Fournisseur</span>
              <select value={chart.supplier ?? ""} onChange={(e) => setChart((f) => ({ ...f, supplier: e.currentTarget.value || undefined }))}>
                <option value="">Tous</option><option value="EDF">EDF</option><option value="ENGIE">ENGIE</option><option value="TOTALENERGIES">TotalEnergies</option>
              </select>
            </label>
            <label><span>Lot</span>
              <select value={chart.lot_number?.toString() ?? ""} onChange={(e) => setChart((f) => ({ ...f, lot_number: e.currentTarget.value ? Number(e.currentTarget.value) : undefined }))}>
                <option value="">Tous</option><option value="1">Lot 1</option><option value="2">Lot 2</option><option value="3">Lot 3</option><option value="7">Lot 7</option>
              </select>
            </label>
          </div>
          {timelineQ.isError ? <p className="po2-muted-line">Indisponible : {errorMessage(timelineQ.error)}</p>
            : timelineQ.isFetching && !timelineQ.data ? <p className="po2-muted-line">Chargement du graphe…</p>
            : <BpuTimelineChart points={timelineQ.data ?? []} formula={formulaQ.data} includeTotal />}
          {formulaQ.data ? <p className="po2-muted-line" style={{ marginTop: 12 }}>Formule : <code>{formulaQ.data.expression}</code></p> : null}
        </Card>
      )}

      <BpuDetailDrawer token={token!} documentId={selectedId} onClose={() => setSelectedId(null)} />
      <BpuManageDrawer token={token!} open={manage} onClose={() => setManage(false)} />
    </div>
  );
}

// ── Drawer détail d'un BPU : prix par segment/poste ────────────────────────────
function BpuDetailDrawer({ token, documentId, onClose }: { token: string; documentId: number | null; onClose: () => void }) {
  const q = useQuery({ queryKey: ["bpu", "document", documentId], enabled: documentId != null, queryFn: () => fetchBpuDocument(token, documentId as number) });
  const d = q.data;

  type PriceRow = { key: string; segment: string; period: string; component: string; type: string; value: string };
  const rows: PriceRow[] = useMemo(() => {
    if (!d) return [];
    const out: PriceRow[] = [];
    for (const seg of d.segments) {
      for (const per of seg.periods) {
        for (const c of per.components) {
          out.push({
            key: `${seg.id}-${per.id}-${c.id}`,
            segment: seg.segment_label ? `${seg.segment_code} — ${seg.segment_label}` : seg.segment_code,
            period: per.period_label ?? per.period_code,
            component: c.component_label ?? c.component_type,
            type: c.component_type,
            value: c.price_value_eur_per_mwh != null ? priceMwh(c.price_value_eur_per_mwh) : `${c.price_value} ${c.price_unit}`,
          });
        }
      }
    }
    return out;
  }, [d]);

  return (
    <Drawer
      open={documentId != null}
      onClose={onClose}
      wide
      eyebrow={d ? `${d.supplier} · ${d.valid_year} · Lot ${d.lot_number}` : "BPU"}
      title={d ? (d.amendment_number != null ? `Avenant ${d.amendment_number}` : "Détail du BPU") : "Détail du BPU"}
      description={d?.pdf_filename}
    >
      {q.isError ? <p className="po2-muted-line">Indisponible : {errorMessage(q.error)}</p>
        : q.isFetching && !d ? <p className="po2-muted-line">Chargement du détail…</p>
        : d ? (
          <>
            <p className="po2-muted-line" style={{ marginTop: 0 }}>
              Statut extraction : <StatusBadge tone={STATUS_TONE[d.extraction_status] ?? "neutral"}>{STATUS_LABEL[d.extraction_status] ?? d.extraction_status}</StatusBadge>
              {d.extraction_confidence != null ? ` · confiance ${(Number(d.extraction_confidence) * 100).toFixed(0)} %` : ""}
            </p>
            {rows.length === 0 ? <p className="po2-muted-line">Aucune composante de prix enregistrée.</p> : (
              <DataTable<PriceRow>
                rows={rows}
                getRowKey={(r) => r.key}
                columns={[
                  { key: "segment", header: "Segment", render: (r) => r.segment },
                  { key: "period", header: "Poste", render: (r) => r.period },
                  { key: "component", header: "Composante", render: (r) => <span title={COMPONENT_DEFS[r.type] ?? r.type}>{r.component}</span> },
                  { key: "value", header: "Prix", render: (r) => r.value },
                ]}
              />
            )}
            {d.fixed_charges.length > 0 ? (
              <div style={{ marginTop: 16 }}>
                <h3 className="po2-eyebrow">Surcoûts / frais fixes</h3>
                <DataTable
                  rows={d.fixed_charges}
                  getRowKey={(c) => String(c.id)}
                  columns={[
                    { key: "label", header: "Frais", render: (c) => c.charge_label ?? c.charge_type },
                    { key: "value", header: "Valeur", render: (c) => `${c.charge_value} ${c.charge_unit}` },
                  ]}
                />
              </div>
            ) : null}
            {d.extraction_notes ? <p className="po2-muted-line" style={{ marginTop: 12 }}>Note : {d.extraction_notes}</p> : null}
          </>
        ) : null}
    </Drawer>
  );
}

// ── Drawer admin « Gérer » : import (source de vérité + PDF/OCR) + édition ──────
function BpuManageDrawer({ token, open, onClose }: { token: string; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const xlsx = useMutation<BpuXlsxImportResponse, Error, void>({ mutationFn: () => triggerBpuXlsxImport(token, { force: true }), onSuccess: () => qc.invalidateQueries({ queryKey: ["bpu"] }) });
  const pdf = useMutation<BpuImportResponse, Error, { force: boolean }>({ mutationFn: ({ force }) => triggerBpuImport(token, { force, enable_ocr: true }), onSuccess: () => qc.invalidateQueries({ queryKey: ["bpu"] }) });

  return (
    <Drawer open={open} onClose={onClose} wide eyebrow="administration" title="Gérer les BPU">
      <Card title="Importer le fichier de référence (xlsx)" eyebrow="source de vérité · recommandé">
        <p className="po2-muted-line" style={{ marginTop: 0 }}>
          Charge l'extraction manuelle validée (confiance 1.0). À privilégier : prix exacts, contrairement à la ré-ingestion PDF/OCR.
        </p>
        <Button onClick={() => xlsx.mutate()} disabled={xlsx.isPending}>{xlsx.isPending ? "Import en cours…" : "Importer le fichier de référence"}</Button>
        {xlsx.data ? <p className="po2-muted-line">{xlsx.data.documents} docs · {xlsx.data.components} prix · {xlsx.data.charges} surcoûts{xlsx.data.errors > 0 ? ` · ${xlsx.data.errors} erreurs` : ""}</p> : null}
        {xlsx.isError ? <p className="po2-muted-line">Erreur : {errorMessage(xlsx.error)}</p> : null}
      </Card>

      <Card title="Avancé — ré-ingestion PDF/OCR (serveur)" eyebrow="pour un nouveau PDF non encore saisi">
        <p className="po2-muted-line" style={{ marginTop: 0 }}>
          Re-parse les PDF du serveur. Ne reprend pas les corrections du xlsx et peut réintroduire des imprécisions d'OCR.
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Button variant="secondary" onClick={() => pdf.mutate({ force: false })} disabled={pdf.isPending}>{pdf.isPending ? "Import…" : "Importer depuis le serveur"}</Button>
          <Button variant="ghost" onClick={() => pdf.mutate({ force: true })} disabled={pdf.isPending}>Forcer le remplacement</Button>
        </div>
        {pdf.data ? <p className="po2-muted-line">{pdf.data.total} fichiers · {pdf.data.succeeded} OK · {pdf.data.failed} erreurs · {pdf.data.skipped} skippés</p> : null}
        {pdf.isError ? <p className="po2-muted-line">Erreur : {errorMessage(pdf.error)}</p> : null}
      </Card>

      <Card title="Édition des prix unitaires" eyebrow="clique une cellule, puis Enregistrer">
        <BpuEditableTable />
      </Card>
    </Drawer>
  );
}
