import { useMemo, useState, type CSSProperties } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, Cell, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { KpiCard, SegmentControl, StatusBadge } from "../../design-system";
import { fetchCvcParcTechnique, type CvcParcBucket, type CvcParcTechniqueReport } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";
import { CarencesAuditV1 } from "./CarencesAuditV1";
import { CvcImportPage } from "../../pages/CvcImportPage";

type TechniqueTab = "parc" | "carences" | "import";

const TABS: { value: TechniqueTab; label: string }[] = [
  { value: "parc", label: "État du parc" },
  { value: "carences", label: "Audit des carences" },
  { value: "import", label: "Import des inventaires" },
];

// Série unique (un effectif par tranche) → une seule couleur, pas de légende.
const AGE_COLOR = "#3e6ea8";

// La criticité est un ÉTAT (sain → dépassé), pas une série catégorielle : on
// utilise la palette de statut du design system, jamais des couleurs de séries.
// Chaque barre porte son libellé en axe : l'information n'est pas dans la couleur seule.
const CRITICITE_COLORS: Record<string, string> = {
  faible: "#247a60", // po2-status--ok
  moyenne: "#91631b", // po2-status--warn
  elevee: "#c2410c", // palier « sérieux »
  depasse: "#a6413b", // po2-status--bad
  inconnu: "#94a3b8", // donnée absente — neutre, jamais un statut
};

function fmtInt(value: number): string {
  return value.toLocaleString("fr-FR");
}

function completudeTone(pct: number): "ok" | "warn" | "bad" {
  if (pct >= 80) return "ok";
  if (pct >= 50) return "warn";
  return "bad";
}

/** Barre de complétude : ce n'est pas un graphe, juste une jauge lisible. */
function CompletudeBar({ label, pct, helper }: { label: string; pct: number; helper: string }) {
  const tone = completudeTone(pct);
  const color = tone === "ok" ? "#247a60" : tone === "warn" ? "#91631b" : "#a6413b";
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 3 }}>
        <span>{label}</span>
        <strong>{pct} %</strong>
      </div>
      <div style={{ height: 6, background: "rgba(148,163,184,0.18)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(100, pct)}%`, height: "100%", background: color }} />
      </div>
      <small className="po2-muted-line" style={{ fontSize: 11 }}>{helper}</small>
    </div>
  );
}

function BucketChart({
  buckets,
  unit,
  colorFor,
}: {
  buckets: CvcParcBucket[];
  unit: string;
  colorFor: (bucket: CvcParcBucket) => string;
}) {
  const data = buckets.map((bucket) => ({ ...bucket, name: bucket.label }));
  return (
    <div style={{ height: 250 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.22)" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} />
          <YAxis tick={{ fontSize: 11 }} width={44} allowDecimals={false} />
          <Tooltip
            cursor={{ fill: "rgba(148,163,184,0.12)" }}
            formatter={(value: number, _name, payload) => [
              `${fmtInt(value)} ${unit} (${payload?.payload?.share_pct ?? 0} %)`,
              payload?.payload?.label ?? "",
            ]}
            labelFormatter={() => ""}
          />
          <Bar dataKey="count" maxBarSize={46} radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.key} fill={colorFor(entry)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

type SortKey = "nom_batiment" | "count" | "age_moyen" | "depasses" | "fin_de_vie_5ans";

function BatimentsTable({ report }: { report: CvcParcTechniqueReport }) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("depasses");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = report.par_batiment.filter((b) => !q || (b.nom_batiment ?? "").toLowerCase().includes(q));
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const va = a[sortKey];
      const vb = b[sortKey];
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
      return String(va).localeCompare(String(vb), "fr") * dir;
    });
  }, [report.par_batiment, query, sortKey, sortDir]);

  const onSort = (key: SortKey) => {
    if (key === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir(key === "nom_batiment" ? "asc" : "desc");
    }
  };
  const caret = (key: SortKey) => (key === sortKey ? (sortDir === "asc" ? " ▲" : " ▼") : "");

  const th: CSSProperties = {
    textAlign: "left",
    padding: "6px 8px",
    cursor: "pointer",
    whiteSpace: "nowrap",
    position: "sticky",
    top: 0,
    background: "var(--po2-surface, #0f172a1a)",
    userSelect: "none",
  };
  const td: CSSProperties = { padding: "5px 8px", borderBottom: "1px solid rgba(148,163,184,0.14)", whiteSpace: "nowrap" };

  const columns: { key: SortKey; label: string; num?: boolean }[] = [
    { key: "nom_batiment", label: "Bâtiment" },
    { key: "count", label: "Équipements", num: true },
    { key: "age_moyen", label: "Âge moyen", num: true },
    { key: "depasses", label: "Dépassés", num: true },
    { key: "fin_de_vie_5ans", label: "Fin de vie < 5 ans", num: true },
  ];

  return (
    <section className="po2-card">
      <header className="po2-card__header">
        <div>
          <span className="po2-eyebrow">Par bâtiment</span>
          <h2>Où renouveler en priorité</h2>
        </div>
      </header>
      <div className="po2-card__body">
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher un bâtiment…"
            style={{ flex: "0 1 320px", minWidth: 200, padding: "7px 10px", borderRadius: 8, border: "1px solid #d1d5db" }}
          />
          <span className="po2-muted-line" style={{ marginLeft: "auto" }}>{fmtInt(rows.length)} bâtiments</span>
        </div>
        <div style={{ overflowX: "auto", maxHeight: 460, overflowY: "auto" }}>
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
              {rows.map((b) => (
                <tr key={b.building_id}>
                  <td style={{ ...td, fontWeight: 600 }}>{b.nom_batiment || `Bâtiment ${b.building_id}`}</td>
                  <td style={{ ...td, textAlign: "right" }}>{fmtInt(b.count)}</td>
                  <td style={{ ...td, textAlign: "right" }}>{b.age_moyen != null ? `${b.age_moyen} ans` : "—"}</td>
                  <td style={{ ...td, textAlign: "right" }}>
                    {b.depasses > 0 ? <StatusBadge tone="bad">{String(b.depasses)}</StatusBadge> : "—"}
                  </td>
                  <td style={{ ...td, textAlign: "right" }}>
                    {b.fin_de_vie_5ans > 0 ? <StatusBadge tone="warn">{String(b.fin_de_vie_5ans)}</StatusBadge> : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

export function TechniqueParcDetailV1() {
  const { token } = useAuth();
  const [tab, setTab] = useState<TechniqueTab>("parc");
  const [provider, setProvider] = useState<string>("");
  const [famille, setFamille] = useState<string>("");

  const { data: report, isLoading } = useQuery({
    queryKey: ["cvc-parc-technique", provider, famille],
    queryFn: () => fetchCvcParcTechnique(token!, { provider: provider || undefined, famille: famille || undefined }),
    enabled: !!token,
    staleTime: 60_000,
  });

  // Le référentiel de familles vient du parc complet, pas du parc filtré, sinon
  // le filtre se viderait lui-même dès qu'il est appliqué.
  const { data: fullReport } = useQuery({
    queryKey: ["cvc-parc-technique", "__all__"],
    queryFn: () => fetchCvcParcTechnique(token!),
    enabled: !!token,
    staleTime: 60_000,
  });

  const familles = useMemo(
    () => (fullReport?.par_famille ?? []).map((f) => f.famille),
    [fullReport],
  );
  const providers = useMemo(
    () => (fullReport?.par_provider ?? []).map((p) => p.key),
    [fullReport],
  );

  const nonCalculable = report?.ages.find((bucket) => bucket.key === "inconnu");
  const aRenouveler = report ? report.depasses + report.fin_de_vie_5ans : 0;

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head po2-fluid-head">
        <div>
          <span className="po2-eyebrow">Patrimoine technique · CVC</span>
          <h1>État du parc technique</h1>
          <p className="po2-muted-line" style={{ maxWidth: 620 }}>
            Âge, vétusté et échéances de renouvellement des équipements de chauffage, ventilation et
            climatisation, à partir des inventaires de maintenance.
          </p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
          <div className="po2-fluid-source" style={{ margin: 0 }}>
            <span className="po2-fluid-dot" />
            <b>Inventaires</b>
            <span>{(report?.par_provider ?? []).map((p) => p.key).join(" · ") || "—"}</span>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Link to="/buildings/cvc-import" className="po2-muted-line" style={{ fontSize: 12 }}>
              Import →
            </Link>
            <Link to="/buildings/cvc-import/batiments" className="po2-muted-line" style={{ fontSize: 12 }}>
              Rattachements →
            </Link>
            <Link to="/buildings/cvc-fluides" className="po2-muted-line" style={{ fontSize: 12 }}>
              Fluides frigorigènes →
            </Link>
          </div>
        </div>
      </header>

      <div style={{ marginBottom: 16 }}>
        <SegmentControl value={tab} options={TABS} onChange={setTab} />
      </div>

      {tab === "carences" ? <CarencesAuditV1 /> : null}

      {/* L'écran d'import existant est ré-hébergé tel quel : un flux qui fonctionne
          n'est pas réécrit pour l'esthétique. */}
      {tab === "import" ? (
        <section className="po2-card">
          <div className="po2-card__body">
            <CvcImportPage />
          </div>
        </section>
      ) : null}

      {tab === "parc" && isLoading && !report ? (
        <p className="po2-muted-line">Chargement de l'inventaire technique…</p>
      ) : null}

      {tab === "parc" && report ? (
        <>
          {/* Filtres — une seule rangée au-dessus des graphes */}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 14 }}>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              style={{ padding: "7px 10px", borderRadius: 8, border: "1px solid #d1d5db" }}
            >
              <option value="">Tous les prestataires</option>
              {providers.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
            <select
              value={famille}
              onChange={(e) => setFamille(e.target.value)}
              style={{ padding: "7px 10px", borderRadius: 8, border: "1px solid #d1d5db" }}
            >
              <option value="">Toutes les familles</option>
              {familles.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
            {(provider || famille) && (
              <button
                type="button"
                className="po2-button po2-button--ghost"
                onClick={() => {
                  setProvider("");
                  setFamille("");
                }}
              >
                Réinitialiser
              </button>
            )}
          </div>

          {/* KPI */}
          <div className="po2-kpi-grid">
            <KpiCard
              label="Équipements"
              value={fmtInt(report.equipements_total)}
              detail={`${fmtInt(report.equipements_rattaches)} rattachés · ${report.batiments_couverts} bâtiments`}
              tone="neutral"
            />
            <KpiCard
              label="Âge moyen"
              value={report.age_moyen != null ? `${report.age_moyen} ans` : "—"}
              detail={nonCalculable ? `calculé hors ${fmtInt(nonCalculable.count)} équipements sans date` : undefined}
              tone="neutral"
            />
            <KpiCard
              label="Durée de vie dépassée"
              value={fmtInt(report.depasses)}
              detail="à remplacer ou à requalifier"
              tone={report.depasses > 0 ? "warning" : "good"}
            />
            <KpiCard
              label="Fin de vie sous 5 ans"
              value={fmtInt(report.fin_de_vie_5ans)}
              detail="à budgéter"
              tone={report.fin_de_vie_5ans > 0 ? "warning" : "good"}
            />
            <KpiCard
              label="À traiter sous 5 ans"
              value={fmtInt(aRenouveler)}
              detail={
                report.equipements_total
                  ? `${Math.round((100 * aRenouveler) / report.equipements_total)} % du parc`
                  : undefined
              }
              tone={aRenouveler > 0 ? "warning" : "good"}
            />
          </div>

          {/* Graphes */}
          <div className="po2-two-columns" style={{ gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
            <section className="po2-card">
              <header className="po2-card__header">
                <div>
                  <span className="po2-eyebrow">Âges</span>
                  <h2>Pyramide des âges du parc</h2>
                </div>
              </header>
              <div className="po2-card__body">
                <BucketChart buckets={report.ages} unit="équipements" colorFor={() => AGE_COLOR} />
                <p className="po2-muted-line" style={{ fontSize: 12 }}>
                  Nombre d'équipements par tranche d'âge. « Non calculable » = date de mise en service absente.
                </p>
              </div>
            </section>

            <section className="po2-card">
              <header className="po2-card__header">
                <div>
                  <span className="po2-eyebrow">Vétusté</span>
                  <h2>Criticité vs durée de vie de référence</h2>
                </div>
              </header>
              <div className="po2-card__body">
                <BucketChart
                  buckets={report.criticites}
                  unit="équipements"
                  colorFor={(bucket) => CRITICITE_COLORS[bucket.key] ?? "#94a3b8"}
                />
                <p className="po2-muted-line" style={{ fontSize: 12 }}>
                  Part de durée de vie consommée (âge / durée de référence SYPEMI). Au-delà de 100 %,
                  l'équipement a dépassé sa durée de vie théorique.
                </p>
              </div>
            </section>
          </div>

          {/* Complétude — la lecture honnête des chiffres ci-dessus */}
          <section className="po2-card">
            <header className="po2-card__header">
              <div>
                <span className="po2-eyebrow">Qualité de la donnée</span>
                <h2>Ce que l'on sait vraiment du parc</h2>
              </div>
              {nonCalculable && nonCalculable.count > 0 ? (
                <StatusBadge tone="warn">{`${nonCalculable.share_pct} % non calculable`}</StatusBadge>
              ) : null}
            </header>
            <div className="po2-card__body">
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 20 }}>
                <CompletudeBar
                  label="Rattachement au patrimoine"
                  pct={report.completude.rattachement_pct}
                  helper="équipements reliés à un bâtiment — conditionne toute analyse par site"
                />
                <CompletudeBar
                  label="Date de mise en service"
                  pct={report.completude.date_mes_pct}
                  helper="condition du calcul d'âge et de vétusté"
                />
                <CompletudeBar
                  label="Référence durée de vie"
                  pct={report.completude.reference_pct}
                  helper="rapprochement au référentiel SYPEMI"
                />
                <CompletudeBar
                  label="Durée de vie restante"
                  pct={report.completude.duree_vie_pct}
                  helper="calculée ou fournie par le prestataire"
                />
              </div>
              <p className="po2-muted-line" style={{ fontSize: 12, marginTop: 10 }}>
                Les indicateurs d'âge et de criticité ne portent que sur les équipements dont la donnée
                est disponible : ces taux se lisent à côté des chiffres, pas après.
              </p>
            </div>
          </section>

          <BatimentsTable report={report} />

          {/* Familles */}
          <section className="po2-card">
            <header className="po2-card__header">
              <div>
                <span className="po2-eyebrow">Par famille</span>
                <h2>Typologies d'équipements</h2>
              </div>
            </header>
            <div className="po2-card__body" style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.2)" }}>
                    <th style={{ textAlign: "left", padding: "4px 6px" }}>Famille</th>
                    <th style={{ textAlign: "right", padding: "4px 6px" }}>Équipements</th>
                    <th style={{ textAlign: "right", padding: "4px 6px" }}>Âge moyen</th>
                    <th style={{ textAlign: "right", padding: "4px 6px" }}>Dépassés</th>
                    <th style={{ textAlign: "right", padding: "4px 6px" }}>Fin de vie &lt; 5 ans</th>
                  </tr>
                </thead>
                <tbody>
                  {report.par_famille.map((f) => (
                    <tr key={f.famille} style={{ borderBottom: "1px solid rgba(148,163,184,0.12)" }}>
                      <td style={{ padding: "4px 6px", fontWeight: 600 }}>{f.famille}</td>
                      <td style={{ textAlign: "right", padding: "4px 6px" }}>{fmtInt(f.count)}</td>
                      <td style={{ textAlign: "right", padding: "4px 6px" }}>
                        {f.age_moyen != null ? `${f.age_moyen} ans` : "—"}
                      </td>
                      <td style={{ textAlign: "right", padding: "4px 6px" }}>
                        {f.depasses > 0 ? <StatusBadge tone="bad">{String(f.depasses)}</StatusBadge> : "—"}
                      </td>
                      <td style={{ textAlign: "right", padding: "4px 6px" }}>
                        {f.fin_de_vie_5ans > 0 ? <StatusBadge tone="warn">{String(f.fin_de_vie_5ans)}</StatusBadge> : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
