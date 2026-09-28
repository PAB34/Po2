import { useEffect, useState } from "react";

import type { PontsCatalogue, StudyContent, StudyElementRef, StudyOperation, StudyReleveElement } from "../api";
import { LIBELLES_TYPE, memeElement, pontDeElement, refDeElement } from "./elements";
import { avancement, pontsDuNiveau } from "./parcours";
import {
  A_MODELISER,
  alerteAngle,
  coefficientAngle,
  TYPES_ANGLE,
  libellePontType,
  libelleReference,
  pontsTypesPour,
  TYPES_PONT_REATTRIBUABLES,
} from "./pontsTypes";

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

const nombre = (valeur: number, decimales = 2) =>
  valeur.toLocaleString("fr-FR", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });

/**
 * L'angle réel d'un angle sortant ou rentrant et ce qu'il fait à ψ (remarque E, D160). L'angle saisi
 * l'emporte sur la mesure du tracé ; il est lu sur l'élément, pour que la saisie se voie tout de suite.
 */
function AngleDuPont({
  element,
  mesure,
  catalogue,
}: {
  element: StudyReleveElement;
  mesure: number | null;
  catalogue?: PontsCatalogue | null;
}) {
  if (!TYPES_ANGLE.includes(element.type)) return null;
  const angle = element.angle_deg ?? mesure;
  const coefficient = coefficientAngle(angle);
  const type = catalogue?.ponts.find((item) => item.code === element.reference_pont);
  const alerte = alerteAngle(angle);
  return (
    <>
      <p className="th-muted">
        {angle == null
          ? "Angle non mesurable ici : l'angle droit du catalogue est retenu (ψ × 1)."
          : `Angle : ${nombre(angle, 0)}° (${element.angle_deg != null ? "saisi par vous" : "mesuré sur le tracé"}) → ψ × ${nombre(coefficient)}`}
      </p>
      {type && (
        <p className="th-ponts__reference">
          ψ retenu : {nombre(type.psi_i)} × {nombre(coefficient)} = {nombre(type.psi_i * coefficient)} W/(m·K)
        </p>
      )}
      {alerte && <p className="th-alert th-alert--warn">{alerte}</p>}
    </>
  );
}

/** Ce que l'agent a lu du pont, et où il se trouve. Rien de plus : une chose à la fois (D107). */
function Lecture({
  element,
  content,
  catalogue,
}: {
  element: StudyReleveElement;
  content: StudyContent;
  catalogue?: PontsCatalogue | null;
}) {
  const pont = pontDeElement(content, element);
  const reference = libelleReference(element.reference_pont, catalogue);
  return (
    <>
      <h3 className="th-ponts__titre">{LIBELLES_TYPE[element.type] ?? element.type}</h3>
      <p className="th-muted">
        {pont?.piece ? `Dans « ${pont.piece} »` : "Rattaché à aucun local"} · {element.troncon} à{" "}
        {((element.debut_m + element.fin_m) / 2).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} m
      </p>
      {element.composant && <p className="th-muted">Composant : {element.composant}</p>}
      {reference && <p className="th-ponts__reference">{reference}</p>}
      <AngleDuPont element={element} mesure={pont?.angle_mesure_deg ?? null} catalogue={catalogue} />
      {/* Un pont posé par le thermicien n'a pas de lecture d'agent à montrer : on dit d'où il vient. */}
      {element.ajoute ? (
        <p className="th-muted">Pont posé par vous sur le plan.</p>
      ) : element.indice && (
        <p className="th-element-indice">
          Ce que l'agent a lu : « {element.indice} »
          {element.confiance != null ? ` (confiance ${Math.round(element.confiance * 100)} %)` : ""}
        </p>
      )}
    </>
  );
}

/**
 * Réattribuer un pont mal reconnu (remarque D, D158) : son type, puis son pont type NF EN ISO 14683 —
 * ceux de sa famille d'abord, les autres ensuite —, ou « à modéliser » s'il n'est pas au catalogue.
 * Un seul geste `element_corriger`, qui vaut jugement.
 */
function Reattribution({
  element,
  mesure,
  catalogue,
  busy,
  onValider,
  onRevenir,
}: {
  element: StudyReleveElement;
  /** Angle lu sur le tracé, proposé tel quel ; le changer le saisit (D160). */
  mesure: number | null;
  catalogue?: PontsCatalogue | null;
  busy: boolean;
  onValider: (type: string, reference: string, angle: number | null) => void;
  onRevenir: () => void;
}) {
  const [type, setType] = useState(element.type);
  const depart = element.angle_deg ?? mesure;
  const [angle, setAngle] = useState(depart == null ? "" : String(Math.round(depart)));
  const angleSaisi = angle.trim() === "" ? null : Number(angle.replace(",", "."));
  const angleInvalide = angleSaisi != null && (!Number.isFinite(angleSaisi) || angleSaisi <= 0 || angleSaisi > 180);
  const proposes = catalogue ? pontsTypesPour(catalogue, type) : [];
  const [reference, setReference] = useState(element.reference_pont ?? proposes[0]?.code ?? A_MODELISER);
  const autres = catalogue ? catalogue.ponts.filter((pont) => !proposes.includes(pont)) : [];
  const choisi = catalogue?.ponts.find((pont) => pont.code === reference);

  return (
    <div className="th-ponts__reattribuer">
      <label>
        Type de liaison
        <select
          value={type}
          disabled={busy}
          onChange={(event) => {
            setType(event.target.value);
            // Le pont type suit le type : un angle sortant ne garde pas un about de refend.
            const premier = catalogue ? pontsTypesPour(catalogue, event.target.value)[0] : undefined;
            setReference(premier?.code ?? A_MODELISER);
          }}
        >
          {TYPES_PONT_REATTRIBUABLES.map((item) => (
            <option key={item.type} value={item.type}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Pont type (NF EN ISO 14683, tableau C.2)
        <select value={reference} disabled={busy || !catalogue} onChange={(event) => setReference(event.target.value)}>
          {catalogue && proposes.length > 0 && (
            <optgroup label="Pour ce type de liaison">
              {proposes.map((pont) => (
                <option key={pont.code} value={pont.code}>
                  {libellePontType(pont, catalogue)}
                </option>
              ))}
            </optgroup>
          )}
          {catalogue &&
            Object.entries(catalogue.familles).map(([famille, { libelle }]) => {
              const liste = autres.filter((pont) => pont.famille === famille);
              return liste.length ? (
                <optgroup key={famille} label={libelle}>
                  {liste.map((pont) => (
                    <option key={pont.code} value={pont.code}>
                      {libellePontType(pont, catalogue)}
                    </option>
                  ))}
                </optgroup>
              ) : null;
            })}
          <option value={A_MODELISER}>À modéliser — absent du catalogue</option>
        </select>
      </label>
      {TYPES_ANGLE.includes(type) && (
        <label>
          Angle réel, en degrés (90 = angle droit)
          <input
            inputMode="decimal"
            value={angle}
            disabled={busy}
            onChange={(event) => setAngle(event.target.value)}
            placeholder="non mesuré : 90 retenu"
          />
          {angleInvalide ? (
            <small className="th-alert th-alert--warn">L'angle se donne entre 0 et 180 degrés.</small>
          ) : (
            <small className="th-muted">
              ψ minoré à proportion : × {coefficientAngle(angleSaisi).toLocaleString("fr-FR")}
            </small>
          )}
        </label>
      )}
      {!catalogue && <small className="th-muted">Catalogue des ponts types en cours de chargement…</small>}
      {choisi && (
        <small className="th-muted">
          Croquis : NF EN ISO 14683, page {choisi.page_pdf} du PDF. ψe {choisi.psi_e.toLocaleString("fr-FR")} ·
          ψoi {choisi.psi_oi.toLocaleString("fr-FR")} · ψi {choisi.psi_i.toLocaleString("fr-FR")} W/(m·K).
        </small>
      )}
      <div className="th-inline">
        <button
          type="button"
          className="po2-button po2-button--primary"
          disabled={busy || angleInvalide}
          onClick={() => {
            // L'angle n'est saisi que s'il a changé : la mesure du tracé reste sinon la référence.
            const change = TYPES_ANGLE.includes(type) && angleSaisi != null && angleSaisi !== (depart == null ? null : Math.round(depart));
            onValider(type, reference, change ? angleSaisi : null);
          }}
        >
          Réattribuer
        </button>
        <button type="button" className="th-link" onClick={onRevenir}>
          Revenir
        </button>
      </div>
    </div>
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
  catalogue = null,
}: {
  content: StudyContent;
  selected: StudyElementRef | null;
  onSelect: (ref: StudyElementRef | null) => void;
  busy: boolean;
  message: string | null;
  onOperation: (operation: StudyOperation) => void;
  /** Ponts types NF EN ISO 14683 : de quoi réattribuer un pont (D158). */
  catalogue?: PontsCatalogue | null;
}) {
  const ponts = pontsDuNiveau(content);
  // Régime exigeant : ici, la confiance de l'agent ne vaut pas validation (voir `avancement`).
  const compte = avancement(ponts, true);
  const [refus, setRefus] = useState(false);
  const [reattribuer, setReattribuer] = useState(false);
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
    setReattribuer(false);
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

  function reattribuerA(type: string, reference: string, angle: number | null) {
    if (!element) return;
    onOperation({
      type: "element_corriger",
      element: refDeElement(element),
      changes: {
        ...(type !== element.type ? { type } : {}),
        reference_pont: reference,
        ...(angle != null ? { angle_deg: angle } : {}),
      },
      portee: "cet_element",
    });
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
            <Lecture element={element} content={content} catalogue={catalogue} />

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
            ) : reattribuer ? (
              // Remonté quand le catalogue arrive, pour proposer d'emblée un pont type de la famille.
              <Reattribution
                key={`${rang}-${catalogue ? "catalogue" : "attente"}`}
                element={element}
                mesure={pontDeElement(content, element)?.angle_mesure_deg ?? null}
                catalogue={catalogue}
                busy={busy}
                onValider={reattribuerA}
                onRevenir={() => setReattribuer(false)}
              />
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
                <button
                  type="button"
                  className="po2-button po2-button--ghost"
                  disabled={busy}
                  onClick={() => setReattribuer(true)}
                >
                  Réattribuer…
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
