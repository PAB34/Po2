import { useEffect, useState } from "react";

import { thermiqueApi, type MenuiseriesDuProjet, type ModeleMenuiserie } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";
import { avisSurLaMenuiserie } from "./mesuresVue";
import { nomPropose, type CoteDeMenuiserie } from "./modeles";

const format = (v: number) => v.toLocaleString("fr-FR", { maximumFractionDigits: 2 });

/** Après deux coins : la mesure, et le nom du modèle à enregistrer (D219). */
export function ModeleDeMenuiserie({
  largeurM,
  hauteurM,
  menuiseries,
  busy = false,
  onEnregistrer,
  onAnnuler,
}: {
  largeurM: number;
  hauteurM: number;
  menuiseries?: MenuiseriesDuProjet;
  busy?: boolean;
  onEnregistrer: (nom: string) => void;
  onAnnuler: () => void;
}) {
  const [nom, setNom] = useState(() => nomPropose(largeurM, hauteurM, menuiseries));
  const existants = menuiseries?.modeles ?? [];
  const remplace = existants.find((modele) => modele.nom === nom.trim());
  const avis = avisSurLaMenuiserie(largeurM, hauteurM);
  return (
    <div className="th-fenetre-coupe__choix">
      <p>
        Menuiserie mesurée : <strong>{format(largeurM)} m</strong> de large, <strong>{format(hauteurM)} m</strong> de haut
        (baie entière, cadre compris).
      </p>
      {avis && <p className="th-alert th-alert--warn">{avis}</p>}
      <label>
        Nom du modèle
        <input
          list="th-modeles-existants"
          value={nom}
          maxLength={60}
          onChange={(event) => setNom(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && nom.trim()) onEnregistrer(nom.trim());
          }}
        />
        <datalist id="th-modeles-existants">
          {existants.map((modele) => (
            <option key={modele.nom} value={modele.nom} />
          ))}
        </datalist>
      </label>
      {remplace && (
        <small className="th-muted">
          Ce modèle existe ({Math.round(remplace.largeur_cm)}×{Math.round(remplace.hauteur_m * 100)}) : la nouvelle mesure le remplace
          pour ses {remplace.poses} menuiserie{remplace.poses > 1 ? "s" : ""}.
        </small>
      )}
      <div className="th-fenetre-coupe__actions">
        <button type="button" className="po2-button po2-button--primary" disabled={busy || !nom.trim()} onClick={() => onEnregistrer(nom.trim())}>
          Enregistrer le modèle et le poser
        </button>
        <button type="button" className="th-link" onClick={onAnnuler}>
          Annuler
        </button>
      </div>
    </div>
  );
}

/** Les cotes des menuiseries sur le plan (D221) : celle du modèle posé, sinon la largeur relevée. */
export function CotesMenuiseries({ cotes, toScreen }: { cotes: CoteDeMenuiserie[]; toScreen: ToScreen }) {
  return (
    <g className="th-cotes-menuiseries">
      {cotes.map((cote) => {
        const [x, y] = toScreen(cote.point);
        return (
          <text key={cote.cle} x={x} y={y - 6} textAnchor="middle" className={cote.posee ? "is-posee" : undefined}>
            {cote.texte}
          </text>
        );
      })}
    </g>
  );
}

/** La vignette d'un modèle : sa capture, chargée avec le jeton (D222). */
function Vignette({ token, projectId, modele }: { token: string; projectId: number; modele: ModeleMenuiserie }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!modele.capture) return;
    let lien: string | null = null;
    let actif = true;
    thermiqueApi
      .captureDuModele(token, projectId, modele.nom)
      .then((blob) => {
        if (!actif) return;
        lien = URL.createObjectURL(blob);
        setUrl(lien);
      })
      .catch(() => setUrl(null));
    return () => {
      actif = false;
      if (lien) URL.revokeObjectURL(lien);
    };
  }, [token, projectId, modele.nom, modele.horodatage, modele.capture]);
  return url ? <img className="th-modeles__vignette" src={url} alt={`Capture du modèle ${modele.nom}`} /> : <span className="th-modeles__vignette is-vide" />;
}

/** La bibliothèque des modèles de menuiserie du projet (D222). */
export function BibliothequeModeles({
  token,
  projectId,
  modeles,
  onPoser,
  onRetirer,
}: {
  token: string;
  projectId: number;
  modeles: ModeleMenuiserie[];
  /** Reprend le modèle pour le poser sur d'autres menuiseries du plan. */
  onPoser: (modele: ModeleMenuiserie) => void;
  onRetirer: (modele: ModeleMenuiserie) => void;
}) {
  if (!modeles.length) {
    return (
      <p className="th-muted">
        Aucun modèle mesuré. « Coupes et élévations » → « Mesurer une menuiserie » : deux coins de la baie entière, cadre compris.
      </p>
    );
  }
  return (
    <ul className="th-modeles">
      {modeles.map((modele) => (
        <li key={modele.nom}>
          <Vignette token={token} projectId={projectId} modele={modele} />
          <span>
            <strong>{modele.nom}</strong>
            <small className="th-muted">
              {Math.round(modele.largeur_cm)} × {Math.round(modele.hauteur_m * 100)} cm · mesuré sur {modele.vue} · {modele.poses} posée
              {modele.poses > 1 ? "s" : ""}
            </small>
          </span>
          <span className="th-modeles__actions">
            <button type="button" className="po2-button po2-button--ghost" onClick={() => onPoser(modele)}>
              Poser
            </button>
            <button type="button" className="th-link" onClick={() => onRetirer(modele)}>
              Retirer
            </button>
          </span>
        </li>
      ))}
    </ul>
  );
}
