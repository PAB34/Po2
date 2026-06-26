import { useMemo, useState } from "react";
import { Button, Drawer, StatusBadge } from "../../design-system";
import { useCpeFinanceQueueV1, useCpeInvoiceDetailV1, useCpeInvoiceActionsV1 } from "./useCpeFinanceQueueV1";
import type { CpeFinanceControl, CpeFinanceControlReport, CpeFinanceLine } from "../../lib/api";

type QueueInvoice = CpeFinanceControlReport["invoices"][number];

// ---------------------------------------------------------------------------
// Libellés & helpers
// ---------------------------------------------------------------------------
const STATUS_OPTIONS = [
  { value: "a_controler", label: "À contrôler" },
  { value: "valide", label: "Validée" },
  { value: "refuse", label: "Refusée" },
  { value: "conteste", label: "Contestée" },
];

const CONTROL_TYPE_LABELS: Record<string, string> = {
  coherence: "Cohérence",
  fourniture: "Fourniture",
  acheminement: "Acheminement",
  taxes: "Taxes",
  p1: "P1 gaz",
  p1_quantite: "P1 quantité",
  p1_prix: "P1 prix",
  revision: "Révision",
  documentaire: "Documentaire",
  comptable: "Comptable",
  echeance: "Échéance",
};

function controlTypeLabel(type: string) {
  return CONTROL_TYPE_LABELS[type] ?? type.replace(/_/g, " ");
}

function statusLabel(status: string) {
  return STATUS_OPTIONS.find((o) => o.value === status)?.label ?? status;
}

function statusTone(status: string) {
  if (status === "valide") return "ok" as const;
  if (status === "refuse" || status === "conteste") return "bad" as const;
  return "warn" as const;
}

function controlTone(status: string, severity: string) {
  if (status === "ok") return "ok" as const;
  if (status === "blocked" || severity === "blocking") return "bad" as const;
  if (status === "error") return "bad" as const;
  return "warn" as const;
}

function isProcessed(row: QueueInvoice) {
  return row.invoice_status === "valide" || Boolean(row.finance_exported_at);
}

function fmtEur(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value);
}

const MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"];

export function InvoicesDecisionPageV1() {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { report, invoices } = useCpeFinanceQueueV1();
  const detail = useCpeInvoiceDetailV1(selectedId);
  const actions = useCpeInvoiceActionsV1();

  const rows = report.data?.invoices ?? [];
  const selected = rows.find((r) => r.invoice_id === selectedId) ?? null;

  // Date d'émission par facture (pour le graphique mensuel)
  const issueMonthById = useMemo(() => {
    const map = new Map<number, number>();
    for (const inv of invoices.data ?? []) {
      if (inv.invoice_date) {
        const m = Number(inv.invoice_date.slice(5, 7)) - 1;
        if (m >= 0 && m < 12) map.set(inv.id, m);
      }
    }
    return map;
  }, [invoices.data]);

  const monthly = useMemo(() => {
    const data = MONTHS.map(() => ({ traitees: 0, aTraiter: 0 }));
    for (const row of rows) {
      const m = issueMonthById.get(row.invoice_id);
      if (m === undefined) continue;
      if (isProcessed(row)) data[m].traitees += 1;
      else data[m].aTraiter += 1;
    }
    const max = Math.max(1, ...data.map((d) => d.traitees + d.aTraiter));
    return { data, max };
  }, [rows, issueMonthById]);

  const kpis = useMemo(() => {
    const report_ = report.data;
    const traitees = rows.filter(isProcessed).length;
    const aTraiter = rows.length - traitees;
    return {
      aTraiter,
      traitees,
      ecarts: report_?.invoices_with_errors ?? 0,
      bloquees: report_?.invoices_blocked ?? 0,
    };
  }, [rows, report.data]);

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((row) => {
      if (statusFilter !== "all" && row.invoice_status !== statusFilter) return false;
      if (q) {
        const hay = [row.invoice_number, row.contract_label, row.contract_code, row.market, row.billed_items, row.recipient_ref]
          .filter(Boolean).join(" ").toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [rows, query, statusFilter]);

  const isLoading = report.isLoading;
  const isError = report.isError;

  return (
    <div className="po2-page-v1">
      <header className="po2-prototype-page-head">
        <div>
          <span className="po2-eyebrow">Factures & décisions · CPE DALKIA</span>
          <h1>Contrôler, décider, transmettre aux finances.</h1>
          <p>La comptable valide chaque numéro de facture ; l’export finance en restitue la décomposition comptable.</p>
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
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Filtrer décision">
          <option value="all">Toutes les décisions</option>
          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <span style={{ marginLeft: "auto", color: "var(--po2-color-muted)", fontSize: ".8rem" }}>
          {filteredRows.length} / {rows.length} facture(s)
        </span>
      </div>

      <section className="po2-proto-panel po2-proto-table-panel">
        {isLoading ? (
          <p className="po2-muted-line" style={{ padding: "1rem" }}>Chargement du rapport de contrôle…</p>
        ) : isError ? (
          <p className="po2-action-error" style={{ padding: "1rem" }}>Rapport de contrôle indisponible. Lancez un contrôle global depuis la page CPE.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Facture</th>
                <th>Contrat</th>
                <th>Type</th>
                <th>Destinataire</th>
                <th>Marché</th>
                <th>Postes facturés</th>
                <th style={{ textAlign: "right" }}>HT</th>
                <th style={{ textAlign: "right" }}>OK</th>
                <th style={{ textAlign: "right" }}>Écarts</th>
                <th style={{ textAlign: "right" }}>Bloqués</th>
                <th>Décision</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => (
                <tr key={row.invoice_id} className={row.invoice_id === selectedId ? "active" : ""} onClick={() => setSelectedId(row.invoice_id)}>
                  <td><b>{row.invoice_number}</b></td>
                  <td>{row.contract_label ?? row.contract_code ?? "—"}</td>
                  <td>{row.invoice_type ?? "—"}</td>
                  <td>{row.recipient_ref ?? "—"}</td>
                  <td>{row.market ?? "—"}</td>
                  <td>{row.billed_items ?? "—"}</td>
                  <td style={{ textAlign: "right" }}><strong>{fmtEur(row.total_ht)}</strong></td>
                  <td style={{ textAlign: "right", color: "#166534" }}>{row.ok}</td>
                  <td style={{ textAlign: "right", color: row.error ? "#b91c1c" : undefined, fontWeight: row.error ? 700 : 400 }}>{row.error}</td>
                  <td style={{ textAlign: "right", color: row.blocked ? "#b45309" : undefined, fontWeight: row.blocked ? 700 : 400 }}>{row.blocked}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <select
                      value={row.invoice_status}
                      disabled={actions.setStatus.isPending}
                      onChange={(e) => actions.setStatus.mutate({ invoiceId: row.invoice_id, status: e.target.value })}
                      style={{ padding: "4px 6px", borderRadius: 6, border: "1px solid var(--po2-color-line)", fontSize: ".75rem" }}
                    >
                      {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
              {filteredRows.length === 0 ? (
                <tr><td colSpan={11} className="po2-muted-line">Aucune facture ne correspond aux filtres.</td></tr>
              ) : null}
            </tbody>
          </table>
        )}
      </section>

      <Drawer
        open={Boolean(selected)}
        title={selected ? "Facture " + selected.invoice_number : "Facture"}
        eyebrow="Dossier facture"
        description={selected ? (selected.contract_label ?? selected.contract_code ?? "") + " · " + (selected.market ?? "") : undefined}
        onClose={() => setSelectedId(null)}
      >
        {selected ? (
          <div className="po2-proto-dossier">
            <div className="po2-proto-dossier-kpis">
              <div><span>Montant HT</span><b>{fmtEur(selected.total_ht)}</b></div>
              <div><span>Contrôles</span><b>{selected.ok} OK · {selected.error} écart · {selected.blocked} bloqué</b></div>
              <div><span>Décision</span><b>{statusLabel(selected.invoice_status)}</b></div>
            </div>

            <h3>Contrôles par numéro de facture</h3>
            <ControlDecomposition controls={detail.controls.data ?? []} loading={detail.controls.isLoading} />

            <h3>Décomposition comptable (export finance)</h3>
            <LineDecomposition lines={detail.lines.data ?? []} loading={detail.lines.isLoading} />

            <div className="po2-proto-decision-box">
              <span>Décision comptable</span>
              <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap", alignItems: "center", marginTop: ".4rem" }}>
                <select
                  value={selected.invoice_status}
                  disabled={actions.setStatus.isPending}
                  onChange={(e) => actions.setStatus.mutate({ invoiceId: selected.invoice_id, status: e.target.value })}
                  style={{ padding: "6px 8px", borderRadius: 8, border: "1px solid var(--po2-color-line)" }}
                >
                  {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <StatusBadge tone={statusTone(selected.invoice_status)}>{statusLabel(selected.invoice_status)}</StatusBadge>
              </div>
            </div>

            <div className="po2-proto-action-stack">
              <Button onClick={() => actions.exportLiaison.mutate({ invoiceId: selected.invoice_id, invoiceNumber: selected.invoice_number })} disabled={actions.exportLiaison.isPending}>
                {actions.exportLiaison.isPending ? "Export…" : "Exporter la fiche finance (XLSX)"}
              </Button>
              <Button variant="danger" disabled title="Génération du courrier de réclamation à venir">Préparer une réclamation (à venir)</Button>
            </div>
            {actions.setStatus.isError ? <p className="po2-action-error">Décision : {(actions.setStatus.error as Error).message}</p> : null}
            {actions.exportLiaison.isError ? <p className="po2-action-error">Export : {(actions.exportLiaison.error as Error).message}</p> : null}

            {selected.finance_exported_at ? (
              <p className="po2-muted-line" style={{ marginTop: ".6rem" }}>Transmise aux finances le {selected.finance_exported_at}.</p>
            ) : null}
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sous-composants du tiroir
// ---------------------------------------------------------------------------
function ControlDecomposition({ controls, loading }: { controls: CpeFinanceControl[]; loading: boolean }) {
  const groups = useMemo(() => {
    const map = new Map<string, CpeFinanceControl[]>();
    for (const c of controls) {
      const arr = map.get(c.control_type) ?? [];
      arr.push(c);
      map.set(c.control_type, arr);
    }
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
            <div>
              <strong>{controlTypeLabel(type)}</strong>
              <small>{items.map((i) => i.message).filter(Boolean).slice(0, 2).join(" · ") || "Contrôle effectué"}</small>
            </div>
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
            <div>
              <strong>{line.billed_item ?? line.market ?? "Ligne"} · {fmtEur(line.amount_ht)}</strong>
              <small>
                {[line.accounting_nature, line.accounting_label, line.service_sold, line.site_code_detected].filter(Boolean).join(" · ") || "Nature comptable à compléter"}
              </small>
            </div>
            {!line.accounting_nature ? <StatusBadge tone="warn">À compléter</StatusBadge> : <StatusBadge tone="ok">Imputée</StatusBadge>}
          </article>
        ))}
      </div>
      {lines.length > 12 ? <p className="po2-muted-line" style={{ marginTop: ".4rem" }}>+ {lines.length - 12} autre(s) ligne(s)…</p> : null}
      <p className="po2-muted-line" style={{ marginTop: ".4rem" }}>Total décomposé : <strong>{fmtEur(total)}</strong></p>
    </>
  );
}
