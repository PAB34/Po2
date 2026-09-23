import type { PdfPoint, Study, StudyLocalNature, StudyRoom } from "../api";

export const studyQueryKey = (sheetId: number | null) => ["thermique", "etude", sheetId] as const;

const NATURE_ORDER: Record<StudyLocalNature, number> = { chauffe: 0, circulation: 1, non_chauffe: 2 };

export const NATURE_LABELS: Record<StudyLocalNature, string> = {
  chauffe: "Chauffé",
  circulation: "Circulation",
  non_chauffe: "Non chauffé",
};

export const NATURE_COLORS: Record<StudyLocalNature, string> = {
  chauffe: "#e58c25",
  circulation: "#3278ad",
  non_chauffe: "#6b7280",
};

export function sortedStudyRooms(rooms: StudyRoom[]): StudyRoom[] {
  return rooms
    .map((room, index) => ({ room, index }))
    .sort((left, right) => NATURE_ORDER[left.room.nature] - NATURE_ORDER[right.room.nature] || left.index - right.index)
    .map(({ room }) => room);
}

/** Le point est-il dans le polygone ? Lancer de rayon, la méthode la plus sûre sur un contour concave. */
function contient(contour: PdfPoint[], [x, y]: PdfPoint): boolean {
  let dedans = false;
  for (let rang = 0, precedent = contour.length - 1; rang < contour.length; precedent = rang++) {
    const [xi, yi] = contour[rang];
    const [xj, yj] = contour[precedent];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
      dedans = !dedans;
    }
  }
  return dedans;
}

function aire(contour: PdfPoint[]): number {
  let somme = 0;
  for (let rang = 0, precedent = contour.length - 1; rang < contour.length; precedent = rang++) {
    somme += contour[precedent][0] * contour[rang][1] - contour[rang][0] * contour[precedent][1];
  }
  return Math.abs(somme) / 2;
}

/** Le local sous ce point du plan. Quand deux locaux se recouvrent, le plus petit gagne : c'est celui
 *  que l'on vise en cliquant dans un coin d'un grand plateau ouvert. */
export function roomAt(rooms: StudyRoom[], point: PdfPoint): StudyRoom | null {
  const candidats = rooms.filter((room) => room.contour_pdf?.length >= 3 && contient(room.contour_pdf, point));
  if (candidats.length === 0) {
    return null;
  }
  return candidats.reduce((petit, room) => (aire(room.contour_pdf) < aire(petit.contour_pdf) ? room : petit));
}

export function validatedRoomCount(study: Study): number {
  return Object.values(study.local_states).filter((state) => state.status === "valide").length;
}
