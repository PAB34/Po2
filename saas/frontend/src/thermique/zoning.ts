import type { Room } from "./pieces";

export type ZoneKind = "bureau" | "equipement" | "sanitaire" | "public" | "circulation" | "exterieur";

export const ZONE_STYLES: Record<ZoneKind, { label: string; color: string }> = {
  bureau: { label: "Bureaux", color: "#2f80c9" },
  equipement: { label: "Stockage / équipement", color: "#3d9b62" },
  sanitaire: { label: "Sanitaires", color: "#e98224" },
  public: { label: "Public", color: "#8e5cc2" },
  circulation: { label: "Circulation", color: "#60758a" },
  exterieur: { label: "Exclu / vide / extérieur", color: "#d64a45" },
};

const normalized = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

export function zoneKind(room: Room): ZoneKind {
  if (room.classe === "exterieur") return "exterieur";
  const name = normalized(room.nom);
  if (/sanitaire|vestiaire|douche|toilette|\bwc\b/.test(name)) return "sanitaire";
  if (/circul|couloir|palier|degagement|escalier|ascenseur|hall/.test(name)) return "circulation";
  if (/equip|stock|acquisition|catalog|archive|local technique|reserve/.test(name)) return "equipement";
  if (/bureau|direction|assistant|administration|reunion|pause/.test(name)) return "bureau";
  return "public";
}

export function zoneSummary(rooms: Room[]) {
  return (Object.keys(ZONE_STYLES) as ZoneKind[])
    .map((kind) => {
      const matching = rooms.filter((room) => zoneKind(room) === kind);
      return { kind, count: matching.length, area: matching.reduce((total, room) => total + room.surface_m2, 0) };
    })
    .filter((entry) => entry.count > 0);
}
