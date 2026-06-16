import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  fetchBuildings,
  fetchCpeSites,
  fetchEnergieOverview,
  fetchEnergyInvoiceImports,
  fetchSites,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

function formatInt(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("fr-FR").format(value);
}

function formatEur(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

type Domain = "energie" | "patrimoine" | "marches" | "technique";

const DOMAIN_LABEL: Record<Domain, string> = {
  energie: "Énergie",
  patrimoine: "Patrimoine",
  marches: "Marchés",
  technique: "Technique",
};

type BadgeTone = "warn" | "danger" | "ok" | "info" | "neutral";

function KpiCard({ label, value, hint, to }: { label: string; value: string; hint?: string; to: string }) {
  return (
    <Link to={to} className="cockpit-kpi">
      <span className="cockpit-kpi-label">{label}</span>
      <strong className="cockpit-kpi-value">{value}</strong>
      {hint && <small className="cockpit-kpi-hint">{hint}</small>}
    </Link>
  );
}

function QueueCard({
  domain,
  category,
  title,
  value,
  badge,
  badgeTone,
  action,
  to,
}: {
  domain: Domain;
  category: string;
  title: string;
  value: string;
  badge?: string;
  badgeTone?: BadgeTone;
  action: string;
  to: string;
}) {
  return (
    <article className="cockpit-queue-card">
      <div className="cockpit-queue-cat">
        <span className={`cockpit-dot cockpit-dot--${domain}`} aria-hidden="true" />
        {DOMAIN_LABEL[domain]} · {category}
      </div>
      <p className="cockpit-queue-title">{title}</p>
      <div className="cockpit-queue-num">
        <strong>{value}</strong>
        {badge && <span className={`cockpit-badge cockpit-badge--${badgeTone ?? "neutral"}`}>{badge}</span>}
      </div>
      <Link to={to} className="cockpit-queue-action">
        {action} <span aria-hidden="true">↗</span>
      </Link>
    </article>
  );
}

export function HomePage() {
  const { token, user } = useAuth();

  const invoicesQuery = useQuery({
    queryKey: ["dashboard-invoices"],
    queryFn: () => fetchEnergyInvoiceImports(token!),
    enabled: !!token,
  });
  const buildingsQuery = useQuery({
    queryKey: ["dashboard-buildings"],
    queryFn: () => fetchBuildings(token!),
    enabled: !!token,
  });
  const sitesQuery = useQuery({
    queryKey: ["dashboard-sites"],
    queryFn: () => fetchSites(token!),
    enabled: !!token,
  });
  const energieQuery = useQuery({
    queryKey: ["dashboard-energie"],
    queryFn: () => fetchEnergieOverview(token!),
    enabled: !!token,
  });
  const cpeQuery = useQuery({
    queryKey: ["dashboard-cpe"],
    queryFn: () => fetchCpeSites(token!),
    enabled: !!token,
  });

  const billing = useMemo(() => {
    const invoices = invoicesQuery.data ?? [];
    const invalid = invoices.filter((i) => i.control_status === "invalid").length;
    const review = invoices.filter((i) => i.control_status === "review").length;
    const inBpuGap = invoices.filter((i) => (i.control_errors_count ?? 0) > 0).length;
    const toExport = invoices.filter(
      (i) => i.control_status === "valid" && !i.finance_exported_at,
    ).length;
    const amount = invoices.reduce((sum, i) => sum + (i.total_ttc ?? 0), 0);
    return { total: invoices.length, invalid, review, inBpuGap, toExport, amount };
  }, [invoicesQuery.data]);

  const perimeter = useMemo(() => {
    const kpis = energieQuery.data?.kpis;
    const toRecalibrate = kpis ? (kpis.sous_dimensionnes ?? 0) + (kpis.sur_souscrits ?? 0) : null;
    return {
      buildings: buildingsQuery.data?.length ?? null,
      sites: sitesQuery.data?.length ?? null,
      prms: kpis?.total_prms ?? null,
      toRecalibrate,
      cpeActive: cpeQuery.data?.filter((s) => s.actif).length ?? null,
    };
  }, [buildingsQuery.data, sitesQuery.data, energieQuery.data, cpeQuery.data]);

  return (
    <section className="cockpit">
      <div className="cockpit-header">
        <div>
          <p className="cockpit-eyebrow">Patrimoineaucarré</p>
          <h2 className="cockpit-title">Tableau de bord</h2>
          <p className="cockpit-subtitle">
            {user
              ? `Bonjour ${user.prenom}. Voici l’état courant de ton périmètre et des contrôles à mener.`
              : "Connecte-toi pour accéder à ton périmètre."}
          </p>
        </div>
        <Link className="primary-link" to="/factures">
          Contrôler les factures
        </Link>
      </div>

      <div className="cockpit-kpi-grid">
        <KpiCard label="Bâtiments" value={formatInt(perimeter.buildings)} to="/patrimoine" />
        <KpiCard
          label="Points de livraison"
          value={formatInt(perimeter.prms)}
          hint="PRM électricité"
          to="/energie"
        />
        <KpiCard
          label="Factures importées"
          value={formatInt(billing.total)}
          to="/factures"
        />
        <KpiCard
          label="Montant TTC importé"
          value={formatEur(billing.amount)}
          hint="cumul des factures"
          to="/factures"
        />
      </div>

      <p className="cockpit-section-label">Files à traiter</p>
      <div className="cockpit-queue-grid">
        <QueueCard
          domain="energie"
          category="Factures fournisseurs"
          title="Factures en anomalie"
          value={formatInt(billing.invalid)}
          badge={billing.inBpuGap > 0 ? `${formatInt(billing.inBpuGap)} en écart BPU` : undefined}
          badgeTone="danger"
          action="Traiter"
          to="/factures"
        />
        <QueueCard
          domain="energie"
          category="Factures fournisseurs"
          title="Factures à revoir"
          value={formatInt(billing.review)}
          badge="alertes non bloquantes"
          badgeTone="warn"
          action="Revoir"
          to="/factures"
        />
        <QueueCard
          domain="energie"
          category="Liaison finance"
          title="À transmettre à la finance"
          value={formatInt(billing.toExport)}
          badge={billing.toExport > 0 ? "prêtes" : undefined}
          badgeTone="ok"
          action="Transmettre"
          to="/factures"
        />
        <QueueCard
          domain="energie"
          category="Préconisations"
          title="Puissance à recalibrer"
          value={formatInt(perimeter.toRecalibrate)}
          badge="sous / sur-souscrits"
          badgeTone="warn"
          action="Analyser"
          to="/energie/preconisations"
        />
        <QueueCard
          domain="patrimoine"
          category="Rapprochements"
          title="Compteurs à rattacher"
          value={formatInt(perimeter.prms)}
          badge="vérifier les liaisons"
          badgeTone="info"
          action="Rapprocher"
          to="/patrimoine/rattachements"
        />
        <QueueCard
          domain="marches"
          category="CPE DALKIA"
          title="Suivi du marché de performance"
          value={formatInt(perimeter.cpeActive)}
          badge="sites actifs"
          badgeTone="neutral"
          action="Voir"
          to="/marches"
        />
      </div>
    </section>
  );
}
