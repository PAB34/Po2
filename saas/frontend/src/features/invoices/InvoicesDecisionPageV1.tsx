import { useMemo, useState } from "react";
import { Button, Drawer, StatusBadge } from "../../design-system";
import { useCpeFinanceQueueV1, useCpeInvoiceDetailV1, useCpeInvoiceActionsV1 } from "./useCpeFinanceQueueV1";
import type { CpeFinanceControl, CpeFinanceControlReport, CpeFinanceLine, EnergyInvoiceImport } from "../../lib/api";

type CpeQueueInvoice = CpeFinanceControlReport["invoices"][number];
type UnifiedStatus = "todo" | "valid" | "refused" | "disputed";
type UnifiedRow = {
  key: string;
  source: "cpe" | "energy";
  rowId: number;
  invoiceNumber: string;
  supplier: string;
  type: string;
  client: string;
  marche: string;
  perimetre: string;
  total: number;
  ok: number;
  error: number;
  blocked: number;
  status: UnifiedStatus;
  processed: boolean;
  month: number | null;
};

// ---------------------------------------------------------------------------
// Statuts unifiés (CPE et énergie ont des codes différents)
// ---------------------------------------------------------------------------
const UNIFIED_OPTIONS: { value: UnifiedStatus; label: string }[] = [
  { value: "todo", label: "À contrôler" },
  { value: "valid", label: "Validée" },
  { value: "refused", label: "Refusée" },
  { value: "disputed", label: "Contestée" },
];
const CPE_TO_UNIFIED: Record<string, UnifiedStatus> = { a_controler: "todo", valide: "valid", refuse: "refused", conteste: "disputed" };
const UNIFIED_TO_CPE: Record<UnifiedStatus, string> = { todo: "a_controler", valid: "valide", refused: "refuse", disputed: "conteste" };
const ENERGY_TO_UNIFIED: Record<string, UnifiedStatus> = { to_review: "todo", approved: "valid", rejected: "refused", dispute_sent: "disputed" };
const UNIFIED_TO_ENERGY: Record<UnifiedStatus, "to_review" | "approved" | "rejected" | "dispute_sent"> = { todo: "to_review", valid: "approved", refused: "rejected", disputed: "dispute_sent" };

const CONTROL_TYPE_LABELS: Record<string, string> = {
  coherence: "Cohérence", fourniture: "Fourniture", acheminement: "Acheminement", taxes: "Taxes",
  p1: "P1 gaz", p1_quantite: "P1 quantité", p1_prix: "P1 prix", revision: "Révision",
  documentaire: "Documentaire", comptable: "Comptable", echeance: "Échéance",
};
function controlTypeLabel(type: string) { return CONTROL_TYPE_LABELS[type] ?? type.replace(/_/g, " "); }
function statusLabel(s: UnifiedStatus) { return UNIFIED_OPTIONS.find((o) => o.value === s)?.label ?? s; }
function statusTone(s: UnifiedStatus) { return s === "valid" ? ("ok" as const) : s === "todo" ? ("warn" as const) : ("bad" as const); }
function controlTone(status: string, severity: string) {
  if (status === "ok") return "ok" as const;
  if (status === "blocked" || severity === "blocking" || status === "error") return "bad" as const;
  return "warn" as const;
}
function fmtEur(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value);
}
function parseMonth(date: string | null | undefined): number | null {
  if (!date) return null;
  const m = date.includes("/") ? Number(date.split("/")[1]) - 1 : Number(date.slice(5, 7)) - 1;
  return m >= 0 && m < 12 ? m : null;
}
function supplierFromEnergy(inv: EnergyInvoiceImport) {
  return inv.supplier_guess || (inv.source?.toUpperCase().includes("EDF") ? "EDF" : inv.source?.toUpperCase().includes("ENGIE") ? "ENGIE" : "Énergie");
}

const MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"];

export function InvoicesDecisionPageV1() {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [supplierFilter, setSupplierFilter] = useState("all");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const { report, invoices, energy } = useCpeFinanceQueueV1();
  const actions = useCpeInvoiceActionsV1();

  // Mois d'émission des factures CPE (le rapport de contrôle ne porte pas la date)
  const cpeMonthById = useMemo(() => {
    const map = new Map<number, number | null>();
    for (const inv of invoices.data ?? []) map.set(inv.id, parseMonth(inv.invoice_date));
    return map;
  }, [invoices.data]);

  const rows: UnifiedRow[] = useMemo(() => {
    const out: UnifiedRow[] = [];
    for (const r of report.data?.invoices ?? []) {
      out.push({
        key: `cpe:${r.invoice_id}`, source: "cpe", rowId: r.invoice_id,
        invoiceNumber: r.invoice_number, supplier: "DALKIA",
        type: r.invoice_type ?? "—", client: r.recipient_ref ?? "—",
        marche: r.contract_code ?? r.contract_label ?? "—", perimetre: r.market ?? "—",
        total: r.total_ht, ok: r.ok, error: r.error, blocked: r.blocked,
        status: CPE_TO_UNIFIED[r.invoice_status] ?? "todo",
        processed: r.invoice_status === "valide" || Boolean(r.finance_exported_at),
        month: cpeMonthById.get(r.invoice_id) ?? null,
      });
    }
    for (const e of energy.data ?? []) {
      const status = ENERGY_TO_UNIFIED[e.decision_status] ?? "todo";
      const sites = e.site_count ? ` · ${e.site_count} site(s)` : "";
      const docType = e.filter_facets?.document_types?.[0];
      out.push({
        key: `energy:${e.id}`, source: "energy", rowId: e.id,
        invoiceNumber: e.invoice_number ?? `import-${e.id}`, supplier: supplierFromEnergy(e),
        type: docType ? (docType.toLowerCase().includes("avoir") ? "Avoir" : "Facture") : "Facture",
        client: e.contract_holder ?? "—",
        marche: e.market_reference ?? "—",
        perimetre: (e.regroupement ?? "Portefeuille") + sites,
        total: e.total_ht ?? e.total_ttc ?? 0, ok: 0, error: e.control_errors_count, blocked: 0,
        status, processed: status === "valid",
        month: parseMonth(e.invoice_date),
      });
    }
    return out;
  }, [report.data, energy.data, cpeMonthById]);

  const selected = rows.find((r) => r.key === selectedKey) ?? null;
  const detail = useCpeInvoiceDetailV1(selected?.source === "cpe" ? selected.rowId : null);

  const suppliers = useMemo(() => Array.from(new Set(rows.map((r) => r.supplier))).sort(), [rows]);

  const monthly = useMemo(() => {
    const data = MONTHS.map(() => ({ traitees: 0, aTraiter: 0 }));
    for (const r of rows) {
      if (r.month === null) continue;
      if (r.processed) data[r.month].traitees += 1; else data[r.month].aTraiter += 1;
    }
    const max = Math.max(1, ...data.map((d) => d.traitees + d.aTraiter));
    return { data, max };
  }, [rows]);

  const kpis = useMemo(() => {
    const traitees = rows.filter((r) => r.processed).length;
    return { aTraiter: rows.length - traitees, traitees, ecarts: rows.filter((r) => r.error > 0).length, bloquees: rows.filter((r) => r.blocked > 0).length };
  }, [rows]);

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (statusFilter !== "all" && r.status !== statusFilter) return false;
      if (supplierFilter !== "all" && r.supplier !== supplierFilter) return false;
      if (q && ![r.invoiceNumber, r.marche, r.perimetre, r.client, r.supplier].filter(Boolean).join(" ").toLowerCase().includes(q)) return false;
      return true;
    });
  }, [rows, query, statusFilter, supplierFilter]);

  const changeStatus = (row: UnifiedRow, value: UnifiedStatus) => {
    if (row.source === "cpe") actions.setStatus.mutate({ invoiceId: row.rowId, status: UNIFIED_TO_CPE[value] });
    else actions.setEnergyStatus.mutate({ importId: row.rowId, decisionStatus: UNIFIED_TO_ENERGY[value] });
  };

  const isLoading = report.isLoading && energy.isLoading;

  return (
    <div className="po2-page-v1">
      <header className="po2-prototype-page-head">
        <div>
          <span className="po2-eyebrow">Factures & décisions</span>
          <h1>Contrôler, décider, transmettre aux finances.</h1>
          <p>DALKIA (CPE), ENGIE et EDF dans une file unique. La comptable valide chaque numéro de facture.</p>
        </div>
        <div className="po2-prototype-actions">
          <Button variant="ghost">Rapport de contrôle</Button>
          <Button>Importer des factures</Button>
        </div>
      </header>

      <div className="po2-proto-kpi-grid">
        <article><span>À traiter</span><strong>{kpis.aTraiter}</strong><small>en attente de décision</small></article>
        <article><span>Déjà traitées</span><strong>{kpis.traitees}</strong><small>validées ou transmises</small></article>
        <article><span>Avec écarts</span><strong>{kpis.ecarts}</strong><small>à examiner</small></article>
        <article><span>Bloquées</span><strong>{kpis.bloquees}</strong><small>donnée manquante</small></article>
      </div>

      <section className="po2-proto-panel" style={{ padding: "1.15rem", marginBottom: "1rem" }}>
        <div className="po2-proto-panel-head">
          <div>
            <span className="po2-eyebrow">Charge annuelle</span>
            <h2>Factures par mois d’émission</h2>
            <p>Vert : déjà traitées (validées ou transmises). Orange : à traiter.</p>
          </div>
        </div>
        <div className="po2-month-chart">
          {monthly.data.map((d, i) => {
            const total = d.traitees + d.aTraiter;
            return (
              <div key={MONTHS[i]} className="po2-month-chart__col" title={`${MONTHS[i]} : ${d.traitees} traitée(s), ${d.aTraiter} à traiter`}>
                <div className="po2-month-chart__bar">
                  <div className="po2-month-chart__seg po2-month-chart__seg--todo" style={{ height: `${(d.aTraiter / monthly.max) * 100}%` }} />
                  <div className="po2-month-chart__seg po2-month-chart__seg--done" style={{ height: `${(d.traitees / monthly.max) * 100}%` }} />
                </div>
                <span className="po2-month-chart__count">{total || ""}</span>
                <span className="po2-month-chart__label">{MONTHS[i]}</span>
              </div>
            );
          })}
        </div>
      </section>

      <div className="po2-proto-toolbar-row">
        <label>
          <span>⌕</span>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="N° facture, contrat, marché, destinataire…" />
        </label>
        <select value={supplierFilter} onChange={(e) => setSupplierFilter(e.target.value)} aria-label="Filtrer fournisseur">
          <option value="all">Tous les fournisseurs</option>
          {suppliers.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Filtrer décision">
          <option value="all">Toutes les décisions</option>
          {UNIFIED_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <span style={{ marginLeft: "auto", color: "var(--po2-color-muted)", fontSize: ".8rem" }}>{filteredRows.length} / {rows.length} facture(s)</span>
      </div>

      <section className="po2-proto-panel po2-proto-table-panel">
        {isLoading ? (
          <p className="po2-muted-line" style={{ padding: "1rem" }}>Chargement des factures…</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Facture</th><th>Fournisseur</th><th>Type</th><th>Client</th><th>Marché</th><th>Périmètre</th>
                <th style={{ textAlign: "right" }}>Montant</th><th style={{ textAlign: "right" }}>OK</th><th style={{ textAlign: "right" }}>Écarts</th><th style={{ textAlign: "right" }}>Bloqués</th><th>Décision</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => (
                <tr key={row.key} className={row.key === selectedKey ? "active" : ""} onClick={() => setSelectedKey(row.key)}>
                  <td><div className="po2-proto-supplier"><span className="po2-proto-supplier-logo">{row.supplier.slice(0, 2).toUpperCase()}</span><b>{row.invoiceNumber}</b></div></td>
                  <td>{row.supplier}</td>
                  <td>{row.type}</td>
                  <td>{row.client}</td>
                  <td>{row.marche}</td>
                  <td>{row.perimetre}</td>
                  <td style={{ textAlign: "right" }}><strong>{fmtEur(row.total)}</strong></td>
                  <td style={{ textAlign: "right", color: "#166534" }}>{row.source === "cpe" ? row.ok : "—"}</td>
                  <td style={{ textAlign: "right", color: row.error ? "#b91c1c" : undefined, fontWeight: row.error ? 700 : 400 }}>{row.error}</td>
                  <td style={{ textAlign: "right", color: row.blocked ? "#b45309" : undefined, fontWeight: row.blocked ? 700 : 400 }}>{row.source === "cpe" ? row.blocked : "—"}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <select value={row.status} disabled={actions.setStatus.isPending || actions.setEnergyStatus.isPending}
                      onChange={(e) => changeStatus(row, e.target.value as UnifiedStatus)}
                      style={{ padding: "4px 6px", borderRadius: 6, border: "1px solid var(--po2-color-line)", fontSize: ".75rem" }}>
                      {UNIFIED_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
              {filteredRows.length === 0 ? <tr><td colSpan={11} className="po2-muted-line">Aucune facture ne correspond aux filtres.</td></tr> : null}
            </tbody>
          </table>
        )}
      </section>

      <Drawer
        open={Boolean(selected)}
        title={selected ? "Facture " + selected.invoiceNumber : "Facture"}
        eyebrow={selected ? "Dossier facture · " + selected.supplier : "Dossier facture"}
        description={selected ? selected.supplier + " · " + selected.marche + " · " + selected.perimetre : undefined}
        onClose={() => setSelectedKey(null)}
      >
        {selected ? (
          <div className="po2-proto-dossier">
            <div className="po2-proto-dossier-kpis">
              <div><span>Montant</span><b>{fmtEur(selected.total)}</b></div>
              <div><span>Contrôles</span><b>{selected.source === "cpe" ? `${selected.ok} OK · ${selected.error} écart · ${selected.blocked} bloqué` : `${selected.error} écart(s)`}</b></div>
              <div><span>Décision</span><b>{statusLabel(selected.status)}</b></div>
            </div>

            {selected.source === "cpe" ? (
              <>
                <h3>Contrôles par numéro de facture</h3>
                <ControlDecomposition controls={detail.controls.data ?? []} loading={detail.controls.isLoading} />
                <h3>Décomposition comptable (export finance)</h3>
                <LineDecomposition lines={detail.lines.data ?? []} loading={detail.lines.isLoading} />
              </>
            ) : (
              <>
                <h3>Contrôle fournisseur</h3>
                <p className="po2-muted-line">{selected.error > 0 ? `${selected.error} écart(s) de contrôle détecté(s).` : "Aucun écart de contrôle bloquant."} Le détail BPU/TURPE/taxes est disponible dans le module Énergie.</p>
              </>
            )}

            <div className="po2-proto-decision-box">
              <span>Décision comptable</span>
              <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap", alignItems: "center", marginTop: ".4rem" }}>
                <select value={selected.status} disabled={actions.setStatus.isPending || actions.setEnergyStatus.isPending}
                  onChange={(e) => changeStatus(selected, e.target.value as UnifiedStatus)}
                  style={{ padding: "6px 8px", borderRadius: 8, border: "1px solid var(--po2-color-line)" }}>
                  {UNIFIED_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <StatusBadge tone={statusTone(selected.status)}>{statusLabel(selected.status)}</StatusBadge>
              </div>
            </div>

            <div className="po2-proto-action-stack">
              {selected.source === "cpe" ? (
                <Button onClick={() => actions.exportLiaison.mutate({ invoiceId: selected.rowId, invoiceNumber: selected.invoiceNumber })} disabled={actions.exportLiaison.isPending}>
                  {actions.exportLiaison.isPending ? "Export…" : "Exporter la fiche finance (XLSX)"}
                </Button>
              ) : null}
              <Button variant="danger" disabled title="Génération du courrier de réclamation à venir">Préparer une réclamation (à venir)</Button>
            </div>
            {actions.setStatus.isError ? <p className="po2-action-error">Décision : {(actions.setStatus.error as Error).message}</p> : null}
            {actions.setEnergyStatus.isError ? <p className="po2-action-error">Décision : {(actions.setEnergyStatus.error as Error).message}</p> : null}
            {actions.exportLiaison.isError ? <p className="po2-action-error">Export : {(actions.exportLiaison.error as Error).message}</p> : null}
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}

function ControlDecomposition({ controls, loading }: { controls: CpeFinanceControl[]; loading: boolean }) {
  const groups = useMemo(() => {
    const map = new Map<string, CpeFinanceControl[]>();
    for (const c of controls) { const arr = map.get(c.control_type) ?? []; arr.push(c); map.set(c.control_type, arr); }
    return Array.from(map.entries());
  }, [controls]);
  if (loading) return <p className="po2-muted-line">Chargement des contrôles…</p>;
  if (controls.length === 0) return <p className="po2-muted-line">Aucun contrôle enregistré pour cette facture.</p>;
  return (
    <div className="po2-proto-control-list">
      {groups.map(([type, items]) => {
        const worst = items.find((i) => i.status === "blocked") ?? items.find((i) => i.status === "error") ?? items[0];
        return (
          <article key={type}>
            <StatusBadge tone={controlTone(worst.status, worst.severity)}>{worst.status === "ok" ? "OK" : worst.status.toUpperCase()}</StatusBadge>
            <div><strong>{controlTypeLabel(type)}</strong><small>{items.map((i) => i.message).filter(Boolean).slice(0, 2).join(" · ") || "Contrôle effectué"}</small></div>
          </article>
        );
      })}
    </div>
  );
}

function LineDecomposition({ lines, loading }: { lines: CpeFinanceLine[]; loading: boolean }) {
  if (loading) return <p className="po2-muted-line">Chargement de la décomposition…</p>;
  if (lines.length === 0) return <p className="po2-muted-line">Aucune ligne comptable. La décomposition apparaît après rattachement à la matrice.</p>;
  const total = lines.reduce((s, l) => s + (l.amount_ht ?? 0), 0);
  return (
    <>
      <div className="po2-proto-control-list">
        {lines.slice(0, 12).map((line) => (
          <article key={line.id} style={{ gridTemplateColumns: "1fr auto" }}>
            <div><strong>{line.billed_item ?? line.market ?? "Ligne"} · {fmtEur(line.amount_ht)}</strong>
              <small>{[line.accounting_nature, line.accounting_label, line.service_sold, line.site_code_detected].filter(Boolean).join(" · ") || "Nature comptable à compléter"}</small></div>
            {!line.accounting_nature ? <StatusBadge tone="warn">À compléter</StatusBadge> : <StatusBadge tone="ok">Imputée</StatusBadge>}
          </article>
        ))}
      </div>
      {lines.length > 12 ? <p className="po2-muted-line" style={{ marginTop: ".4rem" }}>+ {lines.length - 12} autre(s) ligne(s)…</p> : null}
      <p className="po2-muted-line" style={{ marginTop: ".4rem" }}>Total décomposé : <strong>{fmtEur(total)}</strong></p>
    </>
  );
}
