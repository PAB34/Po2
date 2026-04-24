import { useEffect, useMemo, useRef, useState } from "react";

import type { GeoJsonFeatureCollection } from "../lib/api";

type BuildingNamingMapProps = {
  addressLabel: string;
  lat: number | null;
  lon: number | null;
  usedSource: string;
  parcelFeatureCollection?: GeoJsonFeatureCollection | null;
  featureCollection?: GeoJsonFeatureCollection | null;
  selectedFeatureId: string;
  onSelectFeatureId: (featureId: string) => void;
};

type RuntimeFeature = {
  properties?: Record<string, unknown>;
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
};

type LeafletRuntime = {
  map: (element: HTMLDivElement, options: Record<string, unknown>) => RuntimeMap;
  tileLayer: ((url: string, options: Record<string, unknown>) => RuntimeLayer) & {
    wms?: (url: string, options: Record<string, unknown>) => RuntimeLayer;
  };
  circleMarker: (coords: [number, number], options: Record<string, unknown>) => RuntimeLayer;
  layerGroup: (layers?: RuntimeLayer[]) => RuntimeLayer;
  geoJSON: (data?: unknown, options?: Record<string, unknown>) => RuntimeGeoJsonLayer;
  featureGroup: () => RuntimeFeatureGroup;
};

type WindowWithLeaflet = Window & {
  L?: LeafletRuntime;
  __po2LeafletLoader__?: Promise<LeafletRuntime>;
};

function getFeatureId(feature: RuntimeFeature | null | undefined) {
  const properties = feature?.properties ?? {};
  return String(properties.ign_id ?? properties.id ?? "");
}

function getFeatureLabel(feature: RuntimeFeature | null | undefined) {
  const properties = feature?.properties ?? {};
  return String(properties.resolved_label ?? properties.label ?? properties.name ?? "Objet IGN");
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
      { once: true }
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

export function BuildingNamingMap({
  addressLabel,
  lat,
  lon,
  usedSource,
  parcelFeatureCollection,
  featureCollection,
  selectedFeatureId,
  onSelectFeatureId,
}: BuildingNamingMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const runtimeRef = useRef<LeafletRuntime | null>(null);
  const mapRef = useRef<RuntimeMap | null>(null);
  const centerLayerRef = useRef<RuntimeLayer | null>(null);
  const parcelLayerRef = useRef<RuntimeGeoJsonLayer | null>(null);
  const buildingLayerRef = useRef<RuntimeGeoJsonLayer | null>(null);
  const [mapReady, setMapReady] = useState(false);

  const osmUrl = useMemo(() => {
    if (lat == null || lon == null) {
      return null;
    }
    return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=19/${lat}/${lon}`;
  }, [lat, lon]);

  const geoportailUrl = useMemo(() => {
    if (lat == null || lon == null) {
      return null;
    }
    return `https://www.geoportail.gouv.fr/carte?c=${lon},${lat}&z=18&l0=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&permalink=yes`;
  }, [lat, lon]);

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
      centerLayerRef.current = null;
      parcelLayerRef.current = null;
      buildingLayerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const runtime = runtimeRef.current;
    const map = mapRef.current;
    if (!runtime || !map || !mapReady) {
      return;
    }

    centerLayerRef.current?.remove?.();
    parcelLayerRef.current?.remove?.();
    buildingLayerRef.current?.remove?.();
    centerLayerRef.current = null;
    parcelLayerRef.current = null;
    buildingLayerRef.current = null;

    const focusGroup = runtime.featureGroup();

    if (lat != null && lon != null) {
      const centerMarker = runtime.circleMarker([lat, lon], {
        radius: 7,
        color: "#38bdf8",
        fillColor: "#0ea5e9",
        fillOpacity: 0.95,
        weight: 2,
      });
      centerMarker.bindPopup?.(`<strong>${addressLabel}</strong><br/>Source de centrage : ${usedSource}`);
      const centerLayer = runtime.featureGroup();
      centerLayer.addLayer(centerMarker);
      centerLayer.addTo(map);
      focusGroup.addLayer(centerMarker);
      centerLayerRef.current = centerLayer;
    }

    if (parcelFeatureCollection?.features?.length) {
      const parcelLayer = runtime.geoJSON(undefined, {
        style: {
          color: "#22c55e",
          weight: 2,
          fillColor: "#22c55e",
          fillOpacity: 0.08,
        },
      });
      parcelLayer.addData(parcelFeatureCollection);
      parcelLayer.addTo(map);
      focusGroup.addLayer(parcelLayer);
      parcelLayerRef.current = parcelLayer;
    }

    if (featureCollection?.features?.length) {
      const buildingLayer = runtime.geoJSON(undefined, {
        style: (feature: RuntimeFeature) => {
          const featureId = getFeatureId(feature);
          const isSelected = featureId !== "" && featureId === selectedFeatureId;
          return {
            color: isSelected ? "#f97316" : "#facc15",
            weight: isSelected ? 3 : 2,
            fillColor: isSelected ? "#fb923c" : "#fde047",
            fillOpacity: isSelected ? 0.38 : 0.16,
          };
        },
        pointToLayer: (feature: RuntimeFeature, latlng: { lat: number; lng: number }) => {
          const featureId = getFeatureId(feature);
          const isSelected = featureId !== "" && featureId === selectedFeatureId;
          return runtime.circleMarker([latlng.lat, latlng.lng], {
            radius: isSelected ? 8 : 6,
            color: isSelected ? "#f97316" : "#facc15",
            fillColor: isSelected ? "#fb923c" : "#fde047",
            fillOpacity: 0.9,
            weight: 2,
          });
        },
        onEachFeature: (feature: RuntimeFeature, layer: RuntimeLayer) => {
          const featureId = getFeatureId(feature);
          const label = getFeatureLabel(feature);
          layer.bindPopup?.(`<strong>${label}</strong><br/>ID IGN : ${featureId || "inconnu"}`);
          layer.on?.("click", () => {
            if (featureId) {
              onSelectFeatureId(featureId);
            }
          });
        },
      });
      buildingLayer.addData(featureCollection);
      buildingLayer.addTo(map);
      focusGroup.addLayer(buildingLayer);
      buildingLayerRef.current = buildingLayer;
    }

    if (featureCollection?.features?.length && buildingLayerRef.current) {
      const buildingBounds = focusGroup.getBounds();
      if (buildingBounds.isValid()) {
        map.fitBounds(buildingBounds.pad(0.12));
      } else if (lat != null && lon != null) {
        map.setView([lat, lon], 19);
      }
    } else if (parcelFeatureCollection?.features?.length) {
      const parcelBounds = focusGroup.getBounds();
      if (parcelBounds.isValid()) {
        map.fitBounds(parcelBounds.pad(0.12));
      } else if (lat != null && lon != null) {
        map.setView([lat, lon], 19);
      }
    } else if (lat != null && lon != null) {
      map.setView([lat, lon], 19);
    }
    map.invalidateSize?.();
    window.setTimeout(() => map.invalidateSize?.(), 50);

    return () => {
      focusGroup.clearLayers();
    };
  }, [addressLabel, featureCollection, lat, lon, mapReady, onSelectFeatureId, parcelFeatureCollection, selectedFeatureId, usedSource]);

  return (
    <div className="map-shell">
      <div className="map-toolbar">
        <span>
          Carte centrée sur <strong>{addressLabel}</strong>.
        </span>
        <div className="map-toolbar-actions">
          {osmUrl ? (
            <a className="secondary-link" href={osmUrl} target="_blank" rel="noreferrer">
              Ouvrir dans OSM
            </a>
          ) : null}
          {geoportailUrl ? (
            <a className="secondary-link" href={geoportailUrl} target="_blank" rel="noreferrer">
              Ouvrir dans Géoportail
            </a>
          ) : null}
        </div>
      </div>
      <div ref={containerRef} className="map-canvas" />
      <div className="map-legend">
        <span><strong>Bleu</strong> : point de centrage</span>
        <span><strong>Vert</strong> : parcelles détectées</span>
        <span><strong>Jaune</strong> : candidats IGN</span>
        <span><strong>Orange</strong> : bâtiment sélectionné</span>
      </div>
    </div>
  );
}
