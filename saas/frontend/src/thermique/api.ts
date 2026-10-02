const apiBaseUrl = (import.meta as ImportMeta & { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? "/api";

export type SheetNature = "plan" | "coupe" | "facade" | "plan_masse" | "autre";
export type SheetStatus = "a_classer" | "a_mettre_a_l_echelle" | "prete";
export type PdfPoint = [number, number];

/** Flèche du nord tracée sur la planche, en points PDF : `p2` est la pointe, du côté du nord. */
export type SheetNorth = {
  p1: PdfPoint;
  p2: PdfPoint;
  longueur_pt: number;
};

export type SheetCalibration = {
  p1: PdfPoint;
  p2: PdfPoint;
  length_pt: number;
  real_length_m: number;
  denominator_from_cote: number;
  // Échelle usuelle à moins de 1 % de celle déduite de la cote (ex. 99,97 → 100), sinon null.
  standard_scale: number | null;
  /** Précision de la cote en % (1 pt de clic sur la longueur cliquée, D203). */
  precision_pct?: number | null;
  measured_m: number | null;
  ecart_pct: number | null;
};

export type Sheet = {
  id: number;
  project_id: number;
  document_id: number;
  page_index: number;
  label: string;
  nature: SheetNature | null;
  nature_suggested: SheetNature | null;
  level_label: string | null;
  scale_denominator: number | null;
  scale_source: "declaree" | "cote" | null;
  rotation_deg: number;
  page_width_pt: number;
  page_height_pt: number;
  status: SheetStatus;
  calibration: SheetCalibration | null;
  nord: SheetNorth | null;
  /** Calage sur la planche de référence (S2, D173) : similitude de ses points PDF vers ceux de la référence. */
  calage?: SheetCalage | null;
};

export type SheetCalage = {
  a: number;
  b: number;
  tx: number;
  ty: number;
  reference_sheet_id: number;
  cible_sheet_id: number;
  points: PdfPoint[];
  points_cible: PdfPoint[];
  /** Écart entre le rapport d'échelle trouvé et celui des échelles déclarées, en %. */
  ecart_echelle_pct: number | null;
};

export type ThermiqueDocument = {
  id: number;
  project_id: number;
  original_filename: string;
  file_format: string;
  size_bytes: number;
  page_count: number;
  created_at: string;
  sheets: Sheet[];
};

export type Project = {
  id: number;
  owner_user_id: number;
  name: string;
  description: string | null;
  reference_sheet_id: number | null;
  created_at: string;
  updated_at: string;
  document_count: number;
  sheet_count: number;
  sheets_ready: number;
};

export type ProjectDetail = Project & { documents: ThermiqueDocument[] };

export type StudyLocalNature = "chauffe" | "circulation" | "non_chauffe" | "gaine_technique" | "exterieur";
/** Nature d'un côté de local : sur l'enveloppe, le long d'une paroi lue, ou limite d'usage (D59). */
export type StudyLimit = "exterieur" | "paroi" | "convention";
export type StudyLocalState = { status: "a_verifier" | "valide" | "a_revoir"; motif: string | null };
export type StudyEnvelopeItem = {
  composant?: string;
  type?: string;
  composition?: string;
  lineaire_m?: number;
  largeurs_cm?: number[];
};
export type StudySide = {
  adjacence: string;
  voisin?: string;
  longueur_m: number;
  epaisseur_cm?: number | null;
  orientation?: string;
  deperditif: boolean;
  /** Côté d'un local chauffé contre un espace extérieur à plancher : liaison linéique créée d'office (D161). */
  liaison_exterieur?: boolean;
  /** Polyligne du côté : un côté est un regroupement de sondages, sa position ne se déduit pas
   *  du contour. Sans elle, aucune cote ne peut être posée sur le plan (D80). */
  trace?: PdfPoint[];
  trace_pdf?: PdfPoint[];
  enveloppe?: StudyEnvelopeItem[];
};
/** Un élément d'enveloppe relevé, tel qu'il se dessine sur le plan (mur, isolant, doublage, menuiserie…). */
export type StudyEnvelopeShape = {
  id: string;
  category: string;
  subtype: string;
  geometry_type: "polygon" | "polyline";
  confidence?: number;
  review_required?: boolean;
  points_pdf?: PdfPoint[];
  source_parcours?: { troncon?: string; debut_m?: number; fin_m?: number; piece?: string | null; composant?: string | null };
};
/** La ligne de métré d'un mur (D242) : sa face intérieure, sa longueur et son épaisseur. */
export type LigneMetre = {
  points_pdf?: PdfPoint[];
  source_parcours: { troncon: string; debut_m: number; fin_m: number; piece?: string | null; composant?: string | null };
  composant: string;
  epaisseur_cm: number;
  epaisseur_fin_cm: number;
  longueur_m: number;
};
/**
 * Un élément tel qu'il a été relevé sur l'enveloppe. C'est **la** donnée qui fait foi : les formes
 * dessinées en sont régénérées à chaque recalcul, donc toute correction s'écrit ici (D99).
 */
export type StudyReleveElement = {
  troncon: string;
  debut_m: number;
  fin_m: number;
  type: string;
  composant: string | null;
  nu_exterieur_cm: number;
  nu_interieur_cm: number;
  nu_exterieur_fin_cm?: number;
  nu_interieur_fin_cm?: number;
  confiance?: number;
  /** Ce que l'agent a cru voir : la phrase qui justifie sa lecture. */
  indice?: string;
  a_verifier?: boolean;
  confirme?: boolean;
  corrige?: boolean;
  exclu?: boolean;
  motif_exclusion?: string;
  /** Valeurs lues par l'agent, gardées à côté de la correction humaine (Q7). */
  releve_origine?: Record<string, unknown>;
  /** Pont type NF EN ISO 14683 retenu par le thermicien, ou `a_modeliser` (D158). */
  reference_pont?: string;
  /** Pont ou mur posé par le thermicien, et non lu par l'agent (D157, D250). */
  ajoute?: boolean;
  /** Mur dessiné ou retouché à la main (D249, D250) : jamais réuni d'office avec un voisin. */
  geometrie_manuelle?: boolean;
  /** Angle saisi par le thermicien ; sans lui, c'est la mesure du tracé qui vaut (D160). */
  angle_deg?: number;
  /** Autres pièces qui partagent cette menuiserie, à parts égales (D217). */
  pieces_en_plus?: string[];
  /** Modèle de menuiserie posé par le thermicien (D220). */
  modele?: string | null;
  /** Genre de menuiserie lu par l'IA (fenêtre, porte, mur-rideau…). */
  menuiserie_type?: string;
  /** Exposition de la menuiserie selon le nord posé (D225) : secteur et azimut en degrés. */
  exposition?: string;
  azimut_deg?: number | null;
  /** Morceaux relevés par l'IA, réunis en cette menuiserie (D223). */
  morceaux_reunis?: StudyElementRef[];
  /** Composition de la paroi (couches, du nu extérieur vers l'intérieur). */
  couches?: StudyCouche[];
  /** Paroi retracée par le thermicien (D240). */
  retrace?: boolean;
};
/** Un pont type du tableau C.2 de la NF EN ISO 14683 (D158). */
export type PontType = {
  code: string;
  famille: string;
  page_pdf: number;
  psi_e: number;
  psi_oi: number;
  psi_i: number;
  angle?: "sortant" | "rentrant";
  isolant?: string;
  plancher?: string;
  croquis?: string;
};
export type PontsCatalogue = {
  source: { norme: string; edition: string; tableau: string };
  emplacement_isolant: Record<string, string>;
  familles: Record<string, { libelle: string; correspond_a: string[] }>;
  ponts: PontType[];
};
/** Un pont thermique relevé, avec sa position sur la feuille. */
export type StudyBridge = {
  type: string;
  troncon: string;
  abscisse_m?: number;
  longueur_m?: number;
  piece: string | null;
  composant?: string | null;
  point_pdf?: PdfPoint;
  /** État repris du relevé : une liaison écartée reste dessinée, en grisé (D113). */
  exclu?: boolean;
  a_verifier?: boolean;
  confirme?: boolean;
  /** Posé par le thermicien (D157). */
  ajoute?: boolean;
  /** Remarque E (D160) : changement de direction lu sur le tracé, `null` s'il ne se lit pas. */
  angle_mesure_deg?: number | null;
  /** Angle retenu : celui saisi par le thermicien, sinon la mesure. */
  angle_deg?: number | null;
  angle_saisi?: boolean;
  /** Minoration proportionnelle de ψ : angle / 90 (1 sans angle connu). */
  coefficient_angle?: number;
  reference_pont?: string | null;
};
/** Composition d'une paroi : couches de l'extérieur vers l'intérieur. */
export type CompositionParoi = { composant: string | null; couches: StudyCouche[]; epaisseur_cm: number };
/**
 * Une paroi d'un local (option C, D260) : une portion droite de son contour, face intérieure. Elle porte la
 * composition validée par le thermicien, ou la proposition tirée du relevé de l'IA.
 */
export type StudyParoiLocal = {
  rang: number;
  adjacence: string;
  voisin?: string | null;
  deperditif: boolean;
  longueur_m: number;
  epaisseur_cm: number;
  orientation?: string;
  trace: [number, number][];
  trace_pdf?: PdfPoint[];
  proposition: CompositionParoi | null;
  composition: (CompositionParoi & { id: string }) | null;
  /** Devant une menuiserie relevée, sans mur : la paroi est vitrée et se traite à l'étape Menuiseries. */
  vitree?: boolean;
  /** D267 : les menuiseries du relevé posées sur cette paroi. */
  menuiseries?: MenuiseriePosee[];
};
/** Une menuiserie posée sur une paroi de local (D267) : sa portion le long de la paroi. */
export type MenuiseriePosee = {
  ref: StudyElementRef;
  composant: string | null;
  modele: string | null;
  menuiserie_type: string | null;
  largeur_m: number;
  /** Position le long de la paroi, depuis le début de sa ligne (m). */
  debut_m: number;
  fin_m: number;
  trace: [number, number][];
  trace_pdf?: PdfPoint[];
};
export type StudyRoomSheet = {
  piece: string;
  local: StudyLocalNature;
  surface_m2: number;
  perimetre_m: number;
  cotes: StudySide[];
  /** D260 : les parois du local, une par arête du contour et par nature de ce qu'il y a derrière. */
  parois?: StudyParoiLocal[];
  deperditif_m?: number;
  /** Longueur des côtés contre un espace extérieur à plancher (terrasse, balcon…) : liaison linéique (D161). */
  liaison_exterieur_m?: number;
  par_adjacence?: Record<string, number>;
  baies?: StudyEnvelopeItem[];
  ponts?: Record<string, number>;
  liaison_plancher_m?: number;
  a_completer?: string[];
  alertes?: string[];
};
/** D'où vient la hauteur d'un local (D178 à D180). */
export type HauteurSource = "saisie" | "lue" | "moyenne" | "deduite" | "double_hauteur" | "absente";

export type LocalHauteur = {
  hauteur_m: number | null;
  proposee_m: number | null;
  source: HauteurSource;
  lectures: { vue: string; hsp_m: number; longueur_m: number }[];
  alerte: string | null;
};

export type HauteursDuPlan = {
  sheet_id: number;
  locaux: Record<string, LocalHauteur>;
  coupes: { trait: string; deduit: boolean; vue_id: number; vue: string; vue_sheet_id: number; alertes: string[] }[];
  traits_sans_vue: string[];
  coupes_non_situees?: string[];
  traits: { nom: string; points: PdfPoint[]; sens: [number, number]; deduit?: boolean; vue_id?: number; manuel?: boolean }[];
};

/** D'où vient la hauteur d'une baie (S5e, D196, D200). */
export type BaieSource = "modele" | "baie" | "composant" | "hauteur_du_local" | "a_lire";

/** Un modèle de menuiserie mesuré en coupe ou en élévation, posé sur les menuiseries du plan (D219 à D222). */
export type ModeleMenuiserie = {
  nom: string;
  largeur_cm: number;
  hauteur_m: number;
  vue_id: number;
  vue: string;
  capture: boolean;
  horodatage: string | null;
  /** Nombre de baies du projet posées sur ce modèle. */
  poses: number;
};

export type Baie = {
  composant: string;
  /** Modèle posé par le thermicien (D220) : il fait foi pour la largeur et la hauteur (D221). */
  modele?: string | null;
  /** Largeur relevée sur le plan. */
  largeur_cm: number;
  /** Largeur retenue : celle du modèle s'il y en a un, sinon celle du plan (D221). */
  largeur_retenue_cm?: number;
  largeur_modele_cm?: number;
  /** Plan moins modèle, en cm : un grand écart trahit une baie double ou un morceau. */
  ecart_modele_cm?: number | null;
  surface_m2?: number | null;
  mur_rideau: boolean;
  morceau_a_verifier: boolean;
  morceaux: { troncon: string; debut_m: number; fin_m: number }[];
  sheet_id: number;
  niveau: string;
  hauteur_m: number | null;
  source: BaieSource;
  vue_id: number | null;
  vue: string | null;
};

export type MenuiseriesDuProjet = {
  composants: {
    composant: string;
    mur_rideau: boolean;
    baies: Baie[];
    hauteur_m: number | null;
    a_lire: number;
    confirmation: { vue_id: number; vue: string; largeur_mesuree_cm: number | null } | null;
  }[];
  modeles?: ModeleMenuiserie[];
  morceaux_a_verifier: { composant: string; largeur_cm: number; niveau: string }[];
};

/** Une vue lue sur une planche de coupes ou de façades (S5), en points PDF de sa planche. */
export type VueCoupe = {
  id: number;
  sheet_id: number;
  nom: string;
  nature: "coupe" | "facade" | "detail";
  cadre: [number, number, number, number];
  haut: [number, number];
  corrections?: { sol: number; plafond: number; hauteur_m: number }[];
  /** Menuiseries mesurées sur cette vue : hauteurs par composant (D193) ou modèles avec leurs coins (D219, D232). */
  menuiseries?: {
    composant?: string;
    largeur_cm?: number | null;
    hauteur_m: number;
    modele?: string;
    largeur_mesuree_cm?: number;
    coins?: PdfPoint[];
  }[];
  /** Pièces lues dans la vue (vide tant qu'une vue au cadre corrigé n'est pas relue, D205). */
  pieces?: unknown[];
  /** Cadre ou haut corrigé par le thermicien : la vue attend sa relecture (D205). */
  a_relire?: boolean;
  /** Le thermicien a demandé la lecture de cette vue par l'IA (D212). */
  lecture_demandee?: boolean;
  haut_impose?: boolean;
};

export type HautDeVue = "haut" | "bas" | "gauche" | "droite";

/** Ce que le thermicien corrige d'une vue (D205, D206) ; le haut est exprimé dans la page PDF. */
export type CorrectionDeVue = { cadre?: number[]; haut?: HautDeVue; nom?: string; nature?: "coupe" | "facade" };

export type StudyRoom = {
  id: string;
  nom: string;
  nature: StudyLocalNature;
  /** Hauteur sous plafond fini saisie ou validée par le thermicien (S5, D178). */
  hauteur_m?: number | null;
  contour: PdfPoint[];
  contour_pdf: PdfPoint[];
  limites: StudyLimit[];
  surface_m2: number;
  fiche: StudyRoomSheet;
  synthese: Record<string, unknown> & {
    parois?: StudyEnvelopeItem[];
    menuiseries?: StudyEnvelopeItem[];
    ponts?: Record<string, number>;
    sur_non_chauffe_m?: number;
  };
  demandes: { piece: string; objet: string; motif: string }[];
};
export type StudyContent = {
  /** D264 : coupures de parois posées par le thermicien. */
  coupures_parois?: CoupureParoi[];
  format: "thermique.etude_niveau";
  format_version: number;
  niveau: string;
  locaux: StudyRoom[];
  enveloppe: {
    catalogue: unknown[];
    releve_brut: { elements: StudyReleveElement[]; catalogue: unknown[]; observations: string[] };
    /** Tracé reprojeté des éléments relevés, pour les dessiner sur le plan (D75). */
    objets?: StudyEnvelopeShape[];
    /** Une ligne de métré par mur, sa face intérieure, qui porte sa composition (D242). */
    lignes_metre?: LigneMetre[];
    /** Liaisons du relevé avec leur position sur la feuille : les ponts thermiques (D74). */
    liaisons?: StudyBridge[];
    raccords: unknown[];
    controle: Record<string, unknown>;
    demandes: { piece: string; objet: string; motif: string }[];
  };
  couverture: StudyCoverage;
  coherence?: StudyCoherence;
};
/** Rapport de la chaîne sur elle-même : les deux lectures du niveau confrontées (D77). */
export type StudyCoherence = {
  version: number;
  niveau: string | null;
  locaux: number;
  anomalies: number;
  statut: "ok" | "attention";
  controles: {
    code: string;
    titre: string;
    statut: "ok" | "attention";
    resume: string;
    anomalies: { message: string; local?: string | null }[];
  }[];
};
export type StudyCoverage = {
  surface_emprise_m2: number;
  surface_affectee_m2: number;
  surface_non_affectee_m2: number;
  surface_hors_emprise_m2: number;
  chevauchement_m2: number;
  chevauchements: { locaux: string[]; surface_m2: number }[];
  taux_couverture_pct: number;
  zones_non_affectees: PdfPoint[][];
  zones_non_affectees_pdf?: PdfPoint[][];
};
/** Un élément relevé, désigné par sa position sur l'enveloppe : la clé que porte aussi son tracé (F4). */
export type StudyElementRef = { troncon: string; debut_m: number; fin_m: number };
/** Ce que F4 laisse corriger : les trois familles qui changent le calcul (Q1). */
export type StudyElementChanges = Partial<{
  type: string;
  composant: string;
  /** Pont type NF EN ISO 14683 (`C1`, `IW3`…) ou `a_modeliser` (D158). */
  reference_pont: string;
  /** Angle réel d'un angle sortant ou rentrant, en degrés (D160). */
  angle_deg: number;
  nu_exterieur_cm: number;
  nu_interieur_cm: number;
  nu_exterieur_fin_cm: number;
  nu_interieur_fin_cm: number;
  /** Menuiserie partagée avec d'autres pièces (D217). */
  pieces_en_plus: string[];
  /** Modèle de menuiserie posé (D220) ; une chaîne vide le retire. */
  modele: string;
  /** Composition copiée d'une paroi de référence (D239). */
  couches: StudyCouche[];
}>;
export type StudyElementScope = "cet_element" | "partout";
export type StudyOperation =
  | {
      type: "modifier";
      id: string;
      contour_pdf?: PdfPoint[];
      nature?: StudyLocalNature;
      nom?: string;
      hauteur_m?: number;
      retirer_hauteur?: boolean;
    }
  | { type: "couper"; id: string; segment_pdf: PdfPoint[]; noms?: string[] }
  | { type: "fusionner"; ids: string[]; nom?: string }
  | { type: "local_ajouter"; contour_pdf: PdfPoint[]; nature: StudyLocalNature; nom: string }
  | { type: "local_supprimer"; id: string }
  | { type: "element_confirmer"; element: StudyElementRef }
  | { type: "element_corriger"; element: StudyElementRef; changes: StudyElementChanges; portee?: StudyElementScope }
  | { type: "element_ecarter"; element: StudyElementRef; motif: string }
  | { type: "element_reactiver"; element: StudyElementRef }
  /** Un pont que l'agent n'a pas vu, posé là où le thermicien clique (remarque C, D157). */
  | {
      type: "pont_ajouter";
      point_pdf: PdfPoint;
      type_pont: string;
      reference_pont?: string;
      /** Position calculée par l'écran, que le serveur vérifie au lieu de la recalculer (P5, D164). */
      troncon?: string;
      abscisse_m?: number;
    }
  /** Un pan de mur retracé d'un bout à l'autre (abscisses globales au parcours) avec une composition copiée (D240). */
  | { type: "paroi_retracer"; debut_m: number; fin_m: number; modele: CompositionCopiee }
  /** Une extrémité de la ligne de métré d'un mur, déplacée librement sur le plan (D249). */
  | { type: "paroi_extremite"; element: StudyElementRef; extremite: "debut" | "fin"; abscisse_m: number; nu_interieur_cm: number }
  /** Un mur tracé à la main, situé par l'écran sur le tronçon le plus proche (D250). */
  | {
      type: "paroi_creer";
      troncon: string;
      debut_m: number;
      fin_m: number;
      nu_interieur_cm: number;
      nu_interieur_fin_cm: number;
      composant: string | null;
      couches: StudyCouche[];
    }
  /** Un point ajouté sur la ligne d'un mur : deux morceaux qui partagent ce sommet (D247). */
  | { type: "paroi_couper"; element: StudyElementRef; abscisse_m: number }
  /** La composition validée d'une paroi d'un local (option C, D261). */
  | { type: "paroi_composer"; local: string; trace: [number, number][]; composant: string | null; couches: StudyCouche[] }
  /** D264 : une paroi de local coupée à ce point (composition qui change en cours de côté), ou recollée. */
  | { type: "cote_couper"; local: string; point_pdf: PdfPoint }
  | { type: "cote_recoller"; local: string; point_pdf: PdfPoint };
/** Une coupure de paroi posée par le thermicien (D264). */
export type CoupureParoi = { id: string; local: string; point: [number, number]; point_pdf?: PdfPoint };

/** La composition d'une paroi de référence, copiée au pinceau (D239). */
export type CompositionCopiee = {
  composant: string | null;
  couches: StudyCouche[];
  nu_exterieur_cm: number;
  nu_interieur_cm: number;
  /** Repère lisible : composant et épaisseur totale. */
  libelle: string;
};
export type StudyCouche = { nature: string; epaisseur_cm: number; indice?: string; presume?: boolean };
export type StudyPreview = {
  content: StudyContent;
  couverture: StudyCoverage;
  voisins_modifies: string[];
  bloquant: string | null;
};
export type StudyVersion = {
  version_number: number;
  reason: string;
  created_by_user_id: number | null;
  created_at: string;
};
/** Un niveau dans la file d'analyse, que le relais du poste vient prendre (F0). */
export type Work = {
  id: number;
  project_id: number;
  sheet_id: number;
  label: string;
  level_label: string | null;
  /** « niveau » : étude d'un plan ; « traits » : traits de coupe d'un plan ; « coupes » : vues d'une planche (S5). */
  type?: "niveau" | "traits" | "coupes" | "vues";
  statut: "en_attente" | "en_cours" | "fini" | "refuse" | "echec";
  rang: number;
  message: string | null;
  pris_a: string | null;
  fini_a: string | null;
  created_at: string;
};
export type QueueResult = {
  ajoutes: Work[];
  /** Niveaux non mis en file, avec la raison en clair : échelle absente, travail déjà fait… */
  ecartes: { sheet_id: number; label: string; motif: string }[];
};
export type Study = {
  id: number;
  project_id: number;
  sheet_id: number;
  format_version: number;
  version_number: number;
  content: StudyContent;
  local_states: Record<string, StudyLocalState>;
  imported_by_user_id: number | null;
  created_at: string;
  updated_at: string;
};

export type UploadResult = {
  project: ProjectDetail;
  imported: string[];
  errors: { filename: string; message: string }[];
};

export type SheetChanges = Partial<{
  label: string;
  nature: SheetNature | null;
  level_label: string | null;
  rotation_deg: number;
  scale_denominator: number | null;
}>;

export type CalibrationPayload = {
  p1: PdfPoint;
  p2: PdfPoint;
  real_length_m: number;
  apply: boolean;
};

export async function request<T>(token: string, path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers });
  if (!response.ok) {
    let message = `Erreur ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (response.status === 422) {
        // Refus de format côté serveur : « Erreur 422 » seul ne disait rien, et le travail semblait perdu.
        message =
          "Le serveur a refusé le format de la demande (erreur 422). Vos modifications sont toujours dans cet onglet : ne le rechargez pas et signalez le problème.";
      }
    } catch {
      // réponse sans corps JSON : on garde le code HTTP
    }
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const thermiqueApi = {
  listProjects: (token: string) => request<Project[]>(token, "/thermique/projects"),
  createProject: (token: string, payload: { name: string; description?: string }) =>
    request<Project>(token, "/thermique/projects", { method: "POST", body: JSON.stringify(payload) }),
  getProject: (token: string, projectId: number) => request<ProjectDetail>(token, `/thermique/projects/${projectId}`),
  updateProject: (token: string, projectId: number, payload: { name?: string; description?: string | null; reference_sheet_id?: number | null }) =>
    request<Project>(token, `/thermique/projects/${projectId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteProject: (token: string, projectId: number) =>
    request<void>(token, `/thermique/projects/${projectId}`, { method: "DELETE" }),
  eraseAllProjects: (token: string, confirmation: string) =>
    request<{ projets_effaces: number }>(token, "/thermique/projects/tout-effacer", {
      method: "POST",
      body: JSON.stringify({ confirmation }),
    }),
  uploadDocuments: (token: string, projectId: number, files: File[]) => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    return request<UploadResult>(token, `/thermique/projects/${projectId}/documents`, { method: "POST", body: form });
  },
  deleteDocument: (token: string, documentId: number) =>
    request<void>(token, `/thermique/documents/${documentId}`, { method: "DELETE" }),
  updateSheet: (token: string, sheetId: number, changes: SheetChanges) =>
    request<Sheet>(token, `/thermique/sheets/${sheetId}`, { method: "PATCH", body: JSON.stringify(changes) }),
  calibrateSheet: (token: string, sheetId: number, payload: CalibrationPayload) =>
    request<Sheet>(token, `/thermique/sheets/${sheetId}/calibration`, { method: "POST", body: JSON.stringify(payload) }),
  /** Pose le nord : p1 la base de la flèche, p2 sa pointe du côté du nord. Renvoie les planches modifiées. */
  setNorth: (token: string, sheetId: number, payload: { p1: PdfPoint; p2: PdfPoint; tout_le_projet: boolean }) =>
    request<Sheet[]>(token, `/thermique/sheets/${sheetId}/nord`, { method: "POST", body: JSON.stringify(payload) }),
  /** Cale la planche sur la référence par deux points communs avec une planche déjà calée (S2, D173). */
  calerPlanche: (
    token: string,
    sheetId: number,
    payload: { cible_sheet_id: number; points: PdfPoint[]; points_cible: PdfPoint[] },
  ) => request<Sheet>(token, `/thermique/sheets/${sheetId}/calage`, { method: "POST", body: JSON.stringify(payload) }),
  getStudy: (token: string, sheetId: number) => request<Study | null>(token, `/thermique/sheets/${sheetId}/etude`),
  getPontsCatalogue: (token: string) => request<PontsCatalogue>(token, "/thermique/ponts/catalogue"),
  getHauteurs: (token: string, sheetId: number) => request<HauteursDuPlan>(token, `/thermique/sheets/${sheetId}/hauteurs`),
  getVues: (token: string, projectId: number) => request<VueCoupe[]>(token, `/thermique/projects/${projectId}/vues`),
  confirmerHauteur: (token: string, vueId: number, sol: PdfPoint, plafond: PdfPoint) =>
    request<VueCoupe>(token, `/thermique/vues/${vueId}/hauteur`, { method: "POST", body: JSON.stringify({ sol, plafond }) }),
  getMenuiseries: (token: string, projectId: number) =>
    request<MenuiseriesDuProjet>(token, `/thermique/projects/${projectId}/menuiseries`),
  // Modèle de menuiserie mesuré, nommé et capturé (D219, D222).
  enregistrerModele: (token: string, vueId: number, coins: PdfPoint[], nom: string) =>
    request<{ modele: string; largeur_mesuree_cm: number; hauteur_m: number; capture: string | null }>(
      token,
      `/thermique/vues/${vueId}/modeles`,
      { method: "POST", body: JSON.stringify({ coins, nom }) },
    ),
  retirerModele: (token: string, projectId: number, nom: string) =>
    request<unknown>(token, `/thermique/projects/${projectId}/modeles?nom=${encodeURIComponent(nom)}`, { method: "DELETE" }),
  captureDuModele: async (token: string, projectId: number, nom: string): Promise<Blob> => {
    const reponse = await fetch(`${apiBaseUrl}/thermique/projects/${projectId}/modeles/capture?nom=${encodeURIComponent(nom)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!reponse.ok) throw new Error("Capture introuvable.");
    return reponse.blob();
  },
  confirmerMenuiserie: (token: string, vueId: number, coins: PdfPoint[], composant: string, largeurCm: number | null) =>
    request<{ hauteur_m: number; largeur_mesuree_cm: number }>(token, `/thermique/vues/${vueId}/menuiseries`, {
      method: "POST",
      body: JSON.stringify({ coins, composant, largeur_cm: largeurCm }),
    }),
  retirerHauteurs: (token: string, vueId: number) =>
    request<VueCoupe>(token, `/thermique/vues/${vueId}/hauteur`, { method: "DELETE" }),
  // Cadre redessiné ou haut donné d'une vue mal située par l'agent ; une coupe repart en relecture (D205).
  corrigerVue: (token: string, vueId: number, correction: CorrectionDeVue) =>
    request<VueCoupe>(token, `/thermique/vues/${vueId}`, { method: "PATCH", body: JSON.stringify(correction) }),
  supprimerVue: (token: string, vueId: number) =>
    request<void>(token, `/thermique/vues/${vueId}`, { method: "DELETE" }),
  // Vue tracée à la main sur une planche de coupes ou d'élévations (D231) ; le haut est un côté de la page.
  creerVue: (token: string, sheetId: number, vue: { nom: string; nature: "coupe" | "facade"; cadre: number[]; haut: HautDeVue }) =>
    request<VueCoupe>(token, `/thermique/sheets/${sheetId}/vues`, { method: "POST", body: JSON.stringify(vue) }),
  // « Faire lire par l'IA » une coupe cadrée et orientée (D212).
  faireLireVue: (token: string, vueId: number) => request<VueCoupe>(token, `/thermique/vues/${vueId}/lire`, { method: "POST" }),
  // Trait d'une coupe tracé à la main sur le plan (D209).
  tracerTraitDeCoupe: (token: string, planId: number, trait: { vue_id: number; points: PdfPoint[]; sens: [number, number] }) =>
    request<unknown>(token, `/thermique/sheets/${planId}/traits-coupe`, { method: "POST", body: JSON.stringify(trait) }),
  // Lecture d'une planche de coupes ou de façades produite sur le poste (`lecture.json`, D204).
  importerLecture: (token: string, sheetId: number, lecture: unknown) =>
    request<{ vues?: number; traits?: number }>(token, `/thermique/sheets/${sheetId}/lecture/importer`, {
      method: "POST",
      body: JSON.stringify(lecture),
    }),
  importStudy: (token: string, sheetId: number, file: File, replace = false) => {
    const form = new FormData();
    form.append("fichier", file);
    return request<Study>(token, `/thermique/sheets/${sheetId}/etude/importer?remplacer=${replace}`, {
      method: "POST",
      body: form,
    });
  },
  remodelStudy: (token: string, sheetId: number, operations: StudyOperation[], localId?: string | null) =>
    request<StudyPreview>(
      token,
      `/thermique/sheets/${sheetId}/etude/remodeliser${localId ? `?local_id=${encodeURIComponent(localId)}` : ""}`,
      { method: "POST", body: JSON.stringify({ operations }) },
    ),
  saveStudy: (
    token: string,
    sheetId: number,
    payload: { operations: StudyOperation[]; local_id?: string | null; motif?: string; valider?: boolean },
  ) => request<Study>(token, `/thermique/sheets/${sheetId}/etude/enregistrer`, { method: "POST", body: JSON.stringify(payload) }),
  validateStudyRoom: (token: string, sheetId: number, localId: string) =>
    request<Study>(token, `/thermique/sheets/${sheetId}/etude/locaux/${encodeURIComponent(localId)}/valider`, {
      method: "POST",
    }),
  listStudyVersions: (token: string, sheetId: number) =>
    request<StudyVersion[]>(token, `/thermique/sheets/${sheetId}/etude/versions`),
  restoreStudyVersion: (token: string, sheetId: number, numero: number) =>
    request<Study>(token, `/thermique/sheets/${sheetId}/etude/versions/${numero}/restaurer`, { method: "POST" }),
  /** Met en file les niveaux analysables du projet ; le relais du poste videra la file (D93). */
  analyseProject: (token: string, projectId: number) =>
    request<QueueResult>(token, `/thermique/projects/${projectId}/analyser`, { method: "POST" }),
  listWorks: (token: string, projectId: number) =>
    request<Work[]>(token, `/thermique/projects/${projectId}/travaux`),
  documentFileUrl: (documentId: number) => `${apiBaseUrl}/thermique/documents/${documentId}/file`,
  // Fiche des tuiles d'une planche (rendue par le serveur à la première demande).
  getRaster: (token: string, sheetId: number, rotation: number) =>
    request<import("./raster").RasterManifest>(token, `/thermique/sheets/${sheetId}/raster?rotation=${rotation}`),
  apiUrl: (path: string) => `${apiBaseUrl}${path}`,
};
