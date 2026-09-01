/**
 * Les défauts de la carte, figés en tests.
 *
 * Chaque cas ci-dessous correspond à un défaut **réellement remonté en prod** sur l'écran
 * de rapprochement ASTECH. Ils n'ont pas été inventés pour couvrir du code : ils sont la
 * trace de ce qui a été découvert à l'usage, faute d'avoir pu vérifier cette géométrie
 * autrement qu'en la regardant. C'est la raison d'être de `mapLayout.ts`.
 */
import { describe, expect, it } from "vitest";

import {
  computeLegacyLayout,
  computeLocalMarkers,
  decideDrop,
  distanceMeters,
  spreadCoLocatedMarkers,
  type DisplayPoint,
  type LegacyMapPoint,
  type LegacyRenderMarker,
  type LocalMapPoint,
  type MappableBuilding,
} from "./mapLayout";

// Sète, pour rester dans les latitudes où la correction de méridien joue vraiment.
const LAT = 43.4053;
const LON = 3.6936;

/**
 * Un bâtiment cartographiable réduit à ce que la disposition lit vraiment. Le type
 * complet vient de l'API et porte une trentaine de champs sans effet ici.
 */
function batiment(id: number, latitude: number, longitude: number, nom = `BAT ${id}`): MappableBuilding {
  return { id, nom_batiment: nom, latitude, longitude } as unknown as MappableBuilding;
}

function bien(id: number, latitude: number, longitude: number, reste: Partial<LegacyMapPoint> = {}): LegacyMapPoint {
  return { id, label: `BIEN ${id}`, latitude, longitude, ...reste };
}

function local(id: number, buildingId: number, latitude: number, longitude: number): LocalMapPoint {
  return { id, buildingId, label: `LOCAL ${id}`, buildingLabel: null, latitude, longitude };
}

function affichage(...batiments: MappableBuilding[]): Map<number, DisplayPoint> {
  return new Map(batiments.map((b) => [b.id, { lat: b.latitude, lon: b.longitude }]));
}

describe("computeLegacyLayout", () => {
  it("fond en UN SEUL point le bien unique posé sur son bâtiment", () => {
    // Le défaut : le point apparié se dédoublait dès qu'on y touchait. Un bien seul sur
    // sa cible n'a rien à démêler — un point, et pas de trait.
    const bat = batiment(42, LAT, LON);
    const { legacyMarkers, spiderLegs } = computeLegacyLayout({
      legacyPoints: [bien(1, LAT, LON, { isLinked: true, buildingId: 42 })],
      mappableBuildings: [bat],
      buildingDisplay: affichage(bat),
    });

    expect(legacyMarkers).toHaveLength(1);
    expect(legacyMarkers[0].isMerged).toBe(true);
    expect(legacyMarkers[0].points.map((p) => p.id)).toEqual([1]);
    expect(spiderLegs).toHaveLength(0);
  });

  it("garde l'araignée dès qu'il y a plusieurs biens sur le même bâtiment", () => {
    const bat = batiment(42, LAT, LON);
    const { legacyMarkers, spiderLegs } = computeLegacyLayout({
      legacyPoints: [
        bien(1, LAT, LON, { isLinked: true, buildingId: 42 }),
        bien(2, LAT, LON, { isLinked: true, buildingId: 42 }),
      ],
      mappableBuildings: [bat],
      buildingDisplay: affichage(bat),
    });

    expect(legacyMarkers).toHaveLength(2);
    expect(legacyMarkers.every((m) => m.isMerged !== true)).toBe(true);
    expect(spiderLegs).toHaveLength(2);
    // Chaque branche part bien du bâtiment, à une quinzaine de mètres.
    for (const leg of spiderLegs) {
      const d = distanceMeters(leg.fromLat, leg.fromLon, leg.toLat, leg.toLon);
      expect(d).toBeGreaterThan(10);
      expect(d).toBeLessThan(20);
    }
  });

  it("ne rabat aucune branche sur un axe aux effectifs courants (2 à 6 biens)", () => {
    // Le défaut d'origine : la liaison paraissait toujours horizontale. Elle l'était —
    // l'araignée démarrait plein ouest, et à deux biens les deux branches formaient une
    // ligne droite qu'on lisait comme un unique trait horizontal. Le départ en diagonale
    // l'interdit sur toute la plage réellement rencontrée.
    //
    // Au-delà (8, 12, 16…), l'étoile repose forcément deux branches sur les axes : c'est
    // la géométrie d'un partage régulier, et sans conséquence — dans une étoile à huit
    // branches, personne ne lit une branche horizontale comme « la » liaison.
    const bat = batiment(42, LAT, LON);
    for (const nombre of [2, 3, 4, 5, 6]) {
      const { spiderLegs } = computeLegacyLayout({
        legacyPoints: Array.from({ length: nombre }, (_, i) =>
          bien(i + 1, LAT, LON, { isLinked: true, buildingId: 42 }),
        ),
        mappableBuildings: [bat],
        buildingDisplay: affichage(bat),
      });
      expect(spiderLegs).toHaveLength(nombre);
      for (const leg of spiderLegs) {
        expect(Math.abs(leg.toLat - leg.fromLat)).toBeGreaterThan(1e-9);
        expect(Math.abs(leg.toLon - leg.fromLon)).toBeGreaterThan(1e-9);
      }
    }
  });

  it("donne à chaque branche une direction distincte, quel que soit l'effectif", () => {
    // La règle qui, elle, ne souffre pas d'exception : deux biens ne peuvent pas partir
    // dans la même direction, sinon leurs pastilles se recouvrent et l'un est indésignable.
    const bat = batiment(42, LAT, LON);
    for (const nombre of [2, 3, 8, 12]) {
      const { spiderLegs } = computeLegacyLayout({
        legacyPoints: Array.from({ length: nombre }, (_, i) =>
          bien(i + 1, LAT, LON, { isLinked: true, buildingId: 42 }),
        ),
        mappableBuildings: [bat],
        buildingDisplay: affichage(bat),
      });
      const directions = spiderLegs.map((leg) =>
        Math.atan2(leg.toLat - leg.fromLat, leg.toLon - leg.fromLon).toFixed(4),
      );
      expect(new Set(directions).size).toBe(nombre);
    }
  });

  it("laisse un bien rattaché mais déplacé à SA position, et va le chercher en oblique", () => {
    // ~100 m au nord-est : le trait doit suivre cet angle-là, pas se rabattre sur un axe.
    const bat = batiment(42, LAT, LON);
    const ailleurs = bien(1, LAT + 0.0009, LON + 0.0009, { isLinked: true, buildingId: 42 });
    const { legacyMarkers, spiderLegs } = computeLegacyLayout({
      legacyPoints: [ailleurs],
      mappableBuildings: [bat],
      buildingDisplay: affichage(bat),
    });

    expect(legacyMarkers).toHaveLength(1);
    expect(legacyMarkers[0].latitude).toBeCloseTo(ailleurs.latitude, 9);
    expect(legacyMarkers[0].longitude).toBeCloseTo(ailleurs.longitude, 9);
    // Aucun décalage : ce que l'on saisit est ce que l'on enregistre.
    expect(legacyMarkers[0].offsetLat).toBe(0);
    expect(legacyMarkers[0].offsetLon).toBe(0);

    expect(spiderLegs).toHaveLength(1);
    expect(spiderLegs[0].fromLat).toBeCloseTo(LAT, 9);
    expect(spiderLegs[0].toLat).toBeCloseTo(ailleurs.latitude, 9);
    expect(Math.abs(spiderLegs[0].toLon - spiderLegs[0].fromLon)).toBeGreaterThan(1e-9);
  });

  it("suit la position D'AFFICHAGE du bâtiment quand celui-ci a été écarté d'une pile", () => {
    // Sinon le trait part d'un endroit où plus aucune pastille n'est dessinée.
    const bat = batiment(42, LAT, LON);
    const decale: DisplayPoint = { lat: LAT + 0.0002, lon: LON + 0.0002 };
    const { legacyMarkers } = computeLegacyLayout({
      legacyPoints: [bien(1, LAT, LON, { isLinked: true, buildingId: 42 })],
      mappableBuildings: [bat],
      buildingDisplay: new Map([[42, decale]]),
    });

    expect(legacyMarkers[0].latitude).toBeCloseTo(decale.lat, 9);
    // Le décalage consenti est retranché au moment du glisser : il ne doit pas entrer
    // dans les coordonnées enregistrées.
    expect(legacyMarkers[0].offsetLat).toBeCloseTo(decale.lat - LAT, 9);
  });
});

describe("spreadCoLocatedMarkers", () => {
  const marqueur = (id: number, latitude: number, longitude: number): LegacyRenderMarker => ({
    points: [bien(id, latitude, longitude)],
    latitude,
    longitude,
    buildingId: null,
    buildingLabel: null,
    isBuildingAnchor: false,
    offsetLat: 0,
    offsetLon: 0,
  });

  it("ne touche pas à un marqueur seul", () => {
    const [seul] = spreadCoLocatedMarkers([marqueur(1, LAT, LON)]);
    expect(seul.latitude).toBe(LAT);
    expect(seul.offsetLat).toBe(0);
  });

  it("sépare des marqueurs empilés en reportant l'écart dans l'offset", () => {
    // C'est cette égalité qui empêche l'écartement — purement visuel — de s'inscrire
    // dans la base quand on saisit puis repose le point.
    const spread = spreadCoLocatedMarkers([marqueur(1, LAT, LON), marqueur(2, LAT, LON)]);
    expect(spread).toHaveLength(2);
    const ecarte = spread.find((m) => m.offsetLat !== 0)!;
    expect(ecarte.latitude - ecarte.points[0].latitude).toBeCloseTo(ecarte.offsetLat, 12);
    expect(ecarte.longitude - ecarte.points[0].longitude).toBeCloseTo(ecarte.offsetLon, 12);
  });
});

describe("computeLocalMarkers", () => {
  it("écarte le local SEUL posé sur son bâtiment", () => {
    // Le défaut : l'écartement ne comparait que les locaux entre eux. Un local unique
    // hérité de la position de son parent restait dessous — étiquette invisible.
    const bat = batiment(42, LAT, LON);
    const [dessine] = computeLocalMarkers({
      localPoints: [local(7, 42, LAT, LON)],
      buildingDisplay: affichage(bat),
    });

    const ecart = distanceMeters(dessine.latitude, dessine.longitude, LAT, LON);
    expect(ecart).toBeGreaterThan(5);
    expect(ecart).toBeLessThan(15);
  });

  it("ne déplace pas un local qui porte une position propre", () => {
    // On ne déforme pas une donnée relevée pour la commodité de l'affichage.
    const bat = batiment(42, LAT, LON);
    const propre = local(7, 42, LAT + 0.0005, LON + 0.0005);
    const [dessine] = computeLocalMarkers({
      localPoints: [propre],
      buildingDisplay: affichage(bat),
    });

    expect(dessine.latitude).toBe(propre.latitude);
    expect(dessine.longitude).toBe(propre.longitude);
  });

  it("sépare des locaux empilés au même endroit", () => {
    const bat = batiment(42, LAT, LON);
    const dessines = computeLocalMarkers({
      localPoints: [local(7, 42, LAT, LON), local(8, 42, LAT, LON), local(9, 42, LAT, LON)],
      buildingDisplay: affichage(bat),
    });

    expect(dessines).toHaveLength(3);
    for (let i = 0; i < dessines.length; i += 1) {
      for (let j = i + 1; j < dessines.length; j += 1) {
        const d = distanceMeters(
          dessines[i].latitude,
          dessines[i].longitude,
          dessines[j].latitude,
          dessines[j].longitude,
        );
        expect(d).toBeGreaterThan(5);
      }
    }
  });
});

describe("decideDrop", () => {
  const bat = batiment(42, LAT, LON);
  const autre = batiment(43, LAT + 0.01, LON + 0.01);
  const commun = {
    mappableBuildings: [bat, autre],
    buildingDisplay: affichage(bat, autre),
    radiusM: 30,
  };

  it("traite comme un simple DÉPLACEMENT le lâcher sur la cible déjà tenue", () => {
    // Le défaut : un point apparié est confondu avec son bâtiment, donc tout petit
    // déplacement retombait dans le rayon d'accrochage et rouvrait une proposition de
    // rattachement à la cible qu'il avait déjà — le point restait suspendu en attendant.
    const decision = decideDrop({
      ...commun,
      position: { lat: LAT + 0.00002, lon: LON },
      point: bien(1, LAT, LON, { isLinked: true, buildingId: 42 }),
      localMarkers: [],
    });
    expect(decision).toEqual({ kind: "move" });
  });

  it("propose un rattachement quand on vise un LOCAL du même bâtiment", () => {
    // Viser un local reste une vraie décision : on change de cible, on précise le niveau.
    const localMarkers = computeLocalMarkers({
      localPoints: [local(7, 42, LAT + 0.0004, LON)],
      buildingDisplay: affichage(bat),
    });
    const decision = decideDrop({
      ...commun,
      position: { lat: LAT + 0.0004, lon: LON },
      point: bien(1, LAT, LON, { isLinked: true, buildingId: 42 }),
      localMarkers,
    });
    expect(decision).toEqual({ kind: "link", buildingId: 42, localId: 7 });
  });

  it("propose de repasser au bâtiment entier un bien qui visait un local", () => {
    const decision = decideDrop({
      ...commun,
      position: { lat: LAT, lon: LON },
      point: bien(1, LAT, LON, { isLinked: true, buildingId: 42, isLocalTarget: true }),
      localMarkers: [],
    });
    expect(decision).toEqual({ kind: "link", buildingId: 42, localId: null });
  });

  it("propose un rattachement quand on vise un AUTRE bâtiment", () => {
    const decision = decideDrop({
      ...commun,
      position: { lat: autre.latitude, lon: autre.longitude },
      point: bien(1, LAT, LON, { isLinked: true, buildingId: 42 }),
      localMarkers: [],
    });
    expect(decision).toEqual({ kind: "link", buildingId: 43, localId: null });
  });

  it("ne propose rien quand on lâche dans le vide", () => {
    const decision = decideDrop({
      ...commun,
      position: { lat: LAT + 0.005, lon: LON + 0.005 },
      point: bien(1, LAT, LON),
      localMarkers: [],
    });
    expect(decision).toEqual({ kind: "move" });
  });

  it("retient la cible la PLUS PROCHE quand plusieurs sont dans le rayon", () => {
    const localMarkers = computeLocalMarkers({
      localPoints: [local(7, 42, LAT + 0.0002, LON)],
      buildingDisplay: affichage(bat),
    });
    const decision = decideDrop({
      ...commun,
      position: { lat: LAT + 0.00019, lon: LON },
      point: bien(1, LAT + 0.002, LON),
      localMarkers,
    });
    expect(decision).toEqual({ kind: "link", buildingId: 42, localId: 7 });
  });
});
