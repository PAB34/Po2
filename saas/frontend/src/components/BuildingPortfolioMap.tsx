import { useEffect, useMemo, useRef, useState } from "react";

import type { Building } from "../lib/api";

type BuildingPortfolioMapProps = {
  buildings: Building[];
  activeBuildingId: number | null;
  onSelectBuildingId: (buildingId: number) => void;
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

type LeafletRuntime = {
  map: (element: HTMLDivElement, options: Record<string, unknown>) => RuntimeMap;
  tileLayer: ((url: string, options: Record<string, unknown>) => RuntimeLayer) & {
    wms?: (url: string, options: Record<string, unknown>) => RuntimeLayer;
  };
  circleMarker: (coords: [number, number], options: Record<string, unknown>) => RuntimeLayer;
  featureGroup: () => RuntimeFeatureGroup;
};

type WindowWithLeaflet = Window & {
  L?: LeafletRuntime;
  __po2LeafletLoader__?: Promise<LeafletRuntime>;
};

type MappableBuilding = Building & {
  latitude: number;
  longitude: number;
};

function buildAddressLine(building: Pick<Building, "numero_voirie" | "nature_voie" | "nom_voie" | "adresse_reconstituee" | "nom_commune">) {
  if (building.adresse_reconstituee) {
    return building.adresse_reconstituee;
  }

  const parts = [building.numero_voirie, building.nature_voie, building.nom_voie].filter(Boolean);
  return parts.length > 0 ? `${parts.join(" ")}, ${building.nom_commune}` : building.nom_commune;
}

function ensureStylesheet(documentRef: Document, href: string) {
  const existing = Array.from(documentRef.querySelectorAll("link")).find((node) => node.getAttribute("href") === href);
  if (existing) {
    return;
  }
  const link = documentRef.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  documentRef.head.appendChild(link);
}

function ensureScript(documentRef: Document, src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = Array.from(documentRef.querySelectorAll("script")).find((node) => node.getAttribute("src") === src);
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
    script.addEventListener(
      "load",
      () => {
        script.setAttribute("data-loaded", "true");
        resolve();
      },
      { once: true },
    );
    script.addEventListener("error", () => reject(new Error("Chargement Leaflet impossible.")), { once: true });
    documentRef.head.appendChild(script);
  });
}

function ensureLeafletRuntime(): Promise<LeafletRuntime> {
  const runtimeWindow = window as WindowWithLeaflet;
  if (runtimeWindow.L) {
    return Promise.resolve(runtimeWindow.L);
  }
  if (runtimeWindow.__po2LeafletLoader__) {
    return runtimeWindow.__po2LeafletLoader__;
  }
  runtimeWindow.__po2LeafletLoader__ = (async () => {
    ensureStylesheet(document, "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css");
    await ensureScript(document, "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js");
    if (!runtimeWindow.L) {
      throw new Error("Leaflet indisponible dans le navigateur.");
    }
    return runtimeWindow.L;
  })();
  return runtimeWindow.__po2LeafletLoader__;
}

export function BuildingPortfolioMap({ buildings, activeBuildingId, onSelectBuildingId }: BuildingPortfolioMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const runtimeRef = useRef<LeafletRuntime | null>(null);
  const mapRef = useRef<RuntimeMap | null>(null);
  const buildingsLayerRef = useRef<RuntimeFeatureGroup | null>(null);
  const [mapReady, setMapReady] = useState(false);

  const mappableBuildings = useMemo(
    () =>
      buildings.filter(
        (building): building is MappableBuilding => typeof building.latitude === "number" && typeof building.longitude === "number",
      ),
    [buildings],
  );

  const selectedBuilding = useMemo(
    () => mappableBuildings.find((building: MappableBuilding) => building.id === activeBuildingId) ?? mappableBuildings[0] ?? null,
    [activeBuildingId, mappableBuildings],
  );

  const osmUrl = useMemo(() => {
    if (!selectedBuilding) {
      return null;
    }
    return `https://www.openstreetmap.org/?mlat=${selectedBuilding.latitude}&mlon=${selectedBuilding.longitude}#map=18/${selectedBuilding.latitude}/${selectedBuilding.longitude}`;
  }, [selectedBuilding]);

  useEffect(() => {
    let disposed = false;
    async function mountMap() {
      if (!containerRef.current || mapRef.current) {
        return;
      }
      const runtime = await ensureLeafletRuntime();
      if (disposed || !containerRef.current) {
        return;
      }
      runtimeRef.current = runtime;
      const map = runtime.map(containerRef.current, {
        zoomControl: true,
        attributionControl: true,
        preferCanvas: true,
      }).setView([43.4028, 3.6928], 13);
      if (runtime.tileLayer.wms) {
        runtime.tileLayer.wms("https://data.geopf.fr/wms-r?", {
          layers: "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2",
          format: "image/png",
          transparent: false,
          version: "1.3.0",
          attribution: "&copy; IGN Géoplateforme",
        }).addTo(map);
      } else {
        runtime.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 22,
          attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);
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
    };
  }, []);

  useEffect(() => {
    const runtime = runtimeRef.current;
    const map = mapRef.current;
    if (!runtime || !map || !mapReady) {
      return;
    }

    buildingsLayerRef.current?.remove?.();
    buildingsLayerRef.current = null;

    if (mappableBuildings.length === 0) {
      map.setView([43.4028, 3.6928], 13);
      return;
    }

    const layerGroup = runtime.featureGroup();
    for (const building of mappableBuildings) {
      const isActive = building.id === (activeBuildingId ?? selectedBuilding?.id ?? null);
      const marker = runtime.circleMarker([building.latitude, building.longitude], {
        radius: isActive ? 9 : 7,
        color: isActive ? "#f97316" : "#38bdf8",
        fillColor: isActive ? "#fb923c" : "#0ea5e9",
        fillOpacity: 0.92,
        weight: isActive ? 3 : 2,
      });
      marker.bindPopup?.(`<strong>${building.nom_batiment || `Bâtiment #${building.id}`}</strong><br/>${buildAddressLine(building)}`);
      marker.on?.("click", () => onSelectBuildingId(building.id));
      layerGroup.addLayer(marker);
    }

    layerGroup.addTo(map);
    buildingsLayerRef.current = layerGroup;

    const bounds = layerGroup.getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds.pad(0.18));
    } else if (selectedBuilding) {
      map.setView([selectedBuilding.latitude, selectedBuilding.longitude], 17);
    }
    map.invalidateSize?.();
    window.setTimeout(() => map.invalidateSize?.(), 50);

    return () => {
      layerGroup.clearLayers();
    };
  }, [activeBuildingId, mapReady, mappableBuildings, onSelectBuildingId, selectedBuilding]);

  if (mappableBuildings.length === 0) {
    return (
      <div className="empty-state map-empty-state">
        <strong>Aucun bâtiment géolocalisé.</strong>
        <span>La carte apparaîtra dès qu’au moins un bâtiment disposera de coordonnées.</span>
      </div>
    );
  }

  return (
    <div className="map-shell">
      <div className="map-toolbar">
        <span>
          {mappableBuildings.length} bâtiment(s) affiché(s) sur la carte.
        </span>
        <div className="map-toolbar-actions">
          {osmUrl ? (
            <a className="secondary-link" href={osmUrl} target="_blank" rel="noreferrer">
              Ouvrir dans OSM
            </a>
          ) : null}
        </div>
      </div>
      <div ref={containerRef} className="map-canvas" />
      <div className="map-legend">
        <span><strong>Bleu</strong> : bâtiments affichés</span>
        <span><strong>Orange</strong> : bâtiment actif</span>
      </div>
    </div>
  );
}
