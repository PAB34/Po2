import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type CorrectionDeVue, type HautDeVue, type PdfPoint, type StudyElementRef, type ProjectDetail, type Sheet, type Study, type VueCoupe } from "../api";
import { TileSheetViewer, type PickEvent, type ViewerTool, type ViewerView } from "../components/TileSheetViewer";
import { STATUS_LABELS } from "../natures";
import { allSheets, projectQueryKey, projectsQueryKey } from "../projectCache";
import { DocumentsPanel } from "./DocumentsPanel";
import { InfoPanel } from "./InfoPanel";
import { groupSheets, referenceSheet, sheetTitle } from "./levels";
import { LibraryPanel } from "./LibraryPanel";
import { SheetPanel, sheetSegments } from "./SheetPanel";
import { NorthOverlay } from "./NorthOverlay";
import { PlanMenu, type PlanAction } from "./PlanMenu";
import { METRICS_DEFAUT, StudyMetrics, type MetricsShow } from "./StudyMetrics";
import { StudyCoherenceReport, StudyCoverageBanner, StudyOverlay, StudyRoomCreationPanel, StudyRoomList, StudyRoomPanel } from "./StudyPanel";
import { ElementPanel, IndeterminesDuNiveau, MOTIF_INDETERMINE_SUPPRIME, MOTIF_MUR_SUPPRIME } from "./ElementPanel";
import { FenetreCoupe, type OutilDeMesure } from "./FenetreCoupe";
import { menuiseriesQueryKey } from "./baies";
import { PontsPanel } from "./PontsPanel";
import { coteAt, empreinteCote, milieuCote, rangVise, type CoteVisee } from "./cotes";
import { elementDuPont, paroisATrancher, pontAt, pontDeElement, refDeElement, trouverElement, viserSurLePlan } from "./elements";
import { baieDeLElement, cleDeRef, cotesDesMenuiseries, menuiseriesDeMemeLargeur } from "./modeles";
import { formesDesLignes, formesEtapeParois } from "./parois";
import { BibliothequeModeles, CotesMenuiseries } from "./ModelesMenuiseries";
import { demandeUneHauteur, etapeCourante, hauteurConnue, locauxSansHauteur, parcours, vueDeLEtape, type EtapeId } from "./parcours";
import { TYPES_PONT_REATTRIBUABLES } from "./pontsTypes";
import {
  cliquer as cliquerAlignement,
  debuterAlignement,
  garderLaRotation,
  pairesAEnregistrer,
  refaireEtape,
  type Alignement,
} from "./alignement";
import { GuideCalage } from "./GuideCalage";
import { CadresDesVues, ListeDesVues, NOUVELLE_VUE, cadreDeDeuxCoins, type CadreEnCours } from "./CadresDesVues";
import { NiveauFantome, PointsDeCalage } from "./NiveauFantome";
import { appliquer, calageAEnregistrer, correspondance, inverser, niveauxVoisins } from "./superposition";
import { useStudyEdition } from "./useStudyEdition";
import { useStudyElements } from "./useStudyElements";
import {
  boutLePlusProche,
  extremitesDuMur,
  extremitesPartagees,
  gesteCoupe,
  gesteCreation,
  gesteExtremite,
  longueurEntre,
  longueurSurLePlan,
  type Extremite,
  type GesteExtremite,
} from "./murs";
import { PoigneesDuMur, TraceDuMur } from "./PoigneesDuMur";
import { FicheParoi, ListeParoisDuLocal, ParoisDesLocaux } from "./ParoisDesLocaux";
import { gesteComposition, paroiVisee, trouverParoi, type ParoiRef } from "./paroisLocaux";
import { cibleEditable } from "./elementsHistory";
import { peutAnnulerEditionAvecEchap } from "./edition";
import { hauteursQueryKey, NATURE_LABELS, otherLocalNatures, roomAt, sortedStudyRooms, studyQueryKey } from "./study";

type Panel = "planche" | "fiche" | "documents" | "bibliotheque" | "infos";

const PANELS: { id: Panel; label: string }[] = [
  { id: "planche", label: "Planche" },
  { id: "fiche", label: "Fiche" },
  { id: "documents", label: "Documents" },
  { id: "bibliotheque", label: "Bibliothèque" },
  { id: "infos", label: "Infos" },
];

// Les adresses de tuiles signées valent 12 h : on redemande la fiche avant.
const RASTER_STALE_MS = 6 * 3600 * 1000;

// Ancienne persistance locale du plan de référence : E2 la migre une fois vers le projet côté serveur.
const referenceKey = (projectId: number) => `thermique.reference.${projectId}`;

function readReference(projectId: number): number | null {
  try {
    const value = window.localStorage.getItem(referenceKey(projectId));
    return value ? Number(value) : null;
  } catch {
    return null;
  }
}

function writeReference(projectId: number, sheetId: number) {
  try {
    window.localStorage.setItem(referenceKey(projectId), String(sheetId));
  } catch {
    // stockage indisponible : le choix vaut pour la session en cours
  }
}

function removeReference(projectId: number) {
  try {
    window.localStorage.removeItem(referenceKey(projectId));
  } catch {
    // stockage indisponible
  }
}

// Affichage des métrés : mémorisé par planche, pour ne pas le reposer à chaque local (Q6).
const metricsKey = (sheetId: number) => `thermique.metres.${sheetId}`;
// Rayon de saisie d'un élément d'enveloppe, en pixels d'écran : un trait fin doit rester attrapable.
const PRISE_ELEMENT_PX = 6;
const PRISE_ELEMENT_PAROIS_PX = 10;
// La pastille d'un pont fait 5 px de rayon : on vise un peu plus large pour l'attraper sans peine.
const PRISE_PONT_PX = 8;
// D249 : prise d'une poignée de mur et portée de l'aimant, en pixels écran.
const PRISE_POIGNEE_PX = 12;
const AIMANT_POIGNEE_PX = 14;
// Deux bouts de murs à moins de ce nombre de pixels forment un sommet partagé, qui se glisse d'un seul geste.
const SOMMET_PARTAGE_PX = 1.5;
// Option C (D262) : les gestes sur les murs du relevé (créer, ajouter un point, indéterminés) sont retirés de
// l'écran ; l'étape Parois compose les parois des locaux. Leur code sera retiré avec le nettoyage (objectif 2b).
const GESTES_MURS_DU_RELEVE = false;
// À l'étape des ponts, rien d'autre n'est attrapable : on vise large (D156).
const PRISE_PONT_ETAPE_PX = 18;
// Serrage du plan sur le pont en cours, en multiple du cadrage ajusté : de quoi voir le coin et ses
// voisins, sans perdre le bâtiment de vue (Q4).
const ZOOM_PONT = 5;
// Un côté se lit sur toute sa longueur : on serre moins que sur un pont (D148).
const ZOOM_COTE = 3;
// Un côté se désigne de l'intérieur du local, à cette distance de son tracé (D149).
const PRISE_COTE_PX = 8;

function readMetrics(sheetId: number | null): MetricsShow {
  if (sheetId == null) {
    return METRICS_DEFAUT;
  }
  try {
    const brut = window.localStorage.getItem(metricsKey(sheetId));
    return brut ? { ...METRICS_DEFAUT, ...(JSON.parse(brut) as Partial<MetricsShow>) } : METRICS_DEFAUT;
  } catch {
    return METRICS_DEFAUT;
  }
}

function writeMetrics(sheetId: number, show: MetricsShow) {
  try {
    window.localStorage.setItem(metricsKey(sheetId), JSON.stringify(show));
  } catch {
    // stockage indisponible : le choix vaut pour la session en cours
  }
}

const METRICS_CASES: { cle: keyof MetricsShow; label: string; titre: string }[] = [
  { cle: "metres", label: "Métrés", titre: "Coter tous les locaux du niveau, pas seulement celui sélectionné" },
  { cle: "ponts", label: "Ponts", titre: "Montrer les ponts thermiques de tout le niveau" },
  { cle: "elements", label: "Éléments", titre: "Montrer les éléments d'enveloppe relevés sur tout le niveau" },
  { cle: "toutesCotes", label: "Côtés intérieurs", titre: "Coter aussi les côtés qui ne déperdent pas" },
];

function SheetMenu({ label, sheets, currentId, onPick }: { label: string; sheets: Sheet[]; currentId: number | null; onPick: (id: number) => void }) {
  if (sheets.length === 0) {
    return null;
  }
  const current = sheets.find((sheet) => sheet.id === currentId);
  return (
    <select
      className={current ? "th-ws__menu is-active" : "th-ws__menu"}
      aria-label={label}
      value={current ? current.id : ""}
      onChange={(event) => event.target.value && onPick(Number(event.target.value))}
    >
      <option value="">
        {label} ({sheets.length})
      </option>
      {sheets.map((sheet) => (
        <option key={sheet.id} value={sheet.id}>
          {sheetTitle(sheet)}
        </option>
      ))}
    </select>
  );
}

// Espace de travail du thermicien (D47) : un projet, ses plans, sa bibliothèque et ses infos, sans quitter l'écran.
export function WorkspacePage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const projectId = Number(useParams().projectId);
  const [searchParams, setSearchParams] = useSearchParams();
  const [referenceId, setReferenceId] = useState<number | null>(() => readReference(projectId));
  const [tool, setTool] = useState<ViewerTool>("pan");
  const [points, setPoints] = useState<PdfPoint[]>([]);
  const views = useRef(new Map<string, ViewerView>());
  const referenceMigration = useRef<number | null>(null);
  const [metrics, setMetrics] = useState<MetricsShow>(METRICS_DEFAUT);
  const [menu, setMenu] = useState<{ x: number; y: number; actions: PlanAction[] } | null>(null);
  // D250 : tracé d'un mur en cours (premier point posé, point sous le curseur pour l'aperçu).
  const [traceMur, setTraceMur] = useState<{ premier: PdfPoint | null; survol: PdfPoint | null } | null>(null);
  const [traceMessage, setTraceMessage] = useState<string | null>(null);
  // Option C (D262) : la paroi de local ouverte à l'étape Parois.
  const [paroiChoisie, setParoiChoisie] = useState<ParoiRef | null>(null);
  // Dès que le thermicien touche une case d'affichage, l'étape rend la main : c'est lui qui décide (Q6).
  const [calquesLibres, setCalquesLibres] = useState(false);
  // Niveau qu'on cherche à quitter alors que des corrections attendent (D111) : pas de départ silencieux.
  const [departEnAttente, setDepartEnAttente] = useState<number | null>(null);
  // Le côté désigné, partagé entre la fiche et le plan (sujet 2, D145).
  const [coteVisee, setCoteVisee] = useState<CoteVisee | null>(null);
  const clicsCote = useRef(0);
  // « Valider ce local » : un geste à part depuis que les recadrages se conservent localement (Q7).
  const [validation, setValidation] = useState<{ busy: boolean; message: string | null }>({ busy: false, message: null });
  // Superposition des niveaux (S3, D168, D169) : les deux cases « Voir niveau inférieur / supérieur ».
  const [fantomes, setFantomes] = useState<{ inferieur: boolean; superieur: boolean }>({ inferieur: false, superieur: false });
  // Calage en cours (S2, D173 ; méthode Aligner d'AutoCAD, D201) : voir `alignement.ts`.
  const [calage, setCalage] = useState<Alignement | null>(null);

  const { data: project, error } = useQuery({
    queryKey: projectQueryKey(projectId),
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled: Boolean(token) && Number.isFinite(projectId),
  });
  const { data: projects } = useQuery({
    queryKey: projectsQueryKey,
    queryFn: () => thermiqueApi.listProjects(token!),
    enabled: Boolean(token),
  });

  const sheets = project ? allSheets(project) : [];
  const groups = groupSheets(sheets);
  const reference = referenceSheet(sheets, project?.reference_sheet_id ?? referenceId);
  const requestedId = Number(searchParams.get("planche")) || null;
  const sheet = sheets.find((item) => item.id === requestedId) ?? reference;
  const panel = (PANELS.find((item) => item.id === searchParams.get("panneau"))?.id ?? (sheets.length ? "planche" : "documents")) as Panel;

  const setParams = useCallback(
    (changes: { planche?: number; panneau?: Panel; local?: string | null; etape?: EtapeId }) => {
      const next = new URLSearchParams(searchParams);
      if (changes.planche !== undefined) {
        next.set("planche", String(changes.planche));
      }
      if (changes.panneau !== undefined) {
        next.set("panneau", changes.panneau);
      }
      if (changes.etape !== undefined) {
        next.set("etape", changes.etape);
      }
      if (changes.local !== undefined) {
        if (changes.local === null) next.delete("local");
        else next.set("local", changes.local);
      }
      setSearchParams(next);
    },
    [searchParams, setSearchParams],
  );

  const sheetId = sheet?.id ?? null;
  useEffect(() => {
    setPoints([]);
  }, [sheetId, tool]);

  // Les réglages d'affichage suivent la planche : on reprend ceux qu'elle avait à la dernière visite.
  useEffect(() => {
    setMetrics(readMetrics(sheetId));
  }, [sheetId]);

  const basculerMetrique = useCallback(
    (cle: keyof MetricsShow, depart: MetricsShow) => {
      setCalquesLibres(true);
      setMetrics(() => {
        const suivant = { ...depart, [cle]: !depart[cle] };
        if (sheetId != null) {
          writeMetrics(sheetId, suivant);
        }
        return suivant;
      });
    },
    [sheetId],
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPoints([]);
        setCalage(null);
        setCadreVue(null);
        setHauteurAPoser(null);
        setModeleAPoser(null);
        setTraceMur(null);
        setTraceMessage(null);
        setParoiChoisie(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const rotation = sheet?.rotation_deg ?? 0;
  // Les ponts types NF EN ISO 14683 : un fichier fixe, chargé une fois (D158).
  const pontsCatalogue = useQuery({
    queryKey: ["thermique", "ponts-catalogue"],
    queryFn: () => thermiqueApi.getPontsCatalogue(token!),
    enabled: Boolean(token),
    staleTime: Infinity,
  });
  const raster = useQuery({
    queryKey: ["thermique", "raster", sheetId, rotation],
    queryFn: () => thermiqueApi.getRaster(token!, sheetId!, rotation),
    enabled: Boolean(token && sheetId),
    staleTime: RASTER_STALE_MS,
  });
  const viewKey = `${sheetId}|${rotation}`;
  // Les niveaux voisins et leurs images, chargées seulement quand leur case est cochée (S3).
  const voisins = niveauxVoisins(sheets, sheet ?? null);
  const rasterInferieur = useQuery({
    queryKey: ["thermique", "raster", voisins.inferieur?.id ?? null, voisins.inferieur?.rotation_deg ?? 0],
    queryFn: () => thermiqueApi.getRaster(token!, voisins.inferieur!.id, voisins.inferieur!.rotation_deg),
    enabled: Boolean(token && voisins.inferieur && (fantomes.inferieur || calage?.sens === "inferieur")),
    staleTime: RASTER_STALE_MS,
  });
  const rasterSuperieur = useQuery({
    queryKey: ["thermique", "raster", voisins.superieur?.id ?? null, voisins.superieur?.rotation_deg ?? 0],
    queryFn: () => thermiqueApi.getRaster(token!, voisins.superieur!.id, voisins.superieur!.rotation_deg),
    enabled: Boolean(token && voisins.superieur && (fantomes.superieur || calage?.sens === "superieur")),
    staleTime: RASTER_STALE_MS,
  });
  const referenceProjet = project?.reference_sheet_id ?? null;
  const fantomesAffiches = (["inferieur", "superieur"] as const).flatMap((sens) => {
    const voisin = voisins[sens];
    const image = sens === "inferieur" ? rasterInferieur.data : rasterSuperieur.data;
    if (!voisin || !image || !sheet || !(fantomes[sens] || calage?.sens === sens)) return [];
    const pose = correspondance(voisin, sheet, referenceProjet);
    // Pendant un calage, le calque suit la pose en cours : il bouge après chaque étape (D201).
    return [{ sens, voisin, image, ...pose, ...(calage?.sens === sens ? { sim: calage.sim } : {}) }];
  });
  // Changer de planche abandonne un calage commencé : ses points n'ont de sens que sur ce plan-ci.
  useEffect(() => setCalage(null), [sheetId]);

  const enregistrerCalage = async (al: Alignement) => {
    const voisin = voisins[al.sens];
    const paires = pairesAEnregistrer(al);
    if (!voisin || !sheet || !token || !paires) return;
    const geste = calageAEnregistrer(voisin, sheet, referenceProjet, paires);
    if ("refus" in geste) {
      setCalage({ ...al, message: geste.refus });
      return;
    }
    setCalage({ ...al, busy: true, message: null });
    try {
      await thermiqueApi.calerPlanche(token, geste.planche, {
        cible_sheet_id: geste.cible,
        points: geste.points,
        points_cible: geste.points_cible,
      });
      await queryClient.invalidateQueries({ queryKey: projectQueryKey(projectId) });
      setFantomes((current) => ({ ...current, [al.sens]: true }));
      // Les croix restent jusqu'à la fermeture du bandeau, pour vérifier que tout tombe juste (Q51).
      setCalage({ ...al, etape: "enregistre", busy: false, message: "Calage enregistré." });
    } catch (echec) {
      setCalage({ ...al, busy: false, message: echec instanceof Error ? echec.message : "Le calage a échoué." });
    }
  };

  // Un clic du calage : point de base, puis rotation, comme la commande Aligner d'AutoCAD (D201).
  // Rapport des échelles déclarées du voisin et du plan actif ; à défaut, celle de la pose en cours.
  const echelleDuCalage = (al: Alignement) => {
    const voisin = voisins[al.sens];
    const declaree =
      voisin?.scale_denominator && sheet?.scale_denominator ? voisin.scale_denominator / sheet.scale_denominator : null;
    return declaree ?? Math.hypot(al.depart.a, al.depart.b);
  };
  const cliquerCalage = (point: PdfPoint, libre: boolean) => {
    if (!calage || !sheet) return;
    setCalage(cliquerAlignement(calage, point, echelleDuCalage(calage), libre));
  };

  const studyQuery = useQuery({
    queryKey: studyQueryKey(sheetId),
    queryFn: () => thermiqueApi.getStudy(token!, sheetId!),
    enabled: Boolean(token && sheetId),
  });
  const study = studyQuery.data;
  // Hauteur de chaque local, lue dans les coupes ou saisie (S5, D178 à D189).
  const hauteurs = useQuery({
    queryKey: hauteursQueryKey(sheetId),
    queryFn: () => thermiqueApi.getHauteurs(token!, sheetId!),
    enabled: Boolean(token && sheetId && study),
    retry: false,
  });
  // Les vues de coupe du projet, et celle ouverte dans la fenêtre flottante (D183).
  const vues = useQuery({
    queryKey: ["thermique", "vues", projectId],
    queryFn: () => thermiqueApi.getVues(token!, projectId),
    enabled: Boolean(token && projectId),
  });
  const [coupeOuverte, setCoupeOuverte] = useState<number | null>(null);
  // Baies du projet et leur hauteur lue en élévation (S5e, D199, D200).
  const menuiseries = useQuery({
    queryKey: menuiseriesQueryKey(projectId),
    queryFn: () => thermiqueApi.getMenuiseries(token!, projectId),
    enabled: Boolean(token && projectId),
  });
  // Cadres des vues de cette planche (D205) : montrés, choisis, redessinés en deux clics.
  const vuesDeLaPlanche = (vues.data ?? []).filter((vue) => vue.sheet_id === sheet?.id);
  const [vueChoisie, setVueChoisie] = useState<number | null>(null);
  const [cadreVue, setCadreVue] = useState<CadreEnCours | null>(null);
  const [vuesEtat, setVuesEtat] = useState<{ busy: boolean; message: string | null }>({ busy: false, message: null });
  useEffect(() => setCadreVue(null), [sheetId]);
  const corrigerUneVue = async (vueId: number, correction: CorrectionDeVue) => {
    if (!token) return;
    setVuesEtat({ busy: true, message: null });
    try {
      const vue = await thermiqueApi.corrigerVue(token, vueId, correction);
      await queryClient.invalidateQueries({ queryKey: ["thermique", "vues"] });
      await queryClient.invalidateQueries({ queryKey: ["thermique", "hauteurs"] });
      setVuesEtat({
        busy: false,
        message: `« ${vue.nom} » corrigée.`,
      });
    } catch (echec) {
      setVuesEtat({ busy: false, message: echec instanceof Error ? echec.message : "La correction a échoué." });
    }
  };
  const cliquerCadreVue = (point: PdfPoint) => {
    if (!cadreVue) return;
    if (!cadreVue.premier) {
      setCadreVue({ ...cadreVue, premier: point });
      return;
    }
    const cadre = cadreDeDeuxCoins(cadreVue.premier, point);
    setCadreVue(null);
    // D231 : le cadre d'une vue à créer attend son nom, sa nature et son haut dans la fiche.
    if (cadreVue.vueId === NOUVELLE_VUE) {
      setNouvelleVue(cadre);
      return;
    }
    void corrigerUneVue(cadreVue.vueId, { cadre });
  };
  const [nouvelleVue, setNouvelleVue] = useState<number[] | null>(null);
  useEffect(() => setNouvelleVue(null), [sheetId]);
  const creerUneVue = async (vue: { nom: string; nature: "coupe" | "facade"; cadre: number[]; haut: HautDeVue }) => {
    if (!token || !sheet) return;
    setVuesEtat({ busy: true, message: null });
    try {
      const creee = await thermiqueApi.creerVue(token, sheet.id, vue);
      await queryClient.invalidateQueries({ queryKey: ["thermique", "vues"] });
      setNouvelleVue(null);
      setVueChoisie(creee.id);
      setVuesEtat({ busy: false, message: `« ${creee.nom} » créée : elle s'ouvre depuis le plan d'un niveau, « Coupes et élévations ».` });
    } catch (echec) {
      setVuesEtat({ busy: false, message: echec instanceof Error ? echec.message : "La vue n'a pas été créée." });
    }
  };
  // Hauteur mesurée dans une coupe, posée local par local d'un clic sur le plan (D211).
  const [hauteurAPoser, setHauteurAPoser] = useState<{ valeur: number; poses: string[] } | null>(null);
  useEffect(() => setHauteurAPoser(null), [sheetId]);
  const fileHauteurs = useRef<Promise<void>>(Promise.resolve());
  const supprimerUneVue = async (vue: VueCoupe) => {
    if (!token || !window.confirm(`Supprimer la vue « ${vue.nom} » de cette planche ?`)) return;
    setVuesEtat({ busy: true, message: null });
    try {
      await thermiqueApi.supprimerVue(token, vue.id);
      await queryClient.invalidateQueries({ queryKey: ["thermique", "vues"] });
      await queryClient.invalidateQueries({ queryKey: ["thermique", "hauteurs"] });
      setVuesEtat({ busy: false, message: `« ${vue.nom} » supprimée.` });
    } catch (echec) {
      setVuesEtat({ busy: false, message: echec instanceof Error ? echec.message : "La suppression a échoué." });
    }
  };
  // Fenêtre « Coupes et élévations » (D214) : on y choisit la vue, sans trait sur le plan (D216). Elle
  // garde la dernière vue choisie ; ouverte depuis une fiche, elle est prête à mesurer.
  const vuesDuProjet = (vues.data ?? []).filter((vue) => vue.nature !== "detail");
  const [derniereVue, setDerniereVue] = useState<number | null>(null);
  const [outilArme, setOutilArme] = useState<{ outil: OutilDeMesure; fois: number } | null>(null);
  const ouvrirLaFenetre = (outil?: OutilDeMesure, vueId?: number) => {
    const preferee = outil === "menuiserie" ? "facade" : "coupe";
    const choisie =
      vueId ??
      (derniereVue !== null && vuesDuProjet.some((vue) => vue.id === derniereVue) ? derniereVue : null) ??
      vuesDuProjet.find((vue) => vue.nature === preferee)?.id ??
      vuesDuProjet[0]?.id ??
      null;
    if (choisie === null) return;
    setCoupeOuverte(choisie);
    setDerniereVue(choisie);
    setOutilArme(outil ? { outil, fois: (outilArme?.fois ?? 0) + 1 } : null);
  };
  const vueOuverte = vues.data?.find((vue) => vue.id === coupeOuverte) ?? null;
  const plancheOuverte = vueOuverte ? sheets.find((s) => s.id === vueOuverte.sheet_id) ?? null : null;
  const selectedLocalId = searchParams.get("local");
  const selectRoomDirect = useCallback((id: string) => setParams({ local: id, panneau: "fiche" }), [setParams]);
  // Les corrections d'éléments s'appliquent d'abord : l'édition des contours travaille ensuite sur
  // l'étude qu'elles montrent, pour que les deux aperçus ne se contredisent jamais.
  const elementsState = useStudyElements({ token: token ?? null, sheetId, study: study ?? undefined });
  const natureBlockedReason =
    elementsState.pending > 0
      ? "Enregistrez ou abandonnez d'abord les corrections d'éléments en attente."
      : null;
  const editionState = useStudyEdition({
    token: token ?? null,
    sheetId,
    study: elementsState.shown,
    selectedRoom: study?.content.locaux.find((room) => room.id === selectedLocalId) ?? null,
    onSelectRoom: selectRoomDirect,
    natureBlockedReason,
  });
  const selectRoom = useCallback(
    (id: string) => {
      if (editionState.draft?.mode === "contour" && editionState.draft.roomId !== id) {
        editionState.keepDraft();
      } else if (editionState.draft && editionState.draft.roomId !== id) {
        return;
      }
      // Ouvrir un local, ou recliquer dans le sien hors d'un côté, relâche le côté désigné (D149).
      setCoteVisee(null);
      setValidation({ busy: false, message: null });
      selectRoomDirect(id);
    },
    [editionState.draft, editionState.keepDraft, selectRoomDirect],
  );

  useEffect(() => {
    const annulerEdition = (event: KeyboardEvent) => {
      if (!peutAnnulerEditionAvecEchap(event.key, editionState.draft, editionState.busy)) return;
      event.preventDefault();
      setMenu(null);
      editionState.reset();
    };
    window.addEventListener("keydown", annulerEdition, true);
    return () => window.removeEventListener("keydown", annulerEdition, true);
  }, [editionState.busy, editionState.draft, editionState.reset]);

  useEffect(() => {
    const gererHistorique = (event: KeyboardEvent) => {
      if (editionState.draft || cibleEditable(event.target)) return;
      const modificateur = event.ctrlKey || event.metaKey;
      if (!modificateur) return;
      const touche = event.key.toLowerCase();
      const retablir = (touche === "z" && event.shiftKey) || touche === "y";
      const annuler = touche === "z" && !event.shiftKey;
      if ((!annuler && !retablir) || (annuler && !elementsState.canUndo) || (retablir && !elementsState.canRedo)) {
        return;
      }
      event.preventDefault();
      if (retablir) elementsState.redo();
      else elementsState.undo();
    };
    window.addEventListener("keydown", gererHistorique, true);
    return () => window.removeEventListener("keydown", gererHistorique, true);
  }, [editionState.draft, elementsState.canRedo, elementsState.canUndo, elementsState.redo, elementsState.undo]);
  // Tant qu'un aperçu n'est pas enregistré, c'est lui qui est affiché sur le plan et dans la fiche.
  const shownStudy = editionState.shown;
  const selectedRoom = shownStudy?.content.locaux.find((room) => room.id === selectedLocalId) ?? null;

  // Le parcours (F2, D106) : il se déduit de l'étude, et c'est lui qui règle le panneau et les calques.
  const etapes = parcours(sheet ?? null, shownStudy, vues.data ?? [], hauteurs.data);
  const demandee = searchParams.get("etape");
  const etape = (etapes.find((item) => item.id === demandee)?.id ?? etapeCourante(etapes)) as EtapeId;
  const etapeActive = etapes.find((item) => item.id === etape) ?? etapes[0];
  // Ce que l'étape montre et laisse attraper (D155).
  const vue = vueDeLEtape(etape);
  // Les calques de l'étape s'appliquent jusqu'à ce qu'une case soit touchée ; la mention le dit (Q6).
  const calquesPilotes = !calquesLibres && etapeActive.calques !== null;
  const metricsAffiches = calquesPilotes ? (etapeActive.calques as MetricsShow) : metrics;

  const allerEtape = (cible: EtapeId) => {
    const trouvee = etapes.find((item) => item.id === cible);
    setCalquesLibres(false);
    elementsState.select(null);
    setParoiChoisie(null);
    setParams({ etape: cible, panneau: trouvee?.panneau ?? "fiche" });
  };

  // Le pont en cours amène le plan à lui : l'étape sert à les distinguer un à un (Q4).
  const elementCourant = shownStudy ? trouverElement(shownStudy.content, elementsState.selected) : null;
  // D244, D254 : à l'étape des parois, la touche Suppr supprime le mur ou l'indéterminé désigné (écarté,
  // réactivable) ; il quitte le plan à l'instant et l'enregistrement part tout seul (D252).
  const murDesigne =
    etape === "enveloppe" && (elementCourant?.type === "paroi" || elementCourant?.type === "indetermine") && !elementCourant.exclu
      ? elementCourant
      : null;
  useEffect(() => {
    if (!murDesigne || editionState.draft) return;
    const supprimer = (event: KeyboardEvent) => {
      if (event.key !== "Delete" || cibleEditable(event.target)) return;
      event.preventDefault();
      elementsState.supprimer(
        [refDeElement(murDesigne)],
        murDesigne.type === "paroi" ? MOTIF_MUR_SUPPRIME : MOTIF_INDETERMINE_SUPPRIME,
      );
    };
    window.addEventListener("keydown", supprimer);
    return () => window.removeEventListener("keydown", supprimer);
  }, [murDesigne, editionState.draft, elementsState]);
  // D249 : le mur désigné à l'étape des parois montre ses deux extrémités ; on les glisse librement.
  const murAPoignees = murDesigne?.type === "paroi" ? murDesigne : null;
  const extremites = shownStudy && murAPoignees ? extremitesDuMur(shownStudy.content, murAPoignees) : null;
  const [glisse, setGlisse] = useState<{
    extremite: Extremite;
    point: PdfPoint;
    longueur_m: number | null;
    aimante: boolean;
    pixelsPerPt: number;
  } | null>(null);
  const attraperExtremite = (point: PdfPoint, pixelsPerPt: number): boolean => {
    if (!extremites || editionState.draft) return false;
    const prise = PRISE_POIGNEE_PX / pixelsPerPt;
    const extremite = (["debut", "fin"] as const).find(
      (bout) => Math.hypot(extremites[bout][0] - point[0], extremites[bout][1] - point[1]) <= prise,
    );
    if (!extremite) return false;
    setGlisse({ extremite, point: extremites[extremite], longueur_m: null, aimante: false, pixelsPerPt });
    return true;
  };
  const glisserExtremite = (point: PdfPoint, event: PickEvent) => {
    if (!glisse || !shownStudy || !murAPoignees || !extremites) return;
    // Aimant (D249) : l'extrémité s'accroche au bout d'un autre mur, pour fermer les angles ; Maj le coupe.
    const depart = extremites[glisse.extremite];
    const trouve = event.shiftKey
      ? null
      : boutLePlusProche(shownStudy.content, murAPoignees, point, AIMANT_POIGNEE_PX / glisse.pixelsPerPt);
    // Le bout d'un mur qui partage ce sommet n'est pas une cible : il suit le glisser (D247).
    const cible = trouve && Math.hypot(trouve[0] - depart[0], trouve[1] - depart[1]) > 1e-6 ? trouve : null;
    const pose = cible ?? point;
    const autre = extremites[glisse.extremite === "debut" ? "fin" : "debut"];
    setGlisse({ ...glisse, point: pose, aimante: Boolean(cible), longueur_m: longueurEntre(shownStudy.content, murAPoignees, autre, pose) });
  };
  const lacherExtremite = () => {
    const fini = glisse;
    setGlisse(null);
    if (!fini || !shownStudy || !murAPoignees || !extremites) return;
    const depart = extremites[fini.extremite];
    if (Math.hypot(depart[0] - fini.point[0], depart[1] - fini.point[1]) * fini.pixelsPerPt < 2) return;
    const geste = gesteExtremite(shownStudy.content, murAPoignees, fini.extremite, fini.point);
    if (typeof geste === "string") {
      setModeleMessage(geste);
      return;
    }
    const entraines = extremitesPartagees(shownStudy.content, murAPoignees, depart, SOMMET_PARTAGE_PX / fini.pixelsPerPt)
      .map((autre) => gesteExtremite(shownStudy.content, autre.element, autre.extremite, fini.point))
      .filter((autre): autre is GesteExtremite => typeof autre !== "string");
    elementsState.deplacerExtremite(geste, entraines);
  };
  // D250 : le point posé s'accroche au bout d'un mur existant (Maj pour le poser librement).
  const pointDuTrace = (point: PdfPoint, pixelsPerPt: number, libre: boolean): PdfPoint => {
    if (libre || !shownStudy) return point;
    const aucun = { troncon: "", debut_m: 0, fin_m: 0 } as unknown as Parameters<typeof boutLePlusProche>[1];
    return boutLePlusProche(shownStudy.content, aucun, point, AIMANT_POIGNEE_PX / pixelsPerPt) ?? point;
  };
  const pontCourant =
    etape === "ponts" && shownStudy && elementCourant ? pontDeElement(shownStudy.content, elementCourant) : null;
  // Le côté désigné, s'il est toujours le même côté du local ouvert. Pas à l'étape des ponts, où la
  // fiche du local n'est pas affichée (D150).
  const rangCote = vue.cotes && vue.ficheLocal && !elementsState.selected ? rangVise(selectedRoom, coteVisee) : null;
  const milieuDuCote = rangCote != null && selectedRoom ? milieuCote(selectedRoom.fiche.cotes[rangCote]) : null;
  const focusPlan = pontCourant?.point_pdf
    ? { point: pontCourant.point_pdf, cle: `${pontCourant.troncon}|${pontCourant.abscisse_m}`, zoom: ZOOM_PONT }
    : milieuDuCote && coteVisee?.clic != null
      ? { point: milieuDuCote, cle: `cote|${coteVisee.clic}`, zoom: ZOOM_COTE }
      : null;
  // Désigner un côté relâche l'élément désigné, sinon la fiche resterait masquée (D150). Un second clic
  // sur le même côté le relâche (D146). Depuis la fiche, le plan va au côté ; depuis le plan, le côté est
  // déjà sous les yeux et le plan ne bouge pas.
  // Ce qui empêche de valider le local ouvert : un travail en attente d'abord, puis les parois douteuses.
  const validationBloquee = editionState.draft
    ? "Terminez ou annulez d'abord la reprise du contour."
    : elementsState.pending > 0
      ? "Enregistrez d'abord les corrections d'éléments en attente."
      : editionState.pending > 0
        ? "Enregistrez ou abandonnez d'abord les modifications de locaux en attente."
        : selectedRoom && demandeUneHauteur(selectedRoom) && hauteurConnue(selectedRoom, hauteurs.data) === null
          ? "Donnez d'abord sa hauteur sous plafond : « Mesurer la hauteur » dans une coupe, ou saisissez-la."
          : null;
  // D215 : la hauteur mesurée va d'abord au local ouvert, puis aux locaux cliqués ou à tous ceux qui n'en ont pas.
  const enfiler = (ids: string | string[], valeur: number) => {
    const changer = editionState.changeHauteur;
    fileHauteurs.current = fileHauteurs.current.then(() => changer(ids, valeur));
  };
  const poserHauteur = (valeur: number) => {
    const premier = etape === "locaux" && selectedRoom && demandeUneHauteur(selectedRoom) ? selectedRoom.id : null;
    if (premier) enfiler(premier, valeur);
    setHauteurAPoser({ valeur, poses: premier ? [premier] : [] });
  };
  // D220 : un modèle de menuiserie se pose sur la menuiserie désignée, puis sur chaque menuiserie cliquée.
  const [modeleAPoser, setModeleAPoser] = useState<{ nom: string; largeur_cm: number; hauteur_m: number; poses: string[] } | null>(null);
  const [modeleMessage, setModeleMessage] = useState<string | null>(null);
  const fileModeles = useRef<Promise<void>>(Promise.resolve());
  const affecterModele = (refs: StudyElementRef[], nom: string) => {
    if (!token || !sheetId || refs.length === 0) return;
    if (elementsState.pending > 0 || editionState.pending > 0 || editionState.draft) {
      setModeleMessage("Enregistrez ou abandonnez d'abord les corrections en attente : le modèle n'a pas été posé.");
      return;
    }
    const planche = sheetId;
    fileModeles.current = fileModeles.current.then(async () => {
      try {
        const enregistre = await thermiqueApi.saveStudy(token, planche, {
          operations: refs.map((ref) => ({ type: "element_corriger", element: ref, changes: { modele: nom } })),
          motif: "modele_menuiserie",
          valider: false,
        });
        queryClient.setQueryData<Study>(studyQueryKey(planche), enregistre);
        void queryClient.invalidateQueries({ queryKey: menuiseriesQueryKey(projectId) });
        setModeleMessage(
          nom
            ? `« ${nom} » posé sur ${refs.length} menuiserie${refs.length > 1 ? "s" : ""}.`
            : "Modèle retiré : la menuiserie reprend sa largeur relevée.",
        );
      } catch (echec) {
        setModeleMessage(echec instanceof Error ? echec.message : "Le modèle n'a pas été posé.");
      }
    });
  };
  const poserModele = (modele: { nom: string; largeur_cm: number; hauteur_m: number }) => {
    const designe = shownStudy ? trouverElement(shownStudy.content, elementsState.selected) : null;
    // D224 : la menuiserie désignée reçoit le modèle sur tous ses morceaux.
    const premiers = shownStudy && designe && designe.type === "menuiserie" ? baieDeLElement(shownStudy.content, designe) : [];
    if (premiers.length) affecterModele(premiers, modele.nom);
    setModeleMessage(null);
    setModeleAPoser({ ...modele, poses: premiers.map(cleDeRef) });
  };
  const memeLargeurRestantes =
    modeleAPoser && shownStudy
      ? menuiseriesDeMemeLargeur(shownStudy.content, modeleAPoser).filter((ref) => !modeleAPoser.poses.includes(cleDeRef(ref)))
      : [];
  const sansHauteurRestants =
    hauteurAPoser && shownStudy
      ? locauxSansHauteur(shownStudy.content, hauteurs.data).filter((local) => !hauteurAPoser.poses.includes(local.id))
      : [];
  const validerLocal = async () => {
    if (!token || !sheetId || !selectedRoom) return;
    setValidation({ busy: true, message: null });
    try {
      const enregistre = await thermiqueApi.validateStudyRoom(token, sheetId, selectedRoom.id);
      queryClient.setQueryData<Study>(studyQueryKey(sheetId), enregistre);
      setValidation({ busy: false, message: null });
      // Enchaîner sur le premier local encore à valider, chauffés d'abord (D63).
      const suivant = sortedStudyRooms(enregistre.content.locaux).find(
        (room) => (enregistre.local_states[room.id]?.status ?? "a_verifier") !== "valide",
      );
      if (suivant) selectRoom(suivant.id);
    } catch (error) {
      setValidation({ busy: false, message: error instanceof Error ? error.message : "La validation a échoué." });
    }
  };
  const viserCote = (rang: number, depuis: "fiche" | "plan") => {
    if (!selectedRoom || rang === rangCote) {
      setCoteVisee(null);
      return;
    }
    elementsState.select(null);
    if (depuis === "fiche") clicsCote.current += 1;
    setCoteVisee({
      localId: selectedRoom.id,
      rang,
      empreinte: empreinteCote(selectedRoom.fiche.cotes[rang]),
      clic: depuis === "fiche" ? clicsCote.current : null,
    });
  };

  useEffect(() => {
    if (!project || !token || referenceMigration.current === project.id) return;
    referenceMigration.current = project.id;
    if (project.reference_sheet_id !== null) {
      setReferenceId(project.reference_sheet_id);
      removeReference(project.id);
      return;
    }
    const stored = readReference(project.id);
    if (stored !== null && allSheets(project).some((item) => item.id === stored)) {
      setReferenceId(stored);
      void thermiqueApi.updateProject(token, project.id, { reference_sheet_id: stored }).then(() => {
        removeReference(project.id);
        void queryClient.invalidateQueries({ queryKey: projectQueryKey(project.id) });
        void queryClient.invalidateQueries({ queryKey: projectsQueryKey });
      });
    } else {
      setReferenceId(null);
    }
  }, [project, queryClient, token]);

  useEffect(() => {
    if (selectedLocalId && study !== undefined && !study?.content.locaux.some((room) => room.id === selectedLocalId)) {
      setParams({ local: null, panneau: panel === "fiche" ? "planche" : panel });
    }
  }, [panel, selectedLocalId, setParams, study]);

  if (error) {
    return <p className="th-alert th-alert--error th-main">{error.message}</p>;
  }
  if (!project || !token) {
    return <p className="th-muted th-main">Chargement du projet…</p>;
  }

  const makeReference = async (id: number) => {
    writeReference(project.id, id);
    setReferenceId(id);
    try {
      await thermiqueApi.updateProject(token, project.id, { reference_sheet_id: id });
      removeReference(project.id);
      queryClient.setQueryData<ProjectDetail>(projectQueryKey(project.id), (current) =>
        current ? { ...current, reference_sheet_id: id } : current,
      );
      void queryClient.invalidateQueries({ queryKey: projectsQueryKey });
    } catch {
      // Le choix reste dans le navigateur et sera migré à la prochaine ouverture.
    }
  };
  const levelTitle = sheet ? sheetTitle(sheet) : "";
  const changerDeNiveau = (id: number) => {
    editionState.reset();
    editionState.cancelPending();
    elementsState.select(null);
    setCalquesLibres(false);
    setParams({ planche: id, local: null, panneau: panel === "fiche" ? "planche" : panel });
  };
  const selectSheet = (id: number) => {
    // Des corrections en attente disparaîtraient sans un mot : on demande d'abord (D111).
    if ((elementsState.pending > 0 || editionState.pending > 0) && id !== sheetId) {
      setDepartEnAttente(id);
      return;
    }
    changerDeNiveau(id);
  };

  return (
    <div className="th-ws">
      <div className="th-ws__bar">
        <select
          className="th-ws__project"
          aria-label="Projet"
          value={project.id}
          onChange={(event) => navigate(`/projets/${event.target.value}`)}
        >
          {(projects ?? [project]).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <nav className="th-ws__levels" aria-label="Niveaux">
          {groups.levels.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={item.id === sheetId}
              className={item.id === sheetId ? "is-active" : undefined}
              onClick={() => selectSheet(item.id)}
              title={item.label}
            >
              {sheetTitle(item)}
              {item.id === reference?.id && <span className="th-ws__ref" aria-label="plan de référence"> ★</span>}
            </button>
          ))}
          {groups.levels.length === 0 && sheets.length > 0 && <span className="th-muted">Aucune planche classée en plan</span>}
        </nav>
        <SheetMenu label="Coupes" sheets={groups.sections} currentId={sheetId} onPick={selectSheet} />
        <SheetMenu label="Façades" sheets={groups.elevations} currentId={sheetId} onPick={selectSheet} />
        <SheetMenu label="Autres" sheets={groups.others} currentId={sheetId} onPick={selectSheet} />
        <div className="th-ws__tabs" role="tablist" aria-label="Panneau">
          {PANELS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={panel === item.id}
              className={panel === item.id ? "is-active" : undefined}
              onClick={() => setParams({ panneau: item.id })}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className={`th-ws__body th-ws__body--${panel}`}>
        <aside className="th-ws__side" aria-label="Étude du niveau">
          <section>
            <h2>Étude {levelTitle ? `· ${levelTitle}` : ""}</h2>
            {/* D106 : le parcours pilote. Cliquer une étape change le panneau de droite et les calques
                du plan. Rien n'est verrouillé : une étape en retard ne barre pas la suivante (D109). */}
            <ol className="th-ws-steps">
              {etapes.map((item) => (
                <li
                  key={item.id}
                  className={`th-ws-step--${item.etat}${item.id === etape ? " is-current" : ""}`}
                  aria-current={item.id === etape ? "step" : undefined}
                >
                  <button type="button" onClick={() => allerEtape(item.id)}>
                    {item.titre}
                  </button>
                  <small>
                    {item.id === "planche" && sheet ? `${STATUS_LABELS[sheet.status]} · ` : ""}
                    {item.reste}
                  </small>
                </li>
              ))}
            </ol>
            {/* D111 : pas de départ silencieux. On ne change pas de niveau sans le dire. */}
            {departEnAttente !== null && (
              <div className="th-alert th-alert--warn th-ws-depart">
                <p>
                  {elementsState.pending + editionState.pending} modification
                  {elementsState.pending + editionState.pending > 1 ? "s" : ""} ne sont pas encore enregistrée
                  {elementsState.pending + editionState.pending > 1 ? "s" : ""} sur ce niveau.
                </p>
                <div className="th-inline">
                  <button
                    type="button"
                    className="po2-button po2-button--primary"
                    disabled={elementsState.busy || editionState.busy}
                    onClick={() => void (async () => {
                      const cible = departEnAttente;
                      const elementsOk = await elementsState.saveAsync();
                      const locauxOk = await editionState.savePendingAsync();
                      if (!elementsOk || !locauxOk) return;
                      setDepartEnAttente(null);
                      if (cible !== null) changerDeNiveau(cible);
                    })()}
                  >
                    Enregistrer puis changer de niveau
                  </button>
                  <button
                    type="button"
                    className="po2-button po2-button--ghost"
                    onClick={() => {
                      const cible = departEnAttente;
                      elementsState.cancel();
                      editionState.cancelPending();
                      setDepartEnAttente(null);
                      if (cible !== null) changerDeNiveau(cible);
                    }}
                  >
                    Abandonner les corrections
                  </button>
                  <button type="button" className="th-link" onClick={() => setDepartEnAttente(null)}>
                    Rester ici
                  </button>
                </div>
              </div>
            )}
          </section>
          <section>
            <h2>Locaux</h2>
            <StudyCoverageBanner coverage={shownStudy?.content.couverture ?? null} />
            <StudyCoherenceReport coherence={shownStudy?.content.coherence ?? null} />
            {shownStudy ? (
              <StudyRoomList study={shownStudy} selectedId={selectedRoom?.id ?? null} onSelect={selectRoom} />
            ) : (
              <p className="th-muted">Les locaux du niveau, chauffés d'abord, apparaîtront ici une fois l'étude importée.</p>
            )}
            {editionState.pending > 0 && (
              <div className="th-element-enregistrer">
                <p className="th-alert th-alert--warn">
                  {editionState.pending} modification{editionState.pending > 1 ? "s" : ""} de locaux en attente —
                  contours provisoires, métrés actualisés au prochain enregistrement.
                </p>
                <div className="th-inline">
                  <button
                    type="button"
                    className="po2-button po2-button--primary"
                    disabled={editionState.busy}
                    onClick={editionState.savePending}
                  >
                    {editionState.busy ? "Calcul…" : "Enregistrer les modifications"}
                  </button>
                  <button type="button" className="th-link" disabled={editionState.busy} onClick={editionState.cancelPending}>
                    Tout annuler
                  </button>
                </div>
              </div>
            )}
          </section>
        </aside>

        <div className="th-ws__plan">
          {hauteurAPoser && (
            <div className="th-poser-hauteur" role="status">
              <span>
                Hauteur <strong>{hauteurAPoser.valeur.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} m</strong> : cliquez
                les locaux concernés sur le plan
                {hauteurAPoser.poses.length > 4
                  ? ` (${hauteurAPoser.poses.length} locaux posés)`
                  : hauteurAPoser.poses.length > 0 &&
                    ` (${hauteurAPoser.poses
                      .map((id) => shownStudy?.content.locaux.find((local) => local.id === id)?.nom ?? id)
                      .join(", ")})`}
                .
              </span>
              {sansHauteurRestants.length > 0 && (
                <button
                  type="button"
                  className="po2-button po2-button--ghost"
                  onClick={() => {
                    const ids = sansHauteurRestants.map((local) => local.id);
                    enfiler(ids, hauteurAPoser.valeur);
                    setHauteurAPoser({ ...hauteurAPoser, poses: [...hauteurAPoser.poses, ...ids] });
                  }}
                >
                  Appliquer aux {sansHauteurRestants.length} locaux sans hauteur
                </button>
              )}
              {shownStudy && (
                <button
                  type="button"
                  className="po2-button po2-button--ghost"
                  onClick={() => {
                    const tous = shownStudy.content.locaux.filter(demandeUneHauteur).map((local) => local.id);
                    const valeur = hauteurAPoser.valeur.toLocaleString("fr-FR");
                    if (!window.confirm(`Donner ${valeur} m aux ${tous.length} locaux du niveau, y compris ceux qui ont déjà une hauteur ?`)) return;
                    enfiler(tous, hauteurAPoser.valeur);
                    setHauteurAPoser({ ...hauteurAPoser, poses: tous });
                  }}
                >
                  Appliquer à tous les locaux du niveau
                </button>
              )}
              <button type="button" className="po2-button po2-button--primary" onClick={() => setHauteurAPoser(null)}>
                Terminé
              </button>
            </div>
          )}
          {traceMur && (
            <div className="th-poser-hauteur" role="status">
              <span>
                Nouveau mur : {traceMur.premier ? "cliquez sa fin" : "cliquez son début"} sur la face intérieure. Les points
                s'accrochent au bout des murs voisins (Maj : point libre). Échap pour annuler.
                {traceMessage && <small className="th-poser-hauteur__message"> {traceMessage}</small>}
              </span>
              <button
                type="button"
                className="po2-button po2-button--ghost"
                onClick={() => {
                  setTraceMur(null);
                  setTraceMessage(null);
                }}
              >
                Annuler
              </button>
            </div>
          )}
          {!traceMur && traceMessage && etape === "enveloppe" && (
            <div className="th-poser-hauteur" role="status">
              <span>{traceMessage}</span>
              <button type="button" className="po2-button po2-button--ghost" onClick={() => setTraceMessage(null)}>
                OK
              </button>
            </div>
          )}
          {modeleAPoser && (
            <div className="th-poser-hauteur" role="status">
              <span>
                Modèle <strong>{modeleAPoser.nom}</strong> ({Math.round(modeleAPoser.largeur_cm)} × {Math.round(modeleAPoser.hauteur_m * 100)} cm) :
                cliquez sur le plan les menuiseries de ce modèle
                {modeleAPoser.poses.length > 0 && ` (${modeleAPoser.poses.length} posée${modeleAPoser.poses.length > 1 ? "s" : ""})`}.
                {modeleMessage && <small className="th-poser-hauteur__message"> {modeleMessage}</small>}
              </span>
              {memeLargeurRestantes.length > 0 && (
                <button
                  type="button"
                  className="po2-button po2-button--ghost"
                  title="Les menuiseries du niveau dont la largeur relevée est à ± 2 cm de celle du modèle"
                  onClick={() => {
                    affecterModele(memeLargeurRestantes, modeleAPoser.nom);
                    setModeleAPoser({ ...modeleAPoser, poses: [...modeleAPoser.poses, ...memeLargeurRestantes.map(cleDeRef)] });
                  }}
                >
                  Appliquer aux {memeLargeurRestantes.length} menuiseries de même largeur (± 2 cm)
                </button>
              )}
              <button type="button" className="po2-button po2-button--primary" onClick={() => setModeleAPoser(null)}>
                Terminé
              </button>
            </div>
          )}
          {!sheet ? (
            <div className="th-viewer th-viewer--empty">
              <p className="th-viewer__status">Déposez les plans du projet dans le panneau « Documents » pour commencer.</p>
            </div>
          ) : raster.data ? (
            <TileSheetViewer
              key={viewKey}
              manifest={raster.data}
              tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
              tool={
                editionState.draft
                  ? "edition"
                  : calage || cadreVue
                    ? "calage"
                    : hauteurAPoser || modeleAPoser || traceMur
                      ? "pan"
                      : tool
              }
              points={cadreVue?.premier ? [cadreVue.premier] : points}
              segments={editionState.draft ? [] : sheetSegments(sheet, tool, points)}
              onAddPoint={(point, event) => {
                if (editionState.handlers.onAddPoint(point)) return;
                if (cadreVue) {
                  cliquerCadreVue(point);
                  return;
                }
                if (calage) {
                  cliquerCalage(point, event.altKey);
                  return;
                }
                setPoints((current) => (current.length >= 2 ? [point] : [...current, point]));
              }}
              onHover={
                traceMur?.premier
                  ? (point) => point && setTraceMur((courant) => (courant ? { ...courant, survol: point } : courant))
                  : undefined
              }
              onPick={(point, pixelsPerPt, event) => {
                // D250 : tracé d'un mur, premier puis second point.
                if (traceMur && shownStudy) {
                  const pose = pointDuTrace(point, pixelsPerPt, event.shiftKey);
                  if (!traceMur.premier) {
                    setTraceMur({ premier: pose, survol: pose });
                    return;
                  }
                  const geste = gesteCreation(shownStudy.content, traceMur.premier, pose);
                  if (typeof geste === "string") {
                    setTraceMessage(geste);
                    return;
                  }
                  setTraceMur(null);
                  setTraceMessage(null);
                  setParams({ panneau: "fiche" });
                  elementsState.creerMur(geste);
                  return;
                }
                // Option C (D262) : à l'étape Parois, un clic près d'une paroi d'un local l'ouvre.
                if (etape === "enveloppe" && shownStudy) {
                  const paroi = paroiVisee(shownStudy.content, point, PRISE_ELEMENT_PAROIS_PX / pixelsPerPt);
                  if (paroi) {
                    setParoiChoisie(paroi);
                    setParams({ local: paroi.local, panneau: "fiche" });
                    return;
                  }
                  setParoiChoisie(null);
                }
                // Hauteur mesurée dans une coupe : chaque local cliqué la reçoit (D211).
                if (hauteurAPoser) {
                  const local = shownStudy ? roomAt(shownStudy.content.locaux, point) : null;
                  if (local && !hauteurAPoser.poses.includes(local.id)) {
                    // Les enregistrements se suivent : deux clics rapides ne se marchent pas dessus.
                    enfiler(local.id, hauteurAPoser.valeur);
                    setHauteurAPoser({ ...hauteurAPoser, poses: [...hauteurAPoser.poses, local.id] });
                  }
                  return;
                }
                // Modèle de menuiserie : chaque menuiserie cliquée le reçoit (D220).
                if (modeleAPoser && shownStudy) {
                  const vise = viserSurLePlan(
                    {
                      ...shownStudy.content,
                      enveloppe: {
                        ...shownStudy.content.enveloppe,
                        liaisons: [],
                        objets: (shownStudy.content.enveloppe.objets ?? []).filter((shape) => shape.category === "menuiserie_exterieure"),
                      },
                    },
                    shownStudy.content.locaux,
                    point,
                    { element: PRISE_ELEMENT_PAROIS_PX / pixelsPerPt, pont: 0 },
                  );
                  const element = vise ? trouverElement(shownStudy.content, vise.ref) : null;
                  if (!element || element.type !== "menuiserie") {
                    setModeleMessage("Cliquez sur le trait d'une menuiserie.");
                    return;
                  }
                  // D224 : un clic sur un morceau pose le modèle sur toute la baie.
                  const refs = baieDeLElement(shownStudy.content, element).filter((ref) => !modeleAPoser.poses.includes(cleDeRef(ref)));
                  if (refs.length) {
                    affecterModele(refs, modeleAPoser.nom);
                    setModeleAPoser({ ...modeleAPoser, poses: [...modeleAPoser.poses, ...refs.map(cleDeRef)] });
                  }
                  return;
                }
                // Dans le local ouvert, un clic sur un élément d'enveloppe l'attrape en priorité : c'est
                // le geste de l'étape 5. Le reste du temps, le clic ouvre ou referme un local.
                if (shownStudy) {
                  const liaisons = shownStudy.content.enveloppe.liaisons ?? [];
                  // Étape des ponts : le clic ne vise que les ponts, large, et rien d'autre ne lui dispute —
                  // ni le local, ni sa limite, ni le mur qui porte le pont (D156). Un clic dans le vide ne
                  // change rien : on ne perd pas le pont en cours.
                  if (vue.clic === "ponts") {
                    const pont = pontAt(liaisons, point, PRISE_PONT_ETAPE_PX / pixelsPerPt);
                    const ref = pont ? elementDuPont(shownStudy.content, pont) : null;
                    if (ref) {
                      elementsState.select(ref);
                      setParams({ panneau: "fiche" });
                    }
                    return;
                  }
                  // Un côté du local ouvert se désigne de l'intérieur, près de son tracé ; le mur qui le
                  // porte est au-delà du trait, donc toujours attrapable. Un pont passe avant (D149).
                  if (selectedRoom && (vue.clic === "locaux" || vue.clic === "tout") && !editionState.draft) {
                    const pont = vue.ponts ? pontAt(liaisons, point, PRISE_PONT_PX / pixelsPerPt) : null;
                    const rang = pont ? null : coteAt(selectedRoom, point, PRISE_COTE_PX / pixelsPerPt);
                    if (rang != null) {
                      viserCote(rang, "plan");
                      setParams({ panneau: "fiche" });
                      return;
                    }
                  }
                  // On cherche l'élément dans tout le niveau, et non dans le seul local ouvert : un mur
                  // est en dehors du contour de son local, donc introuvable autrement. Le pont passe en
                  // premier, sinon le mur qui le porte l'emporterait toujours. À l'étape des parois, les
                  // ponts ne sont pas attrapables ; à celle des locaux, rien de l'enveloppe ne l'est.
                  const vise =
                    vue.clic === "locaux"
                      ? null
                      : viserSurLePlan(
                          vue.clic === "elements"
                            ? {
                                ...shownStudy.content,
                                enveloppe: {
                                  ...shownStudy.content.enveloppe,
                                  liaisons: [],
                                  // D227 : à l'étape des parois, seuls les murs s'attrapent ; à celle des
                                  // menuiseries, seules les menuiseries.
                                  // D242 : à l'étape des parois, on vise la ligne de métré du mur.
                                  objets: (vue.famille === "parois"
                                    ? formesEtapeParois(shownStudy.content)
                                    : shownStudy.content.enveloppe.objets ?? []
                                  ).filter(
                                    (shape) =>
                                      !vue.famille || (shape.category === "menuiserie_exterieure") === (vue.famille === "menuiseries"),
                                  ),
                                },
                              }
                            : shownStudy.content,
                          shownStudy.content.locaux,
                          point,
                          {
                            // Étape des parois : les menuiseries y sont épaissies, la prise suit (M1).
                            element: (vue.clic === "elements" ? PRISE_ELEMENT_PAROIS_PX : PRISE_ELEMENT_PX) / pixelsPerPt,
                            pont: PRISE_PONT_PX / pixelsPerPt,
                          },
                        );
                  if (vise) {
                    setCoteVisee(null);
                    elementsState.select(vise.ref);
                    setParams({ local: vise.room?.id ?? selectedLocalId, panneau: "fiche" });
                    return;
                  }
                }
                const room = shownStudy ? roomAt(shownStudy.content.locaux, point) : null;
                if (room) {
                  if (room.id !== selectedRoom?.id) {
                    elementsState.select(null);
                  }
                  selectRoom(room.id);
                } else if (selectedLocalId) {
                  elementsState.select(null);
                  setCoteVisee(null);
                  setParams({ local: null, panneau: panel === "fiche" ? "planche" : panel });
                }
              }}
              onContextPick={(point, pixelsPerPt, ecran) => {
                // Clic droit : les gestes du contour en cours d'édition, sinon ceux du local visé.
                const actions: PlanAction[] = editionState.draft
                  ? editionState.contextActions(point, pixelsPerPt)
                  : (() => {
                      // Étape des ponts : le clic droit pose un pont, même sur un local — l'étape ne propose
                      // que ses propres gestes (D155), et le pont manquant est souvent au milieu d'un local
                      // pour le zonage, sous le calque de la pièce (remarque C, D157).
                      if (vue.clic === "ponts") {
                        if (!shownStudy) return [];
                        const occupe = elementsState.busy
                          ? "Un calcul est déjà en cours."
                          : editionState.pending > 0
                            ? "Enregistrez ou abandonnez d'abord les modifications de locaux en attente."
                            : undefined;
                        return TYPES_PONT_REATTRIBUABLES.map(({ type, label }) => ({
                          cle: `pont-${type}`,
                          label: `Ajouter un pont ici : ${label.toLowerCase()}`,
                          disabled: Boolean(occupe),
                          title: occupe,
                          faire: () => {
                            setParams({ panneau: "fiche" });
                            elementsState.ajouterPont(point, type);
                          },
                        }));
                      }
                      // D250, D247 : à l'étape des parois, le clic droit crée un mur ou ajoute un point sur un mur.
                      const actionsMurs: PlanAction[] = [];
                      if (GESTES_MURS_DU_RELEVE && etape === "enveloppe" && shownStudy) {
                        actionsMurs.push({
                          cle: "creer-mur",
                          label: "Créer un mur à partir d'ici",
                          faire: () => {
                            elementsState.select(null);
                            setTraceMessage(null);
                            setTraceMur({ premier: pointDuTrace(point, pixelsPerPt, false), survol: null });
                          },
                        });
                        const surMur = viserSurLePlan(
                          { ...shownStudy.content, enveloppe: { ...shownStudy.content.enveloppe, liaisons: [], objets: formesDesLignes(shownStudy.content) } },
                          shownStudy.content.locaux,
                          point,
                          { element: PRISE_ELEMENT_PAROIS_PX / pixelsPerPt, pont: 0 },
                        );
                        const mur = surMur ? trouverElement(shownStudy.content, surMur.ref) : null;
                        if (mur && mur.type === "paroi" && !mur.exclu) {
                          actionsMurs.push({
                            cle: "point-mur",
                            label: "Ajouter un point ici sur ce mur",
                            faire: () => {
                              const geste = gesteCoupe(shownStudy.content, mur, point);
                              if (typeof geste === "string") {
                                setTraceMessage(geste);
                                return;
                              }
                              elementsState.couperMur(geste);
                            },
                          });
                        }
                      }
                      const room = shownStudy ? roomAt(shownStudy.content.locaux, point) : null;
                      if (actionsMurs.length) return actionsMurs;
                      if (!room) {
                        if (!shownStudy) return [];
                        return [
                          {
                            cle: "creer-local",
                            label: "Créer un local ici",
                            disabled: editionState.natureChangeDisabled,
                            title: editionState.natureBlockedReason ?? undefined,
                            faire: () => {
                              elementsState.select(null);
                              setParams({ local: null, panneau: "fiche" });
                              editionState.startNew(point);
                            },
                          },
                        ];
                      }
                      const actionsNature: PlanAction[] = otherLocalNatures(room.nature).map((nature) => ({
                        cle: `nature-${nature}`,
                        label: `Classer : ${NATURE_LABELS[nature]}`,
                        disabled: editionState.natureChangeDisabled,
                        title:
                          editionState.natureBlockedReason ??
                          (editionState.natureChangeDisabled ? "Un calcul est déjà en cours." : undefined),
                        faire: () => {
                          selectRoom(room.id);
                          void editionState.changeNature(room.id, nature);
                        },
                      }));
                      return [
                        { cle: "fiche", label: `Ouvrir « ${room.nom} »`, faire: () => selectRoom(room.id) },
                        ...actionsNature,
                        {
                          cle: "contour",
                          label: "Reprendre le contour",
                          faire: () => {
                            selectRoom(room.id);
                            editionState.startOn(room.id, "contour");
                          },
                        },
                        {
                          cle: "couper",
                          label: "Couper en deux",
                          faire: () => {
                            selectRoom(room.id);
                            editionState.startOn(room.id, "couper");
                          },
                        },
                        {
                          cle: "supprimer-local",
                          label: `Supprimer définitivement « ${room.nom} »`,
                          disabled: editionState.busy || Boolean(editionState.draft) || Boolean(natureBlockedReason),
                          title: natureBlockedReason ?? undefined,
                          faire: () => {
                            if (!window.confirm(
                              `Retirer le local « ${room.nom} » du brouillon ?\n\nLa suppression deviendra définitive lorsque vous enregistrerez les modifications. Avant cela, « Tout annuler » permet encore de le récupérer.`,
                            )) return;
                            if (editionState.deleteRoom(room.id)) {
                              elementsState.select(null);
                              setParams({ local: null, panneau: "fiche" });
                            }
                          },
                        },
                      ];
                    })();
                setMenu(actions.length ? { x: ecran.x, y: ecran.y, actions } : null);
              }}
              onGrab={(point, pixelsPerPt, event) =>
                attraperExtremite(point, pixelsPerPt) || editionState.handlers.onGrab(point, pixelsPerPt, event)
              }
              onGrabMove={(point, event) => (glisse ? glisserExtremite(point, event) : editionState.handlers.onGrabMove(point))}
              onGrabEnd={() => (glisse ? lacherExtremite() : editionState.handlers.onGrabEnd())}
              initialView={views.current.get(viewKey) ?? null}
              onViewChange={(view) => views.current.set(viewKey, view)}
              focus={focusPlan}
              renderTools={
                <div className="th-viewer__display" role="group" aria-label="Ce qui s'affiche sur le plan">
                  {/* Superposition des niveaux (S3, D169) : deux cases indépendantes, à toutes les étapes. */}
                  {(["inferieur", "superieur"] as const).map((sens) => {
                    const voisin = voisins[sens];
                    return (
                      <label
                        key={sens}
                        className={`th-viewer__fantome th-viewer__fantome--${sens}`}
                        title={voisin ? `En transparence : ${sheetTitle(voisin)}` : "Pas de plan de niveau à cet étage"}
                      >
                        <input
                          type="checkbox"
                          disabled={!voisin}
                          checked={fantomes[sens]}
                          onChange={() => setFantomes((current) => ({ ...current, [sens]: !current[sens] }))}
                        />
                        {/* Le nom du voisin dans la case : on sait quel plan va apparaître avant de cocher. */}
                        {voisin
                          ? `Voir ${sheetTitle(voisin)} (${sens === "inferieur" ? "dessous" : "dessus"})`
                          : sens === "inferieur"
                            ? "Pas de niveau en dessous"
                            : "Pas de niveau au-dessus"}
                      </label>
                    );
                  })}
                  {sheet.nature === "plan" && (
                    <button
                      type="button"
                      className="po2-button po2-button--ghost th-ouvrir-vues"
                      disabled={vuesDuProjet.length === 0}
                      title={vuesDuProjet.length ? "Ouvrir une coupe ou une élévation pour y mesurer" : "Aucune coupe ni élévation lue dans le projet"}
                      onClick={() => ouvrirLaFenetre(etape === "menuiseries" ? "menuiserie" : etape === "locaux" ? "hauteur" : undefined)}
                    >
                      Coupes et élévations
                    </button>
                  )}
                  {shownStudy &&
                    METRICS_CASES.map((item) => (
                      <label key={item.cle} title={item.titre}>
                        <input
                          type="checkbox"
                          checked={metricsAffiches[item.cle]}
                          onChange={() => basculerMetrique(item.cle, metricsAffiches)}
                        />
                        {item.label}
                      </label>
                    ))}
                  {/* Dire qui commande, sinon une case cochée par l'étape passe pour un bug (Q6). */}
                  {shownStudy && calquesPilotes && <small className="th-viewer__pilote">réglés par l'étape</small>}
                </div>
              }
              renderOverlay={(toScreen, taille) => (
                <>
                  {/* Le voisin passe sous tout le reste : c'est un fond de lecture, pas un objet du plan. */}
                  {fantomesAffiches.map((fantome) => (
                    <NiveauFantome
                      key={fantome.sens}
                      manifest={fantome.image}
                      tileTemplate={thermiqueApi.apiUrl(fantome.image.tile_url)}
                      sim={fantome.sim}
                      toScreen={toScreen}
                      taille={taille}
                      sens={fantome.sens}
                    />
                  ))}
                  {calage && (
                    <PointsDeCalage
                      calage={{
                        sens: calage.sens,
                        paires: [calage.base, calage.second, calage.longueur].filter((paire): paire is [PdfPoint, PdfPoint] => paire !== null),
                        enAttente: calage.enAttente,
                      }}
                      sim={fantomesAffiches.find((item) => item.sens === calage.sens)?.sim ?? null}
                      toScreen={toScreen}
                    />
                  )}
                  <NorthOverlay nord={sheet.nord} enCours={points} toScreen={toScreen} actif={tool === "nord"} />
                  {vuesDeLaPlanche.length > 0 && (
                    <CadresDesVues vues={vuesDeLaPlanche} toScreen={toScreen} choisie={vueChoisie} enCours={cadreVue} survol={null} />
                  )}
                  {shownStudy && (
                    <>
                        <StudyOverlay
                          rooms={shownStudy.content.locaux}
                          selectedId={selectedRoom?.id ?? null}
                          toScreen={toScreen}
                          onSelect={selectRoom}
                          draft={editionState.draft}
                          locked={tool !== "pan"}
                          gaps={shownStudy.content.couverture?.zones_non_affectees_pdf ?? []}
                          discret={vue.locauxDiscrets && !editionState.draft}
                        />
                        {!editionState.draft && (
                          <StudyMetrics
                            rooms={shownStudy.content.locaux}
                            selected={selectedRoom}
                            shapes={
                              // D242 : à l'étape des parois, un mur = sa ligne de métré, plus ses couches une à une.
                              vue.famille === "parois" ? formesEtapeParois(shownStudy.content) : shownStudy.content.enveloppe.objets ?? []
                            }
                            bridges={shownStudy.content.enveloppe.liaisons ?? []}
                            show={metricsAffiches}
                            toScreen={toScreen}
                            selectedElement={elementsState.selected}
                            grouperPonts={etape !== "ponts"}
                            coteVisee={rangCote}
                            familles={vue}
                            accentMenuiseries={etape === "enveloppe" || etape === "menuiseries"}
                            famille={vue.famille}
                            memeBaie={
                              elementCourant?.type === "menuiserie" ? baieDeLElement(shownStudy.content, elementCourant) : undefined
                            }
                          />
                      )}
                      {traceMur?.premier && (
                        <TraceDuMur
                          premier={traceMur.premier}
                          survol={traceMur.survol}
                          longueur_m={traceMur.survol ? longueurSurLePlan(shownStudy.content, traceMur.premier, traceMur.survol) : null}
                          toScreen={toScreen}
                        />
                      )}
                      {etape === "enveloppe" && !editionState.draft && (
                        <ParoisDesLocaux content={shownStudy.content} choisie={paroiChoisie} toScreen={toScreen} />
                      )}
                      {!editionState.draft && extremites && (
                        <PoigneesDuMur extremites={extremites} glisse={glisse} toScreen={toScreen} />
                      )}
                      {/* D221 : à l'étape des menuiseries, chacune porte sa cote, héritée du modèle posé. */}
                      {!editionState.draft && (etape === "menuiseries" || modeleAPoser) && (
                        <CotesMenuiseries cotes={cotesDesMenuiseries(shownStudy.content, menuiseries.data?.modeles)} toScreen={toScreen} />
                      )}
                    </>
                  )}
                </>
              )}
            />
          ) : (
            <div className="th-viewer th-viewer--empty">
              <p className="th-viewer__status">
                {raster.error ? `Affichage impossible : ${raster.error.message}` : "Préparation de la planche… (quelques secondes à la première ouverture)"}
              </p>
            </div>
          )}
          {menu && <PlanMenu x={menu.x} y={menu.y} actions={menu.actions} onClose={() => setMenu(null)} />}
          {/* Calage des niveaux (S2, D173, D201) : dit si le calque tombe juste, et guide point de base puis rotation. */}
          {(fantomesAffiches.length > 0 || calage) && (
            <div className="th-calage" role="status">
              {calage ? (
                <>
                  <GuideCalage
                    al={calage}
                    voisin={voisins[calage.sens] ? sheetTitle(voisins[calage.sens]!) : "niveau voisin"}
                    plan={sheet ? sheetTitle(sheet) : "plan actif"}
                    couleur={calage.sens === "inferieur" ? "bleu" : "orange"}
                    echelle={echelleDuCalage(calage)}
                    onEnregistrer={() => void enregistrerCalage(calage)}
                    onGarderRotation={() => setCalage(garderLaRotation(calage, echelleDuCalage(calage)))}
                    onRefaire={() => setCalage(refaireEtape(calage))}
                  />
                  {calage.message && <span className="th-calage__message">{calage.message}</span>}
                  <button type="button" className="th-link" onClick={() => setCalage(null)} title="Raccourci : Échap">
                    {calage.etape === "enregistre" || (calage.etape === "base" && !calage.enAttente) ? "Fermer" : "Annuler"}
                  </button>
                </>
              ) : (
                fantomesAffiches.map((fantome) => (
                  <span key={fantome.sens} className={`th-calage__ligne th-calage__ligne--${fantome.sens}`}>
                    {sheetTitle(fantome.voisin)} : {fantome.calee ? "calé" : "posé provisoirement, non calé"}
                    <button
                      type="button"
                      className="th-link"
                      onClick={() => setCalage(debuterAlignement(fantome.sens, fantome.sim))}
                    >
                      {fantome.calee ? "Recaler" : "Caler ce niveau"}
                    </button>
                  </span>
                ))
              )}
            </div>
          )}
        </div>

        <aside className="th-panel th-ws__panel" aria-label={PANELS.find((item) => item.id === panel)?.label}>
          {panel === "planche" &&
            (sheet ? (
              <SheetPanel
                key={sheet.id}
                projectId={project.id}
                sheet={sheet}
                isReference={sheet.id === reference?.id}
                onMakeReference={() => makeReference(sheet.id)}
                tool={tool}
                onTool={setTool}
                points={points}
                study={study}
                transform={raster.data?.transform ?? null}
                onStudyImported={(imported) => queryClient.setQueryData<Study>(studyQueryKey(sheet.id), imported)}
                vuesDeLaPlanche={
                  <>
                    <ListeDesVues
                      vues={vuesDeLaPlanche}
                      choisie={vueChoisie}
                      enCours={cadreVue}
                      busy={vuesEtat.busy}
                      transform={raster.data?.transform}
                      onChoisir={setVueChoisie}
                      onRedessiner={(vueId) => {
                        setVueChoisie(vueId);
                        setCalage(null);
                        setCadreVue({ vueId, premier: null });
                      }}
                      onCorriger={(vueId, correction) => void corrigerUneVue(vueId, correction)}
                      nouvelle={nouvelleVue}
                      onAjouter={() => {
                        setCalage(null);
                        setNouvelleVue(null);
                        setCadreVue({ vueId: NOUVELLE_VUE, premier: null });
                      }}
                      onCreer={(vue) => void creerUneVue(vue)}
                      onAbandonner={() => setNouvelleVue(null)}
                      onSupprimer={(vue) => void supprimerUneVue(vue)}
                    />
                    {vuesEtat.message && <p className="th-alert th-alert--ok">{vuesEtat.message}</p>}
                  </>
                }
              />
            ) : (
              <p className="th-muted">Aucune planche : déposez les plans dans « Documents ».</p>
            ))}
          {panel === "documents" && (
            <DocumentsPanel project={project} currentSheetId={sheetId} onShowSheet={(id) => setParams({ planche: id })} />
          )}
          {panel === "bibliotheque" && <LibraryPanel projectId={project.id} />}
          {panel === "infos" && <InfoPanel key={project.id} project={project} referenceId={reference?.id ?? null} onReference={makeReference} />}
          {panel === "fiche" && (
            <>
              {editionState.creation ? (
                <StudyRoomCreationPanel creation={editionState.creation} />
              ) : (
                <>
              {/* Une chose à la fois (D107) : l'étape « ponts thermiques » est une passe sur le niveau,
                  et la fiche du local n'a rien à y faire. */}
              {etape === "ponts" && shownStudy && !editionState.draft ? (
                <PontsPanel
                  catalogue={pontsCatalogue.data ?? null}
                  content={shownStudy.content}
                  selected={elementsState.selected}
                  onSelect={elementsState.select}
                  busy={elementsState.busy}
                  message={elementsState.message}
                  onOperation={elementsState.apply}
                />
              ) : (
                <>
                  {/* Un élément désigné prend tout le bandeau : voir la fiche du local par-dessus noyait
                      l'information qu'on venait justement de demander. */}
                  {!vue.ficheLocal && !selectedRoom && !elementsState.selected && etape !== "enveloppe" && (
                    <p className="th-muted">
                      Cliquez un mur ou une menuiserie sur le plan, ou ouvrez un local, pour vérifier ses parois.
                    </p>
                  )}
                  {/* Option C (D262) : la fiche de la paroi choisie, sinon les parois du local ouvert. */}
                  {etape === "enveloppe" && shownStudy && !editionState.draft &&
                    (() => {
                      const choisie = trouverParoi(shownStudy.content, paroiChoisie);
                      if (choisie) {
                        return (
                          <FicheParoi
                            content={shownStudy.content}
                            room={choisie.room}
                            paroi={choisie.paroi}
                            busy={elementsState.busy}
                            onRetour={() => setParoiChoisie(null)}
                            onValider={(couches, composant, aussi) =>
                              elementsState.gesteImmediat([
                                gesteComposition(choisie.room, choisie.paroi, couches, composant),
                                ...aussi.map((autre) => gesteComposition(autre.room, autre.paroi, couches, composant)),
                              ])
                            }
                          />
                        );
                      }
                      if (selectedRoom) return <ListeParoisDuLocal room={selectedRoom} onChoisir={setParoiChoisie} />;
                      return (
                        <p className="th-muted">
                          Cliquez une paroi sur le plan : verte, composée ; orange, proposée par le relevé de l'IA ; rouge, à
                          composer.
                        </p>
                      );
                    })()}
                  {etape === "enveloppe" && elementsState.message && <p className="th-alert">{elementsState.message}</p>}
                  {GESTES_MURS_DU_RELEVE && etape === "enveloppe" && shownStudy && !elementsState.selected && !editionState.draft && (
                    <IndeterminesDuNiveau
                      content={shownStudy.content}
                      busy={elementsState.busy}
                      onSupprimer={(refs) => elementsState.supprimer(refs, MOTIF_INDETERMINE_SUPPRIME)}
                    />
                  )}
                  {vue.ficheLocal && !elementsState.selected && (
                    <StudyRoomPanel
                      room={selectedRoom}
                      state={selectedRoom ? study?.local_states[selectedRoom.id] : undefined}
                      edition={editionState.edition}
                      coteVisee={rangCote}
                      onCote={editionState.draft ? undefined : (rang) => viserCote(rang, "fiche")}
                      validation={
                        shownStudy && selectedRoom
                          ? {
                              restants: paroisATrancher(shownStudy.content, selectedRoom).length,
                              bloque: validationBloquee,
                              busy: validation.busy || editionState.busy || elementsState.busy,
                              message: validation.message,
                              onValider: () => void validerLocal(),
                              onVoirParois: vue.listeElements === "aucune" ? () => allerEtape("enveloppe") : undefined,
                            }
                          : undefined
                      }
                      hauteur={selectedRoom ? hauteurs.data?.locaux[selectedRoom.id] : undefined}
                      coupes={hauteurs.data?.coupes}
                      onVoirCoupe={(vueId) => ouvrirLaFenetre("hauteur", vueId)}
                      onMesurerHauteur={vuesDuProjet.length ? () => ouvrirLaFenetre("hauteur") : undefined}
                    />
                  )}
                  {/* Les éléments du local, sous sa fiche et jamais en carte flottante (F4, Q8). À l'étape des
                      locaux, ils n'apparaissent que si l'un d'eux a été désigné ailleurs (D155). */}
                  {shownStudy && !editionState.draft && (vue.listeElements !== "aucune" || elementsState.selected) && (
                    <ElementPanel
                      parois={vue.listeElements === "parois" || vue.listeElements === "menuiseries"}
                      famille={vue.famille}
                      content={shownStudy.content}
                      room={selectedRoom}
                      selected={elementsState.selected}
                      onSelect={elementsState.select}
                      busy={elementsState.busy}
                      message={elementsState.message}
                      onOperation={elementsState.apply}
                      onSupprimer={(element, motif) => elementsState.supprimer([refDeElement(element)], motif)}
                      menuiseries={menuiseries.data}
                      sheetId={sheetId}
                      onMesurerBaie={vuesDuProjet.length ? () => ouvrirLaFenetre("menuiserie") : undefined}
                      onChoisirModele={(element, nom) =>
                        // D226 : un modèle de la bibliothèque, posé sur toute la baie (D224).
                        affecterModele(baieDeLElement(shownStudy.content, element), nom)
                      }
                    />
                  )}
                  {modeleMessage && !modeleAPoser && elementsState.selected && <p className="th-alert">{modeleMessage}</p>}
                  {/* D222 : la bibliothèque des modèles du projet, à l'étape des menuiseries. */}
                  {etape === "menuiseries" && token && !elementsState.selected && !editionState.draft && (
                    <section className="th-modeles-section">
                      <h2>Modèles de menuiserie du projet</h2>
                      <BibliothequeModeles
                        token={token}
                        projectId={projectId}
                        modeles={menuiseries.data?.modeles ?? []}
                        onPoser={(modele) => poserModele({ nom: modele.nom, largeur_cm: modele.largeur_cm, hauteur_m: modele.hauteur_m })}
                        onRetirer={(modele) => {
                          if (!window.confirm(`Retirer le modèle « ${modele.nom} » ? Ses ${modele.poses} menuiserie(s) perdront sa hauteur.`)) return;
                          void thermiqueApi
                            .retirerModele(token, projectId, modele.nom)
                            .then(() => queryClient.invalidateQueries({ queryKey: menuiseriesQueryKey(projectId) }));
                        }}
                      />
                    </section>
                  )}
                </>
              )}
              {(elementsState.pending > 0 || elementsState.canRedo) && (
                <div className="th-element-enregistrer">
                  {/* D105 : le geste est immédiat, seul le plan attend un recalcul. On le dit. */}
                  {elementsState.pending > 0 ? (
                    <p className="th-alert th-alert--warn">
                      {elementsState.pending} correction{elementsState.pending > 1 ? "s" : ""} en attente —
                      recalculez pour les voir sur le plan.
                    </p>
                  ) : (
                    <p className="th-alert">Aucune correction en attente. Une action peut encore être rétablie.</p>
                  )}
                  <div className="th-inline">
                    <button
                      type="button"
                      className="po2-button po2-button--ghost"
                      disabled={elementsState.busy || !elementsState.canUndo}
                      onClick={elementsState.undo}
                    >
                      Annuler (Ctrl+Z)
                    </button>
                    <button
                      type="button"
                      className="po2-button po2-button--ghost"
                      disabled={elementsState.busy || !elementsState.canRedo}
                      onClick={elementsState.redo}
                    >
                      Rétablir
                    </button>
                    <button
                      type="button"
                      className="po2-button po2-button--primary"
                      disabled={elementsState.busy || elementsState.pending === 0}
                      onClick={elementsState.save}
                    >
                      Enregistrer les corrections
                    </button>
                    <button
                      type="button"
                      className="po2-button po2-button--ghost"
                      disabled={elementsState.busy || elementsState.pending === 0}
                      onClick={elementsState.recompute}
                    >
                      {elementsState.busy ? "Recalcul…" : "Recalculer le plan"}
                    </button>
                    <button type="button" className="th-link" disabled={elementsState.busy || elementsState.pending === 0} onClick={elementsState.cancel}>
                      Tout annuler
                    </button>
                  </div>
                </div>
              )}
                </>
              )}
            </>
          )}
        </aside>
      </div>
      {token && vueOuverte && plancheOuverte && (
        <FenetreCoupe
          token={token}
          vue={vueOuverte}
          vues={vuesDuProjet}
          onChoisirVue={(vueId) => {
            setCoupeOuverte(vueId);
            setDerniereVue(vueId);
          }}
          planche={plancheOuverte}
          planSheetId={sheetId}
          menuiseries={menuiseries.data}
          outilPrefere={etape === "menuiseries" ? "menuiserie" : etape === "locaux" ? "hauteur" : undefined}
          outilArme={outilArme}
          onPoserHauteur={sheet?.nature === "plan" && study ? poserHauteur : undefined}
          onPoserModele={sheet?.nature === "plan" && study ? poserModele : undefined}
          onClose={() => setCoupeOuverte(null)}
        />
      )}
    </div>
  );
}
