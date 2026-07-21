import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SegmentControl } from "../../design-system";
import {
  fetchEnergieOverview,
  fetchFluidsClimate,
  fetchDjuMonthly,
  fetchFluidsElecObservedPrice,
  fetchGasPortfolio,
  fetchGasBudgetRevise,
} from "../../lib/api";
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

function formatEur(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} M€`;
  if (value >= 1_000) return `${(value / 1_000).toLocaleString("fr-FR", { maximumFractionDigits: 0 })} k€`;
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} €`;
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
  const { data: observedElecPrice } = useQuery({
    queryKey: ["fluids-elec-observed-price"],
    queryFn: () => fetchFluidsElecObservedPrice(token!),
    enabled: !!token,
    staleTime: 300_000,
  });

  const { data: gasPortfolio } = useQuery({
    queryKey: ["gas-portfolio"],
    queryFn: () => fetchGasPortfolio(token!),
    enabled: !!token,
    staleTime: 60_000,
  });

  const gasBudgetYear = Number(period);
  const { data: gasBudget } = useQuery({
    queryKey: ["gas-budget-revise", gasBudgetYear],
    queryFn: () => fetchGasBudgetRevise(token!, gasBudgetYear),
    enabled: !!token,
    staleTime: 60_000,
  });

  const djuOutlook = useMemo(() => {
    const byYear = new Map<number, { chauffe: number; froid: number; months: number }>();
    for (const p of djuMonthly ?? []) {
      const y = parseInt((p.month ?? "").slice(0, 4), 10);
      if (!Number.isFinite(y)) continue;
      const cur = byYear.get(y) ?? { chauffe: 0, froid: 0, months: 0 };
      cur.chauffe += p.dju_chauffe ?? 0;
      cur.froid += p.dju_froid ?? 0;
      cur.months += 1;
      byYear.set(y, cur);
    }
    const complete = Array.from(byYear.entries())
      .filter(([, v]) => v.months >= 12)
      .map(([y, v]) => ({ y, chauffe: v.chauffe, froid: v.froid }))
      .sort((a, b) => a.y - b.y);
    if (complete.length < 2) return null;
    const hist = complete; // tout l'historique (années complètes)
    const histMap = new Map(hist.map((r) => [r.y, r]));
    const fit = (get: (r: { y: number; chauffe: number; froid: number }) => number) => {
      const xs = hist.map((r) => r.y);
      const ys = hist.map(get);
      const n = xs.length;
      const mx = xs.reduce((a, b) => a + b, 0) / n;
      const my = ys.reduce((a, b) => a + b, 0) / n;
      let num = 0;
      let den = 0;
      for (let i = 0; i < n; i++) { num += (xs[i] - mx) * (ys[i] - my); den += (xs[i] - mx) ** 2; }
      const slope = den ? num / den : 0;
      const intercept = my - slope * mx;
      return (year: number) => Math.max(0, intercept + slope * year);
    };
    const fH = fit((r) => r.chauffe);
    const fC = fit((r) => r.froid);
    const lastHistYear = hist[hist.length - 1].y;
    const years = [...hist.map((r) => r.y), ...Array.from({ length: 10 }, (_u, i) => lastHistYear + i + 1)];
    const rows = years.map((yr) => {
      const h = histMap.get(yr);
      return {
        label: String(yr),
        chauffeHist: h ? Math.round(h.chauffe) : null,
        froidHist: h ? Math.round(h.froid) : null,
        chauffeProj: yr > lastHistYear ? Math.round(fH(yr)) : yr === lastHistYear && h ? Math.round(h.chauffe) : null,
        froidProj: yr > lastHistYear ? Math.round(fC(yr)) : yr === lastHistYear && h ? Math.round(h.froid) : null,
      };
    });
    const pct = (f: (y: number) => number) => { const a = f(lastHistYear); const b = f(lastHistYear + 10); return a > 0 ? ((b - a) / a) * 100 : null; };
    const total = (y: number) => fH(y) + fC(y);
    return { rows, heatingPct: pct(fH), coolingPct: pct(fC), histFrom: hist[0].y, histTo: lastHistYear, projTo: lastHistYear + 10, histCount: hist.length, totalNow: total(lastHistYear), total5: total(lastHistYear + 5), total10: total(lastHistYear + 10) };
  }, [djuMonthly]);

  const finance = useMemo(() => {
    const conso = overview?.kpis.annual_consumption_kwh ?? null;
    const priceNow = observedElecPrice?.current_eur_per_kwh_ttc ?? null;
    if (!conso || !djuOutlook || priceNow == null) return null;
    const thermoShare = climate?.thermal.thermosensitive_share_pct != null ? climate.thermal.thermosensitive_share_pct / 100 : 0.25;
    const ratio5 = djuOutlook.totalNow > 0 ? djuOutlook.total5 / djuOutlook.totalNow : 1;
    const ratio10 = djuOutlook.totalNow > 0 ? djuOutlook.total10 / djuOutlook.totalNow : 1;
    const consoAt = (ratio: number) => conso * (1 + thermoShare * (ratio - 1));
    const price5 = observedElecPrice?.projected_5y_eur_per_kwh_ttc ?? null;
    const price10 = observedElecPrice?.projected_10y_eur_per_kwh_ttc ?? null;
    return {
      now: conso * priceNow,
      y5: price5 == null ? null : consoAt(ratio5) * price5,
      y10: price10 == null ? null : consoAt(ratio10) * price10,
      priceNow, price5, price10,
      currentYear: observedElecPrice?.current_year ?? null,
      invoiceCount: observedElecPrice?.points.at(-1)?.invoice_count ?? 0,
    };
  }, [overview, djuOutlook, observedElecPrice, climate]);

  const elecKwh = overview?.kpis.annual_consumption_kwh ?? null;
  const elecPrms = overview?.kpis.total_prms ?? null;
  const elecCoveredPrms = overview?.kpis.annual_consumption_prms ?? null;
  const elecCoverage = elecPrms != null && elecCoveredPrms != null && elecPrms > 0
    ? Math.round((elecCoveredPrms / elecPrms) * 100)
    : null;
  const elecSurveiller = overview ? overview.kpis.sous_dimensionnes + overview.kpis.proche_seuil : null;
  const gasPceCount = gasPortfolio?.by_site.length ?? null;
  const gasLinkedCount = gasPortfolio?.by_site.filter((s) => s.linked).length ?? null;
  const gasCoverage = gasPceCount != null && gasLinkedCount != null && gasPceCount > 0
    ? Math.round((gasLinkedCount / gasPceCount) * 100)
    : null;
  const gasDerives = gasPortfolio
    ? (gasPortfolio.by_control.review ?? 0) + (gasPortfolio.by_control.invalid ?? 0)
    : null;

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head po2-fluid-head">
        <div>
          <span className="po2-eyebrow">Lecture climatique &amp; performance</span>
          <h1>Fluides &amp; consommations</h1>
          <p>Le climat (DJU) explique l'essentiel des consommations. On lit d'abord le contexte, puis on estime l'effet financier à partir du prix TTC observé sur les factures électricité.</p>
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
            <div className="po2-fluid-access__metric"><span>Couverture</span><strong title="Part des PRM contractuels dont la consommation a effectivement été collectée">{elecCoverage != null ? `${elecCoverage}%` : "—"}</strong></div>
          </div>
          <div className="po2-fluid-access__foot">
            <span style={{ fontSize: 11, opacity: 0.85 }}>{elecSurveiller != null ? `${elecSurveiller.toLocaleString("fr-FR")} à recalibrer` : "— à recalibrer"} · dérives —</span>
            <span className="po2-fluid-access__open">Ouvrir le détail →</span>
          </div>
        </Link>

        <Link to="/refonte-v1/fluides/gaz" className="po2-fluid-access po2-fluid-access--gaz">
          <div className="po2-fluid-access__top"><div className="po2-fluid-access__ic">G</div><div><b>Gaz</b><small>Distributeur GRDF - TotalEnergies</small></div></div>
          <div className="po2-fluid-access__metrics">
            <div className="po2-fluid-access__metric"><span>Observe</span><strong>{formatKwh(gasPortfolio?.total_kwh)}</strong></div>
            <div className="po2-fluid-access__metric"><span>PCE</span><strong>{gasPceCount != null ? gasPceCount.toLocaleString("fr-FR") : "-"}</strong></div>
            <div className="po2-fluid-access__metric"><span>Couverture</span><strong title="Part des PCE factures deja rattaches a un batiment">{gasCoverage != null ? `${gasCoverage}%` : "-"}</strong></div>
          </div>
          <div className="po2-fluid-access__foot">
            <span style={{ fontSize: 11, opacity: 0.85 }}>{gasDerives != null ? `${gasDerives.toLocaleString("fr-FR")} derive(s)` : "derives -"} - {gasLinkedCount != null && gasPceCount != null ? `${gasLinkedCount}/${gasPceCount} rattaches` : "calibrage a consolider"}</span>
            <span className="po2-fluid-access__open">Ouvrir le detail -></span>
          </div>
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

      <div className="po2-two-columns">
      {djuOutlook ? (
        <section className="po2-card">
          <header className="po2-card__header">
            <div>
              <span className="po2-eyebrow">Perspective climatique</span>
              <h2>Degrés-jours — {djuOutlook.histFrom}–{djuOutlook.histTo} &amp; projection +10 ans</h2>
            </div>
          </header>
          <div className="po2-card__body">
            <div className="po2-fluid-chips">
              <div className="po2-fluid-chip po2-fluid-chip--heat">
                <span>Chauffage</span>
                <b>{pctLabel(djuOutlook.heatingPct)}</b>
                <em>tendance projetée +10 ans</em>
              </div>
              <div className="po2-fluid-chip po2-fluid-chip--cool">
                <span>Froid / clim.</span>
                <b>{pctLabel(djuOutlook.coolingPct)}</b>
                <em>tendance projetée +10 ans</em>
              </div>
            </div>
            <div style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={djuOutlook.rows} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.22)" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} width={46} unit=" DJU" domain={["auto", "auto"]} allowDecimals={false} />
                  <Tooltip
                    formatter={(v: number, n: string) => [`${v.toLocaleString("fr-FR")} DJU`, n.startsWith("chauffe") ? "Chauffage" : "Froid / clim."]}
                    labelFormatter={(l) => `Année ${l}`}
                  />
                  <Legend />
                  <Line dataKey="chauffeHist" name="Chauffage" stroke="#3e6ea8" strokeWidth={3} dot connectNulls={false} />
                  <Line dataKey="chauffeProj" stroke="#3e6ea8" strokeWidth={2} strokeDasharray="6 5" dot={false} legendType="none" connectNulls />
                  <Line dataKey="froidHist" name="Froid / clim." stroke="#e39a2c" strokeWidth={3} dot connectNulls={false} />
                  <Line dataKey="froidProj" stroke="#e39a2c" strokeWidth={2} strokeDasharray="6 5" dot={false} legendType="none" connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="po2-muted-line" style={{ marginTop: 6, fontSize: 12 }}>Historique réel sur tout l'historique ({djuOutlook.histCount} années complètes, trait plein) et projection tendancielle +10 ans (tirets, régression linéaire sur l'ensemble de l'historique, base Météo-France) — repère indicatif, pas une prévision météo.</p>
          </div>
        </section>
      ) : null}

      <section className="po2-card">
        <header className="po2-card__header"><div><span className="po2-eyebrow">Impact financier - fluides</span><h2>Electricite observee - gaz atterrissage</h2></div></header>
        <div className="po2-card__body">
          {finance || gasBudget ? (
            <>
              <div style={{ display: "grid", gap: 14 }}>
                <div>
                  <b style={{ display: "block", marginBottom: 8 }}>Electricite</b>
                  {finance ? (
                    <div style={{ display: "grid", gap: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                        <span className="po2-muted-line">Base observee</span>
                        <strong style={{ fontSize: 20 }}>{formatEur(finance.now)}<small style={{ fontSize: 12, fontWeight: 400 }}> /an</small></strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                        <span className="po2-muted-line">Projection +5 ans</span>
                        <strong style={{ fontSize: 20, color: "#c2410c" }}>{formatEur(finance.y5)}<small style={{ fontSize: 12, fontWeight: 400 }}> /an</small></strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                        <span className="po2-muted-line">Projection +10 ans</span>
                        <strong style={{ fontSize: 20, color: "#b91c1c" }}>{formatEur(finance.y10)}<small style={{ fontSize: 12, fontWeight: 400 }}> /an</small></strong>
                      </div>
                    </div>
                  ) : <p className="po2-muted-line">Necessite des factures electricite avec TTC + kWh factures.</p>}
                </div>
                <div style={{ borderTop: "1px solid rgba(148,163,184,0.24)", paddingTop: 12 }}>
                  <b style={{ display: "block", marginBottom: 8 }}>Gaz TotalEnergies</b>
                  {gasBudget ? (
                    <div style={{ display: "grid", gap: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                        <span className="po2-muted-line">Atterrissage {gasBudgetYear}</span>
                        <strong style={{ fontSize: 20 }}>{formatEur(gasBudget.totals.atterrissage)}<small style={{ fontSize: 12, fontWeight: 400 }}> /an</small></strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                        <span className="po2-muted-line">Realise a date</span>
                        <strong style={{ fontSize: 18 }}>{formatEur(gasBudget.totals.realise)}</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                        <span className="po2-muted-line">Ecart / reference</span>
                        <strong style={{ fontSize: 18, color: gasBudget.totals.ecart_atterrissage_vs_prevision > 0 ? "#b91c1c" : "#15803d" }}>{formatEur(gasBudget.totals.ecart_atterrissage_vs_prevision)}</strong>
                      </div>
                    </div>
                  ) : <p className="po2-muted-line">Necessite les factures gaz TotalEnergies pour calculer l'atterrissage.</p>}
                </div>
              </div>
              <p className="po2-muted-line" style={{ marginTop: 12, fontSize: 12 }}>
                Electricite : prix observe = total TTC facture / kWh factures, toutes composantes incluses. Gaz : atterrissage annuel issu des factures TotalEnergies, avec reste projete par DJU quand disponible.
                <br />Prochaine etape : brancher la projection gaz +5/+10 ans sur une tendance prix gaz TTC ou sur la perspective BPU gaz.
              </p>
            </>
          ) : (
            <p className="po2-muted-line">Necessite des factures electricite ou gaz importees pour afficher l'impact financier.</p>
          )}
        </div>
      </section>
      </div>

    </div>
  );
}
