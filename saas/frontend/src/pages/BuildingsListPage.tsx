import { useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { BuildingPortfolioMap } from "../components/BuildingPortfolioMap";
import {
  deleteAllBuildingsRequest,
  fetchAllLocals,
  fetchBuildings,
  fetchSites,
  updateBuildingRequest,
  updateLocalRequest,
  updateSiteRequest,
  type Building,
  type Local,
  type Site,
  type UpdateBuildingPayload,
  type UpdateLocalPayload,
  type UpdateSitePayload,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

// =====================================================================
// Types & helpers
// =====================================================================

type SelectedNode =
  | { type: "site"; id: number }
  | { type: "building"; id: number }
  | { type: "local"; id: number }
  | null;

function buildAddressLine(b: Pick<Building, "numero_voirie" | "nature_voie" | "nom_voie" | "adresse_reconstituee" | "nom_commune">) {
  if (b.adresse_reconstituee) return b.adresse_reconstituee;
  const parts = [b.numero_voirie, b.nature_voie, b.nom_voie].filter(Boolean);
  return parts.length > 0 ? `${parts.join(" ")}, ${b.nom_commune}` : b.nom_commune;
}

function siteCentroid(buildings: Building[]): { lat: number; lon: number } | null {
  const geocoded = buildings.filter((b) => b.latitude != null && b.longitude != null);
  if (geocoded.length === 0) return null;
  const lat = geocoded.reduce((acc, b) => acc + (b.latitude as number), 0) / geocoded.length;
  const lon = geocoded.reduce((acc, b) => acc + (b.longitude as number), 0) / geocoded.length;
  return { lat, lon };
}

// =====================================================================
// Composant principal
// =====================================================================

export function BuildingsListPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [selectedNode, setSelectedNode] = useState<SelectedNode>(null);
  const [expandedSites, setExpandedSites] = useState<Set<number>>(new Set());
  const [expandedBuildings, setExpandedBuildings] = useState<Set<number>>(new Set());
  const [editMode, setEditMode] = useState(false);

  const sitesQuery = useQuery({
    queryKey: ["buildings", "sites", token],
    queryFn: () => fetchSites(token as string),
    enabled: Boolean(token),
  });

  const buildingsQuery = useQuery({
    queryKey: ["buildings", token],
    queryFn: () => fetchBuildings(token as string),
    enabled: Boolean(token),
  });

  const localsQuery = useQuery({
    queryKey: ["buildings", "locals", token],
    queryFn: () => fetchAllLocals(token as string),
    enabled: Boolean(token),
  });

  const deleteAllMutation = useMutation({
    mutationFn: () => deleteAllBuildingsRequest(token as string),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["buildings"] });
      alert(`${data.deleted} bâtiment(s) supprimé(s).`);
    },
  });

  // ---------------------------------------------------------------------
  // Donnees derivees
  // ---------------------------------------------------------------------
  const sites = sitesQuery.data ?? [];
  const buildings = buildingsQuery.data ?? [];
  const locals = localsQuery.data ?? [];

  const buildingsBySiteId = useMemo(() => {
    const map = new Map<number | null, Building[]>();
    for (const b of buildings) {
      const key = b.site_id ?? null;
      const list = map.get(key) ?? [];
      list.push(b);
      map.set(key, list);
    }
    return map;
  }, [buildings]);

  const localsByBuildingId = useMemo(() => {
    const map = new Map<number, Local[]>();
    for (const l of locals) {
      const list = map.get(l.building_id) ?? [];
      list.push(l);
      map.set(l.building_id, list);
    }
    return map;
  }, [locals]);

  // Filtre de recherche
  const lowerSearch = search.trim().toLowerCase();
  const matchesSearch = (text: string | null | undefined) => !lowerSearch || (text ?? "").toLowerCase().includes(lowerSearch);

  const visibleSites = useMemo(() => {
    if (!lowerSearch) return sites;
    return sites.filter((s) => {
      if (matchesSearch(s.nom_site) || matchesSearch(s.adresse)) return true;
      const childBuildings = buildingsBySiteId.get(s.id) ?? [];
      return childBuildings.some(
        (b) =>
          matchesSearch(b.nom_batiment) ||
          matchesSearch(buildAddressLine(b)) ||
          matchesSearch(b.dgfip_reference_norm) ||
          (localsByBuildingId.get(b.id) ?? []).some((l) => matchesSearch(l.nom_local)),
      );
    });
  }, [sites, lowerSearch, buildingsBySiteId, localsByBuildingId]);

  const orphanBuildings = useMemo(
    () => (buildingsBySiteId.get(null) ?? []).filter((b) => matchesSearch(b.nom_batiment) || matchesSearch(buildAddressLine(b))),
    [buildingsBySiteId, lowerSearch],
  );

  // Resolution de la selection
  const selectedSite = selectedNode?.type === "site" ? sites.find((s) => s.id === selectedNode.id) ?? null : null;
  const selectedBuilding = selectedNode?.type === "building" ? buildings.find((b) => b.id === selectedNode.id) ?? null : null;
  const selectedLocal = selectedNode?.type === "local" ? locals.find((l) => l.id === selectedNode.id) ?? null : null;
  const selectedLocalParent = selectedLocal ? buildings.find((b) => b.id === selectedLocal.building_id) ?? null : null;

  // Mise en valeur sur la carte
  const highlightedBuildingIds = useMemo(() => {
    if (selectedSite) {
      return (buildingsBySiteId.get(selectedSite.id) ?? []).map((b) => b.id);
    }
    return [];
  }, [selectedSite, buildingsBySiteId]);

  const focusBuilding = selectedBuilding ?? selectedLocalParent;
  const focusLatLon =
    focusBuilding && focusBuilding.latitude != null && focusBuilding.longitude != null
      ? { lat: focusBuilding.latitude, lon: focusBuilding.longitude }
      : selectedSite
        ? siteCentroid(buildingsBySiteId.get(selectedSite.id) ?? [])
        : null;

  const activeMapBuildingId = selectedBuilding?.id ?? selectedLocalParent?.id ?? null;

  // Compteurs
  const geocodedCount = buildings.filter((b) => b.latitude != null && b.longitude != null).length;
  const ignAttachedCount = buildings.filter((b) => b.statut_geocodage === "IGN_VALIDE").length;

  // ---------------------------------------------------------------------
  // Mutations d'edition inline
  // ---------------------------------------------------------------------
  const updateSiteMutation = useMutation({
    mutationFn: ({ siteId, payload }: { siteId: number; payload: UpdateSitePayload }) =>
      updateSiteRequest(token as string, siteId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["buildings", "sites", token] });
      setEditMode(false);
    },
  });

  const updateBuildingMutation = useMutation({
    mutationFn: ({ buildingId, payload }: { buildingId: number; payload: UpdateBuildingPayload }) =>
      updateBuildingRequest(token as string, buildingId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["buildings", token] });
      setEditMode(false);
    },
  });

  const updateLocalMutation = useMutation({
    mutationFn: ({ buildingId, localId, payload }: { buildingId: number; localId: number; payload: UpdateLocalPayload }) =>
      updateLocalRequest(token as string, buildingId, localId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["buildings", "locals", token] });
      setEditMode(false);
    },
  });

  // ---------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------
  function toggleSiteExpand(siteId: number) {
    setExpandedSites((current) => {
      const next = new Set(current);
      if (next.has(siteId)) next.delete(siteId);
      else next.add(siteId);
      return next;
    });
  }

  function toggleBuildingExpand(buildingId: number) {
    setExpandedBuildings((current) => {
      const next = new Set(current);
      if (next.has(buildingId)) next.delete(buildingId);
      else next.add(buildingId);
      return next;
    });
  }

  function selectAndExpand(node: SelectedNode) {
    setSelectedNode(node);
    setEditMode(false);
    if (!node) return;
    if (node.type === "site") {
      setExpandedSites((current) => new Set(current).add(node.id));
    } else if (node.type === "building") {
      const b = buildings.find((x) => x.id === node.id);
      if (b?.site_id) setExpandedSites((current) => new Set(current).add(b.site_id as number));
      setExpandedBuildings((current) => new Set(current).add(node.id));
    } else if (node.type === "local") {
      const l = locals.find((x) => x.id === node.id);
      if (l) {
        const parent = buildings.find((b) => b.id === l.building_id);
        if (parent?.site_id) setExpandedSites((current) => new Set(current).add(parent.site_id as number));
        if (parent) setExpandedBuildings((current) => new Set(current).add(parent.id));
      }
    }
  }

  function handleDeleteAll() {
    const count = buildings.length;
    if (!window.confirm(`Supprimer les ${count} bâtiment(s) de ta ville ? Cette action est irréversible.`)) return;
    deleteAllMutation.mutate();
  }

  // ---------------------------------------------------------------------
  // Garde-fous auth & loading
  // ---------------------------------------------------------------------
  if (!token) {
    return (
      <section className="panel stack-lg">
        <div>
          <h2>Patrimoine</h2>
          <p>Connecte-toi pour consulter ton patrimoine.</p>
        </div>
      </section>
    );
  }

  const totalCount = sites.length + buildings.length + locals.length;

  return (
    <section className="panel stack-lg buildings-workspace-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Patrimoine</p>
          <h2>Mon patrimoine — vue cascade</h2>
          <p>
            Explore l'arborescence Site &gt; Bâtiment &gt; Local. Clique un élément pour voir ses détails et le centrer
            sur la carte. Les bâtiments avec un attachement IGN apparaissent dans une couleur plus foncée.
          </p>
        </div>
        <div className="buildings-header-actions">
          <Link className="secondary-link" to="/buildings">
            Retour aux entrées bâtiments
          </Link>
          <Link className="secondary-link" to="/buildings/create-edit">
            Importer / éditer
          </Link>
          <div className="header-badge">
            <strong>{sites.length}</strong>
            <span>site(s)</span>
          </div>
          <div className="header-badge">
            <strong>{buildings.length}</strong>
            <span>bâtiment(s)</span>
          </div>
          <div className="header-badge">
            <strong>{locals.length}</strong>
            <span>local(aux)</span>
          </div>
          {buildings.length > 0 ? (
            <button type="button" className="danger-button" onClick={handleDeleteAll} disabled={deleteAllMutation.isPending}>
              {deleteAllMutation.isPending ? "Suppression..." : "Supprimer tout"}
            </button>
          ) : null}
        </div>
      </div>

      {sitesQuery.isLoading || buildingsQuery.isLoading || localsQuery.isLoading ? <p>Chargement...</p> : null}

      {totalCount === 0 && !sitesQuery.isLoading ? (
        <div className="empty-state">
          <strong>Aucun patrimoine importé pour le moment.</strong>
          <span>Importe ton fichier patrimonial pour commencer.</span>
          <div className="form-actions">
            <Link className="secondary-link" to="/buildings/create-edit">
              Importer le patrimoine
            </Link>
          </div>
        </div>
      ) : null}

      {totalCount > 0 ? (
        <div className="detail-grid">
          <div className="detail-card">
            <span>Bâtiments géolocalisés</span>
            <strong>{geocodedCount}</strong>
          </div>
          <div className="detail-card">
            <span>Avec attachement IGN</span>
            <strong>{ignAttachedCount}</strong>
          </div>
        </div>
      ) : null}

      {totalCount > 0 ? (
        <div className="buildings-list-layout">
          {/* COLONNE GAUCHE - arborescence cascade */}
          <aside className="buildings-sidebar">
            <div className="section-block buildings-addresses-section">
              <div className="section-heading">
                <h3>Arborescence patrimoine</h3>
                <p>Site &gt; Bâtiment &gt; Local. Clique pour voir le détail.</p>
              </div>
              <label className="field">
                <span>Recherche</span>
                <input
                  type="text"
                  value={search}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)}
                  placeholder="Nom, adresse, parcelle..."
                />
              </label>
              <div className="resource-list buildings-address-list">
                {visibleSites.map((site) => {
                  const isSiteSelected = selectedNode?.type === "site" && selectedNode.id === site.id;
                  const isSiteExpanded = expandedSites.has(site.id);
                  const siteBuildings = buildingsBySiteId.get(site.id) ?? [];
                  return (
                    <div key={`site-${site.id}`} style={{ marginBottom: 4 }}>
                      <div
                        className={`tree-node tree-node-site${isSiteSelected ? " tree-node-active" : ""}`}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "6px 8px",
                          cursor: "pointer",
                          background: isSiteSelected ? "rgba(249, 115, 22, 0.15)" : undefined,
                          borderLeft: isSiteSelected ? "3px solid #f97316" : "3px solid transparent",
                        }}
                      >
                        <span
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleSiteExpand(site.id);
                          }}
                          style={{ cursor: "pointer", userSelect: "none", minWidth: 14 }}
                        >
                          {isSiteExpanded ? "▼" : "▶"}
                        </span>
                        <span style={{ flex: 1 }} onClick={() => selectAndExpand({ type: "site", id: site.id })}>
                          <strong>{site.nom_site}</strong>
                          <span style={{ marginLeft: 6, color: "#6b7280", fontSize: 12 }}>
                            ({siteBuildings.length} bâtiment{siteBuildings.length > 1 ? "s" : ""})
                          </span>
                        </span>
                      </div>
                      {isSiteExpanded ? (
                        <div style={{ marginLeft: 20 }}>
                          {siteBuildings.map((building) => {
                            const isBuildingSelected = selectedNode?.type === "building" && selectedNode.id === building.id;
                            const isBuildingExpanded = expandedBuildings.has(building.id);
                            const buildingLocals = localsByBuildingId.get(building.id) ?? [];
                            const hasIgn = building.statut_geocodage === "IGN_VALIDE";
                            return (
                              <div key={`building-${building.id}`}>
                                <div
                                  style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 6,
                                    padding: "5px 8px",
                                    cursor: "pointer",
                                    background: isBuildingSelected ? "rgba(249, 115, 22, 0.15)" : undefined,
                                    borderLeft: isBuildingSelected ? "3px solid #f97316" : "3px solid transparent",
                                  }}
                                >
                                  <span
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      toggleBuildingExpand(building.id);
                                    }}
                                    style={{ cursor: "pointer", userSelect: "none", minWidth: 14 }}
                                  >
                                    {buildingLocals.length > 0 ? (isBuildingExpanded ? "▼" : "▶") : "·"}
                                  </span>
                                  <span style={{ flex: 1 }} onClick={() => selectAndExpand({ type: "building", id: building.id })}>
                                    <span style={{ color: hasIgn ? "#15803d" : undefined, fontWeight: hasIgn ? 600 : undefined }}>
                                      {hasIgn ? "● " : "○ "}
                                    </span>
                                    {building.nom_batiment || `Bâtiment #${building.id}`}
                                    {buildingLocals.length > 0 ? (
                                      <span style={{ marginLeft: 6, color: "#6b7280", fontSize: 12 }}>
                                        ({buildingLocals.length} local{buildingLocals.length > 1 ? "aux" : ""})
                                      </span>
                                    ) : null}
                                  </span>
                                </div>
                                {isBuildingExpanded ? (
                                  <div style={{ marginLeft: 20 }}>
                                    {buildingLocals.map((local) => {
                                      const isLocalSelected = selectedNode?.type === "local" && selectedNode.id === local.id;
                                      return (
                                        <div
                                          key={`local-${local.id}`}
                                          onClick={() => selectAndExpand({ type: "local", id: local.id })}
                                          style={{
                                            padding: "4px 8px",
                                            cursor: "pointer",
                                            color: "#4b5563",
                                            fontSize: 13,
                                            background: isLocalSelected ? "rgba(249, 115, 22, 0.15)" : undefined,
                                            borderLeft: isLocalSelected ? "3px solid #f97316" : "3px solid transparent",
                                          }}
                                        >
                                          ◇ {local.nom_local}
                                          {local.niveau ? <span style={{ color: "#9ca3af", marginLeft: 6 }}>· niv. {local.niveau}</span> : null}
                                        </div>
                                      );
                                    })}
                                  </div>
                                ) : null}
                              </div>
                            );
                          })}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
                {orphanBuildings.length > 0 ? (
                  <div style={{ marginTop: 12 }}>
                    <div style={{ padding: "6px 8px", color: "#6b7280", fontSize: 12, fontStyle: "italic" }}>
                      Bâtiments sans site rattaché ({orphanBuildings.length})
                    </div>
                    {orphanBuildings.map((building) => {
                      const isSelected = selectedNode?.type === "building" && selectedNode.id === building.id;
                      const hasIgn = building.statut_geocodage === "IGN_VALIDE";
                      return (
                        <div
                          key={`orphan-${building.id}`}
                          onClick={() => selectAndExpand({ type: "building", id: building.id })}
                          style={{
                            padding: "5px 8px",
                            cursor: "pointer",
                            background: isSelected ? "rgba(249, 115, 22, 0.15)" : undefined,
                            borderLeft: isSelected ? "3px solid #f97316" : "3px solid transparent",
                          }}
                        >
                          <span style={{ color: hasIgn ? "#15803d" : undefined, fontWeight: hasIgn ? 600 : undefined }}>
                            {hasIgn ? "● " : "○ "}
                          </span>
                          {building.nom_batiment || `Bâtiment #${building.id}`}
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            </div>
          </aside>

          {/* COLONNE DROITE - carte + panneau detail */}
          <div className="buildings-main-content">
            <div className="section-block">
              <div className="section-heading">
                <h3>Carte</h3>
                <p>
                  ● vert foncé = IGN attaché · ○ bleu clair = non attaché · Orange = sélection courante · Vert foncé épais = bâtiment d'un site sélectionné AVEC IGN
                </p>
              </div>
              <BuildingPortfolioMap
                buildings={buildings}
                activeBuildingId={activeMapBuildingId}
                onSelectBuildingId={(id) => selectAndExpand({ type: "building", id })}
                highlightedBuildingIds={highlightedBuildingIds}
                focusLatLon={focusLatLon}
              />
            </div>

            <PatrimonyDetailPanel
              selectedSite={selectedSite}
              selectedBuilding={selectedBuilding}
              selectedLocal={selectedLocal}
              selectedLocalParent={selectedLocalParent}
              siteBuildings={selectedSite ? buildingsBySiteId.get(selectedSite.id) ?? [] : []}
              buildingLocals={selectedBuilding ? localsByBuildingId.get(selectedBuilding.id) ?? [] : []}
              editMode={editMode}
              onToggleEdit={() => setEditMode((v) => !v)}
              onSaveSite={(payload) => selectedSite && updateSiteMutation.mutate({ siteId: selectedSite.id, payload })}
              onSaveBuilding={(payload) =>
                selectedBuilding && updateBuildingMutation.mutate({ buildingId: selectedBuilding.id, payload })
              }
              onSaveLocal={(payload) =>
                selectedLocal &&
                updateLocalMutation.mutate({ buildingId: selectedLocal.building_id, localId: selectedLocal.id, payload })
              }
              savePending={
                updateSiteMutation.isPending || updateBuildingMutation.isPending || updateLocalMutation.isPending
              }
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}

// =====================================================================
// Composant : panneau detail inline
// =====================================================================

type DetailPanelProps = {
  selectedSite: Site | null;
  selectedBuilding: Building | null;
  selectedLocal: Local | null;
  selectedLocalParent: Building | null;
  siteBuildings: Building[];
  buildingLocals: Local[];
  editMode: boolean;
  onToggleEdit: () => void;
  onSaveSite: (payload: UpdateSitePayload) => void;
  onSaveBuilding: (payload: UpdateBuildingPayload) => void;
  onSaveLocal: (payload: UpdateLocalPayload) => void;
  savePending: boolean;
};

function PatrimonyDetailPanel(props: DetailPanelProps) {
  const {
    selectedSite,
    selectedBuilding,
    selectedLocal,
    selectedLocalParent,
    siteBuildings,
    buildingLocals,
    editMode,
    onToggleEdit,
    onSaveSite,
    onSaveBuilding,
    onSaveLocal,
    savePending,
  } = props;

  if (!selectedSite && !selectedBuilding && !selectedLocal) {
    return (
      <div className="section-block">
        <div className="empty-state">
          <strong>Sélectionne un élément dans l'arborescence pour voir ses détails ici.</strong>
        </div>
      </div>
    );
  }

  if (selectedSite) {
    return (
      <SiteDetail
        site={selectedSite}
        childBuildings={siteBuildings}
        editMode={editMode}
        onToggleEdit={onToggleEdit}
        onSave={onSaveSite}
        savePending={savePending}
      />
    );
  }

  if (selectedBuilding) {
    return (
      <BuildingDetail
        building={selectedBuilding}
        childLocals={buildingLocals}
        editMode={editMode}
        onToggleEdit={onToggleEdit}
        onSave={onSaveBuilding}
        savePending={savePending}
      />
    );
  }

  if (selectedLocal && selectedLocalParent) {
    return (
      <LocalDetail
        local={selectedLocal}
        parent={selectedLocalParent}
        editMode={editMode}
        onToggleEdit={onToggleEdit}
        onSave={onSaveLocal}
        savePending={savePending}
      />
    );
  }

  return null;
}

// =====================================================================
// Detail Site
// =====================================================================

function SiteDetail({
  site,
  childBuildings,
  editMode,
  onToggleEdit,
  onSave,
  savePending,
}: {
  site: Site;
  childBuildings: Building[];
  editMode: boolean;
  onToggleEdit: () => void;
  onSave: (payload: UpdateSitePayload) => void;
  savePending: boolean;
}) {
  const [nomSite, setNomSite] = useState(site.nom_site);
  const [adresse, setAdresse] = useState(site.adresse ?? "");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSave({ nom_site: nomSite, adresse: adresse || null });
  }

  return (
    <div className="section-block">
      <div className="panel-header">
        <div className="section-heading">
          <h3>📍 Site sélectionné</h3>
          <p>{childBuildings.length} bâtiment(s) rattaché(s)</p>
        </div>
        <button type="button" className="secondary-button" onClick={onToggleEdit}>
          {editMode ? "Annuler l'édition" : "Modifier"}
        </button>
      </div>
      {editMode ? (
        <form className="form" onSubmit={handleSubmit}>
          <div className="form-grid">
            <label className="field">
              <span>Nom du site</span>
              <input type="text" value={nomSite} onChange={(e) => setNomSite(e.target.value)} required />
            </label>
            <label className="field">
              <span>Adresse</span>
              <input type="text" value={adresse} onChange={(e) => setAdresse(e.target.value)} />
            </label>
          </div>
          <div className="form-actions">
            <button type="submit" disabled={savePending}>
              {savePending ? "Enregistrement..." : "Enregistrer le site"}
            </button>
          </div>
        </form>
      ) : (
        <>
          <div className="detail-grid">
            <div className="detail-card">
              <span>Nom du site</span>
              <strong>{site.nom_site}</strong>
            </div>
            <div className="detail-card">
              <span>Adresse</span>
              <strong>{site.adresse || "Non renseignée"}</strong>
            </div>
            <div className="detail-card">
              <span>Bâtiments rattachés</span>
              <strong>{childBuildings.length}</strong>
            </div>
            <div className="detail-card">
              <span>Source</span>
              <strong>{site.source_file || "Saisie manuelle"}</strong>
            </div>
          </div>
          {childBuildings.length > 0 ? (
            <div className="section-block">
              <div className="section-heading">
                <h4>Bâtiments rattachés à ce site</h4>
              </div>
              <ul style={{ paddingLeft: 20 }}>
                {childBuildings.map((b) => (
                  <li key={b.id}>
                    {b.nom_batiment || `Bâtiment #${b.id}`}
                    {b.statut_geocodage === "IGN_VALIDE" ? <span style={{ color: "#15803d", marginLeft: 6 }}>● IGN</span> : null}
                    <span style={{ color: "#6b7280", marginLeft: 6, fontSize: 12 }}>{buildAddressLine(b)}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

// =====================================================================
// Detail Bâtiment
// =====================================================================

function BuildingDetail({
  building,
  childLocals,
  editMode,
  onToggleEdit,
  onSave,
  savePending,
}: {
  building: Building;
  childLocals: Local[];
  editMode: boolean;
  onToggleEdit: () => void;
  onSave: (payload: UpdateBuildingPayload) => void;
  savePending: boolean;
}) {
  const [nomBatiment, setNomBatiment] = useState(building.nom_batiment ?? "");
  const [adresseReconstituee, setAdresseReconstituee] = useState(building.adresse_reconstituee ?? "");
  const [nomCommune, setNomCommune] = useState(building.nom_commune);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSave({
      nom_batiment: nomBatiment || null,
      adresse_reconstituee: adresseReconstituee || null,
      nom_commune: nomCommune,
    });
  }

  return (
    <div className="section-block">
      <div className="panel-header">
        <div className="section-heading">
          <h3>🏢 Bâtiment sélectionné</h3>
          <p>
            {building.statut_geocodage === "IGN_VALIDE" ? "Attachement IGN validé · " : "IGN non attaché · "}
            {childLocals.length} local(aux) rattaché(s)
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button type="button" className="secondary-button" onClick={onToggleEdit}>
            {editMode ? "Annuler l'édition" : "Modifier"}
          </button>
          <Link className="secondary-link" to={`/buildings/${building.id}`}>
            Ouvrir la fiche complète →
          </Link>
        </div>
      </div>
      {editMode ? (
        <form className="form" onSubmit={handleSubmit}>
          <div className="form-grid">
            <label className="field">
              <span>Nom du bâtiment</span>
              <input type="text" value={nomBatiment} onChange={(e) => setNomBatiment(e.target.value)} />
            </label>
            <label className="field">
              <span>Adresse reconstituée</span>
              <input type="text" value={adresseReconstituee} onChange={(e) => setAdresseReconstituee(e.target.value)} />
            </label>
            <label className="field">
              <span>Commune</span>
              <input type="text" value={nomCommune} onChange={(e) => setNomCommune(e.target.value)} required />
            </label>
          </div>
          <p style={{ color: "#6b7280", fontSize: 12 }}>
            Pour modifier l'attachement IGN/DGFIP, les compteurs, les détails parcellaires : ouvre la fiche complète.
          </p>
          <div className="form-actions">
            <button type="submit" disabled={savePending}>
              {savePending ? "Enregistrement..." : "Enregistrer le bâtiment"}
            </button>
          </div>
        </form>
      ) : (
        <>
          <div className="detail-grid">
            <div className="detail-card">
              <span>Nom</span>
              <strong>{building.nom_batiment || "—"}</strong>
            </div>
            <div className="detail-card">
              <span>Adresse</span>
              <strong>{buildAddressLine(building)}</strong>
            </div>
            <div className="detail-card">
              <span>Commune</span>
              <strong>{building.nom_commune}</strong>
            </div>
            <div className="detail-card">
              <span>Statut géocodage</span>
              <strong>{building.statut_geocodage}</strong>
            </div>
            <div className="detail-card">
              <span>Coordonnées</span>
              <strong>
                {building.latitude != null && building.longitude != null
                  ? `${building.latitude.toFixed(6)}, ${building.longitude.toFixed(6)}`
                  : "Non géolocalisé"}
              </strong>
            </div>
            <div className="detail-card">
              <span>Référence DGFIP</span>
              <strong>{building.dgfip_reference_norm ?? "Non renseignée"}</strong>
            </div>
            <div className="detail-card">
              <span>Source de création</span>
              <strong>{building.source_creation}</strong>
            </div>
            <div className="detail-card">
              <span>Nom IGN retenu</span>
              <strong>{building.ign_name_proposed || building.ign_name || "—"}</strong>
            </div>
          </div>
          {childLocals.length > 0 ? (
            <div className="section-block">
              <div className="section-heading">
                <h4>Locaux rattachés à ce bâtiment</h4>
              </div>
              <ul style={{ paddingLeft: 20 }}>
                {childLocals.map((l) => (
                  <li key={l.id}>
                    {l.nom_local}
                    {l.niveau ? <span style={{ color: "#9ca3af", marginLeft: 6 }}>· niv. {l.niveau}</span> : null}
                    <span style={{ color: "#6b7280", marginLeft: 6, fontSize: 12 }}>{l.type_local}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

// =====================================================================
// Detail Local
// =====================================================================

function LocalDetail({
  local,
  parent,
  editMode,
  onToggleEdit,
  onSave,
  savePending,
}: {
  local: Local;
  parent: Building;
  editMode: boolean;
  onToggleEdit: () => void;
  onSave: (payload: UpdateLocalPayload) => void;
  savePending: boolean;
}) {
  const [nomLocal, setNomLocal] = useState(local.nom_local);
  const [typeLocal, setTypeLocal] = useState(local.type_local);
  const [niveau, setNiveau] = useState(local.niveau ?? "");
  const [surfaceM2, setSurfaceM2] = useState(local.surface_m2?.toString() ?? "");
  const [usage, setUsage] = useState(local.usage ?? "");
  const [statutOccupation, setStatutOccupation] = useState(local.statut_occupation ?? "");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const surface = surfaceM2.trim() ? Number(surfaceM2.replace(",", ".")) : null;
    onSave({
      nom_local: nomLocal,
      type_local: typeLocal,
      niveau: niveau || null,
      surface_m2: Number.isFinite(surface as number) ? (surface as number) : null,
      usage: usage || null,
      statut_occupation: statutOccupation || null,
    });
  }

  return (
    <div className="section-block">
      <div className="panel-header">
        <div className="section-heading">
          <h3>◇ Local sélectionné</h3>
          <p>
            Bâtiment parent : <strong>{parent.nom_batiment || `#${parent.id}`}</strong>
          </p>
        </div>
        <button type="button" className="secondary-button" onClick={onToggleEdit}>
          {editMode ? "Annuler l'édition" : "Modifier"}
        </button>
      </div>
      {editMode ? (
        <form className="form" onSubmit={handleSubmit}>
          <div className="form-grid">
            <label className="field">
              <span>Nom du local</span>
              <input type="text" value={nomLocal} onChange={(e) => setNomLocal(e.target.value)} required />
            </label>
            <label className="field">
              <span>Type</span>
              <input type="text" value={typeLocal} onChange={(e) => setTypeLocal(e.target.value)} required />
            </label>
            <label className="field">
              <span>Niveau</span>
              <input type="text" value={niveau} onChange={(e) => setNiveau(e.target.value)} />
            </label>
            <label className="field">
              <span>Surface (m²)</span>
              <input type="number" step="0.01" value={surfaceM2} onChange={(e) => setSurfaceM2(e.target.value)} />
            </label>
            <label className="field">
              <span>Usage</span>
              <input type="text" value={usage} onChange={(e) => setUsage(e.target.value)} />
            </label>
            <label className="field">
              <span>Statut d'occupation</span>
              <input type="text" value={statutOccupation} onChange={(e) => setStatutOccupation(e.target.value)} />
            </label>
          </div>
          <div className="form-actions">
            <button type="submit" disabled={savePending}>
              {savePending ? "Enregistrement..." : "Enregistrer le local"}
            </button>
          </div>
        </form>
      ) : (
        <div className="detail-grid">
          <div className="detail-card">
            <span>Nom</span>
            <strong>{local.nom_local}</strong>
          </div>
          <div className="detail-card">
            <span>Type</span>
            <strong>{local.type_local}</strong>
          </div>
          <div className="detail-card">
            <span>Niveau</span>
            <strong>{local.niveau || "—"}</strong>
          </div>
          <div className="detail-card">
            <span>Surface (m²)</span>
            <strong>{local.surface_m2 ?? "—"}</strong>
          </div>
          <div className="detail-card">
            <span>Usage</span>
            <strong>{local.usage || "—"}</strong>
          </div>
          <div className="detail-card">
            <span>Statut d'occupation</span>
            <strong>{local.statut_occupation || "—"}</strong>
          </div>
          {local.commentaire ? (
            <div className="detail-card" style={{ gridColumn: "1 / -1" }}>
              <span>Commentaire</span>
              <strong>{local.commentaire}</strong>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
