import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchBuildings, fetchHealth, type Building } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

function buildAddressLine(building: Pick<Building, "numero_voirie" | "nature_voie" | "nom_voie" | "adresse_reconstituee" | "nom_commune">) {
  if (building.adresse_reconstituee) {
    return building.adresse_reconstituee;
  }

  const parts = [building.numero_voirie, building.nature_voie, building.nom_voie].filter(Boolean);
  return parts.length > 0 ? `${parts.join(" ")}, ${building.nom_commune}` : building.nom_commune;
}

export function HomePage() {
  const { token, user } = useAuth();
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });
  const buildingsQuery = useQuery({
    queryKey: ["buildings", "home", token],
    queryFn: () => fetchBuildings(token as string),
    enabled: Boolean(token),
  });
  const recentBuildings = buildingsQuery.data?.slice(0, 3) ?? [];

  return (
    <section className="panel stack-lg">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Accueil</p>
          <h2>Tableau de bord</h2>
          <p>
            {user
              ? `Bienvenue ${user.prenom}. Voici l’état courant de ton périmètre patrimoine.`
              : "Le socle est prêt. Connecte-toi pour accéder à ton périmètre bâtiments et locaux."}
          </p>
        </div>
        <div className="form-actions">
          <Link className="secondary-link" to={user ? "/buildings" : "/login"}>
            {user ? "Voir les bâtiments" : "Se connecter"}
          </Link>
        </div>
      </div>

      <dl className="status-grid">
        <div>
          <dt>Utilisateur</dt>
          <dd>{user ? `${user.prenom} ${user.nom}` : "Non connecté"}</dd>
        </div>
        <div>
          <dt>API</dt>
          <dd>{healthQuery.data?.status ?? (healthQuery.isLoading ? "Vérification..." : "Indisponible")}</dd>
        </div>
        <div>
          <dt>Bâtiments</dt>
          <dd>{user ? (buildingsQuery.data?.length ?? 0) : "-"}</dd>
        </div>
      </dl>

      {healthQuery.error instanceof Error && <p className="error-text">{healthQuery.error.message}</p>}
      {buildingsQuery.error instanceof Error && <p className="error-text">{buildingsQuery.error.message}</p>}

      <div className="section-block">
        <div className="section-heading">
          <h3>Accès rapides</h3>
          <p>Va directement vers les écrans les plus utilisés du MVP.</p>
        </div>
        <div className="resource-list">
          <article className="resource-card">
            <div className="resource-card-header">
              <div>
                <h3>Bâtiments</h3>
                <p>Consulte la liste, crée un bâtiment et ouvre sa fiche.</p>
              </div>
            </div>
            <div className="resource-card-actions">
              <Link className="secondary-link" to={user ? "/buildings" : "/login"}>
                Ouvrir
              </Link>
            </div>
          </article>
          <article className="resource-card">
            <div className="resource-card-header">
              <div>
                <h3>Compte</h3>
                <p>Gère tes informations personnelles et ton mot de passe.</p>
              </div>
            </div>
            <div className="resource-card-actions">
              <Link className="secondary-link" to={user ? "/account" : "/login"}>
                Ouvrir
              </Link>
            </div>
          </article>
        </div>
      </div>

      {user && (
        <div className="section-block">
          <div className="section-heading">
            <h3>Derniers bâtiments</h3>
            <p>Accès rapide aux bâtiments récemment créés ou consultables dans ton périmètre.</p>
          </div>
          {buildingsQuery.isLoading && <p>Chargement des bâtiments...</p>}
          {!buildingsQuery.isLoading && recentBuildings.length === 0 && (
            <div className="empty-state">
              <strong>Aucun bâtiment disponible.</strong>
              <span>Commence par créer ton premier bâtiment depuis l’écran dédié.</span>
            </div>
          )}
          <div className="resource-list">
            {recentBuildings.map((building) => (
              <article key={building.id} className="resource-card">
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
                    <dt>Source</dt>
                    <dd>{building.source_creation}</dd>
                  </div>
                  <div>
                    <dt>Référence cadastrale</dt>
                    <dd>{[building.prefixe, building.section, building.numero_plan].filter(Boolean).join(" ") || "Non renseignée"}</dd>
                  </div>
                </dl>
                <div className="resource-card-actions">
                  <Link className="secondary-link" to={`/buildings/${building.id}`}>
                    Ouvrir la fiche
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
