import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../../providers/AuthProvider";
import {
  ORIENTATION_LABELS,
  POSITION_LABELS,
  SOURCE_LABELS,
  VITRAGE_LABELS,
  libraryApi,
  menuiserieLabel,
  type ClosureResult,
  type Statut,
} from "../library";
import { parseDecimal } from "../scale";

type Tab = "fenetres" | "correctifs" | "portes" | "fermetures";

const TABS: { id: Tab; label: string }[] = [
  { id: "fenetres", label: "Fenêtres et portes-fenêtres" },
  { id: "correctifs", label: "Correctifs d'intégration" },
  { id: "portes", label: "Portes" },
  { id: "fermetures", label: "Fermetures, Ujour-nuit" },
];

const VITRAGE_ORDER = ["triple", "double", "double_controle_solaire"];
const decimal2 = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const decimal1 = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 2 });
const dateFormat = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" });

function StatusMark({ statut }: { statut: Statut }) {
  if (statut === "valide") {
    return null;
  }
  return (
    <span className={`th-status ${statut === "erreur" ? "th-status--a_classer" : "th-status--a_mettre_a_l_echelle"}`}>
      {statut === "erreur" ? "Erreur" : "Alerte"}
    </span>
  );
}

export function WindowsLibraryPanel() {
  const { token } = useAuth();
  const [tab, setTab] = useState<Tab>("fenetres");
  const [protection, setProtection] = useState("2.1");
  const [correction, setCorrection] = useState("3.1");
  const [uwInput, setUwInput] = useState("1,8");
  const [rInput, setRInput] = useState("0,19");
  const [result, setResult] = useState<ClosureResult | null>(null);
  const [calcError, setCalcError] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["thermique", "bibliotheque", "menuiseries"],
    queryFn: () => libraryApi.windows(token!),
    enabled: Boolean(token),
    staleTime: Infinity,
  });

  if (isLoading) {
    return <p className="th-muted">Chargement de la bibliothèque…</p>;
  }
  if (error || !data) {
    return <p className="th-alert th-alert--error">{error?.message ?? "Bibliothèque indisponible."}</p>;
  }

  const controls = data.controles;
  const selectedProtection = data.protections.find((item) => item.section === protection) ?? data.protections[0];
  const windowRows = data.fenetres
    .filter((row) => row.section.startsWith(`${protection}.`))
    .sort(
      (a, b) =>
        a.section.localeCompare(b.section, "fr", { numeric: true }) ||
        VITRAGE_ORDER.indexOf(a.vitrage) - VITRAGE_ORDER.indexOf(b.vitrage),
    );
  const withProtection = protection !== "2.1";
  const correctionTable = data.correctifs.find((table) => table.section === correction) ?? data.correctifs[0];

  const computeClosure = async () => {
    const uw = parseDecimal(uwInput);
    const r = parseDecimal(rInput);
    setCalcError(null);
    setResult(null);
    if (!uw || !r) {
      setCalcError("Saisissez un Uw et une résistance R.");
      return;
    }
    try {
      setResult(await libraryApi.closure(token!, uw, r));
    } catch (failure) {
      setCalcError(failure instanceof Error ? failure.message : "Calcul impossible.");
    }
  };

  return (
    <>
      <div className="th-page-head">
        <div>
          <p className="po2-eyebrow">Bibliothèque de composants</p>
          <h1>Menuiseries</h1>
          <p className="th-muted">
            {data.regles} · édition du {dateFormat.format(new Date(data.edition))} · extrait le{" "}
            {dateFormat.format(new Date(data.extrait_le))}
          </p>
        </div>
      </div>

      <section className="po2-card th-section">
        <div className="po2-card__body">
          <p className={controls.erreurs.length ? "th-alert th-alert--error" : "th-alert th-alert--ok"}>
            <strong>Contrôles automatiques</strong> : {controls.erreurs.length} erreur(s), {controls.alertes.length} alerte(s)
            sur {controls.comptes.fenetres} lignes de fenêtres, {controls.comptes.correctifs} lignes de correctifs,{" "}
            {controls.comptes.portes} portes, {controls.comptes.fermetures} fermetures. {controls.methode}
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
            Sources :{" "}
            {Object.entries(data.sources)
              .map(([key, source]) => `${SOURCE_LABELS[key] ?? key} (${source.document}, ${source.pages} p.)`)
              .join(" · ")}
          </p>
        </div>
      </section>

      <div className="th-segmented th-section" role="tablist" aria-label="Familles de menuiseries">
        {TABS.map((item) => (
          <button key={item.id} type="button" className={tab === item.id ? "is-active" : undefined} onClick={() => setTab(item.id)}>
            {item.label}
          </button>
        ))}
      </div>

      {tab === "fenetres" && (
        <section className="po2-card th-section">
          <div className="po2-card__header">
            <div>
              <h2>{selectedProtection.libelle}</h2>
              <p className="th-muted">{data.regles_usage.fenetres}</p>
            </div>
            <select value={protection} onChange={(event) => setProtection(event.target.value)} aria-label="Protection solaire">
              {data.protections.map((item) => (
                <option key={item.section} value={item.section}>
                  {item.libelle}
                </option>
              ))}
            </select>
          </div>
          <div className="th-table-wrap">
            <table className="th-table">
              <thead>
                <tr>
                  <th rowSpan={2}>Menuiserie</th>
                  <th rowSpan={2}>σ</th>
                  <th rowSpan={2}>Vitrage</th>
                  <th rowSpan={2}>{withProtection ? "Uws" : "Uw"} W/(m²·K)</th>
                  <th colSpan={3}>{withProtection ? "Sws" : "Sw"} hiver (C)</th>
                  <th colSpan={3}>{withProtection ? "Sws" : "Sw"} été (E)</th>
                  <th rowSpan={2}>{withProtection ? "TLws" : "TLw"}</th>
                  <th rowSpan={2}>TL diffus</th>
                  <th rowSpan={2}>Source</th>
                </tr>
                <tr>
                  <th>1</th>
                  <th>2</th>
                  <th>3</th>
                  <th>1</th>
                  <th>2</th>
                  <th>3</th>
                </tr>
              </thead>
              <tbody>
                {windowRows.map((row) => (
                  <tr key={row.id}>
                    <td>{menuiserieLabel(row.menuiserie, row.vantaux)}</td>
                    <td>{decimal2.format(row.sigma)}</td>
                    <td>{VITRAGE_LABELS[row.vitrage]}</td>
                    <td>
                      <strong>{decimal1.format(row.u)}</strong> <StatusMark statut={row.statut} />
                      {row.correction && (
                        <div className="th-muted" style={{ fontSize: "0.75rem" }}>
                          Corrigé : {row.correction}
                        </div>
                      )}
                    </td>
                    {[...row.s_c, ...row.s_e].map((value, index) => (
                      <td key={index}>{decimal2.format(value)}</td>
                    ))}
                    <td>{decimal2.format(row.tl)}</td>
                    <td>{decimal2.format(row.tl_dif)}</td>
                    <td className="th-muted">
                      p. {row.page} · §{row.section}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === "correctifs" && correctionTable && (
        <section className="po2-card th-section">
          <div className="po2-card__header">
            <div>
              <h2>{correctionTable.libelle}</h2>
              <p className="th-muted">
                Coefficients à appliquer aux facteurs S (CS) ou TL (CTL) selon l'orientation, la position de la fenêtre dans
                le mur et l'épaisseur de la paroi. Source : p. {correctionTable.page} · §{correctionTable.section}.
              </p>
            </div>
            <select value={correction} onChange={(event) => setCorrection(event.target.value)} aria-label="Correctif">
              {data.correctifs.map((table) => (
                <option key={table.section} value={table.section}>
                  {table.libelle}
                </option>
              ))}
            </select>
          </div>
          <div className="th-table-wrap">
            <table className="th-table">
              <thead>
                <tr>
                  <th rowSpan={3}>Menuiserie</th>
                  {Object.keys(ORIENTATION_LABELS).map((orientation) => (
                    <th key={orientation} colSpan={4}>
                      {ORIENTATION_LABELS[orientation]}
                    </th>
                  ))}
                </tr>
                <tr>
                  {Object.keys(ORIENTATION_LABELS).map((orientation) => (
                    <Fragment key={orientation}>
                      {Object.keys(POSITION_LABELS).map((position) => (
                        <th key={`${orientation}-${position}`} colSpan={2}>
                          {POSITION_LABELS[position]}
                        </th>
                      ))}
                    </Fragment>
                  ))}
                </tr>
                <tr>
                  {correctionTable.colonnes.map((column, index) => (
                    <th key={index}>{column.epaisseur_cm} cm</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {correctionTable.lignes.map((row) => (
                  <tr key={`${row.menuiserie}-${row.vantaux}`}>
                    <td>{menuiserieLabel(row.menuiserie, row.vantaux)}</td>
                    {row.valeurs.map((value, index) => (
                      <td key={index}>{decimal2.format(value)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === "portes" && (
        <section className="po2-card th-section">
          <div className="po2-card__header">
            <h2>Coefficient Ud des portes courantes (valeurs par défaut)</h2>
          </div>
          <div className="th-table-wrap">
            <table className="th-table">
              <thead>
                <tr>
                  <th>Nature</th>
                  <th>Type</th>
                  <th>Ud W/(m²·K)</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {data.portes.map((door) => (
                  <tr key={door.id}>
                    <td>{door.nature}</td>
                    <td>{door.type}</td>
                    <td>
                      <strong>{decimal1.format(door.ud)}</strong> <StatusMark statut={door.statut} />
                    </td>
                    <td className="th-muted">p. {door.page}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === "fermetures" && (
        <div className="th-columns">
          <section className="po2-card th-section">
            <div className="po2-card__header">
              <div>
                <h2>Résistance additionnelle des fermetures</h2>
                <p className="th-muted">Cliquez une fermeture pour la reprendre dans le calcul.</p>
              </div>
            </div>
            <div className="th-table-wrap">
              <table className="th-table">
                <thead>
                  <tr>
                    <th>Fermeture</th>
                    <th>R m²·K/W</th>
                  </tr>
                </thead>
                <tbody>
                  {data.fermetures.map((closure) => (
                    <tr key={closure.id} onClick={() => setRInput(String(closure.r).replace(".", ","))} style={{ cursor: "pointer" }}>
                      <td>{closure.libelle}</td>
                      <td>
                        <strong>{decimal2.format(closure.r)}</strong> <StatusMark statut={closure.statut} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="po2-card th-section">
            <div className="po2-card__header">
              <div>
                <h2>Ujour-nuit et Uws d'une fenêtre avec fermeture</h2>
                <p className="th-muted">{data.regles_usage.ujn_uws}</p>
              </div>
            </div>
            <div className="po2-card__body th-form">
              <label className="th-field">
                <span>Uw de la fenêtre nue, W/(m²·K)</span>
                <input inputMode="decimal" value={uwInput} onChange={(event) => setUwInput(event.target.value)} />
              </label>
              <label className="th-field">
                <span>Résistance R de la fermeture, m²·K/W</span>
                <input inputMode="decimal" value={rInput} onChange={(event) => setRInput(event.target.value)} />
              </label>
              <button type="button" className="po2-button po2-button--primary" onClick={() => void computeClosure()}>
                Calculer
              </button>
              {calcError && <p className="th-alert th-alert--error">{calcError}</p>}
              {result && (
                <div className="th-alert th-alert--ok">
                  Ujour-nuit = <strong>{decimal2.format(result.ujn)}</strong> W/(m²·K)
                  <br />
                  Uws = {result.uws !== null ? <strong>{decimal2.format(result.uws)}</strong> : "non disponible"}
                  {result.remarque && <> ({result.remarque})</>}
                </div>
              )}
              <p className="th-muted">
                Tableaux : Ujour-nuit pour Uw de {decimal1.format(data.ujn.lignes[0]?.uw ?? 0)} à{" "}
                {decimal1.format(data.ujn.lignes[data.ujn.lignes.length - 1]?.uw ?? 0)}, Uws pour Uw de{" "}
                {decimal1.format(data.uws.lignes[0]?.uw ?? 0)} à {decimal1.format(data.uws.lignes[data.uws.lignes.length - 1]?.uw ?? 0)} ;
                R de {decimal2.format(data.ujn.r[0] ?? 0)} à {decimal2.format(data.ujn.r[data.ujn.r.length - 1] ?? 0)}.
              </p>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
