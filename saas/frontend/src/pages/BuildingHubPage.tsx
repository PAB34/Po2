import { Link } from "react-router-dom";

import { useAuth } from "../providers/AuthProvider";

export function BuildingHubPage() {
  const { token } = useAuth();

  if (!token) {
    return (
      <section className="panel stack-lg">
        <div className="section-heading">
          <p className="eyebrow">Bâtiments</p>
          <h2>Choisir un mode de création du patrimoine</h2>
          <p>Connecte-toi pour accéder au flux manuel existant ou au nouveau flux d'import patrimonial.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel stack-lg buildings-workspace-panel">
      <div className="panel-header">
        <div className="section-heading">
          <p className="eyebrow">Bâtiments</p>
          <h2>Choisir un mode de création du patrimoine</h2>
          <p>
            Pour le MVP, tu peux soit continuer à créer les bâtiments avec le flux actuel basé sur les adresses DGFIP et le
            rapprochement IGN, soit tester le nouveau module d'import de patrimoine externe.
          </p>
        </div>
      </div>

      <div className="workflow-choice-grid">
        <article className="resource-card workflow-choice-card">
          <div className="resource-card-header">
            <div>
              <h3>Solution actuelle déjà fonctionnelle</h3>
              <p>Créer le patrimoine à partir des adresses DGFIP, du nom de commune et du rapprochement avec les objets IGN.</p>
            </div>
            <span className="resource-badge">Recommandé</span>
          </div>
          <dl className="resource-metadata">
            <div>
              <dt>Usage</dt>
              <dd>Créer ou compléter les bâtiments un par un avec le flux historique.</dd>
            </div>
            <div>
              <dt>Points forts</dt>
              <dd>Flux validé, carte, sélection IGN, saisie manuelle du nom du bâtiment.</dd>
            </div>
          </dl>
          <div className="resource-card-actions">
            <Link className="secondary-link" to="/buildings/manual">
              Ouvrir le flux actuel
            </Link>
          </div>
        </article>

        <article className="resource-card workflow-choice-card">
          <div className="resource-card-header">
            <div>
              <h3>Nouvelle solution d'import patrimonial</h3>
              <p>Téléverser un fichier utilisateur, mapper ses colonnes, prévisualiser puis lancer l'import.</p>
            </div>
            <span className="resource-badge">Test</span>
          </div>
          <dl className="resource-metadata">
            <div>
              <dt>Usage</dt>
              <dd>Tester l'import d'un inventaire externe au format CSV, XLS, XLSX ou XLSM.</dd>
            </div>
            <div>
              <dt>Points forts</dt>
              <dd>Analyse du fichier, mapping des colonnes, preview bâtiments / locaux, provenance des données.</dd>
            </div>
          </dl>
          <div className="resource-card-actions">
            <Link className="secondary-link" to="/buildings/import">
              Tester l'import
            </Link>
          </div>
        </article>
      </div>
    </section>
  );
}
