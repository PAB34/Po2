import { useMemo, useState } from "react";
import type { ChangeEvent, DragEvent, FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { BuildingPortfolioMap } from "../components/BuildingPortfolioMap";
import { BuildingSelectionWorkspace } from "../components/BuildingSelectionWorkspace";
import {
  attachBuildingGeoRequest,
  attachBuildingIgnRequest,
  deleteAllBuildingsRequest,
  fetchAllLocals,
  fetchBuildingNamingLookup,
  fetchBuildings,
  fetchFreeAddressLookup,
  fetchNearbyDgfip,
  fetchSites,
  updateBuildingRequest,
  updateLocalRequest,
  updateSiteRequest,
  type Building,
  type BuildingIgnAttachmentPayload,
  type BuildingNamingLookup,
  type FreeAddressLookup,
  type GeoJsonFeature,
  type Local,
  type NearbyDgfipRow,
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

function buildAttachmentAddress(building: Building): string | null {
  if (building.adresse_reconstituee?.trim()) {
    return building.adresse_reconstituee.trim();
  }
  const parts = [building.numero_voirie, building.nature_voie, building.nom_voie, building.nom_commune].filter(
    (p): p is string => Boolean(p?.trim()),
  );
  return parts.length >= 2 ? parts.join(" ") : null;
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
  // Drag&drop : reparentage Site>Batiment et Batiment>Local depuis l'arborescence.
  const [dragItem, setDragItem] = useState<{ type: "building" | "local"; id: number; sourceParentId: number | null } | null>(null);
  const [dropTargetKey, setDropTargetKey] = useState<string | null>(null);

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
  // Drag & drop : reparentage dans l'arborescence
  // ---------------------------------------------------------------------
  function handleDragStartBuilding(e: DragEvent, building: Building) {
    e.stopPropagation();
    setDragItem({ type: "building", id: building.id, sourceParentId: building.site_id ?? null });
  }

  function handleDragStartLocal(e: DragEvent, local: Local) {
    e.stopPropagation();
    setDragItem({ type: "local", id: local.id, sourceParentId: local.building_id });
  }

  function handleDragEnd() {
    setDragItem(null);
    setDropTargetKey(null);
  }

  function allowDrop(e: DragEvent, targetKey: string, accepts: "building" | "local") {
    if (dragItem?.type !== accepts) return;
    e.preventDefault();
    if (dropTargetKey !== targetKey) setDropTargetKey(targetKey);
  }

  function handleDropOnSite(e: DragEvent, siteId: number) {
    e.preventDefault();
    if (dragItem?.type === "building" && dragItem.sourceParentId !== siteId) {
      updateBuildingMutation.mutate({ buildingId: dragItem.id, payload: { site_id: siteId } });
    }
    handleDragEnd();
  }

  function handleDropOnBuilding(e: DragEvent, buildingId: number) {
    e.preventDefault();
    if (dragItem?.type === "local" && dragItem.sourceParentId !== buildingId) {
      updateLocalMutation.mutate({
        buildingId: dragItem.sourceParentId as number,
        localId: dragItem.id,
        payload: { building_id: buildingId },
      });
    }
    handleDragEnd();
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
        <div className="buildings-workspace">
          {/* COLONNE GAUCHE - arborescence cascade */}
          <aside className="buildings-sidebar">
            <div className="section-block buildings-addresses-section">
              <div className="section-heading">
                <h3>Arborescence patrimoine</h3>
                <p>Site &gt; Bâtiment &gt; Local. Clique pour voir le détail. Glisse un bâtiment vers un site, ou un local vers un bâtiment, pour le rattacher.</p>
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
              <div className="buildings-address-list patrimony-tree">
                {visibleSites.map((site) => {
                  const isSiteSelected = selectedNode?.type === "site" && selectedNode.id === site.id;
                  const isSiteExpanded = expandedSites.has(site.id);
                  const siteBuildings = buildingsBySiteId.get(site.id) ?? [];
                  return (
                    <div key={`site-${site.id}`}>
                      <div
                        className={`patrimony-tree-node patrimony-tree-site${isSiteSelected ? " is-active" : ""}${
                          dropTargetKey === `site-${site.id}` ? " is-drop-target" : ""
                        }`}
                        onDragOver={(e) => allowDrop(e, `site-${site.id}`, "building")}
                        onDragLeave={() => dropTargetKey === `site-${site.id}` && setDropTargetKey(null)}
                        onDrop={(e) => handleDropOnSite(e, site.id)}
                      >
                        <span
                          className="patrimony-tree-toggle"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleSiteExpand(site.id);
                          }}
                        >
                          {isSiteExpanded ? "▼" : "▶"}
                        </span>
                        <span className="patrimony-tree-label" onClick={() => selectAndExpand({ type: "site", id: site.id })}>
                          {site.nom_site}
                          <span className="patrimony-tree-count">({siteBuildings.length})</span>
                        </span>
                      </div>
                      {isSiteExpanded ? (
                        <div className="patrimony-tree-children-site">
                          {siteBuildings.map((building) => {
                            const isBuildingSelected = selectedNode?.type === "building" && selectedNode.id === building.id;
                            const isBuildingExpanded = expandedBuildings.has(building.id);
                            const buildingLocals = localsByBuildingId.get(building.id) ?? [];
                            const hasIgn = building.statut_geocodage === "IGN_VALIDE";
                            return (
                              <div key={`building-${building.id}`}>
                                <div
                                  className={`patrimony-tree-node patrimony-tree-building${isBuildingSelected ? " is-active" : ""}${
                                    dropTargetKey === `building-${building.id}` ? " is-drop-target" : ""
                                  }${dragItem?.type === "building" && dragItem.id === building.id ? " is-dragging" : ""}`}
                                  draggable
                                  onDragStart={(e) => handleDragStartBuilding(e, building)}
                                  onDragEnd={handleDragEnd}
                                  onDragOver={(e) => allowDrop(e, `building-${building.id}`, "local")}
                                  onDragLeave={() => dropTargetKey === `building-${building.id}` && setDropTargetKey(null)}
                                  onDrop={(e) => handleDropOnBuilding(e, building.id)}
                                >
                                  <span
                                    className="patrimony-tree-toggle"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      if (buildingLocals.length > 0) toggleBuildingExpand(building.id);
                                    }}
                                  >
                                    {buildingLocals.length > 0 ? (isBuildingExpanded ? "▼" : "▶") : "·"}
                                  </span>
                                  <span className="patrimony-tree-label" onClick={() => selectAndExpand({ type: "building", id: building.id })}>
                                    <span className={`patrimony-tree-ign-dot${hasIgn ? "" : " is-empty"}`}>{hasIgn ? "●" : "○"}</span>
                                    {building.nom_batiment || `Bâtiment #${building.id}`}
                                    {buildingLocals.length > 0 ? (
                                      <span className="patrimony-tree-count">({buildingLocals.length})</span>
                                    ) : null}
                                  </span>
                                </div>
                                {isBuildingExpanded ? (
                                  <div className="patrimony-tree-children-building">
                                    {buildingLocals.map((local) => {
                                      const isLocalSelected = selectedNode?.type === "local" && selectedNode.id === local.id;
                                      return (
                                        <div
                                          key={`local-${local.id}`}
                                          className={`patrimony-tree-local${isLocalSelected ? " is-active" : ""}${
                                            dragItem?.type === "local" && dragItem.id === local.id ? " is-dragging" : ""
                                          }`}
                                          draggable
                                          onDragStart={(e) => handleDragStartLocal(e, local)}
                                          onDragEnd={handleDragEnd}
                                          onClick={() => selectAndExpand({ type: "local", id: local.id })}
                                        >
                                          ◇ {local.nom_local}
                                          {local.niveau ? <span className="patrimony-tree-count">· niv. {local.niveau}</span> : null}
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
                  <>
                    <div className="patrimony-tree-orphan-header">Bâtiments sans site rattaché ({orphanBuildings.length})</div>
                    {orphanBuildings.map((building) => {
                      const isSelected = selectedNode?.type === "building" && selectedNode.id === building.id;
                      const hasIgn = building.statut_geocodage === "IGN_VALIDE";
                      return (
                        <div
                          key={`orphan-${building.id}`}
                          className={`patrimony-tree-node patrimony-tree-building${isSelected ? " is-active" : ""}${
                            dragItem?.type === "building" && dragItem.id === building.id ? " is-dragging" : ""
                          }`}
                          draggable
                          onDragStart={(e) => handleDragStartBuilding(e, building)}
                          onDragEnd={handleDragEnd}
                          onClick={() => selectAndExpand({ type: "building", id: building.id })}
                        >
                          <span className="patrimony-tree-toggle">·</span>
                          <span className="patrimony-tree-label">
                            <span className={`patrimony-tree-ign-dot${hasIgn ? "" : " is-empty"}`}>{hasIgn ? "●" : "○"}</span>
                            {building.nom_batiment || `Bâtiment #${building.id}`}
                          </span>
                        </div>
                      );
                    })}
                  </>
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
        key={`site-${selectedSite.id}`}
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
        key={`building-${selectedBuilding.id}`}
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
        key={`local-${selectedLocal.id}`}
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
  const { token } = useAuth();
  const queryClient = useQueryClient();

  const [nomBatiment, setNomBatiment] = useState(building.nom_batiment ?? "");
  const [adresseReconstituee, setAdresseReconstituee] = useState(building.adresse_reconstituee ?? "");
  const [nomCommune, setNomCommune] = useState(building.nom_commune);

  // Attachement inline (IGN + DGFIP) directement depuis le panneau, sans ouvrir la fiche complete.
  const [showIgnAttachment, setShowIgnAttachment] = useState(false);
  const [showDgfipAttachment, setShowDgfipAttachment] = useState(false);
  const [selectedDgfipKey, setSelectedDgfipKey] = useState<string | null>(null);
  const [geoAttachError, setGeoAttachError] = useState<string | null>(null);
  const [geoAttachSuccess, setGeoAttachSuccess] = useState<string | null>(null);

  const attachmentAddress = buildAttachmentAddress(building);

  const freeAddressLookupQuery = useQuery({
    queryKey: ["buildings", "free-address-lookup", attachmentAddress, token],
    queryFn: () => fetchFreeAddressLookup(token as string, attachmentAddress as string),
    enabled: Boolean(token) && Boolean(attachmentAddress) && showIgnAttachment && !selectedDgfipKey,
    retry: false,
  });

  const dgfipNamingLookupQuery = useQuery({
    queryKey: ["buildings", "naming-lookup", selectedDgfipKey, token],
    queryFn: () => fetchBuildingNamingLookup(token as string, selectedDgfipKey as string),
    enabled: Boolean(token) && Boolean(selectedDgfipKey) && showIgnAttachment,
    retry: false,
  });

  const nearbyDgfipQuery = useQuery({
    queryKey: ["buildings", "nearby-dgfip", building.id, token],
    queryFn: () => fetchNearbyDgfip(token as string, building.id),
    enabled: Boolean(token) && showDgfipAttachment,
    retry: false,
  });

  const activeLookupQuery = selectedDgfipKey ? dgfipNamingLookupQuery : freeAddressLookupQuery;

  async function invalidateAfterAttach() {
    await queryClient.invalidateQueries({ queryKey: ["buildings", token] });
    await queryClient.invalidateQueries({ queryKey: ["building", building.id] });
  }

  const attachGeoMutation = useMutation({
    mutationFn: (payload: {
      unique_key: string;
      validated_name?: string;
      selected_feature?: GeoJsonFeature | null;
      selected_features?: GeoJsonFeature[];
    }) => attachBuildingGeoRequest(token as string, building.id, payload),
    onSuccess: async (updated: Building) => {
      setGeoAttachSuccess(`Attachement DGFIP + IGN réalisé : « ${updated.nom_batiment || `#${updated.id}`} ».`);
      setGeoAttachError(null);
      setShowIgnAttachment(false);
      setShowDgfipAttachment(false);
      setSelectedDgfipKey(null);
      await invalidateAfterAttach();
    },
    onError: (err: unknown) => {
      setGeoAttachSuccess(null);
      setGeoAttachError(err instanceof Error ? err.message : "Attachement GEO impossible.");
    },
  });

  const attachIgnMutation = useMutation({
    mutationFn: (payload: BuildingIgnAttachmentPayload) => attachBuildingIgnRequest(token as string, building.id, payload),
    onSuccess: async (updated: Building) => {
      setGeoAttachSuccess(`Attachement IGN réalisé : « ${updated.nom_batiment || `#${updated.id}`} ».`);
      setGeoAttachError(null);
      setShowIgnAttachment(false);
      setSelectedDgfipKey(null);
      await invalidateAfterAttach();
    },
    onError: (err: unknown) => {
      setGeoAttachSuccess(null);
      setGeoAttachError(err instanceof Error ? err.message : "Attachement IGN impossible.");
    },
  });

  async function handleGeoAttach(payload: {
    validatedName?: string;
    selectedFeature?: GeoJsonFeature | null;
    selectedFeatures?: GeoJsonFeature[];
  }) {
    setGeoAttachError(null);
    setGeoAttachSuccess(null);
    if (selectedDgfipKey) {
      await attachGeoMutation.mutateAsync({
        unique_key: selectedDgfipKey,
        validated_name: payload.validatedName,
        selected_feature: payload.selectedFeature,
        selected_features: payload.selectedFeatures,
      });
    } else {
      const lookupData = activeLookupQuery.data;
      await attachIgnMutation.mutateAsync({
        validated_name: payload.validatedName,
        selected_feature: payload.selectedFeature,
        selected_features: payload.selectedFeatures,
        lat: lookupData?.lat ?? null,
        lon: lookupData?.lon ?? null,
      });
    }
  }

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
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button type="button" className="secondary-button" onClick={onToggleEdit}>
            {editMode ? "Annuler l'édition" : "Modifier"}
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setShowIgnAttachment((v) => !v);
              setShowDgfipAttachment(false);
              setGeoAttachError(null);
              setGeoAttachSuccess(null);
            }}
          >
            {showIgnAttachment ? "Fermer l'attachement IGN" : "Attachement IGN"}
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setShowDgfipAttachment((v) => !v);
              setSelectedDgfipKey(null);
              setGeoAttachError(null);
              setGeoAttachSuccess(null);
            }}
          >
            {showDgfipAttachment ? "Fermer l'attachement DGFIP" : "Attachement DGFIP"}
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

      {geoAttachError ? <p className="error-text">{geoAttachError}</p> : null}
      {geoAttachSuccess ? <p className="success-text">{geoAttachSuccess}</p> : null}

      {showIgnAttachment ? (
        <div className="section-block">
          <div className="section-heading">
            <h4>Attachement IGN</h4>
            <p>
              {attachmentAddress
                ? `Carte IGN centrée sur « ${attachmentAddress} ». Sélectionne le ou les bâtiments IGN qui correspondent.`
                : "Aucune adresse renseignée — complète la fiche (adresse) avant de lancer l'attachement."}
            </p>
          </div>
          {activeLookupQuery.isLoading ? <p>Chargement des candidats IGN...</p> : null}
          {activeLookupQuery.error instanceof Error ? <p className="error-text">{activeLookupQuery.error.message}</p> : null}
          <BuildingSelectionWorkspace
            lookupData={(activeLookupQuery.data ?? null) as BuildingNamingLookup | FreeAddressLookup | null}
            emptyTitle={attachmentAddress ? "Chargement de la carte IGN..." : "Adresse manquante."}
            emptyDescription={
              attachmentAddress
                ? "La carte IGN se charge à partir de l'adresse du bâtiment."
                : "Renseigne l'adresse reconstituée ou les champs de voirie via « Modifier »."
            }
            createPending={attachGeoMutation.isPending || attachIgnMutation.isPending}
            error={geoAttachError}
            success={geoAttachSuccess}
            createLabelWithSelection={selectedDgfipKey ? "Rattacher DGFIP + IGN sélectionné" : "Rattacher les données IGN"}
            createLabelWithoutSelection={selectedDgfipKey ? "Rattacher DGFIP sans sélection IGN" : "Rattacher sans sélection IGN"}
            onCreate={handleGeoAttach}
            nearbyDgfipMarkers={nearbyDgfipQuery.data?.rows}
          />
        </div>
      ) : null}

      {showDgfipAttachment ? (
        <div className="section-block">
          <div className="section-heading">
            <h4>Attachement DGFIP / MAJIC</h4>
            <p>
              Adresses DGFIP / MAJIC dans un rayon de 200 m. Sélectionner une adresse recadre la carte IGN sur sa parcelle
              cadastrale (ouvre l'attachement IGN).
            </p>
          </div>
          {nearbyDgfipQuery.isLoading ? <p>Recherche des adresses proches...</p> : null}
          {nearbyDgfipQuery.error instanceof Error ? (
            <p className="error-text">Impossible de charger les adresses DGFIP : {nearbyDgfipQuery.error.message}</p>
          ) : null}
          {nearbyDgfipQuery.data && nearbyDgfipQuery.data.majic_configured === false ? (
            <div className="info-banner" style={{ background: "#fff4e6", borderColor: "#e07a5f" }}>
              <strong>Source MAJIC non disponible sur ce serveur.</strong>
              <p style={{ marginTop: 8 }}>
                Le fichier DGFIP / MAJIC n'est pas configuré côté backend (
                {nearbyDgfipQuery.data.majic_unavailable_reason ?? "fichier introuvable"}). L'attachement DGFIP automatique
                n'est donc pas disponible pour l'instant.
              </p>
            </div>
          ) : null}
          {nearbyDgfipQuery.data && nearbyDgfipQuery.data.majic_configured && nearbyDgfipQuery.data.rows.length === 0 ? (
            <p className="empty-state-text">Aucune adresse DGFIP trouvée dans un rayon de 200 m.</p>
          ) : null}
          <div className="resource-list buildings-address-list">
            {(nearbyDgfipQuery.data?.rows ?? []).map((row: NearbyDgfipRow) => {
              const isActive = selectedDgfipKey === row.unique_key;
              return (
                <article key={row.unique_key} className={`resource-card ${isActive ? "resource-card-active" : ""}`}>
                  <div className="resource-card-header">
                    <div>
                      <h3>{row.address_display}</h3>
                      <p>{row.nom_commune}</p>
                    </div>
                    <span className="resource-badge">{row.distance_m} m</span>
                  </div>
                  <dl className="resource-metadata">
                    <div>
                      <dt>Indices MAJIC</dt>
                      <dd>{row.majic_building_values.join(", ") || "Aucun"}</dd>
                    </div>
                  </dl>
                  <div className="resource-card-actions">
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => {
                        const nextKey = isActive ? null : row.unique_key;
                        setSelectedDgfipKey(nextKey);
                        setGeoAttachError(null);
                        if (nextKey && !showIgnAttachment) {
                          setShowIgnAttachment(true);
                        }
                      }}
                    >
                      {isActive ? "Désélectionner" : "Sélectionner cette adresse DGFIP"}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      ) : null}
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
