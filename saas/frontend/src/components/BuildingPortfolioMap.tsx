import { useEffect, useMemo, useRef, useState } from "react";
import Leaflet from "leaflet";
import "leaflet/dist/leaflet.css";

import type { Building, GeoJsonFeature, GeoJsonFeatureCollection } from "../lib/api";

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
  contains?: (point: [number, number]) => boolean;
};

type RuntimeMap = {
  setView: (coords: [number, number], zoom: number) => RuntimeMap;
  fitBounds: (bounds: RuntimeBounds, options?: Record<string, unknown>) => void;
  remove: () => void;
  invalidateSize?: () => void;
  on?: (event: string, handler: (payload: unknown) => void) => void;
  getBounds?: () => RuntimeBounds;
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

/** Marqueur déplaçable : `getLatLng` donne la position après un glisser-déposer. */
type RuntimeMarker = RuntimeLayer & {
  getLatLng: () => { lat: number; lng: number };
  setLatLng?: (coords: [number, number]) => RuntimeMarker;
};

type LeafletRuntime = {
  map: (element: HTMLDivElement, options: Record<string, unknown>) => RuntimeMap;
  tileLayer: ((url: string, options: Record<string, unknown>) => RuntimeLayer) & {
    wms?: (url: string, options: Record<string, unknown>) => RuntimeLayer;
  };
  circleMarker: (coords: [number, number], options: Record<string, unknown>) => RuntimeLayer;
  polyline?: (
    coords: [number, number][],
    options: Record<string, unknown>,
  ) => RuntimeLayer;
  marker: (coords: [number, number], options: Record<string, unknown>) => RuntimeMarker;
  divIcon: (options: Record<string, unknown>) => unknown;
  featureGroup: () => RuntimeFeatureGroup;
  geoJSON: (data?: unknown, options?: Record<string, unknown>) => RuntimeGeoJsonLayer;
};

/** Un bien du référentiel historique (ASTECH) posé sur la carte. */
export type LegacyMapPoint = {
  id: number;
  label: string;
  latitude: number;
  longitude: number;
  /** `true` quand le point n'a pas encore été confirmé (posé par défaut, à déplacer). */
  isProvisional?: boolean;
  /** `true` quand le bien est rattaché à un bâtiment Po2 : point vert. */
  isLinked?: boolean;
  /** `true` quand la cible est un LOCAL et non le bâtiment entier. */
  isLocalTarget?: boolean;
  /**
   * `true` quand le rattachement est une **proposition du moteur non confirmée**.
   * Sans cette distinction, une suggestion s'affichait du même vert qu'un rattachement
   * validé par un humain : impossible de savoir ce qui avait réellement été décidé.
   */
  isProposal?: boolean;
  /** Bâtiment Po2 porteur : centre de l'araignée à laquelle ce bien est relié. */
  buildingId?: number | null;
  /** Nom du bâtiment porteur, rappelé dans la bulle du bien. */
  buildingLabel?: string | null;
};

/**
 * Un marqueur ASTECH réellement dessiné — **un seul bien** par marqueur.
 *
 * Les biens rattachés à un même bâtiment sont disposés en ARAIGNÉE autour de lui : le
 * bâtiment reste au centre à sa vraie position, chaque bien est posé à ~15 m et relié
 * par un trait. Chacun garde ainsi sa pastille, donc reste sélectionnable et
 * détachable — ce qu'un point fusionné interdisait dès qu'un rattachement était faux.
 */
type LegacyRenderMarker = {
  points: LegacyMapPoint[];
  latitude: number;
  longitude: number;
  buildingId: number | null;
  buildingLabel: string | null;
  /** `true` quand ce marqueur tient lieu de bâtiment : il ne doit pas être décalé. */
  isBuildingAnchor: boolean;
  /** Décalage visuel appliqué (patte d'araignée), à retrancher au déplacement. */
  offsetLat: number;
  offsetLon: number;
};

/** Un trait reliant un bien ASTECH au bâtiment qui le porte. */
type LegacySpiderLeg = {
  fromLat: number;
  fromLon: number;
  toLat: number;
  toLon: number;
  isLocalTarget: boolean;
  /** Proposition non confirmée : trait ambre, comme la pastille. */
  isProposal: boolean;
};

type WindowWithLeaflet = Window & {
  L?: LeafletRuntime;
  __po2LeafletLoader__?: Promise<LeafletRuntime>;
};

type MappableBuilding = Building & { latitude: number; longitude: number };

/** Zoom de travail sur un bien : assez pres pour distinguer les batiments, mais dans
    la plage ou OpenStreetMap fournit encore des tuiles nettes. */
const FOCUS_ZOOM = 18;
// Rayon des pattes d'araignee : ~15 m. Assez pour separer les pastilles et laisser voir
// le batiment au centre, assez peu pour qu'on lise l'appartenance au meme batiment.
const SPIDER_RADIUS_DEG = 15 / 111_320;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

type BuildingPortfolioMapProps = {
  buildings: Building[];
  activeBuildingId: number | null;
  onSelectBuildingId: (buildingId: number) => void;
  highlightedBuildingIds?: number[];
  focusLatLon?: { lat: number; lon: number } | null;
  /** Polygones IGN déjà attachés à afficher en mode portfolio (bleu translucide). */
  portfolioIgnFeatures?: GeoJsonFeatureCollection | null;
  // --- Mode attachement IGN ---
  // Quand attachMode === "ign" :
  //   - La carte se centre sur attachLat/Lon
  //   - Les polygones de attachFeatureCollection sont rendus sur la carte
  //   - Clic sur un polygone → onSelectAttachFeature / onDeselectAttachFeatureId
  attachMode?: "none" | "ign";
  attachLat?: number | null;
  attachLon?: number | null;
  attachAddress?: string | null;
  attachFeatureCollection?: GeoJsonFeatureCollection | null; // polygones WFS depuis le serveur
  attachSelectedIds?: string[];
  onSelectAttachFeature?: (feature: GeoJsonFeature) => void;
  onDeselectAttachFeatureId?: (featureId: string) => void;
  isAttachLoading?: boolean; // overlay "Chargement..." sur la carte
  // --- Biens du référentiel historique (ASTECH) ---
  // Couleur dédiée (violet), distincte des bâtiments du patrimoine. Le marqueur actif
  // est déplaçable : au lâcher, `onMoveLegacyPoint` reçoit la nouvelle position.
  legacyPoints?: LegacyMapPoint[];
  activeLegacyId?: number | null;
  onSelectLegacyId?: (legacyId: number) => void;
  onMoveLegacyPoint?: (legacyId: number, lat: number, lon: number) => void;
  /**
   * Appele quand le point ASTECH est lache SUR un batiment Po2 (a moins de
   * `legacyDropRadiusM` metres). Le geste « je depose le point sur le batiment »
   * vaut rattachement : le bien herite alors des informations du batiment.
   */
  onDropLegacyOnBuilding?: (legacyId: number, buildingId: number) => void;
  /** Rayon d'accrochage du depot, en metres. */
  legacyDropRadiusM?: number;
  /**
   * Bâtiment Po2 rendu déplaçable. Un seul à la fois — comme pour les points ASTECH,
   * cela évite de déplacer un voisin par mégarde en naviguant sur la carte.
   */
  draggableBuildingId?: number | null;
  onMoveBuilding?: (buildingId: number, lat: number, lon: number) => void;
  /**
   * Clic sur le FOND de carte (ni marqueur, ni polygone) : sert à sortir de la
   * sélection en cours. Voir `markerClickAtRef` pour la distinction avec un clic
   * sur un marqueur.
   */
  onBackgroundClick?: () => void;
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

/**
 * Ecarte les marqueurs qui partagent exactement la meme position.
 *
 * Cas qui l'impose : un bien qu'on vient de DETACHER de son batiment garde la position
 * qu'il en avait heritee. Il se retrouvait alors pile sous le marqueur du batiment, donc
 * invisible — le detachement semblait sans effet.
 *
 * Le marqueur **ancre** (celui qui represente le batiment, c'est-a-dire le groupe
 * fusionne) ne bouge pas : c'est lui qui dit ou est le batiment. Ce sont les autres qui
 * sont disposes autour. Le decalage est purement visuel, la position enregistree ne
 * change pas tant qu'on ne deplace pas le point a la main.
 */
function spreadCoLocatedMarkers(markers: LegacyRenderMarker[]): LegacyRenderMarker[] {
  const groups = new Map<string, LegacyRenderMarker[]>();
  for (const marker of markers) {
    const key = `${marker.latitude.toFixed(5)}|${marker.longitude.toFixed(5)}`;
    groups.set(key, [...(groups.get(key) ?? []), marker]);
  }

  const spread: LegacyRenderMarker[] = [];
  for (const group of groups.values()) {
    if (group.length === 1) {
      spread.push(group[0]);
      continue;
    }
    // L'ancre est le marqueur qui tient lieu de batiment ; a defaut, le premier.
    const anchorIndex = Math.max(
      0,
      group.findIndex((marker) => marker.isBuildingAnchor),
    );
    const others = group.filter((_, index) => index !== anchorIndex);
    spread.push(group[anchorIndex]);
    // ~14 m de rayon : assez pour separer les pastilles sans mentir sur la position.
    const radiusDeg = 14 / 111_320;
    others.forEach((marker, index) => {
      const angle = (2 * Math.PI * index) / others.length;
      spread.push({
        ...marker,
        latitude: marker.latitude + radiusDeg * Math.cos(angle),
        longitude:
          marker.longitude +
          (radiusDeg * Math.sin(angle)) / Math.max(0.2, Math.cos((marker.latitude * Math.PI) / 180)),
      });
    });
  }
  return spread;
}

/** Distance approximative entre deux points, en metres. */
function distanceMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000;
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

function toCoordinate(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
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
  if (Leaflet) return Promise.resolve(Leaflet as unknown as LeafletRuntime);

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

/** ID d'un feature IGN (serveur ou brut WFS). */
function wfsFeatureId(feature: RuntimeFeature): string {
  // Les features serveur ont ign_id dans properties (priorité absolue).
  // Les features bruts WFS ont l'id dans feature.id ou properties.cleabs.
  const val =
    feature.properties?.ign_id ??
    feature.id ??
    feature.properties?.cleabs ??
    feature.properties?.id_local ??
    feature.properties?.id ??
    "";
  return String(val);
}

/** Label d'un feature IGN (serveur ou brut WFS). */
function wfsFeatureLabel(feature: RuntimeFeature): string {
  // Les features serveur ont resolved_name / label / name.
  const val =
    feature.properties?.resolved_name ??
    feature.properties?.label ??
    feature.properties?.name ??
    feature.properties?.nom_usuel ??
    feature.properties?.nature ??
    feature.properties?.usage_1 ??
    "Bâtiment IGN";
  return String(val);
}

/**
 * Normalise un feature WFS brut (BDTOPO) au format attendu par le backend
 * (champs ign_id, ign_layer, resolved_name… dans properties).
 */
function normalizeWfsFeature(feature: RuntimeFeature, featureId: string): GeoJsonFeature {
  const props = feature.properties ?? {};
  return {
    type: "Feature",
    geometry: (feature.geometry ?? null) as GeoJsonFeature["geometry"],
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
  portfolioIgnFeatures,
  attachMode = "none",
  attachLat,
  attachLon,
  attachAddress,
  attachFeatureCollection,
  attachSelectedIds,
  onSelectAttachFeature,
  onDeselectAttachFeatureId,
  isAttachLoading = false,
  legacyPoints,
  activeLegacyId = null,
  onSelectLegacyId,
  onMoveLegacyPoint,
  onDropLegacyOnBuilding,
  legacyDropRadiusM = 30,
  draggableBuildingId = null,
  onMoveBuilding,
  onBackgroundClick,
}: BuildingPortfolioMapProps) {
  const highlightedSet = useMemo(() => new Set(highlightedBuildingIds ?? []), [highlightedBuildingIds]);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const runtimeRef = useRef<LeafletRuntime | null>(null);
  const mapRef = useRef<RuntimeMap | null>(null);
  const buildingsLayerRef = useRef<RuntimeFeatureGroup | null>(null);
  const portfolioIgnLayerRef = useRef<RuntimeGeoJsonLayer | null>(null);
  const attachLayerRef = useRef<RuntimeGeoJsonLayer | null>(null);
  const centerMarkerRef = useRef<RuntimeLayer | null>(null);
  const legacyLayerRef = useRef<RuntimeFeatureGroup | null>(null);
  // Derniere « intention de cadrage » appliquee : evite de rezoomer a chaque
  // rafraichissement de donnees (cf. bloc de cadrage plus bas).
  const framingSignatureRef = useRef<string | null>(null);
  // Horodatage du dernier clic sur un marqueur. Leaflet fait aussi remonter l'evenement
  // au fond de carte selon le type de couche : sans ce garde, selectionner un point
  // declencherait la deselection dans la foulee.
  const markerClickAtRef = useRef(0);
  // Le cadrage « tout le parc » est un cadrage d'ARRIVEE : il ne doit jouer qu'une
  // fois. Ensuite, seuls un focus explicite ou une selection recadrent la carte.
  const hasFramedOnceRef = useRef(false);
  // Le handler de clic vit dans une ref : l'abonnement Leaflet est pose une seule fois
  // a l'initialisation, il ne doit pas se re-abonner a chaque rendu du parent.
  const backgroundClickRef = useRef(onBackgroundClick);
  backgroundClickRef.current = onBackgroundClick;
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const [mapReady, setMapReady] = useState(false);

  const mappableBuildings = useMemo(
    () =>
      buildings.flatMap((building) => {
        const latitude = toCoordinate(building.latitude);
        const longitude = toCoordinate(building.longitude);
        return latitude == null || longitude == null ? [] : [{ ...building, latitude, longitude } as MappableBuilding];
      }),
    [buildings],
  );

  const selectedBuilding = useMemo(
    () => mappableBuildings.find((b) => b.id === activeBuildingId) ?? mappableBuildings[0] ?? null,
    [activeBuildingId, mappableBuildings],
  );

  /**
   * Position d'AFFICHAGE de chaque bâtiment, écartée quand plusieurs partagent le même
   * point.
   *
   * Mesuré en prod le 2026-08-20 : **67 bâtiments sur 184** ont exactement les mêmes
   * coordonnées qu'un autre, en 26 groupes — 143 positions distinctes seulement. Ils
   * ont hérité du point de leur parcelle, pas de leur emprise propre. Empilés au même
   * pixel, un seul était visible et cliquable : les autres semblaient avoir disparu de
   * la carte, alors qu'ils étaient dessous.
   *
   * L'écart est **purement visuel** — la position enregistrée ne change pas — et il est
   * retranché au déplacement d'un bâtiment.
   */
  const buildingDisplay = useMemo(() => {
    const groups = new Map<string, MappableBuilding[]>();
    for (const building of mappableBuildings) {
      const key = `${building.latitude.toFixed(6)}|${building.longitude.toFixed(6)}`;
      groups.set(key, [...(groups.get(key) ?? []), building]);
    }
    const display = new Map<number, { lat: number; lon: number; offsetLat: number; offsetLon: number }>();
    for (const group of groups.values()) {
      if (group.length === 1) {
        display.set(group[0].id, {
          lat: group[0].latitude, lon: group[0].longitude, offsetLat: 0, offsetLon: 0,
        });
        continue;
      }
      // ~22 m : au-delà du rayon des pattes d'araignée (15 m), pour que les grappes de
      // deux bâtiments voisins ne se mélangent pas.
      const radiusDeg = 22 / 111_320;
      group.forEach((building, index) => {
        const angle = (2 * Math.PI * index) / group.length;
        const lat = building.latitude + radiusDeg * Math.cos(angle);
        const lon =
          building.longitude +
          (radiusDeg * Math.sin(angle)) /
            Math.max(0.2, Math.cos((building.latitude * Math.PI) / 180));
        display.set(building.id, {
          lat, lon, offsetLat: lat - building.latitude, offsetLon: lon - building.longitude,
        });
      });
    }
    return display;
  }, [mappableBuildings]);

  const { legacyMarkers, spiderLegs } = useMemo(() => {
    const perBuilding = new Map<number, LegacyMapPoint[]>();
    const loose: LegacyMapPoint[] = [];

    for (const point of legacyPoints ?? []) {
      const building =
        point.isLinked && point.buildingId != null
          ? mappableBuildings.find((candidate) => candidate.id === point.buildingId)
          : undefined;
      // Le point doit être **effectivement posé sur** le bâtiment (< 5 m). Déplacé
      // ailleurs, il décrit autre chose : le fondre dans le bâtiment mentirait sur sa
      // position, et masquer le bâtiment ferait disparaître une réalité distincte.
      const onBuilding =
        building != null &&
        distanceMeters(point.latitude, point.longitude, building.latitude, building.longitude) <= 5;
      if (building && onBuilding) {
        perBuilding.set(building.id, [...(perBuilding.get(building.id) ?? []), point]);
      } else {
        loose.push(point);
      }
    }

    const markers: LegacyRenderMarker[] = [];
    const legs: LegacySpiderLeg[] = [];

    for (const [buildingId, points] of perBuilding) {
      const building = mappableBuildings.find((candidate) => candidate.id === buildingId)!;
      // Centre de l'araignee = la position d'AFFICHAGE du batiment. Sans cela, les
      // araignees de plusieurs batiments empiles au meme point se superposeraient
      // exactement, et les traits partiraient tous du meme endroit.
      const center = buildingDisplay.get(buildingId) ?? {
        lat: building.latitude, lon: building.longitude,
      };
      // Disposition en ARAIGNEE : le batiment ne bouge pas, chaque bien est pose autour
      // et relie par un trait. La fusion en un point unique se lisait bien tant que tout
      // etait juste, mais elle enlevait toute prise des qu'un rattachement etait faux :
      // impossible de designer, ni de detacher, un bien parmi ceux qui se superposaient.
      points.forEach((point, index) => {
        const angle = (2 * Math.PI * index) / points.length - Math.PI / 2;
        const latitude = center.lat + SPIDER_RADIUS_DEG * Math.cos(angle);
        const longitude =
          center.lon +
          (SPIDER_RADIUS_DEG * Math.sin(angle)) /
            Math.max(0.2, Math.cos((building.latitude * Math.PI) / 180));
        markers.push({
          points: [point],
          latitude,
          longitude,
          buildingId,
          buildingLabel: building.nom_batiment ?? point.buildingLabel ?? null,
          isBuildingAnchor: false,
          // L'ecart est purement visuel : au deplacement, on le retranche pour ne pas
          // enregistrer une position decalee de 15 m.
          offsetLat: latitude - point.latitude,
          offsetLon: longitude - point.longitude,
        });
        legs.push({
          fromLat: center.lat,
          fromLon: center.lon,
          toLat: latitude,
          toLon: longitude,
          isLocalTarget: point.isLocalTarget === true,
          isProposal: point.isProposal === true,
        });
      });
    }

    for (const point of loose) {
      markers.push({
        points: [point],
        latitude: point.latitude,
        longitude: point.longitude,
        buildingId: point.buildingId ?? null,
        buildingLabel: point.buildingLabel ?? null,
        isBuildingAnchor: false,
        offsetLat: 0,
        offsetLon: 0,
      });
    }

    return {
      // Les biens detaches gardent la position heritee du batiment : sans cet
      // ecartement ils resteraient pile sous lui, et le detachement semblerait sans
      // effet. C'est le symptome remonte le 2026-08-20.
      legacyMarkers: spreadCoLocatedMarkers(markers),
      spiderLegs: legs,
    };
  }, [buildingDisplay, legacyPoints, mappableBuildings]);

  // Priorité : focusLatLon (bâtiment sélectionné ou centroïde du site sélectionné),
  // sinon le bâtiment actif, sinon le premier bâtiment mappable.
  const streetViewUrl = useMemo(() => {
    const lat = focusLatLon?.lat ?? selectedBuilding?.latitude ?? null;
    const lon = focusLatLon?.lon ?? selectedBuilding?.longitude ?? null;
    if (lat == null || lon == null) return null;
    return `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${lat},${lon}`;
  }, [focusLatLon, selectedBuilding]);

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
      runtime
        .tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          // OpenStreetMap ne publie pas de tuiles au-dela du niveau 19 : au-dela,
          // Leaflet reclamait des tuiles inexistantes et la carte devenait blanche.
          // `maxNativeZoom` lui fait agrandir la derniere tuile disponible.
          maxZoom: 19,
          maxNativeZoom: 19,
          attribution: "&copy; OpenStreetMap contributors",
        })
        .addTo(map);
      // Clic sur le fond de carte = sortir de la selection. On ignore les clics qui
      // suivent immediatement un clic sur un marqueur : selon le type de couche,
      // Leaflet fait remonter l'evenement jusqu'a la carte, et la selection qu'on
      // vient de faire serait annulee dans la foulee.
      map.on?.("click", (payload) => {
        // Deux gardes, parce qu'un seul ne suffit pas :
        // - la cible reelle du clic. Leaflet laisse remonter l'evenement depuis les
        //   marqueurs et les polygones ; seul un clic sur les tuiles est un clic
        //   « dans le vide » ;
        // - un delai apres un clic ou un glisser sur marqueur, car un deposer emet un
        //   `click` dont la cible est deja demontee au moment ou on l'examine.
        if (Date.now() - markerClickAtRef.current < 400) return;
        const original = (payload as { originalEvent?: Event } | undefined)?.originalEvent;
        const target = original?.target as HTMLElement | undefined;
        if (
          target?.closest?.(
            ".leaflet-marker-pane, .leaflet-overlay-pane, .leaflet-popup-pane, .leaflet-control-container",
          )
        ) {
          return;
        }
        backgroundClickRef.current?.();
      });
      mapRef.current = map;
      setMapReady(true);
      window.setTimeout(() => map.invalidateSize?.(), 0);
      window.setTimeout(() => map.invalidateSize?.(), 80);

      // Leaflet fige les dimensions du conteneur a l'initialisation. Or la carte vit
      // dans une grille dont la colonne de gauche s'elargit quand les donnees arrivent,
      // bien apres ces deux rafraichissements : la carte gardait alors une largeur
      // perimee et n'affichait aucune tuile au premier chargement. Elle ne reapparaissait
      // qu'apres un aller-retour de navigation, qui la remontait a la bonne taille.
      // L'observateur rattrape tout changement de taille, d'ou qu'il vienne.
      if (typeof ResizeObserver !== "undefined" && containerRef.current) {
        const observer = new ResizeObserver(() => map.invalidateSize?.());
        observer.observe(containerRef.current);
        resizeObserverRef.current = observer;
      }
    }
    void mountMap();
    return () => {
      disposed = true;
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = null;
      setMapReady(false);
      mapRef.current?.remove();
      mapRef.current = null;
      buildingsLayerRef.current = null;
      portfolioIgnLayerRef.current = null;
      attachLayerRef.current = null;
      centerMarkerRef.current = null;
      legacyLayerRef.current = null;
    };
  }, []);

  // ------------------------------------------------------------------
  // Couche « biens historiques ASTECH » — couleur dédiée, marqueur déplaçable
  // ------------------------------------------------------------------
  useEffect(() => {
    const runtime = runtimeRef.current;
    const map = mapRef.current;
    if (!runtime || !map || !mapReady) return;

    legacyLayerRef.current?.remove?.();
    legacyLayerRef.current = null;

    if (legacyMarkers.length === 0) return;

    const layerGroup = runtime.featureGroup();

    // Les pattes d'araignee AVANT les pastilles, pour passer dessous. Un trait pointille
    // pour une cible « local », plein pour le batiment entier : le niveau du
    // rattachement se lit sur la carte, sans ouvrir quoi que ce soit.
    for (const leg of spiderLegs) {
      const line = runtime.polyline?.(
        [
          [leg.fromLat, leg.fromLon],
          [leg.toLat, leg.toLon],
        ],
        {
          color: "#22c55e",
          weight: 2,
          opacity: 0.75,
          dashArray: leg.isLocalTarget ? "3 4" : undefined,
          interactive: false,
        },
      );
      if (line) layerGroup.addLayer(line);
    }

    for (const entry of legacyMarkers) {
      // Un marqueur = UN bien, toujours. C'est ce que la disposition en araignee
      // retablit : chaque bien reste designable et detachable individuellement, la ou
      // le point fusionne les rendait inatteignables des qu'un rattachement etait faux.
      const point = entry.points[0];
      const isActive = point.id === activeLegacyId;
      const isDraggable = isActive;
      const marker = runtime.marker([entry.latitude, entry.longitude], {
        draggable: isDraggable,
        autoPan: isDraggable,
        icon: runtime.divIcon({
          className: "legacy-marker",
          html: `<span class="legacy-marker-dot${isActive ? " is-active" : ""}${
            point.isLinked ? " is-linked" : ""
          }${point.isProposal ? " is-proposal" : ""}${point.isLocalTarget ? " is-local" : ""}${
            point.isProvisional ? " is-provisional" : ""
          }"></span>`,
          iconSize: [18, 18],
          iconAnchor: [9, 9],
        }),
      });
      marker.bindPopup?.(
        `<strong>${point.label}</strong><br/><em>Bien ASTECH — ${
          point.isLinked
            ? `${point.isProposal ? "proposé par le moteur, à confirmer" : "rattaché"} — ${
                point.isLocalTarget ? "un local" : "le bâtiment entier"
              }`
            : "non rattaché"
        }${point.isProvisional ? ", position à confirmer" : ""}</em>${
          point.isLinked && entry.buildingLabel
            ? `<br/>Po2 : <strong>${entry.buildingLabel}</strong>`
            : ""
        }`,
      );
      marker.on?.("click", () => {
        markerClickAtRef.current = Date.now();
        onSelectLegacyId?.(point.id);
      });
      if (isDraggable && (onMoveLegacyPoint || onDropLegacyOnBuilding)) {
        // Leaflet fait suivre un glisser-deposer d'un `click` qui remonte jusqu'au fond
        // de carte. Sans ce marquage, lacher le point declenchait la deselection — et
        // la carte se recadrait aussitot sur tout le parc.
        marker.on?.("dragstart", () => {
          markerClickAtRef.current = Date.now();
        });
        marker.on?.("dragend", () => {
          markerClickAtRef.current = Date.now();
          const dropped = marker.getLatLng();
          // Le marqueur est dessine DECALE (patte d'araignee) : ce decalage est
          // purement visuel. On le retranche avant d'enregistrer, sinon deplacer un
          // point de quelques metres y ajouterait les 15 m de la patte.
          const position = {
            lat: dropped.lat - entry.offsetLat,
            lng: dropped.lng - entry.offsetLon,
          };
          // Depot sur un batiment Po2 : on cherche le plus proche dans le rayon
          // d'accrochage. C'est le geste « ce bien ASTECH, c'est ce batiment-la ».
          let nearest: { id: number; distance: number } | null = null;
          for (const building of mappableBuildings) {
            const distance = distanceMeters(
              position.lat, position.lng, building.latitude, building.longitude,
            );
            if (distance <= legacyDropRadiusM && (nearest === null || distance < nearest.distance)) {
              nearest = { id: building.id, distance };
            }
          }
          if (nearest !== null && onDropLegacyOnBuilding) {
            onDropLegacyOnBuilding(point.id, nearest.id);
            return;
          }
          onMoveLegacyPoint?.(point.id, position.lat, position.lng);
        });
      }
      layerGroup.addLayer(marker);
    }

    layerGroup.addTo(map);
    legacyLayerRef.current = layerGroup;
    return () => {
      layerGroup.clearLayers();
    };
  }, [
    activeLegacyId, legacyDropRadiusM, legacyMarkers, mappableBuildings, mapReady,
    onDropLegacyOnBuilding, onMoveLegacyPoint, onSelectLegacyId, spiderLegs,
  ]);

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
      // Meme garde que le cadrage plus bas : ne recentrer qu'au premier passage.
      if (framingSignatureRef.current !== "empty") {
        framingSignatureRef.current = "empty";
        map.setView([43.4028, 3.6928], 13);
      }
      return;
    }

    const layerGroup = runtime.featureGroup();
    const dimInAttach = attachMode === "ign"; // assombrissement des markers hors-mode

    for (const building of mappableBuildings) {
      const isActive = building.id === (activeBuildingId ?? selectedBuilding?.id ?? null);
      const isHighlighted = highlightedSet.has(building.id);
      const hasIgn = building.statut_geocodage === "IGN_VALIDE";

      // Le batiment est TOUJOURS dessine : c'est le centre de l'araignee, le point
      // fixe auquel les biens ASTECH se rattachent par un trait. L'avoir masque au
      // profit d'une pastille fusionnee rendait les rattachements faux impossibles a
      // corriger — on ne pouvait plus designer un bien en particulier.

      let color = dimInAttach ? "#94a3b8" : "#38bdf8";
      let fillColor = dimInAttach ? "#94a3b8" : "#0ea5e9";

      // La couleur dit l'ETAT du batiment (bleu = attache IGN, vert = cible du bien
      // selectionne, gris = estompe en mode attachement). La selection, elle, ne
      // repeint plus rien : elle ajoute un anneau (plus bas). Repeindre le point
      // selectionne en orange faisait croire que son etat avait change au clic.
      if (!dimInAttach) {
        if (isHighlighted && hasIgn) { color = "#15803d"; fillColor = "#16a34a"; }
        else if (isHighlighted) { color = "#ea580c"; fillColor = "#f97316"; }
        else if (hasIgn) { color = "#1d4ed8"; fillColor = "#2563eb"; }
      }

      // Position d'affichage : ecartee quand plusieurs batiments partagent le meme
      // point (67 sur 184 en prod). Empiles, un seul etait visible et cliquable.
      const shown = buildingDisplay.get(building.id) ?? {
        lat: building.latitude, lon: building.longitude, offsetLat: 0, offsetLon: 0,
      };

      // Anneau de selection : pose SOUS le marqueur, il ne touche pas a sa couleur.
      // C'est ce qui permet au point selectionne de rester bleu (ou vert) tout en
      // etant clairement designe.
      if (isActive) {
        layerGroup.addLayer(
          runtime.circleMarker([shown.lat, shown.lon], {
            radius: 14,
            color: "#f8fafc",
            fillColor: "#38bdf8",
            fillOpacity: 0.18,
            weight: 2,
            interactive: false,
          }),
        );
      }

      const isDraggable = building.id === draggableBuildingId && attachMode === "none";
      // `circleMarker` n'est pas deplaçable : le batiment que l'on veut bouger passe
      // donc en marqueur classique, avec la meme apparence.
      const marker = isDraggable
        ? runtime.marker([shown.lat, shown.lon], {
            draggable: true,
            autoPan: true,
            icon: runtime.divIcon({
              className: "legacy-marker",
              html: '<span class="po2-marker-dot is-draggable"></span>',
              iconSize: [20, 20],
              iconAnchor: [10, 10],
            }),
          })
        : runtime.circleMarker([shown.lat, shown.lon], {
            radius: isActive ? 9 : dimInAttach ? 5 : isHighlighted ? 8 : 7,
            color,
            fillColor,
            fillOpacity: dimInAttach && !isActive ? 0.45 : 0.92,
            weight: isActive ? 3 : 2,
          });
      if (isDraggable && onMoveBuilding) {
        const draggableMarker = marker as RuntimeMarker;
        draggableMarker.on?.("dragend", () => {
          const position = draggableMarker.getLatLng();
          // L'ecart d'affichage (batiments empiles) est retranche : deplacer un
          // batiment de deux metres ne doit pas y ajouter les 22 m de l'ecartement.
          onMoveBuilding(
            building.id,
            position.lat - shown.offsetLat,
            position.lng - shown.offsetLon,
          );
        });
      }
      marker.bindPopup?.(
        `<strong>${building.nom_batiment || `Bâtiment #${building.id}`}</strong><br/>${buildAddressLine(building)}${hasIgn ? "<br/><em>IGN attaché</em>" : ""}`,
      );
      marker.on?.("click", () => {
        markerClickAtRef.current = Date.now();
        if (attachMode === "none") onSelectBuildingId(building.id);
      });
      layerGroup.addLayer(marker);
    }

    layerGroup.addTo(map);
    buildingsLayerRef.current = layerGroup;

    // Le recadrage ne doit se produire QUE si l'intention de cadrage a change
    // (selection, focus, mode). Sans ce garde, le moindre rafraichissement de la
    // liste des batiments — par exemple apres avoir deplace un point ASTECH —
    // rejouait fitBounds et rezoomait la carte au niveau ville : l'utilisateur
    // devait rezoomer manuellement apres chaque deplacement.
    const framingSignature = [
      attachMode,
      focusLatLon ? `${focusLatLon.lat},${focusLatLon.lon}` : "",
      [...highlightedSet].sort((a, b) => a - b).join("-"),
      mappableBuildings.length > 0 ? "has-buildings" : "empty",
    ].join("|");
    const shouldFrame = framingSignatureRef.current !== framingSignature;
    framingSignatureRef.current = framingSignature;

    if (attachMode !== "ign" && shouldFrame) {
      // Cadrage normal (non-attach)
      if (focusLatLon) {
        map.setView([focusLatLon.lat, focusLatLon.lon], FOCUS_ZOOM);
      } else if (highlightedSet.size > 0) {
        const highlighted = mappableBuildings.filter((b) => highlightedSet.has(b.id));
        // Ne pas bouger la carte quand la cible est DEJA a l'ecran. Valider un
        // rattachement sur un batiment qu'on vient de cliquer recadrait dessus au
        // zoom 18 : si on travaillait plus pres, cela ressemblait a un dezoom subi.
        // Le recadrage n'a de sens que pour aller chercher un batiment hors champ,
        // typiquement quand la selection vient de la liste de gauche.
        const viewBounds = map.getBounds?.();
        const alreadyVisible =
          highlighted.length > 0 &&
          viewBounds?.contains != null &&
          highlighted.every((b) => viewBounds.contains?.([b.latitude, b.longitude]));

        const hGroup = runtime.featureGroup();
        for (const b of highlighted) {
          hGroup.addLayer(runtime.circleMarker([b.latitude, b.longitude], { radius: 1, opacity: 0 }));
        }
        const hBounds = hGroup.getBounds();
        if (alreadyVisible) {
          // rien a faire : la vue courante convient
        } else if (hBounds.isValid()) map.fitBounds(hBounds.pad(0.3), { maxZoom: FOCUS_ZOOM });
        else {
          const bounds = layerGroup.getBounds();
          if (bounds.isValid()) map.fitBounds(bounds.pad(0.18), { maxZoom: FOCUS_ZOOM });
        }
      } else if (!hasFramedOnceRef.current) {
        // Cadrage sur TOUT le parc : uniquement au premier affichage. Le rejouer
        // ensuite est le bug du « dezoom » — perdre la selection (validation d'un
        // rattachement, lacher d'un point, clic dans le vide) vidait `highlightedSet`
        // et renvoyait la carte au niveau ville, obligeant a rezoomer a chaque geste.
        // Une DESELECTION ne doit pas deplacer la carte : on laisse la vue en place.
        const bounds = layerGroup.getBounds();
        if (bounds.isValid()) map.fitBounds(bounds.pad(0.18), { maxZoom: FOCUS_ZOOM });
        else if (selectedBuilding) map.setView([selectedBuilding.latitude, selectedBuilding.longitude], 17);
      }
      hasFramedOnceRef.current = true;
    }

    map.invalidateSize?.();
    window.setTimeout(() => map.invalidateSize?.(), 50);
    return () => { layerGroup.clearLayers(); };
  }, [
    activeBuildingId, attachMode, buildingDisplay, draggableBuildingId, focusLatLon,
    highlightedSet, mapReady, mappableBuildings, onMoveBuilding, onSelectBuildingId,
    selectedBuilding,
  ]);

  // ------------------------------------------------------------------
  // Couche polygones IGN déjà attachés (mode portfolio, bleu translucide)
  // ------------------------------------------------------------------
  useEffect(() => {
    const runtime = runtimeRef.current;
    const map = mapRef.current;
    if (!runtime || !map || !mapReady) return;

    portfolioIgnLayerRef.current?.remove?.();
    portfolioIgnLayerRef.current = null;

    // N'afficher que hors mode attachement
    if (attachMode === "ign") return;
    const features = portfolioIgnFeatures?.features ?? [];
    if (!features.length) return;

    const geoLayer = runtime.geoJSON(undefined, {
      style: () => ({
        color: "#1d4ed8",
        weight: 2,
        fillColor: "#3b82f6",
        fillOpacity: 0.18,
        interactive: false,
      }),
    });
    geoLayer.addData({ type: "FeatureCollection", features });
    geoLayer.addTo(map);
    portfolioIgnLayerRef.current = geoLayer;
  }, [portfolioIgnFeatures, attachMode, mapReady]);

  // ------------------------------------------------------------------
  // Couche attachement IGN : centre + polygones WFS sélectionnables
  // Les polygones viennent du serveur (lookup/free-address avec feature_collection)
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
    map.setView([attachLat, attachLon], FOCUS_ZOOM);
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

    // Polygones WFS BDTOPO depuis la feature_collection serveur
    const features = attachFeatureCollection?.features ?? [];
    if (!features.length) return;

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
            // Construire un GeoJsonFeature normalisé depuis le feature serveur
            const props = (feature.properties ?? {}) as Record<string, unknown>;
            const normalized: GeoJsonFeature = {
              type: "Feature",
              geometry: (feature.geometry ?? null) as GeoJsonFeature["geometry"],
              properties: {
                ...props,
                // S'assurer que ign_id est présent pour la sélection
                ign_id: props.ign_id ?? fid,
              },
            };
            onSelectAttachFeature?.(normalized);
          }
        });
      },
    });
    geoLayer.addData({ type: "FeatureCollection", features });
    geoLayer.addTo(map);
    attachLayerRef.current = geoLayer;
  }, [attachMode, attachLat, attachLon, attachAddress, attachSelectedIds, attachFeatureCollection, mapReady, onSelectAttachFeature, onDeselectAttachFeatureId]);

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

  const showOverlay = isAttachLoading;
  const overlayText = isAttachLoading ? "Chargement des polygones IGN..." : null;

  return (
    <div className="map-shell">
      <div className="map-toolbar">
        <span>
          {attachMode === "ign" ? (
            <>
              Mode attachement IGN ·{" "}
              {isAttachLoading ? (
                <em>Chargement des polygones...</em>
              ) : (
                <strong>
                  {attachFeatureCollection?.features.length ?? 0} polygone(s) BDTOPO ·{" "}
                  {attachSelectedIds?.length ?? 0} sélectionné(s)
                </strong>
              )}
            </>
          ) : (
            <span>{mappableBuildings.length} bâtiment(s) affiché(s).</span>
          )}
        </span>
        <div className="map-toolbar-actions">
          {streetViewUrl && attachMode === "none" ? (
            <a className="secondary-link" href={streetViewUrl} target="_blank" rel="noreferrer">
              Google Street View
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
        {!isAttachLoading && attachMode === "ign" && (attachFeatureCollection?.features.length ?? 0) === 0 && !isAttachLoading ? (
          <div className="map-loading-overlay map-loading-overlay--error">
            <span>Aucun polygone IGN détecté dans ce secteur.</span>
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
