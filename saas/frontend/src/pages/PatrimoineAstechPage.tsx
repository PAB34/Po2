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
  fetchBuildings,
  createBuildingRequest,
  fetchFreeAddressLookup,
  fetchIgnBuildingsAtPoint,
  fetchLegacyAssets,
  fetchLegacyCounts,
  importLegacyAstechFile,
  updateLegacyAsset,
  type Building,
  type GeoJsonFeature,
  type GeoJsonFeatureCollection,
  type LegacyAsset,
} from "../lib/api";

const STATUS_LABEL: Record<string, string> = {
  a_traiter: "À traiter",
  lie: "Rattaché",
  hors_perimetre: "Hors périmètre",
  a_creer: "À créer",
  ignore: "Ignoré",
};

const STATUS_ORDER = ["a_traiter", "lie", "hors_perimetre", "ignore"] as const;

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
  const selected = useMemo(
    () => assets.find((asset) => asset.id === selectedId) ?? null,
    [assets, selectedId],
  );

  const buildingsById = useMemo(() => {
    const index = new Map<number, Building>();
    for (const building of buildings) index.set(building.id, building);
    return index;
  }, [buildings]);

  // Le bâtiment que pilote l'écran : celui déjà rattaché, sinon le candidat proposé.
  const targetBuilding = useMemo(() => {
    if (!selected) return null;
    const id = selected.building_id ?? selected.candidate_building_id;
    return id != null ? buildingsById.get(id) ?? null : null;
  }, [buildingsById, selected]);

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

  const updateMutation = useMutation({
    mutationFn: (variables: { id: number; payload: Parameters<typeof updateLegacyAsset>[2] }) =>
      updateLegacyAsset(token!, variables.id, variables.payload),
    onSuccess: () => invalidate(),
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
          label: `${asset.code_bien} — ${assetLabel(asset)}`,
          latitude: DEFAULT_LAT,
          longitude: DEFAULT_LON,
          isProvisional: true,
          isLinked: asset.building_id != null,
        };
      }
      return {
        id: asset.id,
        label: `${asset.code_bien} — ${assetLabel(asset)}`,
        latitude,
        longitude,
        isProvisional: asset.latitude == null,
        isLinked: asset.building_id != null,
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

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 16 }}>
        {STATUS_ORDER.map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => setStatusFilter(statusFilter === status ? "" : status)}
            style={{
              ...card,
              textAlign: "left",
              cursor: "pointer",
              border: statusFilter === status ? "1px solid #60a5fa" : BORDER,
              boxShadow: statusFilter === status ? "0 0 0 1px #60a5fa inset" : undefined,
            }}
          >
            <div style={{ fontSize: 13, color: TEXT_MUTED }}>{STATUS_LABEL[status]}</div>
            <div style={{ fontSize: 24, fontWeight: 500, color: TEXT }}>{counts[status] ?? 0}</div>
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
              if (!selected || attachMode) return;
              const building = buildingsById.get(buildingId);
              updateMutation.mutate({ id: selected.id, payload: { building_id: buildingId } });
              setFlash(
                `« ${assetLabel(selected)} » rattaché à « ${building?.nom_batiment ?? buildingId} ». ` +
                  "Utilise « Détacher » si ce n'est pas le bon.",
              );
            }}
            highlightedBuildingIds={targetBuilding ? [targetBuilding.id] : []}
            legacyPoints={legacyPoints}
            activeLegacyId={selected?.id ?? null}
            onSelectLegacyId={(id) => setSelectedId(id)}
            onMoveLegacyPoint={(id, lat, lon) => {
              // Le serveur géocode le point à l'envers et renseigne l'adresse
              // trouvée, à côté de l'adresse ASTECH d'origine (jamais à sa place).
              updateMutation.mutate({ id, payload: { latitude: lat, longitude: lon } });
              setFlash("Position enregistrée, recherche de l'adresse correspondante…");
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
          />

          {/* Légende : sans elle, les trois états du point violet sont indevinables. */}
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center", fontSize: 12, color: TEXT_MUTED }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#7c3aed", border: "2px solid #fff", display: "inline-block" }} />
              Bien ASTECH rattaché ({linkedAssetsQuery.data?.length ?? 0})
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#fff", border: "2px dashed #a855f7", display: "inline-block" }} />
              Position à confirmer
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#2563eb", border: "2px solid #38bdf8", display: "inline-block" }} />
              Bâtiment Po2
            </span>
          </div>

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
                      "Adresse trouvée",
                      selected.resolved_label
                        ? `${selected.resolved_label}${
                            selected.resolved_source === "building"
                              ? " (bâtiment Po2)"
                              : " (point sur la carte)"
                          }`
                        : "— (déplace le point sur la carte)",
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
