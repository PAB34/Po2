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

import { BuildingPortfolioMap, type LegacyMapPoint } from "../components/BuildingPortfolioMap";
import { useAuth } from "../providers/AuthProvider";
import {
  attachBuildingIgnRequest,
  computeLegacyCandidates,
  confirmLegacyProposals,
  fetchAllLocals,
  fetchBuildings,
  createBuildingRequest,
  createLegacyAssetFromBuilding,
  fetchFreeAddressLookup,
  fetchIgnBuildingsAtPoint,
  fetchLegacyAssets,
  fetchLegacyCounts,
  importLegacyAstechFile,
  moveBuildingRequest,
  updateLegacyAsset,
  type Building,
  type GeoJsonFeature,
  type GeoJsonFeatureCollection,
  type LegacyAsset,
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

  // Les biens deja rattaches sont charges a part : la liste de gauche est filtree
  // (« a traiter » par defaut), or la carte doit montrer l'avancement en permanence.
  const linkedAssetsQuery = useQuery({
    queryKey: ["legacy-assets", "lie"],
    queryFn: () => fetchLegacyAssets(token!, { status: "lie", limit: 2000 }),
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

  const invalidate = () => {
    // La cle ["legacy-assets"] couvre aussi ["legacy-assets", "lie"] : la couche
    // violette de la carte se met a jour des qu'un rattachement change.
    void queryClient.invalidateQueries({ queryKey: ["legacy-assets"] });
    void queryClient.invalidateQueries({ queryKey: ["legacy-counts"] });
  };

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
      setFlash(
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
          `${result.proposed} candidat(s) proposé(s) sur ${result.scanned} bien(s).`,
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
  }, [selectedId]);

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
      };
    };

    const byId = new Map<number, LegacyMapPoint>();
    for (const asset of linkedAssetsQuery.data ?? []) {
      const point = toPoint(asset);
      if (point) byId.set(point.id, point);
    }
    if (selected) {
      const point = toPoint(selected);
      if (point) byId.set(point.id, point);
    }
    return [...byId.values()];
  }, [buildingsById, linkedAssetsQuery.data, selected]);

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
      </div>

      {flash && (
        <div
          role="status"
          onClick={() => setFlash(null)}
          style={{ fontSize: 13, color: "#0369a1", marginBottom: 12, cursor: "pointer" }}
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

      <div style={{ display: "grid", gridTemplateColumns: "minmax(280px, 360px) 1fr", gap: 16, alignItems: "start" }}>
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
          <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 620, overflowY: "auto" }}>
            {assets.map((asset) => {
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
                  {asset.candidate_label && (
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

        {/* --- Carte + panneau d'action -------------------------------------- */}
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
              setInspectedBuildingId(buildingId);
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
            onDropLegacyOnBuilding={(id, buildingId) => {
              // Déposer le point ASTECH sur un point Po2 vaut rattachement : le bien
              // reprend l'adresse et la position du bâtiment.
              const building = buildingsById.get(buildingId);
              updateMutation.mutate({ id, payload: { building_id: buildingId } });
              setFlash(
                `Rattaché à « ${building?.nom_batiment ?? buildingId} » : le bien reprend son ` +
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
              Apparié ASTECH + Po2 ({linkedAssetsQuery.data?.length ?? 0})
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#a855f7", border: "2px solid #fff", display: "inline-block" }} />
              Bien ASTECH non rattaché
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#2563eb", border: "2px solid #38bdf8", display: "inline-block" }} />
              Bâtiment Po2
            </span>
          </div>

          {inspectedBuilding && (
            <div style={{ ...card, borderColor: "rgba(56, 189, 248, 0.55)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontSize: 11, color: "#7dd3fc", textTransform: "uppercase" }}>
                    Bâtiment Po2 — déplaçable sur la carte
                  </div>
                  <h3 style={{ margin: "2px 0 8px", fontSize: 15 }}>{inspectedBuilding.nom_batiment}</h3>
                </div>
                <button type="button" style={btnSecondary} onClick={() => setInspectedBuildingId(null)}>
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
                        `« ${assetLabel(selected)} » rattaché à « ${inspectedBuilding.nom_batiment} ».`,
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
                <h3 style={{ margin: "0 0 10px", fontSize: 15 }}>
                  <span style={{ fontFamily: "monospace", color: "#c4b5fd" }}>{selected.code_bien}</span>{" "}
                  — {assetLabel(selected)}
                </h3>
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

                {selected.candidate_label && selected.status !== "lie" && (
                  <div style={{ borderTop: BORDER, paddingTop: 10, marginBottom: 10 }}>
                    <p style={{ margin: "0 0 4px", fontSize: 13 }}>
                      Candidat proposé : <strong>{selected.candidate_label}</strong>{" "}
                      <span style={{ color: scoreColor(selected.candidate_score) }}>
                        {selected.candidate_score != null
                          ? `${Math.round(selected.candidate_score * 100)} %`
                          : ""}
                      </span>
                    </p>
                    {selected.candidate_reason && (
                      <p style={{ margin: "0 0 8px", fontSize: 12, color: TEXT_MUTED }}>
                        Motif : {selected.candidate_reason}
                      </p>
                    )}
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <button
                        type="button"
                        style={btnPrimary}
                        onClick={() =>
                          updateMutation.mutate({
                            id: selected.id,
                            payload: { building_id: selected.candidate_building_id },
                          })
                        }
                      >
                        Valider ce rattachement
                      </button>
                      <button
                        type="button"
                        style={btnSecondary}
                        onClick={() =>
                          updateMutation.mutate({ id: selected.id, payload: { status: "ignore" } })
                        }
                      >
                        Écarter
                      </button>
                    </div>
                  </div>
                )}

                {/* Cible du rattachement. Le site n'est pas proposé (décision Q15) :
                    il n'a ni position ni cadastre à transmettre à ASTECH. */}
                {targetBuilding && (
                  <div style={{ borderTop: BORDER, paddingTop: 10, marginBottom: 10 }}>
                    <p style={{ margin: "0 0 6px", fontSize: 13 }}>
                      Cible :{" "}
                      <strong>
                        {selected.target_type === "local"
                          ? localsById.get(selected.local_id ?? -1)?.nom_local ?? "Local"
                          : targetBuilding.nom_batiment}
                      </strong>{" "}
                      <span style={{ color: TEXT_MUTED, fontSize: 12 }}>
                        ({selected.target_type === "local" ? "local" : "bâtiment"}
                        {selected.target_type === "local"
                          ? ` de ${targetBuilding.nom_batiment}`
                          : ""}
                        )
                      </span>
                    </p>
                    {localsOfTarget.length > 0 && (
                      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                        <label style={{ fontSize: 12, color: TEXT_MUTED }}>
                          Préciser un local&nbsp;
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
                            style={{ ...input, width: "auto", padding: "4px 8px" }}
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
                        <span style={{ fontSize: 12, color: TEXT_MUTED }}>
                          L'adresse et le cadastre restent ceux du bâtiment.
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {selected.status === "lie" && targetBuilding && (
                  <div style={{ borderTop: BORDER, paddingTop: 10, marginBottom: 10 }}>
                    <p style={{ margin: "0 0 8px", fontSize: 13 }}>
                      Rattaché à <strong>{targetBuilding.nom_batiment}</strong>
                      {selected.link_origin === "auto" ? " (reconnaissance automatique)" : ""}
                    </p>
                    <button
                      type="button"
                      style={btnSecondary}
                      onClick={() =>
                        updateMutation.mutate({
                          id: selected.id,
                          payload: { clear_building: true, status: "a_traiter" },
                        })
                      }
                    >
                      Détacher
                    </button>
                  </div>
                )}

                {/* Rapprochement manuel : le moteur ne propose rien pour environ un
                    quart des biens, et sa proposition peut être fausse. Sans ce
                    sélecteur, il n'y a aucun moyen de rattacher ces biens-là. */}
                <div style={{ borderTop: BORDER, paddingTop: 10, marginBottom: 10 }}>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                    <button
                      type="button"
                      style={btnSecondary}
                      onClick={() => setPickerOpen((open) => !open)}
                    >
                      {pickerOpen ? "Fermer la liste" : "Choisir un bâtiment Po2…"}
                    </button>
                    <span style={{ fontSize: 12, color: TEXT_MUTED }}>
                      ou clique directement un point bleu sur la carte
                    </span>
                  </div>

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
                                `« ${assetLabel(selected)} » rattaché à « ${building.nom_batiment} ».`,
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
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
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
