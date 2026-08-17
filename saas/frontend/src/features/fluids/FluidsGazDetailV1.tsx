import { useMemo, useState, type CSSProperties } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { KpiCard, StatusBadge } from "../../design-system";
import {
  fetchDjuMonthly,
  fetchGrdfConsoStatus,
  fetchGrdfMonthly,
  fetchGrdfPces,
  fetchGrdfReconcileP1,
  startGrdfBackfill,
  type GrdfMonthlySeries,
  type GrdfP1ReconcileItem,
  type GrdfPce,
} from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

const MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"];
const YEAR_COLORS = ["#3e6ea8", "#f97316", "#16a34a", "#a855f7", "#06b6d4", "#eab308", "#ec4899", "#64748b"];
// En dessous de ce seuil de DJU, le ratio MWh/DJU explose (division par ~0) et n'a
// plus de sens : les mois d'été sont écartés du graphe de performance chauffage.
const DJU_MIN = 30;

function formatMwh(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1000) return `${(value / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} GWh`;
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} MWh`;
}
function fmtNum(value: number, digits = 1): string {
  return value.toLocaleString("fr-FR", { maximumFractionDigits: digits });
}
function fmtPct(value: number | null): string {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${fmtNum(value)} %`;
}

type PerimeterCompare = {
  currentYear: number;
  previousYear: number;
  monthsLabel: string;
  brutePct: number | null;
  constantPct: number | null;
  perimeterPct: number | null;
  pceCurrent: number;
  pcePrevious: number;
  pceCommon: number;
};

/**
 * Agrège les séries par PCE en indicateurs annuels + comparaison N vs N-1.
 *
 * Le parc GRDF n'est pas stable d'une année sur l'autre (consentements accordés au
 * fil de l'eau) : comparer les totaux bruts fait passer un élargissement de parc
 * pour une hausse de consommation. On calcule donc l'évolution **à périmètre
 * constant** (mêmes PCE, mêmes mois) et on isole l'effet périmètre.
 */
function analyseSeries(series: GrdfMonthlySeries[]) {
  const years = new Set<number>();
  // year -> mois -> { mwh, pces }
  const grid = new Map<number, Map<number, { mwh: number; pces: Set<string> }>>();
  const pcesByYear = new Map<number, Set<string>>();
  const totalsByYear = new Map<number, number>();

  for (const s of series) {
    for (const p of s.points) {
      years.add(p.annee);
      if (!grid.has(p.annee)) grid.set(p.annee, new Map());
      const monthMap = grid.get(p.annee)!;
      if (!monthMap.has(p.mois)) monthMap.set(p.mois, { mwh: 0, pces: new Set() });
      const cell = monthMap.get(p.mois)!;
      cell.mwh += p.mwh_pcs;
      totalsByYear.set(p.annee, (totalsByYear.get(p.annee) ?? 0) + p.mwh_pcs);
      // « PCE actif » = qui a réellement consommé ; un relevé à 0 ne compte pas
      // comme un site alimenté et fausserait le décompte de périmètre.
      if (p.mwh_pcs > 0) {
        cell.pces.add(s.id_pce);
        if (!pcesByYear.has(p.annee)) pcesByYear.set(p.annee, new Set());
        pcesByYear.get(p.annee)!.add(s.id_pce);
      }
    }
  }

  const sortedYears = [...years].sort((a, b) => a - b);

  // Graphe 1 — consommation mensuelle par année
  const consoRows = MONTHS.map((label, i) => {
    const row: Record<string, number | string> = { month: label };
    for (const y of sortedYears) {
      const cell = grid.get(y)?.get(i + 1);
      if (cell) row[String(y)] = Math.round(cell.mwh * 10) / 10;
    }
    return row;
  });

  // Graphe 2 — nombre de PCE actifs par mois et par année
  const perimeterRows = MONTHS.map((label, i) => {
    const row: Record<string, number | string> = { month: label };
    for (const y of sortedYears) {
      const cell = grid.get(y)?.get(i + 1);
      if (cell) row[String(y)] = cell.pces.size;
    }
    return row;
  });

  // Comparaison N vs N-1 : mêmes mois (l'année en cours est incomplète) et mêmes PCE
  let compare: PerimeterCompare | null = null;
  if (sortedYears.length >= 2) {
    const cy = sortedYears[sortedYears.length - 1];
    const py = sortedYears[sortedYears.length - 2];
    const cyMonths = new Set([...(grid.get(cy)?.keys() ?? [])]);
    const pyMonths = new Set([...(grid.get(py)?.keys() ?? [])]);
    const commonMonths = [...cyMonths].filter((m) => pyMonths.has(m)).sort((a, b) => a - b);
    const cyPces = pcesByYear.get(cy) ?? new Set<string>();
    const pyPces = pcesByYear.get(py) ?? new Set<string>();
    const commonPces = new Set([...cyPces].filter((p) => pyPces.has(p)));

    let bruteCy = 0;
    let brutePy = 0;
    let constCy = 0;
    let constPy = 0;
    for (const s of series) {
      const inCommon = commonPces.has(s.id_pce);
      for (const p of s.points) {
        if (!commonMonths.includes(p.mois)) continue;
        if (p.annee === cy) {
          bruteCy += p.mwh_pcs;
          if (inCommon) constCy += p.mwh_pcs;
        } else if (p.annee === py) {
          brutePy += p.mwh_pcs;
          if (inCommon) constPy += p.mwh_pcs;
        }
      }
    }
    const brutePct = brutePy > 0 ? ((bruteCy - brutePy) / brutePy) * 100 : null;
    const constantPct = constPy > 0 ? ((constCy - constPy) / constPy) * 100 : null;
    const monthsLabel =
      commonMonths.length === 12
        ? "année complète"
        : commonMonths.length > 0
          ? `${MONTHS[commonMonths[0] - 1]}→${MONTHS[commonMonths[commonMonths.length - 1] - 1]}`
          : "—";
    compare = {
      currentYear: cy,
      previousYear: py,
      monthsLabel,
      brutePct,
      constantPct,
      // Écart entre l'évolution brute et l'évolution réelle = ce qu'explique le
      // seul changement de parc.
      perimeterPct: brutePct != null && constantPct != null ? brutePct - constantPct : null,
      pceCurrent: cyPces.size,
      pcePrevious: pyPces.size,
      pceCommon: commonPces.size,
    };
  }

  return {
    years: sortedYears,
    consoRows,
    perimeterRows,
    compare,
    totalsByYear,
    pcesByYear,
    grid,
  };
}

/** Ratio MWh/DJU chauffage : année en cours vs moyenne des années précédentes. */
function buildDjuRows(
  grid: Map<number, Map<number, { mwh: number; pces: Set<string> }>>,
  years: number[],
  dju: { month: string; dju_chauffe: number }[] | undefined,
) {
  if (!dju || years.length === 0) return { rows: [], current: null as number | null, prevCount: 0 };
  const djuByYm = new Map<string, number>();
  for (const d of dju) djuByYm.set(d.month.slice(0, 7), d.dju_chauffe);

  const ratio = (y: number, m: number): number | null => {
    const cell = grid.get(y)?.get(m);
    if (!cell || cell.mwh <= 0) return null;
    const key = `${y}-${String(m).padStart(2, "0")}`;
    const d = djuByYm.get(key);
    if (d == null || d < DJU_MIN) return null;
    return cell.mwh / d;
  };

  const cy = years[years.length - 1];
  const prev = years.slice(0, -1);
  const rows = MONTHS.map((label, i) => {
    const m = i + 1;
    const cur = ratio(cy, m);
    const prevVals = prev.map((y) => ratio(y, m)).filter((v): v is number => v != null);
    const avg = prevVals.length ? prevVals.reduce((a, b) => a + b, 0) / prevVals.length : null;
    return { label, cur, avg };
  });
  return { rows, current: cy, prevCount: prev.length };
}

function reconcileTone(statut: string): "ok" | "warn" | "bad" | "info" | "neutral" {
  if (statut === "ok") return "ok";
  if (statut === "ecart") return "warn";
  return "neutral";
}
function reconcileLabel(statut: string): string {
  if (statut === "ok") return "Cohérent";
  if (statut === "ecart") return "Écart";
  if (statut === "blocked") return "Non rapprochable";
  return statut;
}

type PceSortKey = "nom_site" | "id_pce" | "nom_titulaire" | "tarif_acheminement" | "car_actuelle" | "frequence_releve" | "etat_droit_acces" | "conso";

/** Tableau complet des PCE (parité avec « Tous les compteurs » côté électricité). */
function PcesTable({ pces, consoByPce }: { pces: GrdfPce[]; consoByPce: Map<string, number> }) {
  const [query, setQuery] = useState("");
  const [etat, setEtat] = useState("all");
  const [sortKey, setSortKey] = useState<PceSortKey>("conso");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    let out = pces.filter((p) => {
      if (etat === "collectable" && !(p.etat_droit_acces === "Active" && p.perim_publiees)) return false;
      if (etat === "active" && p.etat_droit_acces !== "Active") return false;
      if (!q) return true;
      return [p.nom_site, p.id_pce, p.nom_titulaire, p.tarif_acheminement, p.frequence_releve, p.etat_droit_acces]
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
    const dir = sortDir === "asc" ? 1 : -1;
    out = [...out].sort((a, b) => {
      const va = sortKey === "conso" ? (consoByPce.get(a.id_pce) ?? 0) : a[sortKey];
      const vb = sortKey === "conso" ? (consoByPce.get(b.id_pce) ?? 0) : b[sortKey];
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
      return String(va).localeCompare(String(vb), "fr") * dir;
    });
    return out;
  }, [pces, query, etat, sortKey, sortDir, consoByPce]);

  const onSort = (k: PceSortKey) => {
    if (k === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(k);
      setSortDir(k === "conso" || k === "car_actuelle" ? "desc" : "asc");
    }
  };
  const caret = (k: PceSortKey) => (k === sortKey ? (sortDir === "asc" ? " ▲" : " ▼") : "");

  const columns: { key: PceSortKey; label: string; num?: boolean }[] = [
    { key: "nom_site", label: "Site" },
    { key: "id_pce", label: "PCE" },
    { key: "nom_titulaire", label: "Titulaire" },
    { key: "tarif_acheminement", label: "Tarif" },
    { key: "car_actuelle", label: "CAR", num: true },
    { key: "frequence_releve", label: "Relevé" },
    { key: "conso", label: "Conso cumulée", num: true },
    { key: "etat_droit_acces", label: "Droit" },
  ];

  const th: CSSProperties = { textAlign: "left", padding: "6px 8px", cursor: "pointer", whiteSpace: "nowrap", position: "sticky", top: 0, background: "var(--po2-surface, #0f172a1a)", userSelect: "none" };
  const td: CSSProperties = { padding: "5px 8px", borderBottom: "1px solid rgba(148,163,184,0.14)", whiteSpace: "nowrap" };

  return (
    <section className="po2-card">
      <header className="po2-card__header">
        <div>
          <span className="po2-eyebrow">Référentiel</span>
          <h2>Tous les PCE</h2>
        </div>
      </header>
      <div className="po2-card__body">
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 10, width: "100%" }}>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher (site, PCE, titulaire…)"
            style={{ flex: "0 1 340px", minWidth: 200, padding: "7px 10px", borderRadius: 8, border: "1px solid #d1d5db" }}
          />
          <select value={etat} onChange={(e) => setEtat(e.target.value)} style={{ flex: "0 0 auto", padding: "7px 10px", borderRadius: 8, border: "1px solid #d1d5db" }}>
            <option value="all">Tous les PCE</option>
            <option value="active">Droit actif</option>
            <option value="collectable">Collectables</option>
          </select>
          <span className="po2-muted-line" style={{ marginLeft: "auto" }}>{rows.length.toLocaleString("fr-FR")} résultats</span>
        </div>
        <div style={{ overflowX: "auto", maxHeight: 560, overflowY: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c.key} style={{ ...th, textAlign: c.num ? "right" : "left" }} onClick={() => onSort(c.key)}>
                    {c.label}{caret(c.key)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((p) => {
                const conso = consoByPce.get(p.id_pce);
                return (
                  <tr key={p.id_pce}>
                    <td style={{ ...td, fontWeight: 600 }}>{p.nom_site || "—"}</td>
                    <td style={{ ...td, fontFamily: "monospace" }}>{p.id_pce}</td>
                    <td style={td}>{p.nom_titulaire || "—"}</td>
                    <td style={td}>{p.tarif_acheminement || "—"}</td>
                    <td style={{ ...td, textAlign: "right" }}>{p.car_actuelle != null ? `${p.car_actuelle.toLocaleString("fr-FR")} kWh` : "—"}</td>
                    <td style={td}>{p.frequence_releve || "—"}</td>
                    <td style={{ ...td, textAlign: "right" }}>{conso ? formatMwh(conso / 1000) : "—"}</td>
                    <td style={td}>
                      {p.etat_droit_acces ? (
                        <StatusBadge tone={p.etat_droit_acces === "Active" ? (p.perim_publiees ? "ok" : "info") : "neutral"}>
                          {p.etat_droit_acces === "Active" && !p.perim_publiees ? "Actif (sans conso)" : p.etat_droit_acces}
                        </StatusBadge>
                      ) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

export function FluidsGazDetailV1() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  const { data: pces = [], isLoading: pcesLoading } = useQuery({
    queryKey: ["grdf-pces"],
    queryFn: () => fetchGrdfPces(token!),
    enabled: !!token,
    staleTime: 60_000,
  });
  const { data: series = [] } = useQuery({
    queryKey: ["grdf-monthly", "__all__"],
    queryFn: () => fetchGrdfMonthly(token!),
    enabled: !!token,
    staleTime: 60_000,
  });
  const { data: dju } = useQuery({
    queryKey: ["dju-monthly"],
    queryFn: () => fetchDjuMonthly(token!),
    enabled: !!token,
    staleTime: 300_000,
  });
  const { data: status } = useQuery({
    queryKey: ["grdf-conso-status"],
    queryFn: () => fetchGrdfConsoStatus(token!),
    enabled: !!token,
    refetchInterval: (query) => (query.state.data?.status === "running" ? 4000 : false),
  });

  const collecte = useMutation({
    mutationFn: () => startGrdfBackfill(token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["grdf-conso-status"] });
      queryClient.invalidateQueries({ queryKey: ["grdf-monthly"] });
    },
  });

  const analyse = useMemo(() => analyseSeries(series), [series]);
  const djuChart = useMemo(() => buildDjuRows(analyse.grid, analyse.years, dju), [analyse, dju]);
  const consoByPce = useMemo(() => {
    const m = new Map<string, number>();
    for (const s of series) m.set(s.id_pce, s.total_kwh);
    return m;
  }, [series]);

  const availableYears = useMemo(() => [...analyse.years].sort((a, b) => b - a), [analyse.years]);
  const [reconcileYear, setReconcileYear] = useState<number | null>(null);
  const effectiveYear = reconcileYear ?? availableYears[0] ?? new Date().getFullYear();
  const { data: reconcile = [] } = useQuery({
    queryKey: ["grdf-reconcile-p1", effectiveYear],
    queryFn: () => fetchGrdfReconcileP1(token!, effectiveYear),
    enabled: !!token && availableYears.length > 0,
    staleTime: 60_000,
  });

  const isRunning = status?.status === "running";
  const compare = analyse.compare;
  const currentYear = availableYears[0] ?? null;
  const collectablePces = pces.filter((p) => p.etat_droit_acces === "Active" && p.perim_publiees).length;
  const pcesWithData = consoByPce.size;
  const coverage = collectablePces > 0 ? Math.round((pcesWithData / collectablePces) * 100) : null;
  const currentYearTotal = currentYear != null ? analyse.totalsByYear.get(currentYear) ?? 0 : 0;
  const ecartsP1 = reconcile.filter((r) => r.statut === "ecart").length;

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head po2-fluid-head">
        <div>
          <span className="po2-eyebrow">Distributeur GRDF · Gaz</span>
          <h1>Détail gaz</h1>
          <p><Link to="/refonte-v1/fluides">← Retour vue globale</Link></p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
          <div className="po2-fluid-source" style={{ margin: 0 }}>
            <span className="po2-fluid-dot" />
            <b>GRDF ADICT</b>
            <span>{pcesWithData} PCE collectés</span>
          </div>
          <button
            type="button"
            className="po2-button po2-button--ghost"
            onClick={() => collecte.mutate()}
            disabled={collecte.isPending || isRunning}
          >
            {isRunning
              ? `Collecte… ${status && status.pce_total > 0 ? `${status.pce_done}/${status.pce_total}` : ""}`
              : "Relancer la collecte"}
          </button>
        </div>
      </header>

      {pcesLoading && pces.length === 0 ? <p className="po2-muted-line">Chargement des données GRDF…</p> : null}

      {/* KPI */}
      <div className="po2-kpi-grid">
        <KpiCard
          label="PCE contractuels"
          value={pces.length.toLocaleString("fr-FR")}
          detail={`${collectablePces.toLocaleString("fr-FR")} collectables · ${pcesWithData} avec conso`}
          tone="neutral"
        />
        <KpiCard
          label={`Conso ${currentYear ?? ""}`}
          value={formatMwh(currentYearTotal)}
          detail={compare ? `${compare.monthsLabel} — parc ${compare.pceCurrent} PCE actifs` : undefined}
          tone="good"
        />
        <KpiCard
          label="Couverture collecte"
          value={coverage != null ? `${coverage}%` : "—"}
          detail={`${pcesWithData} / ${collectablePces} PCE collectables`}
          tone="neutral"
        />
        <KpiCard
          label="Évolution à périmètre constant"
          value={compare ? fmtPct(compare.constantPct) : "—"}
          detail={compare ? `${compare.pceCommon} PCE communs ${compare.previousYear}↔${compare.currentYear} · ${compare.monthsLabel}` : undefined}
          tone={compare?.constantPct != null ? (compare.constantPct > 0 ? "warning" : "good") : "neutral"}
        />
        <KpiCard
          label="Effet périmètre"
          value={compare ? fmtPct(compare.perimeterPct) : "—"}
          detail={compare ? `${compare.pcePrevious} → ${compare.pceCurrent} PCE actifs (brut ${fmtPct(compare.brutePct)})` : undefined}
          tone="info"
        />
        <KpiCard
          label="Écarts P1 DALKIA"
          value={reconcile.length > 0 ? ecartsP1.toLocaleString("fr-FR") : "—"}
          detail={reconcile.length > 0 ? `sur ${reconcile.length} PCE rapprochés (${effectiveYear})` : undefined}
          tone={ecartsP1 > 0 ? "warning" : "neutral"}
        />
      </div>

      {/* Lecture de l'évolution : brut vs périmètre constant */}
      {compare && compare.brutePct != null && compare.constantPct != null ? (
        <section className="po2-card">
          <header className="po2-card__header">
            <div>
              <span className="po2-eyebrow">Lecture</span>
              <h2>{compare.previousYear} → {compare.currentYear} : ce qui explique l'écart</h2>
            </div>
            <StatusBadge tone={compare.constantPct > 0 ? "warn" : "ok"}>
              {compare.constantPct > 0 ? "hausse réelle" : "baisse réelle"}
            </StatusBadge>
          </header>
          <div className="po2-card__body">
            <div className="po2-decision-list">
              <article className="po2-decision-item">
                <StatusBadge tone="neutral">1</StatusBadge>
                <div>
                  <strong>Évolution brute : {fmtPct(compare.brutePct)}</strong>
                  <small>Tous PCE confondus, sur {compare.monthsLabel} — mélange l'évolution réelle et le changement de parc.</small>
                </div>
              </article>
              <article className="po2-decision-item">
                <StatusBadge tone="info">2</StatusBadge>
                <div>
                  <strong>Effet périmètre : {fmtPct(compare.perimeterPct)}</strong>
                  <small>
                    Le parc collecté passe de {compare.pcePrevious} à {compare.pceCurrent} PCE actifs
                    ({compare.pceCommon} présents les deux années). Cette part de l'écart ne traduit aucune
                    variation de consommation des sites.
                  </small>
                </div>
              </article>
              <article className="po2-decision-item">
                <StatusBadge tone={compare.constantPct > 0 ? "warn" : "ok"}>3</StatusBadge>
                <div>
                  <strong>Évolution réelle : {fmtPct(compare.constantPct)}</strong>
                  <small>À périmètre constant ({compare.pceCommon} PCE communs) et sur les mêmes mois — c'est le chiffre à retenir.</small>
                </div>
              </article>
            </div>
          </div>
        </section>
      ) : null}

      {/* Graphes */}
      <div className="po2-two-columns" style={{ gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
        <section className="po2-card" style={{ gridColumn: "1 / -1" }}>
          <header className="po2-card__header">
            <div>
              <span className="po2-eyebrow">Consommations</span>
              <h2>Consommation mensuelle par année</h2>
            </div>
          </header>
          <div className="po2-card__body">
            {analyse.years.length === 0 ? (
              <p className="po2-muted-line">Aucun relevé disponible — lancer une collecte.</p>
            ) : (
              <>
                <div style={{ height: 260 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analyse.consoRows} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.22)" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} width={54} unit=" MWh" />
                      <Tooltip formatter={(v: number, n: string) => [`${fmtNum(v)} MWh`, `Année ${n}`]} labelFormatter={(l) => `Mois : ${l}`} />
                      <Legend formatter={(v) => `Année ${v}`} />
                      {analyse.years.map((y, i) => (
                        <Bar key={y} dataKey={String(y)} fill={YEAR_COLORS[i % YEAR_COLORS.length]} maxBarSize={22} />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="po2-muted-line" style={{ fontSize: 12 }}>
                  Consommation du parc en MWh PCS. À lire avec le graphe de périmètre : le parc collecté n'est pas identique d'une année à l'autre.
                </p>
              </>
            )}
          </div>
        </section>

        {/* Graphe périmètre — répond au biais de comparaison */}
        <section className="po2-card">
          <header className="po2-card__header">
            <div>
              <span className="po2-eyebrow">Périmètre</span>
              <h2>PCE actifs par mois</h2>
            </div>
          </header>
          <div className="po2-card__body">
            {analyse.years.length === 0 ? (
              <p className="po2-muted-line">—</p>
            ) : (
              <>
                <div style={{ height: 240 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={analyse.perimeterRows} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.22)" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} width={40} allowDecimals={false} unit=" PCE" />
                      <Tooltip formatter={(v: number, n: string) => [`${v} PCE`, `Année ${n}`]} labelFormatter={(l) => `Mois : ${l}`} />
                      <Legend formatter={(v) => `Année ${v}`} />
                      {analyse.years.map((y, i) => (
                        <Line key={y} dataKey={String(y)} stroke={YEAR_COLORS[i % YEAR_COLORS.length]} strokeWidth={2} dot={{ r: 2 }} connectNulls />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <p className="po2-muted-line" style={{ fontSize: 12 }}>
                  Nombre de PCE ayant réellement consommé chaque mois. Une marche sur cette courbe explique
                  mécaniquement une hausse/baisse du graphe de consommation, sans changement sur les sites.
                </p>
              </>
            )}
          </div>
        </section>

        {/* Performance chauffage — équivalent gaz du kWh/DJU électricité */}
        <section className="po2-card">
          <header className="po2-card__header">
            <div>
              <span className="po2-eyebrow">Performance</span>
              <h2>Performance chauffage — MWh/DJU</h2>
            </div>
          </header>
          <div className="po2-card__body">
            {djuChart.rows.filter((r) => r.cur != null || r.avg != null).length === 0 ? (
              <p className="po2-muted-line">Données DJU ou consommations insuffisantes pour calculer un ratio.</p>
            ) : (
              <>
                <div style={{ height: 240 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={djuChart.rows} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.22)" />
                      <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} width={58} unit=" MWh/DJU" />
                      <Tooltip
                        formatter={(v: number, n: string) => [`${fmtNum(v, 3)} MWh/DJU`, n === "cur" ? `Année ${djuChart.current}` : "Moyenne années préc."]}
                        labelFormatter={(l) => `Mois : ${l}`}
                      />
                      <Line dataKey="avg" name="avg" stroke="#94a3b8" strokeWidth={2} strokeDasharray="6 5" dot={{ r: 3 }} connectNulls />
                      <Line dataKey="cur" name="cur" stroke="#3e6ea8" strokeWidth={3} dot={{ r: 4 }} connectNulls />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <p className="po2-muted-line" style={{ fontSize: 12 }}>
                  Consommation corrigée du climat : {djuChart.current} (trait plein) vs moyenne des {djuChart.prevCount} années
                  précédentes (tirets). Mois sous {DJU_MIN} DJU écartés (ratio non significatif hors saison de chauffe).
                </p>
              </>
            )}
          </div>
        </section>
      </div>

      {/* Rapprochement P1 DALKIA */}
      <section className="po2-card">
        <header className="po2-card__header">
          <div>
            <span className="po2-eyebrow">Marché CPE</span>
            <h2>Rapprochement P1 gaz DALKIA</h2>
          </div>
          {availableYears.length > 0 ? (
            <select
              value={effectiveYear}
              onChange={(e) => setReconcileYear(Number(e.target.value))}
              style={{ padding: "6px 10px", borderRadius: 8, border: "1px solid #d1d5db" }}
            >
              {availableYears.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          ) : null}
        </header>
        <div className="po2-card__body" style={{ overflowX: "auto" }}>
          {reconcile.length === 0 ? (
            <p className="po2-muted-line">Aucun rapprochement disponible pour {effectiveYear}.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.2)" }}>
                  <th style={{ textAlign: "left", padding: "4px 6px" }}>Site / PCE</th>
                  <th style={{ textAlign: "right", padding: "4px 6px" }}>GRDF</th>
                  <th style={{ textAlign: "right", padding: "4px 6px" }}>P1 DALKIA</th>
                  <th style={{ textAlign: "right", padding: "4px 6px" }}>Écart</th>
                  <th style={{ textAlign: "left", padding: "4px 6px" }}>Statut</th>
                </tr>
              </thead>
              <tbody>
                {reconcile.map((item: GrdfP1ReconcileItem) => (
                  <tr key={item.id_pce} style={{ borderBottom: "1px solid rgba(148,163,184,0.12)" }}>
                    <td style={{ padding: "4px 6px" }}>
                      <strong>{item.nom_site || item.code_site || "—"}</strong>{" "}
                      <span className="po2-muted-line" style={{ fontFamily: "monospace", fontSize: 11 }}>{item.id_pce}</span>
                    </td>
                    <td style={{ textAlign: "right", padding: "4px 6px" }}>{fmtNum(item.grdf_mwh_pcs)} MWh</td>
                    <td style={{ textAlign: "right", padding: "4px 6px" }}>
                      {item.dalkia_p1_qt_mwhpcs != null ? `${fmtNum(item.dalkia_p1_qt_mwhpcs)} MWh` : "—"}
                    </td>
                    <td style={{ textAlign: "right", padding: "4px 6px", fontWeight: 600, color: item.ecart_pct != null && Math.abs(item.ecart_pct) > 5 ? "#c2410c" : undefined }}>
                      {fmtPct(item.ecart_pct)}
                    </td>
                    <td style={{ padding: "4px 6px" }}>
                      <StatusBadge tone={reconcileTone(item.statut)}>{reconcileLabel(item.statut)}</StatusBadge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <PcesTable pces={pces} consoByPce={consoByPce} />
    </div>
  );
}
