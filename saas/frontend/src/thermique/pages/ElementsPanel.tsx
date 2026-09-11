import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../../providers/AuthProvider";
import { elementSignals, elementTableLabel, normalizeSearch, wallApi } from "../library";

const valueFormat = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 3 });
const dateFormat = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" });

export function useElements() {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["thermique", "bibliotheque", "elements"],
    queryFn: () => wallApi.elements(token!),
    enabled: Boolean(token),
    staleTime: Infinity,
  });
}

// Résistances tabulées des fascicules « applications » : briques, blocs, planchers, isolants en vrac, cloisons.
export function ElementsPanel() {
  const [family, setFamily] = useState("tout");
  const [search, setSearch] = useState("");
  const [tableId, setTableId] = useState("");
  const { data, isLoading, error } = useElements();

  if (isLoading) {
    return <p className="th-muted">Chargement des éléments…</p>;
  }
  if (error || !data) {
    return <p className="th-alert th-alert--error">{error?.message ?? "Bibliothèque des éléments indisponible."}</p>;
  }

  const query = normalizeSearch(search.trim());
  const tables = data.tableaux.filter(
    (table) =>
      (family === "tout" || table.famille === family) &&
      (!query || normalizeSearch(`${table.titre} ${table.lignes.map((line) => line.libelle).join(" ")}`).includes(query)),
  );
  const selected = tables.find((table) => table.id === tableId) ?? tables[0];
  const controls = data.controles;

  return (
    <>
      <div className="th-page-head">
        <div>
          <p className="po2-eyebrow">Bibliothèque de composants</p>
          <h1>Éléments à résistance tabulée</h1>
          <p className="th-muted">
            {data.regles} · mis à jour le {dateFormat.format(new Date(data.edition))} · extrait le {dateFormat.format(new Date(data.extrait_le))}
          </p>
        </div>
      </div>

      <section className="po2-card th-section">
        <div className="po2-card__body">
          <p className={controls.erreurs.length ? "th-alert th-alert--error" : "th-alert th-alert--ok"}>
            <strong>Contrôles automatiques</strong> : {controls.erreurs.length} erreur(s), {controls.alertes.length} alerte(s) sur{" "}
            {controls.comptes.valeurs} valeurs de {controls.comptes.tableaux} tableaux, dont {controls.comptes.tableaux_image} imprimés en
            image dans le document et transcrits. {controls.methode}
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
          {Object.values(data.regles_usage).map((rule) => (
            <p key={rule} className="th-muted">
              {rule}
            </p>
          ))}
        </div>
      </section>

      <section className="po2-card th-section">
        <div className="po2-card__header">
          <div>
            <h2>{tables.length} tableau(x)</h2>
          </div>
          <div className="th-actions">
            <select value={family} onChange={(event) => setFamily(event.target.value)} aria-label="Famille">
              <option value="tout">Toutes les familles</option>
              {data.familles.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.libelle}
                </option>
              ))}
            </select>
            <input value={search} placeholder="Rechercher (ex. parpaing 20)" onChange={(event) => setSearch(event.target.value)} />
            <select value={selected?.id ?? ""} onChange={(event) => setTableId(event.target.value)} aria-label="Tableau" style={{ maxWidth: "28rem" }}>
              {tables.map((table) => (
                <option key={table.id} value={table.id}>
                  {data.fascicules[table.fascicule]} · {elementTableLabel(table)}
                </option>
              ))}
            </select>
          </div>
        </div>
        {selected && (
          <div className="po2-card__body">
            <h3>{selected.titre}</h3>
            <p className="th-muted">
              {data.fascicules[selected.fascicule]} · §{selected.section} · {selected.numero ? `tableau ${selected.numero}` : "figure"} p.{" "}
              {selected.page} · {selected.lecture === "image" ? "imprimé en image dans le document : valeurs transcrites et relues" : "lu dans le texte du document"}
              {selected.isolant && " · couche isolante"} · R en m²·K/W
            </p>
            {Object.entries(selected.variantes).map(([key, label]) => (
              <p key={key} className="th-muted">
                {key === "parentheses" ? "Entre parenthèses" : "Variante"} : {label}
              </p>
            ))}
            {selected.remarques.map((note) => (
              <p key={note} className="th-muted">
                {note}
              </p>
            ))}
            <div className="th-table-wrap" style={{ padding: 0 }}>
              <table className="th-table">
                <thead>
                  <tr>
                    <th>{selected.axe_lignes}</th>
                    {selected.colonnes.map((column, index) => (
                      <th key={index}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {selected.lignes.map((line, row) => (
                    <tr key={row}>
                      <td>{line.libelle}</td>
                      {line.valeurs.map((value, column) => {
                        const signals = elementSignals(selected, row, column);
                        const variants = Object.entries(line.variantes)
                          .map(([key, values]) => ({ key, value: values[column] }))
                          .filter((variant) => variant.value !== null && variant.value !== undefined);
                        return (
                          <td key={column} title={signals.join("\n") || undefined}>
                            {value === null ? (
                              <span className="th-muted">–</span>
                            ) : (
                              <strong>{valueFormat.format(value)}</strong>
                            )}
                            {variants.map((variant) => (
                              <span key={variant.key} className="th-muted">
                                {" "}
                                {variant.key === "parentheses" ? `(${valueFormat.format(variant.value!)})` : `· ${valueFormat.format(variant.value!)}`}
                              </span>
                            ))}
                            {signals.length > 0 && <span className="th-status th-status--a_mettre_a_l_echelle"> à vérifier</span>}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </>
  );
}
