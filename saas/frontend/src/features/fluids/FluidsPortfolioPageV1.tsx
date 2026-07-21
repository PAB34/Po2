import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { KpiCard, SegmentControl } from "../../design-system";
import { fetchEnergieOverview, fetchFluidsClimate, fetchDjuMonthly } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";
import { FluidsClimateSectionV1 } from "./FluidsClimateSectionV1";
import { FluidsAcquisitionDrawerV1 } from "./FluidsAcquisitionDrawerV1";

function pctLabel(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %`;
}

function formatKwh(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} GWh`;
  if (value >= 1_000) return `${(value / 1_000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} MWh`;
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} kWh`;
}

export function FluidsPortfolioPageV1() {
  const { token } = useAuth();
  const [period, setPeriod] = useState<"2026" | "2025">("2026");
  const [acqOpen, setAcqOpen] = useState(false);

  const { data: overview } = useQuery({
    queryKey: ["energie-overview"],
    queryFn: () => fetchEnergieOverview(token!),
    enabled: !!token,
    staleTime: 60_000,
  });

  const { data: climate } = useQuery({
    queryKey: ["fluids-climate"],
    queryFn: () => fetchFluidsClimate(token!),
    enabled: !!token,
    staleTime: 60_000,
  });

  const { data: djuMonthly } = useQuery({
    queryKey: ["dju-monthly"],
    queryFn: () => fetchDjuMonthly(token!),
    enabled: !!token,
    staleTime: 60_000,
  });

  const djuYears = useMemo(() => {
    const byYear = new Map<string, { chauffe: number; froid: number }>();
    for (const p of djuMonthly ?? []) {
      const y = (p.month ?? "").slice(0, 4);
      if (!/^\d{4}$/.test(y)) continue;
      const cur = byYear.get(y) ?? { chauffe: 0, froid: 0 };
      cur.chauffe += p.dju_chauffe ?? 0;
      cur.froid += p.dju_froid ?? 0;
      byYear.set(y, cur);
    }
    return Array.from(byYear.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .slice(-6)
      .map(([year, v]) => ({ year, chauffe: Math.round(v.chauffe), froid: Math.round(v.froid) }));
  }, [djuMonthly]);

  const elecKwh = overview?.kpis.annual_consumption_kwh ?? null;
  const elecPrms = overview?.kpis.total_prms ?? null;
  const elecCoveredPrms = overview?.kpis.annual_consumption_prms ?? null;
  const elecCoverage = elecPrms != null && elecCoveredPrms != null && elecPrms > 0
    ? Math.round((elecCoveredPrms / elecPrms) * 100)
    : null;

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head po2-fluid-head">
        <div>
          <span className="po2-eyebrow">Lecture climatique &amp; performance</span>
          <h1>Fluides &amp; consommations</h1>
          <p>Le climat (DJU) explique l'essentiel des consommations. On lit d'abord le contexte, puis on entre dans le détail d'un distributeur. Cette page ne projette pas d'impact financier.</p>
        </div>
        <SegmentControl
          value={period}
          options={[{ value: "2026", label: "2026" }, { value: "2025", label: "2025" }]}
          onChange={setPeriod}
        />
      </header>

      <div className="po2-fluid-source">
        <span className="po2-fluid-dot" />
        <b>Sources distributeurs</b>
        <span>ENEDIS · GRDF · SUEZ non raccordé · DJU Météo-France</span>
        {elecCoverage != null ? <span className="cov">Couverture élec {elecCoverage}%</span> : null}
        <button type="button" className="po2-src-manage" onClick={() => setAcqOpen(true)}>⟳ Gérer la collecte</button>
      </div>
      <FluidsAcquisitionDrawerV1 open={acqOpen} onClose={() => setAcqOpen(false)} />

      <div className="po2-fluid-lead">
        <h2>Entrer dans le détail par distributeur</h2>
        <span>Donnée réelle, dérives et surveillance des contrats propres à chaque fluide.</span>
      </div>

      <div className="po2-fluid-access-grid">
        <Link to="/refonte-v1/fluides/electricite" className="po2-fluid-access po2-fluid-access--elec">
          <div className="po2-fluid-access__top"><div className="po2-fluid-access__ic">ϟ</div><div><b>Électricité</b><small>Distributeur ENEDIS · EDF / ENGIE</small></div></div>
          <div className="po2-fluid-access__metrics">
            <div className="po2-fluid-access__metric"><span>Observé</span><strong>{formatKwh(elecKwh)}</strong></div>
            <div className="po2-fluid-access__metric"><span>PRM</span><strong>{elecPrms != null ? elecPrms.toLocaleString("fr-FR") : "—"}</strong></div>
            <div className="po2-fluid-access__metric"><span>Couverture</span><strong>{elecCoverage != null ? `${elecCoverage}%` : "—"}</strong></div>
          </div>
          <div className="po2-fluid-access__foot"><span className="po2-fluid-access__open">Ouvrir le détail →</span></div>
        </Link>

        <Link to="/refonte-v1/fluides/gaz" className="po2-fluid-access po2-fluid-access--gaz">
          <div className="po2-fluid-access__top"><div className="po2-fluid-access__ic">♨</div><div><b>Gaz</b><small>Distributeur GRDF · TotalEnergies</small></div></div>
          <div className="po2-fluid-access__metrics">
            <div className="po2-fluid-access__metric"><span>Distributeur</span><strong>GRDF</strong></div>
            <div className="po2-fluid-access__metric"><span>PCE</span><strong>51</strong></div>
            <div className="po2-fluid-access__metric"><span>Couverture</span><strong>—</strong></div>
          </div>
          <div className="po2-fluid-access__foot"><span className="po2-fluid-access__open">Ouvrir le détail →</span></div>
        </Link>

        <Link to="/refonte-v1/fluides/eau" className="po2-fluid-access po2-fluid-access--eau po2-fluid-access--soon">
          <div className="po2-fluid-access__top"><div className="po2-fluid-access__ic">◌</div><div><b>Eau</b><small>Distributeur SUEZ · titulaire à référencer</small></div></div>
          <div className="po2-fluid-access__metrics">
            <div className="po2-fluid-access__metric"><span>Observé</span><strong>—</strong></div>
            <div className="po2-fluid-access__metric"><span>Compteurs</span><strong>—</strong></div>
            <div className="po2-fluid-access__metric"><span>Couverture</span><strong>—</strong></div>
          </div>
          <div className="po2-fluid-access__foot"><span className="po2-fluid-access__open">Voir le chantier →</span><span className="po2-fluid-access__soon">À construire</span></div>
        </Link>
      </div>

      <FluidsClimateSectionV1 climate={climate} />

      {djuYears.length > 0 ? (
        <section className="po2-card">
          <header className="po2-card__header">
            <div>
              <span className="po2-eyebrow">Historique climatique</span>
              <h2>Degrés-jours annuels — perspective 5 ans+</h2>
            </div>
          </header>
          <div className="po2-card__body">
            <div style={{ height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={djuYears} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.22)" />
                  <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} width={48} />
                  <Tooltip
                    formatter={(v: number, n: string) => [`${v.toLocaleString("fr-FR")} DJU`, n === "chauffe" ? "Chauffage" : "Froid / clim."]}
                    labelFormatter={(l) => `Année ${l}`}
                  />
                  <Legend formatter={(v) => (v === "chauffe" ? "Chauffage" : "Froid / clim.")} />
                  <Bar dataKey="chauffe" fill="#3e6ea8" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="froid" fill="#e39a2c" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="po2-muted-line" style={{ marginTop: 6, fontSize: 12 }}>Cumul annuel des degrés-jours (base historique Météo-France) — rigueur climatique d'une année sur l'autre.</p>
          </div>
        </section>
      ) : null}

      <div className="po2-kpi-grid">
        <KpiCard label="Consommation électricité" value={formatKwh(elecKwh)} detail="ENEDIS · année glissante" trend={elecCoveredPrms != null ? `${elecCoveredPrms.toLocaleString("fr-FR")} PRM couverts` : undefined} tone="neutral" />
        <KpiCard label="Couverture données élec" value={elecCoverage != null ? `${elecCoverage}%` : "—"} detail="PRM avec consommation collectée" tone="neutral" />
        <KpiCard
          label="Rigueur climatique"
          value={climate ? pctLabel(climate.heating.delta_previous_pct) : "—"}
          detail={climate ? `DJU chauffage vs ${climate.previous_year}` : "DJU chauffage vs N-1"}
          tone={climate && climate.heating.delta_previous_pct != null && climate.heating.delta_previous_pct < 0 ? "good" : "neutral"}
        />
        <KpiCard
          label="Thermosensibilité"
          value={climate?.thermal.sensitivity_kwh_per_dju != null ? `${climate.thermal.sensitivity_kwh_per_dju.toLocaleString("fr-FR")} kWh/DJU` : "—"}
          detail={climate?.thermal.sensitivity_delta_pct != null ? `${pctLabel(climate.thermal.sensitivity_delta_pct)} vs 12 mois préc.` : "élec · pente conso/DJU (12 mois)"}
          tone={climate && climate.thermal.sensitivity_delta_pct != null && climate.thermal.sensitivity_delta_pct > 0 ? "warning" : "neutral"}
        />
      </div>
    </div>
  );
}
