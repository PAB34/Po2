import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../../providers/AuthProvider";
import { normalizeSearch, wallApi } from "../library";

const lambdaFormat = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 4 });
const dateFormat = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" });

export function useMaterials() {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["thermique", "bibliotheque", "materiaux"],
    queryFn: () => wallApi.materials(token!),
    enabled: Boolean(token),
    staleTime: Infinity,
  });
}

export function MaterialsPanel() {
  const [family, setFamily] = useState("tout");
  const [search, setSearch] = useState("");
  const { data, isLoading, error } = useMaterials();

  if (isLoading) {
    return <p className="th-muted">Chargement des matériaux…</p>;
  }
  if (error || !data) {
    return <p className="th-alert th-alert--error">{error?.message ?? "Bibliothèque des matériaux indisponible."}</p>;
  }

  const query = normalizeSearch(search.trim());
  const rows = data.materiaux.filter(
    (material) =>
      (family === "tout" || material.famille === family) &&
      (!query || normalizeSearch(`${material.section_titre} ${material.libelle} ${material.section}`).includes(query)),
  );
  const controls = data.controles;

  return (
    <>
      <div className="th-page-head">
        <div>
          <p className="po2-eyebrow">Bibliothèque de composants</p>
          <h1>Matériaux</h1>
          <p className="th-muted">
            {data.regles} · publié le {dateFormat.format(new Date(data.edition))} · extrait le {dateFormat.format(new Date(data.extrait_le))}
          </p>
        </div>
      </div>

      <section className="po2-card th-section">
        <div className="po2-card__body">
          <p className={controls.erreurs.length ? "th-alert th-alert--error" : "th-alert th-alert--ok"}>
            <strong>Contrôles automatiques</strong> : {controls.erreurs.length} erreur(s), {controls.alertes.length} alerte(s)
            sur {controls.comptes.materiaux} matériaux. {controls.methode}
            {data.verification_constantes.ok && (
              <>
                {" "}
                Les {data.verification_constantes.controles} constantes du calcul de paroi sont retrouvées à l'identique dans le
                fascicule méthodes.
              </>
            )}
          </p>
          {(controls.erreurs.length > 0 || controls.alertes.length > 0) && (
            <details>
              <summary className="th-link">Voir le détail des contrôles</summary>
              <ul>
                {[...controls.erreurs, ...controls.alertes].map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </details>
          )}
          <p className="th-muted">
            {data.regles_usage.valeurs} {data.regles_usage.masse_volumique_inconnue}
          </p>
        </div>
      </section>

      <section className="po2-card th-section">
        <div className="po2-card__header">
          <div>
            <h2>{rows.length} matériau(x)</h2>
          </div>
          <div className="th-actions">
            <select value={family} onChange={(event) => setFamily(event.target.value)} aria-label="Famille">
              <option value="tout">Toutes les familles</option>
              {data.familles.map((item) => (
                <option key={item.section} value={item.section}>
                  {item.section} {item.titre}
                </option>
              ))}
            </select>
            <input value={search} placeholder="Rechercher (ex. laine de verre)" onChange={(event) => setSearch(event.target.value)} />
          </div>
        </div>
        <div className="th-table-wrap">
          <table className="th-table">
            <thead>
              <tr>
                <th>§</th>
                <th>Matériau ou application</th>
                <th>ρ kg/m³</th>
                <th>λ W/(m·K)</th>
                <th>Cp J/(kg·K)</th>
                <th>μ sec / humide</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((material) => (
                <tr key={material.id}>
                  <td className="th-muted">{material.section}</td>
                  <td>
                    {material.libelle !== material.section_titre && <span className="th-muted">{material.section_titre} : </span>}
                    {material.libelle}
                  </td>
                  <td>{material.rho_texte}</td>
                  <td>
                    <strong>{lambdaFormat.format(material.lambda)}</strong>
                    {material.statut !== "valide" && (
                      <span className="th-status th-status--a_mettre_a_l_echelle" title={material.note_texte}>
                        {" "}
                        {material.note_document ? `note ${material.note_document}` : "alerte"}
                      </span>
                    )}
                  </td>
                  <td>{material.cp_texte}</td>
                  <td>
                    {material.mu_sec}
                    {material.mu_humide && ` / ${material.mu_humide}`}
                  </td>
                  <td className="th-muted">p. {material.page}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {data.renvois.length > 0 && (
        <section className="po2-card th-section">
          <div className="po2-card__body">
            <details>
              <summary className="th-link">{data.renvois.length} ligne(s) sans valeur (renvois du document)</summary>
              <ul>
                {data.renvois.map((item, index) => (
                  <li key={index}>
                    §{item.section} p. {item.page} : {item.texte}
                  </li>
                ))}
              </ul>
            </details>
          </div>
        </section>
      )}
    </>
  );
}
