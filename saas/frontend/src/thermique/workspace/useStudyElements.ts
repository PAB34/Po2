import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import {
  thermiqueApi,
  type PdfPoint,
  type Study,
  type StudyContent,
  type StudyElementRef,
  type StudyOperation,
} from "../api";
import { appliquerEnLocal, refusDeCorrection } from "./elementsLocal";
import { annulerOperation, rejouerOperations, retablirOperation } from "./elementsHistory";
import { memeElement, refDeElement } from "./elements";
import { studyQueryKey } from "./study";

const cle = (ref: StudyElementRef) => `${ref.troncon}|${ref.debut_m}|${ref.fin_m}`;
const avecAjout = (liste: StudyOperation[]) => liste.some((operation) => operation.type === "pont_ajouter");

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

  /**
   * Envoie une liste de gestes au serveur et affiche le niveau qu'elle donne, sans enregistrer.
   *
   * Un pont ajouté ne s'applique pas dans l'écran : seul le serveur sait sur quel tronçon il tombe, donc
   * quelle identité il prend dans le relevé (D157). Dès qu'un ajout est dans la liste, l'aperçu passe par
   * ici — sinon le pont disparaîtrait de l'écran et les gestes qui le visent ne viseraient plus rien.
   */
  const apercevoir = useCallback(
    async (liste: StudyOperation[], reussite: string) => {
      if (!token || !sheetId || liste.length === 0) {
        return null;
      }
      setBusy(true);
      setMessage(null);
      try {
        const apercu = await thermiqueApi.remodelStudy(token, sheetId, liste);
        setLocal(apercu.content);
        setMessage(reussite);
        return apercu.content;
      } catch (echec) {
        setMessage(echec instanceof Error ? echec.message : "Le recalcul a échoué.");
        return null;
      } finally {
        setBusy(false);
      }
    },
    [sheetId, token],
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
    if (avecAjout(suivant.operations)) {
      void apercevoir(suivant.operations, "Dernière correction annulée. Plan recalculé, rien n'est encore enregistré.");
    }
  }, [annulees, apercevoir, operations, study]);

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
    if (avecAjout(suivant.operations)) {
      void apercevoir(suivant.operations, "Correction rétablie. Plan recalculé, rien n'est encore enregistré.");
    }
  }, [annulees, apercevoir, operations, study]);

  /** Envoie les gestes accumulés au serveur pour voir leur effet sur le plan, sans enregistrer. */
  const recompute = useCallback(async () => {
    await apercevoir(operations, "Plan à jour. Les corrections ne sont pas encore enregistrées.");
  }, [apercevoir, operations]);

  /**
   * Pose un pont que l'agent n'a pas vu, là où le thermicien a cliqué (remarque C, D157), puis le désigne
   * pour qu'il puisse aussitôt lui donner son pont type.
   */
  const ajouterPont = useCallback(
    async (point_pdf: PdfPoint, type_pont: string) => {
      const base = local ?? study?.content;
      if (!base) return;
      const avant = new Set(base.enveloppe.releve_brut.elements.map((element) => cle(refDeElement(element))));
      const liste: StudyOperation[] = [...operations, { type: "pont_ajouter", point_pdf, type_pont }];
      setOperations(liste);
      setAnnulees([]);
      const apercu = await apercevoir(
        liste,
        "Pont ajouté. Donnez-lui son pont type avec « Réattribuer… » ; rien n'est encore enregistré.",
      );
      const nouveau = apercu?.enveloppe.releve_brut.elements.find(
        (element) => element.ajoute && !avant.has(cle(refDeElement(element))),
      );
      if (nouveau) {
        setSelected(refDeElement(nouveau));
      } else if (!apercu) {
        // Le serveur a refusé : le geste ne reste pas dans la liste, sinon il bloquerait l'enregistrement.
        setOperations(operations);
      }
    },
    [apercevoir, local, operations, study],
  );

  const save = useCallback(async () => {
    if (!token || !sheetId || operations.length === 0) {
      return true;
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
      return true;
    } catch (echec) {
      setMessage(echec instanceof Error ? echec.message : "L'enregistrement a échoué.");
      return false;
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
    ajouterPont: (point: PdfPoint, type: string) => void ajouterPont(point, type),
    recompute: () => void recompute(),
    save: () => void save(),
    saveAsync: save,
    cancel: reset,
    undo,
    redo,
  };
}
