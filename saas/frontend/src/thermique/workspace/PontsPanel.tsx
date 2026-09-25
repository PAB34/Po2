import { useEffect, useState } from "react";

import type { StudyContent, StudyElementRef, StudyOperation, StudyReleveElement } from "../api";
import { LIBELLES_TYPE, memeElement, pontDeElement, refDeElement } from "./elements";
import { avancement, pontsDuNiveau } from "./parcours";

/**
 * Motifs de refus pré-écrits (Q3).
 *
 * Le R+1 porte 77 ponts. Exiger une phrase tapée à chaque refus, comme F4 le fait pour un élément,
 * rendrait l'étape intenable : le thermicien écrirait « doublon » soixante fois. Les trois motifs
 * couvrent ce que la recette a fait remonter ; la case libre garde le reste possible.
 */
const MOTIFS = [
  { cle: "trace", label: "Angle du tracé, pas un vrai pont" },
  { cle: "doublon", label: "Doublon du pont voisin" },
  { cle: "hors", label: "Hors enveloppe chauffée" },
] as const;

/** Un pont reste à juger tant que personne ne l'a gardé, corrigé ou écarté (régime exigeant). */
const aJuger = (element: StudyReleveElement) =>
  !element.exclu && !element.confirme && !element.corrige;

function Position({ rang, total, reste }: { rang: number; total: number; reste: number }) {
  return (
    <p className="th-ponts__position">
      <strong>
        Pont {rang + 1} sur {total}
      </strong>
      {reste > 0 ? ` · ${reste} encore à juger` : " · tous jugés"}
    </p>
  );
}

/** Ce que l'agent a lu du pont, et où il se trouve. Rien de plus : une chose à la fois (D107). */
function Lecture({ element, content }: { element: StudyReleveElement; content: StudyContent }) {
  const pont = pontDeElement(content, element);
  return (
    <>
      <h3 className="th-ponts__titre">{LIBELLES_TYPE[element.type] ?? element.type}</h3>
      <p className="th-muted">
        {pont?.piece ? `Dans « ${pont.piece} »` : "Rattaché à aucun local"} · {element.troncon} à{" "}
        {((element.debut_m + element.fin_m) / 2).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} m
      </p>
      {element.composant && <p className="th-muted">Composant : {element.composant}</p>}
      {element.indice && (
        <p className="th-element-indice">
          Ce que l'agent a lu : « {element.indice} »
          {element.confiance != null ? ` (confiance ${Math.round(element.confiance * 100)} %)` : ""}
        </p>
      )}
    </>
  );
}

/**
 * Étape « ponts thermiques » du parcours (F2, Q1 à Q5).
 *
 * Une passe continue sur **tout le niveau**, et non local par local : un pont appartient à un tronçon,
 * et sur le R+1 treize liaisons ne sont rattachées à aucun local — une passe par local les rendrait
 * invisibles, donc injugeables (Q1).
 *
 * Deux gestes explicites, jamais un « Suivant » qui vaudrait acceptation : soixante-dix-sept ponts
 * « validés » sans que personne les ait regardés seraient pires qu'aucune validation (Q2).
 */
export function PontsPanel({
  content,
  selected,
  onSelect,
  busy,
  message,
  onOperation,
}: {
  content: StudyContent;
  selected: StudyElementRef | null;
  onSelect: (ref: StudyElementRef | null) => void;
  busy: boolean;
  message: string | null;
  onOperation: (operation: StudyOperation) => void;
}) {
  const ponts = pontsDuNiveau(content);
  // Régime exigeant : ici, la confiance de l'agent ne vaut pas validation (voir `avancement`).
  const compte = avancement(ponts, true);
  const [refus, setRefus] = useState(false);
  const [libre, setLibre] = useState("");

  // Le pont en cours est celui désigné sur le plan : cliquer une pastille déplace la passe, et la
  // passe déplace la pastille. Un seul état pour les deux, sinon les deux se contredisent.
  const rang = ponts.findIndex((element) => memeElement(refDeElement(element), selected));
  const element = rang >= 0 ? ponts[rang] : null;

  // Entrer dans l'étape sans rien de désigné : on se place sur le premier pont qui reste à juger.
  useEffect(() => {
    if (element || ponts.length === 0) {
      return;
    }
    const premier = ponts.find(aJuger) ?? ponts[0];
    onSelect(refDeElement(premier));
  }, [element, onSelect, ponts]);

  useEffect(() => {
    setRefus(false);
    setLibre("");
  }, [rang]);

  function allerA(cible: number) {
    if (cible >= 0 && cible < ponts.length) {
      onSelect(refDeElement(ponts[cible]));
    }
  }

  /** Après un geste, on enchaîne : c'est ce qui rend une passe de 77 ponts tenable (Q2). */
  function suivant() {
    const apres = ponts.findIndex((item, position) => position > rang && aJuger(item));
    allerA(apres >= 0 ? apres : rang + 1);
  }

  function garder() {
    if (!element) return;
    onOperation({ type: "element_confirmer", element: refDeElement(element) });
    suivant();
  }

  function ecarter(motif: string) {
    if (!element || motif.trim().length === 0) return;
    onOperation({ type: "element_ecarter", element: refDeElement(element), motif: motif.trim() });
    suivant();
  }

  if (ponts.length === 0) {
    return (
      <section className="th-ponts">
        <h2>Ponts thermiques</h2>
        <p className="th-muted">Aucune liaison relevée sur ce niveau.</p>
      </section>
    );
  }

  return (
    <section className="th-ponts">
      <h2>Ponts thermiques</h2>
      <p className="th-muted">
        Chaque liaison relevée passe devant vous une fois. Plusieurs ponts au même coin ne sont pas une
        erreur : l'enveloppe de ce niveau est très découpée, c'est à vous de dire lesquels comptent.
      </p>

      {element ? (
        <>
          <Position rang={rang} total={ponts.length} reste={compte.restants} />
          <article className="th-ponts__fiche">
            <Lecture element={element} content={content} />

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
            ) : refus ? (
              <div className="th-ponts__motifs">
                <p className="th-muted">Écarter ce pont, parce que :</p>
                {MOTIFS.map((motif) => (
                  <button
                    key={motif.cle}
                    type="button"
                    className="po2-button po2-button--ghost"
                    disabled={busy}
                    onClick={() => ecarter(motif.label)}
                  >
                    {motif.label}
                  </button>
                ))}
                <label>
                  Autre raison
                  <input
                    value={libre}
                    onChange={(event) => setLibre(event.target.value)}
                    disabled={busy}
                    placeholder="ex. escalier extérieur pris pour un refend"
                  />
                </label>
                <div className="th-inline">
                  <button
                    type="button"
                    className="po2-button po2-button--danger"
                    disabled={busy || libre.trim().length === 0}
                    onClick={() => ecarter(libre)}
                  >
                    Écarter
                  </button>
                  <button type="button" className="th-link" onClick={() => setRefus(false)}>
                    Revenir
                  </button>
                </div>
              </div>
            ) : (
              <div className="th-ponts__gestes">
                <button type="button" className="po2-button po2-button--primary" disabled={busy} onClick={garder}>
                  Garder
                </button>
                <button
                  type="button"
                  className="po2-button po2-button--danger"
                  disabled={busy}
                  onClick={() => setRefus(true)}
                >
                  Écarter…
                </button>
                {(element.confirme || element.corrige) && (
                  <span className="th-badge th-element-badge--confirme">déjà jugé</span>
                )}
              </div>
            )}
          </article>

          <div className="th-ponts__nav">
            <button type="button" className="th-link" disabled={rang === 0} onClick={() => allerA(rang - 1)}>
              ← Précédent
            </button>
            {/* Passer sans juger reste possible : sinon l'étape devient un couloir sans sortie. Le
                compteur, lui, ne descend pas — c'est bien le but. */}
            <button
              type="button"
              className="th-link"
              disabled={rang >= ponts.length - 1}
              onClick={() => allerA(rang + 1)}
            >
              Passer sans juger →
            </button>
          </div>
        </>
      ) : (
        <p className="th-muted">Choisissez un pont sur le plan pour commencer.</p>
      )}

      {message && <p className="th-alert">{message}</p>}
    </section>
  );
}
