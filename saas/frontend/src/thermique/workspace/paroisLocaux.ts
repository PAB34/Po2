import type { PdfPoint, StudyContent, StudyCouche, StudyOperation, StudyParoiLocal, StudyRoom } from "../api";

// Option C (D255 à D262) : un mur = la composition affectée à une paroi d'un local, portion droite de son
// contour. Les parois viennent des fiches des locaux ; la composition validée est enregistrée à part, par le
// serveur, et l'écran l'applique aussitôt pour qu'elle se voie sans attendre le recalcul.

export type ParoiRef = { local: string; rang: number };
export type EtatParoi = "validee" | "proposee" | "vide" | "vitree";
export type GesteComposition = Extract<StudyOperation, { type: "paroi_composer" }>;

export const LIBELLES_ADJACENCE: Record<string, string> = {
  exterieur: "l'extérieur",
  non_chauffe: "un local non chauffé",
  gaine_technique: "une gaine technique",
  vide: "un vide",
  inconnu: "rien d'identifié",
};

export function paroisDuLocal(room: StudyRoom): StudyParoiLocal[] {
  return room.fiche?.parois ?? [];
}

/** Les parois qui demandent une composition : celles qui déperdent (extérieur, local non chauffé, vide). */
export function paroisDeperditives(content: StudyContent): { room: StudyRoom; paroi: StudyParoiLocal }[] {
  return content.locaux.flatMap((room) => paroisDuLocal(room).filter((paroi) => paroi.deperditif).map((paroi) => ({ room, paroi })));
}

export function etatParoi(paroi: StudyParoiLocal): EtatParoi {
  if (paroi.composition) return "validee";
  if (paroi.vitree) return "vitree";
  return paroi.proposition && paroi.proposition.couches.length > 0 ? "proposee" : "vide";
}

/** Compteur de l'étape Parois : parois déperditives opaques sans composition validée (les vitrées vont aux menuiseries). */
export function avancementParois(content: StudyContent): { total: number; restants: number } {
  const liste = paroisDeperditives(content).filter(({ paroi }) => paroi.composition || !paroi.vitree);
  return { total: liste.length, restants: liste.filter(({ paroi }) => !paroi.composition).length };
}

export function trouverParoi(content: StudyContent, ref: ParoiRef | null): { room: StudyRoom; paroi: StudyParoiLocal } | null {
  if (!ref) return null;
  const room = content.locaux.find((local) => local.id === ref.local);
  const paroi = room ? paroisDuLocal(room).find((item) => item.rang === ref.rang) : undefined;
  return room && paroi ? { room, paroi } : null;
}

function distanceAuSegment(point: PdfPoint, a: PdfPoint, b: PdfPoint): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const longueur2 = dx * dx + dy * dy;
  const t = longueur2 === 0 ? 0 : Math.max(0, Math.min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / longueur2));
  return Math.hypot(point[0] - (a[0] + t * dx), point[1] - (a[1] + t * dy));
}

/** La paroi déperditive la plus proche du clic, à moins de `tolerance` (points PDF). */
export function paroiVisee(content: StudyContent, point: PdfPoint, tolerance: number): ParoiRef | null {
  let meilleure: { distance: number; ref: ParoiRef } | null = null;
  for (const { room, paroi } of paroisDeperditives(content)) {
    const trace = paroi.trace_pdf ?? [];
    if (trace.length < 2) continue;
    const distance = distanceAuSegment(point, trace[0], trace[trace.length - 1]);
    if (distance <= tolerance && (!meilleure || distance < meilleure.distance)) {
      meilleure = { distance, ref: { local: room.id, rang: paroi.rang } };
    }
  }
  return meilleure?.ref ?? null;
}

/** Les autres parois à composer qui ont la même proposition (même composant relevé) : « appliquer aussi à ». */
export function paroisSemblables(content: StudyContent, room: StudyRoom, paroi: StudyParoiLocal): { room: StudyRoom; paroi: StudyParoiLocal }[] {
  const composant = paroi.composition?.composant ?? paroi.proposition?.composant;
  if (!composant) return [];
  return paroisDeperditives(content).filter(
    (autre) =>
      !(autre.room.id === room.id && autre.paroi.rang === paroi.rang) &&
      !autre.paroi.composition &&
      autre.paroi.proposition?.composant === composant,
  );
}

export function gesteComposition(room: StudyRoom, paroi: StudyParoiLocal, couches: StudyCouche[], composant: string | null): GesteComposition {
  return {
    type: "paroi_composer",
    local: room.id,
    trace: paroi.trace,
    composant,
    couches: couches.map(({ nature, epaisseur_cm }) => ({ nature, epaisseur_cm })),
  };
}

const memeTrace = (a: [number, number][], b: [number, number][]) =>
  a.length === b.length && a.every((point, rang) => Math.abs(point[0] - b[rang][0]) < 1e-6 && Math.abs(point[1] - b[rang][1]) < 1e-6);

/** La composition posée dans l'écran, comme le serveur la rattachera au recalcul (D261). */
export function appliquerComposition(content: StudyContent, geste: GesteComposition): StudyContent {
  const epaisseur = Math.round(geste.couches.reduce((total, couche) => total + couche.epaisseur_cm, 0) * 10) / 10;
  return {
    ...content,
    locaux: content.locaux.map((room) =>
      room.id !== geste.local || !room.fiche?.parois
        ? room
        : {
            ...room,
            fiche: {
              ...room.fiche,
              parois: room.fiche.parois.map((paroi) =>
                memeTrace(paroi.trace, geste.trace)
                  ? {
                      ...paroi,
                      composition: { id: paroi.composition?.id ?? "en-cours", composant: geste.composant, couches: geste.couches, epaisseur_cm: epaisseur },
                    }
                  : paroi,
              ),
            },
          },
    ),
  };
}
