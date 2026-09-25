import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import {
  thermiqueApi,
  type PdfPoint,
  type Study,
  type StudyLocalNature,
  type StudyOperation,
  type StudyPreview,
  type StudyRoom,
} from "../api";
import type { PickEvent } from "../components/TileSheetViewer";
import type { StudyEdition } from "./StudyPanel";
import {
  draftFromRoom,
  insertVertex,
  moveVertex,
  nearestSide,
  nearestVertex,
  removeVertex,
  removeVerticesInLasso,
  straightenSide,
  type EditMode,
  type StudyDraft,
} from "./edition";
import { changeLocalNatureOperation, sortedStudyRooms, studyQueryKey } from "./study";

// Rayon de saisie d'une poignée, en pixels d'écran.
const PRISE_PX = 10;
// Pas d'échantillonnage du lasso, en pixels d'écran.
const PAS_LASSO_PX = 2;

export function useStudyEdition({
  token,
  sheetId,
  study,
  selectedRoom,
  onSelectRoom,
  natureBlockedReason,
}: {
  token: string | null;
  sheetId: number | null;
  study: Study | undefined;
  selectedRoom: StudyRoom | null;
  onSelectRoom: (id: string) => void;
  natureBlockedReason: string | null;
}) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<StudyDraft | null>(null);
  const [preview, setPreview] = useState<StudyPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const dragIndex = useRef<number | null>(null);
  // Tracé du lasso en cours. Hors état React : il se remplit à chaque mouvement de souris.
  const lassoPath = useRef<PdfPoint[] | null>(null);
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
    lassoPath.current = null;
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

  const changeNature = useCallback(
    async (roomId: string, nature: StudyLocalNature) => {
      if (!token || !sheetId) {
        return;
      }
      if (busy) {
        return;
      }
      if (draft) {
        setMessage("Terminez ou annulez d'abord la reprise du contour.");
        return;
      }
      if (natureBlockedReason) {
        setMessage(natureBlockedReason);
        return;
      }
      const room = study?.content.locaux.find((item) => item.id === roomId);
      if (!room || room.nature === nature) {
        return;
      }
      setBusy(true);
      setMessage(null);
      try {
        const enregistre = await thermiqueApi.saveStudy(token, sheetId, {
          operations: [changeLocalNatureOperation(roomId, nature)],
          local_id: roomId,
          motif: "nature_local",
          valider: false,
        });
        queryClient.setQueryData<Study>(studyQueryKey(sheetId), enregistre);
        setPreview(null);
        setMessage("Nature enregistrée et métrés recalculés.");
        void versions.refetch();
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Le changement de nature a échoué.");
      } finally {
        setBusy(false);
      }
    },
    [busy, draft, natureBlockedReason, queryClient, sheetId, study, token, versions],
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
        natureBlockedReason: draft ? "Terminez ou annulez d'abord la reprise du contour." : natureBlockedReason,
        onNature: (nature: StudyLocalNature) => void changeNature(selectedRoom.id, nature),
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

  /** Ouvre l'édition sur un local désigné, sans attendre qu'il soit déjà sélectionné (clic droit). */
  const startOn = (roomId: string, mode: EditMode) => {
    const room = study?.content.locaux.find((item) => item.id === roomId);
    if (!room) {
      return;
    }
    setPreview(null);
    setMessage(null);
    setDraft(draftFromRoom(room, mode));
  };

  const grab = (point: PdfPoint, echelle: number, event: PickEvent): boolean => {
    pixelsPerPt.current = echelle;
    if (!draft || draft.mode !== "contour") {
      return false;
    }
    const index = nearestVertex(draft.contour, point, PRISE_PX / echelle);
    if (index === null) {
      // Alt dans le vide : on ouvre un lasso plutôt que de déplacer le plan. Alt veut dire
      // « supprimer » partout : sur une poignée un seul sommet, en entourant tous ceux visés.
      if (event.altKey) {
        lassoPath.current = [point];
        setDraft({ ...draft, lasso: [point] });
        return true;
      }
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
    const trace = lassoPath.current;
    if (trace) {
      // Un point tous les 2 pixels écran suffit à suivre la main sans alourdir le tracé.
      const dernier = trace[trace.length - 1];
      if (Math.hypot(point[0] - dernier[0], point[1] - dernier[1]) * pixelsPerPt.current >= PAS_LASSO_PX) {
        trace.push(point);
        setDraft((current) => (current ? { ...current, lasso: [...trace] } : current));
      }
      return;
    }
    const index = dragIndex.current;
    if (index === null) {
      return;
    }
    setDraft((current) => (current ? { ...current, contour: moveVertex(current.contour, index, point) } : current));
  };

  const grabEnd = () => {
    dragIndex.current = null;
    const trace = lassoPath.current;
    if (!trace) {
      return;
    }
    lassoPath.current = null;
    setDraft((current) => {
      if (!current) {
        return current;
      }
      const { contour, removed, refus } = removeVerticesInLasso(current.contour, trace);
      setMessage(
        removed > 0
          ? `${removed} point${removed > 1 ? "s" : ""} supprimé${removed > 1 ? "s" : ""} : le contour passe tout droit.`
          : refus === "trop"
            ? "Lasso trop large : il ne resterait pas assez de points pour fermer le local. Zoomez et reprenez."
            : "Aucun point entouré.",
      );
      return { ...current, contour, lasso: null };
    });
  };

  /** Ce que le clic droit propose là où il tombe. Le menu ne montre que des gestes applicables. */
  const contextActions = (point: PdfPoint, echelle: number): { cle: string; label: string; faire: () => void }[] => {
    if (!draft || draft.mode !== "contour") {
      return [];
    }
    const tolerance = PRISE_PX / echelle;
    const sommet = nearestVertex(draft.contour, point, tolerance);
    const cote = nearestSide(draft.contour, point, tolerance * 2);
    const actions: { cle: string; label: string; faire: () => void }[] = [];
    if (sommet !== null && draft.contour.length > 3) {
      actions.push({
        cle: "supprimer",
        label: "Supprimer ce point",
        faire: () => {
          setDraft((current) =>
            current ? { ...current, contour: removeVertex(current.contour, sommet) } : current,
          );
          setMessage("Point supprimé : le contour passe tout droit entre ses deux voisins.");
        },
      });
    } else if (cote !== null) {
      actions.push({
        cle: "ajouter",
        label: "Ajouter un point ici",
        faire: () =>
          setDraft((current) =>
            current ? { ...current, contour: insertVertex(current.contour, point, tolerance * 2) } : current,
          ),
      });
    }
    if (cote !== null) {
      actions.push({
        cle: "redresser",
        label: "Redresser ce côté",
        faire: () =>
          setDraft((current) => {
            if (!current) {
              return current;
            }
            const { contour, removed } = straightenSide(current.contour, cote);
            setMessage(
              removed > 0
                ? `Côté redressé : ${removed} point${removed > 1 ? "s" : ""} de moins.`
                : "Ce côté est déjà droit.",
            );
            return { ...current, contour };
          }),
      });
    }
    return actions;
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
      onGrabEnd: grabEnd,
      onAddPoint: addPoint,
    },
    contextActions,
    startOn,
    changeNature,
    natureChangeDisabled: Boolean(draft || busy || natureBlockedReason),
    natureBlockedReason: draft ? "Terminez ou annulez d'abord la reprise du contour." : natureBlockedReason,
    reset,
  };
}
