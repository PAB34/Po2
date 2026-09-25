import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { StudyRoom } from "../api";
import { StudyRoomPanel, type StudyEdition } from "./StudyPanel";

const room = {
  id: "piece-001",
  nom: "Bureau",
  nature: "chauffe",
  contour: [],
  contour_pdf: [],
  limites: [],
  surface_m2: 12,
  fiche: { piece: "Bureau", local: "chauffe", surface_m2: 12, perimetre_m: 14, cotes: [], deperditif_m: 4 },
  synthese: {},
  demandes: [],
} as StudyRoom;

const edition = (natureBlockedReason: string | null = null): StudyEdition => ({
  draft: null,
  busy: false,
  message: null,
  blocking: null,
  neighbours: [],
  coverage: null,
  versions: [],
  rooms: [room],
  natureBlockedReason,
  onNature: vi.fn(),
  onStart: vi.fn(),
  onCancel: vi.fn(),
  onDraft: vi.fn(),
  onRecompute: vi.fn(),
  onSave: vi.fn(),
  onMerge: vi.fn(),
  onRestore: vi.fn(),
});

describe("nature directement sur la fiche du local", () => {
  it("propose les quatre natures, dont la gaine technique, hors du brouillon de contour", () => {
    const html = renderToStaticMarkup(<StudyRoomPanel room={room} edition={edition()} />);
    expect(html).toContain('aria-label="Nature de Bureau"');
    expect(html).toContain("Gaine technique");
    expect(html).not.toContain("disabled");
  });

  it("explique pourquoi le choix est bloqué quand une correction d'élément attend", () => {
    const motif = "Enregistrez ou abandonnez d'abord les corrections d'éléments en attente.";
    const html = renderToStaticMarkup(<StudyRoomPanel room={room} edition={edition(motif)} />);
    expect(html).toContain("disabled");
    expect(html).toContain("Enregistrez ou abandonnez d&#x27;abord");
  });
});
