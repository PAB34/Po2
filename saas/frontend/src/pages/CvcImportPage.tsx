import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";
import {
  fetchBuildings,
  postCvcPreview,
  postCvcMatchBuildings,
  postCvcImport,
  type Building,
  type CvcPreviewResponse,
  type SiteMatchResult,
  type CvcImportResult,
} from "../lib/api";

const SUBTLE_TEXT = "#94a3b8";
const NEUTRAL_BORDER = "rgba(148, 163, 184, 0.25)";

type Step = "upload" | "mapping" | "result";

function scoreColor(score: number): string {
  if (score >= 0.8) return "#4ade80";
  if (score >= 0.5) return "#fbbf24";
  return "#f87171";
}

// ─── Composant SearchableSelect ──────────────────────────────────────────────

type SelectOption = {
  id: number;
  label: string;
  score?: number;
};

type SearchableSelectProps = {
  value: number | "";
  onChange: (value: number | "") => void;
  suggestions: SelectOption[];
  allBuildings: SelectOption[];
};

function SearchableSelect({ value, onChange, suggestions, allBuildings }: SearchableSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fermer si clic en dehors
  useEffect(() => {
    function onMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch("");
      }
    }
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, []);

  // Focus sur l'input à l'ouverture
  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const allOptions = [...suggestions, ...allBuildings];
  const selectedOption = value !== "" ? allOptions.find((o) => o.id === value) : null;
  const displayLabel = selectedOption ? selectedOption.label : "— Ignorer ce site —";

  const query = search.toLowerCase().trim();
  const filteredSuggestions = query
    ? suggestions.filter((o) => o.label.toLowerCase().includes(query))
    : suggestions;
  const filteredAll = query
    ? allBuildings.filter((o) => o.label.toLowerCase().includes(query))
    : allBuildings;
  const hasResults = filteredSuggestions.length > 0 || filteredAll.length > 0;

  function select(id: number | "") {
    onChange(id);
    setOpen(false);
    setSearch("");
  }

  const itemStyle = (isSelected: boolean): React.CSSProperties => ({
    padding: "7px 12px",
    fontSize: "0.82rem",
    color: isSelected ? "#93c5fd" : "#cbd5e1",
    cursor: "pointer",
    background: isSelected ? "rgba(59,130,246,0.12)" : "transparent",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 8,
  });

  const groupHeaderStyle: React.CSSProperties = {
    padding: "5px 12px",
    fontSize: "0.68rem",
    color: "#475569",
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    background: "rgba(15,23,42,0.6)",
    borderTop: "1px solid rgba(148,163,184,0.1)",
    borderBottom: "1px solid rgba(148,163,184,0.08)",
  };

  return (
    <div ref={containerRef} style={{ position: "relative", width: "100%" }}>
      {/* Déclencheur */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%",
          padding: "6px 10px",
          textAlign: "left",
          background: "rgba(15,23,42,0.7)",
          border: `1px solid ${value !== "" ? "rgba(34,197,94,0.4)" : "rgba(148,163,184,0.25)"}`,
          borderRadius: 6,
          color: value !== "" ? "#e2e8f0" : "#64748b",
          fontSize: "0.84rem",
          cursor: "pointer",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 6,
        }}
      >
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
          {displayLabel}
        </span>
        <span style={{ color: "#475569", fontSize: "0.65rem", flexShrink: 0 }}>▾</span>
      </button>

      {/* Panneau dropdown */}
      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            right: 0,
            zIndex: 1000,
            background: "rgba(13,20,35,0.98)",
            border: "1px solid rgba(148,163,184,0.25)",
            borderRadius: 8,
            boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
            overflow: "hidden",
          }}
        >
          {/* Champ de recherche */}
          <div style={{ padding: "8px 8px 6px", borderBottom: "1px solid rgba(148,163,184,0.15)" }}>
            <input
              ref={inputRef}
              type="text"
              placeholder="Rechercher un bâtiment…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: "100%",
                padding: "5px 9px",
                background: "rgba(30,41,59,0.9)",
                border: "1px solid rgba(148,163,184,0.2)",
                borderRadius: 5,
                color: "#e2e8f0",
                fontSize: "0.82rem",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Liste */}
          <div style={{ maxHeight: 300, overflowY: "auto" }}>
            {/* Option "Ignorer" */}
            <div
              style={{ ...itemStyle(value === ""), borderBottom: "1px solid rgba(148,163,184,0.1)", color: value === "" ? "#93c5fd" : "#475569" }}
              onMouseEnter={(e) => { if (value !== "") e.currentTarget.style.background = "rgba(51,65,85,0.5)"; }}
              onMouseLeave={(e) => { if (value !== "") e.currentTarget.style.background = "transparent"; }}
              onClick={() => select("")}
            >
              — Ignorer ce site —
            </div>

            {/* Suggestions automatiques */}
            {filteredSuggestions.length > 0 && (
              <>
                <div style={groupHeaderStyle}>Suggestions automatiques</div>
                {filteredSuggestions.map((o) => (
                  <div
                    key={o.id}
                    style={itemStyle(value === o.id)}
                    onMouseEnter={(e) => { if (value !== o.id) e.currentTarget.style.background = "rgba(51,65,85,0.5)"; }}
                    onMouseLeave={(e) => { if (value !== o.id) e.currentTarget.style.background = value === o.id ? "rgba(59,130,246,0.12)" : "transparent"; }}
                    onClick={() => select(o.id)}
                  >
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{o.label}</span>
                    {o.score !== undefined && (
                      <span style={{ fontSize: "0.7rem", color: scoreColor(o.score), fontWeight: 700, flexShrink: 0 }}>
                        {Math.round(o.score * 100)} %
                      </span>
                    )}
                  </div>
                ))}
              </>
            )}

            {/* Tous les bâtiments */}
            {filteredAll.length > 0 && (
              <>
                <div style={groupHeaderStyle}>
                  Tous les bâtiments {query ? `— ${filteredAll.length} résultat${filteredAll.length > 1 ? "s" : ""}` : ""}
                </div>
                {filteredAll.map((o) => (
                  <div
                    key={o.id}
                    style={{ ...itemStyle(value === o.id), color: value === o.id ? "#93c5fd" : "#94a3b8" }}
                    onMouseEnter={(e) => { if (value !== o.id) e.currentTarget.style.background = "rgba(51,65,85,0.5)"; }}
                    onMouseLeave={(e) => { if (value !== o.id) e.currentTarget.style.background = value === o.id ? "rgba(59,130,246,0.12)" : "transparent"; }}
                    onClick={() => select(o.id)}
                  >
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{o.label}</span>
                  </div>
                ))}
              </>
            )}

            {/* Aucun résultat */}
            {!hasResults && (
              <div style={{ padding: "18px 12px", textAlign: "center", fontSize: "0.82rem", color: "#475569" }}>
                Aucun résultat pour « {search} »
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Page principale ─────────────────────────────────────────────────────────

export function CvcImportPage() {
  const { token } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<Step>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CvcPreviewResponse | null>(null);
  const [matches, setMatches] = useState<SiteMatchResult[]>([]);
  const [selectedMapping, setSelectedMapping] = useState<Record<string, number | "">>({});
  const [result, setResult] = useState<CvcImportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const buildingsQuery = useQuery<Building[]>({
    queryKey: ["buildings"],
    queryFn: () => fetchBuildings(token ?? ""),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  });

  async function handlePreview() {
    if (!file || !token) return;
    setLoading(true);
    setError(null);
    try {
      const prev = await postCvcPreview(token, file);
      setPreview(prev);
      const matchRes = await postCvcMatchBuildings(token, prev.unique_sites);
      const m = matchRes.matches;
      setMatches(m);
      const init: Record<string, number | ""> = {};
      for (const r of m) {
        init[r.site_raw] = r.auto_selected_id ?? "";
      }
      setSelectedMapping(init);
      setStep("mapping");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erreur de lecture du fichier.");
    } finally {
      setLoading(false);
    }
  }

  async function handleImport() {
    if (!file || !token) return;
    const mapping = Object.entries(selectedMapping)
      .filter(([, bid]) => bid !== "")
      .map(([site_raw, building_id]) => ({ site_raw, building_id: building_id as number }));
    if (mapping.length === 0) {
      setError("Aucun bâtiment mappé. Associe au moins un site à un bâtiment.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await postCvcImport(token, file, mapping);
      setResult(res);
      setStep("result");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erreur lors de l'import.");
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setStep("upload");
    setFile(null);
    setPreview(null);
    setMatches([]);
    setSelectedMapping({});
    setResult(null);
    setError(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  const mappedCount = Object.values(selectedMapping).filter((v) => v !== "").length;
  const unmappedCount = matches.length - mappedCount;

  if (!token) {
    return (
      <section className="panel stack-lg">
        <h2>Import inventaire CVC</h2>
        <p>Connecte-toi pour accéder à cette page.</p>
      </section>
    );
  }

  return (
    <section className="panel stack-lg">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Gestion Technique</p>
          <h2>Import inventaire CVC terrain</h2>
          <p>Importe le fichier Excel d'inventaire matériels et rattache chaque site à un bâtiment de ta base.</p>
        </div>
        <div className="buildings-header-actions">
          <Link className="secondary-link" to="/buildings/technique">Retour à la gestion technique</Link>
        </div>
      </div>

      {/* Stepper */}
      <div style={{ display: "flex", gap: 4, alignItems: "center", fontSize: "0.85rem" }}>
        {(["upload", "mapping", "result"] as Step[]).map((s, i) => {
          const labels = ["1. Upload", "2. Mapping bâtiments", "3. Résultat"];
          const isActive = step === s;
          const isDone = (step === "mapping" && s === "upload") || step === "result";
          return (
            <span key={s} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span
                style={{
                  padding: "4px 12px",
                  borderRadius: 12,
                  fontWeight: isActive ? 700 : 400,
                  background: isActive
                    ? "rgba(59, 130, 246, 0.25)"
                    : isDone
                      ? "rgba(34, 197, 94, 0.15)"
                      : "rgba(51, 65, 85, 0.3)",
                  color: isActive ? "#93c5fd" : isDone ? "#4ade80" : SUBTLE_TEXT,
                  border: `1px solid ${isActive ? "rgba(59,130,246,0.4)" : "transparent"}`,
                }}
              >
                {labels[i]}
              </span>
              {i < 2 && <span style={{ color: SUBTLE_TEXT }}>→</span>}
            </span>
          );
        })}
      </div>

      {error && (
        <div style={{ padding: "10px 14px", background: "rgba(220,38,38,0.15)", border: "1px solid rgba(220,38,38,0.4)", borderRadius: 8, color: "#fca5a5" }}>
          {error}
        </div>
      )}

      {/* ── Étape 1 : Upload ── */}
      {step === "upload" && (
        <div className="section-block" style={{ maxWidth: 560 }}>
          <h3>Sélectionne le fichier Excel</h3>
          <p style={{ color: SUBTLE_TEXT, fontSize: "0.9rem" }}>
            Format attendu : colonnes SITE, BATIMENT, NIVEAU, LOCAL, DESIGNATION, STATUT, ETAT SANTE, QTE, FAMILLE, MARQUE, MODELE, DATE MES.
          </p>
          <label className="field" style={{ marginTop: 16 }}>
            <span>Fichier .xlsx</span>
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          {file && (
            <p style={{ fontSize: "0.85rem", color: SUBTLE_TEXT, marginTop: 4 }}>
              Fichier sélectionné : <strong style={{ color: "#e2e8f0" }}>{file.name}</strong>
            </p>
          )}
          <button
            type="button"
            className="primary-button"
            style={{ marginTop: 16 }}
            onClick={handlePreview}
            disabled={!file || loading}
          >
            {loading ? "Analyse en cours..." : "Analyser le fichier →"}
          </button>
        </div>
      )}

      {/* ── Étape 2 : Mapping ── */}
      {step === "mapping" && preview && (
        <div className="section-block">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
            <div>
              <h3>Associe chaque site à un bâtiment</h3>
              <p style={{ color: SUBTLE_TEXT, fontSize: "0.9rem" }}>
                {preview.total_rows} lignes — {matches.length} sites détectés —{" "}
                <strong style={{ color: "#4ade80" }}>{mappedCount} mappés</strong>
                {unmappedCount > 0 && <span style={{ color: "#fbbf24" }}> · {unmappedCount} non mappés (ignorés)</span>}
              </p>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="button" className="secondary-button" onClick={reset}>
                Recommencer
              </button>
              <button
                type="button"
                className="primary-button"
                onClick={handleImport}
                disabled={loading || mappedCount === 0}
              >
                {loading ? "Import en cours..." : `Importer (${mappedCount} sites) →`}
              </button>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 16 }}>
            {matches.map((m) => {
              const selectedId = selectedMapping[m.site_raw];
              const bestSuggestion = m.suggestions[0];
              const suggestionIds = new Set(m.suggestions.map((s) => s.building_id));

              // Convertir suggestions en SelectOption
              const suggestionOptions: SelectOption[] = m.suggestions.map((s) => ({
                id: s.building_id,
                label: [s.nom_batiment ?? `Bâtiment #${s.building_id}`, s.adresse]
                  .filter(Boolean)
                  .join(" — "),
                score: s.score,
              }));

              // Tous les bâtiments hors suggestions, triés par nom
              const allBuildingOptions: SelectOption[] = (buildingsQuery.data ?? [])
                .filter((b) => !suggestionIds.has(b.id))
                .sort((a, b) =>
                  (a.nom_batiment ?? "").localeCompare(b.nom_batiment ?? "", "fr", { sensitivity: "base" }),
                )
                .map((b) => ({
                  id: b.id,
                  label: [b.nom_batiment ?? `Bâtiment #${b.id}`, b.adresse_reconstituee]
                    .filter(Boolean)
                    .join(" — "),
                }));

              return (
                <div
                  key={m.site_raw}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 12,
                    alignItems: "center",
                    padding: "10px 14px",
                    border: `1px solid ${selectedId ? "rgba(34,197,94,0.3)" : NEUTRAL_BORDER}`,
                    borderRadius: 8,
                    background: selectedId ? "rgba(34,197,94,0.05)" : "rgba(15,23,42,0.3)",
                  }}
                >
                  <div>
                    <strong style={{ fontSize: "0.88rem" }}>{m.site_raw}</strong>
                    {bestSuggestion && (
                      <div style={{ fontSize: "0.75rem", color: SUBTLE_TEXT, marginTop: 2 }}>
                        Meilleure suggestion :{" "}
                        <span style={{ color: scoreColor(bestSuggestion.score), fontWeight: 600 }}>
                          {Math.round(bestSuggestion.score * 100)} %
                        </span>
                      </div>
                    )}
                  </div>
                  <SearchableSelect
                    value={selectedId ?? ""}
                    onChange={(val) =>
                      setSelectedMapping((prev) => ({ ...prev, [m.site_raw]: val }))
                    }
                    suggestions={suggestionOptions}
                    allBuildings={allBuildingOptions}
                  />
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Étape 3 : Résultat ── */}
      {step === "result" && result && (
        <div className="section-block" style={{ maxWidth: 560 }}>
          <h3>Import terminé</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              <div style={{ textAlign: "center", padding: "12px 20px", background: "rgba(34,197,94,0.12)", border: "1px solid rgba(34,197,94,0.3)", borderRadius: 8 }}>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "#4ade80" }}>{result.imported}</div>
                <div style={{ fontSize: "0.8rem", color: SUBTLE_TEXT }}>lignes importées</div>
              </div>
              <div style={{ textAlign: "center", padding: "12px 20px", background: "rgba(59,130,246,0.12)", border: "1px solid rgba(59,130,246,0.3)", borderRadius: 8 }}>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "#60a5fa" }}>{result.sypemi_matched}</div>
                <div style={{ fontSize: "0.8rem", color: SUBTLE_TEXT }}>liées au référentiel SYPEMI</div>
              </div>
              <div style={{ textAlign: "center", padding: "12px 20px", background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.3)", borderRadius: 8 }}>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "#fbbf24" }}>{result.skipped}</div>
                <div style={{ fontSize: "0.8rem", color: SUBTLE_TEXT }}>ignorées (site non mappé)</div>
              </div>
            </div>
            <p style={{ fontSize: "0.85rem", color: SUBTLE_TEXT }}>
              Référence import : <code style={{ color: "#e2e8f0" }}>{result.import_batch}</code>
            </p>
            {result.sypemi_unmatched > 0 && (
              <p style={{ fontSize: "0.85rem", color: "#fbbf24" }}>
                {result.sypemi_unmatched} équipements sans correspondance SYPEMI — durée de vie non calculée pour ceux-ci.
              </p>
            )}
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
            <Link to="/buildings/technique" className="primary-button" style={{ textDecoration: "none" }}>
              Voir l'inventaire technique →
            </Link>
            <button type="button" className="secondary-button" onClick={reset}>
              Importer un autre fichier
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
