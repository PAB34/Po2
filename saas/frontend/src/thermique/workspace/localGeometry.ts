import type { StudyContent, StudyOperation } from "../api";

type LocalOperation = Extract<StudyOperation, { type: "modifier" | "local_supprimer" }>;

/** Aperçu immédiat des gestes simples ; les métrés restent ceux du dernier calcul serveur. */
export function appliquerGeometrieLocale(content: StudyContent, operation: LocalOperation): StudyContent {
  if (operation.type === "local_supprimer") {
    return { ...content, locaux: content.locaux.filter((room) => room.id !== operation.id) };
  }
  return {
    ...content,
    locaux: content.locaux.map((room) =>
      room.id !== operation.id
        ? room
        : {
            ...room,
            nom: operation.nom?.trim() || room.nom,
            nature: operation.nature ?? room.nature,
            contour_pdf: operation.contour_pdf?.map((point) => [...point]) ?? room.contour_pdf,
          },
    ),
  };
}

export function rejouerGeometrieLocale(content: StudyContent, operations: LocalOperation[]): StudyContent {
  return operations.reduce(appliquerGeometrieLocale, content);
}
