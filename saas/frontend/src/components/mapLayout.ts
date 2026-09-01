/**
 * Disposition des points sur la carte du rapprochement ASTECH — calcul PUR.
 *
 * Extrait de `BuildingPortfolioMap` pour être testable sans Leaflet, sans DOM et sans
 * React. Ce n'est pas une élégance : c'est ici que se sont logés la moitié des défauts
 * remontés en prod — traits systématiquement horizontaux, étiquettes de locaux cachées
 * sous celles de leur bâtiment, point apparié qui se dédouble au déplacement. Tous
 * relevaient d'une géométrie fausse, et aucun n'était couvert.
 *
 * Le composant garde le dessin ; ce module décide **où** chaque chose va.
 */
import type { Building } from "../lib/api";

/** Un bien ASTECH tel que l'écran veut le montrer. */
export type LegacyMapPoint = {
  id: number;
  label: string;
  latitude: number;
  longitude: number;
  /** Position empruntée au bâtiment, jamais relevée pour ce bien. */
  isProvisional?: boolean;
  isLinked?: boolean;
  /** Rattaché par le moteur, pas encore confirmé par un humain. */
  isProposal?: boolean;
  /** Le bien désigne un local, et non le bâtiment entier. */
  isLocalTarget?: boolean;
  buildingId?: number | null;
  buildingLabel?: string | null;
};

/** Un **local** Po2 posé sur la carte. */
export type LocalMapPoint = {
  id: number;
  buildingId: number;
  label: string;
  buildingLabel: string | null;
  latitude: number;
  longitude: number;
  /** Position venue du bâtiment parent et non du local lui-même. */
  isInherited?: boolean;
  address?: string | null;
};

/** Un marqueur ASTECH réellement dessiné — **un seul bien** par marqueur. */
export type LegacyRenderMarker = {
  points: LegacyMapPoint[];
  latitude: number;
  longitude: number;
  buildingId: number | null;
  buildingLabel: string | null;
  /** `true` quand ce marqueur tient lieu de bâtiment : il ne doit pas être décalé. */
  isBuildingAnchor: boolean;
  /** Bien et bâtiment fondus en un seul point : relation simple, rien à démêler. */
  isMerged?: boolean;
  /** Décalage visuel appliqué, à retrancher au déplacement. */
  offsetLat: number;
  offsetLon: number;
};

/** Un trait reliant un bien ASTECH au bâtiment qui le porte. */
export type LegacySpiderLeg = {
  fromLat: number;
  fromLon: number;
  toLat: number;
  toLon: number;
  isLocalTarget: boolean;
  isProposal: boolean;
};

export type MappableBuilding = Building & { latitude: number; longitude: number };

/** Position d'AFFICHAGE d'un bâtiment : elle diffère de la vraie quand il est empilé. */
export type DisplayPoint = { lat: number; lon: number };

/** Rayon de l'araignée : 15 m, plus large que l'écartement des locaux (9 m). */
export const SPIDER_RADIUS_DEG = 15 / 111_320;

/** Au-delà, un bien rattaché n'est plus « posé sur » son bâtiment. */
export const ON_BUILDING_M = 5;

/** Distance approximative entre deux points, en mètres. */
export function distanceMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000;
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

/** Correction du méridien : un degré de longitude rétrécit avec la latitude. */
function lonScale(latitude: number): number {
  return Math.max(0.2, Math.cos((latitude * Math.PI) / 180));
}

export function spreadCoLocatedMarkers(markers: LegacyRenderMarker[]): LegacyRenderMarker[] {
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
    const anchorIndex = Math.max(0, group.findIndex((marker) => marker.isBuildingAnchor));
    const others = group.filter((_, index) => index !== anchorIndex);
    spread.push(group[anchorIndex]);
    // ~14 m de rayon : assez pour separer les pastilles sans mentir sur la position.
    const radiusDeg = 14 / 111_320;
    others.forEach((marker, index) => {
      const angle = (2 * Math.PI * index) / others.length;
      const shiftLat = radiusDeg * Math.cos(angle);
      const shiftLon = (radiusDeg * Math.sin(angle)) / lonScale(marker.latitude);
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

/**
 * Où poser chaque bien ASTECH, et quels traits tracer.
 *
 * Trois cas, et c'est leur distinction qui compte :
 *
 * - **un seul bien posé sur son bâtiment** → les deux ne font qu'un point, sans trait ;
 * - **plusieurs biens sur un bâtiment** → araignée, pour pouvoir en désigner un ;
 * - **un bien rattaché mais posé ailleurs** → il garde sa position, et un trait va le
 *   chercher, à n'importe quelle distance et sous n'importe quel angle.
 */
export function computeLegacyLayout(input: {
  legacyPoints: LegacyMapPoint[] | undefined;
  mappableBuildings: MappableBuilding[];
  buildingDisplay: Map<number, DisplayPoint>;
}): { legacyMarkers: LegacyRenderMarker[]; spiderLegs: LegacySpiderLeg[] } {
  const { legacyPoints, mappableBuildings, buildingDisplay } = input;
  const perBuilding = new Map<number, LegacyMapPoint[]>();
  const loose: LegacyMapPoint[] = [];
  const linkedAway: { point: LegacyMapPoint; building: MappableBuilding }[] = [];

  for (const point of legacyPoints ?? []) {
    const building =
      point.isLinked && point.buildingId != null
        ? mappableBuildings.find((candidate) => candidate.id === point.buildingId)
        : undefined;
    const onBuilding =
      building != null &&
      distanceMeters(point.latitude, point.longitude, building.latitude, building.longitude) <=
        ON_BUILDING_M;
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
    const center = buildingDisplay.get(buildingId) ?? {
      lat: building.latitude,
      lon: building.longitude,
    };
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
      // `cos` pilote la LATITUDE (le nord), `sin` la LONGITUDE (l'est) : l'angle 0 vise
      // deja le nord. Un `- PI/2` faisait pivoter l'araignee vers l'OUEST — d'ou des
      // traits horizontaux avec 1 bien comme avec 2. Le depart en diagonale evite en
      // plus de s'aligner sur un axe quel que soit leur nombre.
      const angle = (2 * Math.PI * index) / points.length + Math.PI / 4;
      const latitude = center.lat + SPIDER_RADIUS_DEG * Math.cos(angle);
      const longitude =
        center.lon + (SPIDER_RADIUS_DEG * Math.sin(angle)) / lonScale(building.latitude);
      markers.push({
        points: [point],
        latitude,
        longitude,
        buildingId,
        buildingLabel: building.nom_batiment ?? point.buildingLabel ?? null,
        isBuildingAnchor: false,
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

  for (const { point, building } of linkedAway) {
    const center = buildingDisplay.get(building.id) ?? {
      lat: building.latitude,
      lon: building.longitude,
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

  return { legacyMarkers: spreadCoLocatedMarkers(markers), spiderLegs: legs };
}

/**
 * Position réellement dessinée de chaque local, écartement compris.
 *
 * Deux empilements à défaire : plusieurs locaux sur un même point, **et un local seul
 * posé exactement sur son bâtiment** — ce second cas était oublié, l'écartement ne
 * comparant que les locaux entre eux. Un local portant une position propre et distincte
 * n'est pas déplacé : on ne déforme pas une donnée pour la commodité de l'affichage.
 */
export function computeLocalMarkers(input: {
  localPoints: LocalMapPoint[] | undefined;
  buildingDisplay: Map<number, DisplayPoint>;
}): { point: LocalMapPoint; latitude: number; longitude: number }[] {
  const { localPoints, buildingDisplay } = input;
  // ~9 m : plus serré que l'araignée ASTECH (15 m) et que l'écartement des bâtiments
  // (22 m), pour que les trois familles restent distinctes à l'œil.
  const radiusDeg = 9 / 111_320;
  const groups = new Map<string, LocalMapPoint[]>();
  for (const point of localPoints ?? []) {
    const key = `${point.latitude.toFixed(6)}|${point.longitude.toFixed(6)}`;
    groups.set(key, [...(groups.get(key) ?? []), point]);
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
      // Départ décalé d'un quart de tour par rapport à l'araignée ASTECH : les deux
      // familles ne se superposent pas autour d'un même bâtiment.
      const angle = (2 * Math.PI * index) / group.length - Math.PI / 4;
      drawn.push({
        point,
        latitude: point.latitude + radiusDeg * Math.cos(angle),
        longitude: point.longitude + (radiusDeg * Math.sin(angle)) / lonScale(point.latitude),
      });
    });
  }
  return drawn;
}

export type DropDecision =
  | { kind: "move" }
  | { kind: "link"; buildingId: number; localId: number | null };

/**
 * Ce que vaut un point lâché : un déplacement, ou une proposition de rattachement.
 *
 * Le piège tenait à la distance : un point apparié étant confondu avec son bâtiment,
 * tout déplacement de quelques mètres le lâche forcément dans le rayon d'accrochage.
 * Le geste était alors pris pour une proposition de rattachement **à la cible qu'il a
 * déjà** — et le point restait retenu à l'endroit lâché pendant qu'on répondait.
 *
 * Viser un LOCAL du même bâtiment reste une vraie décision (on précise le niveau), tout
 * comme repasser d'un local au bâtiment entier.
 */
export function decideDrop(input: {
  position: { lat: number; lon: number };
  point: LegacyMapPoint;
  mappableBuildings: MappableBuilding[];
  buildingDisplay: Map<number, DisplayPoint>;
  localMarkers: { point: LocalMapPoint; latitude: number; longitude: number }[];
  radiusM: number;
}): DropDecision {
  const { position, point, mappableBuildings, buildingDisplay, localMarkers, radiusM } = input;
  let nearest: { id: number; distance: number; localId: number | null } | null = null;
  for (const building of mappableBuildings) {
    const shown = buildingDisplay.get(building.id);
    const distance = distanceMeters(
      position.lat,
      position.lon,
      shown?.lat ?? building.latitude,
      shown?.lon ?? building.longitude,
    );
    if (distance <= radiusM && (nearest === null || distance < nearest.distance)) {
      nearest = { id: building.id, distance, localId: null };
    }
  }
  for (const local of localMarkers) {
    const distance = distanceMeters(position.lat, position.lon, local.latitude, local.longitude);
    if (distance <= radiusM && (nearest === null || distance < nearest.distance)) {
      nearest = { id: local.point.buildingId, distance, localId: local.point.id };
    }
  }
  if (nearest === null) return { kind: "move" };
  const sameTargetAsNow =
    nearest.id === point.buildingId && nearest.localId == null && point.isLocalTarget !== true;
  if (sameTargetAsNow) return { kind: "move" };
  return { kind: "link", buildingId: nearest.id, localId: nearest.localId };
}
