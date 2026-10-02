import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

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
import { appliquerCreation, appliquerExtremite, type GesteCoupe, type GesteCreation, type GesteExtremite } from "./murs";
import { preparerAjout } from "./pontsAjoutes";
import { studyQueryKey } from "./study";

/**
 * Gestes sur les éléments d'enveloppe (F4, D68, D103 et D105).
 *
 * Chaque geste s'applique **dans l'écran**, sans serveur : un recalcul de niveau coûte 3,2 s sur le R+1,
 * et confirmer les 92 éléments douteux un par un ferait attendre cinq minutes pour rien. Les gestes
 * s'accumulent, le serveur ne recalcule qu'à la demande ou à l'enregistrement — et c'est ce recalcul
 * qui met le **plan** à jour, ce que l'écran annonce.
 *
 * Exception (D252) : **supprimer** un mur ou un indéterminé se voit à l'instant et s'enregistre tout seul,
 * en arrière-plan. Les gestes sont donc tenus dans des références : plusieurs gestes d'un même clic
 * (« tous les indéterminés ») s'enchaînent sans se marcher dessus, et un enregistrement ne perd pas les
 * gestes faits pendant qu'il tournait.
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
  const operationsRef = useRef<StudyOperation[]>([]);
  const annuleesRef = useRef<StudyOperation[]>([]);
  const localRef = useRef<StudyContent | null>(null);
  const busyRef = useRef(false);
  const fileEnregistrement = useRef<Promise<boolean>>(Promise.resolve(true));

  const poser = useCallback((suivantes: StudyOperation[], annuleesSuivantes: StudyOperation[], contenu: StudyContent | null) => {
    operationsRef.current = suivantes;
    annuleesRef.current = annuleesSuivantes;
    localRef.current = contenu;
    setOperations(suivantes);
    setAnnulees(annuleesSuivantes);
    setLocal(contenu);
  }, []);

  const occupe = useCallback((valeur: boolean) => {
    busyRef.current = valeur;
    setBusy(valeur);
  }, []);

  const reset = useCallback(() => {
    poser([], [], null);
    setMessage(null);
  }, [poser]);

  const apply = useCallback(
    (operation: StudyOperation) => {
      const base = localRef.current ?? study?.content;
      if (!base) {
        return false;
      }
      if (operation.type === "element_corriger") {
        const vise = base.enveloppe.releve_brut.elements.find((element) =>
          memeElement(refDeElement(element), operation.element),
        );
        const refus = vise ? refusDeCorrection(vise, operation.changes) : "Cet élément n'existe plus.";
        if (refus) {
          setMessage(refus);
          return false;
        }
      }
      poser([...operationsRef.current, operation], [], appliquerEnLocal(base, operation));
      setMessage(null);
      return true;
    },
    [poser, study],
  );

  /** Envoie une liste de gestes au serveur et affiche le niveau qu'elle donne, sans enregistrer. */
  const apercevoir = useCallback(
    async (liste: StudyOperation[], reussite: string) => {
      if (!token || !sheetId || liste.length === 0) {
        return null;
      }
      occupe(true);
      setMessage(null);
      try {
        const apercu = await thermiqueApi.remodelStudy(token, sheetId, liste);
        localRef.current = apercu.content;
        setLocal(apercu.content);
        setMessage(reussite);
        return apercu.content;
      } catch (echec) {
        setMessage(echec instanceof Error ? echec.message : "Le recalcul a échoué.");
        return null;
      } finally {
        occupe(false);
      }
    },
    [occupe, sheetId, token],
  );

  const undo = useCallback(() => {
    if (busyRef.current) {
      setMessage("Enregistrement en cours : annulez dans un instant.");
      return;
    }
    if (!study?.content || operationsRef.current.length === 0) {
      setMessage("Aucune correction locale à annuler.");
      return;
    }
    const suivant = annulerOperation({ operations: operationsRef.current, annulees: annuleesRef.current });
    poser(
      suivant.operations,
      suivant.annulees,
      suivant.operations.length ? rejouerOperations(study.content, suivant.operations) : null,
    );
    setMessage(
      suivant.operations.length
        ? "Dernière correction annulée — recalculez le plan pour actualiser le résultat."
        : "Dernière correction annulée. Aucune correction locale en attente.",
    );
  }, [poser, study]);

  const redo = useCallback(() => {
    if (busyRef.current) {
      setMessage("Enregistrement en cours : rétablissez dans un instant.");
      return;
    }
    if (!study?.content || annuleesRef.current.length === 0) {
      setMessage("Aucune correction locale à rétablir.");
      return;
    }
    const suivant = retablirOperation({ operations: operationsRef.current, annulees: annuleesRef.current });
    poser(suivant.operations, suivant.annulees, rejouerOperations(study.content, suivant.operations));
    setMessage("Correction rétablie — recalculez le plan pour actualiser le résultat.");
  }, [poser, study]);

  /** Envoie les gestes accumulés au serveur pour voir leur effet sur le plan, sans enregistrer. */
  const recompute = useCallback(async () => {
    await apercevoir(operationsRef.current, "Plan à jour. Les corrections ne sont pas encore enregistrées.");
  }, [apercevoir]);

  /**
   * Pose un pont que l'agent n'a pas vu, là où le thermicien a cliqué (remarque C, D157), **aussitôt**
   * (P5, D164), puis le désigne pour qu'il puisse lui donner son pont type.
   */
  const ajouterPont = useCallback(
    (point_pdf: PdfPoint, type_pont: string, reference_pont?: string) => {
      const base = localRef.current ?? study?.content;
      if (!base) return;
      const operation = preparerAjout(base, point_pdf, type_pont);
      if (!operation) {
        setMessage("Ce niveau n'a pas d'enveloppe relevée : le pont ne peut pas être situé.");
        return;
      }
      const geste = reference_pont ? { ...operation, reference_pont } : operation;
      poser([...operationsRef.current, geste], [], appliquerEnLocal(base, geste));
      setSelected({ troncon: geste.troncon, debut_m: geste.abscisse_m, fin_m: geste.abscisse_m });
      setMessage("Pont ajouté. Il sera enregistré avec les autres corrections.");
    },
    [poser, study],
  );

  /**
   * Enregistre les gestes en attente. Seuls ceux envoyés sont retirés de l'attente : un geste fait pendant
   * l'enregistrement reste en attente, rejoué sur l'étude que le serveur vient de rendre.
   */
  const save = useCallback(async () => {
    const envoyees = operationsRef.current;
    if (!token || !sheetId || envoyees.length === 0) {
      return true;
    }
    occupe(true);
    setMessage(null);
    try {
      const enregistre = await thermiqueApi.saveStudy(token, sheetId, {
        operations: envoyees,
        motif: "elements",
        valider: false,
      });
      queryClient.setQueryData<Study>(studyQueryKey(sheetId), enregistre);
      const reste = operationsRef.current.slice(envoyees.length);
      poser(reste, [], reste.length ? rejouerOperations(enregistre.content, reste) : null);
      return true;
    } catch (echec) {
      setMessage(echec instanceof Error ? echec.message : "L'enregistrement a échoué.");
      return false;
    } finally {
      occupe(false);
    }
  }, [occupe, poser, queryClient, sheetId, token]);
  const saveRef = useRef(save);
  saveRef.current = save;

  /**
   * Supprime (écarte, réactivable) un ou plusieurs éléments : ils quittent le plan à l'instant et
   * l'enregistrement part tout seul, à la suite d'un éventuel enregistrement en cours (D252).
   */
  const supprimer = useCallback(
    (refs: StudyElementRef[], motif: string) => {
      const posees = refs.filter((ref) => apply({ type: "element_ecarter", element: ref, motif }));
      if (posees.length === 0) return;
      setSelected(null);
      fileEnregistrement.current = fileEnregistrement.current.then(() => saveRef.current());
      void fileEnregistrement.current.then((ok) => {
        if (ok) {
          setMessage(posees.length > 1 ? `${posees.length} éléments supprimés et enregistrés.` : "Supprimé et enregistré.");
        }
      });
    },
    [apply],
  );

  /**
   * Déplace une extrémité de la ligne de métré du mur désigné (D249) : visible à l'instant, le mur reste
   * désigné sous sa nouvelle identité (ses bornes ont changé), l'enregistrement part tout seul (D252).
   */
  const deplacerExtremite = useCallback(
    (geste: GesteExtremite, entraines: GesteExtremite[] = []) => {
      const base = localRef.current ?? study?.content;
      if (!base) return;
      const { ref } = appliquerExtremite(base, geste);
      if (!ref || !apply(geste)) {
        setMessage("Ce mur ne peut plus être modifié ainsi.");
        return;
      }
      // Le sommet partagé entraîne l'extrémité des murs qui y aboutissent (D247).
      entraines.forEach((autre) => apply(autre));
      setSelected(ref);
      fileEnregistrement.current = fileEnregistrement.current.then(() => saveRef.current());
    },
    [apply, study],
  );

  /** Un mur tracé à la main (D250) : créé, désigné pour valider sa composition, enregistré aussitôt. */
  const creerMur = useCallback(
    (geste: GesteCreation) => {
      const base = localRef.current ?? study?.content;
      if (!base || !apply(geste)) return;
      setSelected(appliquerCreation(base, geste).ref);
      setMessage("Mur créé. Vérifiez et validez sa composition.");
      fileEnregistrement.current = fileEnregistrement.current.then(() => saveRef.current());
    },
    [apply, study],
  );

  /** Un point ajouté sur un mur (D247) : deux morceaux, le sommet commun se glisse ensuite. */
  const couperMur = useCallback(
    (geste: GesteCoupe) => {
      if (!apply(geste)) return;
      setSelected({ ...geste.element, fin_m: geste.abscisse_m });
      setMessage("Point ajouté : glissez le rond du sommet pour plier le mur.");
      fileEnregistrement.current = fileEnregistrement.current.then(() => saveRef.current());
    },
    [apply],
  );

  /** Des gestes visibles à l'instant et enregistrés aussitôt, en arrière-plan (D252, D262). */
  const gesteImmediat = useCallback(
    (gestes: StudyOperation[]) => {
      if (gestes.filter((geste) => apply(geste)).length === 0) return;
      fileEnregistrement.current = fileEnregistrement.current.then(() => saveRef.current());
    },
    [apply],
  );

  return {
    selected,
    select: setSelected,
    gesteImmediat,
    deplacerExtremite,
    creerMur,
    couperMur,
    /** Étude à afficher : celle que les gestes en attente décrivent, sinon celle en base. */
    shown: local && study ? { ...study, content: local } : study,
    pending: operations.length,
    canUndo: operations.length > 0,
    canRedo: annulees.length > 0,
    busy,
    message,
    apply: (operation: StudyOperation) => void apply(operation),
    supprimer,
    ajouterPont,
    recompute: () => void recompute(),
    save: () => void save(),
    saveAsync: save,
    cancel: reset,
    undo,
    redo,
  };
}
