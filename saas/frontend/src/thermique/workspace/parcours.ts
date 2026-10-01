import type { HauteursDuPlan, Sheet, Study, StudyContent, StudyReleveElement, StudyRoom, VueCoupe } from "../api";
import { estPont } from "./elements";
import { baiesDuNiveau } from "./modeles";
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
export type EtapeId = "planche" | "analyse" | "lecture" | "locaux" | "enveloppe" | "menuiseries" | "ponts" | "hauteurs";

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

/**
 * Les menuiseries du niveau (baies entières, D224) et celles qui n'ont pas encore de modèle mesuré (D227). Un
 * mur-rideau n'en attend pas : sa hauteur est celle du local qu'il borde (D196).
 */
export function avancementMenuiseries(content: StudyContent): { total: number; sansModele: number } {
  const baies = baiesDuNiveau(content).filter(
    (baie) => !baie.some((morceau) => String(morceau.menuiserie_type ?? "").toLowerCase().includes("rideau")),
  );
  return { total: baies.length, sansModele: baies.filter((baie) => !baie[0].modele).length };
}

const pluriel = (nombre: number, mot: string) => `${nombre} ${mot}${nombre > 1 ? "s" : ""}`;

/**
 * Le parcours d'une planche de coupes ou de façades (S5) : ni nord, ni locaux, ni ponts. L'échelle suffit, l'agent
 * lit les vues (bouton « Analyser avec Claude Code » des Documents), puis le thermicien confirme les hauteurs
 * dans la fenêtre de la vue, ouverte depuis le plan d'un niveau (D183, D191, D193).
 */
function parcoursDesVues(sheet: Sheet, vues: VueCoupe[]): Etape[] {
  const prete = sheet.status === "prete";
  const facade = sheet.nature === "facade";
  const lues = vues.filter((vue) => vue.nature !== "detail");
  const confirmees = facade
    ? lues.reduce((total, vue) => total + new Set((vue.menuiseries ?? []).map((m) => m.modele ?? m.composant)).size, 0)
    : lues.reduce((total, vue) => total + (vue.corrections?.length ?? 0), 0);
  return [
    {
      id: "planche",
      titre: "Planche à l'échelle",
      // Le nord se pose sur les plans de niveau, pas ici : une élévation dit déjà quelle façade elle montre.
      reste: prete ? "prête" : "à classer et mettre à l'échelle",
      etat: prete ? "fait" : "en_cours",
      panneau: "planche",
      calques: null,
    },
    {
      // D230, D231 : plus de lecture IA ; les vues se tracent à la main sur la planche.
      id: "lecture",
      titre: "Vues",
      reste: lues.length
        ? `${pluriel(lues.length, "vue cadrée")}`
        : prete
          ? "« Ajouter une vue » : deux clics sur la planche"
          : "après la planche",
      etat: lues.length ? "fait" : prete ? "en_cours" : "attente",
      panneau: "planche",
      calques: null,
    },
    {
      id: "hauteurs",
      titre: facade ? "Hauteur des menuiseries" : "Hauteurs des locaux",
      reste: !lues.length
        ? "après la lecture"
        : confirmees
          ? `${pluriel(confirmees, facade ? "menuiserie mesurée" : "étage confirmé")}`
          : "depuis le plan d'un niveau : « Coupes et élévations »",
      etat: !lues.length ? "attente" : confirmees ? "fait" : "en_cours",
      panneau: "planche",
      calques: null,
    },
  ];
}

/** Un local qui doit avoir une hauteur pour être validé (D213) : tout sauf un espace extérieur. */
export function demandeUneHauteur(room: StudyRoom): boolean {
  return room.nature !== "exterieur";
}

/** La hauteur connue d'un local : lue dans les coupes, mesurée ou saisie. */
export function hauteurConnue(room: StudyRoom, hauteurs?: HauteursDuPlan): number | null {
  return hauteurs?.locaux[room.id]?.hauteur_m ?? room.hauteur_m ?? null;
}

/** Les locaux du niveau à qui il manque une hauteur (D213, D215). */
export function locauxSansHauteur(content: StudyContent, hauteurs?: HauteursDuPlan): StudyRoom[] {
  return content.locaux.filter((room) => demandeUneHauteur(room) && hauteurConnue(room, hauteurs) === null);
}

export function parcours(
  sheet: Sheet | null,
  study: Study | undefined,
  vues: VueCoupe[] = [],
  hauteurs?: HauteursDuPlan,
): Etape[] {
  if (sheet && (sheet.nature === "coupe" || sheet.nature === "facade")) {
    return parcoursDesVues(sheet, vues.filter((vue) => vue.sheet_id === sheet.id));
  }
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
      { id: "locaux", titre: "Locaux et hauteur", reste: "après l'analyse", etat: "attente", panneau: "fiche", calques: null },
      { id: "enveloppe", titre: "Parois", reste: "après l'analyse", etat: "attente", panneau: "fiche", calques: null },
      { id: "menuiseries", titre: "Menuiseries", reste: "après l'analyse", etat: "attente", panneau: "fiche", calques: null },
      { id: "ponts", titre: "Ponts thermiques", reste: "après l'analyse", etat: "attente", panneau: "fiche", calques: null },
    ];
  }

  const locaux = content.locaux.length;
  const valides = study ? validatedRoomCount(study) : 0;
  const sansHauteur = locauxSansHauteur(content, hauteurs).length;
  const parois = avancement(paroisDuNiveau(content).filter((element) => element.type !== "menuiserie"));
  const menuiseries = avancementMenuiseries(content);
  // Les ponts se jugent un par un, sans exception : voir `avancement`.
  const ponts = avancement(pontsDuNiveau(content), true);

  etapes.push(
    {
      id: "locaux",
      titre: "Locaux et hauteur",
      reste:
        (valides >= locaux ? `${locaux} validés` : `${valides} sur ${locaux} validés`) +
        (sansHauteur > 0 ? ` · ${pluriel(sansHauteur, "hauteur")} à mesurer` : ""),
      etat: valides >= locaux && sansHauteur === 0 ? "fait" : "en_cours",
      panneau: "fiche",
      // Les contours seuls : à cette étape on juge des pièces, pas de la maçonnerie.
      calques: TOUT_ETEINT,
    },
    {
      id: "enveloppe",
      titre: "Parois",
      reste:
        parois.restants === 0
          ? `${parois.total} relevées${parois.ecartes > 0 ? `, ${pluriel(parois.ecartes, "écartée")}` : ""}`
          : `${pluriel(parois.restants, "paroi")} à vérifier`,
      etat: parois.restants === 0 ? "fait" : "en_cours",
      panneau: "fiche",
      calques: { metres: true, ponts: false, elements: true, toutesCotes: false },
    },
    {
      // D227 : les menuiseries ont leur étape, où rien d'autre ne se dessine ni ne s'attrape.
      id: "menuiseries",
      titre: "Menuiseries",
      reste:
        menuiseries.total === 0
          ? "aucune menuiserie relevée"
          : menuiseries.sansModele === 0
            ? `${pluriel(menuiseries.total, "menuiserie")}, toutes avec un modèle`
            : `${pluriel(menuiseries.sansModele, "menuiserie")} sans modèle sur ${menuiseries.total}`,
      etat: menuiseries.sansModele === 0 ? "fait" : "en_cours",
      panneau: "fiche",
      calques: { metres: false, ponts: false, elements: true, toutesCotes: false },
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
  );
  return etapes;
}

/**
 * Ce que l'étape montre et laisse attraper (retour d'usage du 2026-09-28, D155) : « quand je suis dans une
 * étape, je ne dois voir que les objets concernés par la catégorie et les actions prévues à cet effet ».
 *
 * Les calques (`calques`) règlent ce qui s'étend au reste du niveau ; ceci borne ce qui existe **du tout**
 * à l'étape, y compris pour le local ouvert — qui, sinon, montrait toujours tout (D83).
 */
export type VueEtape = {
  /** Familles dessinées sur le plan. */
  cotes: boolean;
  elements: boolean;
  ponts: boolean;
  /** Ce qu'un clic sur le plan attrape : `tout` garde l'aiguillage complet d'avant. */
  clic: "tout" | "locaux" | "elements" | "ponts";
  /** Fiche du local (nature, côtés, validation, édition du contour). */
  ficheLocal: boolean;
  /** Liste des éléments d'enveloppe du local, et laquelle. */
  listeElements: "aucune" | "parois" | "menuiseries" | "toutes";
  /** Les locaux s'estompent : on regarde le plan dessous, pas le zonage. */
  locauxDiscrets: boolean;
  /** D227 : la famille d'éléments mise en avant et seule attrapable ; les autres s'estompent. */
  famille?: "parois" | "menuiseries";
};

export function vueDeLEtape(etape: EtapeId): VueEtape {
  switch (etape) {
    case "locaux":
      return { cotes: true, elements: false, ponts: false, clic: "locaux", ficheLocal: true, listeElements: "aucune", locauxDiscrets: false };
    case "enveloppe":
      return { cotes: true, elements: true, ponts: false, clic: "elements", ficheLocal: false, listeElements: "parois", locauxDiscrets: true, famille: "parois" };
    case "menuiseries":
      return { cotes: false, elements: true, ponts: false, clic: "elements", ficheLocal: false, listeElements: "menuiseries", locauxDiscrets: true, famille: "menuiseries" };
    case "ponts":
      return { cotes: false, elements: false, ponts: true, clic: "ponts", ficheLocal: false, listeElements: "aucune", locauxDiscrets: true };
    default:
      return { cotes: true, elements: true, ponts: true, clic: "tout", ficheLocal: true, listeElements: "toutes", locauxDiscrets: false };
  }
}

/**
 * L'étape où l'on se trouve quand rien n'est demandé : la première qui n'est pas finie.
 *
 * Le parcours n'interdit rien (D109) : c'est une proposition d'entrée, pas un verrou. Tout étant fini,
 * on reste sur les ponts, dernière étape réellement travaillable.
 */
export function etapeCourante(etapes: Etape[]): EtapeId {
  return (
    etapes.find((etape) => etape.etat === "en_cours") ??
    etapes.find((etape) => etape.id === "ponts") ??
    etapes[etapes.length - 2]
  ).id;
}
