import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchCpeFinanceInvoices, fetchCpeMarketTracking, fetchEnergyInvoiceImports } from "../lib/api";
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

function HeraultEtat({
  invoices,
  onSelectSupplier,
}: {
  invoices: EnergyInvoiceImport[];
  onSelectSupplier: (supplier: HeraultSupplier) => void;
}) {
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
  const totalTtc = stats.reduce((sum, stat) => sum + stat.ttc, 0);
  const totalGaps = stats.reduce((sum, stat) => sum + stat.gaps, 0);
  const totalExported = stats.reduce((sum, stat) => sum + stat.exported, 0);

  return (
    <div className="fct-etat">
      <div className="fct-etat-head">
        <strong>État — Hérault Énergie</strong>
        <span className="fct-etat-meta">dernier import {formatDate(lastImport)}</span>
      </div>
      <div className="fct-overview-grid">
        <div className="fct-overview-card">
          <span>Factures importees</span>
          <strong>{formatInt(invoices.length)}</strong>
          <small>ENGIE, EDF et gaz a venir</small>
        </div>
        <div className="fct-overview-card">
          <span>Ecarts a traiter</span>
          <strong>{formatInt(totalGaps)}</strong>
          <small>Controle BPU, TURPE, periodes</small>
        </div>
        <div className="fct-overview-card">
          <span>Montant TTC suivi</span>
          <strong>{formatEur(totalTtc)}</strong>
          <small>{formatInt(totalExported)} transmise(s) finance</small>
        </div>
      </div>
      <table className="fct-etat-table">
        <thead>
          <tr>
            <th>Fournisseur</th>
            <th>Factures</th>
            <th>Écarts</th>
            <th>Montant TTC</th>
            <th>Transmises finance</th>
            <th>Action</th>
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
              <td>
                {stat.supplier === "TOTALENERGIES" ? (
                  <span className="cockpit-badge cockpit-badge--neutral">a preparer</span>
                ) : (
                  <button type="button" className="btn-secondary btn-compact" onClick={() => onSelectSupplier(stat.supplier)}>
                    Ouvrir
                  </button>
                )}
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

function ecartBadge(ecart: number) {
  const tone = ecart > 0 ? "danger" : "ok";
  const sign = ecart > 0 ? "+" : "";
  return <span className={`cockpit-badge cockpit-badge--${tone}`}>{sign}{formatEur(ecart)}</span>;
}

type DalkiaSub = "etat" | "global" | "poste" | "destinataire";

const DALKIA_SUBS: { key: DalkiaSub; label: string }[] = [
  { key: "etat", label: "État" },
  { key: "global", label: "Global" },
  { key: "poste", label: "Poste" },
  { key: "destinataire", label: "Destinataire" },
];

function DalkiaSection() {
  const { token } = useAuth();
  const [sub, setSub] = useState<DalkiaSub>("etat");
  const yearTo = new Date().getFullYear();
  const yearFrom = yearTo - 2;

  const trackingQuery = useQuery({
    queryKey: ["factures-dalkia-tracking", yearFrom, yearTo],
    queryFn: () => fetchCpeMarketTracking(token!, yearFrom, yearTo),
    enabled: !!token,
  });
  const invoicesQuery = useQuery({
    queryKey: ["factures-dalkia-invoices"],
    queryFn: () => fetchCpeFinanceInvoices(token!),
    enabled: !!token,
  });

  const tracking = trackingQuery.data;
  const invoices = invoicesQuery.data ?? [];

  const byRecipient = useMemo(() => {
    const map = new Map<string, number>();
    for (const inv of invoices) {
      const key = (inv.recipient_reference_1 || inv.customer_name || "—").trim() || "—";
      map.set(key, (map.get(key) ?? 0) + 1);
    }
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1]);
  }, [invoices]);

  return (
    <div className="fct-market-body">
      <div className="fct-subtabs" role="tablist" aria-label="DALKIA">
        {DALKIA_SUBS.map((item) => (
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

      {sub === "etat" && (
        <div className="fct-etat">
          <div className="fct-etat-head">
            <strong>État — DALKIA (CPE)</strong>
            <Link to="/cpe" className="cockpit-queue-action">
              Ouvrir le suivi DALKIA <span aria-hidden="true">↗</span>
            </Link>
          </div>
          <table className="fct-etat-table">
            <thead>
              <tr><th>Indicateur</th><th>Valeur</th></tr>
            </thead>
            <tbody>
              <tr><td>Factures CPE importées</td><td>{formatInt(invoices.length)}</td></tr>
              <tr><td>Destinataires distincts</td><td>{formatInt(byRecipient.length)}</td></tr>
              <tr><td>Prévu (cumul)</td><td>{formatEur(tracking?.grand_total.prevu)}</td></tr>
              <tr><td>Reçu / facturé (cumul)</td><td>{formatEur(tracking?.grand_total.recu)}</td></tr>
              <tr>
                <td>Écart cumulé</td>
                <td>{tracking ? ecartBadge(tracking.grand_total.ecart) : "—"}</td>
              </tr>
            </tbody>
          </table>
          <p className="fct-etat-note">
            « Prévu » = cibles/échéancier contractuel ; « reçu » = facturé. Le détail (atterrissage par cible,
            intéressement) est dans l'onglet Poste et sur le suivi DALKIA.
          </p>
        </div>
      )}

      {sub === "global" && (
        <div className="fct-etat">
          <div className="fct-etat-head"><strong>Global — prévu / facturé par année</strong></div>
          {tracking && tracking.totals_by_year.length > 0 ? (
            <table className="fct-etat-table">
              <thead>
                <tr><th>Année</th><th>Prévu</th><th>Facturé</th><th>Écart</th><th>Taux</th></tr>
              </thead>
              <tbody>
                {tracking.totals_by_year.map((cell) => (
                  <tr key={cell.year}>
                    <td>{cell.year}</td>
                    <td>{formatEur(cell.prevu)}</td>
                    <td>{formatEur(cell.recu)}</td>
                    <td>{ecartBadge(cell.ecart)}</td>
                    <td className="fct-etat-muted">{cell.taux != null ? `${Math.round(cell.taux * 100)} %` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="fct-etat-note">{trackingQuery.isLoading ? "Chargement…" : "Aucune référence de suivi disponible."}</p>
          )}
        </div>
      )}

      {sub === "poste" && (
        <div className="fct-etat">
          <div className="fct-etat-head"><strong>Poste — P1 / P2 / P3</strong></div>
          {tracking && tracking.postes.length > 0 ? (
            <table className="fct-etat-table">
              <thead>
                <tr><th>Poste</th><th>Prévu</th><th>Facturé</th><th>Écart</th></tr>
              </thead>
              <tbody>
                {tracking.postes.map((poste) => (
                  <tr key={poste.poste}>
                    <td>{poste.poste} · {poste.label}</td>
                    <td>{formatEur(poste.total.prevu)}</td>
                    <td>{formatEur(poste.total.recu)}</td>
                    <td>{ecartBadge(poste.total.ecart)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="fct-etat-note">{trackingQuery.isLoading ? "Chargement…" : "Aucune donnée par poste."}</p>
          )}
        </div>
      )}

      {sub === "destinataire" && (
        <div className="fct-etat">
          <div className="fct-etat-head"><strong>Destinataire — REF DESTINATAIRE 1 / nom client</strong></div>
          {byRecipient.length > 0 ? (
            <table className="fct-etat-table">
              <thead>
                <tr><th>Destinataire</th><th>Factures</th></tr>
              </thead>
              <tbody>
                {byRecipient.map(([recipient, count]) => (
                  <tr key={recipient}>
                    <td>{recipient}</td>
                    <td>{formatInt(count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="fct-etat-note">{invoicesQuery.isLoading ? "Chargement…" : "Aucune facture DALKIA importée."}</p>
          )}
          <p className="fct-etat-note">
            Le périmètre Ville est filtré sur le destinataire (« Commune de Sète » retenu) côté contrôle finances.
          </p>
        </div>
      )}
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

      {market === "dalkia" && <DalkiaSection />}

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
        <HeraultEtatLoader onSelectSupplier={setSub} />
      ) : sub === "TOTALENERGIES" ? (
        <div className="fct-etat">
          <div className="fct-etat-head">
            <strong>TotalEnergies - gaz batiments</strong>
            <span className="cockpit-badge cockpit-badge--neutral">a preparer</span>
          </div>
          <p className="fct-etat-note">
            Cette sous-section doit controler les factures gaz du marche Herault Energie avec les PCE, les releves GRDF
            et le BPU gaz lot 7. Le moteur de prix gaz est documente, mais la page facture gaz ne doit pas etre ouverte
            tant que le parser et le rapprochement PCE ne sont pas finalises.
          </p>
        </div>
      ) : (
        <div className="fct-embed">
          <EnergieInvoicesPage supplierFilter={sub} />
        </div>
      )}
    </div>
  );
}

function HeraultEtatLoader({ onSelectSupplier }: { onSelectSupplier: (supplier: HeraultSupplier) => void }) {
  const { token } = useAuth();
  const invoicesQuery = useQuery({
    queryKey: ["factures-herault-etat"],
    queryFn: () => fetchEnergyInvoiceImports(token!),
    enabled: !!token,
  });
  return <HeraultEtat invoices={invoicesQuery.data ?? []} onSelectSupplier={onSelectSupplier} />;
}
