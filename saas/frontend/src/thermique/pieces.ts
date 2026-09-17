// Pièces des plans, étape E3 (docs/thermique/refondation-parcours-decisions.md §13).
import { request, type PdfPoint } from "./api";

export type RoomClass = "chauffe" | "non_chauffe" | "exterieur";

export type Room = {
  id: number;
  nom: string;
  repere: string | null;
  nom_source: "lu" | "saisi" | null;
  classe: RoomClass;
  classe_source: "propose" | "choisi";
  // x1, y1, x2, y2… en points PDF
  contour: number[];
  centre: PdfPoint;
  surface_m2: number;
  source: "auto" | "manuel";
};

export type SheetRooms = {
  pieces: Room[];
  lecture_noms: "a_faire" | "en_cours" | "faite";
  limites: { elements: number; natures: string[] };
  classes: Record<RoomClass, string>;
  totaux: Record<RoomClass, number>;
};

export const ROOM_COLORS: Record<RoomClass, string> = {
  chauffe: "#d9480f",
  non_chauffe: "#1c7ed6",
  exterieur: "#2b8a3e",
};

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const piecesApi = {
  list: (token: string, sheetId: number) => request<SheetRooms>(token, `/thermique/sheets/${sheetId}/pieces`),
  detect: (token: string, sheetId: number, fermetureCm: number) =>
    request<SheetRooms>(token, `/thermique/sheets/${sheetId}/pieces/detecter`, json("POST", { fermeture_cm: fermetureCm })),
  add: (token: string, sheetId: number, point: PdfPoint, fermetureCm: number) =>
    request<SheetRooms>(token, `/thermique/sheets/${sheetId}/pieces`, json("POST", { x: point[0], y: point[1], fermeture_cm: fermetureCm })),
  merge: (token: string, sheetId: number, ids: number[]) =>
    request<SheetRooms>(token, `/thermique/sheets/${sheetId}/pieces/fusion`, json("POST", { ids })),
  update: (token: string, roomId: number, payload: { nom?: string; classe?: RoomClass }) =>
    request<SheetRooms>(token, `/thermique/pieces/${roomId}`, json("PATCH", payload)),
  remove: (token: string, roomId: number) => request<SheetRooms>(token, `/thermique/pieces/${roomId}`, { method: "DELETE" }),
  split: (token: string, roomId: number, p1: PdfPoint, p2: PdfPoint) =>
    request<SheetRooms>(token, `/thermique/pieces/${roomId}/decoupe`, json("POST", { p1, p2 })),
};

export function insideRoom(point: PdfPoint, contour: number[]): boolean {
  let inside = false;
  const n = contour.length / 2;
  for (let k = 0, j = n - 1; k < n; j = k++) {
    const [x1, y1, x2, y2] = [contour[2 * k], contour[2 * k + 1], contour[2 * j], contour[2 * j + 1]];
    if (y1 > point[1] !== y2 > point[1] && point[0] < x1 + ((point[1] - y1) * (x2 - x1)) / (y2 - y1)) {
      inside = !inside;
    }
  }
  return inside;
}
