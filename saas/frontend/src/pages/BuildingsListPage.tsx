import { useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { BuildingPortfolioMap } from "../components/BuildingPortfolioMap";
import { fetchBuildings, deleteAllBuildingsRequest, type Building } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

function buildAddressLine(building: Pick<Building, "numero_voirie" | "nature_voie" | "nom_voie" | "adresse_reconstituee" | "nom_commune">) {
  if (building.adresse_reconstituee) {
    return building.adresse_reconstituee;
  }

  const parts = [building.numero_voirie, building.nature_voie, building.nom_voie].filter(Boolean);
  return parts.length > 0 ? `${parts.join(" ")}, ${building.nom_commune}` : building.nom_commune;
}

export function BuildingsListPage() {
  const { token } = useAuth();
  const [search, setSearch] = useState("");
  const [selectedBuildingId, setSelectedBuildingId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const deleteAllMutation = useMutation({
    mutationFn: () => deleteAllBuildingsRequest(token as string),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["buildings"] });
      alert(`${data.deleted} bâtiment(s) supprimé(s).`);
    },
  });

  function handleDeleteAll() {
    const count = buildingsQuery.data?.length ?? 0;
    if (!window.confirm(`Supprimer les ${count} bâtiment(s) de ta ville ? Cette action est irréversible.`)) return;
    deleteAllMutation.mutate();
  }

  const buildingsQuery = useQuery({
    queryKey: ["buildings", token],
    queryFn: () => fetchBuildings(token as string),
    enabled: Boolean(token),
  });

  const filteredBuildings = useMemo(() => {
    const query = search.trim().toLowerCase();
    const buildings = (buildingsQuery.data ?? []) as Building[];
    if (!query) {
      return buildings;
    }
    return buildings.filter((building: Building) => {
      return [
        building.nom_batiment,
        buildAddressLine(building),
        building.nom_commune,
        building.dgfip_reference_norm,
        building.ign_name_proposed,
        building.ign_name,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query));
    });
  }, [buildingsQuery.data, search]);

  const selectedBuilding = useMemo(
    () => filteredBuildings.find((building: Building) => building.id === selectedBuildingId) ?? filteredBuildings[0] ?? null,
    [filteredBuildings, selectedBuildingId],
  );

  const geocodedCount = useMemo(
    () => ((buildingsQuery.data ?? []) as Building[]).filter((building: Building) => building.latitude != null && building.longitude != null).length,
    [buildingsQuery.data],
  );

  const importCount = useMemo(
    () => ((buildingsQuery.data ?? []) as Building[]).filter((building: Building) => building.source_creation === "IMPORT").length,
    [buildingsQuery.data],
  );

  if (!token) {
    return (
      <section className="panel stack-lg">
        <div>
          <h2>Liste des bâtiments</h2>
          <p>Connecte-toi pour consulter la liste patrimoniale et les bâtiments déjà créés.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel stack-lg buildings-workspace-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Bâtiments</p>
          <h2>Liste des bâtiments</h2>
          <p>
            Consulte le parc bâtimentaire validé, localise les bâtiments sur la carte et ouvre une fiche pour les modifier.
          </p>
        </div>
        <div className="buildings-header-actions">
          <Link className="secondary-link" to="/buildings">
            Retour aux entrées bâtiments
          </Link>
          <div className="header-badge">
            <strong>{buildingsQuery.data?.length ?? 0}</strong>
            <span>bâtiment(s)</span>
          </div>
          {(buildingsQuery.data?.length ?? 0) > 0 ? (
            <button
              type="button"
              className="danger-button"
              onClick={handleDeleteAll}
              disabled={deleteAllMutation.isPending}
            >
              {deleteAllMutation.isPending ? "Suppression..." : "Supprimer tout le listing"}
            </button>
          ) : null}
        </div>
      </div>

      {buildingsQuery.isLoading ? <p>Chargement des bâtiments...</p> : null}
      {buildingsQuery.error instanceof Error ? <p className="error-text">{buildingsQuery.error.message}</p> : null}

      {!buildingsQuery.isLoading && !buildingsQuery.error && (buildingsQuery.data?.length ?? 0) === 0 ? (
        <div className="empty-state">
          <strong>Aucune liste patrimoniale validée pour le moment.</strong>
          <span>Commence par constituer ta liste patrimoniale avant d’accéder à cet espace.</span>
          <div className="form-actions">
            <Link className="secondary-link" to="/buildings/create-edit">
              Constituer la liste patrimoniale
            </Link>
          </div>
        </div>
      ) : null}

      {(buildingsQuery.data?.length ?? 0) > 0 ? (
        <>
          <div className="detail-grid">
            <div className="detail-card">
              <span>Bâtiments géolocalisés</span>
              <strong>{geocodedCount}</strong>
            </div>
            <div className="detail-card">
              <span>Créés depuis import</span>
              <strong>{importCount}</strong>
            </div>
            <div className="detail-card">
              <span>Affichés selon le filtre</span>
              <strong>{filteredBuildings.length}</strong>
            </div>
          </div>

          <div className="buildings-list-layout">
            <div className="buildings-main-content">
              <div className="section-block">
                <div className="section-heading">
                  <h3>Carte du parc bâtimentaire</h3>
                  <p>La carte te permet de repérer rapidement les bâtiments validés et de focaliser la liste sur un bâtiment actif.</p>
                </div>
                <BuildingPortfolioMap
                  buildings={filteredBuildings}
                  activeBuildingId={selectedBuilding?.id ?? null}
                  onSelectBuildingId={setSelectedBuildingId}
                />
              </div>

              {selectedBuilding ? (
                <div className="resource-card resource-card-active">
                  <div className="resource-card-header">
                    <div>
                      <h3>{selectedBuilding.nom_batiment || `Bâtiment #${selectedBuilding.id}`}</h3>
                      <p>{buildAddressLine(selectedBuilding)}</p>
                    </div>
                    <span className="resource-badge">{selectedBuilding.statut_geocodage}</span>
                  </div>
                  <dl className="resource-metadata">
                    <div>
                      <dt>Commune</dt>
                      <dd>{selectedBuilding.nom_commune}</dd>
                    </div>
                    <div>
                      <dt>Création</dt>
                      <dd>{selectedBuilding.source_creation}</dd>
                    </div>
                    <div>
                      <dt>Nom IGN proposé</dt>
                      <dd>{selectedBuilding.ign_name_proposed || selectedBuilding.ign_name || "Aucun"}</dd>
                    </div>
                  </dl>
                  <div className="resource-card-actions">
                    <Link className="secondary-link" to={`/buildings/${selectedBuilding.id}`}>
                      Ouvrir la fiche bâtiment
                    </Link>
                  </div>
                </div>
              ) : null}
            </div>

            <aside className="buildings-sidebar">
              <div className="section-block buildings-addresses-section">
                <div className="section-heading">
                  <h3>Parc bâtimentaire</h3>
                  <p>Filtre la liste, active un bâtiment sur la carte, puis ouvre sa fiche pour le modifier.</p>
                </div>
                <label className="field">
                  <span>Recherche par nom, adresse, commune ou référence</span>
                  <input type="text" value={search} onChange={(event: ChangeEvent<HTMLInputElement>) => setSearch(event.target.value)} />
                </label>
                <div className="resource-list buildings-address-list">
                  {filteredBuildings.map((building: Building) => {
                    const isActive = selectedBuilding?.id === building.id;
                    return (
                      <article key={building.id} className={`resource-card ${isActive ? "resource-card-active" : ""}`}>
                        <div className="resource-card-header">
                          <div>
                            <h3>{building.nom_batiment || `Bâtiment #${building.id}`}</h3>
                            <p>{buildAddressLine(building)}</p>
                          </div>
                          <span className="resource-badge">{building.statut_geocodage}</span>
                        </div>
                        <dl className="resource-metadata">
                          <div>
                            <dt>Commune</dt>
                            <dd>{building.nom_commune}</dd>
                          </div>
                          <div>
                            <dt>Référence DGFIP</dt>
                            <dd>
                              {building.dgfip_reference_norm ??
                                ([building.prefixe, building.section, building.numero_plan].filter(Boolean).join(" ") || "Non renseignée")}
                            </dd>
                          </div>
                          <div>
                            <dt>Origine</dt>
                            <dd>{building.source_creation}</dd>
                          </div>
                        </dl>
                        <div className="resource-card-actions">
                          <Link className="secondary-link" to={`/buildings/${building.id}`}>
                            Modifier la fiche
                          </Link>
                          <button type="button" className="secondary-button" onClick={() => setSelectedBuildingId(building.id)}>
                            {isActive ? "Bâtiment actif" : "Afficher sur la carte"}
                          </button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </div>
            </aside>
          </div>
        </>
      ) : null}
    </section>
  );
}
