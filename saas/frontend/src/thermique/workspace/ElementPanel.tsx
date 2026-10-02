import { useEffect, useState } from "react";

import type {
  Baie,
  MenuiseriesDuProjet,
  ModeleMenuiserie,
  StudyContent,
  StudyCouche,
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
import { baieDeElement, provenanceBaie } from "./baies";
import { expositionLisible } from "./modeles";
import { NATURES_COUCHE, changesDeComposition, couchesValidees } from "./parois";

const LIBELLES_CHAMP: Record<string, string> = {
  type: "type",
  composant: "composant",
  nu_exterieur_cm: "face extérieure",
  nu_interieur_cm: "face intérieure",
  nu_exterieur_fin_cm: "face extérieure (fin)",
  nu_interieur_fin_cm: "face intérieure (fin)",
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
      setErreur(`La face intérieure (${int} cm) ne peut pas être au-delà de la face extérieure (${ext} cm).`);
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
      {/* « Nu extérieur / intérieur » ne parlait pas (retour d'usage M3) : ce sont les deux faces du mur,
          repérées depuis le trait de façade qui guide le relevé, en cm, négatif vers l'intérieur. */}
      <div className="th-element-nus">
        <label>
          Face extérieure du mur (cm)
          <input value={nuExt} onChange={(event) => setNuExt(event.target.value)} disabled={busy} inputMode="decimal" />
        </label>
        <label>
          Face intérieure du mur (cm)
          <input value={nuInt} onChange={(event) => setNuInt(event.target.value)} disabled={busy} inputMode="decimal" />
        </label>
      </div>
      <small className="th-muted">
        Distances au trait de façade qui guide le relevé, négatives vers l'intérieur.
        {Number.isFinite(Number(nuExt.replace(",", "."))) && Number.isFinite(Number(nuInt.replace(",", ".")))
          ? ` Épaisseur du mur : ${Math.round((Number(nuExt.replace(",", ".")) - Number(nuInt.replace(",", "."))) * 10) / 10} cm.`
          : ""}
        {element.type === "menuiserie" ? " Pour une menuiserie, c'est le mur dans lequel elle est posée." : ""}
      </small>
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
  baie = null,
  onMesurerBaie,
  modeles = [],
  onChoisirModele,
}: {
  element: StudyReleveElement;
  content: StudyContent;
  room: StudyRoom | null;
  busy: boolean;
  motif: string;
  onMotif: (valeur: string) => void;
  onOperation: (operation: StudyOperation) => void;
  baie?: Baie | null;
  onMesurerBaie?: () => void;
  modeles?: ModeleMenuiserie[];
  onChoisirModele?: (element: StudyReleveElement, nom: string) => void;
}) {
  const menuiserie = element.type === "menuiserie";
  // D243, D244 : la composition d'un mur se vérifie et se valide ici ; un mur de trop se supprime d'un geste.
  const porteurs =
    element.type === "paroi" && element.composant
      ? content.enveloppe.releve_brut.elements.filter(
          (autre) =>
            autre.type === "paroi" &&
            !autre.exclu &&
            autre.composant === element.composant &&
            !(autre.troncon === element.troncon && autre.debut_m === element.debut_m && autre.fin_m === element.fin_m),
        )
      : [];
  const composition =
    element.type === "paroi" && !element.exclu ? (
      <EditeurComposition
        key={`${element.troncon}|${element.debut_m}|${element.fin_m}`}
        element={element}
        autres={porteurs.length}
        busy={busy}
        onValider={(couches, partout) => {
          const inchangee = JSON.stringify(couchesValidees(couches)) === JSON.stringify(couchesValidees(element.couches ?? []));
          if (inchangee && !partout) {
            onOperation({ type: "element_confirmer", element: refDeElement(element) });
            return;
          }
          for (const mur of partout ? [element, ...porteurs] : [element]) {
            onOperation({ type: "element_corriger", element: refDeElement(mur), changes: changesDeComposition(mur, couches) });
          }
        }}
        onSupprimer={() =>
          onOperation({ type: "element_ecarter", element: refDeElement(element), motif: "mur supprimé par le thermicien" })
        }
      />
    ) : null;
  const lecture = (
    <>
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
    </>
  );
  const gestes = element.exclu ? (
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
        onApply={(changes, portee) => onOperation({ type: "element_corriger", element: refDeElement(element), changes, portee })}
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
  );

  // D228 : la fiche d'une menuiserie montre l'essentiel ; la lecture de l'IA et les corrections du relevé
  // sont repliées. « Affecter aussi à… » n'est plus proposé (D229).
  if (menuiserie) {
    return (
      <article className="th-element-detail">
        <header>
          <strong>
            Menuiserie {element.composant ?? ""}
            {element.menuiserie_type ? ` · ${element.menuiserie_type}` : ""}
          </strong>
          <Etat element={element} />
        </header>
        {element.exclu && <p className="th-alert th-alert--warn">Écartée : {element.motif_exclusion}</p>}
        <p className="th-muted">
          Exposition :{" "}
          {expositionLisible(element) ? (
            <strong>
              {expositionLisible(element)}
              {element.azimut_deg != null ? ` (${element.azimut_deg}° depuis le nord)` : ""}
            </strong>
          ) : (
            "nord à caler (onglet Planche)"
          )}
        </p>
        {!element.exclu && onChoisirModele && (
          <ChoixDuModele element={element} modeles={modeles} busy={busy} onChoisir={(nom) => onChoisirModele(element, nom)} />
        )}
        {baie && <BaieDeLaMenuiserie baie={baie} onMesurer={onMesurerBaie} />}
        <details className="th-element-releve">
          <summary>Corriger le relevé</summary>
          <p className="th-muted">
            {element.troncon} de {element.debut_m} à {element.fin_m} m
            {(element.morceaux_reunis?.length ?? 0) > 1 && ` · ${element.morceaux_reunis!.length} morceaux relevés réunis`}
          </p>
          {lecture}
          {gestes}
        </details>
      </article>
    );
  }

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
        {composition}
        {element.type === "paroi" && !element.exclu ? (
          // D243 : pour un mur, la composition d'abord ; la lecture de l'IA et les autres corrections sont repliées.
          <details className="th-element-releve">
            <summary>Corriger le relevé</summary>
            {lecture}
            {gestes}
          </details>
        ) : (
          <>
            {lecture}
            {gestes}
          </>
        )}
      </article>
    </>
  );
}

/**
 * La composition d'un mur, couche par couche, de l'extérieur vers l'intérieur (D243). « Valider la composition »
 * l'enregistre (ce mur seul, ou aussi les autres murs du même composant) et marque le mur comme vérifié.
 */
export function EditeurComposition({
  element,
  autres,
  busy,
  onValider,
  onSupprimer,
}: {
  element: StudyReleveElement;
  /** Autres murs actifs du même composant. */
  autres: number;
  busy: boolean;
  onValider: (couches: StudyCouche[], partout: boolean) => void;
  onSupprimer: () => void;
}) {
  const [couches, setCouches] = useState<StudyCouche[]>(() =>
    (element.couches ?? []).length ? (element.couches ?? []).map((couche) => ({ ...couche })) : [{ nature: "mur", epaisseur_cm: 20 }],
  );
  const [partout, setPartout] = useState(false);
  const total = Math.round(couches.reduce((somme, couche) => somme + (couche.epaisseur_cm || 0), 0) * 10) / 10;
  const valide = Boolean(element.confirme || element.corrige);
  const changer = (rang: number, champ: Partial<StudyCouche>) =>
    setCouches((liste) => liste.map((couche, i) => (i === rang ? { ...couche, ...champ, presume: false } : couche)));
  return (
    <div className="th-composition">
      <p>
        Composition <strong>{element.composant ?? "sans composant"}</strong> · <strong>{total} cm</strong>{" "}
        <span className={valide ? "th-composition__etat is-valide" : "th-composition__etat"}>{valide ? "validée" : "à valider"}</span>
      </p>
      <small className="th-muted">De l'extérieur (en haut) vers l'intérieur (en bas) ; la ligne de métré est la face intérieure.</small>
      <ol className="th-composition__couches">
        {couches.map((couche, rang) => (
          <li key={rang}>
            <select
              aria-label={`Nature de la couche ${rang + 1}`}
              value={couche.nature}
              disabled={busy}
              onChange={(event) => changer(rang, { nature: event.target.value })}
            >
              {!NATURES_COUCHE.some((n) => n.id === couche.nature) && <option value={couche.nature}>{couche.nature}</option>}
              {NATURES_COUCHE.map((nature) => (
                <option key={nature.id} value={nature.id}>
                  {nature.label}
                </option>
              ))}
            </select>
            <input
              aria-label={`Épaisseur de la couche ${rang + 1} (cm)`}
              type="number"
              min={0.1}
              step={0.1}
              value={couche.epaisseur_cm}
              disabled={busy}
              onChange={(event) => changer(rang, { epaisseur_cm: Number(event.target.value) })}
            />
            <span className="th-muted">cm{couche.presume ? " (présumé)" : ""}</span>
            <button
              type="button"
              className="th-link"
              aria-label={`Retirer la couche ${rang + 1}`}
              disabled={busy || couches.length === 1}
              onClick={() => setCouches((liste) => liste.filter((_, i) => i !== rang))}
            >
              ×
            </button>
          </li>
        ))}
      </ol>
      <button
        type="button"
        className="th-link"
        disabled={busy}
        onClick={() => setCouches((liste) => [...liste, { nature: "isolant", epaisseur_cm: 10 }])}
      >
        + Ajouter une couche
      </button>
      {autres > 0 && element.composant && (
        <label className="th-inline">
          <input type="checkbox" checked={partout} onChange={(event) => setPartout(event.target.checked)} />
          Appliquer aussi aux {autres} autres murs {element.composant}
        </label>
      )}
      <div className="th-composition__actions">
        <button
          type="button"
          className="po2-button po2-button--primary"
          disabled={busy || couchesValidees(couches).length === 0}
          onClick={() => onValider(couches, partout)}
        >
          Valider la composition
        </button>
        <button type="button" className="po2-button po2-button--danger" disabled={busy} onClick={onSupprimer}>
          Supprimer ce mur
        </button>
      </div>
    </div>
  );
}

/** Choisir, dans la bibliothèque du projet, le modèle mesuré de cette menuiserie (D226). */
export function ChoixDuModele({
  element,
  modeles,
  busy,
  onChoisir,
}: {
  element: StudyReleveElement;
  modeles: ModeleMenuiserie[];
  busy: boolean;
  /** Nom du modèle, ou chaîne vide pour le retirer. */
  onChoisir: (nom: string) => void;
}) {
  const actuel = element.modele ?? "";
  return (
    <label className="th-choix-modele">
      Modèle mesuré
      <select value={actuel} disabled={busy || (!modeles.length && !actuel)} onChange={(event) => onChoisir(event.target.value)}>
        <option value="">{modeles.length ? "— aucun : choisir dans la bibliothèque —" : "— aucun modèle mesuré —"}</option>
        {modeles.map((modele) => (
          <option key={modele.nom} value={modele.nom}>
            {modele.nom} · {Math.round(modele.largeur_cm)}×{Math.round(modele.hauteur_m * 100)}
          </option>
        ))}
        {actuel && !modeles.some((modele) => modele.nom === actuel) && <option value={actuel}>{actuel} (retiré de la bibliothèque)</option>}
      </select>
    </label>
  );
}

/** « Affecter aussi à… » (D217) : la menuiserie se partage, à parts égales, avec les pièces cochées. */
export function AffecterAussiA({
  element,
  pieces,
  piece,
  busy,
  onAffecter,
}: {
  element: StudyReleveElement;
  /** Noms des pièces du niveau. */
  pieces: string[];
  /** La pièce à laquelle le plan rattache déjà la menuiserie. */
  piece: string | null;
  busy: boolean;
  onAffecter: (noms: string[]) => void;
}) {
  const actuelles = element.pieces_en_plus ?? [];
  const [ouvert, setOuvert] = useState(false);
  const [cochees, setCochees] = useState<string[]>(actuelles);
  useEffect(() => setCochees(element.pieces_en_plus ?? []), [element.pieces_en_plus]);
  const autres = pieces.filter((nom) => nom !== piece);
  const parts = 1 + actuelles.length;
  return (
    <div className="th-affecter">
      {actuelles.length > 0 && (
        <p className="th-muted">
          Partagée avec {actuelles.join(", ")} : 1/{parts} de la baie à chaque pièce.
        </p>
      )}
      {!ouvert ? (
        <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={() => setOuvert(true)}>
          Affecter aussi à…
        </button>
      ) : (
        <fieldset className="th-affecter__liste">
          <legend>Pièces qui partagent cette menuiserie{piece ? ` avec « ${piece} »` : ""}</legend>
          {autres.map((nom) => (
            <label key={nom}>
              <input
                type="checkbox"
                checked={cochees.includes(nom)}
                onChange={() => setCochees((liste) => (liste.includes(nom) ? liste.filter((n) => n !== nom) : [...liste, nom]))}
              />
              {nom}
            </label>
          ))}
          <div className="th-affecter__actions">
            <button
              type="button"
              className="po2-button po2-button--primary"
              disabled={busy}
              onClick={() => {
                onAffecter(cochees);
                setOuvert(false);
              }}
            >
              Enregistrer l'affectation
            </button>
            <button type="button" className="th-link" onClick={() => setOuvert(false)}>
              Annuler
            </button>
          </div>
          <small className="th-muted">La baie est répartie à parts égales entre ses pièces : elle n'est jamais comptée deux fois.</small>
        </fieldset>
      )}
    </div>
  );
}

/** La baie d'une menuiserie (S5e, D199) : largeur réunie, hauteur et sa provenance, mesure à faire (D214). */
export function BaieDeLaMenuiserie({
  baie,
  onMesurer,
}: {
  baie: Baie;
  /** Ouvre « Coupes et élévations », prête à mesurer une menuiserie. */
  onMesurer?: () => void;
}) {
  return (
    <div className="th-baie">
      <p>
        Baie {baie.modele ? <strong>{baie.modele}</strong> : baie.composant} ·{" "}
        <strong>{(baie.largeur_retenue_cm ?? baie.largeur_cm).toLocaleString("fr-FR")} cm</strong>
        {baie.morceaux.length > 1 ? ` (${baie.morceaux.length} morceaux réunis)` : ""} — hauteur{" "}
        <strong>{baie.hauteur_m === null ? "inconnue" : `${baie.hauteur_m.toLocaleString("fr-FR")} m`}</strong>,{" "}
        {provenanceBaie(baie)}
        {baie.surface_m2 != null ? ` · ${baie.surface_m2.toLocaleString("fr-FR")} m²` : ""}
      </p>
      {baie.ecart_modele_cm != null && Math.abs(baie.ecart_modele_cm) > 5 && (
        <p className="th-alert th-alert--warn">
          Le plan relève {baie.largeur_cm.toLocaleString("fr-FR")} cm, le modèle mesure{" "}
          {(baie.largeur_modele_cm ?? 0).toLocaleString("fr-FR")} cm : baie double, morceau mal relevé, ou mauvais modèle ?
        </p>
      )}
      {baie.morceau_a_verifier && (
        <p className="th-alert th-alert--warn">
          Morceau de {baie.largeur_cm.toLocaleString("fr-FR")} cm seul : sans doute la tranche d'une menuiserie mal
          relevée. Corrigez ses bornes ou écartez-le.
        </p>
      )}
      {onMesurer && !baie.mur_rideau && (
        <button type="button" className="po2-button po2-button--ghost" onClick={onMesurer}>
          {baie.hauteur_m === null ? "Mesurer sa hauteur" : "Mesurer de nouveau"} (coupes et élévations)
        </button>
      )}
    </div>
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
  parois = false,
  menuiseries,
  sheetId = null,
  onMesurerBaie,
  onChoisirModele,
  famille,
}: {
  /** D227 : l'étape ne liste que les parois, ou que les menuiseries. */
  famille?: "parois" | "menuiseries";
  content: StudyContent;
  room: StudyRoom | null;
  selected: StudyElementRef | null;
  onSelect: (ref: StudyElementRef | null) => void;
  busy: boolean;
  message: string | null;
  onOperation: (operation: StudyOperation) => void;
  /** Étape « parois et menuiseries » : les ponts ont leur propre étape, ils n'ont rien à faire ici (D155). */
  parois?: boolean;
  /** Baies du projet et façades lues (S5e) : hauteur de la menuiserie désignée. */
  menuiseries?: MenuiseriesDuProjet;
  sheetId?: number | null;
  /** Ouvre « Coupes et élévations » prête à mesurer la menuiserie (D214). */
  onMesurerBaie?: () => void;
  /** Pose un modèle de la bibliothèque sur la menuiserie et tous ses morceaux (D226). */
  onChoisirModele?: (element: StudyReleveElement, nom: string) => void;
}) {
  const [motif, setMotif] = useState("");
  const liste = elementsDuLocal(content, room).filter(
    (item) =>
      (!parois || !estPont(item)) &&
      // D227 : chaque étape ne liste que sa famille.
      (!famille || (item.type === "menuiserie") === (famille === "menuiseries")),
  );
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
          baie={baieDeElement(menuiseries, sheetId, element)}
          onMesurerBaie={onMesurerBaie}
          modeles={menuiseries?.modeles ?? []}
          onChoisirModele={onChoisirModele}
        />
        {message && <p className="th-alert">{message}</p>}
      </section>
    );
  }

  return (
    <section className="th-elements">
      {/* Seule à l'étape des parois, la liste doit dire de quel local il s'agit. */}
      {parois && room && <h2 className="th-panel__title">{room.nom}</h2>}
      <h2>{famille === "menuiseries" ? "Menuiseries" : famille === "parois" ? "Parois" : parois ? "Parois et menuiseries" : "Éléments d'enveloppe"}</h2>
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
