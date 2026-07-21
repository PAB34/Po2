import { useMemo, useState, type CSSProperties } from "react";
import { Link } from "react-router-dom";
import { KpiCard, StatusBadge } from "../../design-system";
import { fetchEnergieOverview, type PrmListItem } from "../../lib/api";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../providers/AuthProvider";

function formatKwh(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} GWh`;
  if (value >= 1_000) return `${(value / 1_000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} MWh`;
  return `${Math.round(value).toLocaleString("fr-FR")} kWh`;
}
function formatKva(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} kVA`;
}
function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("fr-FR");
}
function shortSupplier(s: string | null | undefined): string {
  if (!s) return "—";
  if (s.toUpperCase().includes("FRANCE")) return "EDF";
  if (s.toUpperCase().includes("ENGIE")) return "ENGIE";
  return s;
}

const CALIB_LABEL: Record<string, string> = {
  sous_dimensionne: "Sous-dimensionné",
  proche_seuil: "Proche du seuil",
  bien_calibre: "Bien calibré",
  sur_souscrit: "Sur-souscrit",
};
const CALIB_TONE: Record<string, "ok" | "warn" | "bad" | "info" | "neutral"> = {
  sous_dimensionne: "bad",
  proche_seuil: "warn",
  bien_calibre: "ok",
  sur_souscrit: "info",
};
const CALIB_ORDER = ["sous_dimensionne", "proche_seuil", "bien_calibre", "sur_souscrit"];

function etatTone(s: string | null | undefined): "ok" | "warn" | "bad" | "neutral" {
  if (!s) return "neutral";
  const l = s.toLowerCase();
  if (l.includes("non") || l.includes("coup")) return l.includes("coup") ? "neutral" : "bad";
  if (l.includes("limit")) return "warn";
  if (l.includes("aliment")) return "ok";
  return "neutral";
}

const PREVIEW_DRIFTS = [
  { rank: 1, tone: "bad" as const, label: "Talon nocturne élevé", detail: "conso 0 h–5 h anormalement haute — veilles/équipements non coupés" },
  { rank: 2, tone: "warn" as const, label: "Consommation week-end", detail: "profil samedi/dimanche proche des jours ouvrés — occupation à vérifier" },
  { rank: 3, tone: "warn" as const, label: "Rupture de profil", detail: "changement de régime soudain vs historique — incident ou nouvel usage" },
];

type SortKey = "name" | "usage_point_id" | "address" | "contractor" | "subscribed_power_kva" | "peak_kva_3y" | "calibration_status" | "connection_state" | "services_level";

// ---------------------------------------------------------------------------
// Tableau complet des compteurs (tri + recherche + filtre calibrage)
// ---------------------------------------------------------------------------
function MetersTable({ prms }: { prms: PrmListItem[] }) {
  const [query, setQuery] = useState("");
  const [calib, setCalib] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    let out = prms.filter((p) => {
      if (calib !== "all" && (p.calibration_status ?? "") !== calib) return false;
      if (!q) return true;
      const hay = [
        p.name, p.usage_point_id, p.address, shortSupplier(p.contractor),
        p.subscribed_power_kva != null ? `${p.subscribed_power_kva} kva` : "",
        p.peak_kva_3y != null ? `${p.peak_kva_3y} kva` : "",
        p.calibration_status ? CALIB_LABEL[p.calibration_status] ?? p.calibration_status : "",
        p.connection_state, p.services_level,
      ].join(" ").toLowerCase();
      return hay.includes(q);
    });
    const dir = sortDir === "asc" ? 1 : -1;
    out = [...out].sort((a, b) => {
      const va = a[sortKey];
      const vb = b[sortKey];
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
      return String(va).localeCompare(String(vb), "fr") * dir;
    });
    return out;
  }, [prms, query, calib, sortKey, sortDir]);

  const onSort = (k: SortKey) => {
    if (k === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir("asc"); }
  };
  const caret = (k: SortKey) => (k === sortKey ? (sortDir === "asc" ? " ▲" : " ▼") : "");

  const columns: { key: SortKey; label: string; num?: boolean }[] = [
    { key: "name", label: "Nom" },
    { key: "usage_point_id", label: "PRM" },
    { key: "address", label: "Adresse" },
    { key: "contractor", label: "Fournisseur" },
    { key: "subscribed_power_kva", label: "Souscrit", num: true },
    { key: "peak_kva_3y", label: "Pic 3 ans", num: true },
    { key: "calibration_status", label: "Calibrage" },
    { key: "connection_state", label: "État" },
    { key: "services_level", label: "Communicant" },
  ];

  const th: CSSProperties = { textAlign: "left", padding: "6px 8px", cursor: "pointer", whiteSpace: "nowrap", position: "sticky", top: 0, background: "var(--po2-surface, #0f172a1a)", userSelect: "none" };
  const td: CSSProperties = { padding: "5px 8px", borderBottom: "1px solid rgba(148,163,184,0.14)", whiteSpace: "nowrap" };

  return (
    <section className="po2-card">
      <header className="po2-card__header">
        <div>
          <span className="po2-eyebrow">Référentiel</span>
          <h2>Tous les compteurs</h2>
        </div>
      </header>
      <div className="po2-card__body">
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 10, width: "100%" }}>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher (toutes colonnes)…"
            style={{ flex: "0 1 340px", minWidth: 200, padding: "7px 10px", borderRadius: 8, border: "1px solid #d1d5db" }}
          />
          <select value={calib} onChange={(e) => setCalib(e.target.value)} style={{ flex: "0 0 auto", padding: "7px 10px", borderRadius: 8, border: "1px solid #d1d5db" }}>
            <option value="all">Tous calibrages</option>
            <option value="sous_dimensionne">Sous-dimensionnés</option>
            <option value="proche_seuil">Proches du seuil</option>
            <option value="bien_calibre">Bien calibrés</option>
            <option value="sur_souscrit">Sur-souscrits</option>
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
              {rows.map((p) => (
                <tr key={p.usage_point_id}>
                  <td style={{ ...td, fontWeight: 600 }}>{p.name || "—"}</td>
                  <td style={{ ...td, fontFamily: "monospace" }}>{p.usage_point_id}</td>
                  <td style={td}>{p.address || "—"}</td>
                  <td style={td}>{shortSupplier(p.contractor)}</td>
                  <td style={{ ...td, textAlign: "right" }}>{p.subscribed_power_kva != null ? `${p.subscribed_power_kva} kVA` : "—"}</td>
                  <td style={{ ...td, textAlign: "right" }}>{p.peak_kva_3y != null ? `${p.peak_kva_3y} kVA` : "—"}</td>
                  <td style={td}>{p.calibration_status ? <StatusBadge tone={CALIB_TONE[p.calibration_status] ?? "neutral"}>{CALIB_LABEL[p.calibration_status] ?? p.calibration_status}</StatusBadge> : "—"}</td>
                  <td style={td}>{p.connection_state ? <StatusBadge tone={etatTone(p.connection_state)}>{p.connection_state}</StatusBadge> : "—"}</td>
                  <td style={td}>{p.services_level ? <StatusBadge tone={p.services_level.toLowerCase().includes("non") ? "neutral" : "info"}>{p.services_level.includes("(") ? p.services_level.split("(")[0].trim() : p.services_level}</StatusBadge> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

export function FluidsElecDetailV1() {
  const { token } = useAuth();
  const { data: overview, isLoading } = useQuery({
    queryKey: ["energie-overview"],
    queryFn: () => fetchEnergieOverview(token!),
    enabled: !!token,
    staleTime: 60_000,
  });

  const k = overview?.kpis;
  const coverage = k && k.total_prms > 0 ? Math.round((k.annual_consumption_prms / k.total_prms) * 100) : null;
  const surveiller = k ? (k.sous_dimensionnes ?? 0) + (k.proche_seuil ?? 0) : null;
  const suppliers = overview?.supplier_distribution ?? [];
  const prms = overview?.prms ?? [];
  const maxSupplierKva = Math.max(1, ...suppliers.map((s) => s.total_kva || 0));

  // Calibrage croisé fournisseur (depuis les PRM : statut × fournisseur)
  const supplierNames = useMemo(() => Array.from(new Set(prms.map((p) => shortSupplier(p.contractor)).filter((s) => s !== "—"))), [prms]);
  const calibCross = useMemo(() => {
    const grid: Record<string, Record<string, number>> = {};
    for (const status of CALIB_ORDER) grid[status] = Object.fromEntries(supplierNames.map((s) => [s, 0]));
    for (const p of prms) {
      const st = p.calibration_status ?? "";
      const sup = shortSupplier(p.contractor);
      if (grid[st] && grid[st][sup] != null) grid[st][sup] += 1;
    }
    return grid;
  }, [prms, supplierNames]);

  const refBlocks: { title: string; items: { label: string; prm_count: number; total_kva: number | null }[] }[] = overview
    ? [
        { title: "Services", items: overview.service_level_distribution },
        { title: "Segments", items: overview.segment_distribution },
        { title: "Tarifs", items: overview.tariff_distribution.slice(0, 5) },
        { title: "Raccordement", items: overview.connection_state_distribution },
      ]
    : [];

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head po2-fluid-head">
        <div>
          <span className="po2-eyebrow">Distributeur ENEDIS · Électricité</span>
          <h1>Détail électricité</h1>
          <p><Link to="/refonte-v1/fluides">← Retour vue globale</Link></p>
        </div>
        <div className="po2-fluid-source" style={{ margin: 0 }}>
          <span className="po2-fluid-dot" />
          <b>ENEDIS</b>
          <span>Conso {fmtDate(k?.annual_consumption_start)} → {fmtDate(k?.annual_consumption_end)}</span>
        </div>
      </header>

      {isLoading && !overview ? <p className="po2-muted-line">Chargement des données ENEDIS…</p> : null}

      {/* KPI ENEDIS */}
      <div className="po2-kpi-grid">
        <KpiCard label="PRM contractuels" value={k ? k.total_prms.toLocaleString("fr-FR") : "—"} detail={k ? `${k.annual_consumption_prms.toLocaleString("fr-FR")} avec conso collectée` : undefined} tone="neutral" />
        <KpiCard label="Puissance souscrite" value={formatKva(k?.total_subscribed_kva)} detail={`${suppliers.length} fournisseur(s)`} tone="neutral" />
        <KpiCard label="Conso annuelle collectée" value={formatKwh(k?.annual_consumption_kwh)} detail={k ? `${k.annual_consumption_prms.toLocaleString("fr-FR")} PRM · ${fmtDate(k.annual_consumption_start)} → ${fmtDate(k.annual_consumption_end)}` : undefined} tone="good" />
        <KpiCard label="Couverture complète" value={coverage != null ? `${coverage}%` : "—"} detail={k ? `${k.annual_consumption_prms.toLocaleString("fr-FR")} / ${k.total_prms.toLocaleString("fr-FR")} PRM` : undefined} tone="neutral" />
        <KpiCard label="À surveiller" value={surveiller != null ? surveiller.toLocaleString("fr-FR") : "—"} detail="Sous-dimensionnés ou proches du seuil" tone={surveiller && surveiller > 0 ? "warning" : "neutral"} />
      </div>

      {/* Graphiques (à l'image de Trajectoire climatique) — branchement en cours */}
      <div className="po2-two-columns">
        <section className="po2-card">
          <header className="po2-card__header">
            <div><span className="po2-eyebrow">Consommations</span><h2>Suivi vs moyenne des années précédentes</h2></div>
            <StatusBadge tone="info">à venir</StatusBadge>
          </header>
          <div className="po2-card__body"><p className="po2-muted-line">Graphique mensuel (année en cours vs moyenne N-1…N-3), dans le style « Trajectoire climatique ». Nécessite l'endpoint conso mensuelle multi-années — branchement au prochain incrément.</p></div>
        </section>
        <section className="po2-card">
          <header className="po2-card__header">
            <div><span className="po2-eyebrow">Performance</span><h2>Ratio kWh/DJU du parc</h2></div>
            <StatusBadge tone="info">à venir</StatusBadge>
          </header>
          <div className="po2-card__body"><p className="po2-muted-line">Ratios kWh/DJU mensuels + cible historique (ligne verte), restylés « Trajectoire climatique ». Données présentes (dju_seasonal) — restyle au prochain incrément.</p></div>
        </section>
      </div>

      {/* Dérives */}
      <section className="po2-card">
        <header className="po2-card__header">
          <div><span className="po2-eyebrow">Signaux · courbe de charge</span><h2>Dérives prioritaires</h2></div>
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
          <p className="po2-muted-line" style={{ marginTop: 10, fontSize: 12 }}>Détection réelle sur courbes de charge 30 min (collectées) — en cours de branchement. Ces items illustrent la mécanique.</p>
        </div>
      </section>

      <div className="po2-two-columns">
        {/* Calibrage croisé fournisseur */}
        <section className="po2-card">
          <header className="po2-card__header"><div><span className="po2-eyebrow">Contrats</span><h2>Calibrage × fournisseur</h2></div></header>
          <div className="po2-card__body" style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.2)" }}>
                  <th style={{ textAlign: "left", padding: "4px 6px" }}>Calibrage</th>
                  {supplierNames.map((s) => <th key={s} style={{ textAlign: "right", padding: "4px 6px" }}>{s}</th>)}
                  <th style={{ textAlign: "right", padding: "4px 6px" }}>Total</th>
                </tr>
              </thead>
              <tbody>
                {CALIB_ORDER.map((status) => {
                  const tot = supplierNames.reduce((a, s) => a + (calibCross[status]?.[s] ?? 0), 0);
                  return (
                    <tr key={status} style={{ borderBottom: "1px solid rgba(148,163,184,0.12)" }}>
                      <td style={{ padding: "4px 6px" }}><StatusBadge tone={CALIB_TONE[status]}>{CALIB_LABEL[status]}</StatusBadge></td>
                      {supplierNames.map((s) => <td key={s} style={{ textAlign: "right", padding: "4px 6px" }}>{(calibCross[status]?.[s] ?? 0).toLocaleString("fr-FR")}</td>)}
                      <td style={{ textAlign: "right", padding: "4px 6px", fontWeight: 700 }}>{tot.toLocaleString("fr-FR")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* Fournisseurs (puissance) */}
        <section className="po2-card">
          <header className="po2-card__header"><div><span className="po2-eyebrow">Marché</span><h2>Fournisseurs (puissance)</h2></div></header>
          <div className="po2-card__body">
            {suppliers.length === 0 ? <p className="po2-muted-line">—</p> : suppliers.map((s) => (
              <div key={s.supplier} style={{ marginBottom: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                  <span>{shortSupplier(s.supplier)}</span>
                  <b>{formatKva(s.total_kva)} · {s.prm_count.toLocaleString("fr-FR")} PRM</b>
                </div>
                <div style={{ height: 6, background: "rgba(148,163,184,0.18)", borderRadius: 4, overflow: "hidden" }}>
                  <div style={{ width: `${Math.round((s.total_kva / maxSupplierKva) * 100)}%`, height: "100%", background: "#6366f1" }} />
                </div>
              </div>
            ))}
            <p className="po2-muted-line" style={{ marginTop: 8, fontSize: 12 }}>Part de consommation par fournisseur : au prochain incrément (agrégat conso/fournisseur).</p>
          </div>
        </section>
      </div>

      {/* Referentiel contractuel ENEDIS */}
      <section className="po2-card">
        <header className="po2-card__header"><div><span className="po2-eyebrow">API contrats</span><h2>Référentiel contractuel ENEDIS</h2></div></header>
        <div className="po2-card__body">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 18 }}>
            {refBlocks.map((b) => (
              <div key={b.title}>
                <h4 style={{ margin: "0 0 6px" }}>{b.title}</h4>
                {b.items.map((it) => (
                  <div key={it.label} style={{ display: "flex", justifyContent: "space-between", gap: 8, padding: "3px 0", borderBottom: "1px solid rgba(148,163,184,0.12)" }}>
                    <span style={{ fontSize: 12 }}>{it.label}</span>
                    <span style={{ whiteSpace: "nowrap", textAlign: "right" }}><strong>{it.prm_count.toLocaleString("fr-FR")} PRM</strong><br /><small className="po2-muted-line">{it.total_kva != null ? formatKva(it.total_kva) : ""}</small></span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </section>

      <MetersTable prms={prms} />
    </div>
  );
}
