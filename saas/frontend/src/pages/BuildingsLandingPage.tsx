import { Link } from "react-router-dom";

import { useAuth } from "../providers/AuthProvider";

export function BuildingsLandingPage() {
  const { token } = useAuth();

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
            Choisis l’espace de travail correspondant à ton besoin. Pour ce lot, l’entrée <strong>Créer / Modifier bâtiments</strong> est pleinement opérationnelle.
          </p>
        </div>
      </div>

      <div className="buildings-entry-grid">
        <article className="resource-card buildings-entry-card buildings-entry-card-primary">
          <div className="section-heading">
            <h3>Créer / Modifier bâtiments</h3>
            <p>
              Importe un listing patrimoine ou travaille à partir de la liste vierge DGFIP / MAJIC, puis rattache les adresses aux bâtiments IGN.
            </p>
          </div>
          <div className="resource-card-actions">
            <Link className="secondary-link buildings-entry-link" to="/buildings/create-edit">
              Ouvrir cet espace
            </Link>
          </div>
        </article>

        <article className="resource-card buildings-entry-card">
          <div className="section-heading">
            <h3>Liste des bâtiments</h3>
            <p>Entrée dédiée à la consultation transverse du parc bâtimentaire.</p>
          </div>
          <span className="resource-badge">Bientôt disponible</span>
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
