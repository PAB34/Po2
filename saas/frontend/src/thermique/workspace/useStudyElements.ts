import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import {
  thermiqueApi,
  type Study,
  type StudyContent,
  type StudyElementRef,
  type StudyOperation,
} from "../api";
import { appliquerEnLocal, refusDeCorrection } from "./elementsLocal";
import { annulerOperation, rejouerOperations, retablirOperation } from "./elementsHistory";
import { memeElement, refDeElement } from "./elements";
import { studyQueryKey } from "./study";

/**
 * Gestes sur les éléments d'enveloppe (F4, D68, D103 et D105).
 *
 * Chaque geste s'applique **dans l'écran**, sans serveur : un recalcul de niveau coûte 3,2 s sur le R+1,
 * et confirmer les 92 éléments douteux un par un ferait attendre cinq minutes pour rien. Les gestes
 * s'accumulent, le serveur ne recalcule qu'à la demande ou à l'enregistrement — et c'est ce recalcul
 * qui met le **plan** à jour, ce que l'écran annonce.
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
  const [annulees, setAnnulees] = useState<StudyOperation[]>([]);
  // Étude telle qu'elle serait après les gestes en attente : recalculée en local, pas par le serveur.
  const [local, setLocal] = useState<StudyContent | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const reset = useCallback(() => {
    setOperations([]);
    setAnnulees([]);
    setLocal(null);
    setMessage(null);
  }, []);

  const apply = useCallback(
    (operation: StudyOperation) => {
      const base = local ?? study?.content;
      if (!base) {
        return;
      }
      if (operation.type === "element_corriger") {
        const vise = base.enveloppe.releve_brut.elements.find((element) =>
          memeElement(refDeElement(element), operation.element),
        );
        const refus = vise ? refusDeCorrection(vise, operation.changes) : "Cet élément n'existe plus.";
        if (refus) {
          setMessage(refus);
          return;
        }
      }
      setLocal(appliquerEnLocal(base, operation));
      setOperations((current) => [...current, operation]);
      setAnnulees([]);
      setMessage(null);
    },
    [local, study],
  );

  const undo = useCallback(() => {
    if (!study?.content || operations.length === 0) {
      setMessage("Aucune correction locale à annuler.");
      return;
    }
    const suivant = annulerOperation({ operations, annulees });
    setOperations(suivant.operations);
    setAnnulees(suivant.annulees);
    setLocal(suivant.operations.length ? rejouerOperations(study.content, suivant.operations) : null);
    setMessage(
      suivant.operations.length
        ? "Dernière correction annulée — recalculez le plan pour actualiser le résultat."
        : "Dernière correction annulée. Aucune correction locale en attente.",
    );
  }, [annulees, operations, study]);

  const redo = useCallback(() => {
    if (!study?.content || annulees.length === 0) {
      setMessage("Aucune correction locale à rétablir.");
      return;
    }
    const suivant = retablirOperation({ operations, annulees });
    setOperations(suivant.operations);
    setAnnulees(suivant.annulees);
    setLocal(rejouerOperations(study.content, suivant.operations));
    setMessage("Correction rétablie — recalculez le plan pour actualiser le résultat.");
  }, [annulees, operations, study]);

  /** Envoie les gestes accumulés au serveur pour voir leur effet sur le plan, sans enregistrer. */
  const recompute = useCallback(async () => {
    if (!token || !sheetId || operations.length === 0) {
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const apercu = await thermiqueApi.remodelStudy(token, sheetId, operations);
      setLocal(apercu.content);
      setMessage("Plan à jour. Les corrections ne sont pas encore enregistrées.");
    } catch (echec) {
      setMessage(echec instanceof Error ? echec.message : "Le recalcul a échoué.");
    } finally {
      setBusy(false);
    }
  }, [operations, sheetId, token]);

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
    /** Étude à afficher : celle que les gestes en attente décrivent, sinon celle en base. */
    shown: local && study ? { ...study, content: local } : study,
    pending: operations.length,
    canUndo: operations.length > 0,
    canRedo: annulees.length > 0,
    busy,
    message,
    apply,
    recompute: () => void recompute(),
    save: () => void save(),
    cancel: reset,
    undo,
    redo,
  };
}
