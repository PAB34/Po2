import { useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";
import {
  fetchBuildings,
  fetchEquipmentReferences,
  fetchEquipmentSummaries,
  fetchBuildingEquipments,
  bulkCreateBuildingEquipments,
  updateBuildingEquipmentRequest,
  deleteBuildingEquipmentRequest,
  type Building,
  type EquipmentReference,
  type BuildingEquipmentSummary,
  type BuildingEquipment as BuildingEquipmentType,
} from "../lib/api";

const ETAT_LABELS: Record<string, string> = {
  obsolete: "Obsolète",
  degrade: "Dégradé",
  moyen: "Moyen",
  neuf: "Neuf",
};

// Couleurs adaptatives mode clair/sombre :
// - text en teinte 400 (suffisamment claire pour fond sombre, suffisamment foncée pour fond clair)
// - background en rgba translucide qui s'adapte au fond du panneau
const ETAT_COLORS: Record<string, string> = {
  obsolete: "#f87171", // red-400
  degrade: "#fbbf24",  // amber-400
  moyen: "#60a5fa",    // blue-400
  neuf: "#4ade80",     // green-400
};

const ETAT_BG: Record<string, string> = {
  obsolete: "rgba(220, 38, 38, 0.18)",
  degrade: "rgba(245, 158, 11, 0.18)",
  moyen: "rgba(59, 130, 246, 0.18)",
  neuf: "rgba(34, 197, 94, 0.18)",
};

const ETAT_BORDER: Record<string, string> = {
  obsolete: "rgba(220, 38, 38, 0.4)",
  degrade: "rgba(245, 158, 11, 0.4)",
  moyen: "rgba(59, 130, 246, 0.4)",
  neuf: "rgba(34, 197, 94, 0.4)",
};

// Tons neutres adaptatifs pour bordures et fonds de section
const NEUTRAL_BORDER = "rgba(148, 163, 184, 0.25)";
const NEUTRAL_BG_LIGHT = "rgba(51, 65, 85, 0.4)";   // headers niveau 1
const NEUTRAL_BG_DARKER = "rgba(51, 65, 85, 0.3)";  // headers niveau 2 / déjà assigné
const SUBTLE_TEXT = "#94a3b8"; // slate-400, lisible sur clair et sombre

const QUANTITE_LABELS: Record<string, string> = {
  faible: "Faible",
  moyenne: "Moyenne",
  elevee: "Élevée",
};

type TechniqueScope = "all" | "cvc" | "enveloppe";

const TECHNIQUE_SCOPE_CONFIG: Record<TechniqueScope, { label: string; shortLabel: string; title: string; emptyLabel: string }> = {
  all: {
    label: "Tous les lots",
    shortLabel: "Tous",
    title: "Inventaire technique",
    emptyLabel: "élément assigné",
  },
  cvc: {
    label: "CVC",
    shortLabel: "CVC",
    title: "Inventaire CVC",
    emptyLabel: "équipement CVC assigné",
  },
  enveloppe: {
    label: "Enveloppe",
    shortLabel: "Enveloppe",
    title: "Inventaire enveloppe",
    emptyLabel: "élément d'enveloppe assigné",
  },
};

function matchesTechniqueScope(ref: EquipmentReference | null | undefined, scope: TechniqueScope): boolean {
  if (scope === "all") return true;
  if (!ref) return false;
  if (scope === "cvc") return ref.code_niveau_2 === "A.2.3";
  return ref.code_niveau_1 === "A.1";
}

function scoreColor(score: number | null): string {
  if (score === null) return "#94a3b8";
  if (score <= 25) return "#dc2626";
  if (score <= 50) return "#f59e0b";
  if (score <= 75) return "#eab308";
  return "#22c55e";
}

function buildAddressLine(b: Building) {
  if (b.adresse_reconstituee) return b.adresse_reconstituee;
  const parts = [b.numero_voirie, b.nature_voie, b.nom_voie].filter(Boolean);
  return parts.length > 0 ? `${parts.join(" ")}, ${b.nom_commune}` : b.nom_commune;
}

type GroupedRefs = {
  code_niveau_1: string;
  libelle_niveau_1: string;
  niveau2: {
    code_niveau_2: string;
    libelle_niveau_2: string;
    items: EquipmentReference[];
  }[];
};

function groupReferences(refs: EquipmentReference[]): GroupedRefs[] {
  const map1 = new Map<string, { libelle: string; map2: Map<string, { libelle: string; items: EquipmentReference[] }> }>();
  for (const r of refs) {
    if (!map1.has(r.code_niveau_1)) {
      map1.set(r.code_niveau_1, { libelle: r.libelle_niveau_1, map2: new Map() });
    }
    const g1 = map1.get(r.code_niveau_1)!;
    if (!g1.map2.has(r.code_niveau_2)) {
      g1.map2.set(r.code_niveau_2, { libelle: r.libelle_niveau_2, items: [] });
    }
    g1.map2.get(r.code_niveau_2)!.items.push(r);
  }
  const result: GroupedRefs[] = [];
  for (const [code1, val1] of map1) {
    const niveau2 = [];
    for (const [code2, val2] of val1.map2) {
      niveau2.push({ code_niveau_2: code2, libelle_niveau_2: val2.libelle, items: val2.items });
    }
    result.push({ code_niveau_1: code1, libelle_niveau_1: val1.libelle, niveau2 });
  }
  return result;
}

type SelectionItem = {
  ref: EquipmentReference;
  etat: string;
  quantite: string;
  commentaire: string;
};

export function BuildingTechniquePage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [selectedBuildingId, setSelectedBuildingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [showSelector, setShowSelector] = useState(false);
  const [expandedL1, setExpandedL1] = useState<Set<string>>(new Set());
  const [expandedL2, setExpandedL2] = useState<Set<string>>(new Set());
  const [selection, setSelection] = useState<Map<number, SelectionItem>>(new Map());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editEtat, setEditEtat] = useState("");
  const [editQuantite, setEditQuantite] = useState("");
  const [editCommentaire, setEditCommentaire] = useState("");
  const [refSearch, setRefSearch] = useState("");
  const [techniqueScope, setTechniqueScope] = useState<TechniqueScope>("all");

  const buildingsQuery = useQuery({
    queryKey: ["buildings", token],
    queryFn: () => fetchBuildings(token as string),
    enabled: Boolean(token),
  });

  const summariesQuery = useQuery({
    queryKey: ["equipment-summaries", token],
    queryFn: () => fetchEquipmentSummaries(token as string),
    enabled: Boolean(token),
  });

  const refsQuery = useQuery({
    queryKey: ["equipment-references", token],
    queryFn: () => fetchEquipmentReferences(token as string),
    enabled: Boolean(token),
  });

  const equipmentsQuery = useQuery({
    queryKey: ["building-equipments", token, selectedBuildingId],
    queryFn: () => fetchBuildingEquipments(token as string, selectedBuildingId!),
    enabled: Boolean(token) && selectedBuildingId !== null,
  });

  const summariesMap = useMemo(() => {
    const map = new Map<number, BuildingEquipmentSummary>();
    for (const s of summariesQuery.data ?? []) {
      map.set(s.building_id, s);
    }
    return map;
  }, [summariesQuery.data]);

  const filteredBuildings = useMemo(() => {
    const q = search.trim().toLowerCase();
    const buildings = (buildingsQuery.data ?? []) as Building[];
    if (!q) return buildings;
    return buildings.filter((b) =>
      [b.nom_batiment, buildAddressLine(b), b.nom_commune].filter(Boolean).some((v) => String(v).toLowerCase().includes(q)),
    );
  }, [buildingsQuery.data, search]);

  const referenceCounts = useMemo(() => {
    const refs = refsQuery.data ?? [];
    return {
      all: refs.length,
      cvc: refs.filter((ref) => matchesTechniqueScope(ref, "cvc")).length,
      enveloppe: refs.filter((ref) => matchesTechniqueScope(ref, "enveloppe")).length,
    };
  }, [refsQuery.data]);

  const grouped = useMemo(() => {
    const refs = refsQuery.data ?? [];
    return groupReferences(refs.filter((ref) => matchesTechniqueScope(ref, techniqueScope)));
  }, [refsQuery.data, techniqueScope]);

  const visibleEquipments = useMemo(() => {
    const equipments = equipmentsQuery.data ?? [];
    return equipments.filter((eq) => matchesTechniqueScope(eq.equipment_ref, techniqueScope));
  }, [equipmentsQuery.data, techniqueScope]);

  const existingRefIds = useMemo(() => {
    const set = new Set<number>();
    for (const eq of equipmentsQuery.data ?? []) {
      set.add(eq.equipment_ref_id);
    }
    return set;
  }, [equipmentsQuery.data]);

  const bulkMutation = useMutation({
    mutationFn: (items: { equipment_ref_id: number; etat: string; quantite: string; commentaire?: string }[]) =>
      bulkCreateBuildingEquipments(token as string, selectedBuildingId!, { items }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["building-equipments"] });
      queryClient.invalidateQueries({ queryKey: ["equipment-summaries"] });
      setSelection(new Map());
      setShowSelector(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ equipmentId, payload }: { equipmentId: number; payload: { etat?: string; quantite?: string; commentaire?: string } }) =>
      updateBuildingEquipmentRequest(token as string, selectedBuildingId!, equipmentId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["building-equipments"] });
      queryClient.invalidateQueries({ queryKey: ["equipment-summaries"] });
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (equipmentId: number) => deleteBuildingEquipmentRequest(token as string, selectedBuildingId!, equipmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["building-equipments"] });
      queryClient.invalidateQueries({ queryKey: ["equipment-summaries"] });
    },
  });

  function toggleL1(code: string) {
    setExpandedL1((prev) => {
      const next = new Set(prev);
      next.has(code) ? next.delete(code) : next.add(code);
      return next;
    });
  }

  function toggleL2(code: string) {
    setExpandedL2((prev) => {
      const next = new Set(prev);
      next.has(code) ? next.delete(code) : next.add(code);
      return next;
    });
  }

  function toggleRefSelection(ref: EquipmentReference) {
    setSelection((prev) => {
      const next = new Map(prev);
      if (next.has(ref.id)) {
        next.delete(ref.id);
      } else {
        next.set(ref.id, { ref, etat: "moyen", quantite: "moyenne", commentaire: "" });
      }
      return next;
    });
  }

  function updateSelectionItem(refId: number, field: string, value: string) {
    setSelection((prev) => {
      const next = new Map(prev);
      const item = next.get(refId);
      if (item) {
        next.set(refId, { ...item, [field]: value });
      }
      return next;
    });
  }

  function handleBulkSubmit() {
    const items = Array.from(selection.values()).map((s) => ({
      equipment_ref_id: s.ref.id,
      etat: s.etat,
      quantite: s.quantite,
      commentaire: s.commentaire || undefined,
    }));
    if (items.length === 0) return;
    bulkMutation.mutate(items);
  }

  function switchTechniqueScope(scope: TechniqueScope) {
    setTechniqueScope(scope);
    setShowSelector(false);
    setSelection(new Map());
    setEditingId(null);
    setRefSearch("");
  }

  function startEdit(eq: BuildingEquipmentType) {
    setEditingId(eq.id);
    setEditEtat(eq.etat);
    setEditQuantite(eq.quantite);
    setEditCommentaire(eq.commentaire || "");
  }

  function saveEdit() {
    if (editingId === null) return;
    updateMutation.mutate({
      equipmentId: editingId,
      payload: { etat: editEtat, quantite: editQuantite, commentaire: editCommentaire },
    });
  }

  const selectedBuilding = filteredBuildings.find((b) => b.id === selectedBuildingId) ?? null;
  const scopeConfig = TECHNIQUE_SCOPE_CONFIG[techniqueScope];

  if (!token) {
    return (
      <section className="panel stack-lg">
        <h2>Gestion Technique</h2>
        <p>Connecte-toi pour accéder à la gestion technique des bâtiments.</p>
      </section>
    );
  }

  return (
    <section className="panel stack-lg">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Bâtiments</p>
          <h2>Gestion Technique</h2>
          <p>Inventaire technique des équipements et matériaux de chaque bâtiment.</p>
        </div>
        <div className="buildings-header-actions">
          <Link className="secondary-link" to="/buildings">Retour aux bâtiments</Link>
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        {(["all", "cvc", "enveloppe"] as TechniqueScope[]).map((scope) => {
          const isActive = techniqueScope === scope;
          return (
            <button
              key={scope}
              type="button"
              className={isActive ? "primary-button" : "secondary-button"}
              style={{ padding: "6px 12px", fontSize: "0.85rem" }}
              onClick={() => switchTechniqueScope(scope)}
            >
              {TECHNIQUE_SCOPE_CONFIG[scope].label}
              <span style={{ marginLeft: 6, opacity: 0.75 }}>({referenceCounts[scope]})</span>
            </button>
          );
        })}
        <span style={{ color: SUBTLE_TEXT, fontSize: "0.82rem" }}>
          Source SYPEMI : CVC = A.2.3 ; Enveloppe = A.1
        </span>
      </div>

      <div className="buildings-list-layout">
        {/* Sidebar — Building list */}
        <aside className="buildings-sidebar" style={{ minWidth: 320 }}>
          <div className="section-block">
            <h3>Bâtiments</h3>
            <label className="field">
              <span>Recherche</span>
              <input type="text" value={search} onChange={(e: ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)} />
            </label>
            <div className="resource-list" style={{ maxHeight: 600, overflowY: "auto" }}>
              {filteredBuildings.map((b) => {
                const summary = summariesMap.get(b.id);
                const counts = summary?.counts;
                const score = counts?.score_sante ?? null;
                const isActive = selectedBuildingId === b.id;
                return (
                  <article
                    key={b.id}
                    className={`resource-card ${isActive ? "resource-card-active" : ""}`}
                    onClick={() => { setSelectedBuildingId(b.id); setShowSelector(false); setEditingId(null); }}
                    style={{ cursor: "pointer" }}
                  >
                    <div className="resource-card-header">
                      <div>
                        <h3>{b.nom_batiment || `Bâtiment #${b.id}`}</h3>
                        <p style={{ fontSize: "0.85rem", color: SUBTLE_TEXT }}>{buildAddressLine(b)}</p>
                      </div>
                      {counts && counts.total > 0 && (
                        <span
                          className="resource-badge"
                          style={{ backgroundColor: scoreColor(score), color: "#fff", fontWeight: 700 }}
                        >
                          {score !== null ? `${score}%` : "—"}
                        </span>
                      )}
                    </div>
                    {counts && counts.total > 0 && (
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                        {counts.neuf > 0 && <span style={{ fontSize: "0.75rem", padding: "2px 6px", borderRadius: 4, background: ETAT_BG.neuf, color: ETAT_COLORS.neuf }}>{counts.neuf} neuf</span>}
                        {counts.moyen > 0 && <span style={{ fontSize: "0.75rem", padding: "2px 6px", borderRadius: 4, background: ETAT_BG.moyen, color: ETAT_COLORS.moyen }}>{counts.moyen} moyen</span>}
                        {counts.degrade > 0 && <span style={{ fontSize: "0.75rem", padding: "2px 6px", borderRadius: 4, background: ETAT_BG.degrade, color: ETAT_COLORS.degrade }}>{counts.degrade} dégradé</span>}
                        {counts.obsolete > 0 && <span style={{ fontSize: "0.75rem", padding: "2px 6px", borderRadius: 4, background: ETAT_BG.obsolete, color: ETAT_COLORS.obsolete }}>{counts.obsolete} obsolète</span>}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          </div>
        </aside>

        {/* Main content — Equipment view */}
        <div className="buildings-main-content" style={{ flex: 1 }}>
          {!selectedBuilding && (
            <div className="empty-state">
              <strong>Sélectionne un bâtiment</strong>
              <span>Clique sur un bâtiment dans la liste pour gérer son inventaire technique.</span>
            </div>
          )}

          {selectedBuilding && !showSelector && (
            <div className="section-block">
              <div className="section-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h3>{selectedBuilding.nom_batiment || `Bâtiment #${selectedBuilding.id}`}</h3>
                  <p>
                    {scopeConfig.title} — {visibleEquipments.length} {scopeConfig.emptyLabel}{visibleEquipments.length > 1 ? "s" : ""}
                  </p>
                </div>
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => { setShowSelector(true); setSelection(new Map()); }}
                >
                  + Ajouter {techniqueScope === "all" ? "des éléments" : `des éléments ${scopeConfig.shortLabel}`}
                </button>
              </div>

              {equipmentsQuery.isLoading && <p>Chargement...</p>}

              {!equipmentsQuery.isLoading && (equipmentsQuery.data?.length ?? 0) === 0 && (
                <div className="empty-state">
                  <strong>Aucun équipement assigné</strong>
                  <span>Clique sur "Ajouter des équipements" pour constituer l'inventaire technique.</span>
                </div>
              )}

              {!equipmentsQuery.isLoading && (equipmentsQuery.data?.length ?? 0) > 0 && visibleEquipments.length === 0 && (
                <div className="empty-state">
                  <strong>Aucun {scopeConfig.emptyLabel}</strong>
                  <span>Les éléments déjà saisis sont dans un autre lot du référentiel.</span>
                </div>
              )}

              {visibleEquipments.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {visibleEquipments.map((eq) => {
                    const ref = eq.equipment_ref;
                    const isEditing = editingId === eq.id;
                    return (
                      <div
                        key={eq.id}
                        style={{
                          border: `1px solid ${NEUTRAL_BORDER}`,
                          borderRadius: 8,
                          padding: 12,
                          borderLeft: `4px solid ${ETAT_COLORS[eq.etat] || SUBTLE_TEXT}`,
                          background: "rgba(15, 23, 42, 0.3)",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                          <div>
                            <strong>{ref?.equipement ?? `Ref #${eq.equipment_ref_id}`}</strong>
                            <p style={{ fontSize: "0.8rem", color: SUBTLE_TEXT, margin: "2px 0" }}>
                              {ref?.libelle_niveau_2} {ref?.niveau_3 ? `› ${ref.niveau_3}` : ""}
                            </p>
                          </div>
                          <span
                            style={{
                              padding: "2px 10px",
                              borderRadius: 12,
                              fontSize: "0.8rem",
                              fontWeight: 600,
                              background: ETAT_BG[eq.etat] || NEUTRAL_BG_DARKER,
                              color: ETAT_COLORS[eq.etat] || SUBTLE_TEXT,
                              border: `1px solid ${ETAT_BORDER[eq.etat] || NEUTRAL_BORDER}`,
                            }}
                          >
                            {ETAT_LABELS[eq.etat] || eq.etat}
                          </span>
                        </div>

                        {!isEditing && (
                          <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: "0.85rem", color: "#cbd5e1", flexWrap: "wrap", alignItems: "center" }}>
                            <span>Quantité : <strong>{QUANTITE_LABELS[eq.quantite] || eq.quantite}</strong></span>
                            <span>Durée restante : <strong>{eq.duree_vie_restante} ans</strong></span>
                            {ref?.sypemi_reference_annees && <span style={{ color: SUBTLE_TEXT }}>Réf : {ref.sypemi_reference_annees} ans</span>}
                            {eq.commentaire && <span style={{ fontStyle: "italic" }}>{eq.commentaire}</span>}
                            <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                              <button type="button" className="secondary-button" style={{ padding: "2px 8px", fontSize: "0.8rem" }} onClick={() => startEdit(eq)}>Modifier</button>
                              <button
                                type="button"
                                className="danger-button"
                                style={{ padding: "2px 8px", fontSize: "0.8rem" }}
                                onClick={() => { if (window.confirm("Retirer cet équipement ?")) deleteMutation.mutate(eq.id); }}
                              >
                                Retirer
                              </button>
                            </div>
                          </div>
                        )}

                        {isEditing && (
                          <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
                            <label className="field" style={{ minWidth: 120 }}>
                              <span>État</span>
                              <select value={editEtat} onChange={(e) => setEditEtat(e.target.value)}>
                                <option value="neuf">Neuf</option>
                                <option value="moyen">Moyen</option>
                                <option value="degrade">Dégradé</option>
                                <option value="obsolete">Obsolète</option>
                              </select>
                            </label>
                            <label className="field" style={{ minWidth: 120 }}>
                              <span>Quantité</span>
                              <select value={editQuantite} onChange={(e) => setEditQuantite(e.target.value)}>
                                <option value="faible">Faible</option>
                                <option value="moyenne">Moyenne</option>
                                <option value="elevee">Élevée</option>
                              </select>
                            </label>
                            <label className="field" style={{ flex: 1, minWidth: 160 }}>
                              <span>Commentaire</span>
                              <input type="text" value={editCommentaire} onChange={(e) => setEditCommentaire(e.target.value)} />
                            </label>
                            <button type="button" className="primary-button" style={{ padding: "6px 12px" }} onClick={saveEdit} disabled={updateMutation.isPending}>
                              {updateMutation.isPending ? "..." : "Enregistrer"}
                            </button>
                            <button type="button" className="secondary-button" style={{ padding: "6px 12px" }} onClick={() => setEditingId(null)}>
                              Annuler
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Equipment selector (hierarchical tree) */}
          {selectedBuilding && showSelector && (
            <div className="section-block">
              <div className="section-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h3>Sélection {techniqueScope === "all" ? "des éléments" : scopeConfig.shortLabel}</h3>
                  <p>
                    {referenceCounts[techniqueScope]} références disponibles dans ce lot.
                  </p>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button type="button" className="secondary-button" onClick={() => setShowSelector(false)}>
                    Annuler
                  </button>
                  <button
                    type="button"
                    className="primary-button"
                    onClick={handleBulkSubmit}
                    disabled={selection.size === 0 || bulkMutation.isPending}
                  >
                    {bulkMutation.isPending ? "Enregistrement..." : `Valider (${selection.size})`}
                  </button>
                </div>
              </div>

              <label className="field" style={{ marginBottom: 12 }}>
                <span>Rechercher</span>
                <input
                  type="text"
                  value={refSearch}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setRefSearch(e.target.value)}
                  placeholder={techniqueScope === "cvc" ? "Ex: chaudière, ventilation, climatisation..." : techniqueScope === "enveloppe" ? "Ex: toiture, façade, menuiserie..." : "Ex: chaudière, toiture, ascenseur..."}
                />
              </label>

              {/* Selected items summary */}
              {selection.size > 0 && (
                <div style={{ marginBottom: 16, padding: 12, background: "rgba(34, 197, 94, 0.12)", border: "1px solid rgba(34, 197, 94, 0.4)", borderRadius: 8 }}>
                  <strong style={{ fontSize: "0.9rem" }}>{selection.size} équipement(s) sélectionné(s)</strong>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
                    {Array.from(selection.values()).map((s) => (
                      <div key={s.ref.id} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", fontSize: "0.85rem" }}>
                        <span style={{ fontWeight: 600, minWidth: 200 }}>{s.ref.equipement}</span>
                        <select value={s.etat} onChange={(e) => updateSelectionItem(s.ref.id, "etat", e.target.value)} style={{ padding: "2px 4px" }}>
                          <option value="neuf">Neuf</option>
                          <option value="moyen">Moyen</option>
                          <option value="degrade">Dégradé</option>
                          <option value="obsolete">Obsolète</option>
                        </select>
                        <select value={s.quantite} onChange={(e) => updateSelectionItem(s.ref.id, "quantite", e.target.value)} style={{ padding: "2px 4px" }}>
                          <option value="faible">Faible</option>
                          <option value="moyenne">Moyenne</option>
                          <option value="elevee">Élevée</option>
                        </select>
                        <input
                          type="text"
                          placeholder="Commentaire..."
                          value={s.commentaire}
                          onChange={(e) => updateSelectionItem(s.ref.id, "commentaire", e.target.value)}
                          style={{ flex: 1, minWidth: 120, padding: "2px 6px" }}
                        />
                        <button type="button" style={{ padding: "2px 6px", cursor: "pointer", border: "1px solid rgba(220, 38, 38, 0.4)", borderRadius: 4, background: "rgba(220, 38, 38, 0.18)", color: "#fca5a5", fontSize: "0.8rem" }} onClick={() => toggleRefSelection(s.ref)}>
                          Retirer
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Hierarchical tree */}
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {grouped.length === 0 && (
                  <div className="empty-state">
                    <strong>Aucune référence</strong>
                    <span>Le lot sélectionné ne contient aucune ligne dans le référentiel chargé.</span>
                  </div>
                )}
                {grouped.map((g1) => {
                  const q = refSearch.trim().toLowerCase();
                  const matchedN2 = g1.niveau2.filter((n2) => {
                    if (!q) return true;
                    return n2.items.some(
                      (r) =>
                        r.equipement.toLowerCase().includes(q) ||
                        n2.libelle_niveau_2.toLowerCase().includes(q) ||
                        (r.niveau_3 && r.niveau_3.toLowerCase().includes(q)),
                    );
                  });
                  if (matchedN2.length === 0) return null;
                  const isOpen1 = expandedL1.has(g1.code_niveau_1) || q.length > 0;
                  return (
                    <div key={g1.code_niveau_1}>
                      <div
                        onClick={() => toggleL1(g1.code_niveau_1)}
                        style={{ cursor: "pointer", padding: "8px 12px", background: NEUTRAL_BG_LIGHT, border: `1px solid ${NEUTRAL_BORDER}`, borderRadius: 6, fontWeight: 700, display: "flex", justifyContent: "space-between" }}
                      >
                        <span>{g1.code_niveau_1} — {g1.libelle_niveau_1}</span>
                        <span>{isOpen1 ? "▼" : "▶"}</span>
                      </div>
                      {isOpen1 && (
                        <div style={{ paddingLeft: 16 }}>
                          {matchedN2.map((n2) => {
                            const isOpen2 = expandedL2.has(n2.code_niveau_2) || q.length > 0;
                            const filteredItems = q
                              ? n2.items.filter(
                                  (r) =>
                                    r.equipement.toLowerCase().includes(q) ||
                                    n2.libelle_niveau_2.toLowerCase().includes(q) ||
                                    (r.niveau_3 && r.niveau_3.toLowerCase().includes(q)),
                                )
                              : n2.items;
                            return (
                              <div key={n2.code_niveau_2} style={{ marginTop: 4 }}>
                                <div
                                  onClick={() => toggleL2(n2.code_niveau_2)}
                                  style={{ cursor: "pointer", padding: "6px 10px", background: NEUTRAL_BG_DARKER, borderRadius: 4, fontWeight: 600, fontSize: "0.9rem", display: "flex", justifyContent: "space-between" }}
                                >
                                  <span>{n2.code_niveau_2} — {n2.libelle_niveau_2}</span>
                                  <span style={{ fontSize: "0.8rem", color: SUBTLE_TEXT }}>{filteredItems.length} éléments {isOpen2 ? "▼" : "▶"}</span>
                                </div>
                                {isOpen2 && (
                                  <div style={{ paddingLeft: 12, marginTop: 4 }}>
                                    {filteredItems.map((r) => {
                                      const isSelected = selection.has(r.id);
                                      const alreadyAssigned = existingRefIds.has(r.id);
                                      return (
                                        <label
                                          key={r.id}
                                          style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: 8,
                                            padding: "4px 8px",
                                            borderRadius: 4,
                                            cursor: alreadyAssigned ? "default" : "pointer",
                                            background: isSelected
                                              ? "rgba(59, 130, 246, 0.18)"
                                              : alreadyAssigned
                                                ? NEUTRAL_BG_DARKER
                                                : "transparent",
                                            opacity: alreadyAssigned ? 0.5 : 1,
                                            fontSize: "0.88rem",
                                          }}
                                        >
                                          <input
                                            type="checkbox"
                                            checked={isSelected}
                                            disabled={alreadyAssigned}
                                            onChange={() => toggleRefSelection(r)}
                                          />
                                          <span style={{ flex: 1 }}>
                                            {r.equipement}
                                            {r.niveau_3 && <span style={{ color: SUBTLE_TEXT, fontSize: "0.8rem" }}> ({r.niveau_3})</span>}
                                          </span>
                                          <span style={{ fontSize: "0.75rem", color: SUBTLE_TEXT }}>
                                            {r.sypemi_reference_annees ? `${r.sypemi_reference_annees} ans` : "—"}
                                          </span>
                                          {alreadyAssigned && <span style={{ fontSize: "0.7rem", color: SUBTLE_TEXT }}>déjà assigné</span>}
                                        </label>
                                      );
                                    })}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
