import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchGrdfConsoStatus,
  fetchGrdfMonthly,
  fetchGrdfPces,
  startGrdfBackfill,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

const MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"];

function formatMwh(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} MWh`;
}

export function EnergieGazPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
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

  const collecteMutation = useMutation({
    mutationFn: () => startGrdfBackfill(token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["grdf-conso-status"] });
      queryClient.invalidateQueries({ queryKey: ["grdf-monthly"] });
    },
  });

  const pces = pcesQuery.data ?? [];
  const status = statusQuery.data;

  const pceKpis = useMemo(() => {
    const active = pces.filter((p) => p.etat_droit_acces === "Active");
    const collectable = active.filter((p) => p.perim_publiees);
    return { total: pces.length, active: active.length, collectable: collectable.length };
  }, [pces]);

  const isRunning = status?.status === "running";

  return (
    <div className="page">
      <header className="page-header">
        <h1>Gaz — GRDF ADICT</h1>
        <p className="muted-text">
          Consommations distributeur GRDF par PCE et suivi temporel.
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
          <span className="kpi-label">Collectables</span>
          <strong className="kpi-value">{pceKpis.collectable}</strong>
        </div>
      </section>

      {/* Collecte */}
      <section className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <button
            className="btn btn-primary"
            onClick={() => collecteMutation.mutate()}
            disabled={collecteMutation.isPending || isRunning}
          >
            Collecter les consommations
          </button>
          {status && (
            <span className="muted-text" style={{ marginLeft: "auto" }}>
              Collecte : <strong>{status.status}</strong>
              {status.pce_total > 0 && ` — ${status.pce_done}/${status.pce_total} PCE`}
              {status.rows_upserted > 0 && ` — ${status.rows_upserted} relevés`}
            </span>
          )}
        </div>
        {collecteMutation.isError && (
          <p className="error-text" style={{ marginTop: 8 }}>
            La collecte a échoué — vérifier que les credentials GRDF sont configurés.
          </p>
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
