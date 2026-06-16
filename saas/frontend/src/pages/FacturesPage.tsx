import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchCpeFinanceInvoices, fetchEnergyInvoiceImports } from "../lib/api";
import type { EnergyInvoiceImport } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";
import { EnergieInvoicesPage, type SupplierKey } from "./EnergieInvoicesPage";

type Market = "herault" | "dalkia" | "spie";

const MARKETS: { key: Market; label: string }[] = [
  { key: "herault", label: "Hérault Énergie" },
  { key: "dalkia", label: "DALKIA" },
  { key: "spie", label: "SPIE" },
];

type HeraultSupplier = "ENGIE" | "EDF" | "TOTALENERGIES";

const HERAULT_SUPPLIER_LABEL: Record<HeraultSupplier, string> = {
  ENGIE: "ENGIE",
  EDF: "EDF",
  TOTALENERGIES: "TotalEnergies",
};

function heraultSupplier(value: string | null): HeraultSupplier | "AUTRE" {
  const upper = (value ?? "").toUpperCase();
  if (upper.includes("ENGIE")) return "ENGIE";
  if (upper.includes("EDF") || upper.includes("ELECTRICITE DE FRANCE")) return "EDF";
  if (upper.includes("TOTAL")) return "TOTALENERGIES";
  return "AUTRE";
}

function formatInt(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("fr-FR").format(value);
}

function formatEur(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value);
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString("fr-FR");
}

type SupplierStat = {
  supplier: HeraultSupplier;
  count: number;
  gaps: number;
  ttc: number;
  exported: number;
};

function HeraultEtat({ invoices }: { invoices: EnergyInvoiceImport[] }) {
  const stats = useMemo<SupplierStat[]>(() => {
    const order: HeraultSupplier[] = ["ENGIE", "EDF", "TOTALENERGIES"];
    return order.map((supplier) => {
      const rows = invoices.filter((i) => heraultSupplier(i.supplier_guess) === supplier);
      return {
        supplier,
        count: rows.length,
        gaps: rows.filter((i) => i.control_status === "invalid" || (i.control_errors_count ?? 0) > 0).length,
        ttc: rows.reduce((sum, i) => sum + (i.total_ttc ?? 0), 0),
        exported: rows.filter((i) => i.finance_exported_at).length,
      };
    });
  }, [invoices]);

  const lastImport = useMemo(() => {
    const dates = invoices.map((i) => i.created_at).filter(Boolean).sort();
    return dates.length ? dates[dates.length - 1] : null;
  }, [invoices]);

  return (
    <div className="fct-etat">
      <div className="fct-etat-head">
        <strong>État — Hérault Énergie</strong>
        <span className="fct-etat-meta">dernier import {formatDate(lastImport)}</span>
      </div>
      <table className="fct-etat-table">
        <thead>
          <tr>
            <th>Fournisseur</th>
            <th>Factures</th>
            <th>Écarts</th>
            <th>Montant TTC</th>
            <th>Transmises finance</th>
          </tr>
        </thead>
        <tbody>
          {stats.map((stat) => (
            <tr key={stat.supplier}>
              <td>{HERAULT_SUPPLIER_LABEL[stat.supplier]}</td>
              <td>{formatInt(stat.count)}</td>
              <td>
                {stat.gaps > 0 ? (
                  <span className="cockpit-badge cockpit-badge--danger">{formatInt(stat.gaps)}</span>
                ) : (
                  <span className="cockpit-badge cockpit-badge--ok">0</span>
                )}
              </td>
              <td>{formatEur(stat.ttc)}</td>
              <td className="fct-etat-muted">
                {formatInt(stat.exported)} / {formatInt(stat.count)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="fct-etat-note">
        Les imports et le contrôle détaillé (par étape) sont disponibles ci-dessous. Montant HT par fournisseur :
        à brancher dans une prochaine étape.
      </p>
    </div>
  );
}

function DalkiaEtat() {
  const { token } = useAuth();
  const invoicesQuery = useQuery({
    queryKey: ["factures-dalkia"],
    queryFn: () => fetchCpeFinanceInvoices(token!),
    enabled: !!token,
  });

  const summary = useMemo(() => {
    const invoices = invoicesQuery.data ?? [];
    const recipients = new Set(
      invoices.map((i) => (i.recipient_reference_1 || i.customer_name || "").trim()).filter(Boolean),
    );
    return { count: invoices.length, recipients: recipients.size };
  }, [invoicesQuery.data]);

  return (
    <div className="fct-etat">
      <div className="fct-etat-head">
        <strong>État — DALKIA (CPE)</strong>
        <Link to="/cpe" className="cockpit-queue-action">
          Ouvrir le suivi DALKIA <span aria-hidden="true">↗</span>
        </Link>
      </div>
      <table className="fct-etat-table">
        <thead>
          <tr>
            <th>Indicateur</th>
            <th>Valeur</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Factures CPE importées</td>
            <td>{invoicesQuery.isLoading ? "…" : formatInt(summary.count)}</td>
          </tr>
          <tr>
            <td>Destinataires distincts</td>
            <td>{invoicesQuery.isLoading ? "…" : formatInt(summary.recipients)}</td>
          </tr>
        </tbody>
      </table>
      <p className="fct-etat-note">
        Détail par poste (P1/P2/P3), par destinataire et atterrissage (cibles contractuelles) : prochaine étape.
        Le contrôle finances DALKIA reste accessible via « Ouvrir le suivi DALKIA ».
      </p>
    </div>
  );
}

export default function FacturesPage() {
  const [market, setMarket] = useState<Market>("herault");

  return (
    <section className="fct">
      <div className="fct-head">
        <div>
          <p className="cockpit-eyebrow">Factures</p>
          <h2 className="cockpit-title">Contrôle des factures par marché</h2>
        </div>
      </div>

      <div className="fct-markets" role="tablist" aria-label="Marchés">
        {MARKETS.map((m) => (
          <button
            key={m.key}
            type="button"
            role="tab"
            aria-selected={market === m.key}
            className={`fct-market-tab${market === m.key ? " fct-market-tab--active" : ""}`}
            onClick={() => setMarket(m.key)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {market === "herault" && <HeraultSection />}

      {market === "dalkia" && (
        <div className="fct-market-body">
          <DalkiaEtat />
        </div>
      )}

      {market === "spie" && (
        <div className="fct-market-body">
          <div className="fct-etat">
            <div className="fct-etat-head">
              <strong>État — SPIE (maintenance P2)</strong>
              <span className="cockpit-badge cockpit-badge--neutral">factures à intégrer</span>
            </div>
            <p className="fct-etat-note">
              Marché de maintenance P2 (pas de P1 ni de cibles contractuelles, donc pas d'atterrissage). L'import
              des factures SPIE et leur contrôle seront branchés ici. SPIE est aujourd'hui présent comme source
              d'inventaire technique CVC.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

type HeraultSub = "etat" | SupplierKey;

const HERAULT_SUBS: { key: HeraultSub; label: string }[] = [
  { key: "etat", label: "État" },
  { key: "ENGIE", label: "ENGIE" },
  { key: "EDF", label: "EDF" },
  { key: "TOTALENERGIES", label: "TotalEnergies" },
];

function HeraultSection() {
  const [sub, setSub] = useState<HeraultSub>("etat");
  return (
    <div className="fct-market-body">
      <div className="fct-subtabs" role="tablist" aria-label="Hérault Énergie">
        {HERAULT_SUBS.map((item) => (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={sub === item.key}
            className={`fct-subtab${sub === item.key ? " fct-subtab--active" : ""}`}
            onClick={() => setSub(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {sub === "etat" ? (
        <HeraultEtatLoader />
      ) : (
        <div className="fct-embed">
          <EnergieInvoicesPage supplierFilter={sub} />
        </div>
      )}
    </div>
  );
}

function HeraultEtatLoader() {
  const { token } = useAuth();
  const invoicesQuery = useQuery({
    queryKey: ["factures-herault-etat"],
    queryFn: () => fetchEnergyInvoiceImports(token!),
    enabled: !!token,
  });
  return <HeraultEtat invoices={invoicesQuery.data ?? []} />;
}
