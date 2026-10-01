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

/** Ce qu'on sait de la vue, en clair. */
export function etatDeLaVue(vue: VueCoupe): string {
  if (vue.nature !== "coupe") return vue.nature === "facade" ? "façade" : "détail";
  if (vue.a_relire) return "à relire : cadre corrigé";
  const n = vue.pieces?.length ?? 0;
  return n ? `${n} pièce${n > 1 ? "s" : ""} lue${n > 1 ? "s" : ""}` : "aucune pièce lue : cadre à vérifier";
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
        const classes = ["th-cadre-vue", vue.id === choisie ? "is-choisie" : "", vue.a_relire ? "is-a-relire" : ""].join(" ");
        return (
          <g key={vue.id} className={classes}>
            <rect {...r} />
            <text x={r.x + 6} y={r.y + 16}>
              {vue.nom} · {etatDeLaVue(vue)}
            </text>
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
}) {
  if (!vues.length) return <p className="th-muted">Aucune vue lue sur cette planche.</p>;
  return (
    <>
      <p className="th-muted">
        Vérifiez chaque vue sur la planche : son nom (celui du trait sur le plan), sa nature, son cadre (tout le
        bâtiment et les cotes de niveau) et le côté où se trouve le haut du dessin, tel que vous le voyez.
      </p>
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
