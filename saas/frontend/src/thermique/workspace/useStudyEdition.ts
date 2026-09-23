import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import { thermiqueApi, type PdfPoint, type Study, type StudyOperation, type StudyPreview, type StudyRoom } from "../api";
import type { PickEvent } from "../components/TileSheetViewer";
import type { StudyEdition } from "./StudyPanel";
import {
  draftFromRoom,
  insertVertex,
  moveVertex,
  nearestVertex,
  removeVertex,
  type EditMode,
  type StudyDraft,
} from "./edition";
import { sortedStudyRooms, studyQueryKey } from "./study";

// Rayon de saisie d'une poignée, en pixels d'écran.
const PRISE_PX = 10;

export function useStudyEdition({
  token,
  sheetId,
  study,
  selectedRoom,
  onSelectRoom,
}: {
  token: string | null;
  sheetId: number | null;
  study: Study | undefined;
  selectedRoom: StudyRoom | null;
  onSelectRoom: (id: string) => void;
}) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<StudyDraft | null>(null);
  const [preview, setPreview] = useState<StudyPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const dragIndex = useRef<number | null>(null);
  const pixelsPerPt = useRef(1);

  const versions = useQuery({
    queryKey: ["thermique", "etude-versions", sheetId],
    queryFn: () => thermiqueApi.listStudyVersions(token!, sheetId!),
    enabled: Boolean(token && sheetId && study),
  });

  const reset = useCallback(() => {
    setDraft(null);
    setPreview(null);
    setMessage(null);
    dragIndex.current = null;
  }, []);

  const operations = useCallback((): StudyOperation[] => {
    if (!draft) {
      return [];
    }
    if (draft.mode === "couper") {
      if (draft.cut.length < 2) {
        return [];
      }
      return [{ type: "couper", id: draft.roomId, segment_pdf: draft.cut, noms: draft.noms }];
    }
    return [{ type: "modifier", id: draft.roomId, contour_pdf: draft.contour, nature: draft.nature, nom: draft.nom }];
  }, [draft]);

  const recompute = useCallback(
    async (gestes?: StudyOperation[]) => {
      const liste = gestes ?? operations();
      if (!token || !sheetId || !liste.length) {
        setMessage("Il n'y a rien à recalculer pour l'instant.");
        return null;
      }
      setBusy(true);
      setMessage(null);
      try {
        const resultat = await thermiqueApi.remodelStudy(token, sheetId, liste, draft?.roomId ?? null);
        setPreview(resultat);
        if (resultat.bloquant) {
          setMessage(null);
        }
        return resultat;
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Le recalcul a échoué.");
        return null;
      } finally {
        setBusy(false);
      }
    },
    [draft, operations, sheetId, token],
  );

  const save = useCallback(async () => {
    const liste = operations();
    if (!token || !sheetId || !liste.length) {
      setMessage("Aucune modification à enregistrer.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const enregistre = await thermiqueApi.saveStudy(token, sheetId, {
        operations: liste,
        local_id: draft?.roomId ?? null,
        motif: "validation_local",
        valider: true,
      });
      queryClient.setQueryData<Study>(studyQueryKey(sheetId), enregistre);
      void versions.refetch();
      reset();
      // Enchaîner sur le premier local encore à vérifier, chauffés d'abord (D63).
      const suivant = sortedStudyRooms(enregistre.content.locaux).find(
        (room) => (enregistre.local_states[room.id]?.status ?? "a_verifier") !== "valide",
      );
      if (suivant) {
        onSelectRoom(suivant.id);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "L'enregistrement a échoué.");
    } finally {
      setBusy(false);
    }
  }, [draft, onSelectRoom, operations, queryClient, reset, sheetId, token, versions]);

  const merge = useCallback(
    async (otherId: string) => {
      if (!selectedRoom) {
        return;
      }
      await recompute([{ type: "fusionner", ids: [selectedRoom.id, otherId] }]);
      setDraft({ ...draftFromRoom(selectedRoom), mode: "contour" });
      setMessage("Fusion calculée : vérifiez le plan puis enregistrez.");
    },
    [recompute, selectedRoom],
  );

  const restore = useCallback(
    async (numero: number) => {
      if (!token || !sheetId) {
        return;
      }
      setBusy(true);
      try {
        const revenu = await thermiqueApi.restoreStudyVersion(token, sheetId, numero);
        queryClient.setQueryData<Study>(studyQueryKey(sheetId), revenu);
        void versions.refetch();
        reset();
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Le retour en arrière a échoué.");
      } finally {
        setBusy(false);
      }
    },
    [queryClient, reset, sheetId, token, versions],
  );

  const edition: StudyEdition | undefined = selectedRoom
    ? {
        draft,
        busy,
        message,
        blocking: preview?.bloquant ?? null,
        neighbours: preview?.voisins_modifies ?? [],
        coverage: preview?.couverture ?? study?.content.couverture ?? null,
        versions: versions.data ?? [],
        rooms: study?.content.locaux ?? [],
        onStart: (mode: EditMode) => {
          setPreview(null);
          setMessage(null);
          setDraft(draftFromRoom(selectedRoom, mode));
        },
        onCancel: reset,
        onDraft: (changes) => setDraft((current) => (current ? { ...current, ...changes } : current)),
        onRecompute: () => void recompute(),
        onSave: () => void save(),
        onMerge: (otherId: string) => void merge(otherId),
        onRestore: (numero: number) => void restore(numero),
      }
    : undefined;

  const grab = (point: PdfPoint, echelle: number, event: PickEvent): boolean => {
    pixelsPerPt.current = echelle;
    if (!draft || draft.mode !== "contour") {
      return false;
    }
    const index = nearestVertex(draft.contour, point, PRISE_PX / echelle);
    if (index === null) {
      return false;
    }
    if (event.altKey) {
      setDraft({ ...draft, contour: removeVertex(draft.contour, index) });
      return false;
    }
    dragIndex.current = index;
    return true;
  };

  const grabMove = (point: PdfPoint) => {
    const index = dragIndex.current;
    if (index === null) {
      return;
    }
    setDraft((current) => (current ? { ...current, contour: moveVertex(current.contour, index, point) } : current));
  };

  const addPoint = (point: PdfPoint): boolean => {
    if (!draft) {
      return false;
    }
    if (draft.mode === "couper") {
      setDraft({ ...draft, cut: draft.cut.length >= 2 ? [point] : [...draft.cut, point] });
    } else {
      setDraft({ ...draft, contour: insertVertex(draft.contour, point, PRISE_PX / pixelsPerPt.current) });
    }
    return true;
  };

  return {
    draft,
    preview,
    edition,
    /** Étude affichée : l'aperçu tant qu'il n'est pas enregistré, sinon l'étude en base. */
    shown: preview ? { ...(study as Study), content: preview.content } : study,
    handlers: {
      onGrab: grab,
      onGrabMove: grabMove,
      onGrabEnd: () => {
        dragIndex.current = null;
      },
      onAddPoint: addPoint,
    },
    reset,
  };
}
