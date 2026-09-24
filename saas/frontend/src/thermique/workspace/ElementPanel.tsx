import { useEffect, useState } from "react";

import type {
  StudyContent,
  StudyElementChanges,
  StudyElementRef,
  StudyElementScope,
  StudyOperation,
  StudyReleveElement,
  StudyRoom,
} from "../api";
import {
  LIBELLES_TYPE,
  TYPES_ELEMENT,
  compterElements,
  ecartsAvecLAgent,
  elementsDuLocal,
  epaisseurCm,
  estPont,
  longueurM,
  memeElement,
  porteursDuComposant,
  refDeElement,
  trouverElement,
} from "./elements";

const LIBELLES_CHAMP: Record<string, string> = {
  type: "type",
  composant: "composant",
  nu_exterieur_cm: "nu extérieur",
  nu_interieur_cm: "nu intérieur",
  nu_exterieur_fin_cm: "nu extérieur (fin)",
  nu_interieur_fin_cm: "nu intérieur (fin)",
};

function Etat({ element }: { element: StudyReleveElement }) {
  if (element.exclu) {
    return <span className="th-badge th-element-badge--ecarte">écarté</span>;
  }
  if (element.a_verifier) {
    return <span className="th-badge th-element-badge--doute">à vérifier</span>;
  }
  if (element.corrige) {
    return <span className="th-badge th-element-badge--corrige">corrigé</span>;
  }
  if (element.confirme) {
    return <span className="th-badge th-element-badge--confirme">confirmé</span>;
  }
  return <span className="th-badge">lu</span>;
}

/** Le formulaire de correction. Il ne propose que ce qui change le calcul (Q1, D104). */
function Correction({
  element,
  content,
  busy,
  onApply,
}: {
  element: StudyReleveElement;
  content: StudyContent;
  busy: boolean;
  onApply: (changes: StudyElementChanges, portee: StudyElementScope) => void;
}) {
  const [type, setType] = useState(element.type);
  const [composant, setComposant] = useState(element.composant ?? "");
  const [nuExt, setNuExt] = useState(String(element.nu_exterieur_cm));
  const [nuInt, setNuInt] = useState(String(element.nu_interieur_cm));
  const [erreur, setErreur] = useState<string | null>(null);

  // Changer d'élément doit repartir de ses valeurs, pas garder celles du précédent.
  useEffect(() => {
    setType(element.type);
    setComposant(element.composant ?? "");
    setNuExt(String(element.nu_exterieur_cm));
    setNuInt(String(element.nu_interieur_cm));
    setErreur(null);
  }, [element.troncon, element.debut_m, element.fin_m, element.type, element.composant, element.nu_exterieur_cm, element.nu_interieur_cm]);

  const porteurs = porteursDuComposant(content, element.composant);
  const composantChange = composant.trim() !== (element.composant ?? "");

  function valider(portee: StudyElementScope) {
    const changes: StudyElementChanges = {};
    if (type !== element.type) {
      changes.type = type;
    }
    if (composantChange) {
      changes.composant = composant.trim();
    }
    const ext = Number(nuExt.replace(",", "."));
    const int = Number(nuInt.replace(",", "."));
    if (!Number.isFinite(ext) || !Number.isFinite(int)) {
      setErreur("Les nus se saisissent en centimètres.");
      return;
    }
    if (int > ext) {
      setErreur(`Le nu intérieur (${int} cm) ne peut pas dépasser le nu extérieur (${ext} cm).`);
      return;
    }
    if (ext !== element.nu_exterieur_cm) {
      changes.nu_exterieur_cm = ext;
    }
    if (int !== element.nu_interieur_cm) {
      changes.nu_interieur_cm = int;
    }
    if (Object.keys(changes).length === 0) {
      setErreur("Rien n'a changé.");
      return;
    }
    setErreur(null);
    onApply(changes, portee);
  }

  return (
    <div className="th-element-form">
      <label>
        Type
        <select value={type} onChange={(event) => setType(event.target.value)} disabled={busy}>
          {TYPES_ELEMENT.map((item) => (
            <option key={item} value={item}>
              {LIBELLES_TYPE[item]}
            </option>
          ))}
        </select>
      </label>
      <label>
        Composant
        <input value={composant} onChange={(event) => setComposant(event.target.value)} disabled={busy} />
      </label>
      <div className="th-element-nus">
        <label>
          Nu extérieur (cm)
          <input value={nuExt} onChange={(event) => setNuExt(event.target.value)} disabled={busy} inputMode="decimal" />
        </label>
        <label>
          Nu intérieur (cm)
          <input value={nuInt} onChange={(event) => setNuInt(event.target.value)} disabled={busy} inputMode="decimal" />
        </label>
      </div>
      {erreur && <p className="th-alert th-alert--error">{erreur}</p>}
      <div className="th-inline">
        <button type="button" className="po2-button po2-button--primary" disabled={busy} onClick={() => valider("cet_element")}>
          Corriger cet élément
        </button>
        {/* La portée n'est jamais devinée : on annonce le nombre avant de proposer (Q3). */}
        {composantChange && porteurs > 1 && (
          <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={() => valider("partout")}>
            Corriger les {porteurs} éléments en « {element.composant} »
          </button>
        )}
      </div>
    </div>
  );
}

/** Le détail d'un élément : ce que l'agent a lu, ce qui a été corrigé, et les trois gestes. */
function Detail({
  element,
  content,
  room,
  busy,
  motif,
  onMotif,
  onOperation,
}: {
  element: StudyReleveElement;
  content: StudyContent;
  room: StudyRoom | null;
  busy: boolean;
  motif: string;
  onMotif: (valeur: string) => void;
  onOperation: (operation: StudyOperation) => void;
}) {
  return (
    <>
      {room && estPont(element) && (
        <p className="th-muted">Pont thermique de « {room.nom} »</p>
      )}
      <article className="th-element-detail">
        <header>
          <strong>
            {LIBELLES_TYPE[element.type] ?? element.type} · {element.troncon} de {element.debut_m} à {element.fin_m} m
          </strong>
          <Etat element={element} />
        </header>
        {element.indice && (
          <p className="th-element-indice">
            Ce que l'agent a lu : « {element.indice} »
            {element.confiance != null ? ` (confiance ${Math.round(element.confiance * 100)} %)` : ""}
          </p>
        )}
        {ecartsAvecLAgent(element).length > 0 && (
          <ul className="th-element-ecarts">
            {ecartsAvecLAgent(element).map((ecart) => (
              <li key={ecart.champ}>
                {LIBELLES_CHAMP[ecart.champ] ?? ecart.champ} : <del>{String(ecart.avant)}</del> → {String(ecart.apres)}
              </li>
            ))}
          </ul>
        )}

        {element.exclu ? (
          <>
            <p className="th-alert th-alert--warn">Écarté : {element.motif_exclusion}</p>
            <button
              type="button"
              className="po2-button po2-button--ghost"
              disabled={busy}
              onClick={() => onOperation({ type: "element_reactiver", element: refDeElement(element) })}
            >
              Remettre dans le calcul
            </button>
          </>
        ) : (
          <>
            {element.a_verifier && (
              <button
                type="button"
                className="po2-button po2-button--secondary"
                disabled={busy}
                onClick={() => onOperation({ type: "element_confirmer", element: refDeElement(element) })}
              >
                C'est juste, confirmer
              </button>
            )}
            <Correction
              element={element}
              content={content}
              busy={busy}
              onApply={(changes, portee) =>
                onOperation({ type: "element_corriger", element: refDeElement(element), changes, portee })
              }
            />
            <div className="th-element-ecarter">
              <label>
                Écarter cet élément, parce que
                <input
                  value={motif}
                  placeholder="ex. trait de cotation pris pour une menuiserie"
                  onChange={(event) => onMotif(event.target.value)}
                  disabled={busy}
                />
              </label>
              <button
                type="button"
                className="po2-button po2-button--danger"
                disabled={busy || motif.trim().length === 0}
                onClick={() => onOperation({ type: "element_ecarter", element: refDeElement(element), motif })}
              >
                Écarter
              </button>
              <p className="th-muted">Il reste dans l'étude, en grisé sur le plan, et peut revenir.</p>
            </div>
          </>
        )}
      </article>
    </>
  );
}

/**
 * Panneau d'un élément d'enveloppe (F4, D102 et Q8).
 *
 * Il s'affiche sous la fiche du local, jamais en carte flottante : elle masquerait le plan qu'on essaie
 * justement de lire.
 */
export function ElementPanel({
  content,
  room,
  selected,
  onSelect,
  busy,
  message,
  onOperation,
}: {
  content: StudyContent;
  room: StudyRoom | null;
  selected: StudyElementRef | null;
  onSelect: (ref: StudyElementRef | null) => void;
  busy: boolean;
  message: string | null;
  onOperation: (operation: StudyOperation) => void;
}) {
  const [motif, setMotif] = useState("");
  const liste = elementsDuLocal(content, room);
  const element = trouverElement(content, selected);
  const comptes = compterElements(content);
  const douteuxIci = liste.filter((item) => !item.exclu && item.a_verifier).length;

  useEffect(() => setMotif(""), [selected?.troncon, selected?.debut_m, selected?.fin_m]);

  if (!room && !element) {
    return null;
  }

  // Un élément désigné prend tout le bandeau : la fiche du local, la liste et les compteurs le noyaient.
  // On ne montre qu'une chose à la fois, et le retour est explicite.
  if (element) {
    return (
      <section className="th-elements th-elements--seul">
        <button type="button" className="th-link th-element-retour" onClick={() => onSelect(null)}>
          ← Revenir {room ? `à « ${room.nom} »` : "à la fiche du local"}
        </button>
        <Detail
          element={element}
          content={content}
          room={room}
          busy={busy}
          motif={motif}
          onMotif={setMotif}
          onOperation={onOperation}
        />
        {message && <p className="th-alert">{message}</p>}
      </section>
    );
  }

  return (
    <section className="th-elements">
      <h2>Éléments d'enveloppe</h2>
      <p className="th-muted">
        {liste.length} sur ce local · {douteuxIci} à vérifier — niveau : {comptes.aVerifier} sur {comptes.total}
        {comptes.ecartes > 0 ? ` · ${comptes.ecartes} écarté${comptes.ecartes > 1 ? "s" : ""}` : ""}
      </p>

      {liste.length === 0 ? (
        <p className="th-muted">Aucun élément relevé ne touche ce local.</p>
      ) : (
        <ul className="th-element-liste">
          {liste.map((item) => {
            const ref = refDeElement(item);
            const actif = memeElement(ref, selected);
            return (
              <li key={`${item.troncon}-${item.debut_m}-${item.fin_m}`}>
                <button
                  type="button"
                  className={actif ? "is-active" : undefined}
                  onClick={() => onSelect(actif ? null : ref)}
                >
                  <span className="th-element-nom">
                    {LIBELLES_TYPE[item.type] ?? item.type}
                    {item.composant ? ` · ${item.composant}` : ""}
                  </span>
                  <span className="th-element-mesure">
                    {/* Pour une liaison, `longueur_m` est l'emprise de l'angle sur le tronçon, pas un
                        linéaire de pont thermique : le mot le dit, pour ne pas induire en erreur. */}
                    {estPont(item) ? "emprise " : ""}
                    {longueurM(item).toLocaleString("fr-FR")} m · {epaisseurCm(item)} cm
                  </span>
                  <Etat element={item} />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {message && <p className="th-alert">{message}</p>}
    </section>
  );
}
