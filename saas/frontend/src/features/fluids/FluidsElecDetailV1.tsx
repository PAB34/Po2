import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { KpiCard, StatusBadge } from "../../design-system";
import { fetchEnergieOverview, fetchFluidsClimate } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

function formatKwh(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} GWh`;
  if (value >= 1_000) return `${(value / 1_000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} MWh`;
  return `${Math.round(value).toLocaleString("fr-FR")} kWh`;
}

function formatKva(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} kVA`;
}

function pct(v: number | null | undefined, d = 1): string {
  if (v == null) return "—";
  return `${v > 0 ? "+" : ""}${v.toLocaleString("fr-FR", { maximumFractionDigits: d })} %`;
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("fr-FR");
}

/** Dérives de démonstration : le module de détection sur courbe de charge (CDC) n'est
 *  pas encore branché. Marqué « aperçu » pour ne jamais faire passer un exemple pour un réel. */
const PREVIEW_DRIFTS = [
  { rank: 1, tone: "bad" as const, label: "Talon nocturne élevé", detail: "conso 0 h–5 h anormalement haute — veilles/équipements non coupés" },
  { rank: 2, tone: "warn" as const, label: "Consommation week-end", detail: "profil samedi/dimanche proche des jours ouvrés — occupation à vérifier" },
  { rank: 3, tone: "warn" as const, label: "Rupture de profil", detail: "changement de régime soudain vs historique — incident ou nouvel usage" },
];

export function FluidsElecDetailV1() {
  const { token } = useAuth();

  const { data: overview, isLoading } = useQuery({
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

  const k = overview?.kpis;
  const coverage = k && k.total_prms > 0 ? Math.round((k.annual_consumption_prms / k.total_prms) * 100) : null;
  const surveiller = k ? (k.sous_dimensionnes ?? 0) + (k.proche_seuil ?? 0) : null;
  const suppliers = overview?.supplier_distribution ?? [];
  const calib = overview?.calibration_distribution ?? [];
  const topConsumers = (overview?.top_consumers ?? []).slice(0, 10);
  const maxSupplierKva = Math.max(1, ...suppliers.map((s) => s.total_kva || 0));
  const maxCalib = Math.max(1, ...calib.map((c) => c.prm_count || 0));
  const maxConso = Math.max(1, ...topConsumers.map((t) => t.annual_consumption_kwh || 0));
  const th = climate?.thermal;

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head po2-fluid-head">
        <div>
          <span className="po2-eyebrow">Distributeur ENEDIS · Électricité</span>
          <h1>Détail électricité</h1>
          <p>
            Vue analyste : performance à climat égal, dérives de courbe de charge et calibrage des
            abonnements. <Link to="/refonte-v1/fluides">← Retour vue globale</Link>
          </p>
        </div>
        <div className="po2-fluid-source" style={{ margin: 0 }}>
          <span className="po2-fluid-dot" />
          <b>ENEDIS</b>
          <span>Conso {fmtDate(k?.annual_consumption_start)} → {fmtDate(k?.annual_consumption_end)}</span>
          {coverage != null ? <span className="cov">Couverture {coverage}%</span> : null}
        </div>
      </header>

      {isLoading && !overview ? <p className="po2-muted-line">Chargement des données ENEDIS…</p> : null}

      <div className="po2-kpi-grid">
        <KpiCard
          label="Consommation annuelle"
          value={formatKwh(k?.annual_consumption_kwh)}
          detail="ENEDIS · année glissante"
          trend={k ? `${k.annual_consumption_prms.toLocaleString("fr-FR")} PRM couverts` : undefined}
          tone="neutral"
        />
        <KpiCard
          label="Couverture données"
          value={coverage != null ? `${coverage}%` : "—"}
          detail={k ? `${k.annual_consumption_prms.toLocaleString("fr-FR")} / ${k.total_prms.toLocaleString("fr-FR")} PRM` : "PRM collectés"}
          tone="neutral"
        />
        <KpiCard
          label="Puissance souscrite"
          value={formatKva(k?.total_subscribed_kva)}
          detail={k ? `${k.total_prms.toLocaleString("fr-FR")} PRM` : undefined}
          tone="neutral"
        />
        <KpiCard
          label="Abonnements à surveiller"
          value={surveiller != null ? surveiller.toLocaleString("fr-FR") : "—"}
          detail={k ? `${k.sous_dimensionnes} sous-dim. · ${k.proche_seuil} proche seuil · ${k.sur_souscrits} sur-souscrits` : undefined}
          tone={surveiller && surveiller > 0 ? "warning" : "neutral"}
        />
      </div>

      <div className="po2-two-columns">
        {/* Performance énergétique (compact, à climat égal) */}
        <section className="po2-card">
          <header className="po2-card__header">
            <div>
              <span className="po2-eyebrow">Performance · corrigée du climat</span>
              <h2>Thermosensibilité</h2>
            </div>
          </header>
          <div className="po2-card__body">
            {th && th.reliable && th.sensitivity_kwh_per_dju != null ? (
              <>
                <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
                  <strong style={{ fontSize: 26 }}>{th.sensitivity_kwh_per_dju.toLocaleString("fr-FR")} kWh/DJU</strong>
                  <StatusBadge tone={th.sensitivity_delta_pct != null && th.sensitivity_delta_pct > 0 ? "bad" : "ok"}>
                    {pct(th.sensitivity_delta_pct)} vs 12 mois préc.
                  </StatusBadge>
                </div>
                <p className="po2-muted-line" style={{ marginTop: 6 }}>
                  {th.sensitivity_delta_pct != null && th.sensitivity_delta_pct > 0
                    ? "À climat égal, le parc consomme plus par degré : performance qui se dégrade."
                    : "Performance stable ou en amélioration à climat égal."}
                </p>
                <div style={{ display: "flex", gap: 24, marginTop: 12 }}>
                  <div>
                    <b style={{ fontSize: 18 }}>{th.thermosensitive_share_pct != null ? `${th.thermosensitive_share_pct.toLocaleString("fr-FR")} %` : "—"}</b>
                    <div className="po2-muted-line">part thermosensible</div>
                  </div>
                  <div>
                    <b style={{ fontSize: 18 }}>{th.base_load_share_pct != null ? `${th.base_load_share_pct.toLocaleString("fr-FR")} %` : "—"}</b>
                    <div className="po2-muted-line">talon non climatique</div>
                  </div>
                </div>
                <p className="po2-muted-line" style={{ marginTop: 10, fontSize: 12 }}>
                  Périmètre {th.scope} · {th.months_used} mois{th.r2 != null ? ` · R² ${th.r2.toLocaleString("fr-FR")}` : ""}.
                </p>
              </>
            ) : (
              <p className="po2-muted-line">Signature énergétique non fiable pour l'instant ({th?.months_used ?? 0} mois exploitables).</p>
            )}
          </div>
        </section>

        {/* Dérives de courbe de charge (aperçu) */}
        <section className="po2-card">
          <header className="po2-card__header">
            <div>
              <span className="po2-eyebrow">Signaux · courbe de charge</span>
              <h2>Dérives prioritaires</h2>
            </div>
            <StatusBadge tone="info">aperçu</StatusBadge>
          </header>
          <div className="po2-card__body">
            <div className="po2-decision-list">
              {PREVIEW_DRIFTS.map((d) => (
                <article key={d.rank} className="po2-decision-item">
                  <StatusBadge tone={d.tone}>{String(d.rank)}</StatusBadge>
                  <div><strong>{d.label}</strong><small>{d.detail}</small></div>
                </article>
              ))}
            </div>
            <p className="po2-muted-line" style={{ marginTop: 10, fontSize: 12 }}>
              Détection réelle en cours de branchement sur les courbes de charge 30 min (déjà collectées).
              Les items ci-dessus illustrent la mécanique — ce ne sont pas encore des signaux mesurés.
            </p>
          </div>
        </section>
      </div>

      <div className="po2-two-columns">
        {/* Calibrage des abonnements */}
        <section className="po2-card">
          <header className="po2-card__header">
            <div>
              <span className="po2-eyebrow">Contrats</span>
              <h2>Calibrage des abonnements</h2>
            </div>
          </header>
          <div className="po2-card__body">
            {calib.length === 0 ? (
              <p className="po2-muted-line">—</p>
            ) : (
              calib.map((c) => (
                <div key={c.status} style={{ marginBottom: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                    <span>{c.label}</span>
                    <b>{c.prm_count.toLocaleString("fr-FR")} PRM</b>
                  </div>
                  <div style={{ height: 6, background: "rgba(148,163,184,0.18)", borderRadius: 4, overflow: "hidden" }}>
                    <div style={{ width: `${Math.round((c.prm_count / maxCalib) * 100)}%`, height: "100%", background: "var(--po2-accent, #3e6ea8)" }} />
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Fournisseurs */}
        <section className="po2-card">
          <header className="po2-card__header">
            <div>
              <span className="po2-eyebrow">Marché</span>
              <h2>Fournisseurs (puissance)</h2>
            </div>
          </header>
          <div className="po2-card__body">
            {suppliers.length === 0 ? (
              <p className="po2-muted-line">—</p>
            ) : (
              suppliers.map((s) => (
                <div key={s.supplier} style={{ marginBottom: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                    <span>{s.supplier}</span>
                    <b>{formatKva(s.total_kva)} · {s.prm_count.toLocaleString("fr-FR")} PRM</b>
                  </div>
                  <div style={{ height: 6, background: "rgba(148,163,184,0.18)", borderRadius: 4, overflow: "hidden" }}>
                    <div style={{ width: `${Math.round((s.total_kva / maxSupplierKva) * 100)}%`, height: "100%", background: "#6366f1" }} />
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      {/* Top consommateurs */}
      <section className="po2-card">
        <header className="po2-card__header">
          <div>
            <span className="po2-eyebrow">Priorités</span>
            <h2>Sites les plus consommateurs</h2>
          </div>
          <Link className="po2-fluid-access__open" to="/energie">Vue complète (378 sites, référentiel, qualité) →</Link>
        </header>
        <div className="po2-card__body">
          {topConsumers.length === 0 ? (
            <p className="po2-muted-line">—</p>
          ) : (
            <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {topConsumers.map((t, i) => (
                <li key={t.usage_point_id} style={{ display: "grid", gridTemplateColumns: "24px 1fr auto", alignItems: "center", gap: 10, padding: "6px 0", borderBottom: "1px solid rgba(148,163,184,0.14)" }}>
                  <span className="po2-muted-line">{i + 1}</span>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.name || t.usage_point_id}</div>
                    <div style={{ height: 5, marginTop: 3, background: "rgba(148,163,184,0.16)", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{ width: `${Math.round((t.annual_consumption_kwh / maxConso) * 100)}%`, height: "100%", background: "#3e6ea8" }} />
                    </div>
                  </div>
                  <b style={{ whiteSpace: "nowrap" }}>{formatKwh(t.annual_consumption_kwh)}</b>
                </li>
              ))}
            </ol>
          )}
        </div>
      </section>
    </div>
  );
}
