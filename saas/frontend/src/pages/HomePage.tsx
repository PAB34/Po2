import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchHealth } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

export function HomePage() {
  const { token, user } = useAuth();
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });

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
      </dl>

      {healthQuery.error instanceof Error && <p className="error-text">{healthQuery.error.message}</p>}

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
    </section>
  );
}
