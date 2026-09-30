import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { PdfPoint } from "../api";
import {
  cliquer,
  debuterAlignement,
  ecartEchellePct,
  garderLaRotation,
  pairesAEnregistrer,
  refaireEtape,
  type Alignement,
} from "./alignement";
import { GuideCalage, etapesDuCalage } from "./GuideCalage";
import { appliquer, similitude, type Similitude } from "./superposition";

// Le vrai passage du voisin au plan actif : un quart de tour, échelle 2 (1/100 sur 1/50), un décalage.
const VRAI: Similitude = { a: 0, b: 2, tx: 400, ty: 50 };
const POSE_PROVISOIRE: Similitude = { a: 2, b: 0, tx: 0, ty: 0 };
const A: PdfPoint = [10, 10];
const B: PdfPoint = [200, 40];
const C: PdfPoint = [60, 250];

// Le thermicien clique un point du calque là où il est affiché, puis où il doit aller sur le plan.
function pointer(al: Alignement, surVoisin: PdfPoint, echelle: number, vrai = VRAI, libre = false) {
  const clic1 = cliquer(al, appliquer(al.sim, surVoisin), echelle, libre);
  return cliquer(clic1, appliquer(vrai, surVoisin), echelle, libre);
}

const proche = (sim: Similitude, attendu: Similitude) => {
  for (const cle of ["a", "b", "tx", "ty"] as const) expect(sim[cle]).toBeCloseTo(attendu[cle], 6);
};

// Le serveur recalcule la similitude à partir des deux paires envoyées : ce doit être la pose affichée.
const commeLeServeur = (al: Alignement) => {
  const paires = pairesAEnregistrer(al)!;
  return similitude([paires[0][0], paires[1][0]], [paires[0][1], paires[1][1]])!;
};

describe("le calage comme la commande Aligner d'AutoCAD (D201, D202)", () => {
  it("le point de base fait seulement glisser le calque", () => {
    const al = pointer(debuterAlignement("inferieur", POSE_PROVISOIRE), A, 2);
    expect(al.etape).toBe("rotation");
    expect(al.sim.a).toBe(2);
    expect(al.sim.b).toBe(0);
    expect(appliquer(al.sim, A)).toEqual(appliquer(VRAI, A));
  });

  it("la rotation autour du point de base retrouve la vraie pose, à l'échelle déclarée", () => {
    const al = pointer(pointer(debuterAlignement("inferieur", POSE_PROVISOIRE), A, 2), B, 2);
    expect(al.etape).toBe("longueur");
    proche(al.sim, VRAI);
    proche(commeLeServeur(al), VRAI);
  });

  it("un clic un peu de travers est aimanté à l'angle droit, sauf avec Alt", () => {
    const presque: Similitude = { a: 2 * Math.cos(Math.PI / 2 + 0.01), b: 2 * Math.sin(Math.PI / 2 + 0.01), tx: 400, ty: 50 };
    const base = pointer(debuterAlignement("inferieur", POSE_PROVISOIRE), A, 2, presque);
    const aimante = pointer(base, B, 2, presque);
    expect(aimante.aimante).toBe(true);
    expect(aimante.sim.a).toBeCloseTo(0, 9);
    const libre = pointer(base, B, 2, presque, true);
    expect(libre.aimante).toBe(false);
    expect(libre.sim.a).toBeCloseTo(presque.a, 6);
  });

  it("une échelle déclarée arrondie se rattrape à l'étape longueur, par un point quelconque", () => {
    // Le vrai rapport est 2 × 100/99,3 : l'une des planches a été arrondie à 1/100.
    const k = 100 / 99.3;
    const vrai: Similitude = { a: 0, b: 2 * k, tx: 400, ty: 50 };
    const tourne = pointer(pointer(debuterAlignement("inferieur", POSE_PROVISOIRE), A, 2, vrai), B, 2, vrai);
    expect(ecartEchellePct(tourne, 2)).toBeCloseTo(0, 6);
    const etire = pointer(tourne, C, 2, vrai);
    proche(etire.sim, vrai);
    expect(ecartEchellePct(etire, 2)).toBeCloseTo((k - 1) * 100, 6);
    proche(commeLeServeur(etire), vrai);
  });

  it("« La rotation est déjà bonne » passe à la longueur sans clic, à l'échelle déclarée", () => {
    const deja: Similitude = { a: 2, b: 0, tx: 30, ty: -20 };
    const base = pointer(debuterAlignement("inferieur", { a: 2.1, b: 0, tx: 0, ty: 0 }), A, 2, deja);
    const garde = garderLaRotation(base, 2);
    expect(garde.etape).toBe("longueur");
    proche(garde.sim, deja);
    proche(commeLeServeur(garde), deja);
  });

  it("refuse un second point collé au point de base", () => {
    const base = pointer(debuterAlignement("inferieur", POSE_PROVISOIRE), A, 2);
    const trop = pointer(base, [A[0] + 2, A[1] + 2], 2);
    expect(trop.etape).toBe("rotation");
    expect(trop.message).toContain("trop près");
  });

  it("« Refaire l'étape » défait la longueur, puis la rotation, puis le point de base", () => {
    const base = pointer(debuterAlignement("inferieur", POSE_PROVISOIRE), A, 2);
    const tourne = pointer(base, B, 2);
    const etire = pointer(tourne, C, 2, { ...VRAI, b: 2.1 });
    const sansLongueur = refaireEtape(etire);
    expect(sansLongueur.etape).toBe("longueur");
    expect(sansLongueur.sim).toEqual(tourne.sim);
    const rotation = refaireEtape(sansLongueur);
    expect(rotation.etape).toBe("rotation");
    expect(rotation.sim).toEqual(base.sim);
    const debut = refaireEtape(rotation);
    expect(debut.etape).toBe("base");
    expect(debut.sim).toEqual(POSE_PROVISOIRE);
  });
});

describe("le guide du calage", () => {
  it("dit ce que fait le prochain clic, étape par étape", () => {
    const debut = debuterAlignement("inferieur", POSE_PROVISOIRE);
    expect(etapesDuCalage(debut, "RDC", "R+1", "bleu").map((etape) => etape.etat)).toEqual(["en_cours", "a_venir", "a_venir"]);
    const attente = cliquer(debut, [5, 5], 2);
    expect(etapesDuCalage(attente, "RDC", "R+1", "bleu")[0].texte).toContain("le calque va glisser");
    const rotation = pointer(debut, A, 2);
    expect(etapesDuCalage(rotation, "RDC", "R+1", "bleu").map((etape) => etape.etat)).toEqual(["faite", "en_cours", "a_venir"]);
  });

  it("propose de garder la rotation, puis d'enregistrer avec l'écart d'échelle affiché", () => {
    const rendu = (al: Alignement) =>
      renderToStaticMarkup(
        <GuideCalage al={al} voisin="RDC" plan="R+1" couleur="bleu" echelle={2} onEnregistrer={() => {}} onGarderRotation={() => {}} onRefaire={() => {}} />,
      );
    const rotation = pointer(debuterAlignement("inferieur", POSE_PROVISOIRE), A, 2);
    expect(rendu(rotation)).toContain("La rotation est déjà bonne");
    const tourne = pointer(rotation, B, 2);
    const html = rendu(tourne);
    expect(html).toContain("Caler le RDC sur le R+1");
    expect(html).toContain("Rotation 90,00°");
    expect(html).toContain("celle déclarée sur les deux planches");
    expect(html).toContain("Enregistrer le calage");
    const etire = pointer(tourne, C, 2, { ...VRAI, b: 2 * (100 / 99.3) });
    expect(rendu(etire)).toContain("sans doute arrondie");
  });
});
