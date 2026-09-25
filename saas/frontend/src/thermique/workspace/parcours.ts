import type { Sheet, Study, StudyContent, StudyReleveElement } from "../api";
import { estPont } from "./elements";
import type { MetricsShow } from "./StudyMetrics";
import { validatedRoomCount } from "./study";

/**
 * Le parcours du thermicien sur un niveau (lot F2, D106 à D112).
 *
 * La colonne de gauche ne décrivait pas le travail, elle le décorait : cinq lignes figées, une seule
 * cliquable, et aucun lien avec ce que montrait le plan. Ici le parcours devient le modèle : chaque
 * étape sait ce qu'il lui reste à faire, quel panneau ouvrir et quels calques régler.
 *
 * Fonction pure : elle ne lit que l'étude, pour être vérifiable sans écran.
 */
export type EtapeId = "planche" | "analyse" | "locaux" | "enveloppe" | "ponts" | "hauteurs";

/** « fait » : rien ne reste. « en_cours » : il reste du travail. « attente » : le préalable manque. */
export type EtatEtape = "fait" | "en_cours" | "attente";

export type Etape = {
  id: EtapeId;
  titre: string;
  /** Ce qu'il reste à faire, en clair : un compteur qui ne descend pas est un défaut visible (D110). */
  reste: string;
  etat: EtatEtape;
  /** Panneau de droite que l'étape ouvre. */
  panneau: "planche" | "documents" | "fiche";
  /**
   * Calques que l'étape règle sur le plan (D106, Q6). `null` : l'étape ne touche pas à l'affichage.
   * Les cases à cocher restent maîtresses dès que le thermicien en touche une.
   */
  calques: MetricsShow | null;
};

const TOUT_ETEINT: MetricsShow = { metres: false, ponts: false, elements: false, toutesCotes: false };

/** Les éléments du relevé qui sont des ponts thermiques, dans l'ordre du parcours de l'enveloppe. */
export function pontsDuNiveau(content: StudyContent): StudyReleveElement[] {
  return content.enveloppe.releve_brut.elements.filter(estPont);
}

/** Les éléments du relevé qui ont un tracé : parois, menuiseries, poteaux, garde-corps. */
export function paroisDuNiveau(content: StudyContent): StudyReleveElement[] {
  return content.enveloppe.releve_brut.elements.filter((element) => !estPont(element));
}

export type Avancement = { total: number; restants: number; ecartes: number };

/**
 * Ce qui reste à juger dans un lot d'éléments.
 *
 * Un élément est jugé dès qu'il est confirmé, corrigé ou écarté. Deux régimes, et la différence vient
 * de l'usage :
 *
 * - `exigeant` faux, pour les 150 parois et menuiseries : ce que l'agent a lu sans hésiter compte pour
 *   jugé. Exiger un clic sur chacune ferait une corvée de 150 gestes sans rien apprendre.
 * - `exigeant` vrai, pour les 77 ponts : **chacun doit passer devant le thermicien**. C'est la demande
 *   explicite — plusieurs ponts au même coin ne sont pas une erreur, encore faut-il que quelqu'un dise
 *   lesquels comptent. La confiance de l'agent ne vaut pas validation ici.
 */
export function avancement(elements: StudyReleveElement[], exigeant = false): Avancement {
  return {
    total: elements.length,
    restants: elements.filter(
      (element) =>
        !element.exclu &&
        !element.confirme &&
        !element.corrige &&
        (exigeant || element.a_verifier),
    ).length,
    ecartes: elements.filter((element) => element.exclu).length,
  };
}

const pluriel = (nombre: number, mot: string) => `${nombre} ${mot}${nombre > 1 ? "s" : ""}`;

export function parcours(sheet: Sheet | null, study: Study | undefined): Etape[] {
  const content = study?.content;
  const planchePrete = sheet?.status === "prete";
  const nord = Boolean(sheet?.nord);

  const etapes: Etape[] = [
    {
      id: "planche",
      titre: "Planche à l'échelle",
      reste: !sheet
        ? "aucune planche"
        : !planchePrete
          ? "à classer et mettre à l'échelle"
          : nord
            ? "prête"
            : "le nord reste à poser",
      etat: !sheet || !planchePrete ? "en_cours" : nord ? "fait" : "en_cours",
      panneau: sheet ? "planche" : "documents",
      calques: TOUT_ETEINT,
    },
    {
      id: "analyse",
      // Sans cette étape, le thermicien ne sait pas où est son niveau quand il attend (Q7).
      titre: "Analyse du plan",
      reste: content ? "relevé reçu" : planchePrete ? "à envoyer à l'analyse" : "après la planche",
      etat: content ? "fait" : planchePrete ? "en_cours" : "attente",
      panneau: "planche",
      calques: null,
    },
  ];

  if (!content) {
    return [
      ...etapes,
      { id: "locaux", titre: "Locaux", reste: "après l'analyse", etat: "attente", panneau: "fiche", calques: null },
      { id: "enveloppe", titre: "Parois et menuiseries", reste: "après l'analyse", etat: "attente", panneau: "fiche", calques: null },
      { id: "ponts", titre: "Ponts thermiques", reste: "après l'analyse", etat: "attente", panneau: "fiche", calques: null },
      { id: "hauteurs", titre: "Hauteurs (coupes)", reste: "à venir", etat: "attente", panneau: "fiche", calques: null },
    ];
  }

  const locaux = content.locaux.length;
  const valides = study ? validatedRoomCount(study) : 0;
  const parois = avancement(paroisDuNiveau(content));
  // Les ponts se jugent un par un, sans exception : voir `avancement`.
  const ponts = avancement(pontsDuNiveau(content), true);

  etapes.push(
    {
      id: "locaux",
      titre: "Locaux",
      reste: valides >= locaux ? `${locaux} validés` : `${valides} sur ${locaux} validés`,
      etat: valides >= locaux ? "fait" : "en_cours",
      panneau: "fiche",
      // Les contours seuls : à cette étape on juge des pièces, pas de la maçonnerie.
      calques: TOUT_ETEINT,
    },
    {
      id: "enveloppe",
      titre: "Parois et menuiseries",
      reste:
        parois.restants === 0
          ? `${parois.total} relevées${parois.ecartes > 0 ? `, ${pluriel(parois.ecartes, "écartée")}` : ""}`
          : `${pluriel(parois.restants, "élément")} à vérifier`,
      etat: parois.restants === 0 ? "fait" : "en_cours",
      panneau: "fiche",
      calques: { metres: true, ponts: false, elements: true, toutesCotes: false },
    },
    {
      id: "ponts",
      titre: "Ponts thermiques",
      reste:
        ponts.restants === 0
          ? `${ponts.total} jugés${ponts.ecartes > 0 ? `, ${pluriel(ponts.ecartes, "écarté")}` : ""}`
          : `${pluriel(ponts.restants, "pont")} à juger sur ${ponts.total}`,
      etat: ponts.restants === 0 ? "fait" : "en_cours",
      panneau: "fiche",
      // Les ponts seuls : c'est l'étape où l'on veut les distinguer un à un (Q4, Q6).
      calques: { metres: false, ponts: true, elements: false, toutesCotes: false },
    },
    {
      id: "hauteurs",
      titre: "Hauteurs (coupes)",
      reste: "à venir",
      etat: "attente",
      panneau: "fiche",
      calques: null,
    },
  );
  return etapes;
}

/**
 * L'étape où l'on se trouve quand rien n'est demandé : la première qui n'est pas finie.
 *
 * Le parcours n'interdit rien (D109) : c'est une proposition d'entrée, pas un verrou. Tout étant fini,
 * on reste sur les ponts, dernière étape réellement travaillable.
 */
export function etapeCourante(etapes: Etape[]): EtapeId {
  return (etapes.find((etape) => etape.etat === "en_cours") ?? etapes[etapes.length - 2]).id;
}
