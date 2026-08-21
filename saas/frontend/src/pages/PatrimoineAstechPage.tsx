// Écran unique du chantier « référentiel patrimoine historique (ASTECH) ».
//
// Décision Q7 : un seul écran porte tout le parcours, plutôt que d'éclater
// « valider les noms » et « localiser sur la carte » sur deux pages.
//   - colonne gauche : la file des biens ASTECH, filtrable par statut ;
//   - colonne droite : la carte, avec les bâtiments Po2 et le bien ASTECH
//     sélectionné en violet, déplaçable ;
//   - panneau d'action : valider le candidat proposé, ou attribuer un bâtiment IGN.
//
// Le bouton « Attribuer IGN » réutilise tel quel l'attachement existant de
// /buildings/list (POST /buildings/{id}/ign-attachment) : le bien ASTECH n'a pas
// son propre moteur de géocodage, il pilote celui du bâtiment rattaché.
import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  BuildingPortfolioMap,
  type LegacyMapPoint,
  type LocalMapPoint,
} from "../components/BuildingPortfolioMap";
import { useAuth } from "../providers/AuthProvider";
import {
  attachBuildingIgnRequest,
  computeLegacyCandidates,
  confirmLegacyProposals,
  fetchAllLocals,
  fetchBuildings,
  convertLegacyAssetToLocal,
  createBuildingRequest,
  createLegacyAssetFromBuilding,
  createLegacyAssetFromLocal,
  deleteLegacyImports,
  downloadLegacyExport,
  previewLegacyExport,
  reclassifyBuildingRequest,
  reclassifyLocalRequest,
  fetchFreeAddressLookup,
  fetchIgnBuildingsAtPoint,
  fetchLegacyAssets,
  fetchLegacyCounts,
  importLegacyAstechFile,
  moveBuildingRequest,
  resetLegacyEverything,
  resetLegacyLinks,
  updateBuildingRequest,
  updateLegacyAsset,
  updateLocalRequest,
  type Building,
  type GeoJsonFeature,
  type GeoJsonFeatureCollection,
  type LegacyAsset,
  type Local,
} from "../lib/api";

const STATUS_LABEL: Record<string, string> = {
  "": "Tous",
  a_traiter: "À traiter",
  propose: "À confirmer",
  lie: "Rattaché",
  hors_perimetre: "Hors périmètre",
  a_creer: "À créer",
  ignore: "Ignoré",
};

// « » = aucun filtre : indispensable, sinon la liste semble incomplète alors qu'elle
// est simplement filtrée sur « À traiter ».
const STATUS_ORDER = ["", "a_traiter", "propose", "lie", "a_creer", "hors_perimetre", "ignore"] as const;

// Centre de Sète : point de départ d'un bien jamais localisé, que l'utilisateur
// fait ensuite glisser à la bonne place.
const DEFAULT_LAT = 43.4028;
const DEFAULT_LON = 3.6928;

// La plateforme est en thème sombre (`:root` : texte #e2e8f0 sur fond #0f172a).
// Toute couleur de fond posée ici doit donc venir avec sa couleur de texte, sinon
// le texte hérité (clair) devient invisible.
const SURFACE = "rgba(30, 41, 59, 0.72)";
const BORDER = "1px solid rgba(148, 163, 184, 0.2)";
const TEXT = "#e2e8f0";
const TEXT_MUTED = "#94a3b8";

const card: CSSProperties = {
  border: BORDER,
  borderRadius: 12,
  padding: "10px 12px",
  background: SURFACE,
  color: TEXT,
};
const btnPrimary: CSSProperties = {
  border: "1px solid #1d4ed8",
  background: "#2563eb",
  color: "#fff",
  borderRadius: 7,
  padding: "6px 12px",
  fontSize: 13,
  cursor: "pointer",
};
const btnSecondary: CSSProperties = {
  border: "1px solid rgba(148, 163, 184, 0.35)",
  background: "transparent",
  color: TEXT,
  borderRadius: 7,
  padding: "6px 12px",
  fontSize: 13,
  cursor: "pointer",
};
const input: CSSProperties = {
  border: "1px solid rgba(148, 163, 184, 0.3)",
  background: "rgba(15, 23, 42, 0.6)",
  color: TEXT,
  borderRadius: 7,
  padding: "6px 10px",
  fontSize: 13,
  width: "100%",
};

function scoreColor(score: number | null): string {
  if (score === null) return TEXT_MUTED;
  if (score >= 0.9) return "#34d399";
  if (score >= 0.7) return "#fbbf24";
  return "#f87171";
}

// Pastille de statut affichée sur chaque ligne de la file. Sans elle, le filtre
// « Tous » ne dit pas ce qui est déjà traité : l'opératrice ne voit pas ce qui lui
// reste à faire, d'autant que les biens sans position n'apparaissent pas sur la carte.
const STATUS_PILL: Record<string, { label: string; color: string; background: string }> = {
  a_traiter: { label: "à traiter", color: "#fca5a5", background: "rgba(248, 113, 113, 0.16)" },
  propose: { label: "à confirmer", color: "#fbbf24", background: "rgba(251, 191, 36, 0.16)" },
  lie: { label: "traité", color: "#4ade80", background: "rgba(34, 197, 94, 0.18)" },
  a_creer: { label: "à créer dans ASTECH", color: "#7dd3fc", background: "rgba(56, 189, 248, 0.16)" },
  ignore: { label: "ignoré", color: "#94a3b8", background: "rgba(148, 163, 184, 0.16)" },
  hors_perimetre: { label: "hors périmètre", color: "#94a3b8", background: "rgba(148, 163, 184, 0.16)" },
};

const pillStyle: CSSProperties = {
  fontSize: 10,
  padding: "1px 6px",
  borderRadius: 999,
  whiteSpace: "nowrap",
};

/**
 * Filtres de second niveau, cumulables entre eux et avec le filtre de statut.
 *
 * Chacun découpe un tas réel, mesuré sur les 444 biens de la collectivité — pas une
 * catégorie théorique :
 * - 364 biens n'apparaissent pas sur la carte et ne se traitent donc que d'ici ;
 * - 217 ont un candidat que le moteur propose (validation rapide) contre 150 qui
 *   n'ont aucune piste et demandent un rattachement manuel complet ;
 * - 44 sont sortis du parc ASTECH, dont 42 dans le tas manuel : les mettre de côté
 *   allège d'autant le travail ;
 * - 103 n'ont aucune adresse dans ASTECH, c'est le tas le plus coûteux.
 */
const REFINE_FILTERS: {
  key: string;
  label: string;
  title: string;
  test: (asset: LegacyAsset, isMappable: boolean) => boolean;
}[] = [
  {
    key: "hors_carte",
    label: "Absent de la carte",
    title: "Ni position ni bâtiment localisé : ces biens ne se traitent que depuis cette liste.",
    test: (_asset, isMappable) => !isMappable,
  },
  {
    key: "candidat",
    label: "Candidat à valider",
    title: "Le moteur propose un bâtiment : il reste à le confirmer ou à le corriger.",
    test: (asset) => asset.building_id == null && asset.candidate_building_id != null,
  },
  {
    key: "sans_candidat",
    label: "Aucune piste",
    title: "Aucun nom approchant trouvé : rattachement entièrement manuel.",
    test: (asset) => asset.building_id == null && asset.candidate_building_id == null,
  },
  {
    key: "sans_adresse",
    label: "Sans adresse ASTECH",
    title: "Le fichier historique ne donne aucune voie : le nom est le seul point de départ.",
    test: (asset) => !(asset.source_libelvoie ?? "").trim(),
  },
  {
    key: "en_service",
    label: "En service",
    title: "Exclut les biens sortis du parc ASTECH (HORSPARC = O).",
    test: (asset) => asset.horsparc !== "O",
  },
  {
    key: "hors_parc",
    label: "Sorti du parc",
    title: "Biens désaffectés côté ASTECH : souvent inutile de les géolocaliser.",
    test: (asset) => asset.horsparc === "O",
  },
];

function assetLabel(asset: LegacyAsset): string {
  return asset.nomcourt || asset.designation || asset.code_bien;
}

function assetAddress(asset: LegacyAsset): string | null {
  const parts = [
    asset.source_norue && asset.source_norue !== "0" ? asset.source_norue : null,
    asset.source_libelvoie,
  ].filter(Boolean);
  const line = parts.join(" ");
  const city = asset.source_ville ? `, ${asset.source_ville}` : "";
  return line ? `${line}${city}` : null;
}

export default function PatrimoineAstechPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  // Une ref par ligne : permet d'amener a l'ecran le bien selectionne depuis la carte.
  const rowRefs = useRef<Map<number, HTMLButtonElement>>(new Map());

  const [statusFilter, setStatusFilter] = useState<string>("a_traiter");
  // Filtres de second niveau, cumulables avec le statut. Ils découpent la charge de
  // travail réelle : « à traiter » compte 338 biens, mais 217 ont un candidat à
  // valider en un clic et 150 n'ont rien du tout. Sans ce tri, l'opératrice ne peut
  // pas commencer par le tas rapide.
  const [refineKeys, setRefineKeys] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [attachMode, setAttachMode] = useState(false);
  const [attachSelection, setAttachSelection] = useState<GeoJsonFeature[]>([]);
  // Rayon de recherche IGN autour du point. Plafonné à 1,5 km côté serveur : au-delà,
  // le WFS renvoie des milliers de polygones et la carte devient inutilisable.
  const [attachRadius, setAttachRadius] = useState(300);
  // Sélecteur manuel de bâtiment Po2 : indispensable quand le moteur ne propose
  // rien (aucun nom approchant) ou quand sa proposition est fausse.
  const [pickerOpen, setPickerOpen] = useState(false);
  const [buildingSearch, setBuildingSearch] = useState("");
  // Bâtiment Po2 consulté depuis la carte. C'est aussi le seul rendu déplaçable :
  // un seul à la fois, pour ne pas bouger un voisin par mégarde.
  const [inspectedBuildingId, setInspectedBuildingId] = useState<number | null>(null);
  // Centre courant de la carte : permet de poser le point d'un bien là où l'utilisateur
  // regarde, au lieu du centre de Sète — souvent hors écran quand on a zoomé.
  const [mapCenter, setMapCenter] = useState<{ lat: number; lon: number } | null>(null);
  // La carte suit-elle le filtre de la liste ? Non par défaut : 338 biens sur 444 n'ont
  // aucune position et le filtre initial est « À traiter », donc la carte se retrouvait
  // vide au chargement — au point de passer pour une panne.
  const [mapFollowsFilter, setMapFollowsFilter] = useState(false);
  // Passer au bien suivant apres chaque decision. Sur 380 biens, c'est le geste qu'on
  // repete le plus : sans cela il faut revenir cliquer la ligne suivante dans la file
  // apres chaque validation.
  const [autoAdvance, setAutoAdvance] = useState(true);
  // Les locaux Po2 sont affichés par défaut : 505 sur 626 ont des coordonnées et la
  // carte les ignorait complètement, alors qu'un CODE_BIEN ASTECH désigne souvent un
  // local. La bascule reste offerte, un parc dense pouvant devenir illisible.
  const [showLocals, setShowLocals] = useState(true);
  // Local Po2 consulte depuis la carte. Symetrique de `inspectedBuildingId` : cliquer
  // un local RATTACHAIT aussitot le bien selectionne, alors que cliquer un batiment ne
  // fait que consulter. Deux gestes identiques aux consequences opposees.
  const [inspectedLocalId, setInspectedLocalId] = useState<number | null>(null);
  const [localNameDraft, setLocalNameDraft] = useState("");
  // Noms en cours de saisie. Enregistrement explicite : la sauvegarde à la sortie du
  // champ partait au moindre clic ailleurs, sans qu'on sache si elle avait eu lieu.
  const [assetNameDraft, setAssetNameDraft] = useState("");
  const [buildingNameDraft, setBuildingNameDraft] = useState("");

  const countsQuery = useQuery({
    queryKey: ["legacy-counts"],
    queryFn: () => fetchLegacyCounts(token!),
    enabled: !!token,
  });

  const assetsQuery = useQuery({
    queryKey: ["legacy-assets", statusFilter, search],
    queryFn: () =>
      fetchLegacyAssets(token!, {
        status: statusFilter || undefined,
        search: search.trim() || undefined,
      }),
    enabled: !!token,
  });

  const localsQuery = useQuery({
    queryKey: ["buildings", "locals"],
    queryFn: () => fetchAllLocals(token!),
    enabled: !!token,
  });

  const buildingsQuery = useQuery({
    queryKey: ["buildings"],
    queryFn: () => fetchBuildings(token!),
    enabled: !!token,
  });

  // La carte doit montrer TOUS les biens localisés, quel que soit leur statut : la
  // liste de gauche est filtrée (« À traiter » par défaut) alors que la carte sert de
  // vue d'ensemble. Filtrer sur « Rattaché » ne laissait apparaître qu'une poignée de
  // points dès que les statuts changeaient.
  const linkedAssetsQuery = useQuery({
    queryKey: ["legacy-assets", "carte"],
    queryFn: () => fetchLegacyAssets(token!, { limit: 2000 }),
    enabled: !!token,
  });

  const assets = useMemo(() => assetsQuery.data ?? [], [assetsQuery.data]);
  const buildings = useMemo(() => buildingsQuery.data ?? [], [buildingsQuery.data]);
  // Tous les biens affichables par l'ecran : la liste filtree ET les biens deja
  // rattaches (montres en permanence sur la carte). Sans cette union, cliquer un point
  // rattache sur la carte ne remplissait pas le panneau, le bien etant absent du filtre.
  const knownAssets = useMemo(() => {
    const byId = new Map<number, LegacyAsset>();
    for (const asset of linkedAssetsQuery.data ?? []) byId.set(asset.id, asset);
    for (const asset of assets) byId.set(asset.id, asset);
    return byId;
  }, [assets, linkedAssetsQuery.data]);

  const selected = useMemo(
    () => (selectedId != null ? knownAssets.get(selectedId) ?? null : null),
    [knownAssets, selectedId],
  );

  const buildingsById = useMemo(() => {
    const index = new Map<number, Building>();
    for (const building of buildings) index.set(building.id, building);
    return index;
  }, [buildings]);

  const locals = useMemo(() => localsQuery.data ?? [], [localsQuery.data]);
  const localsById = useMemo(() => {
    const index = new Map<number, (typeof locals)[number]>();
    for (const local of locals) index.set(local.id, local);
    return index;
  }, [locals]);
  const inspectedBuilding = useMemo(
    () => (inspectedBuildingId != null ? buildingsById.get(inspectedBuildingId) ?? null : null),
    [buildingsById, inspectedBuildingId],
  );

  const inspectedLocal = useMemo(
    () => (inspectedLocalId != null ? localsById.get(inspectedLocalId) ?? null : null),
    [inspectedLocalId, localsById],
  );

  // Le brouillon suit le local consulté, sinon on éditerait le nom du précédent.
  useEffect(() => {
    setLocalNameDraft(inspectedLocal?.nom_local ?? "");
  }, [inspectedLocal]);

  // Pendant de `addToAstechMutation` pour un local : une entite Po2 absente du
  // referentiel de la collectivite doit remonter dans le fichier de retour, sinon les
  // deux referentiels ne convergeront jamais (Q13). Seuls les batiments le pouvaient.
  const addLocalToAstechMutation = useMutation({
    mutationFn: (localId: number) => createLegacyAssetFromLocal(token!, localId),
    onSuccess: (asset) => {
      setFlash(
        `« ${assetLabel(asset)} » ajouté à la liste ASTECH comme bien à créer. ` +
          "Il sortira dans le fichier de retour sans code bien : c'est ASTECH qui lui en attribuera un.",
      );
      setStatusFilter("a_creer");
      setSelectedId(asset.id);
      invalidate();
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  /**
   * Change la TYPOLOGIE d'une entité Po2 : un local devient un bâtiment, ou l'inverse.
   *
   * L'import du patrimoine a classé en « local » des entités qui sont en réalité des
   * bâtiments. Le service transporte désormais adresse, position, cadastre ET les biens
   * ASTECH rattachés — sans quoi le reclassement dépouillait l'entité et orphelinait
   * les rattachements.
   */
  const reclassifyMutation = useMutation({
    mutationFn: (variables:
      | { kind: "localToBuilding"; local: Local }
      | { kind: "buildingToLocal"; building: Building; parentId: number }) =>
      variables.kind === "localToBuilding"
        ? reclassifyLocalRequest(token!, variables.local.building_id, variables.local.id, {
            target_type: "building",
          })
        : reclassifyBuildingRequest(token!, variables.building.id, {
            target_type: "local",
            target_building_id: variables.parentId,
          }),
    onSuccess: (result) => {
      setFlash(
        result.entity_type === "building"
          ? "Local promu en bâtiment Po2. Son adresse, sa position et ses biens ASTECH l'ont suivi."
          : "Bâtiment devenu un local. Son adresse, sa position et ses biens ASTECH l'ont suivi.",
      );
      setInspectedLocalId(result.entity_type === "local" ? result.entity_id : null);
      setInspectedBuildingId(result.entity_type === "building" ? result.entity_id : null);
      void queryClient.invalidateQueries({ queryKey: ["buildings"] });
      invalidate();
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  const renameLocalMutation = useMutation({
    mutationFn: (variables: { local: Local; nom: string }) =>
      updateLocalRequest(token!, variables.local.building_id, variables.local.id, {
        nom_local: variables.nom,
      }),
    onSuccess: (local) => {
      setFlash(`Local renommé en « ${local.nom_local} ».`);
      void queryClient.invalidateQueries({ queryKey: ["buildings"] });
      invalidate();
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  // Le bâtiment que pilote l'écran : celui déjà rattaché, sinon le candidat proposé.
  const targetBuilding = useMemo(() => {
    if (!selected) return null;
    const id = selected.building_id ?? selected.candidate_building_id;
    return id != null ? buildingsById.get(id) ?? null : null;
  }, [buildingsById, selected]);

  const localsOfTarget = useMemo(
    () => (targetBuilding ? locals.filter((local) => local.building_id === targetBuilding.id) : []),
    [locals, targetBuilding],
  );

  // Les autres biens ASTECH qui visent le même bâtiment porteur. Un bâtiment peut en
  // héberger plusieurs (le club et ses salles, l'école et son restaurant) : montrer la
  // fratrie est le seul moyen de voir si la structure est juste — un seul bien doit
  // désigner le bâtiment entier, les autres sont des locaux.
  const siblingAssets = useMemo(() => {
    if (!selected?.building_id) return [];
    return [...knownAssets.values()]
      .filter((asset) => asset.building_id === selected.building_id)
      .sort((a, b) => {
        // Le bâtiment entier d'abord, ses locaux ensuite : c'est la hiérarchie réelle.
        if ((a.target_type === "local") !== (b.target_type === "local")) {
          return a.target_type === "local" ? 1 : -1;
        }
        return assetLabel(a).localeCompare(assetLabel(b));
      });
  }, [knownAssets, selected]);

  const invalidate = () => {
    // La cle ["legacy-assets"] couvre aussi ["legacy-assets", "lie"] : la couche
    // violette de la carte se met a jour des qu'un rattachement change.
    void queryClient.invalidateQueries({ queryKey: ["legacy-assets"] });
    void queryClient.invalidateQueries({ queryKey: ["legacy-counts"] });
  };

  // --- Bâtiments Po2 indistinguables ------------------------------------------
  // Deux pièges constatés en prod sur le groupe scolaire Anatole France :
  //   - plusieurs bâtiments portent EXACTEMENT le même nom, parce que l'attribution
  //     IGN les a nommés depuis la zone qui les englobe et non depuis le bâtiment ;
  //   - deux bâtiments Po2 pointent sur le MÊME bâtiment IGN. Ce n'est PAS forcément un
  //     doublon : vérifié en prod, le restaurant scolaire et la maternelle Lacore
  //     partagent légitimement une seule empreinte IGN. On signale, on ne conclut pas.
  // Dans les deux cas la référente ne peut pas choisir à l'aveugle : on le lui dit,
  // et l'adresse devient le seul critère qui les sépare.
  const buildingAmbiguities = useMemo(() => {
    const byName = new Map<string, number[]>();
    const byIgn = new Map<string, number[]>();
    for (const building of buildings) {
      const name = (building.nom_batiment ?? "").trim().toLowerCase();
      if (name) byName.set(name, [...(byName.get(name) ?? []), building.id]);
      const ignId = (building.ign_id ?? "").trim();
      if (ignId) byIgn.set(ignId, [...(byIgn.get(ignId) ?? []), building.id]);
    }
    const result = new Map<number, { sameName: number; sameIgn: number }>();
    for (const building of buildings) {
      const name = (building.nom_batiment ?? "").trim().toLowerCase();
      const ignId = (building.ign_id ?? "").trim();
      const sameName = name ? (byName.get(name)?.length ?? 1) : 1;
      const sameIgn = ignId ? (byIgn.get(ignId)?.length ?? 1) : 1;
      if (sameName > 1 || sameIgn > 1) result.set(building.id, { sameName, sameIgn });
    }
    return result;
  }, [buildings]);

  const buildingMatches = useMemo(() => {
    const needle = buildingSearch.trim().toLowerCase();
    const pool = needle
      ? buildings.filter((building) =>
          `${building.nom_batiment ?? ""} ${building.adresse_reconstituee ?? ""}`
            .toLowerCase()
            .includes(needle),
        )
      : buildings;
    return [...pool]
      .sort((a, b) => (a.nom_batiment ?? "").localeCompare(b.nom_batiment ?? ""))
      .slice(0, 40);
  }, [buildingSearch, buildings]);

  const importMutation = useMutation({
    mutationFn: (file: File) => importLegacyAstechFile(token!, file),
    onSuccess: (result) => {
      // Un fichier dont AUCUN code ne recoupe l'existant signale un changement de
      // codification cote ASTECH : les deux jeux cohabitent alors au lieu de se mettre
      // a jour. Constate le 2026-08-20 — 444 + 380 = 824 biens, sans explication a
      // l'ecran. On le dit, et on nomme le bouton qui repare.
      setFlash(
        (result.codes_disjoints
          ? `⚠️ Erreur : ce fichier n'a AUCUN code bien en commun avec les ${result.existing_before} ` +
            "biens déjà présents — la codification ASTECH a changé. Les deux jeux cohabitent " +
            "désormais. Utilise « 3 · Supprimer les biens ASTECH » puis réimporte ce fichier. — "
          : "") +
          `Import « ${result.sheet_name} » (${result.columns} colonnes) : ${result.created} bien(s) créé(s), ` +
          `${result.updated} mis à jour, ${result.skipped_scope} écarté(s), ` +
          `${result.out_of_scope_commune} hors périmètre.`,
      );
      invalidate();
    },
    onError: (error) => setFlash(`Erreur d'import : ${(error as Error).message}`),
  });

  const candidatesMutation = useMutation({
    mutationFn: () => computeLegacyCandidates(token!, true),
    onSuccess: (result) => {
      setFlash(
        `Reconnaissance : ${result.auto_linked} rattachement(s) évident(s), ` +
          `${result.proposed} candidat(s) proposé(s) sur ${result.scanned} bien(s).` +
          (result.repaired
            ? ` ${result.repaired} bien(s) pointaient vers un bâtiment supprimé et sont repassés à traiter.`
            : ""),
      );
      invalidate();
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  const confirmMutation = useMutation({
    mutationFn: () => confirmLegacyProposals(token!),
    onSuccess: (result) => {
      setFlash(`${result.confirmed} rattachement(s) confirmé(s).`);
      invalidate();
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  /**
   * Coupe le lien d'un bien avec Po2, quel que soit son niveau (bâtiment ou local) et
   * quel que soit son statut.
   *
   * Le bien garde sa position : c'est voulu, elle reste un point de travail utilisable.
   * C'est aussi pourquoi la carte l'écarte visuellement du bâtiment une fois détaché —
   * sinon il resterait pile dessous et le détachement semblerait sans effet.
   */
  const saveAssetName = () => {
    const value = assetNameDraft.trim();
    if (!selected || !value || value === assetLabel(selected)) return;
    updateMutation.mutate(
      { id: selected.id, payload: { designation: value } },
      { onSuccess: () => setFlash(`Bien ASTECH renommé en « ${value} ».`) },
    );
  };

  const saveBuildingName = () => {
    const value = buildingNameDraft.trim();
    if (!inspectedBuilding || !value || value === (inspectedBuilding.nom_batiment ?? "")) return;
    renameBuildingMutation.mutate({ id: inspectedBuilding.id, nom: value });
  };

  /**
   * Passe au bien suivant de la file, si l'option est active.
   *
   * Appelé après une décision (valider, écarter, ignorer). Le bien traité vient de
   * quitter le filtre courant : « suivant » est donc celui qui occupe désormais sa
   * place, sinon le précédent quand on était en fin de liste.
   */
  const goToNextAsset = (fromId: number) => {
    if (!autoAdvance) return;
    const index = visibleAssets.findIndex((asset) => asset.id === fromId);
    if (index < 0) return;
    const next = visibleAssets[index + 1] ?? visibleAssets[index - 1] ?? null;
    setSelectedId(next ? next.id : null);
  };

  const detachAsset = (assetId: number) => {
    updateMutation.mutate({
      id: assetId,
      payload: { clear_building: true, status: "a_traiter" },
    });
    setFlash("Bien détaché : il repasse « à traiter » et s'écarte du bâtiment sur la carte.");
  };

  const toLocalMutation = useMutation({
    mutationFn: (assetId: number) => convertLegacyAssetToLocal(token!, assetId),
    onSuccess: (asset) => {
      setFlash(
        `« ${assetLabel(asset)} » est désormais un local du bâtiment. ` +
          "Il garde l'adresse et le cadastre du bâtiment pour le retour ASTECH.",
      );
      // La liste des locaux est indexee sous ["buildings", "locals"] : invalider
      // ["locals"] ne l'atteindrait pas, et le local qu'on vient de creer n'apparaitrait
      // pas dans le menu « Preciser un local ».
      void queryClient.invalidateQueries({ queryKey: ["buildings"] });
      invalidate();
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  /**
   * Pose le point du bien sur SON adresse ASTECH, celle du fichier de la collectivité.
   *
   * Cas visé : l'adresse ASTECH est la bonne et celle du bâtiment Po2 est fausse. Le
   * bien étant rattaché, déplacer son point emmène aussi le bâtiment et recalcule
   * l'adresse des deux — c'est ce qui aligne Po2 sur ASTECH.
   *
   * Règle de sûreté (§11.2) : sans numéro de voirie, le géocodeur rend le milieu de la
   * voie. On le DIT au lieu de laisser croire à une position exacte, et aucun numéro
   * n'est inventé : c'est « Attribuer IGN » qui le relèvera dans le DGFIP.
   */
  const geocodeAstechMutation = useMutation({
    mutationFn: async (asset: LegacyAsset) => {
      const address = assetAddress(asset);
      if (!address) throw new Error("Ce bien n'a pas d'adresse dans le fichier ASTECH.");
      const lookup = await fetchFreeAddressLookup(token!, address, {
        citycode: asset.source_commune,
        skip_ign_buildings: true,
      });
      if (lookup.lat == null || lookup.lon == null) {
        throw new Error(`Adresse ASTECH introuvable : « ${address} ».`);
      }
      await updateLegacyAsset(token!, asset.id, {
        latitude: lookup.lat,
        longitude: lookup.lon,
      });
      return lookup;
    },
    onSuccess: (lookup) => {
      const properties = (lookup.geocoder?.properties ?? {}) as Record<string, unknown>;
      const found = String(properties.label ?? "adresse inconnue");
      // Toujours annoncer CE QUI A ÉTÉ TROUVÉ, pas seulement qu'on a trouvé. Vérifié
      // sur les données réelles : « LE BARROU » (un lieu-dit du fichier ASTECH) est
      // géocodé en « Rue Marceau », une voie sans aucun rapport. Sans le libellé sous
      // les yeux, l'utilisateur poserait le point au mauvais endroit en toute confiance.
      setFlash(
        properties.type === "housenumber"
          ? `Point posé sur « ${found} ». Vérifie qu'il tombe bien sur le bâtiment.`
          : `Trouvé : « ${found} » — au milieu de la voie, faute de numéro dans ASTECH. ` +
            "⚠️ Vérifie que c'est bien la bonne rue : sur un lieu-dit, le géocodeur retombe " +
            "parfois sur une voie approchante. Fais glisser le point sur le bon bâtiment, " +
            "puis « Attribuer IGN » relèvera le numéro exact — aucun numéro n'est inventé.",
      );
      void queryClient.invalidateQueries({ queryKey: ["buildings"] });
      invalidate();
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  const renameBuildingMutation = useMutation({
    mutationFn: (variables: { id: number; nom: string }) =>
      updateBuildingRequest(token!, variables.id, { nom_batiment: variables.nom }),
    onSuccess: (building) => {
      setFlash(`Bâtiment Po2 renommé en « ${building.nom_batiment} ».`);
      void queryClient.invalidateQueries({ queryKey: ["buildings"] });
      invalidate();
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  /**
   * Télécharge le classeur de retour ASTECH.
   *
   * Le fichier ne contient que les rattachements **validés par un humain** : une
   * proposition du moteur n'a rien à faire dans le référentiel de la collectivité tant
   * que personne ne l'a confirmée. Les autres biens ressortent en feuille « à vérifier »
   * avec leur motif, ce qui rend le compte lisible plutôt que silencieux.
   */
  const exportMutation = useMutation({
    mutationFn: () => downloadLegacyExport(token!),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
      setFlash(
        `Fichier « ${filename} » téléchargé. Relis la feuille « Traçabilité » avant de le ` +
          "réinjecter dans ASTECH : elle liste chaque valeur remplacée.",
      );
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  // `countsQuery.data` plutôt que `counts` : ce dernier est déclaré plus bas dans le
  // composant, l'utiliser ici lèverait une erreur d'initialisation.
  const exportPreviewQuery = useQuery({
    queryKey: ["legacy-export-preview", countsQuery.data?.lie, countsQuery.data?.a_creer],
    queryFn: () => previewLegacyExport(token!),
    enabled: !!token && (countsQuery.data?.total ?? 0) > 0,
  });

  const resetAllMutation = useMutation({
    mutationFn: () => resetLegacyEverything(token!),
    onSuccess: (result) => {
      setFlash(
        `${result.reset} bien(s) remis à zéro. La carte n'affiche plus que les bâtiments Po2 : ` +
          "les biens ASTECH n'ont pas de coordonnées propres. Clique « 2. Reconnaître les noms » " +
          "pour les y ramener.",
      );
      setSelectedId(null);
      setInspectedBuildingId(null);
      invalidate();
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  const deleteImportsMutation = useMutation({
    mutationFn: () => deleteLegacyImports(token!),
    onSuccess: (result) => {
      setFlash(
        `${result.assets_deleted} bien(s) ASTECH supprimé(s). ` +
          "Tu peux réimporter un export avec « 1. Importer un export ASTECH ».",
      );
      setSelectedId(null);
      setInspectedBuildingId(null);
      invalidate();
    },
    onError: (error) => setFlash(`Erreur de suppression : ${(error as Error).message}`),
  });

  const resetLinksMutation = useMutation({
    mutationFn: () => resetLegacyLinks(token!),
    onSuccess: (result) => {
      setFlash(
        `${result.cleared} rapprochement(s) supprimé(s). Les biens sont repassés « à traiter » : ` +
          "relance « 2. Reconnaître les noms » pour repartir du référentiel Po2 actuel.",
      );
      setSelectedId(null);
      invalidate();
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  const moveBuildingMutation = useMutation({
    mutationFn: (variables: { buildingId: number; lat: number; lon: number }) =>
      moveBuildingRequest(token!, variables.buildingId, variables.lat, variables.lon),
    onSuccess: (building) => {
      setFlash(`« ${building.nom_batiment} » déplacé, adresse mise à jour.`);
      void queryClient.invalidateQueries({ queryKey: ["buildings"] });
      invalidate();
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  const updateMutation = useMutation({
    mutationFn: (variables: { id: number; payload: Parameters<typeof updateLegacyAsset>[2] }) =>
      updateLegacyAsset(token!, variables.id, variables.payload),
    onSuccess: () => invalidate(),
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  // Bâtiment Po2 absent du référentiel de la collectivité : il doit remonter dans le
  // réexport pour y être créé, sinon les deux référentiels ne convergeront jamais (Q13).
  const addToAstechMutation = useMutation({
    mutationFn: (buildingId: number) => createLegacyAssetFromBuilding(token!, buildingId),
    onSuccess: (asset) => {
      setFlash(
        `« ${assetLabel(asset)} » ajouté à la liste ASTECH comme bien à créer. ` +
          "Il sortira dans le fichier de retour sans code bien : c'est ASTECH qui lui en attribuera un.",
      );
      setStatusFilter("a_creer");
      setSelectedId(asset.id);
      invalidate();
    },
    onError: (error) => setFlash(`Erreur : ${(error as Error).message}`),
  });

  // --- Attribution IGN : réutilise le géocodage et l'attachement existants -----
  const attachAddress = useMemo(() => {
    if (!targetBuilding) return null;
    if (targetBuilding.adresse_reconstituee) return targetBuilding.adresse_reconstituee;
    const parts = [targetBuilding.numero_voirie, targetBuilding.nature_voie, targetBuilding.nom_voie]
      .filter(Boolean)
      .join(" ");
    return parts ? `${parts}, ${targetBuilding.nom_commune}` : null;
  }, [targetBuilding]);

  // Deux façons de trouver les bâtiments IGN :
  //  - le bien a un point posé sur la carte -> on cherche AUTOUR DE CE POINT.
  //    C'est le cas normal ici : le fichier ASTECH n'a pas d'adresse exploitable
  //    (n° de voirie absent 9 fois sur 10, cadastre vide), donc le géocodage
  //    d'adresse ne donne rien. L'utilisateur pose le point, on cherche là.
  //  - sinon, repli sur le géocodage de l'adresse du bâtiment Po2 rattaché.
  const pointCenter = useMemo(() => {
    if (selected?.latitude != null && selected?.longitude != null) {
      return { lat: selected.latitude, lon: selected.longitude };
    }
    if (targetBuilding?.latitude != null && targetBuilding?.longitude != null) {
      return { lat: targetBuilding.latitude, lon: targetBuilding.longitude };
    }
    return null;
  }, [selected, targetBuilding]);

  const pointLookupQuery = useQuery({
    queryKey: ["legacy-ign-at-point", pointCenter?.lat, pointCenter?.lon, attachRadius],
    queryFn: () => fetchIgnBuildingsAtPoint(token!, pointCenter!.lat, pointCenter!.lon, attachRadius),
    enabled: !!token && attachMode && pointCenter !== null,
  });

  const addressLookupQuery = useQuery({
    queryKey: ["legacy-attach-lookup", targetBuilding?.id, attachAddress],
    queryFn: () => fetchFreeAddressLookup(token!, attachAddress as string),
    enabled: !!token && attachMode && pointCenter === null && Boolean(attachAddress),
  });

  const attachLookupQuery = pointCenter !== null ? pointLookupQuery : addressLookupQuery;

  const attachMutation = useMutation({
    mutationFn: () =>
      attachBuildingIgnRequest(token!, targetBuilding!.id, {
        selected_features: attachSelection,
        lat: attachLookupQuery.data?.lat ?? null,
        lon: attachLookupQuery.data?.lon ?? null,
      }),
    onSuccess: (building) => {
      setFlash(
        `Bâtiment IGN attribué à « ${building.nom_batiment ?? building.id} » : adresse et cadastre récupérés.`,
      );
      setAttachMode(false);
      setAttachSelection([]);
      void queryClient.invalidateQueries({ queryKey: ["buildings"] });
      invalidate();
    },
    onError: (error) => setFlash(`Erreur d'attribution IGN : ${(error as Error).message}`),
  });

  // Créer le bâtiment Po2 manquant : sans lui, il n'y a rien à quoi attacher l'IGN.
  // On part du nom ASTECH et de la position posée sur la carte.
  const createBuildingMutation = useMutation({
    mutationFn: async () => {
      const point = pointCenter ?? { lat: DEFAULT_LAT, lon: DEFAULT_LON };
      const building = await createBuildingRequest(token!, {
        nom_batiment: assetLabel(selected!),
        nom_commune: selected!.source_ville || "SETE",
        code_postal: selected!.source_codpost || undefined,
        latitude: point.lat,
        longitude: point.lon,
        source_creation: "ASTECH",
      });
      await updateLegacyAsset(token!, selected!.id, { building_id: building.id });
      return building;
    },
    onSuccess: (building) => {
      setFlash(
        `Bâtiment « ${building.nom_batiment} » créé dans Po2 et rattaché. ` +
          "Tu peux maintenant lui attribuer un bâtiment IGN.",
      );
      void queryClient.invalidateQueries({ queryKey: ["buildings"] });
      invalidate();
    },
    onError: (error) => setFlash(`Erreur de création : ${(error as Error).message}`),
  });

  // Amener la ligne sélectionnée à l'écran : sur plusieurs centaines de lignes, une
  // sélection faite depuis la carte serait autrement invisible dans la liste de gauche.
  useEffect(() => {
    if (selectedId == null) return;
    const node = rowRefs.current.get(selectedId);
    node?.scrollIntoView({ block: "nearest" });
  }, [selectedId, assets]);

  // Quitter le mode attribution dès qu'on change de bien : la sélection de
  // polygones ne vaut que pour le bâtiment en cours.
  useEffect(() => {
    setAttachMode(false);
    setAttachSelection([]);
    setPickerOpen(false);
    setBuildingSearch("");
    // Les encarts « Bâtiment Po2 » et « Local Po2 » ne décrivent QUE le point sur
    // lequel on a cliqué. Les laisser ouverts en changeant de bien ASTECH laissait à
    // l'écran la fiche d'une entité sans rapport avec le bien en cours.
    setInspectedBuildingId(null);
    setInspectedLocalId(null);
  }, [selectedId]);

  // Le champ de saisie suit le bien affiché : sans cela, changer de bien laisserait le
  // nom du précédent dans la case, et « Enregistrer » l'écrirait sur le mauvais.
  useEffect(() => {
    setAssetNameDraft(selected ? assetLabel(selected) : "");
  }, [selected]);

  useEffect(() => {
    setBuildingNameDraft(inspectedBuilding?.nom_batiment ?? "");
  }, [inspectedBuilding]);

  // Biens réellement affichables sur la carte : ceux qui ont une position propre, ou
  // un bâtiment rattaché qui en a une. Les autres ne sont visibles QUE dans la file de
  // gauche — c'est là que l'opératrice doit pouvoir les repérer.
  const mappableAssetIds = useMemo(() => {
    const ids = new Set<number>();
    for (const asset of assets) {
      const building = asset.building_id != null ? buildingsById.get(asset.building_id) : null;
      const latitude = asset.latitude ?? building?.latitude ?? null;
      const longitude = asset.longitude ?? building?.longitude ?? null;
      if (latitude != null && longitude != null) ids.add(asset.id);
    }
    return ids;
  }, [assets, buildingsById]);

  // Combien de biens sont positionnés **tous filtres confondus** : sert à expliquer une
  // carte vide plutôt que de la laisser muette.
  const positionedAssetCount = useMemo(
    () =>
      (linkedAssetsQuery.data ?? []).filter((asset) => {
        const building = asset.building_id != null ? buildingsById.get(asset.building_id) : null;
        return (asset.latitude ?? building?.latitude) != null;
      }).length,
    [buildingsById, linkedAssetsQuery.data],
  );

  // Application des filtres de second niveau, cumulés (ET).
  const visibleAssets = useMemo(() => {
    if (refineKeys.length === 0) return assets;
    const active = REFINE_FILTERS.filter((filter) => refineKeys.includes(filter.key));
    return assets.filter((asset) =>
      active.every((filter) => filter.test(asset, mappableAssetIds.has(asset.id))),
    );
  }, [assets, mappableAssetIds, refineKeys]);

  // Compteur de chaque puce **dans le contexte des autres puces actives** : une puce
  // qui donnerait une liste vide (« Candidat à valider » + « Aucune piste », qui
  // s'excluent) affiche 0 au lieu de vider la liste sans explication.
  const refineCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const filter of REFINE_FILTERS) {
      const others = REFINE_FILTERS.filter(
        (other) => other.key !== filter.key && refineKeys.includes(other.key),
      );
      counts[filter.key] = assets.filter(
        (asset) =>
          filter.test(asset, mappableAssetIds.has(asset.id)) &&
          others.every((other) => other.test(asset, mappableAssetIds.has(asset.id))),
      ).length;
    }
    return counts;
  }, [assets, mappableAssetIds, refineKeys]);

  // Locaux affichables : ceux qui ont une position propre. Les 121 sans coordonnées
  // n'ont rien à faire sur la carte — les empiler sur leur bâtiment mentirait.
  const localPoints = useMemo<LocalMapPoint[]>(() => {
    if (!showLocals) return [];
    return locals.flatMap((local) => {
      const building = buildingsById.get(local.building_id);
      // Un local est DANS son bâtiment : hériter de sa position n'invente rien, c'est la
      // meilleure vérité disponible — et c'est déjà ce qu'on fait pour les biens ASTECH.
      // Vérifié en base : les 121 locaux sans coordonnées ont tous un bâtiment parent
      // localisé et adressé, donc aucun n'est laissé de côté.
      const inherited = local.latitude == null || local.longitude == null;
      const latitude = local.latitude ?? building?.latitude ?? null;
      const longitude = local.longitude ?? building?.longitude ?? null;
      if (latitude == null || longitude == null) return [];
      return [
        {
          id: local.id,
          buildingId: local.building_id,
          label: local.nom_local,
          buildingLabel: building?.nom_batiment ?? null,
          latitude,
          longitude,
          isInherited: inherited,
          address: local.adresse_reconstituee ?? building?.adresse_reconstituee ?? null,
        },
      ];
    });
  }, [buildingsById, locals, showLocals]);

  // --- Point ASTECH sur la carte ----------------------------------------------
  const legacyPoints = useMemo<LegacyMapPoint[]>(() => {
    const toPoint = (asset: LegacyAsset): LegacyMapPoint | null => {
      const building = asset.building_id != null ? buildingsById.get(asset.building_id) : null;
      const latitude = asset.latitude ?? building?.latitude ?? null;
      const longitude = asset.longitude ?? building?.longitude ?? null;
      // Un bien sans position ET sans batiment localise n'a rien a faire sur la carte :
      // l'empiler au centre de Sete creerait un tas de points faussement precis.
      if (latitude == null || longitude == null) {
        if (asset.id !== selected?.id) return null;
        return {
          id: asset.id,
          label: assetLabel(asset),
          latitude: DEFAULT_LAT,
          longitude: DEFAULT_LON,
          isProvisional: true,
          isLinked: asset.building_id != null,
          isLocalTarget: asset.target_type === "local",
          isProposal: asset.status === "propose",
          buildingId: asset.building_id,
          buildingLabel: building?.nom_batiment ?? null,
        };
      }
      return {
        id: asset.id,
        label: assetLabel(asset),
        latitude,
        longitude,
        isProvisional: asset.latitude == null,
        isLinked: asset.building_id != null,
        isLocalTarget: asset.target_type === "local",
        // « propose » = rattaché par le moteur, pas encore confirmé par un humain.
        // La carte l'affiche en ambre : une suggestion ne doit pas avoir l'air d'une
        // décision prise.
        isProposal: asset.status === "propose",
        buildingId: asset.building_id,
        buildingLabel: building?.nom_batiment ?? null,
      };
    };

    // Deux lectures de la carte, au choix de l'utilisateur (bascule sous la carte) :
    //
    // - « tous les biens positionnés » (par défaut) : on voit l'ensemble du travail,
    //   quel que soit le filtre de la liste ;
    // - « suit le filtre » : la carte et la liste racontent la même chose.
    //
    // Le mode « suit le filtre » ne peut pas être le défaut : 338 biens sur 444 n'ont
    // aucune position, et le filtre initial est « À traiter » — la carte se retrouvait
    // donc vide au chargement, ce qui ressemblait à une panne.
    const source = mapFollowsFilter ? visibleAssets : linkedAssetsQuery.data ?? [];
    const byId = new Map<number, LegacyMapPoint>();
    for (const asset of source) {
      const point = toPoint(asset);
      if (point) byId.set(point.id, point);
    }
    // Le bien sélectionné reste visible même si le filtre vient de l'exclure : sans
    // cela, valider un rattachement le ferait disparaître de la carte sous le curseur.
    if (selected) {
      const point = toPoint(selected);
      if (point) byId.set(point.id, point);
    }
    return [...byId.values()];
  }, [buildingsById, linkedAssetsQuery.data, mapFollowsFilter, selected, visibleAssets]);

  const counts = countsQuery.data ?? {};
  // Des biens importés mais aucun candidat ni rattachement : l'utilisateur n'a pas
  // encore lancé la reconnaissance et la page semble sans action possible.
  const needsRecognition =
    assets.length > 0 &&
    (counts.lie ?? 0) === 0 &&
    assets.every((asset) => asset.candidate_building_id === null);

  return (
    <section>
      <p style={{ fontSize: 12, letterSpacing: ".05em", textTransform: "uppercase", color: "#94a3b8", margin: 0 }}>
        Patrimoine
      </p>
      <h2 style={{ margin: "4px 0 6px" }}>Référentiel patrimoine historique (ASTECH)</h2>
      <p style={{ color: "#64748b", fontSize: 13, margin: "0 0 16px", maxWidth: 780 }}>
        Rapprocher les biens du fichier de la collectivité avec le patrimoine Po2, les localiser
        sur la carte, puis leur attribuer un bâtiment IGN pour récupérer adresse et cadastre.
      </p>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 14 }}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          style={{ display: "none" }}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) importMutation.mutate(file);
            event.target.value = "";
          }}
        />
        <button
          type="button"
          style={btnSecondary}
          onClick={() => fileInputRef.current?.click()}
          disabled={importMutation.isPending}
        >
          {importMutation.isPending ? "Import…" : "1. Importer un export ASTECH"}
        </button>
        <button
          type="button"
          style={btnPrimary}
          onClick={() => candidatesMutation.mutate()}
          disabled={candidatesMutation.isPending}
        >
          {candidatesMutation.isPending ? "Analyse…" : "2. Reconnaître les noms"}
        </button>
        {(counts.propose ?? 0) > 0 && (
          <button
            type="button"
            style={btnSecondary}
            onClick={() => confirmMutation.mutate()}
            disabled={confirmMutation.isPending}
          >
            {confirmMutation.isPending
              ? "Confirmation…"
              : `3. Confirmer les ${counts.propose} rattachement(s) proposé(s)`}
          </button>
        )}
        {/* Le retour de l'aller-retour : le classeur que la collectivité réinjecte.
            Le compteur annonce ce qui partira AVANT le clic — un export silencieux de
            6 lignes sur 444 serait incompréhensible. */}
        {(counts.total ?? 0) > 0 && (
          <button
            type="button"
            style={btnPrimary}
            disabled={exportMutation.isPending || (exportPreviewQuery.data?.exported_rows ?? 0) === 0}
            title={
              (exportPreviewQuery.data?.exported_rows ?? 0) === 0
                ? "Aucun rattachement validé : confirme d'abord les propositions du moteur."
                : "Classeur au gabarit ASTECH, en-têtes recopiés depuis ton export d'origine."
            }
            onClick={() => exportMutation.mutate()}
          >
            {exportMutation.isPending
              ? "Génération…"
              : `4. Exporter pour ASTECH${
                  exportPreviewQuery.data
                    ? ` (${exportPreviewQuery.data.exported_rows} ligne(s))`
                    : ""
                }`}
          </button>
        )}
        {exportPreviewQuery.data && (exportPreviewQuery.data.review_rows ?? 0) > 0 && (
          <span style={{ fontSize: 12, color: TEXT_MUTED, alignSelf: "center" }}>
            {exportPreviewQuery.data.review_rows} bien(s) resteront en feuille « à vérifier »
          </span>
        )}
        {/* Repartir d'une feuille blanche quand le référentiel Po2 a beaucoup bougé.
            Destructif : on demande confirmation, en annonçant le nombre exact.
            Affiché dès qu'il y a des biens, et non plus seulement quand il reste des
            liens : le bouton disparaissait justement au moment où l'on voulait
            vérifier l'état du référentiel. */}
        {(counts.total ?? 0) > 0 && (
          <button
            type="button"
            style={{ ...btnSecondary, borderColor: "rgba(248, 113, 113, 0.5)", color: "#fca5a5" }}
            onClick={() => {
              const total = (counts.lie ?? 0) + (counts.propose ?? 0);
              if (
                !window.confirm(
                  `Supprimer les ${total} rapprochement(s) entre les biens ASTECH et Po2 ?\n\n` +
                    "Les biens repassent « à traiter » et il faudra relancer « Reconnaître les noms ».\n" +
                    "Les biens « à créer », « ignoré » et « hors périmètre » ne sont pas touchés, " +
                    "et les points déjà posés sur la carte sont conservés.",
                )
              ) {
                return;
              }
              resetLinksMutation.mutate();
            }}
            disabled={resetLinksMutation.isPending}
          >
            {resetLinksMutation.isPending
              ? "Suppression…"
              : "1 · Détacher les rapprochements (garde les biens)"}
          </button>
        )}
        {/* Remise à zéro totale : plus fort que la purge des liens, car elle efface
            AUSSI les positions et les décisions « ignoré ». C'est le « repartir de 0 »
            au sens strict — l'écran revient à l'état juste après l'import. */}
        {(counts.total ?? 0) > 0 && (
          <button
            type="button"
            style={{ ...btnSecondary, borderColor: "rgba(248, 113, 113, 0.5)", color: "#fca5a5" }}
            onClick={() => {
              if (
                !window.confirm(
                  `Remise à zéro totale de ${counts.total ?? 0} bien(s) ASTECH.\n\n` +
                    "Sont effacés : les rattachements, les candidats proposés, les positions " +
                    "posées à la main et les décisions « ignoré ».\n\n" +
                    "⚠️ Les biens ASTECH DISPARAÎTRONT de la carte : ils n'ont pas de " +
                    "coordonnées propres (le fichier n'en porte qu'une sur 444). Ils y " +
                    "reviendront en cliquant « 2. Reconnaître les noms ».\n\n" +
                    "Les biens hors périmètre gardent leur statut, et les bâtiments et locaux " +
                    "Po2 ne sont pas touchés.",
                )
              ) {
                return;
              }
              resetAllMutation.mutate();
            }}
            disabled={resetAllMutation.isPending}
          >
            {resetAllMutation.isPending
              ? "Remise à zéro…"
              : "2 · Remettre le traitement à zéro (garde les biens)"}
          </button>
        )}
        {/* Repartir d'un export ASTECH neuf. Bien plus destructif que la purge des
            rapprochements : les biens eux-mêmes disparaissent. La confirmation annonce
            donc le compte exact, et ce qui survit. */}
        {(counts.total ?? 0) > 0 && (
          <button
            type="button"
            style={{ ...btnSecondary, borderColor: "rgba(248, 113, 113, 0.5)", color: "#fca5a5" }}
            onClick={() => {
              const total = counts.total ?? 0;
              const traites = (counts.lie ?? 0) + (counts.propose ?? 0);
              if (
                !window.confirm(
                  `Supprimer l'import ASTECH : ${total} bien(s) seront effacés.\n\n` +
                    `Tu perdras ${traites} rapprochement(s) déjà faits, ainsi que les points ` +
                    "posés à la main et les décisions (ignoré, hors périmètre).\n\n" +
                    "Les bâtiments et les locaux Po2 créés depuis ASTECH sont CONSERVÉS : " +
                    "le moteur les retrouvera au réimport.\n\n" +
                    "À savoir : réimporter par-dessus sans supprimer met déjà les biens à jour " +
                    "sans rien dupliquer, et garde les rapprochements.",
                )
              ) {
                return;
              }
              deleteImportsMutation.mutate();
            }}
            disabled={deleteImportsMutation.isPending}
          >
            {deleteImportsMutation.isPending
              ? "Suppression…"
              : "3 · Supprimer les biens ASTECH (pour réimporter)"}
          </button>
        )}
      </div>

      {flash && (
        <div
          role="status"
          onClick={() => setFlash(null)}
          // Le message était écrit en bleu foncé (#0369a1) sur le fond sombre de la
          // plateforme : illisible. Les erreurs passaient donc totalement inaperçues et
          // l'action semblait « ne rien faire ». Rouge pour une erreur, bleu clair sinon.
          style={{
            fontSize: 13,
            marginBottom: 12,
            cursor: "pointer",
            padding: "8px 10px",
            borderRadius: 8,
            border: flash.startsWith("Erreur")
              ? "1px solid rgba(248, 113, 113, 0.5)"
              : "1px solid rgba(56, 189, 248, 0.4)",
            background: flash.startsWith("Erreur")
              ? "rgba(248, 113, 113, 0.12)"
              : "rgba(56, 189, 248, 0.10)",
            color: flash.startsWith("Erreur") ? "#fca5a5" : "#7dd3fc",
          }}
        >
          {flash}
        </div>
      )}

      {needsRecognition && (
        <div
          style={{
            ...card,
            marginBottom: 12,
            borderColor: "rgba(251, 191, 36, 0.5)",
            fontSize: 13,
          }}
        >
          <strong>Prochaine étape :</strong> {assets.length} bien(s) importé(s), mais la
          reconnaissance des noms n'a pas encore été lancée. Clique «&nbsp;2. Reconnaître les
          noms&nbsp;» ci-dessus : la plateforme rattachera seule les évidences et proposera un
          candidat pour le reste.
        </div>
      )}

      {/* Avancement : additionner les cartes de statut de tete etait la seule facon de
          savoir ou l'on en etait sur 380 biens. */}
      {(counts.total ?? 0) > 0 && (
        <div
          style={{
            display: "flex",
            gap: 12,
            alignItems: "center",
            flexWrap: "wrap",
            marginBottom: 10,
            fontSize: 13,
          }}
        >
          <strong>
            {(counts.lie ?? 0) + (counts.a_creer ?? 0)} traité(s) sur {counts.total ?? 0}
          </strong>
          <div
            style={{
              flex: 1,
              minWidth: 160,
              height: 8,
              borderRadius: 999,
              background: "rgba(148, 163, 184, 0.2)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${Math.round((100 * ((counts.lie ?? 0) + (counts.a_creer ?? 0))) / Math.max(1, counts.total ?? 1))}%`,
                height: "100%",
                background: "#22c55e",
              }}
            />
          </div>
          <span style={{ color: TEXT_MUTED, fontSize: 12 }}>
            {counts.propose ?? 0} à confirmer · {counts.a_traiter ?? 0} à traiter
          </span>
          <label
            style={{ display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12, color: TEXT_MUTED }}
            title="Après chaque décision, sélectionne automatiquement le bien suivant de la file."
          >
            <input
              type="checkbox"
              checked={autoAdvance}
              onChange={(event) => setAutoAdvance(event.target.checked)}
            />
            Passer au suivant après chaque décision
          </label>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 10, marginBottom: 16 }}>
        {STATUS_ORDER.map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => setStatusFilter(status)}
            style={{
              ...card,
              textAlign: "left",
              cursor: "pointer",
              border: statusFilter === status ? "1px solid #60a5fa" : BORDER,
              boxShadow: statusFilter === status ? "0 0 0 1px #60a5fa inset" : undefined,
            }}
          >
            <div style={{ fontSize: 13, color: TEXT_MUTED }}>{STATUS_LABEL[status]}</div>
            <div style={{ fontSize: 24, fontWeight: 500, color: TEXT }}>
              {status === "" ? counts.total ?? 0 : counts[status] ?? 0}
            </div>
          </button>
        ))}
      </div>

      {/* Filtres de second niveau : ils affinent le statut sélectionné plutôt que de
          le remplacer. Le compteur de chaque puce dit la taille du tas avant de cliquer. */}
      <div
        style={{
          display: "flex",
          gap: 6,
          flexWrap: "wrap",
          alignItems: "center",
          marginBottom: 14,
        }}
      >
        <span style={{ fontSize: 12, color: TEXT_MUTED, marginRight: 2 }}>Affiner :</span>
        {REFINE_FILTERS.map((filter) => {
          const isActive = refineKeys.includes(filter.key);
          return (
            <button
              key={filter.key}
              type="button"
              title={filter.title}
              onClick={() =>
                setRefineKeys((keys) =>
                  keys.includes(filter.key)
                    ? keys.filter((key) => key !== filter.key)
                    : [...keys, filter.key],
                )
              }
              style={{
                ...btnSecondary,
                padding: "4px 10px",
                fontSize: 12,
                borderColor: isActive ? "#a855f7" : "rgba(148, 163, 184, 0.35)",
                background: isActive ? "rgba(168, 85, 247, 0.18)" : "transparent",
                color: isActive ? "#e9d5ff" : TEXT,
              }}
            >
              {filter.label}{" "}
              <span style={{ color: TEXT_MUTED }}>{refineCounts[filter.key] ?? 0}</span>
            </button>
          );
        })}
        {refineKeys.length > 0 && (
          <button
            type="button"
            style={{ ...btnSecondary, padding: "4px 10px", fontSize: 12, border: "none", color: TEXT_MUTED }}
            onClick={() => setRefineKeys([])}
          >
            Tout afficher
          </button>
        )}
      </div>

      {/* Trois colonnes : file · carte · panneau d'action. Les media queries de
          `.astech-layout` (styles.css) replient le panneau sous la carte sur un écran
          étroit — à trois colonnes serrées, la carte devient trop fine pour viser un
          point. La carte garde sa hauteur fixe et son ResizeObserver se charge de
          prévenir Leaflet du changement de largeur. */}
      <div className="astech-layout">
        {/* --- File des biens ASTECH ----------------------------------------- */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <input
            type="search"
            style={input}
            placeholder="Chercher un code bien, une désignation…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          {assetsQuery.isLoading && <p style={{ color: TEXT_MUTED }}>Chargement…</p>}
          {!assetsQuery.isLoading && assets.length === 0 && (
            <p style={{ color: TEXT_MUTED, fontSize: 13 }}>
              Aucun bien pour ce filtre. Commence par importer un export ASTECH.
            </p>
          )}
          {!assetsQuery.isLoading && assets.length > 0 && visibleAssets.length === 0 && (
            <p style={{ color: TEXT_MUTED, fontSize: 13 }}>
              Aucun bien ne réunit ces critères — « Candidat à valider » et « Aucune piste »
              s'excluent, par exemple. <button
                type="button"
                style={{ ...btnSecondary, padding: "2px 8px", fontSize: 12 }}
                onClick={() => setRefineKeys([])}
              >
                Tout afficher
              </button>
            </p>
          )}
          {visibleAssets.length > 0 && visibleAssets.length !== assets.length && (
            <p style={{ color: TEXT_MUTED, fontSize: 12, margin: 0 }}>
              {visibleAssets.length} bien(s) sur {assets.length}
            </p>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 620, overflowY: "auto" }}>
            {visibleAssets.map((asset) => {
              const isSelected = asset.id === selectedId;
              return (
                <button
                  key={asset.id}
                  type="button"
                  ref={(node) => {
                    if (node) rowRefs.current.set(asset.id, node);
                    else rowRefs.current.delete(asset.id);
                  }}
                  onClick={() => setSelectedId(asset.id)}
                  style={{
                    ...card,
                    textAlign: "left",
                    cursor: "pointer",
                    padding: "8px 10px",
                    border: isSelected ? "1px solid #a855f7" : BORDER,
                    background: isSelected ? "rgba(124, 58, 237, 0.22)" : SURFACE,
                  }}
                >
                  <div style={{ fontSize: 11, color: "#c4b5fd", fontFamily: "monospace" }}>
                    {asset.code_bien}
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: TEXT }}>
                    {assetLabel(asset)}
                    {asset.horsparc === "O" && (
                      <span
                        title="Bien sorti du parc dans ASTECH (HORSPARC = O)"
                        style={{
                          marginLeft: 6,
                          fontSize: 10,
                          padding: "1px 6px",
                          borderRadius: 999,
                          background: "rgba(251, 191, 36, 0.18)",
                          color: "#fbbf24",
                          whiteSpace: "nowrap",
                        }}
                      >
                        sorti du parc
                      </span>
                    )}
                  </div>
                  {/* Ce qu'il reste à faire, lisible sans ouvrir le bien : son statut,
                      la cible quand il est traité, et le fait qu'il soit absent de la
                      carte — ces biens-là ne se traitent QUE depuis cette liste. */}
                  <div
                    style={{
                      display: "flex",
                      gap: 5,
                      flexWrap: "wrap",
                      alignItems: "center",
                      marginTop: 4,
                    }}
                  >
                    {STATUS_PILL[asset.status] && (
                      <span
                        style={{
                          ...pillStyle,
                          color: STATUS_PILL[asset.status].color,
                          background: STATUS_PILL[asset.status].background,
                        }}
                      >
                        {STATUS_PILL[asset.status].label}
                      </span>
                    )}
                    {!mappableAssetIds.has(asset.id) && (
                      <span
                        title="Ce bien n'a ni position ni bâtiment localisé : il n'apparaît pas sur la carte et se traite depuis cette liste."
                        style={{ ...pillStyle, color: "#c4b5fd", background: "rgba(168, 85, 247, 0.16)" }}
                      >
                        absent de la carte
                      </span>
                    )}
                  </div>
                  {asset.building_id != null && (
                    <div style={{ fontSize: 12, color: "#86efac", marginTop: 2 }}>
                      ✓ {buildingsById.get(asset.building_id)?.nom_batiment ?? `bâtiment ${asset.building_id}`}
                      {asset.target_type === "local" && asset.local_id != null
                        ? ` › ${localsById.get(asset.local_id)?.nom_local ?? "local"}`
                        : ""}
                    </div>
                  )}
                  {asset.building_id == null && asset.candidate_label && (
                    <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 2 }}>
                      → {asset.candidate_label}{" "}
                      <span style={{ color: scoreColor(asset.candidate_score) }}>
                        {asset.candidate_score != null
                          ? `${Math.round(asset.candidate_score * 100)} %`
                          : ""}
                      </span>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* --- Carte (colonne du milieu) ------------------------------------- */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <BuildingPortfolioMap
            buildings={buildings}
            activeBuildingId={targetBuilding?.id ?? null}
            onSelectBuildingId={(buildingId) => {
              // Clic = CONSULTATION du bâtiment Po2. Le rattachement se fait en
              // déposant le point ASTECH dessus : un clic ne doit pas modifier
              // les données, c'était la source de confusion (le point bleu passait
              // au vert sans qu'on l'ait demandé).
              if (attachMode) return;
              setInspectedLocalId(null);
              setInspectedBuildingId(buildingId);
            }}
            // Clic dans le vide : on sort de la sélection. L'encart « Bâtiment Po2 »
            // et le bien sélectionné disparaissent ensemble — c'est le geste
            // « je ne travaille plus sur rien ».
            onBackgroundClick={() => {
              if (attachMode) return;
              setInspectedBuildingId(null);
              setInspectedLocalId(null);
              setSelectedId(null);
            }}
            onViewCenterChange={setMapCenter}
            localPoints={localPoints}
            // Cliquer un local en fait la cible du bien sélectionné : c'est le geste
            // « ce CODE_BIEN, c'est CE local-là », jusqu'ici seulement possible par le
            // menu déroulant, et seulement après un rattachement au bâtiment.
            onSelectLocalId={(localId) => {
              // Clic = CONSULTATION, comme pour un bâtiment. Le rattachement se fait
              // depuis le panneau : un clic ne doit pas modifier les données.
              if (attachMode) return;
              setInspectedBuildingId(null);
              setInspectedLocalId(localId);
            }}
            highlightedBuildingIds={targetBuilding ? [targetBuilding.id] : []}
            legacyPoints={legacyPoints}
            activeLegacyId={selected?.id ?? null}
            onSelectLegacyId={(id) => {
              // Le bien doit aussi apparaitre dans la liste de gauche : si le filtre
              // courant l'exclut, on bascule sur son statut plutot que de selectionner
              // une ligne invisible.
              const asset = knownAssets.get(id);
              if (asset && statusFilter && asset.status !== statusFilter) {
                setStatusFilter(asset.status);
              }
              // Les filtres d'affinage peuvent aussi masquer la ligne : on les lève
              // plutôt que de sélectionner un bien invisible dans la liste.
              if (
                asset &&
                refineKeys.length > 0 &&
                !REFINE_FILTERS.filter((filter) => refineKeys.includes(filter.key)).every(
                  (filter) => filter.test(asset, mappableAssetIds.has(asset.id)),
                )
              ) {
                setRefineKeys([]);
              }
              setSelectedId(id);
            }}
            onMoveLegacyPoint={(id, lat, lon) => {
              // Le serveur géocode le point à l'envers et renseigne l'adresse
              // trouvée, à côté de l'adresse ASTECH d'origine (jamais à sa place).
              updateMutation.mutate({ id, payload: { latitude: lat, longitude: lon } });
              setFlash(
                selected?.building_id != null
                  ? "Point fusionné déplacé : le bâtiment Po2 suit, adresse recalculée pour les deux."
                  : "Position enregistrée, recherche de l'adresse correspondante…",
              );
            }}
            onDropLegacyOnBuilding={(id, buildingId, localId) => {
              // Déposer le point ASTECH sur une entité Po2 vaut rattachement. Le dépôt
              // reconnaît désormais aussi les LOCAUX : c'est la cible la plus fréquente
              // d'un CODE_BIEN, et il fallait auparavant viser le bâtiment puis
              // corriger dans le panneau.
              const building = buildingsById.get(buildingId);
              const local = localId != null ? localsById.get(localId) : null;
              updateMutation.mutate({
                id,
                payload: localId != null ? { local_id: localId } : { building_id: buildingId },
              });
              setFlash(
                local
                  ? `Rattaché au local « ${local.nom_local} » de « ${building?.nom_batiment ?? buildingId} ». ` +
                    "L'adresse et le cadastre restent ceux du bâtiment."
                  : `Rattaché à « ${building?.nom_batiment ?? buildingId} » : le bien reprend son ` +
                    "adresse et sa position. Utilise « Détacher » si ce n'est pas le bon.",
              );
            }}
            attachMode={attachMode ? "ign" : "none"}
            attachLat={attachLookupQuery.data?.lat ?? pointCenter?.lat ?? null}
            attachLon={attachLookupQuery.data?.lon ?? pointCenter?.lon ?? null}
            attachAddress={attachAddress}
            attachFeatureCollection={
              (attachLookupQuery.data?.feature_collection as GeoJsonFeatureCollection | undefined) ?? null
            }
            attachSelectedIds={attachSelection.map((feature) =>
              String((feature.properties as Record<string, unknown>)?.ign_id ?? ""),
            )}
            onSelectAttachFeature={(feature) => setAttachSelection((current) => [...current, feature])}
            onDeselectAttachFeatureId={(featureId) =>
              setAttachSelection((current) =>
                current.filter(
                  (feature) =>
                    String((feature.properties as Record<string, unknown>)?.ign_id ?? "") !== featureId,
                ),
              )
            }
            isAttachLoading={attachLookupQuery.isFetching}
            draggableBuildingId={inspectedBuildingId}
            onMoveBuilding={(buildingId, lat, lon) =>
              moveBuildingMutation.mutate({ buildingId, lat, lon })
            }
          />

          {/* Légende : sans elle, les trois états du point violet sont indevinables. */}
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center", fontSize: 12, color: TEXT_MUTED }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#22c55e", border: "2px solid #fff", display: "inline-block" }} />
              Rattachement validé (
              {legacyPoints.filter((point) => point.isLinked && !point.isProposal).length})
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#fbbf24", border: "2px solid #fff", display: "inline-block" }} />
              Proposé par le moteur, à confirmer (
              {legacyPoints.filter((point) => point.isProposal).length})
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#a855f7", border: "2px solid #fff", display: "inline-block" }} />
              Bien ASTECH non rattaché ({legacyPoints.filter((point) => !point.isLinked).length})
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#2563eb", border: "2px solid #38bdf8", display: "inline-block" }} />
              Bâtiment Po2
            </span>
            <label
              style={{ display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer" }}
              title="Un CODE_BIEN ASTECH désigne souvent un local (logement de fonction, salle, WC publics). Clique un local pour en faire la cible du bien sélectionné."
            >
              <input
                type="checkbox"
                checked={showLocals}
                onChange={(event) => setShowLocals(event.target.checked)}
              />
              <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#6366f1", border: "1px solid #a5b4fc", display: "inline-block" }} />
              Locaux Po2 ({localPoints.length}
              {localPoints.filter((point) => point.isInherited).length > 0
                ? `, dont ${localPoints.filter((point) => point.isInherited).length} en creux : position héritée du bâtiment`
                : ""}
              )
            </label>
            {/* Rendre le comportement de la carte VISIBLE et réversible : sans cette
                bascule, « la carte suit le filtre » vidait l'écran sans rien expliquer,
                et on ne pouvait pas revenir en arrière. */}
            <label
              style={{ display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer" }}
              title="Sinon la carte affiche tous les biens positionnés, quel que soit le filtre de la liste."
            >
              <input
                type="checkbox"
                checked={mapFollowsFilter}
                onChange={(event) => setMapFollowsFilter(event.target.checked)}
              />
              La carte suit le filtre ({legacyPoints.length} point(s))
            </label>
          </div>

          {/* La carte suit le filtre (demande du 2026-08-20). Conséquence : avec le
              filtre par défaut « À traiter », elle est VIDE de points ASTECH — ces biens
              n'ont pas encore de coordonnées. Une carte muette laissait croire à une
              panne : on dit pourquoi, et on donne le raccourci. */}
          {legacyPoints.length === 0 && (counts.total ?? 0) > 0 && (
            <div
              style={{
                ...card,
                borderColor: "rgba(251, 191, 36, 0.5)",
                background: "rgba(251, 191, 36, 0.10)",
                fontSize: 12,
                lineHeight: 1.5,
              }}
            >
              Aucun bien ASTECH à afficher ici. C'est attendu : un bien ASTECH n'a pas de
              coordonnées propres — le fichier n'en porte qu'une sur 444 — il n'apparaît
              qu'une fois rattaché à un bâtiment ou posé à la main.
              {positionedAssetCount > 0 && (
                <>
                  {" "}
                  <strong>{positionedAssetCount} bien(s)</strong> sont pourtant positionnés.{" "}
                  <button
                    type="button"
                    style={{ ...btnSecondary, padding: "2px 8px", fontSize: 12 }}
                    onClick={() => {
                      setMapFollowsFilter(false);
                      setStatusFilter("");
                      setRefineKeys([]);
                    }}
                  >
                    Les afficher tous
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        {/* --- Panneau d'action (colonne de droite) -------------------------- */}
        <div className="astech-panel" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Panneau du LOCAL consulté — symétrique de celui du bâtiment. Un CODE_BIEN
              ASTECH désigne souvent un local : il lui fallait les mêmes prises. */}
          {inspectedLocal && (
            <div style={{ ...card, borderColor: "rgba(129, 140, 248, 0.55)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 11, color: "#a5b4fc", textTransform: "uppercase" }}>
                    Local Po2
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", margin: "4px 0 8px" }}>
                    <input
                      value={localNameDraft}
                      onChange={(event) => setLocalNameDraft(event.target.value)}
                      style={{ ...input, fontSize: 15, flex: 1, minWidth: 200 }}
                      title="Nom du local Po2. Modifiable."
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && localNameDraft.trim()) {
                          renameLocalMutation.mutate({
                            local: inspectedLocal,
                            nom: localNameDraft.trim(),
                          });
                        }
                        if (event.key === "Escape") setLocalNameDraft(inspectedLocal.nom_local);
                      }}
                    />
                    {localNameDraft.trim() !== "" &&
                      localNameDraft !== inspectedLocal.nom_local && (
                        <>
                          <button
                            type="button"
                            style={btnPrimary}
                            onClick={() =>
                              renameLocalMutation.mutate({
                                local: inspectedLocal,
                                nom: localNameDraft.trim(),
                              })
                            }
                          >
                            Enregistrer
                          </button>
                          <button
                            type="button"
                            style={btnSecondary}
                            onClick={() => setLocalNameDraft(inspectedLocal.nom_local)}
                          >
                            Annuler
                          </button>
                        </>
                      )}
                  </div>
                </div>
                <button type="button" style={btnSecondary} onClick={() => setInspectedLocalId(null)}>
                  Fermer
                </button>
              </div>
              <dl
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
                  gap: 10,
                  margin: 0,
                }}
              >
                {[
                  [
                    "Bâtiment porteur",
                    buildingsById.get(inspectedLocal.building_id)?.nom_batiment ?? "—",
                  ],
                  [
                    "Adresse",
                    inspectedLocal.adresse_reconstituee ??
                      `${
                        buildingsById.get(inspectedLocal.building_id)?.adresse_reconstituee ?? "—"
                      } (héritée du bâtiment)`,
                  ],
                  [
                    "Position",
                    inspectedLocal.latitude != null
                      ? "propre au local"
                      : "héritée du bâtiment",
                  ],
                  [
                    "Référence cadastrale",
                    inspectedLocal.dgfip_reference_norm ??
                      buildingsById.get(inspectedLocal.building_id)?.dgfip_reference_norm ??
                      "—",
                  ],
                  ["Type", inspectedLocal.type_local ?? "—"],
                  [
                    "Biens ASTECH rattachés",
                    String(
                      [...knownAssets.values()].filter(
                        (asset) => asset.local_id === inspectedLocal.id,
                      ).length,
                    ),
                  ],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt style={{ fontSize: 11, color: TEXT_MUTED, textTransform: "uppercase" }}>{label}</dt>
                    <dd style={{ margin: 0, fontSize: 13 }}>{value}</dd>
                  </div>
                ))}
              </dl>
              {selected && (
                <div style={{ marginTop: 10 }}>
                  <button
                    type="button"
                    style={btnPrimary}
                    onClick={() => {
                      updateMutation.mutate(
                        { id: selected.id, payload: { local_id: inspectedLocal.id } },
                        {
                          onSuccess: () =>
                            setFlash(
                              `« ${assetLabel(selected)} » rattaché au local « ${inspectedLocal.nom_local} ». ` +
                                "L'adresse et le cadastre restent ceux du bâtiment porteur.",
                            ),
                        },
                      );
                    }}
                  >
                    Rattacher « {assetLabel(selected)} » à ce local
                  </button>
                </div>
              )}
              {/* Un local Po2 sans contrepartie ASTECH doit pouvoir remonter dans le
                  fichier de retour, comme un bâtiment (Q13). Le bouton disparaît une
                  fois le local présent dans la liste : il n'y a rien à ajouter deux fois. */}
              {![...knownAssets.values()].some(
                (asset) => asset.local_id === inspectedLocal.id,
              ) && (
                <div style={{ marginTop: 10 }}>
                  <button
                    type="button"
                    style={btnSecondary}
                    disabled={addLocalToAstechMutation.isPending}
                    onClick={() => addLocalToAstechMutation.mutate(inspectedLocal.id)}
                  >
                    {addLocalToAstechMutation.isPending
                      ? "Ajout…"
                      : "Ajouter ce local à la liste ASTECH"}
                  </button>
                  <p style={{ margin: "6px 0 0", fontSize: 12, color: TEXT_MUTED }}>
                    Ce local n'a aucun bien ASTECH en face : il remontera dans le fichier de
                    retour comme ligne à créer, avec l'adresse de son bâtiment porteur.
                  </p>
                </div>
              )}
              {/* Typologie : l'import a classé en « local » des entités qui sont en
                  réalité des bâtiments. Le geste doit être disponible là où on le
                  constate, pas dans un autre écran. */}
              <div style={{ marginTop: 10, borderTop: BORDER, paddingTop: 10 }}>
                <div style={{ fontSize: 11, color: TEXT_MUTED, textTransform: "uppercase", marginBottom: 6 }}>
                  Typologie
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  <span style={{ fontSize: 13 }}>Local</span>
                  <button
                    type="button"
                    style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px" }}
                    disabled={reclassifyMutation.isPending}
                    title="En faire un bâtiment Po2 à part entière. Adresse, position, cadastre et biens ASTECH le suivent."
                    onClick={() => {
                      if (
                        !window.confirm(
                          `Faire de « ${inspectedLocal.nom_local} » un BÂTIMENT Po2 ?

` +
                            "Son adresse, sa position, son cadastre et ses biens ASTECH le suivent. " +
                            "Il quitte son bâtiment porteur et devient autonome.",
                        )
                      ) {
                        return;
                      }
                      reclassifyMutation.mutate({ kind: "localToBuilding", local: inspectedLocal });
                    }}
                  >
                    {reclassifyMutation.isPending ? "Reclassement…" : "→ En faire un bâtiment"}
                  </button>
                </div>
              </div>
              <button
                type="button"
                style={{ ...btnSecondary, marginTop: 10 }}
                onClick={() => {
                  setInspectedLocalId(null);
                  setInspectedBuildingId(inspectedLocal.building_id);
                }}
              >
                Voir le bâtiment porteur
              </button>
            </div>
          )}

          {inspectedBuilding && (
            <div style={{ ...card, borderColor: "rgba(56, 189, 248, 0.55)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontSize: 11, color: "#7dd3fc", textTransform: "uppercase" }}>
                    Bâtiment Po2 — déplaçable sur la carte
                  </div>
                  {/* Nom éditable : les noms Po2 viennent d'un import ou d'une
                      attribution IGN, et sont parfois faux ou en doublon. Les corriger
                      ici évite de sortir de l'écran de rapprochement pour le faire. */}
                  <div style={{ display: "flex", gap: 6, alignItems: "center", margin: "2px 0 8px" }}>
                    <input
                      value={buildingNameDraft}
                      onChange={(event) => setBuildingNameDraft(event.target.value)}
                      style={{ ...input, fontSize: 15, minWidth: 180 }}
                      title="Nom du bâtiment Po2. Modifiable."
                      onKeyDown={(event) => {
                        if (event.key === "Enter") saveBuildingName();
                        if (event.key === "Escape")
                          setBuildingNameDraft(inspectedBuilding.nom_batiment ?? "");
                      }}
                    />
                    {buildingNameDraft.trim() !== "" &&
                      buildingNameDraft !== (inspectedBuilding.nom_batiment ?? "") && (
                        <>
                          <button type="button" style={btnPrimary} onClick={saveBuildingName}>
                            Enregistrer
                          </button>
                          <button
                            type="button"
                            style={btnSecondary}
                            onClick={() =>
                              setBuildingNameDraft(inspectedBuilding.nom_batiment ?? "")
                            }
                          >
                            Annuler
                          </button>
                        </>
                      )}
                  </div>
                </div>
                <button type="button" style={btnSecondary} onClick={() => setInspectedBuildingId(null)}>
                  Fermer
                </button>
              </div>
              {buildingAmbiguities.has(inspectedBuilding.id) && (
                <div
                  style={{
                    border: "1px solid rgba(251, 191, 36, 0.5)",
                    background: "rgba(251, 191, 36, 0.10)",
                    borderRadius: 8,
                    padding: "8px 10px",
                    marginBottom: 10,
                    fontSize: 12,
                    lineHeight: 1.5,
                  }}
                >
                  {buildingAmbiguities.get(inspectedBuilding.id)!.sameName > 1 && (
                    <div>
                      ⚠ <strong>{buildingAmbiguities.get(inspectedBuilding.id)!.sameName} bâtiments Po2</strong>{" "}
                      portent ce nom. Il vient probablement de la zone IGN qui les englobe, pas du
                      bâtiment : fie-toi à l'adresse pour choisir.
                    </div>
                  )}
                  {buildingAmbiguities.get(inspectedBuilding.id)!.sameIgn > 1 && (
                    <div>
                      ⚠ Un autre bâtiment Po2 est attaché au <strong>même bâtiment IGN</strong>{" "}
                      ({inspectedBuilding.ign_id}). Ce n'est pas forcément un doublon — une
                      empreinte IGN couvre parfois plusieurs bâtiments d'un même ensemble — mais
                      les deux partageront la même adresse et le même cadastre au réexport.
                    </div>
                  )}
                </div>
              )}
              <dl
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
                  gap: 10,
                  margin: 0,
                }}
              >
                {[
                  ["Adresse", inspectedBuilding.adresse_reconstituee ?? "—"],
                  ["Commune", inspectedBuilding.nom_commune ?? "—"],
                  ["Référence cadastrale", inspectedBuilding.dgfip_reference_norm ?? "—"],
                  [
                    "Attachement IGN",
                    inspectedBuilding.statut_geocodage === "IGN_VALIDE" ? "Oui" : "Non",
                  ],
                  [
                    "Biens ASTECH rattachés",
                    String(
                      (linkedAssetsQuery.data ?? []).filter(
                        (asset) => asset.building_id === inspectedBuilding.id,
                      ).length,
                    ),
                  ],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt style={{ fontSize: 11, color: TEXT_MUTED, textTransform: "uppercase" }}>{label}</dt>
                    <dd style={{ margin: 0, fontSize: 13 }}>{value}</dd>
                  </div>
                ))}
              </dl>
              {!(linkedAssetsQuery.data ?? []).some(
                (asset) => asset.building_id === inspectedBuilding.id,
              ) && (
                <div style={{ marginTop: 10 }}>
                  <button
                    type="button"
                    style={btnSecondary}
                    disabled={addToAstechMutation.isPending}
                    onClick={() => addToAstechMutation.mutate(inspectedBuilding.id)}
                  >
                    {addToAstechMutation.isPending
                      ? "Ajout…"
                      : "Ajouter ce bâtiment à la liste ASTECH"}
                  </button>
                  <p style={{ margin: "6px 0 0", fontSize: 12, color: TEXT_MUTED }}>
                    Ce bâtiment n'a aucun bien ASTECH en face : il remontera dans le fichier
                    de retour comme ligne à créer.
                  </p>
                </div>
              )}

              {/* Les LOCAUX de ce bâtiment. Ils n'apparaissaient nulle part depuis le
                  bâtiment : impossible de voir sa structure sans cliquer ses pastilles
                  une par une sur la carte. */}
              {locals.filter((local) => local.building_id === inspectedBuilding.id).length > 0 && (
                <div style={{ marginTop: 10, borderTop: BORDER, paddingTop: 10, fontSize: 12 }}>
                  <div style={{ color: TEXT_MUTED, marginBottom: 4 }}>
                    {locals.filter((local) => local.building_id === inspectedBuilding.id).length} local(aux) dans ce bâtiment :
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 2, maxHeight: 160, overflowY: "auto" }}>
                    {locals
                      .filter((local) => local.building_id === inspectedBuilding.id)
                      .map((local) => {
                        const biens = [...knownAssets.values()].filter(
                          (asset) => asset.local_id === local.id,
                        ).length;
                        return (
                          <button
                            key={local.id}
                            type="button"
                            style={{
                              ...btnSecondary,
                              textAlign: "left",
                              padding: "3px 8px",
                              fontSize: 12,
                              borderColor: "rgba(129, 140, 248, 0.4)",
                            }}
                            onClick={() => {
                              setInspectedBuildingId(null);
                              setInspectedLocalId(local.id);
                            }}
                          >
                            › {local.nom_local}
                            {biens > 0 && (
                              <span style={{ color: "#86efac" }}> — {biens} bien(s) ASTECH</span>
                            )}
                            {local.latitude == null && (
                              <span style={{ color: TEXT_MUTED }}> · position héritée</span>
                            )}
                          </button>
                        );
                      })}
                  </div>
                </div>
              )}

              {/* Typologie : le pendant du bouton présent sur le panneau du local. Un
                  bâtiment mal classé se ramène sous son vrai porteur. */}
              {targetBuilding && targetBuilding.id !== inspectedBuilding.id && (
                <div style={{ marginTop: 10, borderTop: BORDER, paddingTop: 10 }}>
                  <div style={{ fontSize: 11, color: TEXT_MUTED, textTransform: "uppercase", marginBottom: 6 }}>
                    Typologie
                  </div>
                  <button
                    type="button"
                    style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px" }}
                    disabled={reclassifyMutation.isPending}
                    title="Ce bâtiment est en réalité un local : le ramener sous le bâtiment actuellement ciblé."
                    onClick={() => {
                      if (
                        !window.confirm(
                          `Faire de « ${inspectedBuilding.nom_batiment} » un LOCAL de ` +
                            `« ${targetBuilding.nom_batiment} » ?

` +
                            "Son adresse, sa position, son cadastre et ses biens ASTECH le suivent.",
                        )
                      ) {
                        return;
                      }
                      reclassifyMutation.mutate({
                        kind: "buildingToLocal",
                        building: inspectedBuilding,
                        parentId: targetBuilding.id,
                      });
                    }}
                  >
                    → En faire un local de « {targetBuilding.nom_batiment} »
                  </button>
                </div>
              )}
              {selected && selected.building_id !== inspectedBuilding.id && (
                <div style={{ marginTop: 10 }}>
                  <button
                    type="button"
                    style={btnPrimary}
                    onClick={() => {
                      updateMutation.mutate({
                        id: selected.id,
                        payload: { building_id: inspectedBuilding.id },
                      });
                      setFlash(
                        `« ${assetLabel(selected)} » rattaché — il prend le nom du bâtiment Po2.`,
                      );
                    }}
                  >
                    Rattacher « {assetLabel(selected)} » à ce bâtiment
                  </button>
                </div>
              )}
            </div>
          )}

          <div style={card}>
            {!selected && <p style={{ color: TEXT_MUTED, margin: 0 }}>Sélectionne un bien dans la liste.</p>}
            {selected && (
              <>
                {/* Nom éditable : le fichier historique contient des libellés fautifs
                    ou tronqués, et c'est ce nom qui repartira dans ASTECH. Le CODE_BIEN
                    reste affiché mais jamais modifiable : c'est la clé de réinjection. */}
                <div style={{ display: "flex", gap: 8, alignItems: "center", margin: "0 0 10px" }}>
                  <span
                    title="Code bien ASTECH — clé de réinjection, jamais modifiable"
                    style={{ fontFamily: "monospace", color: "#c4b5fd", fontSize: 13 }}
                  >
                    {selected.code_bien}
                  </span>
                  <input
                    value={assetNameDraft}
                    onChange={(event) => setAssetNameDraft(event.target.value)}
                    style={{ ...input, flex: 1, fontSize: 14 }}
                    title="Nom du bien ASTECH. Modifiable : c'est lui qui repartira dans le fichier de retour."
                    onKeyDown={(event) => {
                      if (event.key === "Enter") saveAssetName();
                      if (event.key === "Escape") setAssetNameDraft(assetLabel(selected));
                    }}
                  />
                  {/* Enregistrement explicite : la sauvegarde à la sortie du champ
                      partait au moindre clic ailleurs, sans qu'on sache si elle avait
                      eu lieu. Le bouton n'apparaît que si le nom a changé. */}
                  {assetNameDraft.trim() !== "" && assetNameDraft !== assetLabel(selected) && (
                    <>
                      <button type="button" style={btnPrimary} onClick={saveAssetName}>
                        Enregistrer
                      </button>
                      <button
                        type="button"
                        style={btnSecondary}
                        onClick={() => setAssetNameDraft(assetLabel(selected))}
                      >
                        Annuler
                      </button>
                    </>
                  )}
                </div>
                <dl
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                    gap: 10,
                    margin: "0 0 12px",
                  }}
                >
                  {[
                    ["Désignation ASTECH", selected.designation ?? "—"],
                    ["Adresse ASTECH", assetAddress(selected) ?? "— (à reconstituer)"],
                    [
                      "Nom retenu",
                      selected.resolved_name ?? "— (rattache le bien à un bâtiment Po2)",
                    ],
                    [
                      "Adresse trouvée",
                      selected.resolved_label
                        ? `${selected.resolved_label}${
                            selected.resolved_source === "building"
                              ? " (bâtiment Po2)"
                              : " (point sur la carte)"
                          }`
                        : "— (déplace le point sur la carte)",
                    ],
                    [
                      "Cadastre trouvé",
                      selected.resolved_refcad ??
                        (selected.resolved_section && selected.resolved_numero_plan
                          ? `${selected.resolved_section} ${selected.resolved_numero_plan} (hors format ASTECH)`
                          : "— (rattache le bien à un bâtiment Po2)"),
                    ],
                    ["Cadastre ASTECH", selected.source_refcad ?? "— (à récupérer via IGN)"],
                    ["Statut", STATUS_LABEL[selected.status] ?? selected.status],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <dt style={{ fontSize: 11, color: TEXT_MUTED, textTransform: "uppercase" }}>{label}</dt>
                      <dd style={{ margin: 0, fontSize: 13 }}>{value}</dd>
                    </div>
                  ))}
                </dl>


                {/* --- RATTACHEMENT : un seul bloc -------------------------------
                    « Candidat proposé » et « Cible » affichaient LE MÊME bâtiment sous
                    deux étiquettes différentes — `targetBuilding` retombe sur le
                    candidat tant qu'aucun lien n'existe. On lisait donc deux fois le
                    même nom, avec deux blocs d'actions séparés.
                    Un seul bloc : l'entité visée, son niveau, son adresse, son état, et
                    toutes les actions à la suite. */}
                {targetBuilding && (
                  <div
                    style={{
                      borderTop: BORDER,
                      // Liseré bleu Po2 : tout ce bloc décrit l'entité Po2 visée, pas le
                      // bien ASTECH. La carte parle déjà ce langage — violet = ASTECH,
                      // bleu = Po2 — le panneau doit le parler aussi.
                      borderLeft: "3px solid #38bdf8",
                      paddingTop: 10,
                      paddingLeft: 10,
                      marginBottom: 10,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "baseline",
                        gap: 8,
                        marginBottom: 4,
                      }}
                    >
                      <span style={{ fontSize: 11, color: "#7dd3fc", textTransform: "uppercase", fontWeight: 600 }}>
                        Rattachement à une entité Po2
                      </span>
                      <span
                        style={{
                          ...pillStyle,
                          color:
                            selected.building_id == null
                              ? "#93c5fd"
                              : selected.status === "propose"
                                ? "#fbbf24"
                                : "#4ade80",
                          background:
                            selected.building_id == null
                              ? "rgba(147, 197, 253, 0.16)"
                              : selected.status === "propose"
                                ? "rgba(251, 191, 36, 0.16)"
                                : "rgba(34, 197, 94, 0.18)",
                        }}
                      >
                        {selected.building_id == null
                          ? `proposé par le moteur${
                              selected.candidate_score != null
                                ? ` · ${Math.round(selected.candidate_score * 100)} %`
                                : ""
                            }`
                          : selected.status === "propose"
                            ? "à confirmer"
                            : "validé"}
                      </span>
                    </div>

                    <div style={{ fontSize: 14, fontWeight: 500, color: "#7dd3fc" }}>
                      {selected.target_type === "local"
                        ? localsById.get(selected.local_id ?? -1)?.nom_local ?? "Local"
                        : targetBuilding.nom_batiment}
                      <span style={{ color: TEXT_MUTED, fontSize: 12, fontWeight: 400 }}>
                        {" · "}
                        {selected.target_type === "local"
                          ? `local de ${targetBuilding.nom_batiment}`
                          : "bâtiment entier"}
                      </span>
                    </div>
                    {targetBuilding.adresse_reconstituee && (
                      <div style={{ fontSize: 12, color: TEXT_MUTED }}>
                        {targetBuilding.adresse_reconstituee}
                      </div>
                    )}
                    {selected.building_id == null && selected.candidate_reason && (
                      <div style={{ fontSize: 12, color: "#fbbf24", marginTop: 2 }}>
                        ⚠ {selected.candidate_reason}
                      </div>
                    )}

                    {/* Niveau visé : tout le bâtiment, ou l'un de ses locaux. */}
                    {localsOfTarget.length > 0 && (
                      <label
                        style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, color: TEXT_MUTED, marginTop: 8 }}
                        title="L'adresse et le cadastre restent toujours ceux du bâtiment porteur."
                      >
                        Niveau
                        <select
                          value={selected.target_type === "local" ? String(selected.local_id ?? "") : ""}
                          onChange={(event) => {
                            const value = event.target.value;
                            updateMutation.mutate({
                              id: selected.id,
                              payload: value
                                ? { local_id: Number(value) }
                                : { building_id: targetBuilding.id },
                            });
                          }}
                          style={{ ...input, width: "auto", padding: "3px 8px", fontSize: 12 }}
                        >
                          <option value="">— tout le bâtiment —</option>
                          {localsOfTarget.map((local) => (
                            <option key={local.id} value={local.id}>
                              {local.nom_local}
                              {local.niveau ? ` (${local.niveau})` : ""}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}

                    {/* Toutes les actions à la suite, plutôt qu'éparpillées en trois blocs. */}
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
                      {selected.building_id == null && selected.candidate_building_id != null && (
                        <>
                          <button
                            type="button"
                            style={btnPrimary}
                            onClick={() =>
                              updateMutation.mutate(
                                { id: selected.id, payload: { building_id: selected.candidate_building_id } },
                                {
                                  onSuccess: () => {
                                    setFlash(`« ${assetLabel(selected)} » rattaché — il prend le nom du bâtiment Po2.`);
                                    goToNextAsset(selected.id);
                                  },
                                },
                              )
                            }
                          >
                            Valider
                          </button>
                          <button
                            type="button"
                            style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px" }}
                            title="Rejette la suggestion. Le bien reste à traiter : pose son point puis rattache-le."
                            onClick={() =>
                              updateMutation.mutate(
                                { id: selected.id, payload: { clear_candidate: true } },
                                {
                                  onSuccess: () =>
                                    setFlash(
                                      "Proposition écartée. Le bien reste à traiter : pose son point sur la carte, " +
                                        "puis dépose-le sur un bâtiment ou un local Po2.",
                                    ),
                                },
                              )
                            }
                          >
                            Écarter
                          </button>
                        </>
                      )}
                      {selected.building_id != null && (
                        <button
                          type="button"
                          style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px" }}
                          onClick={() => detachAsset(selected.id)}
                        >
                          Détacher
                        </button>
                      )}
                      <button
                        type="button"
                        style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px" }}
                        onClick={() => setPickerOpen((open) => !open)}
                      >
                        {pickerOpen ? "Fermer la liste" : "Changer de bâtiment…"}
                      </button>
                      {selected.building_id != null && selected.target_type !== "local" && (
                        <button
                          type="button"
                          style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px" }}
                          disabled={toLocalMutation.isPending}
                          title="Crée le local dans Po2 et y rattache ce bien. Il garde l'adresse et le cadastre du bâtiment."
                          onClick={() => toLocalMutation.mutate(selected.id)}
                        >
                          {toLocalMutation.isPending ? "Création…" : "En faire un local"}
                        </button>
                      )}
                      <button
                        type="button"
                        style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px", color: TEXT_MUTED }}
                        title="Sort ce bien du parcours de rapprochement."
                        onClick={() =>
                          updateMutation.mutate(
                            { id: selected.id, payload: { status: "ignore" } },
                            {
                              onSuccess: () => {
                                setFlash(
                                  `« ${assetLabel(selected)} » ignoré : il sort du parcours. ` +
                                    "Tu le retrouveras avec le filtre « Ignoré ».",
                                );
                                goToNextAsset(selected.id);
                              },
                            },
                          )
                        }
                      >
                        Ignorer ce bien
                      </button>
                    </div>

                    {/* La fratrie : qui d'autre vise ce bâtiment, et à quel niveau. */}
                    {siblingAssets.length > 1 && (
                      <div style={{ marginTop: 10, padding: "6px 8px", border: BORDER, borderRadius: 8, fontSize: 12 }}>
                        <div style={{ color: TEXT_MUTED, marginBottom: 3 }}>
                          {siblingAssets.length} biens ASTECH désignent ce bâtiment :
                        </div>
                        {siblingAssets.map((sibling) => (
                          <div key={sibling.id} style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
                            <span>{sibling.target_type === "local" ? "  ›" : "▪"}</span>
                            <button
                              type="button"
                              onClick={() => setSelectedId(sibling.id)}
                              style={{
                                border: "none",
                                background: "transparent",
                                padding: 0,
                                fontSize: 12,
                                cursor: "pointer",
                                textAlign: "left",
                                color: sibling.id === selected.id ? "#e9d5ff" : TEXT,
                                fontWeight: sibling.id === selected.id ? 600 : 400,
                              }}
                            >
                              {assetLabel(sibling)}
                            </button>
                            <span style={{ color: TEXT_MUTED }}>
                              {sibling.target_type === "local" ? "local" : "bâtiment entier"}
                            </span>
                            <button
                              type="button"
                              title="Détacher ce bien"
                              onClick={() => detachAsset(sibling.id)}
                              style={{
                                marginLeft: "auto",
                                border: "1px solid rgba(248, 113, 113, 0.4)",
                                background: "transparent",
                                color: "#fca5a5",
                                borderRadius: 6,
                                padding: "1px 7px",
                                fontSize: 11,
                                cursor: "pointer",
                              }}
                            >
                              Détacher
                            </button>
                          </div>
                        ))}
                        {siblingAssets.filter((s) => s.target_type !== "local").length > 1 && (
                          <div style={{ marginTop: 5, color: "#fbbf24" }}>
                            ⚠ Plusieurs visent le <strong>bâtiment entier</strong>. En principe un seul
                            le désigne, les autres sont des locaux.
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}


                {/* Rapprochement manuel : le moteur ne propose rien pour environ un
                    quart des biens, et sa proposition peut être fausse.
                    Le bouton qui ouvrait cette liste vit désormais dans le bloc
                    « Rattachement » avec les autres actions — il était ici en double. */}
                <div style={{ marginBottom: 10 }}>
                  {!targetBuilding && (
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", borderTop: BORDER, paddingTop: 10 }}>
                      <button
                        type="button"
                        style={btnSecondary}
                        onClick={() => setPickerOpen((open) => !open)}
                      >
                        {pickerOpen ? "Fermer la liste" : "Choisir un bâtiment Po2…"}
                      </button>
                      <span style={{ fontSize: 12, color: TEXT_MUTED }}>
                        ou clique un point bleu sur la carte
                      </span>
                    </div>
                  )}

                  {pickerOpen && (
                    <div style={{ marginTop: 8 }}>
                      <input
                        type="search"
                        style={input}
                        placeholder="Filtrer les bâtiments Po2 par nom ou adresse…"
                        value={buildingSearch}
                        onChange={(event) => setBuildingSearch(event.target.value)}
                      />
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 4,
                          maxHeight: 240,
                          overflowY: "auto",
                          marginTop: 6,
                        }}
                      >
                        {buildingMatches.length === 0 && (
                          <span style={{ fontSize: 12, color: TEXT_MUTED }}>
                            Aucun bâtiment Po2 ne correspond.
                          </span>
                        )}
                        {buildingMatches.map((building) => (
                          <button
                            key={building.id}
                            type="button"
                            style={{
                              ...btnSecondary,
                              textAlign: "left",
                              padding: "6px 10px",
                              fontSize: 12,
                            }}
                            onClick={() => {
                              updateMutation.mutate({
                                id: selected.id,
                                payload: { building_id: building.id },
                              });
                              setPickerOpen(false);
                              setFlash(
                                `« ${assetLabel(selected)} » rattaché — le bâtiment Po2 porte désormais ce nom.`,
                              );
                            }}
                          >
                            <strong>{building.nom_batiment}</strong>
                            {building.adresse_reconstituee && (
                              <span style={{ color: TEXT_MUTED }}>
                                {" "}
                                — {building.adresse_reconstituee}
                              </span>
                            )}
                            {(buildingAmbiguities.get(building.id)?.sameName ?? 1) > 1 && (
                              <span style={{ color: "#fbbf24" }}>
                                {" "}
                                ⚠ {buildingAmbiguities.get(building.id)!.sameName} bâtiments portent
                                ce nom — c'est l'adresse qui les distingue
                              </span>
                            )}
                            {(buildingAmbiguities.get(building.id)?.sameIgn ?? 1) > 1 && (
                              <span style={{ color: "#fbbf24" }}> ⚠ même empreinte IGN qu'un autre</span>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* --- OÙ EST-IL ? Les deux gestes de positionnement, réunis ---------
                    Ils occupaient deux blocs séparés avec chacun son paragraphe, soit la
                    moitié de la colonne pour une action ponctuelle. Un seul bloc, deux
                    boutons côte à côte, une ligne d'aide. */}
                <div style={{ borderTop: BORDER, paddingTop: 10, marginBottom: 10 }}>
                  <div style={{ fontSize: 11, color: TEXT_MUTED, textTransform: "uppercase", marginBottom: 6 }}>
                    Positionner le point
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {assetAddress(selected) && (
                      <button
                        type="button"
                        style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px" }}
                        disabled={geocodeAstechMutation.isPending}
                        title="Géocode l'adresse du fichier ASTECH. Sans numéro de voirie, le point se pose au milieu de la voie."
                        onClick={() => geocodeAstechMutation.mutate(selected)}
                      >
                        {geocodeAstechMutation.isPending ? "Recherche…" : "Sur l'adresse ASTECH"}
                      </button>
                    )}
                    <button
                      type="button"
                      style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px" }}
                      disabled={mapCenter === null || updateMutation.isPending}
                      title="Pose le point au centre de la vue actuelle, puis affine en le faisant glisser."
                      onClick={() => {
                        if (!mapCenter) return;
                        updateMutation.mutate(
                          {
                            id: selected.id,
                            payload: { latitude: mapCenter.lat, longitude: mapCenter.lon },
                          },
                          {
                            onSuccess: () =>
                              setFlash(
                                `Point de « ${assetLabel(selected)} » posé au centre de la vue. ` +
                                  "Fais-le glisser, ou dépose-le sur un bâtiment ou un local Po2 pour le rattacher.",
                              ),
                          },
                        );
                      }}
                    >
                      Au centre de la carte
                    </button>
                  </div>
                  <p style={{ margin: "6px 0 0", fontSize: 11, color: TEXT_MUTED }}>
                    Puis fais glisser le point : déposé sur un bâtiment ou un local Po2, il s'y rattache.
                  </p>
                </div>


                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    flexWrap: "wrap",
                    alignItems: "center",
                    borderTop: BORDER,
                    paddingTop: 10,
                  }}
                >
                  {!attachMode && (
                    <button
                      type="button"
                      style={{ ...btnPrimary, opacity: targetBuilding ? 1 : 0.5 }}
                      disabled={!targetBuilding}
                      title={targetBuilding ? undefined : "Rattache d'abord ce bien à un bâtiment Po2."}
                      onClick={() => setAttachMode(true)}
                    >
                      Attribuer IGN
                    </button>
                  )}
                  {attachMode && (
                    <>
                      <label style={{ fontSize: 12, color: TEXT_MUTED }}>
                        Rayon&nbsp;
                        <select
                          value={attachRadius}
                          onChange={(event) => setAttachRadius(Number(event.target.value))}
                          style={{ ...input, width: "auto", padding: "4px 8px" }}
                        >
                          <option value={200}>200 m</option>
                          <option value={400}>400 m</option>
                          <option value={800}>800 m</option>
                          <option value={1500}>1,5 km</option>
                        </select>
                      </label>
                      <span style={{ fontSize: 12, color: TEXT_MUTED }}>
                        Clique les polygones jaunes sur la carte ({attachSelection.length} sélectionné
                        {attachSelection.length > 1 ? "s" : ""}).
                      </span>
                      <button
                        type="button"
                        style={{ ...btnPrimary, opacity: attachSelection.length === 0 ? 0.5 : 1 }}
                        disabled={attachSelection.length === 0 || attachMutation.isPending}
                        onClick={() => attachMutation.mutate()}
                      >
                        {attachMutation.isPending ? "Attribution…" : "Confirmer l'attribution"}
                      </button>
                      <button type="button" style={btnSecondary} onClick={() => setAttachMode(false)}>
                        Annuler
                      </button>
                    </>
                  )}
                  {!targetBuilding && (
                    <>
                      <button
                        type="button"
                        style={btnSecondary}
                        disabled={createBuildingMutation.isPending}
                        onClick={() => createBuildingMutation.mutate()}
                      >
                        {createBuildingMutation.isPending
                          ? "Création…"
                          : "Créer ce bâtiment dans Po2"}
                      </button>
                      <span style={{ fontSize: 12, color: TEXT_MUTED }}>
                        Ce bien n'existe pas encore dans Po2. Place le point sur la carte, crée le
                        bâtiment, puis attribue-lui son bâtiment IGN.
                      </span>
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
