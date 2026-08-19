// BuildingsListPage — vue cascade Site > Bâtiment > Local
// Features :
//   - Arborescence drag&drop (reparentage Site>Bâtiment, Bâtiment>Local)
//   - Carte principale unifiée avec mode attachement IGN (WFS client-side)
//   - Panneau détail complet (fiche bâtiment sans "Ouvrir la fiche complète")
//   - Création inline de sites, bâtiments et locaux

import { useMemo, useState } from "react";
import type { ChangeEvent, DragEvent, FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { BuildingPortfolioMap } from "../components/BuildingPortfolioMap";
import {
  attachBuildingGeoRequest,
  attachBuildingIgnRequest,
  createBuildingRequest,
  createLocalRequest,
  createSiteRequest,
  deleteAllBuildingsRequest,
  deleteBuildingRequest,
  deleteLocalRequest,
  deleteSiteRequest,
  fetchAllLocals,
  fetchBuildingMeterLinks,
  fetchBuildings,
  fetchFreeAddressLookup,
  fetchNearbyDgfip,
  fetchSites,
  reclassifyBuildingRequest,
  reclassifyLocalRequest,
  reclassifySiteRequest,
  updateBuildingRequest,
  updateLocalRequest,
  updateSiteRequest,
  type Building,
  type BuildingIgnAttachmentPayload,
  type BuildingMeterLink,
  type CreateBuildingPayload,
  type CreateLocalPayload,
  type CreateSitePayload,
  type FreeAddressLookup,
  type GeoJsonFeature,
  type GeoJsonFeatureCollection,
  type Local,
  type NearbyDgfipResult,
  type NearbyDgfipRow,
  type PatrimonyNodeType,
  type ReclassifyPatrimonyPayload,
  type ReclassifyPatrimonyResult,
  type Site,
  type UpdateBuildingPayload,
  type UpdateLocalPayload,
  type UpdateSitePayload,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

// ─────────────────────────────────────────────────────────────────────────────
// Types helpers
// ─────────────────────────────────────────────────────────────────────────────

type SelectedNode =
  | { type: "site"; id: number }
  | { type: "building"; id: number }
  | { type: "local"; id: number }
  | null;

type AttachMode = "none" | "ign" | "dgfip";

function buildAddressLine(
  b: Pick<Building, "numero_voirie" | "nature_voie" | "nom_voie" | "adresse_reconstituee" | "nom_commune">,
) {
  if (b.adresse_reconstituee) return b.adresse_reconstituee;
  const parts = [b.numero_voirie, b.nature_voie, b.nom_voie].filter(Boolean);
  return parts.length > 0 ? `${parts.join(" ")}, ${b.nom_commune}` : b.nom_commune;
}

function buildAttachmentAddress(building: Building): string | null {
  if (building.adresse_reconstituee?.trim()) return building.adresse_reconstituee.trim();
  const parts = [building.numero_voirie, building.nature_voie, building.nom_voie, building.nom_commune].filter(
    (p): p is string => Boolean(p?.trim()),
  );
  return parts.length >= 2 ? parts.join(" ") : null;
}

function siteCentroid(buildings: Building[]): { lat: number; lon: number } | null {
  const geo = buildings.filter((b) => b.latitude != null && b.longitude != null);
  if (!geo.length) return null;
  return {
    lat: geo.reduce((a, b) => a + (b.latitude as number), 0) / geo.length,
    lon: geo.reduce((a, b) => a + (b.longitude as number), 0) / geo.length,
  };
}

function parseJsonArray(value: string | null | undefined): string[] {
  if (!value) return [];
  try {
    const p = JSON.parse(value) as unknown;
    return Array.isArray(p) ? p.map(String) : [];
  } catch { return []; }
}

type IgnFeatureSummary = {
  ign_id: string; ign_layer: string; ign_typename: string;
  name: string; label: string; resolved_name: string;
  attributes: [string, string][];
};

function parseIgnFeatures(value: string | null | undefined): IgnFeatureSummary[] {
  if (!value) return [];
  try {
    const p = JSON.parse(value) as unknown;
    if (!Array.isArray(p)) return [];
    return p.map((f) => {
      if (!f || typeof f !== "object") return null;
      const props = ((f as Record<string, unknown>).properties ?? {}) as Record<string, unknown>;
      const attrs = (props.attributes && typeof props.attributes === "object" && !Array.isArray(props.attributes))
        ? Object.entries(props.attributes as Record<string, unknown>)
            .map(([k, v]) => [k, v == null ? "" : String(v)] as [string, string])
            .filter(([k, v]) => v !== "" && !k.startsWith("_"))
            .sort(([a], [b]) => a.localeCompare(b, "fr"))
        : [];
      return {
        ign_id: String(props.ign_id ?? ""),
        ign_layer: String(props.ign_layer ?? ""),
        ign_typename: String(props.ign_typename ?? ""),
        name: String(props.name ?? ""),
        label: String(props.label ?? ""),
        resolved_name: String(props.resolved_name ?? props.resolved_label ?? ""),
        attributes: attrs,
      };
    }).filter((e): e is IgnFeatureSummary => e !== null && Boolean(e.ign_id));
  } catch { return []; }
}

// ─────────────────────────────────────────────────────────────────────────────
// Composant principal
// ─────────────────────────────────────────────────────────────────────────────

export function BuildingsListPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  // Arborescence
  const [search, setSearch] = useState("");
  const [selectedNode, setSelectedNode] = useState<SelectedNode>(null);
  const [expandedSites, setExpandedSites] = useState<Set<number>>(new Set());
  const [expandedBuildings, setExpandedBuildings] = useState<Set<number>>(new Set());
  const [editMode, setEditMode] = useState(false);

  // Drag & drop
  const [dragItem, setDragItem] = useState<{ type: "building" | "local"; id: number; sourceParentId: number | null } | null>(null);
  const [dropTargetKey, setDropTargetKey] = useState<string | null>(null);

  // Mode attachement IGN/DGFIP (piloté par la carte principale)
  const [attachMode, setAttachMode] = useState<AttachMode>("none");
  const [attachSelectedFeatures, setAttachSelectedFeatures] = useState<GeoJsonFeature[]>([]);

  // Formulaires de création
  const [showCreateSite, setShowCreateSite] = useState(false);
  const [showCreateBuilding, setShowCreateBuilding] = useState(false);
  const [showCreateLocal, setShowCreateLocal] = useState(false);

  // ── Données ──────────────────────────────────────────────────────────────
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

  const sites = sitesQuery.data ?? [];
  const buildings = buildingsQuery.data ?? [];
  const locals = localsQuery.data ?? [];

  const buildingsBySiteId = useMemo(() => {
    const map = new Map<number | null, Building[]>();
    for (const b of buildings) {
      const key = b.site_id ?? null;
      map.set(key, [...(map.get(key) ?? []), b]);
    }
    return map;
  }, [buildings]);

  const localsByBuildingId = useMemo(() => {
    const map = new Map<number, Local[]>();
    for (const l of locals) map.set(l.building_id, [...(map.get(l.building_id) ?? []), l]);
    return map;
  }, [locals]);

  // Recherche
  const lowerSearch = search.trim().toLowerCase();
  const matchesSearch = (t: string | null | undefined) => !lowerSearch || (t ?? "").toLowerCase().includes(lowerSearch);
  const visibleSites = useMemo(() => {
    if (!lowerSearch) return sites;
    return sites.filter((s) => {
      if (matchesSearch(s.nom_site) || matchesSearch(s.adresse)) return true;
      return (buildingsBySiteId.get(s.id) ?? []).some(
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

  // Sélection
  const selectedSite = selectedNode?.type === "site" ? (sites.find((s) => s.id === selectedNode.id) ?? null) : null;
  const selectedBuilding = selectedNode?.type === "building" ? (buildings.find((b) => b.id === selectedNode.id) ?? null) : null;
  const selectedBuildingParentSite = selectedBuilding?.site_id ? (sites.find((s) => s.id === selectedBuilding.site_id) ?? null) : null;
  const selectedLocal = selectedNode?.type === "local" ? (locals.find((l) => l.id === selectedNode.id) ?? null) : null;
  const selectedLocalParent = selectedLocal ? (buildings.find((b) => b.id === selectedLocal.building_id) ?? null) : null;
  const selectedLocalParentSite = selectedLocalParent?.site_id ? (sites.find((s) => s.id === selectedLocalParent.site_id) ?? null) : null;

  // Carte
  const highlightedBuildingIds = useMemo(
    () => (selectedSite ? (buildingsBySiteId.get(selectedSite.id) ?? []).map((b) => b.id) : []),
    [selectedSite, buildingsBySiteId],
  );
  const focusBuilding = selectedBuilding ?? selectedLocalParent;
  const focusLatLon =
    focusBuilding?.latitude != null && focusBuilding.longitude != null
      ? { lat: focusBuilding.latitude, lon: focusBuilding.longitude }
      : selectedSite
        ? siteCentroid(buildingsBySiteId.get(selectedSite.id) ?? [])
        : null;

  const activeMapBuildingId = attachMode === "none" ? (selectedBuilding?.id ?? selectedLocalParent?.id ?? null) : null;

  // Polygones IGN déjà attachés à afficher sur la carte (mode portfolio)
  const portfolioIgnFeatures = useMemo<GeoJsonFeatureCollection | null>(() => {
    const targetBuildings: Building[] =
      selectedSite
        ? (buildingsBySiteId.get(selectedSite.id) ?? [])
        : selectedBuilding
          ? [selectedBuilding]
          : [];
    const features = targetBuildings.flatMap((b) => {
      if (!b.ign_features_json) return [];
      try {
        const parsed = JSON.parse(b.ign_features_json) as unknown;
        if (Array.isArray(parsed)) return parsed as GeoJsonFeature[];
      } catch { /* empty */ }
      return [];
    });
    return features.length > 0 ? { type: "FeatureCollection", features } : null;
  }, [selectedSite, selectedBuilding, buildingsBySiteId]);

  // Attachement : adresse du bâtiment sélectionné
  const attachBuilding = attachMode !== "none" ? selectedBuilding : null;
  const attachAddress = attachBuilding ? buildAttachmentAddress(attachBuilding) : null;

  const freeAddressLookupQuery = useQuery({
    queryKey: ["buildings", "attach-geocode", attachBuilding?.id, token],
    queryFn: () => fetchFreeAddressLookup(token as string, attachAddress as string),
    enabled: Boolean(token) && Boolean(attachAddress) && attachMode === "ign",
    retry: false,
  });

  const nearbyDgfipQuery = useQuery({
    queryKey: ["buildings", "attach-dgfip", attachBuilding?.id, token],
    queryFn: () => fetchNearbyDgfip(token as string, attachBuilding!.id),
    enabled: Boolean(token) && attachBuilding !== null && attachMode === "dgfip",
    retry: false,
  });

  // Compteurs
  const geocodedCount = buildings.filter((b) => b.latitude != null && b.longitude != null).length;
  const ignAttachedCount = buildings.filter((b) => b.statut_geocodage === "IGN_VALIDE").length;
  const totalCount = sites.length + buildings.length + locals.length;

  function refreshPatrimonyQueries() {
    queryClient.invalidateQueries({ queryKey: ["buildings", "sites", token] });
    queryClient.invalidateQueries({ queryKey: ["buildings", token] });
    queryClient.invalidateQueries({ queryKey: ["buildings", "locals", token] });
  }

  function selectReclassifiedNode(result: ReclassifyPatrimonyResult) {
    selectAndExpand({ type: result.entity_type, id: result.entity_id });
  }

  // ── Mutations ─────────────────────────────────────────────────────────────
  // include_sites : les sites ne sont pas des enfants des bâtiments (c'est l'inverse,
  // via Building.site_id), donc une purge des bâtiments les laissait en place et
  // l'arborescence restait peuplée de sites vides.
  const deleteAllMutation = useMutation({
    mutationFn: (includeSites: boolean) => deleteAllBuildingsRequest(token as string, includeSites),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["buildings"] });
      queryClient.invalidateQueries({ queryKey: ["buildings", "sites", token] });
      queryClient.invalidateQueries({ queryKey: ["buildings", "locals", token] });
      alert(
        `${data.deleted} bâtiment(s) supprimé(s)` +
          (data.deleted_sites ? ` et ${data.deleted_sites} site(s).` : "."),
      );
    },
  });

  const updateSiteMutation = useMutation({
    mutationFn: ({ siteId, payload }: { siteId: number; payload: UpdateSitePayload }) =>
      updateSiteRequest(token as string, siteId, payload),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["buildings", "sites", token] }); setEditMode(false); },
  });

  const updateBuildingMutation = useMutation({
    mutationFn: ({ buildingId, payload }: { buildingId: number; payload: UpdateBuildingPayload }) =>
      updateBuildingRequest(token as string, buildingId, payload),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["buildings", token] }); setEditMode(false); },
  });

  const updateLocalMutation = useMutation({
    mutationFn: ({ buildingId, localId, payload }: { buildingId: number; localId: number; payload: UpdateLocalPayload }) =>
      updateLocalRequest(token as string, buildingId, localId, payload),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["buildings", "locals", token] }); setEditMode(false); },
  });

  const reclassifySiteMutation = useMutation({
    mutationFn: ({ siteId, payload }: { siteId: number; payload: ReclassifyPatrimonyPayload }) =>
      reclassifySiteRequest(token as string, siteId, payload),
    onSuccess: (result) => {
      refreshPatrimonyQueries();
      setEditMode(false);
      selectReclassifiedNode(result);
    },
    onError: (err: unknown) => alert(err instanceof Error ? err.message : "Reclassement impossible."),
  });

  const reclassifyBuildingMutation = useMutation({
    mutationFn: ({ buildingId, payload }: { buildingId: number; payload: ReclassifyPatrimonyPayload }) =>
      reclassifyBuildingRequest(token as string, buildingId, payload),
    onSuccess: (result) => {
      refreshPatrimonyQueries();
      setEditMode(false);
      selectReclassifiedNode(result);
    },
    onError: (err: unknown) => alert(err instanceof Error ? err.message : "Reclassement impossible."),
  });

  const reclassifyLocalMutation = useMutation({
    mutationFn: ({ buildingId, localId, payload }: { buildingId: number; localId: number; payload: ReclassifyPatrimonyPayload }) =>
      reclassifyLocalRequest(token as string, buildingId, localId, payload),
    onSuccess: (result) => {
      refreshPatrimonyQueries();
      setEditMode(false);
      selectReclassifiedNode(result);
    },
    onError: (err: unknown) => alert(err instanceof Error ? err.message : "Reclassement impossible."),
  });

  const createSiteMutation = useMutation({
    mutationFn: (payload: CreateSitePayload) => createSiteRequest(token as string, payload),
    onSuccess: (site) => {
      queryClient.invalidateQueries({ queryKey: ["buildings", "sites", token] });
      setShowCreateSite(false);
      selectAndExpand({ type: "site", id: site.id });
    },
  });

  const createBuildingMutation = useMutation({
    mutationFn: (payload: CreateBuildingPayload) => createBuildingRequest(token as string, payload),
    onSuccess: (building) => {
      queryClient.invalidateQueries({ queryKey: ["buildings", token] });
      setShowCreateBuilding(false);
      selectAndExpand({ type: "building", id: building.id });
    },
  });

  const createLocalMutation = useMutation({
    mutationFn: ({ buildingId, payload }: { buildingId: number; payload: CreateLocalPayload }) =>
      createLocalRequest(token as string, buildingId, payload),
    onSuccess: (local) => {
      queryClient.invalidateQueries({ queryKey: ["buildings", "locals", token] });
      setShowCreateLocal(false);
      selectAndExpand({ type: "local", id: local.id });
    },
  });

  const deleteSiteMutation = useMutation({
    mutationFn: (siteId: number) => deleteSiteRequest(token as string, siteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["buildings", "sites", token] });
      queryClient.invalidateQueries({ queryKey: ["buildings", token] });
      setSelectedNode(null);
    },
  });

  const deleteBuildingMutation = useMutation({
    mutationFn: (buildingId: number) => deleteBuildingRequest(token as string, buildingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["buildings", token] });
      queryClient.invalidateQueries({ queryKey: ["buildings", "locals", token] });
      setSelectedNode(null);
    },
  });

  const deleteLocalMutation = useMutation({
    mutationFn: ({ buildingId, localId }: { buildingId: number; localId: number }) =>
      deleteLocalRequest(token as string, buildingId, localId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["buildings", "locals", token] });
      setSelectedNode(null);
    },
  });

  // ── Handlers arborescence ─────────────────────────────────────────────────
  function toggleSiteExpand(id: number) {
    setExpandedSites((c) => { const n = new Set(c); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }
  function toggleBuildingExpand(id: number) {
    setExpandedBuildings((c) => { const n = new Set(c); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }
  function selectAndExpand(node: SelectedNode) {
    setSelectedNode(node);
    setEditMode(false);
    if (!node) return;
    if (node.type === "site") {
      setExpandedSites((c) => new Set(c).add(node.id));
    } else if (node.type === "building") {
      const b = buildings.find((x) => x.id === node.id);
      if (b?.site_id) setExpandedSites((c) => new Set(c).add(b.site_id as number));
      setExpandedBuildings((c) => new Set(c).add(node.id));
    } else if (node.type === "local") {
      const l = locals.find((x) => x.id === node.id);
      if (l) {
        const p = buildings.find((b) => b.id === l.building_id);
        if (p?.site_id) setExpandedSites((c) => new Set(c).add(p.site_id as number));
        if (p) setExpandedBuildings((c) => new Set(c).add(p.id));
      }
    }
    // Quitter le mode attachement si on change de sélection
    setAttachMode("none");
    setAttachSelectedFeatures([]);
  }

  // ── Drag & drop ───────────────────────────────────────────────────────────
  function handleDragStartBuilding(e: DragEvent, building: Building) {
    e.stopPropagation();
    setDragItem({ type: "building", id: building.id, sourceParentId: building.site_id ?? null });
  }
  function handleDragStartLocal(e: DragEvent, local: Local) {
    e.stopPropagation();
    setDragItem({ type: "local", id: local.id, sourceParentId: local.building_id });
  }
  function handleDragEnd() { setDragItem(null); setDropTargetKey(null); }
  function allowDrop(e: DragEvent, key: string, accepts: "building" | "local") {
    if (dragItem?.type !== accepts) return;
    e.preventDefault();
    if (dropTargetKey !== key) setDropTargetKey(key);
  }
  function handleDropOnSite(e: DragEvent, siteId: number) {
    e.preventDefault();
    if (dragItem?.type === "building" && dragItem.sourceParentId !== siteId)
      updateBuildingMutation.mutate({ buildingId: dragItem.id, payload: { site_id: siteId } });
    handleDragEnd();
  }
  function handleDropOnBuilding(e: DragEvent, buildingId: number) {
    e.preventDefault();
    if (dragItem?.type === "local" && dragItem.sourceParentId !== buildingId)
      updateLocalMutation.mutate({ buildingId: dragItem.sourceParentId as number, localId: dragItem.id, payload: { building_id: buildingId } });
    handleDragEnd();
  }

  // ── Attachement IGN/DGFIP ─────────────────────────────────────────────────
  function enterAttach(mode: "ign" | "dgfip") {
    setAttachMode(mode);
    setAttachSelectedFeatures([]);
  }
  function exitAttach() { setAttachMode("none"); setAttachSelectedFeatures([]); }
  function onAttachSuccess() { setAttachMode("none"); setAttachSelectedFeatures([]); }

  // ── Auth guard ────────────────────────────────────────────────────────────
  if (!token) {
    return (
      <section className="panel stack-lg">
        <h2>Patrimoine</h2>
        <p>Connecte-toi pour consulter ton patrimoine.</p>
      </section>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <section className="panel stack-lg buildings-workspace-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Patrimoine</p>
          <h2>Mon patrimoine — vue cascade</h2>
          <p>Arborescence Site › Bâtiment › Local. Clique pour voir les détails. Glisse pour réorganiser.</p>
        </div>
        <div className="buildings-header-actions">
          <Link className="secondary-link" to="/buildings/create-edit">Importer / éditer</Link>
          <div className="header-badge"><strong>{sites.length}</strong><span>site(s)</span></div>
          <div className="header-badge"><strong>{buildings.length}</strong><span>bâtiment(s)</span></div>
          <div className="header-badge"><strong>{locals.length}</strong><span>local(aux)</span></div>
          {/* Le bouton doit rester atteignable tant qu'il reste QUOI QUE CE SOIT dans
              l'arborescence. Le conditionner aux seuls bâtiments créait une impasse :
              après une purge, il restait des sites visibles et plus aucun moyen de les
              supprimer, puisque le bouton disparaissait avec le dernier bâtiment. */}
          {(buildings.length > 0 || sites.length > 0) && (
            <button type="button" className="danger-button" onClick={() => {
              if (buildings.length > 0) {
                if (!window.confirm(`Supprimer les ${buildings.length} bâtiment(s) et leurs locaux ?`)) return;
                const alsoSites = sites.length > 0 && window.confirm(
                  `Supprimer aussi les ${sites.length} site(s) ? ` +
                    "OK = repartir d'une arborescence entièrement vide. " +
                    "Annuler = ne supprimer que les bâtiments (les sites resteront affichés).",
                );
                deleteAllMutation.mutate(alsoSites);
                return;
              }
              // Plus aucun bâtiment : il ne reste que des sites à vider.
              if (!window.confirm(`Supprimer les ${sites.length} site(s) restant(s) ?`)) return;
              deleteAllMutation.mutate(true);
            }} disabled={deleteAllMutation.isPending}>
              {deleteAllMutation.isPending
                ? "Suppression..."
                : buildings.length > 0
                  ? "Supprimer tout"
                  : `Supprimer les ${sites.length} site(s)`}
            </button>
          )}
        </div>
      </div>

      {(sitesQuery.isLoading || buildingsQuery.isLoading || localsQuery.isLoading) && <p>Chargement...</p>}

      {totalCount === 0 && !sitesQuery.isLoading ? (
        <div className="empty-state">
          <strong>Aucun patrimoine importé.</strong>
          <Link className="secondary-link" to="/buildings/create-edit">Importer le patrimoine</Link>
        </div>
      ) : null}

      {totalCount > 0 && (
        <div className="detail-grid">
          <div className="detail-card"><span>Géolocalisés</span><strong>{geocodedCount}</strong></div>
          <div className="detail-card"><span>Attachement IGN</span><strong>{ignAttachedCount}</strong></div>
        </div>
      )}

      {totalCount > 0 && (
        <div className="buildings-workspace">
          {/* ── COLONNE GAUCHE : arborescence ── */}
          <aside className="buildings-sidebar">
            <div className="section-block buildings-addresses-section">
              <div className="section-heading">
                <h3>Arborescence patrimoine</h3>
                <p>Clique pour voir le détail · Glisse pour réorganiser</p>
              </div>
              <label className="field">
                <span>Recherche</span>
                <input type="text" value={search} onChange={(e: ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)} placeholder="Nom, adresse, parcelle..." />
              </label>

              <div className="buildings-address-list patrimony-tree">
                {/* Sites */}
                {visibleSites.map((site) => {
                  const isSiteSelected = selectedNode?.type === "site" && selectedNode.id === site.id;
                  const isSiteExpanded = expandedSites.has(site.id);
                  const siteBuildings = buildingsBySiteId.get(site.id) ?? [];
                  return (
                    <div key={`site-${site.id}`}>
                      <div
                        className={`patrimony-tree-node patrimony-tree-site${isSiteSelected ? " is-active" : ""}${dropTargetKey === `site-${site.id}` ? " is-drop-target" : ""}`}
                        onDragOver={(e) => allowDrop(e, `site-${site.id}`, "building")}
                        onDragLeave={() => dropTargetKey === `site-${site.id}` && setDropTargetKey(null)}
                        onDrop={(e) => handleDropOnSite(e, site.id)}
                      >
                        <span className="patrimony-tree-toggle" onClick={(e) => { e.stopPropagation(); toggleSiteExpand(site.id); }}>
                          {isSiteExpanded ? "▼" : "▶"}
                        </span>
                        <span className="patrimony-tree-label" onClick={() => selectAndExpand({ type: "site", id: site.id })}>
                          {site.nom_site}<span className="patrimony-tree-count">({siteBuildings.length})</span>
                        </span>
                      </div>
                      {isSiteExpanded && (
                        <div className="patrimony-tree-children-site">
                          {siteBuildings.map((building) => {
                            const isBuildingSelected = selectedNode?.type === "building" && selectedNode.id === building.id;
                            const isBuildingExpanded = expandedBuildings.has(building.id);
                            const buildingLocals = localsByBuildingId.get(building.id) ?? [];
                            const hasIgn = building.statut_geocodage === "IGN_VALIDE";
                            return (
                              <div key={`building-${building.id}`}>
                                <div
                                  className={`patrimony-tree-node patrimony-tree-building${isBuildingSelected ? " is-active" : ""}${dropTargetKey === `building-${building.id}` ? " is-drop-target" : ""}${dragItem?.type === "building" && dragItem.id === building.id ? " is-dragging" : ""}`}
                                  draggable
                                  onDragStart={(e) => handleDragStartBuilding(e, building)}
                                  onDragEnd={handleDragEnd}
                                  onDragOver={(e) => allowDrop(e, `building-${building.id}`, "local")}
                                  onDragLeave={() => dropTargetKey === `building-${building.id}` && setDropTargetKey(null)}
                                  onDrop={(e) => handleDropOnBuilding(e, building.id)}
                                >
                                  <span className="patrimony-tree-toggle" onClick={(e) => { e.stopPropagation(); if (buildingLocals.length > 0) toggleBuildingExpand(building.id); }}>
                                    {buildingLocals.length > 0 ? (isBuildingExpanded ? "▼" : "▶") : "·"}
                                  </span>
                                  <span className="patrimony-tree-label" onClick={() => selectAndExpand({ type: "building", id: building.id })}>
                                    <span className={`patrimony-tree-ign-dot${hasIgn ? "" : " is-empty"}`}>{hasIgn ? "●" : "○"}</span>
                                    {building.nom_batiment || `Bâtiment #${building.id}`}
                                    {buildingLocals.length > 0 && <span className="patrimony-tree-count">({buildingLocals.length})</span>}
                                  </span>
                                </div>
                                {isBuildingExpanded && (
                                  <div className="patrimony-tree-children-building">
                                    {buildingLocals.map((local) => {
                                      const isLocalSelected = selectedNode?.type === "local" && selectedNode.id === local.id;
                                      return (
                                        <div
                                          key={`local-${local.id}`}
                                          className={`patrimony-tree-local${isLocalSelected ? " is-active" : ""}${dragItem?.type === "local" && dragItem.id === local.id ? " is-dragging" : ""}`}
                                          draggable
                                          onDragStart={(e) => handleDragStartLocal(e, local)}
                                          onDragEnd={handleDragEnd}
                                          onClick={() => selectAndExpand({ type: "local", id: local.id })}
                                        >
                                          ◇ {local.nom_local}
                                          {local.niveau && <span className="patrimony-tree-count">· niv. {local.niveau}</span>}
                                        </div>
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

                {/* Bâtiments orphelins */}
                {orphanBuildings.length > 0 && (
                  <>
                    <div className="patrimony-tree-orphan-header">Sans site ({orphanBuildings.length})</div>
                    {orphanBuildings.map((building) => {
                      const isSelected = selectedNode?.type === "building" && selectedNode.id === building.id;
                      const hasIgn = building.statut_geocodage === "IGN_VALIDE";
                      return (
                        <div
                          key={`orphan-${building.id}`}
                          className={`patrimony-tree-node patrimony-tree-building${isSelected ? " is-active" : ""}${dragItem?.type === "building" && dragItem.id === building.id ? " is-dragging" : ""}`}
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
                )}
              </div>

              {/* ── Section création ── */}
              <CreateSection
                selectedNode={selectedNode}
                buildings={buildings}
                sites={sites}
                showCreateSite={showCreateSite}
                showCreateBuilding={showCreateBuilding}
                showCreateLocal={showCreateLocal}
                onToggleSite={() => { setShowCreateSite((v) => !v); setShowCreateBuilding(false); setShowCreateLocal(false); }}
                onToggleBuilding={() => { setShowCreateBuilding((v) => !v); setShowCreateSite(false); setShowCreateLocal(false); }}
                onToggleLocal={() => { setShowCreateLocal((v) => !v); setShowCreateSite(false); setShowCreateBuilding(false); }}
                onCreateSite={(payload) => createSiteMutation.mutate(payload)}
                onCreateBuilding={(payload) => createBuildingMutation.mutate(payload)}
                onCreateLocal={(buildingId, payload) => createLocalMutation.mutate({ buildingId, payload })}
                createSitePending={createSiteMutation.isPending}
                createBuildingPending={createBuildingMutation.isPending}
                createLocalPending={createLocalMutation.isPending}
              />
            </div>
          </aside>

          {/* ── COLONNE DROITE : carte + panneau détail ── */}
          <div className="buildings-main-content">
            <div className="section-block">
              <div className="section-heading">
                <h3>Carte</h3>
                {attachMode === "ign" && (
                  <p style={{ color: "#f97316" }}>
                    Mode attachement IGN actif · Cliquez les polygones jaunes sur la carte pour les sélectionner
                  </p>
                )}
              </div>
              <BuildingPortfolioMap
                buildings={buildings}
                activeBuildingId={activeMapBuildingId}
                onSelectBuildingId={(id) => { if (attachMode === "none") selectAndExpand({ type: "building", id }); }}
                highlightedBuildingIds={highlightedBuildingIds}
                focusLatLon={attachMode === "none" ? focusLatLon : null}
                portfolioIgnFeatures={attachMode === "none" ? portfolioIgnFeatures : null}
                attachMode={attachMode === "ign" ? "ign" : "none"}
                attachLat={freeAddressLookupQuery.data?.lat ?? null}
                attachLon={freeAddressLookupQuery.data?.lon ?? null}
                attachAddress={attachAddress ?? undefined}
                attachFeatureCollection={freeAddressLookupQuery.data?.feature_collection ?? null}
                attachSelectedIds={attachSelectedFeatures.map((f) => String(f.properties?.ign_id ?? ""))}
                onSelectAttachFeature={(f) =>
                  setAttachSelectedFeatures((prev) => {
                    const id = String(f.properties?.ign_id ?? "");
                    return [...prev.filter((x) => String(x.properties?.ign_id ?? "") !== id), f];
                  })
                }
                onDeselectAttachFeatureId={(id) =>
                  setAttachSelectedFeatures((prev) => prev.filter((f) => String(f.properties?.ign_id ?? "") !== id))
                }
                isAttachLoading={freeAddressLookupQuery.isLoading}
              />
            </div>

            <PatrimonyDetailPanel
              selectedSite={selectedSite}
              selectedBuilding={selectedBuilding}
              selectedBuildingParentSite={selectedBuildingParentSite}
              selectedLocal={selectedLocal}
              selectedLocalParent={selectedLocalParent}
              selectedLocalParentSite={selectedLocalParentSite}
              sites={sites}
              buildings={buildings}
              siteBuildings={selectedSite ? (buildingsBySiteId.get(selectedSite.id) ?? []) : []}
              buildingLocals={selectedBuilding ? (localsByBuildingId.get(selectedBuilding.id) ?? []) : []}
              editMode={editMode}
              onToggleEdit={() => setEditMode((v) => !v)}
              onSaveSite={(payload) => selectedSite && updateSiteMutation.mutate({ siteId: selectedSite.id, payload })}
              onSaveBuilding={(payload) => selectedBuilding && updateBuildingMutation.mutate({ buildingId: selectedBuilding.id, payload })}
              onSaveLocal={(payload) => selectedLocal && updateLocalMutation.mutate({ buildingId: selectedLocal.building_id, localId: selectedLocal.id, payload })}
              onReclassifySite={(payload) => selectedSite && reclassifySiteMutation.mutate({ siteId: selectedSite.id, payload })}
              onReclassifyBuilding={(payload) => selectedBuilding && reclassifyBuildingMutation.mutate({ buildingId: selectedBuilding.id, payload })}
              onReclassifyLocal={(payload) => selectedLocal && reclassifyLocalMutation.mutate({ buildingId: selectedLocal.building_id, localId: selectedLocal.id, payload })}
              savePending={updateSiteMutation.isPending || updateBuildingMutation.isPending || updateLocalMutation.isPending}
              reclassifyPending={reclassifySiteMutation.isPending || reclassifyBuildingMutation.isPending || reclassifyLocalMutation.isPending}
              onDeleteSite={(id) => { if (window.confirm("Supprimer ce site ? Les bâtiments rattachés seront détachés (non supprimés).")) deleteSiteMutation.mutate(id); }}
              onDeleteBuilding={(id) => { if (window.confirm("Supprimer ce bâtiment et tous ses locaux ?")) deleteBuildingMutation.mutate(id); }}
              onDeleteLocal={(buildingId, localId) => { if (window.confirm("Supprimer ce local ?")) deleteLocalMutation.mutate({ buildingId, localId }); }}
              deletePending={deleteSiteMutation.isPending || deleteBuildingMutation.isPending || deleteLocalMutation.isPending}
              // Attachement
              attachMode={attachMode}
              attachSelectedFeatures={attachSelectedFeatures}
              onEnterAttach={enterAttach}
              onExitAttach={exitAttach}
              onAttachSuccess={onAttachSuccess}
              nearbyDgfipData={nearbyDgfipQuery.data ?? null}
              nearbyDgfipLoading={nearbyDgfipQuery.isLoading}
              freeAddressLookupData={freeAddressLookupQuery.data ?? null}
            />
          </div>
        </div>
      )}
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section création (bas de l'arborescence)
// ─────────────────────────────────────────────────────────────────────────────

function CreateSection({
  selectedNode, buildings, sites,
  showCreateSite, showCreateBuilding, showCreateLocal,
  onToggleSite, onToggleBuilding, onToggleLocal,
  onCreateSite, onCreateBuilding, onCreateLocal,
  createSitePending, createBuildingPending, createLocalPending,
}: {
  selectedNode: SelectedNode;
  buildings: Building[];
  sites: Site[];
  showCreateSite: boolean;
  showCreateBuilding: boolean;
  showCreateLocal: boolean;
  onToggleSite: () => void;
  onToggleBuilding: () => void;
  onToggleLocal: () => void;
  onCreateSite: (p: CreateSitePayload) => void;
  onCreateBuilding: (p: CreateBuildingPayload) => void;
  onCreateLocal: (buildingId: number, p: CreateLocalPayload) => void;
  createSitePending: boolean;
  createBuildingPending: boolean;
  createLocalPending: boolean;
}) {
  const [nomSite, setNomSite] = useState("");
  const [adresseSite, setAdresseSite] = useState("");
  const [nomBat, setNomBat] = useState("");
  const [communeBat, setCommuneBat] = useState("");
  const [siteIdBat, setSiteIdBat] = useState<number | null>(null);
  const [nomLocal, setNomLocal] = useState("");
  const [typeLocal, setTypeLocal] = useState("BUREAU");
  const [niveauLocal, setNiveauLocal] = useState("");

  // Contexte : site actuel sélectionné → préselection
  const activeSiteId =
    selectedNode?.type === "site"
      ? selectedNode.id
      : selectedNode?.type === "building"
        ? (buildings.find((b) => b.id === selectedNode.id)?.site_id ?? null)
        : null;

  const activeBuildingId =
    selectedNode?.type === "building"
      ? selectedNode.id
      : selectedNode?.type === "local"
        ? (buildings.find((b) => b.id === (buildings.find((bb) => bb.id === selectedNode.id)?.id ?? 0))?.id ?? null)
        : null;

  const [localBuildingId, setLocalBuildingId] = useState<number | null>(null);
  const targetBuildingId = localBuildingId ?? activeBuildingId ?? (buildings[0]?.id ?? null);

  return (
    <div className="patrimony-create-section">
      <div className="patrimony-create-header">
        <span className="patrimony-create-title">Ajouter</span>
        <div className="patrimony-create-buttons">
          <button type="button" className={`patrimony-create-btn${showCreateSite ? " is-active" : ""}`} onClick={onToggleSite}>+ Site</button>
          <button type="button" className={`patrimony-create-btn${showCreateBuilding ? " is-active" : ""}`} onClick={onToggleBuilding}>+ Bâtiment</button>
          <button type="button" className={`patrimony-create-btn${showCreateLocal ? " is-active" : ""}`} onClick={onToggleLocal} disabled={buildings.length === 0}>+ Local</button>
        </div>
      </div>

      {showCreateSite && (
        <form className="patrimony-create-form" onSubmit={(e: FormEvent) => { e.preventDefault(); onCreateSite({ nom_site: nomSite }); setNomSite(""); }}>
          <label className="field"><span>Nom du site *</span><input type="text" value={nomSite} onChange={(e) => setNomSite(e.target.value)} required placeholder="Ex : Groupe scolaire Jean Jaurès" autoFocus /></label>
          <div className="form-actions"><button type="submit" disabled={createSitePending}>{createSitePending ? "Création..." : "Créer le site"}</button></div>
        </form>
      )}

      {showCreateBuilding && (
        <form className="patrimony-create-form" onSubmit={(e: FormEvent) => {
          e.preventDefault();
          onCreateBuilding({ nom_batiment: nomBat, nom_commune: communeBat, adresse_reconstituee: adresseSite || undefined, site_id: siteIdBat ?? activeSiteId ?? undefined, create_default_local: false });
          setNomBat(""); setCommuneBat(""); setAdresseSite(""); setSiteIdBat(null);
        }}>
          <label className="field"><span>Nom du bâtiment *</span><input type="text" value={nomBat} onChange={(e) => setNomBat(e.target.value)} required placeholder="Ex : Gymnase Victor Hugo" autoFocus /></label>
          <label className="field"><span>Adresse *</span><input type="text" value={adresseSite} onChange={(e) => setAdresseSite(e.target.value)} required placeholder="Ex : 12 RUE DU PORT SÈTE" /></label>
          <label className="field"><span>Commune *</span><input type="text" value={communeBat} onChange={(e) => setCommuneBat(e.target.value)} required placeholder="Ex : Sète" /></label>
          <label className="field">
            <span>Site parent</span>
            <select value={siteIdBat ?? activeSiteId ?? ""} onChange={(e) => setSiteIdBat(e.target.value ? Number(e.target.value) : null)}>
              <option value="">— Aucun site —</option>
              {sites.map((s) => <option key={s.id} value={s.id}>{s.nom_site}</option>)}
            </select>
          </label>
          <div className="form-actions"><button type="submit" disabled={createBuildingPending}>{createBuildingPending ? "Création..." : "Créer le bâtiment"}</button></div>
        </form>
      )}

      {showCreateLocal && buildings.length > 0 && (
        <form className="patrimony-create-form" onSubmit={(e: FormEvent) => { e.preventDefault(); if (!targetBuildingId) return; onCreateLocal(targetBuildingId, { nom_local: nomLocal, type_local: typeLocal, niveau: niveauLocal || undefined }); setNomLocal(""); setNiveauLocal(""); }}>
          <label className="field">
            <span>Bâtiment parent *</span>
            <select value={targetBuildingId ?? ""} onChange={(e) => setLocalBuildingId(Number(e.target.value))}>
              {buildings.map((b) => <option key={b.id} value={b.id}>{b.nom_batiment || `Bâtiment #${b.id}`}</option>)}
            </select>
          </label>
          <label className="field"><span>Nom du local *</span><input type="text" value={nomLocal} onChange={(e) => setNomLocal(e.target.value)} required placeholder="Ex : Salle de classe 101" /></label>
          <label className="field">
            <span>Type</span>
            <select value={typeLocal} onChange={(e) => setTypeLocal(e.target.value)}>
              <option value="PRINCIPAL">Principal</option>
              <option value="BUREAU">Bureau</option>
              <option value="LOGEMENT">Logement</option>
              <option value="COMMERCE">Commerce</option>
              <option value="TECHNIQUE">Technique</option>
              <option value="ANNEXE">Annexe</option>
            </select>
          </label>
          <label className="field"><span>Niveau</span><input type="text" value={niveauLocal} onChange={(e) => setNiveauLocal(e.target.value)} placeholder="RDC, 1, 2…" /></label>
          <div className="form-actions"><button type="submit" disabled={createLocalPending || !targetBuildingId}>{createLocalPending ? "Création..." : "Créer le local"}</button></div>
        </form>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Panneau détail (dispatch)
// ─────────────────────────────────────────────────────────────────────────────

type DetailPanelProps = {
  selectedSite: Site | null;
  selectedBuilding: Building | null;
  selectedBuildingParentSite: Site | null;
  selectedLocal: Local | null;
  selectedLocalParent: Building | null;
  selectedLocalParentSite: Site | null;
  sites: Site[];
  buildings: Building[];
  siteBuildings: Building[];
  buildingLocals: Local[];
  editMode: boolean;
  onToggleEdit: () => void;
  onSaveSite: (p: UpdateSitePayload) => void;
  onSaveBuilding: (p: UpdateBuildingPayload) => void;
  onSaveLocal: (p: UpdateLocalPayload) => void;
  onReclassifySite: (p: ReclassifyPatrimonyPayload) => void;
  onReclassifyBuilding: (p: ReclassifyPatrimonyPayload) => void;
  onReclassifyLocal: (p: ReclassifyPatrimonyPayload) => void;
  savePending: boolean;
  reclassifyPending: boolean;
  onDeleteSite: (id: number) => void;
  onDeleteBuilding: (id: number) => void;
  onDeleteLocal: (buildingId: number, localId: number) => void;
  deletePending: boolean;
  // Attachement
  attachMode: AttachMode;
  attachSelectedFeatures: GeoJsonFeature[];
  onEnterAttach: (mode: "ign" | "dgfip") => void;
  onExitAttach: () => void;
  onAttachSuccess: () => void;
  nearbyDgfipData: NearbyDgfipResult | null;
  nearbyDgfipLoading: boolean;
  freeAddressLookupData: FreeAddressLookup | null;
};

function PatrimonyDetailPanel(props: DetailPanelProps) {
  const { selectedSite, selectedBuilding, selectedLocal, selectedLocalParent, onDeleteSite, onDeleteBuilding, onDeleteLocal, deletePending } = props;

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
        childBuildings={props.siteBuildings}
        sites={props.sites}
        buildings={props.buildings}
        editMode={props.editMode}
        onToggleEdit={props.onToggleEdit}
        onSave={props.onSaveSite}
        onReclassify={props.onReclassifySite}
        savePending={props.savePending}
        reclassifyPending={props.reclassifyPending}
        onDelete={() => onDeleteSite(selectedSite.id)}
        deletePending={deletePending}
      />
    );
  }

  if (selectedBuilding) {
    return (
      <BuildingDetail
        key={`building-${selectedBuilding.id}`}
        building={selectedBuilding}
        parentSite={props.selectedBuildingParentSite}
        sites={props.sites}
        buildings={props.buildings}
        childLocals={props.buildingLocals}
        editMode={props.editMode}
        onToggleEdit={props.onToggleEdit}
        onSave={props.onSaveBuilding}
        onReclassify={props.onReclassifyBuilding}
        savePending={props.savePending}
        reclassifyPending={props.reclassifyPending}
        onDelete={() => onDeleteBuilding(selectedBuilding.id)}
        deletePending={deletePending}
        attachMode={props.attachMode}
        attachSelectedFeatures={props.attachSelectedFeatures}
        onEnterAttach={props.onEnterAttach}
        onExitAttach={props.onExitAttach}
        onAttachSuccess={props.onAttachSuccess}
        nearbyDgfipData={props.nearbyDgfipData}
        nearbyDgfipLoading={props.nearbyDgfipLoading}
        freeAddressLookupData={props.freeAddressLookupData}
      />
    );
  }

  if (selectedLocal && selectedLocalParent) {
    return (
      <LocalDetail
        key={`local-${selectedLocal.id}`}
        local={selectedLocal}
        parent={selectedLocalParent}
        parentSite={props.selectedLocalParentSite}
        sites={props.sites}
        buildings={props.buildings}
        editMode={props.editMode}
        onToggleEdit={props.onToggleEdit}
        onSave={props.onSaveLocal}
        onReclassify={props.onReclassifyLocal}
        savePending={props.savePending}
        reclassifyPending={props.reclassifyPending}
        onDelete={() => onDeleteLocal(selectedLocal.building_id, selectedLocal.id)}
        deletePending={deletePending}
      />
    );
  }

  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Détail Site
// ─────────────────────────────────────────────────────────────────────────────

function ReclassifyControls({
  currentType,
  currentName,
  sites,
  buildings,
  currentBuildingId,
  defaultSiteId,
  defaultBuildingId,
  pending,
  onReclassify,
}: {
  currentType: PatrimonyNodeType;
  currentName: string;
  sites: Site[];
  buildings: Building[];
  currentBuildingId?: number | null;
  defaultSiteId?: number | null;
  defaultBuildingId?: number | null;
  pending: boolean;
  onReclassify: (p: ReclassifyPatrimonyPayload) => void;
}) {
  const [targetType, setTargetType] = useState<PatrimonyNodeType>(currentType);
  const [name, setName] = useState(currentName);
  const [targetSiteId, setTargetSiteId] = useState<number | null>(defaultSiteId ?? null);
  const [targetBuildingId, setTargetBuildingId] = useState<number | null>(defaultBuildingId ?? null);
  const eligibleBuildings = buildings.filter((building) => building.id !== currentBuildingId);
  const disabled = pending || targetType === currentType || (targetType === "local" && !targetBuildingId);

  return (
    <div className="section-block patrimony-reclassify-block">
      <div className="section-heading">
        <h4>Reclasser l'entite</h4>
        <p>Transforme l'entite selectionnee en une autre categorie quand elle a ete importee au mauvais niveau.</p>
      </div>
      <div className="form-grid">
        <label className="field">
          <span>Nouvelle categorie</span>
          <select value={targetType} onChange={(e) => setTargetType(e.target.value as PatrimonyNodeType)}>
            <option value="site">Site</option>
            <option value="building">Batiment</option>
            <option value="local">Local</option>
          </select>
        </label>
        <label className="field">
          <span>Nom apres reclassement</span>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        {targetType === "building" && (
          <label className="field">
            <span>Site parent</span>
            <select value={targetSiteId ?? ""} onChange={(e) => setTargetSiteId(e.target.value ? Number(e.target.value) : null)}>
              <option value="">Sans site</option>
              {sites.map((site) => <option key={site.id} value={site.id}>{site.nom_site}</option>)}
            </select>
          </label>
        )}
        {targetType === "local" && (
          <label className="field">
            <span>Batiment parent *</span>
            <select value={targetBuildingId ?? ""} onChange={(e) => setTargetBuildingId(e.target.value ? Number(e.target.value) : null)}>
              <option value="">Choisir un batiment</option>
              {eligibleBuildings.map((building) => (
                <option key={building.id} value={building.id}>{building.nom_batiment || `Batiment #${building.id}`}</option>
              ))}
            </select>
          </label>
        )}
      </div>
      <div className="form-actions">
        <button
          type="button"
          className="secondary-button"
          disabled={disabled}
          onClick={() => {
            if (!window.confirm("Confirmer le reclassement ? Cette action change la categorie de l'entite.")) return;
            onReclassify({
              target_type: targetType,
              target_site_id: targetSiteId,
              target_building_id: targetBuildingId,
              name: name || null,
            });
          }}
        >
          {pending ? "Reclassement..." : "Reclasser"}
        </button>
      </div>
    </div>
  );
}

function SiteDetail({ site, childBuildings, sites, buildings, editMode, onToggleEdit, onSave, onReclassify, savePending, reclassifyPending, onDelete, deletePending }: {
  site: Site; childBuildings: Building[]; sites: Site[]; buildings: Building[]; editMode: boolean;
  onToggleEdit: () => void; onSave: (p: UpdateSitePayload) => void; onReclassify: (p: ReclassifyPatrimonyPayload) => void; savePending: boolean; reclassifyPending: boolean;
  onDelete: () => void; deletePending: boolean;
}) {
  const [nomSite, setNomSite] = useState(site.nom_site);
  return (
    <div className="section-block">
      <div className="panel-header">
        <div className="section-heading"><h3>📍 Site sélectionné</h3><p>{childBuildings.length} bâtiment(s) rattaché(s)</p></div>
        <div style={{ display: "flex", gap: 8 }}>
          <button type="button" className="secondary-button" onClick={onToggleEdit}>{editMode ? "Annuler" : "Modifier"}</button>
          <button type="button" className="danger-button" onClick={onDelete} disabled={deletePending}>Supprimer</button>
        </div>
      </div>
      {editMode ? (
        <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); onSave({ nom_site: nomSite }); }}>
          <div className="form-grid">
            <label className="field"><span>Nom du site</span><input type="text" value={nomSite} onChange={(e) => setNomSite(e.target.value)} required /></label>
          </div>
          <div className="form-actions"><button type="submit" disabled={savePending}>{savePending ? "Enregistrement..." : "Enregistrer"}</button></div>
        </form>
      ) : (
        <>
          <div className="detail-grid">
            <div className="detail-card"><span>Nom</span><strong>{site.nom_site}</strong></div>
            <div className="detail-card"><span>Bâtiments rattachés</span><strong>{childBuildings.length}</strong></div>
            <div className="detail-card"><span>Source</span><strong>{site.source_file || "Saisie manuelle"}</strong></div>
          </div>
          {childBuildings.length > 0 && (
            <div className="section-block">
              <div className="section-heading"><h4>Bâtiments rattachés</h4></div>
              <ul style={{ paddingLeft: 20 }}>
                {childBuildings.map((b) => (
                  <li key={b.id}>
                    {b.nom_batiment || `Bâtiment #${b.id}`}
                    {b.statut_geocodage === "IGN_VALIDE" && <span style={{ color: "#15803d", marginLeft: 6 }}>● IGN</span>}
                    <span style={{ color: "#6b7280", marginLeft: 6, fontSize: 12 }}>{buildAddressLine(b)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <ReclassifyControls
            currentType="site"
            currentName={site.nom_site}
            sites={sites.filter((candidate) => candidate.id !== site.id)}
            buildings={buildings}
            pending={reclassifyPending}
            onReclassify={onReclassify}
          />
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Détail Bâtiment — fiche complète + attachement IGN/DGFIP inline
// ─────────────────────────────────────────────────────────────────────────────

function BuildingDetail({
  building, parentSite, sites, buildings, childLocals, editMode, onToggleEdit, onSave, onReclassify, savePending, reclassifyPending, onDelete, deletePending,
  attachMode, attachSelectedFeatures, onEnterAttach, onExitAttach, onAttachSuccess,
  nearbyDgfipData, nearbyDgfipLoading, freeAddressLookupData,
}: {
  building: Building; parentSite: Site | null; sites: Site[]; buildings: Building[]; childLocals: Local[];
  editMode: boolean; onToggleEdit: () => void;
  onSave: (p: UpdateBuildingPayload) => void; onReclassify: (p: ReclassifyPatrimonyPayload) => void; savePending: boolean; reclassifyPending: boolean;
  onDelete: () => void; deletePending: boolean;
  attachMode: AttachMode;
  attachSelectedFeatures: GeoJsonFeature[];
  onEnterAttach: (mode: "ign" | "dgfip") => void;
  onExitAttach: () => void;
  onAttachSuccess: () => void;
  nearbyDgfipData: NearbyDgfipResult | null;
  nearbyDgfipLoading: boolean;
  freeAddressLookupData: FreeAddressLookup | null;
}) {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  const [nomBatiment, setNomBatiment] = useState(building.nom_batiment ?? "");
  const [adresseReconstituee, setAdresseReconstituee] = useState(building.adresse_reconstituee ?? "");
  const [nomCommune, setNomCommune] = useState(building.nom_commune);
  const [codePostal, setCodePostal] = useState(building.code_postal ?? "");
  const [siteId, setSiteId] = useState<number | null>(building.site_id ?? null);

  // Compteurs rattachés
  const meterLinksQuery = useQuery({
    queryKey: ["building-meters", building.id, token],
    queryFn: () => fetchBuildingMeterLinks(token as string, building.id),
    enabled: Boolean(token),
    retry: false,
  });

  // Mutations attachement
  const [attachError, setAttachError] = useState<string | null>(null);
  const [attachSuccess, setAttachSuccess] = useState<string | null>(null);
  const [selectedDgfipKey, setSelectedDgfipKey] = useState<string | null>(null);

  const attachIgnMutation = useMutation({
    mutationFn: (payload: BuildingIgnAttachmentPayload) => attachBuildingIgnRequest(token as string, building.id, payload),
    onSuccess: async (updated) => {
      setAttachSuccess(`Attachement IGN réalisé : « ${updated.nom_batiment || `#${updated.id}`} ».`);
      setAttachError(null);
      onAttachSuccess();
      await queryClient.invalidateQueries({ queryKey: ["buildings", token] });
    },
    onError: (err: unknown) => { setAttachError(err instanceof Error ? err.message : "Attachement IGN impossible."); },
  });

  const attachGeoMutation = useMutation({
    mutationFn: (payload: { unique_key: string; validated_name?: string; selected_feature?: GeoJsonFeature | null; selected_features?: GeoJsonFeature[] }) =>
      attachBuildingGeoRequest(token as string, building.id, payload),
    onSuccess: async (updated) => {
      setAttachSuccess(`Attachement DGFIP + IGN réalisé : « ${updated.nom_batiment || `#${updated.id}`} ».`);
      setAttachError(null);
      setSelectedDgfipKey(null);
      onAttachSuccess();
      await queryClient.invalidateQueries({ queryKey: ["buildings", token] });
    },
    onError: (err: unknown) => { setAttachError(err instanceof Error ? err.message : "Attachement impossible."); },
  });

  async function handleConfirmIgnAttach() {
    setAttachError(null);
    setAttachSuccess(null);
    const lat = freeAddressLookupData?.lat ?? building.latitude ?? null;
    const lon = freeAddressLookupData?.lon ?? building.longitude ?? null;
    await attachIgnMutation.mutateAsync({
      selected_features: attachSelectedFeatures.length > 0 ? attachSelectedFeatures : undefined,
      lat,
      lon,
    });
  }

  async function handleConfirmDgfipAttach() {
    if (!selectedDgfipKey) return;
    setAttachError(null);
    setAttachSuccess(null);
    await attachGeoMutation.mutateAsync({ unique_key: selectedDgfipKey });
  }

  const ignFeatures = parseIgnFeatures(building.ign_features_json);
  const majicBuilding = parseJsonArray(building.majic_building_values_json);
  const majicEntry = parseJsonArray(building.majic_entry_values_json);
  const majicLevel = parseJsonArray(building.majic_level_values_json);
  const majicDoor = parseJsonArray(building.majic_door_values_json);
  const parcelLabels = parseJsonArray(building.parcel_labels_json);
  const attachmentPending = attachIgnMutation.isPending || attachGeoMutation.isPending;

  return (
    <div className="section-block">
      {/* ── En-tête avec statut + boutons ── */}
      <div className="panel-header">
        <div className="section-heading">
          <h3>🏢 Bâtiment sélectionné</h3>
          <p>
            {building.statut_geocodage === "IGN_VALIDE" ? "✓ IGN attaché · " : "○ IGN non attaché · "}
            {childLocals.length} local(aux)
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button type="button" className="secondary-button" onClick={onToggleEdit}>{editMode ? "Annuler" : "Modifier"}</button>
          <button
            type="button"
            className={`secondary-button${attachMode === "ign" ? " is-active-attach" : ""}`}
            onClick={() => attachMode === "ign" ? onExitAttach() : onEnterAttach("ign")}
          >
            {attachMode === "ign" ? "✕ Fermer IGN" : "Attacher IGN"}
          </button>
          <button
            type="button"
            className={`secondary-button${attachMode === "dgfip" ? " is-active-attach" : ""}`}
            onClick={() => attachMode === "dgfip" ? onExitAttach() : onEnterAttach("dgfip")}
          >
            {attachMode === "dgfip" ? "✕ Fermer DGFIP" : "Attacher DGFIP"}
          </button>
          <button type="button" className="danger-button" onClick={onDelete} disabled={deletePending}>Supprimer</button>
        </div>
      </div>

      {/* ── Messages ── */}
      {attachError && <p className="error-text">{attachError}</p>}
      {attachSuccess && <p className="success-text">{attachSuccess}</p>}

      {/* ── Confirmation IGN ── */}
      {attachMode === "ign" && (
        <div className="info-banner" style={{ borderColor: "#f97316" }}>
          <strong>Attachement IGN en cours sur la carte.</strong>
          <p>Cliquez les polygones jaunes sur la carte pour les sélectionner ({attachSelectedFeatures.length} sélectionné(s)).</p>
          {attachSelectedFeatures.length > 0 && (
            <ul style={{ paddingLeft: 16, marginTop: 8 }}>
              {attachSelectedFeatures.map((f, i) => (
                <li key={i}>{String(f.properties?.label ?? f.properties?.ign_id ?? `Polygone #${i + 1}`)}</li>
              ))}
            </ul>
          )}
          <div className="form-actions" style={{ marginTop: 8 }}>
            {attachSelectedFeatures.length > 0 && (
              <button type="button" onClick={() => void handleConfirmIgnAttach()} disabled={attachmentPending}>
                {attachmentPending ? "Attachement en cours..." : `Valider l'attachement IGN (${attachSelectedFeatures.length} polygone(s))`}
              </button>
            )}
            <button type="button" className="secondary-button" onClick={onExitAttach}>Annuler</button>
          </div>
        </div>
      )}

      {/* ── Sélection DGFIP ── */}
      {attachMode === "dgfip" && (
        <div className="section-block">
          <div className="section-heading"><h4>Adresses DGFIP / MAJIC proches (200 m)</h4></div>
          {nearbyDgfipLoading && <p>Recherche des adresses proches...</p>}
          {nearbyDgfipData?.majic_configured === false && (
            <div className="info-banner" style={{ background: "#fff4e6", borderColor: "#e07a5f" }}>
              <strong>Source MAJIC non disponible.</strong>
              <p>Le fichier DGFIP / MAJIC n'est pas configuré côté backend.</p>
            </div>
          )}
          {nearbyDgfipData?.rows.length === 0 && nearbyDgfipData.majic_configured && (
            <p className="empty-state-text">Aucune adresse DGFIP trouvée dans un rayon de 200 m.</p>
          )}
          <div className="resource-list">
            {(nearbyDgfipData?.rows ?? []).map((row: NearbyDgfipRow) => {
              const isActive = selectedDgfipKey === row.unique_key;
              return (
                <article key={row.unique_key} className={`resource-card${isActive ? " resource-card-active" : ""}`}>
                  <div className="resource-card-header">
                    <div><h3>{row.address_display}</h3><p>{row.nom_commune}</p></div>
                    <span className="resource-badge">{row.distance_m} m</span>
                  </div>
                  <dl className="resource-metadata">
                    <div><dt>Indices MAJIC</dt><dd>{row.majic_building_values.join(", ") || "Aucun"}</dd></div>
                  </dl>
                  <div className="resource-card-actions">
                    <button type="button" className="secondary-button" onClick={() => setSelectedDgfipKey(isActive ? null : row.unique_key)}>
                      {isActive ? "Désélectionner" : "Sélectionner"}
                    </button>
                    {isActive && (
                      <button type="button" onClick={() => void handleConfirmDgfipAttach()} disabled={attachmentPending}>
                        {attachmentPending ? "En cours..." : "Valider l'attachement DGFIP"}
                      </button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
          <div className="form-actions"><button type="button" className="secondary-button" onClick={onExitAttach}>Annuler</button></div>
        </div>
      )}

      {/* ── Formulaire d'édition ── */}
      {editMode ? (
        <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); onSave({ nom_batiment: nomBatiment || null, adresse_reconstituee: adresseReconstituee || null, nom_commune: nomCommune, code_postal: codePostal || null, site_id: siteId }); }}>
          <div className="form-grid">
            <label className="field"><span>Nom du bâtiment</span><input type="text" value={nomBatiment} onChange={(e) => setNomBatiment(e.target.value)} /></label>
            <label className="field">
              <span>Site parent</span>
              <select value={siteId ?? ""} onChange={(e) => setSiteId(e.target.value ? Number(e.target.value) : null)}>
                <option value="">Sans site</option>
                {sites.map((site) => <option key={site.id} value={site.id}>{site.nom_site}</option>)}
              </select>
            </label>
            <label className="field"><span>Commune</span><input type="text" value={nomCommune} onChange={(e) => setNomCommune(e.target.value)} required /></label>
            <label className="field"><span>Code postal</span><input type="text" value={codePostal} onChange={(e) => setCodePostal(e.target.value)} maxLength={10} /></label>
            <label className="field"><span>Adresse reconstituée</span><input type="text" value={adresseReconstituee} onChange={(e) => setAdresseReconstituee(e.target.value)} /></label>
          </div>
          <div className="form-actions"><button type="submit" disabled={savePending}>{savePending ? "Enregistrement..." : "Enregistrer"}</button></div>
        </form>
      ) : (
        <>
          {/* ── Fiche complète ── */}
          <div className="detail-grid">
            <div className="detail-card"><span>Nom</span><strong>{building.nom_batiment || "—"}</strong></div>
            <div className="detail-card"><span>Site parent</span><strong>{parentSite?.nom_site ?? "Sans site"}</strong></div>
            <div className="detail-card"><span>Adresse</span><strong>{buildAddressLine(building)}</strong></div>
            <div className="detail-card"><span>Commune</span><strong>{building.nom_commune}</strong></div>
            <div className="detail-card"><span>Code postal</span><strong>{building.code_postal || "—"}</strong></div>
            <div className="detail-card"><span>Statut géocodage</span><strong>{building.statut_geocodage}</strong></div>
            <div className="detail-card"><span>Source de création</span><strong>{building.source_creation}</strong></div>
            <div className="detail-card">
              <span>Coordonnées</span>
              <strong>{building.latitude != null && building.longitude != null ? `${building.latitude.toFixed(5)}, ${building.longitude.toFixed(5)}` : "Non géolocalisé"}</strong>
            </div>
            <div className="detail-card"><span>Référence DGFIP</span><strong>{building.dgfip_reference_norm ?? "—"}</strong></div>
            <div className="detail-card">
              <span>Référence cadastrale</span>
              <strong>{[building.prefixe, building.section, building.numero_plan].filter(Boolean).join(" ") || "—"}</strong>
            </div>
            {parcelLabels.length > 0 && (
              <div className="detail-card"><span>Parcelles</span><strong>{parcelLabels.join(", ")}</strong></div>
            )}
            {building.ign_id && (
              <>
                <div className="detail-card"><span>Nom IGN retenu</span><strong>{building.ign_name_proposed || building.ign_name || "—"}</strong></div>
                <div className="detail-card"><span>ID IGN</span><strong>{building.ign_id}</strong></div>
              </>
            )}
          </div>

          {/* Attributs IGN multi-polygones */}
          {ignFeatures.length > 0 && (
            <div className="section-block">
              <div className="section-heading">
                <h4>Attributs IGN ({ignFeatures.length} polygone(s))</h4>
                <p>{ignFeatures.length > 1 ? "★ = polygone principal." : "Attributs BD TOPO."}</p>
              </div>
              {ignFeatures.map((feat, idx) => (
                <div key={feat.ign_id || idx} className="section-block" style={{ marginTop: 8 }}>
                  <div className="section-heading">
                    <h4>{idx === 0 ? "★ " : `#${idx + 1} `}{feat.resolved_name || feat.label || feat.ign_id}{idx === 0 ? " (principal)" : ""}</h4>
                    <p>{feat.ign_layer} · {feat.ign_id}</p>
                  </div>
                  {feat.attributes.length > 0 && (
                    <div className="attribute-table">
                      {feat.attributes.map(([k, v]) => <div key={k} className="attribute-row"><dt>{k}</dt><dd>{v}</dd></div>)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Indices MAJIC */}
          {(majicBuilding.length > 0 || majicEntry.length > 0) && (
            <div className="section-block">
              <div className="section-heading"><h4>Indices MAJIC</h4></div>
              <div className="detail-grid">
                <div className="detail-card"><span>Bâtiment</span><strong>{majicBuilding.join(", ") || "—"}</strong></div>
                <div className="detail-card"><span>Entrée</span><strong>{majicEntry.join(", ") || "—"}</strong></div>
                {majicLevel.length > 0 && <div className="detail-card"><span>Niveau</span><strong>{majicLevel.join(", ")}</strong></div>}
                {majicDoor.length > 0 && <div className="detail-card"><span>Porte</span><strong>{majicDoor.join(", ")}</strong></div>}
              </div>
            </div>
          )}

          {/* Compteurs rattachés */}
          <div className="section-block">
            <div className="section-heading"><h4>Compteurs rattachés</h4></div>
            {meterLinksQuery.isLoading && <p style={{ color: "#94a3b8" }}>Chargement compteurs...</p>}
            {!meterLinksQuery.isLoading && (meterLinksQuery.data?.length ?? 0) === 0 && (
              <p style={{ color: "#94a3b8", fontSize: 13 }}>Aucun compteur rattaché. <Link to={`/buildings/${building.id}`} className="secondary-link">Ajouter sur la fiche complète.</Link></p>
            )}
            {(meterLinksQuery.data ?? []).map((m: BuildingMeterLink) => (
              <div key={m.id} className="resource-card" style={{ marginTop: 8 }}>
                <div className="resource-card-header">
                  <div><h3>{m.meter_label || m.meter_identifier}</h3><p>{m.meter_identifier}</p></div>
                  <span className="resource-badge">{m.fluid}</span>
                </div>
                <dl className="resource-metadata">
                  <div><dt>Fournisseur</dt><dd>{m.supplier_name || "—"}</dd></div>
                  <div><dt>Contexte</dt><dd>{m.contract_context || "—"}</dd></div>
                </dl>
              </div>
            ))}
          </div>

          {/* Locaux */}
          {childLocals.length > 0 && (
            <div className="section-block">
              <div className="section-heading"><h4>Locaux ({childLocals.length})</h4></div>
              <ul style={{ paddingLeft: 20 }}>
                {childLocals.map((l) => (
                  <li key={l.id}>
                    {l.nom_local}
                    {l.niveau && <span style={{ color: "#9ca3af", marginLeft: 6 }}>· niv. {l.niveau}</span>}
                    <span style={{ color: "#6b7280", marginLeft: 6, fontSize: 12 }}>{l.type_local}</span>
                    {l.surface_m2 && <span style={{ color: "#6b7280", marginLeft: 6, fontSize: 12 }}>{l.surface_m2} m²</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <ReclassifyControls
            currentType="building"
            currentName={building.nom_batiment || `Batiment #${building.id}`}
            sites={sites}
            buildings={buildings}
            currentBuildingId={building.id}
            defaultSiteId={building.site_id}
            pending={reclassifyPending}
            onReclassify={onReclassify}
          />

        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Détail Local
// ─────────────────────────────────────────────────────────────────────────────

function LocalDetail({ local, parent, parentSite, sites, buildings, editMode, onToggleEdit, onSave, onReclassify, savePending, reclassifyPending, onDelete, deletePending }: {
  local: Local; parent: Building; parentSite: Site | null; sites: Site[]; buildings: Building[]; editMode: boolean;
  onToggleEdit: () => void; onSave: (p: UpdateLocalPayload) => void; onReclassify: (p: ReclassifyPatrimonyPayload) => void; savePending: boolean; reclassifyPending: boolean;
  onDelete: () => void; deletePending: boolean;
}) {
  const [nomLocal, setNomLocal] = useState(local.nom_local);
  const [typeLocal, setTypeLocal] = useState(local.type_local);
  const [niveau, setNiveau] = useState(local.niveau ?? "");
  const [surfaceM2, setSurfaceM2] = useState(local.surface_m2?.toString() ?? "");
  const [usage, setUsage] = useState(local.usage ?? "");
  const [statutOccupation, setStatutOccupation] = useState(local.statut_occupation ?? "");
  const [buildingId, setBuildingId] = useState(local.building_id);

  return (
    <div className="section-block">
      <div className="panel-header">
        <div className="section-heading">
          <h3>◇ Local sélectionné</h3>
          <p>Site : <strong>{parentSite?.nom_site ?? "Sans site"}</strong> · Bâtiment : <strong>{parent.nom_batiment || `#${parent.id}`}</strong></p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button type="button" className="secondary-button" onClick={onToggleEdit}>{editMode ? "Annuler" : "Modifier"}</button>
          <button type="button" className="danger-button" onClick={onDelete} disabled={deletePending}>Supprimer</button>
        </div>
      </div>
      {editMode ? (
        <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); const s = surfaceM2.trim() ? Number(surfaceM2.replace(",", ".")) : null; onSave({ building_id: buildingId, nom_local: nomLocal, type_local: typeLocal, niveau: niveau || null, surface_m2: Number.isFinite(s as number) ? (s as number) : null, usage: usage || null, statut_occupation: statutOccupation || null }); }}>
          <div className="form-grid">
            <label className="field">
              <span>Bâtiment parent</span>
              <select value={buildingId} onChange={(e) => setBuildingId(Number(e.target.value))}>
                {buildings.map((building) => <option key={building.id} value={building.id}>{building.nom_batiment || `Batiment #${building.id}`}</option>)}
              </select>
            </label>
            <label className="field"><span>Nom</span><input type="text" value={nomLocal} onChange={(e) => setNomLocal(e.target.value)} required /></label>
            <label className="field"><span>Type</span><input type="text" value={typeLocal} onChange={(e) => setTypeLocal(e.target.value)} required /></label>
            <label className="field"><span>Niveau</span><input type="text" value={niveau} onChange={(e) => setNiveau(e.target.value)} /></label>
            <label className="field"><span>Surface (m²)</span><input type="number" step="0.01" value={surfaceM2} onChange={(e) => setSurfaceM2(e.target.value)} /></label>
            <label className="field"><span>Usage</span><input type="text" value={usage} onChange={(e) => setUsage(e.target.value)} /></label>
            <label className="field"><span>Statut occupation</span><input type="text" value={statutOccupation} onChange={(e) => setStatutOccupation(e.target.value)} /></label>
          </div>
          <div className="form-actions"><button type="submit" disabled={savePending}>{savePending ? "Enregistrement..." : "Enregistrer"}</button></div>
        </form>
      ) : (
        <>
        <div className="detail-grid">
          <div className="detail-card"><span>Nom</span><strong>{local.nom_local}</strong></div>
          <div className="detail-card"><span>Site parent</span><strong>{parentSite?.nom_site ?? "Sans site"}</strong></div>
          <div className="detail-card"><span>Bâtiment parent</span><strong>{parent.nom_batiment || `Batiment #${parent.id}`}</strong></div>
          <div className="detail-card"><span>Type</span><strong>{local.type_local}</strong></div>
          <div className="detail-card"><span>Niveau</span><strong>{local.niveau || "—"}</strong></div>
          <div className="detail-card"><span>Surface</span><strong>{local.surface_m2 ? `${local.surface_m2} m²` : "—"}</strong></div>
          <div className="detail-card"><span>Usage</span><strong>{local.usage || "—"}</strong></div>
          <div className="detail-card"><span>Statut occupation</span><strong>{local.statut_occupation || "—"}</strong></div>
          {local.commentaire && <div className="detail-card" style={{ gridColumn: "1/-1" }}><span>Commentaire</span><strong>{local.commentaire}</strong></div>}
        </div>
        <ReclassifyControls
          currentType="local"
          currentName={local.nom_local}
          sites={sites}
          buildings={buildings}
          defaultSiteId={parent.site_id}
          defaultBuildingId={parent.id}
          pending={reclassifyPending}
          onReclassify={onReclassify}
        />
        </>
      )}
    </div>
  );
}
