import { useState } from "react";

import type { CorrectionDeVue, HautDeVue, PdfPoint, VueCoupe } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";
import { coteEcran, cotePage, pageDuCoteEcran } from "./orientation";

// Cadres des vues d'une planche de coupes ou de façades (D205) : l'agent les place mal, le thermicien les
// voit sur la planche et les redessine en deux clics.

export type CadreEnCours = { vueId: number; premier: PdfPoint | null };

/** Le cadre [x0, y0, x1, y1] de deux coins opposés cliqués dans n'importe quel ordre. */
export function cadreDeDeuxCoins(a: PdfPoint, b: PdfPoint): [number, number, number, number] {
  return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
}

/** Le côté de la page vers lequel pointe le haut de la vue. */
export function hautDeLaVue(haut: [number, number]): HautDeVue {
  return cotePage(haut);
}

/** Les modèles de menuiserie mesurés sur cette vue, avec leurs deux coins (D232) ; le dernier d'un nom fait foi. */
export function modelesDeLaVue(vue: VueCoupe): { nom: string; coins: [PdfPoint, PdfPoint] }[] {
  const parNom = new Map<string, [PdfPoint, PdfPoint]>();
  for (const mesure of vue.menuiseries ?? []) {
    if (mesure.modele && mesure.coins?.length === 2) parNom.set(mesure.modele, [mesure.coins[0], mesure.coins[1]]);
  }
  return [...parNom].map(([nom, coins]) => ({ nom, coins }));
}

/** Ce qu'on sait de la vue, en clair (D230 : plus de lecture IA ; D232 : menuiseries mesurées). */
export function etatDeLaVue(vue: VueCoupe): string {
  const nature = vue.nature === "facade" ? "élévation" : vue.nature === "detail" ? "détail" : "coupe";
  const n = modelesDeLaVue(vue).length;
  return n ? `${nature} · ${n} menuiserie${n > 1 ? "s" : ""} mesurée${n > 1 ? "s" : ""}` : nature;
}

function rectangle(cadre: number[], toScreen: ToScreen) {
  const coins = [toScreen([cadre[0], cadre[1]]), toScreen([cadre[2], cadre[3]])];
  const x = Math.min(coins[0][0], coins[1][0]);
  const y = Math.min(coins[0][1], coins[1][1]);
  return { x, y, width: Math.abs(coins[1][0] - coins[0][0]), height: Math.abs(coins[1][1] - coins[0][1]) };
}

export function CadresDesVues({
  vues,
  toScreen,
  choisie,
  enCours,
  survol,
}: {
  vues: VueCoupe[];
  toScreen: ToScreen;
  choisie: number | null;
  enCours: CadreEnCours | null;
  survol: PdfPoint | null;
}) {
  return (
    <g className="th-cadres-vues">
      {vues.map((vue) => {
        const r = rectangle(vue.cadre, toScreen);
        const classes = ["th-cadre-vue", vue.id === choisie ? "is-choisie" : ""].join(" ");
        return (
          <g key={vue.id} className={classes}>
            <rect {...r} />
            <text x={r.x + 6} y={r.y + 16}>
              {vue.nom} · {etatDeLaVue(vue)}
            </text>
            {/* D232 : chaque menuiserie mesurée se voit à sa place, avec son modèle. */}
            {modelesDeLaVue(vue).map((modele) => {
              const m = rectangle([...modele.coins[0], ...modele.coins[1]], toScreen);
              return (
                <g key={modele.nom} className="th-menuiserie-mesuree">
                  <rect {...m} />
                  <text x={m.x + 3} y={m.y - 4}>
                    {modele.nom}
                  </text>
                </g>
              );
            })}
          </g>
        );
      })}
      {enCours?.premier && survol && (
        <rect className="th-cadre-vue__trace" {...rectangle(cadreDeDeuxCoins(enCours.premier, survol), toScreen)} />
      )}
    </g>
  );
}

export const HAUTS: { id: HautDeVue; label: string }[] = [
  { id: "haut", label: "en haut" },
  { id: "droite", label: "à droite" },
  { id: "bas", label: "en bas" },
  { id: "gauche", label: "à gauche" },
];

/** Le nom d'une vue, modifiable sur place (D206) : Entrée enregistre, Échap abandonne. */
function NomDeLaVue({ vue, busy, onChoisir, onRenommer }: {
  vue: VueCoupe;
  busy: boolean;
  onChoisir: () => void;
  onRenommer: (nom: string) => void;
}) {
  const [saisie, setSaisie] = useState<string | null>(null);
  if (saisie === null) {
    return (
      <span className="th-vues__nom">
        <button type="button" className="th-link" onClick={onChoisir}>
          <strong>{vue.nom}</strong>
        </button>
        <button type="button" className="th-link" disabled={busy} onClick={() => setSaisie(vue.nom)} title="Renommer la vue">
          Renommer
        </button>
      </span>
    );
  }
  const valider = () => {
    const nom = saisie.trim();
    setSaisie(null);
    if (nom && nom !== vue.nom) onRenommer(nom);
  };
  return (
    <input
      className="th-vues__saisie"
      aria-label={`Nouveau nom de ${vue.nom}`}
      autoFocus
      value={saisie}
      onChange={(event) => setSaisie(event.target.value)}
      onBlur={valider}
      onKeyDown={(event) => {
        if (event.key === "Enter") valider();
        if (event.key === "Escape") setSaisie(null);
      }}
    />
  );
}

/** Le cadre en cours de tracé désigne une vue qui n'existe pas encore (D231). */
export const NOUVELLE_VUE = -1;

/** Après les deux coins : nom, nature et haut de la nouvelle vue (D231). */
function NouvelleVue({
  cadre,
  transform,
  rang,
  busy,
  onCreer,
  onAbandonner,
}: {
  cadre: number[];
  transform?: number[];
  rang: number;
  busy: boolean;
  onCreer: (vue: { nom: string; nature: "coupe" | "facade"; cadre: number[]; haut: HautDeVue }) => void;
  onAbandonner?: () => void;
}) {
  const [nom, setNom] = useState(`Vue ${rang}`);
  const [nature, setNature] = useState<"coupe" | "facade">("facade");
  const [haut, setHaut] = useState<HautDeVue>("haut");
  return (
    <div className="th-nouvelle-vue">
      <label>
        Nom
        <input value={nom} maxLength={80} autoFocus onChange={(event) => setNom(event.target.value)} />
      </label>
      <label>
        Nature
        <select value={nature} onChange={(event) => setNature(event.target.value as "coupe" | "facade")}>
          <option value="facade">élévation</option>
          <option value="coupe">coupe</option>
        </select>
      </label>
      <label>
        Haut du dessin
        <select value={haut} onChange={(event) => setHaut(event.target.value as HautDeVue)}>
          {HAUTS.map((h) => (
            <option key={h.id} value={h.id}>
              {h.label}
            </option>
          ))}
        </select>
      </label>
      <span className="th-vues__actions">
        <button
          type="button"
          className="po2-button po2-button--primary"
          disabled={busy || !nom.trim()}
          onClick={() => onCreer({ nom: nom.trim(), nature, cadre, haut: transform ? pageDuCoteEcran(haut, transform) : haut })}
        >
          Créer la vue
        </button>
        <button type="button" className="th-link" onClick={onAbandonner}>
          Abandonner
        </button>
      </span>
    </div>
  );
}

export function ListeDesVues({
  vues,
  choisie,
  enCours,
  busy,
  transform,
  onChoisir,
  onRedessiner,
  onCorriger,
  onSupprimer,
  nouvelle = null,
  onAjouter,
  onCreer,
  onAbandonner,
}: {
  vues: VueCoupe[];
  choisie: number | null;
  enCours: CadreEnCours | null;
  busy: boolean;
  /** Transformation du raster affiché : le haut se choisit tel qu'on le voit à l'écran (D207). */
  transform?: number[];
  onChoisir: (vueId: number) => void;
  onRedessiner: (vueId: number) => void;
  onCorriger: (vueId: number, correction: CorrectionDeVue) => void;
  onSupprimer: (vue: VueCoupe) => void;
  /** D231 : cadre de la vue en cours de création, une fois ses deux coins cliqués. */
  nouvelle?: number[] | null;
  onAjouter?: () => void;
  onCreer?: (vue: { nom: string; nature: "coupe" | "facade"; cadre: number[]; haut: HautDeVue }) => void;
  onAbandonner?: () => void;
}) {
  const ajout = enCours?.vueId === NOUVELLE_VUE;
  const entete = (
    <>
      <p className="th-muted">
        Une vue par coupe ou élévation : cadrez-la (tout le dessin et ses cotes de niveau), nommez-la comme sur le plan
        (« Coupe A », « Façade Nord »), et dites où se trouve le haut du dessin tel que vous le voyez.
      </p>
      {onAjouter && !nouvelle && (
        <button type="button" className="po2-button po2-button--primary" disabled={busy || ajout} onClick={onAjouter}>
          {ajout ? (enCours?.premier ? "Cliquez le coin opposé…" : "Cliquez un coin de la vue…") : "Ajouter une vue"}
        </button>
      )}
      {nouvelle && onCreer && (
        <NouvelleVue
          cadre={nouvelle}
          transform={transform}
          rang={vues.length + 1}
          busy={busy}
          onCreer={onCreer}
          onAbandonner={onAbandonner}
        />
      )}
    </>
  );
  if (!vues.length) {
    return (
      <>
        {entete}
        <p className="th-muted">Aucune vue sur cette planche.</p>
      </>
    );
  }
  return (
    <>
      {entete}
      <ul className="th-vues">
        {vues.map((vue) => (
          <li key={vue.id} className={vue.id === choisie ? "is-choisie" : undefined}>
            <NomDeLaVue
              vue={vue}
              busy={busy}
              onChoisir={() => onChoisir(vue.id)}
              onRenommer={(nom) => onCorriger(vue.id, { nom })}
            />
            <span className="th-muted">{etatDeLaVue(vue)}</span>
            <span className="th-vues__actions">
              <label className="th-inline">
                Nature
                <select
                  value={vue.nature}
                  disabled={busy || vue.nature === "detail"}
                  onChange={(event) => onCorriger(vue.id, { nature: event.target.value as "coupe" | "facade" })}
                >
                  <option value="coupe">coupe</option>
                  <option value="facade">façade</option>
                  {vue.nature === "detail" && <option value="detail">détail</option>}
                </select>
              </label>
              <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={() => onRedessiner(vue.id)}>
                {enCours?.vueId === vue.id ? (enCours.premier ? "Cliquez le coin opposé…" : "Cliquez un coin…") : "Redessiner le cadre"}
              </button>
              <label className="th-inline">
                Haut du dessin
                <select
                  value={transform ? coteEcran(vue.haut, transform) : hautDeLaVue(vue.haut)}
                  disabled={busy}
                  onChange={(event) => {
                    const cote = event.target.value as HautDeVue;
                    onCorriger(vue.id, { haut: transform ? pageDuCoteEcran(cote, transform) : cote });
                  }}
                >
                  {HAUTS.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.label}
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" className="th-link" disabled={busy} onClick={() => onSupprimer(vue)}>
                Supprimer
              </button>
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}
