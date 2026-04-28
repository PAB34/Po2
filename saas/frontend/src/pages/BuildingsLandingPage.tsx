import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { fetchBuildings } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

export function BuildingsLandingPage() {
  const { token } = useAuth();

  const buildingsQuery = useQuery({
    queryKey: ["buildings", token],
    queryFn: () => fetchBuildings(token as string),
    enabled: Boolean(token),
  });

  const buildingsCount = buildingsQuery.data?.length ?? 0;
  const canAccessBuildingsList = buildingsCount > 0;

  if (!token) {
    return (
      <section className="panel stack-lg">
        <div>
          <h2>Bâtiments</h2>
          <p>Connecte-toi pour accéder aux entrées métier de la section bâtiments.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel stack-lg buildings-entry-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Bâtiments</p>
          <h2>Entrées métier</h2>
          <p>
            Choisis l’espace de travail correspondant à ton besoin. Le parcours principal permet désormais de <strong>constituer la liste patrimoniale</strong> avant d’ouvrir l’espace de consultation et de modification.
          </p>
        </div>
      </div>

      <div className="buildings-entry-grid">
        <article className="resource-card buildings-entry-card buildings-entry-card-primary">
          <div className="section-heading">
            <h3>Constituer la liste patrimoniale</h3>
            <p>
              Démarre un parcours en étapes : choix du mode, préparation de la liste, puis validation de la liste patrimoniale avant exploitation.
            </p>
          </div>
          <div className="resource-card-actions">
            <Link className="secondary-link buildings-entry-link" to="/buildings/create-edit">
              Démarrer le parcours
            </Link>
          </div>
        </article>

        <article className={`resource-card buildings-entry-card ${canAccessBuildingsList ? "" : "resource-card-disabled"}`}>
          <div className="section-heading">
            <h3>Liste des bâtiments</h3>
            <p>Carte du parc bâtimentaire, liste filtrable et accès aux fiches de modification des bâtiments validés.</p>
          </div>
          {canAccessBuildingsList ? (
            <div className="resource-card-actions">
              <Link className="secondary-link buildings-entry-link" to="/buildings/list">
                Ouvrir la liste
              </Link>
            </div>
          ) : (
            <span className="resource-badge">Accessible après constitution de la liste</span>
          )}
        </article>

        <article className="resource-card buildings-entry-card">
          <div className="section-heading">
            <h3>Gestion technique des bâtiments</h3>
            <p>Entrée future pour le pilotage technique, la maintenance et le suivi opérationnel.</p>
          </div>
          <span className="resource-badge">Bientôt disponible</span>
        </article>
      </div>
    </section>
  );
}
