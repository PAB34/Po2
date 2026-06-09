import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  enrichGrdfContractuel,
  fetchGrdfConsoStatus,
  fetchGrdfMonthly,
  fetchGrdfPces,
  fetchGrdfReconcileP1,
  startGrdfBackfill,
  startGrdfConsoSync,
  syncGrdfPces,
} from "../lib/api";
import type { GrdfP1ReconcileItem } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

const MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"];

const STATUT_LABEL: Record<string, string> = {
  ok: "Conforme",
  ecart: "Écart",
  blocked: "Réf. P1 absente",
};
const STATUT_CLASS: Record<string, string> = {
  ok: "badge-green",
  ecart: "badge-red",
  blocked: "badge-gray",
};

function formatMwh(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} MWh`;
}

function formatPct(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %`;
}

function formatEur(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} €`;
}

function reconcileBadge(item: GrdfP1ReconcileItem) {
  return (
    <span className={`badge ${STATUT_CLASS[item.statut] ?? "badge-gray"}`}>
      {STATUT_LABEL[item.statut] ?? item.statut}
    </span>
  );
}

export function EnergieGazPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [selectedPce, setSelectedPce] = useState<string>("");

  const pcesQuery = useQuery({
    queryKey: ["grdf-pces"],
    queryFn: () => fetchGrdfPces(token!),
    enabled: !!token,
  });

  const statusQuery = useQuery({
    queryKey: ["grdf-conso-status"],
    queryFn: () => fetchGrdfConsoStatus(token!),
    enabled: !!token,
    refetchInterval: (query) => (query.state.data?.status === "running" ? 4000 : false),
  });

  const monthlyQuery = useQuery({
    queryKey: ["grdf-monthly", selectedPce],
    queryFn: () => fetchGrdfMonthly(token!, selectedPce || undefined),
    enabled: !!token,
  });

  const reconcileQuery = useQuery({
    queryKey: ["grdf-reconcile-p1", year],
    queryFn: () => fetchGrdfReconcileP1(token!, year),
    enabled: !!token,
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["grdf-conso-status"] });
    queryClient.invalidateQueries({ queryKey: ["grdf-monthly"] });
    queryClient.invalidateQueries({ queryKey: ["grdf-reconcile-p1"] });
  };

  const syncPcesMutation = useMutation({
    mutationFn: () => syncGrdfPces(token!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["grdf-pces"] }),
  });
  const backfillMutation = useMutation({ mutationFn: () => startGrdfBackfill(token!), onSuccess: invalidateAll });
  const syncMutation = useMutation({ mutationFn: () => startGrdfConsoSync(token!), onSuccess: invalidateAll });
  const enrichMutation = useMutation({
    mutationFn: () => enrichGrdfContractuel(token!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["grdf-pces"] }),
  });

  const pces = pcesQuery.data ?? [];
  const status = statusQuery.data;
  const reconcile = reconcileQuery.data ?? [];

  const pceKpis = useMemo(() => {
    const active = pces.filter((p) => p.etat_droit_acces === "Active");
    const collectable = active.filter((p) => p.perim_publiees);
    return { total: pces.length, active: active.length, collectable: collectable.length };
  }, [pces]);

  const reconcileKpis = useMemo(() => {
    const ecarts = reconcile.filter((r) => r.statut === "ecart").length;
    const blocked = reconcile.filter((r) => r.statut === "blocked").length;
    const totalGrdf = reconcile.reduce((acc, r) => acc + (r.grdf_mwh_pcs || 0), 0);
    return { count: reconcile.length, ecarts, blocked, totalGrdf };
  }, [reconcile]);

  const yearOptions = useMemo(
    () => Array.from({ length: 6 }, (_, i) => currentYear - i),
    [currentYear],
  );

  const isRunning = status?.status === "running";
  const busy = backfillMutation.isPending || syncMutation.isPending || isRunning;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Gaz — GRDF ADICT</h1>
        <p className="muted-text">
          Consommations distributeur GRDF par PCE, suivi temporel et rapprochement avec le P1 GAZ DALKIA.
        </p>
      </header>

      {/* KPI référentiel */}
      <section className="card-grid" style={{ marginBottom: 16 }}>
        <div className="kpi-card">
          <span className="kpi-label">PCE référencés</span>
          <strong className="kpi-value">{pceKpis.total}</strong>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Droits actifs</span>
          <strong className="kpi-value">{pceKpis.active}</strong>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Collectables (périm. publiées)</span>
          <strong className="kpi-value">{pceKpis.collectable}</strong>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Conso GRDF {year}</span>
          <strong className="kpi-value">{formatMwh(reconcileKpis.totalGrdf)}</strong>
        </div>
      </section>

      {/* Actions de synchronisation */}
      <section className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <button className="btn" onClick={() => syncPcesMutation.mutate()} disabled={syncPcesMutation.isPending}>
            Resync référentiel (API)
          </button>
          <button className="btn btn-primary" onClick={() => backfillMutation.mutate()} disabled={busy}>
            Backfill 5 ans
          </button>
          <button className="btn" onClick={() => syncMutation.mutate()} disabled={busy}>
            Sync récente
          </button>
          <button className="btn" onClick={() => enrichMutation.mutate()} disabled={enrichMutation.isPending}>
            Enrichir contractuel/technique
          </button>
          {status && (
            <span className="muted-text" style={{ marginLeft: "auto" }}>
              Collecte : <strong>{status.status}</strong>
              {status.pce_total > 0 && ` — ${status.pce_done}/${status.pce_total} PCE`}
              {status.rows_upserted > 0 && ` — ${status.rows_upserted} relevés`}
            </span>
          )}
        </div>
        {(syncPcesMutation.isError || backfillMutation.isError || syncMutation.isError || enrichMutation.isError) && (
          <p className="error-text" style={{ marginTop: 8 }}>
            Une action a échoué — vérifier que les credentials GRDF sont configurés.
          </p>
        )}
        {syncPcesMutation.data && (
          <p className="muted-text" style={{ marginTop: 8 }}>
            Référentiel synchronisé : {syncPcesMutation.data.total_api} droits API
            ({syncPcesMutation.data.created} créés, {syncPcesMutation.data.updated} mis à jour).
          </p>
        )}
      </section>

      {/* Rapprochement P1 DALKIA */}
      <section className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Rapprochement conso GRDF ↔ P1 GAZ DALKIA</h2>
          <select value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {yearOptions.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        <p className="muted-text" style={{ marginBottom: 12 }}>
          {reconcileKpis.count} PCE comparés · {reconcileKpis.ecarts} écart(s) · {reconcileKpis.blocked} sans référence P1.
          Comparaison en MWh PCS (GRDF kWh/1000 vs quantité P1 contractuelle).
        </p>
        {reconcileQuery.isLoading ? (
          <p className="muted-text">Chargement…</p>
        ) : reconcile.length === 0 ? (
          <p className="muted-text">Aucune consommation GRDF collectée pour {year}.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>PCE</th>
                <th>Site</th>
                <th>Conso GRDF</th>
                <th>Quantité P1</th>
                <th>Écart</th>
                <th>Écart %</th>
                <th>P1 HT</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {reconcile.map((r) => (
                <tr key={r.id_pce}>
                  <td>{r.id_pce}</td>
                  <td>{r.nom_site ?? r.code_site ?? "-"}</td>
                  <td>{formatMwh(r.grdf_mwh_pcs)}</td>
                  <td>{formatMwh(r.dalkia_p1_qt_mwhpcs)}</td>
                  <td>{formatMwh(r.ecart_mwh)}</td>
                  <td>{formatPct(r.ecart_pct)}</td>
                  <td>{formatEur(r.p1_total_ht)}</td>
                  <td>{reconcileBadge(r)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Suivi temporel mensuel */}
      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Suivi temporel des consommations</h2>
          <select value={selectedPce} onChange={(e) => setSelectedPce(e.target.value)}>
            <option value="">Tous les PCE</option>
            {pces.map((p) => (
              <option key={p.id_pce} value={p.id_pce}>
                {p.nom_site ? `${p.nom_site} (${p.id_pce})` : p.id_pce}
              </option>
            ))}
          </select>
        </div>
        {monthlyQuery.isLoading ? (
          <p className="muted-text">Chargement…</p>
        ) : (monthlyQuery.data ?? []).length === 0 ? (
          <p className="muted-text">Aucun relevé mensuel disponible.</p>
        ) : (
          (monthlyQuery.data ?? []).map((series) => (
            <div key={series.id_pce} style={{ marginBottom: 20 }}>
              <h3 style={{ marginBottom: 8 }}>
                {series.nom_site ? `${series.nom_site} — ${series.id_pce}` : series.id_pce}
                <span className="muted-text" style={{ fontWeight: "normal", marginLeft: 8 }}>
                  {formatMwh(series.total_kwh / 1000)} cumulé
                </span>
              </h3>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Année</th>
                    {MONTHS.map((m) => (
                      <th key={m}>{m}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Array.from(new Set(series.points.map((p) => p.annee))).sort().map((y) => (
                    <tr key={y}>
                      <td><strong>{y}</strong></td>
                      {MONTHS.map((_, i) => {
                        const point = series.points.find((p) => p.annee === y && p.mois === i + 1);
                        return <td key={i}>{point ? point.mwh_pcs.toLocaleString("fr-FR", { maximumFractionDigits: 1 }) : "-"}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))
        )}
      </section>
    </div>
  );
}

export default EnergieGazPage;
