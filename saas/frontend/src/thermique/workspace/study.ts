import type { Study, StudyLocalNature, StudyRoom } from "../api";

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

export function validatedRoomCount(study: Study): number {
  return Object.values(study.local_states).filter((state) => state.status === "valide").length;
}
