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

type KpiTone = "default" | "energy" | "warn" | "danger";

const KPI_TONE_CLASS: Record<KpiTone, string> = {
  default: "",
  energy: "dashboard-kpi-card--energy",
  warn: "dashboard-kpi-card--warn",
  danger: "dashboard-kpi-card--danger",
};

function KpiCard({
  label,
  value,
  hint,
  to,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: string;
  to: string;
  tone?: KpiTone;
}) {
  return (
    <Link to={to} className={`dashboard-kpi-card dashboard-kpi-card--link ${KPI_TONE_CLASS[tone]}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
    </Link>
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
    const toControl = invoices.filter(
      (i) => i.control_status === "invalid" || i.control_status === "review",
    ).length;
    const errors = invoices.reduce((sum, i) => sum + (i.control_errors_count ?? 0), 0);
    const exported = invoices.filter((i) => i.finance_exported_at).length;
    const amount = invoices.reduce((sum, i) => sum + (i.total_ttc ?? 0), 0);
    return { total: invoices.length, toControl, errors, exported, amount };
  }, [invoicesQuery.data]);

  const perimeter = useMemo(() => {
    const kpis = energieQuery.data?.kpis;
    const toRecalibrate = kpis
      ? (kpis.sous_dimensionnes ?? 0) + (kpis.sur_souscrits ?? 0)
      : null;
    const cpeActive = cpeQuery.data?.filter((s) => s.actif).length ?? null;
    return {
      sites: sitesQuery.data?.length ?? null,
      buildings: buildingsQuery.data?.length ?? null,
      prms: kpis?.total_prms ?? null,
      toRecalibrate,
      cpeActive,
    };
  }, [sitesQuery.data, buildingsQuery.data, energieQuery.data, cpeQuery.data]);

  return (
    <section className="panel stack-lg">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Tableau de bord</p>
          <h2>Pilotage du patrimoine et des dépenses énergie</h2>
          <p>
            {user
              ? `Bonjour ${user.prenom}. Voici l’état courant de ton périmètre et des contrôles à mener.`
              : "Connecte-toi pour accéder à ton périmètre."}
          </p>
        </div>
        <div className="form-actions">
          <Link className="primary-link" to="/energie/factures">
            Contrôler les factures
          </Link>
        </div>
      </div>

      <div className="section-block">
        <div className="section-heading">
          <h3>Factures fournisseurs</h3>
          <p>Contrôle contractuel (BPU Hérault Énergie) puis transmission au service finance.</p>
        </div>
        <div className="dashboard-kpi-grid">
          <KpiCard
            label="Factures importées"
            value={formatInt(billing.total)}
            to="/energie/factures"
          />
          <KpiCard
            label="À contrôler"
            value={formatInt(billing.toControl)}
            hint="anomalies ou à revoir"
            to="/energie/factures"
            tone="warn"
          />
          <KpiCard
            label="Erreurs de contrôle"
            value={formatInt(billing.errors)}
            hint="écarts bloquants détectés"
            to="/energie/factures"
            tone={billing.errors > 0 ? "danger" : "default"}
          />
          <KpiCard
            label="Transmises finance"
            value={`${formatInt(billing.exported)} / ${formatInt(billing.total)}`}
            to="/energie/factures"
            tone="energy"
          />
          <KpiCard
            label="Montant TTC importé"
            value={formatEur(billing.amount)}
            hint="cumul des factures"
            to="/energie/factures"
          />
        </div>
      </div>

      <div className="section-block">
        <div className="section-heading">
          <h3>Mon périmètre</h3>
          <p>Patrimoine, points de livraison et marché de performance énergétique.</p>
        </div>
        <div className="dashboard-kpi-grid">
          <KpiCard label="Sites" value={formatInt(perimeter.sites)} to="/buildings/list" />
          <KpiCard
            label="Bâtiments"
            value={formatInt(perimeter.buildings)}
            to="/buildings/list"
          />
          <KpiCard
            label="Points de livraison"
            value={formatInt(perimeter.prms)}
            hint="PRM électricité"
            to="/energie"
          />
          <KpiCard
            label="Puissance à recalibrer"
            value={formatInt(perimeter.toRecalibrate)}
            hint="sous-dimensionnés + sur-souscrits"
            to="/energie/preconisations"
            tone={perimeter.toRecalibrate && perimeter.toRecalibrate > 0 ? "warn" : "default"}
          />
          <KpiCard
            label="Sites CPE actifs"
            value={formatInt(perimeter.cpeActive)}
            hint="marché DALKIA"
            to="/cpe"
          />
        </div>
      </div>

      <div className="section-block">
        <div className="section-heading">
          <h3>Accès rapides</h3>
          <p>Les écrans les plus utilisés au quotidien.</p>
        </div>
        <div className="resource-list">
          <article className="resource-card">
            <div className="resource-card-header">
              <div>
                <h3>Factures fournisseurs</h3>
                <p>Importer, contrôler contre le BPU, décider et transmettre à la finance.</p>
              </div>
            </div>
            <div className="resource-card-actions">
              <Link className="secondary-link" to="/energie/factures">
                Ouvrir
              </Link>
            </div>
          </article>
          <article className="resource-card">
            <div className="resource-card-header">
              <div>
                <h3>CPE DALKIA</h3>
                <p>Suivi du marché de performance énergétique : cibles, intéressement, atterrissage.</p>
              </div>
            </div>
            <div className="resource-card-actions">
              <Link className="secondary-link" to="/cpe">
                Ouvrir
              </Link>
            </div>
          </article>
          <article className="resource-card">
            <div className="resource-card-header">
              <div>
                <h3>Sites et bâtiments</h3>
                <p>Consulter le patrimoine, ouvrir une fiche, rattacher les compteurs.</p>
              </div>
            </div>
            <div className="resource-card-actions">
              <Link className="secondary-link" to="/buildings/list">
                Ouvrir
              </Link>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
