import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { thermiqueApi, type Study, type StudyElementRef, type StudyOperation, type StudyPreview } from "../api";
import { studyQueryKey } from "./study";

/**
 * Gestes sur les éléments d'enveloppe (F4).
 *
 * Les corrections s'**accumulent** (D103) : chacune part au serveur avec celles qui la précèdent, pour
 * que le plan montre aussitôt leur effet, mais rien n'est écrit en base avant « Enregistrer ». Sur un
 * local à quinze éléments, quinze enregistrements versionnés n'auraient aucun sens.
 */
export function useStudyElements({
  token,
  sheetId,
  study,
}: {
  token: string | null;
  sheetId: number | null;
  study: Study | undefined;
}) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<StudyElementRef | null>(null);
  const [operations, setOperations] = useState<StudyOperation[]>([]);
  const [preview, setPreview] = useState<StudyPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const reset = useCallback(() => {
    setOperations([]);
    setPreview(null);
    setMessage(null);
  }, []);

  const apply = useCallback(
    async (operation: StudyOperation) => {
      if (!token || !sheetId) {
        return;
      }
      const suite = [...operations, operation];
      setBusy(true);
      setMessage(null);
      try {
        setPreview(await thermiqueApi.remodelStudy(token, sheetId, suite));
        setOperations(suite);
      } catch (echec) {
        // La liste ne retient pas un geste refusé : sinon il repartirait à chaque geste suivant.
        setMessage(echec instanceof Error ? echec.message : "Ce geste n'a pas pu être appliqué.");
      } finally {
        setBusy(false);
      }
    },
    [operations, sheetId, token],
  );

  const save = useCallback(async () => {
    if (!token || !sheetId || operations.length === 0) {
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const enregistre = await thermiqueApi.saveStudy(token, sheetId, {
        operations,
        motif: "elements",
        valider: false,
      });
      queryClient.setQueryData<Study>(studyQueryKey(sheetId), enregistre);
      reset();
    } catch (echec) {
      setMessage(echec instanceof Error ? echec.message : "L'enregistrement a échoué.");
    } finally {
      setBusy(false);
    }
  }, [operations, queryClient, reset, sheetId, token]);

  return {
    selected,
    select: setSelected,
    /** Étude à afficher : l'aperçu tant qu'il n'est pas enregistré, sinon celle en base. */
    shown: preview && study ? { ...study, content: preview.content } : study,
    pending: operations.length,
    busy,
    message,
    apply: (operation: StudyOperation) => void apply(operation),
    save: () => void save(),
    cancel: reset,
  };
}
