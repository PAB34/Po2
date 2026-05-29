import { useEffect, useMemo, useRef, useState } from "react";

import type { Building, GeoJsonFeature } from "../lib/api";

// ---------------------------------------------------------------------------
// Types Leaflet runtime (injectés via CDN)
// ---------------------------------------------------------------------------

type RuntimeFeature = {
  properties?: Record<string, unknown>;
  geometry?: Record<string, unknown>;
  id?: unknown;
};

type RuntimeLayer = {
  addTo: (target: RuntimeMap | RuntimeFeatureGroup) => RuntimeLayer;
  remove?: () => void;
  bindPopup?: (html: string) => RuntimeLayer;
  on?: (event: string, handler: () => void) => void;
};

type RuntimeBounds = {
  isValid: () => boolean;
  pad: (ratio: number) => RuntimeBounds;
};

type RuntimeMap = {
  setView: (coords: [number, number], zoom: number) => RuntimeMap;
  fitBounds: (bounds: RuntimeBounds) => void;
  remove: () => void;
  invalidateSize?: () => void;
};

type RuntimeFeatureGroup = RuntimeLayer & {
  addLayer: (layer: RuntimeLayer) => void;
  clearLayers: () => void;
  getBounds: () => RuntimeBounds;
};

type RuntimeGeoJsonLayer = RuntimeLayer & {
  addData: (data: unknown) => void;
  clearLayers?: () => void;
};

type LeafletRuntime = {
  map: (element: HTMLDivElement, options: Record<string, unknown>) => RuntimeMap;
  tileLayer: ((url: string, options: Record<string, unknown>) => RuntimeLayer) & {
    wms?: (url: string, options: Record<string, unknown>) => RuntimeLayer;
  };
  circleMarker: (coords: [number, number], options: Record<string, unknown>) => RuntimeLayer;
  featureGroup: () => RuntimeFeatureGroup;
  geoJSON: (data?: unknown, options?: Record<string, unknown>) => RuntimeGeoJsonLayer;
};

type WindowWithLeaflet = Window & {
  L?: LeafletRuntime;
  __po2LeafletLoader__?: Promise<LeafletRuntime>;
};

type MappableBuilding = Building & { latitude: number; longitude: number };

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

type BuildingPortfolioMapProps = {
  buildings: Building[];
  activeBuildingId: number | null;
  onSelectBuildingId: (buildingId: number) => void;
  highlightedBuildingIds?: number[];
  focusLatLon?: { lat: number; lon: number } | null;
  // --- Mode attachement IGN ---
  // Quand attachMode === "ign" :
  //   - La carte se centre sur attachLat/Lon
  //   - Les polygones WFS BDTOPO sont chargés directement depuis le navigateur
  //   - Clic sur un polygone → onToggleAttachFeature
  attachMode?: "none" | "ign";
  attachLat?: number | null;
  attachLon?: number | null;
  attachAddress?: string | null;
  attachSelectedIds?: string[];
  onSelectAttachFeature?: (feature: GeoJsonFeature) => void;
  onDeselectAttachFeatureId?: (featureId: string) => void;
  isAttachLoading?: boolean; // overlay "Chargement..." sur la carte
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildAddressLine(
  building: Pick<Building, "numero_voirie" | "nature_voie" | "nom_voie" | "adresse_reconstituee" | "nom_commune">,
) {
  if (building.adresse_reconstituee) return building.adresse_reconstituee;
  const parts = [building.numero_voirie, building.nature_voie, building.nom_voie].filter(Boolean);
  return parts.length > 0 ? `${parts.join(" ")}, ${building.nom_commune}` : building.nom_commune;
}

function ensureStylesheet(documentRef: Document, href: string) {
  const existing = Array.from(documentRef.querySelectorAll("link")).find(
    (node) => node.getAttribute("href") === href,
  );
  if (existing) return;
  const link = documentRef.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  documentRef.head.appendChild(link);
}

function ensureScript(documentRef: Document, src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = Array.from(documentRef.querySelectorAll("script")).find(
      (node) => node.getAttribute("src") === src,
    );
    if (existing) {
      if (existing.getAttribute("data-loaded") === "true") {
        resolve();
        return;
      }
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Chargement Leaflet impossible.")), { once: true });
      return;
    }
    const script = documentRef.createElement("script");
    script.src = src;
    script.async = true;
    script.addEventListener("load", () => { script.setAttribute("data-loaded", "true"); resolve(); }, { once: true });
    script.addEventListener("error", () => reject(new Error("Chargement Leaflet impossible.")), { once: true });
    documentRef.head.appendChild(script);
  });
}

function ensureLeafletRuntime(): Promise<LeafletRuntime> {
  const runtimeWindow = window as WindowWithLeaflet;
  if (runtimeWindow.L) return Promise.resolve(runtimeWindow.L);
  if (runtimeWindow.__po2LeafletLoader__) return runtimeWindow.__po2LeafletLoader__;
  runtimeWindow.__po2LeafletLoader__ = (async () => {
    ensureStylesheet(document, "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css");
    await ensureScript(document, "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js");
    if (!runtimeWindow.L) throw new Error("Leaflet indisponible dans le navigateur.");
    return runtimeWindow.L;
  })();
  return runtimeWindow.__po2LeafletLoader__;
}

/** Bounding box (minx, miny, maxx, maxy) autour d'un point, rayon en mètres. */
function bboxAround(lat: number, lon: number, radiusM: number): [number, number, number, number] {
  const deltaLat = radiusM / 111320;
  const deltaLon = radiusM / Math.max(111320 * Math.cos((lat * Math.PI) / 180), 1e-6);
  return [lon - deltaLon, lat - deltaLat, lon + deltaLon, lat + deltaLat];
}

/** ID d'un feature WFS brut. */
function wfsFeatureId(feature: RuntimeFeature): string {
  return String(
    feature.id ??
      feature.properties?.cleabs ??
      feature.properties?.id_local ??
      feature.properties?.id ??
      "",
  );
}

/** Label d'un feature WFS brut. */
function wfsFeatureLabel(feature: RuntimeFeature): string {
  return String(
    feature.properties?.nom_usuel ??
      feature.properties?.nature ??
      feature.properties?.usage_1 ??
      "Bâtiment IGN",
  );
}

/**
 * Normalise un feature WFS brut (BDTOPO) au format attendu par le backend
 * (champs ign_id, ign_layer, resolved_name… dans properties).
 */
function normalizeWfsFeature(feature: RuntimeFeature, featureId: string): GeoJsonFeature {
  const props = feature.properties ?? {};
  return {
    type: "Feature",
    geometry: feature.geometry,
    properties: {
      ign_id: featureId,
      ign_layer: "batiment",
      ign_typename: "BDTOPO_V3:batiment",
      name: String(props.nom_usuel ?? ""),
      label: String(props.nom_usuel ?? props.nature ?? featureId),
      resolved_name: String(props.nom_usuel ?? ""),
      resolved_name_source: "bdtopo_client",
      attributes: props,
    },
  };
}

// ---------------------------------------------------------------------------
// Composant
// ---------------------------------------------------------------------------

export function BuildingPortfolioMap({
  buildings,
  activeBuildingId,
  onSelectBuildingId,
  highlightedBuildingIds,
  focusLatLon,
  attachMode = "none",
  attachLat,
  attachLon,
  attachAddress,
  attachSelectedIds,
  onSelectAttachFeature,
  onDeselectAttachFeatureId,
  isAttachLoading = false,
}: BuildingPortfolioMapProps) {
  const highlightedSet = useMemo(() => new Set(highlightedBuildingIds ?? []), [highlightedBuildingIds]);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const runtimeRef = useRef<LeafletRuntime | null>(null);
  const mapRef = useRef<RuntimeMap | null>(null);
  const buildingsLayerRef = useRef<RuntimeFeatureGroup | null>(null);
  const attachLayerRef = useRef<RuntimeGeoJsonLayer | null>(null);
  const centerMarkerRef = useRef<RuntimeLayer | null>(null);
  const [mapReady, setMapReady] = useState(false);

  // WFS data fetched client-side (mode attachement IGN)
  const [wfsData, setWfsData] = useState<{ features: RuntimeFeature[] } | null>(null);
  const [wfsLoading, setWfsLoading] = useState(false);
  const [wfsError, setWfsError] = useState<string | null>(null);

  const mappableBuildings = useMemo(
    () =>
      buildings.filter(
        (b): b is MappableBuilding => typeof b.latitude === "number" && typeof b.longitude === "number",
      ),
    [buildings],
  );

  const selectedBuilding = useMemo(
    () => mappableBuildings.find((b) => b.id === activeBuildingId) ?? mappableBuildings[0] ?? null,
    [activeBuildingId, mappableBuildings],
  );

  const osmUrl = useMemo(() => {
    if (!selectedBuilding) return null;
    return `https://www.openstreetmap.org/?mlat=${selectedBuilding.latitude}&mlon=${selectedBuilding.longitude}#map=18/${selectedBuilding.latitude}/${selectedBuilding.longitude}`;
  }, [selectedBuilding]);

  // ------------------------------------------------------------------
  // Init Leaflet
  // ------------------------------------------------------------------
  useEffect(() => {
    let disposed = false;
    async function mountMap() {
      if (!containerRef.current || mapRef.current) return;
      const runtime = await ensureLeafletRuntime();
      if (disposed || !containerRef.current) return;
      runtimeRef.current = runtime;
      const map = runtime
        .map(containerRef.current, { zoomControl: true, attributionControl: true, preferCanvas: false })
        .setView([43.4028, 3.6928], 13);
      if (runtime.tileLayer.wms) {
        runtime.tileLayer
          .wms("https://data.geopf.fr/wms-r?", {
            layers: "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2",
            format: "image/png",
            transparent: false,
            version: "1.3.0",
            attribution: "&copy; IGN Géoplateforme",
          })
          .addTo(map);
      } else {
        runtime
          .tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 22,
            attribution: "&copy; OpenStreetMap contributors",
          })
          .addTo(map);
      }
      mapRef.current = map;
      setMapReady(true);
      window.setTimeout(() => map.invalidateSize?.(), 0);
      window.setTimeout(() => map.invalidateSize?.(), 80);
    }
    void mountMap();
    return () => {
      disposed = true;
      setMapReady(false);
      mapRef.current?.remove();
      mapRef.current = null;
      buildingsLayerRef.current = null;
      attachLayerRef.current = null;
      centerMarkerRef.current = null;
    };
  }, []);

  // ------------------------------------------------------------------
  // Couche bâtiments du patrimoine (markers circulaires)
  // ------------------------------------------------------------------
  useEffect(() => {
    const runtime = runtimeRef.current;
    const map = mapRef.current;
    if (!runtime || !map || !mapReady) return;

    buildingsLayerRef.current?.remove?.();
    buildingsLayerRef.current = null;

    if (mappableBuildings.length === 0) {
      map.setView([43.4028, 3.6928], 13);
      return;
    }

    const layerGroup = runtime.featureGroup();
    const dimInAttach = attachMode === "ign"; // assombrissement des markers hors-mode

    for (const building of mappableBuildings) {
      const isActive = building.id === (activeBuildingId ?? selectedBuilding?.id ?? null);
      const isHighlighted = highlightedSet.has(building.id);
      const hasIgn = building.statut_geocodage === "IGN_VALIDE";

      let color = dimInAttach ? "#94a3b8" : "#38bdf8";
      let fillColor = dimInAttach ? "#94a3b8" : "#0ea5e9";

      if (!dimInAttach) {
        if (isActive) { color = "#f97316"; fillColor = "#fb923c"; }
        else if (isHighlighted && hasIgn) { color = "#15803d"; fillColor = "#16a34a"; }
        else if (isHighlighted) { color = "#ea580c"; fillColor = "#f97316"; }
        else if (hasIgn) { color = "#1d4ed8"; fillColor = "#2563eb"; }
      } else if (isActive) {
        color = "#f97316"; fillColor = "#fb923c";
      }

      const marker = runtime.circleMarker([building.latitude, building.longitude], {
        radius: isActive ? 9 : dimInAttach ? 5 : isHighlighted ? 8 : 7,
        color,
        fillColor,
        fillOpacity: dimInAttach && !isActive ? 0.45 : 0.92,
        weight: isActive ? 3 : 2,
      });
      marker.bindPopup?.(
        `<strong>${building.nom_batiment || `Bâtiment #${building.id}`}</strong><br/>${buildAddressLine(building)}${hasIgn ? "<br/><em>IGN attaché</em>" : ""}`,
      );
      marker.on?.("click", () => {
        if (attachMode === "none") onSelectBuildingId(building.id);
      });
      layerGroup.addLayer(marker);
    }

    layerGroup.addTo(map);
    buildingsLayerRef.current = layerGroup;

    if (attachMode !== "ign") {
      // Cadrage normal (non-attach)
      if (focusLatLon) {
        map.setView([focusLatLon.lat, focusLatLon.lon], 18);
      } else if (highlightedSet.size > 0) {
        const hGroup = runtime.featureGroup();
        for (const b of mappableBuildings) {
          if (highlightedSet.has(b.id)) hGroup.addLayer(runtime.circleMarker([b.latitude, b.longitude], { radius: 1, opacity: 0 }));
        }
        const hBounds = hGroup.getBounds();
        if (hBounds.isValid()) map.fitBounds(hBounds.pad(0.3));
        else {
          const bounds = layerGroup.getBounds();
          if (bounds.isValid()) map.fitBounds(bounds.pad(0.18));
        }
      } else {
        const bounds = layerGroup.getBounds();
        if (bounds.isValid()) map.fitBounds(bounds.pad(0.18));
        else if (selectedBuilding) map.setView([selectedBuilding.latitude, selectedBuilding.longitude], 17);
      }
    }

    map.invalidateSize?.();
    window.setTimeout(() => map.invalidateSize?.(), 50);
    return () => { layerGroup.clearLayers(); };
  }, [activeBuildingId, mapReady, mappableBuildings, onSelectBuildingId, selectedBuilding, highlightedSet, focusLatLon, attachMode]);

  // ------------------------------------------------------------------
  // Fetch WFS client-side quand on entre en mode attachement IGN
  // ------------------------------------------------------------------
  useEffect(() => {
    if (attachMode !== "ign" || attachLat == null || attachLon == null) {
      setWfsData(null);
      setWfsError(null);
      return;
    }
    setWfsLoading(true);
    setWfsError(null);
    setWfsData(null);
    const [minx, miny, maxx, maxy] = bboxAround(attachLat, attachLon, 200);
    const url =
      `https://data.geopf.fr/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature` +
      `&typeNames=BDTOPO_V3:batiment` +
      `&bbox=${minx},${miny},${maxx},${maxy},EPSG:4326` +
      `&srsName=EPSG:4326&outputFormat=application/json&count=150`;
    fetch(url)
      .then((r) => r.json())
      .then((data: { features?: RuntimeFeature[] }) => {
        setWfsData({ features: data.features ?? [] });
        setWfsLoading(false);
      })
      .catch(() => {
        setWfsError("Impossible de charger les polygones IGN depuis le navigateur.");
        setWfsLoading(false);
      });
  }, [attachMode, attachLat, attachLon]);

  // ------------------------------------------------------------------
  // Couche attachement IGN : centre + polygones WFS sélectionnables
  // ------------------------------------------------------------------
  useEffect(() => {
    const runtime = runtimeRef.current;
    const map = mapRef.current;
    if (!runtime || !map || !mapReady) return;

    // Nettoyage des couches d'attachement
    attachLayerRef.current?.remove?.();
    centerMarkerRef.current?.remove?.();
    attachLayerRef.current = null;
    centerMarkerRef.current = null;

    if (attachMode !== "ign" || attachLat == null || attachLon == null) return;

    // Centrage sur le bâtiment sélectionné
    map.setView([attachLat, attachLon], 18);
    window.setTimeout(() => map.invalidateSize?.(), 50);

    // Marqueur de centrage (adresse géocodée)
    const centerMarker = runtime.circleMarker([attachLat, attachLon], {
      radius: 9,
      color: "#38bdf8",
      fillColor: "#0ea5e9",
      fillOpacity: 0.95,
      weight: 3,
      zIndexOffset: 1000,
    });
    centerMarker.bindPopup?.(
      `<strong>${attachAddress ?? "Position géocodée"}</strong><br/><em>Centre de recherche IGN</em>`,
    );
    centerMarker.addTo(map);
    centerMarkerRef.current = centerMarker;

    // Polygones WFS BDTOPO (si chargés)
    if (!wfsData?.features?.length) return;

    const selectedIdsSet = new Set(attachSelectedIds ?? []);
    const geoLayer = runtime.geoJSON(undefined, {
      style: (feature: RuntimeFeature) => {
        const fid = wfsFeatureId(feature);
        const selected = Boolean(fid && selectedIdsSet.has(fid));
        return {
          color: selected ? "#f97316" : "#facc15",
          weight: selected ? 3 : 2,
          fillColor: selected ? "#fb923c" : "#fde047",
          fillOpacity: selected ? 0.45 : 0.2,
          interactive: true,
        };
      },
      onEachFeature: (feature: RuntimeFeature, layer: RuntimeLayer) => {
        const fid = wfsFeatureId(feature);
        const label = wfsFeatureLabel(feature);
        const selected = Boolean(fid && selectedIdsSet.has(fid));
        layer.bindPopup?.(
          `<strong>${label}</strong><br/>ID : ${fid || "inconnu"}<br/><em>${selected ? "✓ Sélectionné" : "Cliquer pour sélectionner"}</em>`,
        );
        layer.on?.("click", () => {
          if (!fid) return;
          if (selectedIdsSet.has(fid)) {
            onDeselectAttachFeatureId?.(fid);
          } else {
            onSelectAttachFeature?.(normalizeWfsFeature(feature, fid));
          }
        });
      },
    });
    geoLayer.addData({ type: "FeatureCollection", features: wfsData.features });
    geoLayer.addTo(map);
    attachLayerRef.current = geoLayer;
  }, [attachMode, attachLat, attachLon, attachAddress, attachSelectedIds, wfsData, mapReady, onSelectAttachFeature, onDeselectAttachFeatureId]);

  // ------------------------------------------------------------------
  // Rendu
  // ------------------------------------------------------------------

  if (mappableBuildings.length === 0 && attachMode === "none") {
    return (
      <div className="empty-state map-empty-state">
        <strong>Aucun bâtiment géolocalisé.</strong>
        <span>La carte apparaîtra dès qu'au moins un bâtiment disposera de coordonnées.</span>
      </div>
    );
  }

  const showOverlay = isAttachLoading || wfsLoading;
  const overlayText =
    isAttachLoading
      ? "Géocodage en cours..."
      : wfsLoading
        ? "Chargement des polygones IGN..."
        : null;

  return (
    <div className="map-shell">
      <div className="map-toolbar">
        <span>
          {attachMode === "ign" ? (
            <>
              Mode attachement IGN ·{" "}
              {wfsData ? (
                <strong>
                  {wfsData.features.length} polygone(s) BDTOPO ·{" "}
                  {(attachSelectedIds?.length ?? 0)} sélectionné(s)
                </strong>
              ) : (
                <em>{wfsError ?? "Chargement..."}</em>
              )}
            </>
          ) : (
            <span>{mappableBuildings.length} bâtiment(s) affiché(s).</span>
          )}
        </span>
        <div className="map-toolbar-actions">
          {osmUrl && attachMode === "none" ? (
            <a className="secondary-link" href={osmUrl} target="_blank" rel="noreferrer">
              Ouvrir dans OSM
            </a>
          ) : null}
        </div>
      </div>

      {/* Carte Leaflet */}
      <div style={{ position: "relative" }}>
        <div ref={containerRef} className="map-canvas" />
        {showOverlay ? (
          <div className="map-loading-overlay">
            <div className="map-loading-spinner" />
            <span>{overlayText}</span>
          </div>
        ) : null}
        {wfsError && attachMode === "ign" ? (
          <div className="map-loading-overlay map-loading-overlay--error">
            <span>⚠ {wfsError}</span>
          </div>
        ) : null}
      </div>

      <div className="map-legend">
        {attachMode === "ign" ? (
          <>
            <span><strong>Bleu</strong> : position géocodée</span>
            <span><strong>Jaune</strong> : polygone IGN (cliquer)</span>
            <span><strong>Orange</strong> : polygone sélectionné</span>
          </>
        ) : (
          <>
            <span><strong>Bleu</strong> : bâtiments</span>
            <span><strong>Orange</strong> : bâtiment actif</span>
          </>
        )}
      </div>
    </div>
  );
}
