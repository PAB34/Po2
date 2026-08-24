import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  /** Étiquette permanente posée à côté du marqueur (dénomination affichée au zoom). */
  bindTooltip?: (content: string, options?: Record<string, unknown>) => RuntimeLayer;
  on?: (event: string, handler: () => void) => void;
};

type RuntimeBounds = {
  isValid: () => boolean;
  pad: (ratio: number) => RuntimeBounds;
  contains?: (point: [number, number]) => boolean;
};

type RuntimeMap = {
  getZoom?: () => number;
  setView: (coords: [number, number], zoom: number) => RuntimeMap;
  fitBounds: (bounds: RuntimeBounds, options?: Record<string, unknown>) => void;
  remove: () => void;
  invalidateSize?: () => void;
  getCenter?: () => { lat: number; lng: number };
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
  /** Bien et bâtiment fondus en un seul point : relation simple, rien à démêler. */
  isMerged?: boolean;
  /** Décalage visuel appliqué (patte d'araignée), à retrancher au déplacement. */
  offsetLat: number;
  offsetLon: number;
};

/**
 * Un **local** Po2 posé sur la carte.
 *
 * La carte ne dessinait que les bâtiments : 505 locaux sur 626 ont pourtant des
 * coordonnées, et restaient invisibles. Or un `CODE_BIEN` ASTECH désigne souvent un
 * local (logement de fonction, salle, WC publics) — ne pas les montrer obligeait à
 * passer par le menu déroulant après coup, sans jamais les voir sur le terrain.
 */
export type LocalMapPoint = {
  id: number;
  buildingId: number;
  label: string;
  buildingLabel: string | null;
  latitude: number;
  longitude: number;
  /**
   * `true` quand la position vient du **bâtiment parent** et non du local lui-même.
   *
   * Un local est dans son bâtiment : hériter de sa position n'invente rien, c'est la
   * meilleure vérité disponible — et c'est déjà ce qu'on fait pour les biens ASTECH.
   * Mais un point hérité n'est pas un point relevé : il est dessiné en creux, pour ne
   * pas laisser croire à une position mesurée.
   */
  isInherited?: boolean;
  /** Adresse à rappeler dans la bulle, héritée le cas échéant. */
  address?: string | null;
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
/**
 * Zoom à partir duquel les dénominations s'affichent d'elles-mêmes sur la carte.
 *
 * Relevé de 17 à 19 le 2026-08-21 : à 17 les noms arrivaient trop tôt, alors qu'on
 * cherche encore son quartier. Il faut donc deux crans de molette de plus. Le fond OSM
 * n'a pas de tuiles au-delà de 19 (`maxNativeZoom`), mais la carte va jusqu'à 21 en
 * agrandissant la dernière : sans cela les étiquettes n'existeraient qu'au tout dernier
 * niveau, sans marge pour s'approcher davantage.
 */
const LABEL_MIN_ZOOM = 19;
/** Plafond d'étiquettes dessinées d'un coup, quoi qu'il arrive. */
const MAX_LABELS = 120;

/** Les dénominations viennent des données : elles sont injectées en HTML, donc échappées. */
function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
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
   * Appele quand le point ASTECH est lache SUR une entite Po2 (a moins de
   * `legacyDropRadiusM` metres).
   *
   * La carte ne fait que SIGNALER le geste, elle ne rattache pas : c'est l'appelant qui
   * decide, et depuis Q25 il en fait une proposition a valider. La position lachee est
   * transmise avec, pour que refuser le rattachement puisse valoir « je voulais
   * seulement deplacer ce point ».
   */
  onDropLegacyOnBuilding?: (
    legacyId: number,
    buildingId: number,
    localId: number | null,
    lat: number,
    lon: number,
  ) => void;
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
  /**
   * Centre courant de la carte, émis à chaque déplacement.
   *
   * Sert à poser le point d'un bien **là où l'utilisateur regarde**. Un bien ASTECH
   * sans coordonnées apparaissait au centre de Sète : quand on avait zoomé sur un
   * quartier, il fallait aller le chercher hors écran avant de pouvoir le placer.
   */
  onViewCenterChange?: (center: { lat: number; lon: number }) => void;
  /** Locaux Po2 à dessiner : pastilles plus petites, subordonnées à leur bâtiment. */
  localPoints?: LocalMapPoint[];
  /** Clic sur un local — sert à en faire la cible du bien ASTECH sélectionné. */
  onSelectLocalId?: (localId: number, buildingId: number) => void;
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
      const shiftLat = radiusDeg * Math.cos(angle);
      const shiftLon =
        (radiusDeg * Math.sin(angle)) / Math.max(0.2, Math.cos((marker.latitude * Math.PI) / 180));
      spread.push({
        ...marker,
        latitude: marker.latitude + shiftLat,
        longitude: marker.longitude + shiftLon,
        // L'ecartement est PUREMENT visuel : il doit rejoindre le decalage que
        // `dragend` retranche avant d'enregistrer. Sans cela, saisir puis reposer un
        // point ecarte inscrivait les 14 m de l'ecartement dans ses coordonnees.
        offsetLat: marker.offsetLat + shiftLat,
        offsetLon: marker.offsetLon + shiftLon,
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
/**
 * Surface approchée d'une géométrie, en degrés carrés (boîte englobante).
 *
 * Sert uniquement à ORDONNER le dessin : dans Leaflet, la dernière couche ajoutée est
 * au-dessus et capte les clics. Les grands polygones — un terrain de sport, un parking
 * de complexe sportif — recouvrent des dizaines de bâtiments : dessinés en dernier, ils
 * rendaient tout ce qui est dessous inatteignable, y compris pour le désélectionner.
 */
function geometryBoxArea(geometry: unknown): number {
  const geom = (geometry ?? {}) as { type?: string; coordinates?: unknown };
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const walk = (node: unknown): void => {
    if (!Array.isArray(node)) return;
    if (typeof node[0] === "number" && typeof node[1] === "number") {
      const [x, y] = node as [number, number];
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
      return;
    }
    for (const child of node) walk(child);
  };
  walk(geom.coordinates);
  if (!Number.isFinite(minX) || !Number.isFinite(minY)) return 0;
  return Math.max(0, maxX - minX) * Math.max(0, maxY - minY);
}

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
  onViewCenterChange,
  localPoints,
  onSelectLocalId,
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
  const localsLayerRef = useRef<RuntimeFeatureGroup | null>(null);
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
  const viewCenterRef = useRef(onViewCenterChange);
  viewCenterRef.current = onViewCenterChange;
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const [mapReady, setMapReady] = useState(false);
  // Le conteneur de la carte vit dans un ETAT, pas seulement dans une ref.
  //
  // Ce composant rend un etat vide — sans conteneur — tant qu'aucun batiment n'est
  // geolocalise (voir le rendu). Au premier chargement de la page, les batiments sont
  // encore en cours de requete : l'effet d'initialisation tournait donc avec
  // `containerRef.current` a null, sortait aussitot, et n'etait JAMAIS rejoue (deps
  // `[]`). La carte restait vide pour de bon, et seul un aller-retour de navigation la
  // reparait — en remontant le composant alors que les donnees sont deja en cache.
  // Une ref ne declenche pas de rendu : c'est un etat qu'il faut, pour que l'effet
  // rejoue le jour ou le conteneur apparait enfin.
  /**
   * Les dénominations s'affichent d'elles-mêmes à partir de ce niveau de zoom.
   *
   * En dessous, la ville entière tient à l'écran et 700 étiquettes se chevaucheraient en
   * une bouillie illisible. Au-delà, on est à l'échelle du quartier : les noms sont ce
   * qui permet de reconnaître une entité sans la cliquer une par une.
   *
   * On ne garde que le franchissement du seuil, pas le zoom lui-même : les couches se
   * reconstruisent alors une seule fois, au passage, et non à chaque cran de molette.
   */
  const [labelsVisible, setLabelsVisible] = useState(false);
  // Change a chaque deplacement de la carte : les etiquettes sont recalculees pour le
  // cadre VISIBLE seulement (cf. la couche dediee plus bas).
  const [viewportTick, setViewportTick] = useState(0);
  const labelsLayerRef = useRef<RuntimeFeatureGroup | null>(null);
  const [containerEl, setContainerEl] = useState<HTMLDivElement | null>(null);
  const attachContainer = useCallback((node: HTMLDivElement | null) => {
    containerRef.current = node;
    setContainerEl(node);
  }, []);

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

    // Les biens rattachés mais posés AILLEURS que sur leur bâtiment : ils gardent leur
    // position propre, et c'est le trait qui va les chercher, à l'angle qu'il faut.
    const linkedAway: { point: LegacyMapPoint; building: MappableBuilding }[] = [];

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
        if (building) linkedAway.push({ point, building });
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
      // UN SEUL bien sur ce bâtiment : les deux ne font plus qu'un point, plus gros et
      // marqué d'un ✓. Le trait entre deux pastilles voisines n'apprend rien quand la
      // relation est simple — il ne sert qu'à démêler plusieurs biens. L'araignée reste
      // donc dès qu'ils sont plusieurs : c'est elle qui permet de désigner et de
      // détacher un bien parmi d'autres (§19).
      if (points.length === 1) {
        const only = points[0];
        markers.push({
          points: [only],
          latitude: center.lat,
          longitude: center.lon,
          buildingId,
          buildingLabel: building.nom_batiment ?? only.buildingLabel ?? null,
          isBuildingAnchor: false,
          isMerged: true,
          offsetLat: center.lat - only.latitude,
          offsetLon: center.lon - only.longitude,
        });
        continue;
      }
      points.forEach((point, index) => {
        // `cos` pilote la LATITUDE (le nord), `sin` la LONGITUDE (l'est) : l'angle 0
        // vise donc deja le nord. L'ancien `- PI/2` faisait pivoter toute l'araignee
        // d'un quart de tour vers l'OUEST — d'ou des traits systematiquement
        // horizontaux avec 1 bien (ouest) comme avec 2 (ouest + est), c'est-a-dire
        // 68 batiments rattaches sur 69 en prod. Le depart en diagonale (PI/4,
        // nord-est) evite en plus de s'aligner sur un axe quel que soit le nombre.
        const angle = (2 * Math.PI * index) / points.length + Math.PI / 4;
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

    // Un bien rattaché puis déplacé gardait son lien... mais plus aucun trait : il
    // sortait de l'araignée et rien ne le reliait plus à son bâtiment. Le rattachement
    // devenait invisible au moment précis où on avait le plus besoin de le voir. Le
    // trait part donc du bâtiment vers la position REELLE du point, à n'importe quelle
    // distance et sous n'importe quel angle (Q27).
    for (const { point, building } of linkedAway) {
      const center = buildingDisplay.get(building.id) ?? {
        lat: building.latitude, lon: building.longitude,
      };
      legs.push({
        fromLat: center.lat,
        fromLon: center.lon,
        toLat: point.latitude,
        toLon: point.longitude,
        isLocalTarget: point.isLocalTarget === true,
        isProposal: point.isProposal === true,
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
          maxZoom: 21,
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
      // Le centre courant permet de poser un point la ou l'utilisateur regarde,
      // plutot qu'au centre de Sete — souvent hors ecran quand on a zoome.
      const emitCenter = () => {
        const center = (map as unknown as { getCenter?: () => { lat: number; lng: number } })
          .getCenter?.();
        if (center) viewCenterRef.current?.({ lat: center.lat, lon: center.lng });
      };
      map.on?.("moveend", emitCenter);
      emitCenter();
      const syncLabels = () => {
        const level = map.getZoom?.();
        if (typeof level === "number") setLabelsVisible(level >= LABEL_MIN_ZOOM);
      };
      map.on?.("zoomend", syncLabels);
      map.on?.("moveend", () => setViewportTick((tick) => tick + 1));
      syncLabels();
      mapRef.current = map;
      setMapReady(true);
      window.setTimeout(() => map.invalidateSize?.(), 0);
      window.setTimeout(() => map.invalidateSize?.(), 80);

      // Leaflet fige les dimensions du conteneur a l'initialisation, et la carte vit dans
      // une grille dont les colonnes bougent quand les donnees arrivent : l'observateur
      // rattrape tout changement de taille, d'ou qu'il vienne.
      //
      // Il avait ete ajoute en croyant corriger la carte absente au premier chargement.
      // Ce n'etait pas la cause — la carte n'etait alors pas creee du tout, faute de
      // conteneur au moment de l'effet (cf. `containerEl` plus haut). Il reste utile
      // pour le redimensionnement, mais ne traite pas ce cas-la.
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
      localsLayerRef.current = null;
      labelsLayerRef.current = null;
    };
    // `containerEl` et non `[]` : le conteneur peut n'apparaitre qu'apres l'arrivee des
    // donnees, et c'est alors qu'il faut monter la carte.
  }, [containerEl]);

  /**
   * Position REELLEMENT dessinée de chaque local, écartement compris.
   *
   * Deux empilements à défaire, pas un seul :
   *
   * - plusieurs locaux sur un même point — ils héritent tous de la position de leur
   *   bâtiment à l'import ;
   * - **un local seul, posé exactement sur son bâtiment**. C'était le cas oublié :
   *   l'écartement ne comparait que les locaux entre eux, si bien qu'un local unique
   *   restait pile sous la pastille de son bâtiment, invisible. Mesuré le 2026-08-24 :
   *   39 des 57 locaux affichables sont dans ce cas.
   *
   * Un local qui porte une position propre et distincte n'est PAS déplacé : on ne
   * déforme pas une donnée juste pour la commodité de l'affichage.
   *
   * Le calcul est partagé avec la couche des dénominations : une étiquette posée
   * ailleurs que sa pastille désignerait le mauvais point.
   */
  const localMarkers = useMemo(() => {
    const points = localPoints ?? [];
    // ~9 m : plus serré que les pattes d'araignée ASTECH (15 m) et que l'écartement des
    // bâtiments (22 m), pour que les trois familles restent distinctes à l'œil.
    const radiusDeg = 9 / 111_320;
    const groups = new Map<string, LocalMapPoint[]>();
    for (const point of points) {
      groups.set(
        `${point.latitude.toFixed(6)}|${point.longitude.toFixed(6)}`,
        [...(groups.get(`${point.latitude.toFixed(6)}|${point.longitude.toFixed(6)}`) ?? []), point],
      );
    }
    const drawn: { point: LocalMapPoint; latitude: number; longitude: number }[] = [];
    for (const group of groups.values()) {
      group.forEach((point, index) => {
        const anchorPoint = buildingDisplay.get(point.buildingId);
        const onItsBuilding =
          anchorPoint != null &&
          distanceMeters(point.latitude, point.longitude, anchorPoint.lat, anchorPoint.lon) <= 2;
        if (group.length === 1 && !onItsBuilding) {
          drawn.push({ point, latitude: point.latitude, longitude: point.longitude });
          return;
        }
        // Départ décalé d'un quart de tour par rapport à l'araignée ASTECH (qui part au
        // nord-est) : les deux familles ne se superposent pas autour d'un même bâtiment.
        const angle = (2 * Math.PI * index) / group.length - Math.PI / 4;
        drawn.push({
          point,
          latitude: point.latitude + radiusDeg * Math.cos(angle),
          longitude:
            point.longitude +
            (radiusDeg * Math.sin(angle)) /
              Math.max(0.2, Math.cos((point.latitude * Math.PI) / 180)),
        });
      });
    }
    return drawn;
  }, [buildingDisplay, localPoints]);

  // ------------------------------------------------------------------
  // Couche « locaux Po2 » — pastilles subordonnées aux bâtiments
  // ------------------------------------------------------------------
  useEffect(() => {
    const runtime = runtimeRef.current;
    const map = mapRef.current;
    if (!runtime || !map || !mapReady) return;

    localsLayerRef.current?.remove?.();
    localsLayerRef.current = null;

    if (localMarkers.length === 0 || attachMode === "ign") return;

    const layerGroup = runtime.featureGroup();
    {
      localMarkers.forEach(({ point, latitude, longitude }) => {
        // Un LOSANGE, et non un disque : la forme distingue un local d'un batiment sans
        // dependre de la couleur — le bleu et l'indigo se ressemblent trop sur un fond
        // de carte. C'est le meme signe ◇ que dans l'arbre du patrimoine, le selecteur
        // de cible et les etiquettes. Et il est plus gros que l'ancien disque de 4 px,
        // qui etait a peine visible, tout en restant sous la taille du batiment : la
        // hierarchie se lit dans la taille.
        const marker = runtime.marker([latitude, longitude], {
          icon: runtime.divIcon({
            className: "local-marker",
            html: '<span class="local-marker-diamond"></span>',
            iconSize: [14, 14],
            iconAnchor: [7, 7],
          }),
        }) as RuntimeLayer;
        marker.bindPopup?.(
          `<strong>${point.label}</strong><br/><em>Local Po2${
            point.isInherited ? ", position héritée du bâtiment" : ""
          }</em>` +
            (point.address ? `<br/>${point.address}` : "") +
            (point.buildingLabel ? `<br/>dans : ${point.buildingLabel}` : "") +
            (onSelectLocalId ? "<br/><em>Clic : en faire la cible du bien sélectionné</em>" : ""),
        );
        marker.on?.("click", () => {
          markerClickAtRef.current = Date.now();
          onSelectLocalId?.(point.id, point.buildingId);
        });
        layerGroup.addLayer(marker);
      });
    }

    layerGroup.addTo(map);
    localsLayerRef.current = layerGroup;
    return () => {
      layerGroup.clearLayers();
    };
  }, [attachMode, localMarkers, mapReady, onSelectLocalId]);

  // ------------------------------------------------------------------
  // Couche « dénominations » — une couche À PART, et seulement ce qui est à l'écran
  // ------------------------------------------------------------------
  //
  // Première version : un tooltip permanent accroché à chaque marqueur. Leaflet les
  // crée TOUS, où qu'ils soient — 775 éléments positionnés en absolu, repositionnés à
  // chaque déplacement de la carte. L'écran ramait, et les trois couches de marqueurs se
  // reconstruisaient en entier au passage du seuil de zoom.
  //
  // Ici les étiquettes vivent dans leur propre couche, ne concernent que le cadre
  // visible, et ne touchent plus jamais aux marqueurs. Au zoom où elles s'affichent, le
  // cadre en contient quelques dizaines — pas 775.
  useEffect(() => {
    const runtime = runtimeRef.current;
    const map = mapRef.current;
    if (!runtime || !map || !mapReady) return;

    labelsLayerRef.current?.remove?.();
    labelsLayerRef.current = null;
    if (!labelsVisible) return;

    const bounds = map.getBounds?.();
    const visible = (lat: number, lon: number) =>
      bounds?.contains == null ? true : bounds.contains([lat, lon]);

    const group = runtime.featureGroup();
    let posees = 0;
    const poser = (
      lat: number,
      lon: number,
      text: string | null,
      variant: string,
      glyph = "",
    ) => {
      // Plafond de sûreté : un parc dense, ou des points empilés, ne doivent pas
      // ramener le problème qu'on vient de corriger.
      if (!text || posees >= MAX_LABELS || !visible(lat, lon)) return;
      posees += 1;
      group.addLayer(
        runtime.marker([lat, lon], {
          interactive: false,
          keyboard: false,
          icon: runtime.divIcon({
            className: "map-label-icon",
            html: `<span class="map-label map-label--${variant}">${
              glyph ? `<span class="map-label-glyph">${glyph}</span>` : ""
            }${escapeHtml(text)}</span>`,
            iconSize: [0, 0],
            // Ancre négative en x : l'étiquette se pose À DROITE du point, sans le couvrir.
            iconAnchor: [-9, 7],
          }),
        }) as RuntimeLayer,
      );
    };

    for (const entry of legacyMarkers) {
      poser(entry.latitude, entry.longitude, entry.points[0]?.label ?? null, "astech");
    }
    // Un seul caractere devant le nom pour distinguer les deux niveaux Po2 : la couleur
    // seule ne suffisait pas, le bleu du batiment et l'indigo du local se ressemblent
    // trop sur un fond de carte. Meme signe que dans l'arbre du patrimoine et dans le
    // selecteur de cible, pour ne pas avoir deux langages a apprendre.
    for (const building of mappableBuildings) {
      const shown = buildingDisplay.get(building.id);
      poser(
        shown?.lat ?? building.latitude,
        shown?.lon ?? building.longitude,
        building.nom_batiment || `Bâtiment #${building.id}`,
        "po2",
        "▪",
      );
    }
    if (attachMode !== "ign") {
      // La position DESSINEE, pas la position brute : 39 des 57 locaux affichables
      // partagent le point de leur batiment, leur etiquette se posait donc exactement
      // sous celle du batiment et restait invisible.
      for (const { point, latitude, longitude } of localMarkers) {
        poser(latitude, longitude, point.label, "local", "◇");
      }
    }

    group.addTo(map);
    labelsLayerRef.current = group;
    return () => {
      group.clearLayers();
    };
  }, [
    attachMode, buildingDisplay, labelsVisible, legacyMarkers, localMarkers, mapReady,
    mappableBuildings, viewportTick,
  ]);

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
          }${entry.isMerged ? " is-merged" : ""}"></span>`,
          iconSize: entry.isMerged ? [26, 26] : [18, 18],
          iconAnchor: entry.isMerged ? [13, 13] : [9, 9],
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
          // Depot sur une entite Po2 : on cherche la plus proche dans le rayon
          // d'accrochage, batiment OU LOCAL. Le geste ne connaissait que les batiments,
          // alors qu'un CODE_BIEN ASTECH designe tres souvent un local — il fallait
          // rattacher au batiment puis corriger dans le panneau.
          let nearest: { id: number; distance: number; localId: number | null } | null = null;
          for (const building of mappableBuildings) {
            const shown = buildingDisplay.get(building.id);
            const distance = distanceMeters(
              position.lat, position.lng,
              shown?.lat ?? building.latitude, shown?.lon ?? building.longitude,
            );
            if (distance <= legacyDropRadiusM && (nearest === null || distance < nearest.distance)) {
              nearest = { id: building.id, distance, localId: null };
            }
          }
          for (const local of localPoints ?? []) {
            const distance = distanceMeters(
              position.lat, position.lng, local.latitude, local.longitude,
            );
            if (distance <= legacyDropRadiusM && (nearest === null || distance < nearest.distance)) {
              nearest = { id: local.buildingId, distance, localId: local.id };
            }
          }
          if (nearest !== null && onDropLegacyOnBuilding) {
            onDropLegacyOnBuilding(point.id, nearest.id, nearest.localId, position.lat, position.lng);
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
    activeLegacyId, buildingDisplay, legacyDropRadiusM, legacyMarkers, localPoints,
    mappableBuildings, mapReady, onDropLegacyOnBuilding, onMoveLegacyPoint,
    onSelectLegacyId, spiderLegs,
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
    // Du plus GRAND au plus petit : le dernier ajouté est au-dessus dans Leaflet, donc
    // les petits objets restent cliquables par-dessus les grands qui les recouvrent.
    // Sans cet ordre, un terrain de sport ou un parking captait tous les clics de la
    // zone — impossible de sélectionner un bâtiment dessous, ni de le désélectionner.
    const ordered = [...features].sort(
      (a, b) => geometryBoxArea(b.geometry) - geometryBoxArea(a.geometry),
    );
    geoLayer.addData({ type: "FeatureCollection", features: ordered });
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
        <div ref={attachContainer} className="map-canvas" />
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
