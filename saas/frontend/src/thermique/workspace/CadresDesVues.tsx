import type { HautDeVue, PdfPoint, VueCoupe } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";

// Cadres des vues d'une planche de coupes ou de façades (D205) : l'agent les place mal, le thermicien les
// voit sur la planche et les redessine en deux clics.

export type CadreEnCours = { vueId: number; premier: PdfPoint | null };

/** Le cadre [x0, y0, x1, y1] de deux coins opposés cliqués dans n'importe quel ordre. */
export function cadreDeDeuxCoins(a: PdfPoint, b: PdfPoint): [number, number, number, number] {
  return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
}

/** Le côté de la page vers lequel pointe le haut de la vue. */
export function hautDeLaVue(haut: [number, number]): HautDeVue {
  const [x, y] = haut;
  if (Math.abs(x) > Math.abs(y)) return x > 0 ? "droite" : "gauche";
  return y < 0 ? "bas" : "haut";
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

const HAUTS: { id: HautDeVue; label: string }[] = [
  { id: "haut", label: "en haut" },
  { id: "droite", label: "à droite" },
  { id: "bas", label: "en bas" },
  { id: "gauche", label: "à gauche" },
];

export function ListeDesVues({
  vues,
  choisie,
  enCours,
  busy,
  onChoisir,
  onRedessiner,
  onHaut,
  onSupprimer,
}: {
  vues: VueCoupe[];
  choisie: number | null;
  enCours: CadreEnCours | null;
  busy: boolean;
  onChoisir: (vueId: number) => void;
  onRedessiner: (vueId: number) => void;
  onHaut: (vueId: number, haut: HautDeVue) => void;
  onSupprimer: (vue: VueCoupe) => void;
}) {
  if (!vues.length) return <p className="th-muted">Aucune vue lue sur cette planche.</p>;
  return (
    <>
      <p className="th-muted">
        Chaque vue est encadrée sur la planche. Si un cadre ne couvre pas toute la vue (bâtiment, cotes de niveau),
        redessinez-le : la coupe sera relue dans le bon cadre.
      </p>
      <ul className="th-vues">
        {vues.map((vue) => (
          <li key={vue.id} className={vue.id === choisie ? "is-choisie" : undefined}>
            <button type="button" className="th-link" onClick={() => onChoisir(vue.id)}>
              <strong>{vue.nom}</strong>
            </button>
            <span className="th-muted">{etatDeLaVue(vue)}</span>
            <span className="th-vues__actions">
              <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={() => onRedessiner(vue.id)}>
                {enCours?.vueId === vue.id ? (enCours.premier ? "Cliquez le coin opposé…" : "Cliquez un coin…") : "Redessiner le cadre"}
              </button>
              <label className="th-inline">
                Haut de la vue
                <select value={hautDeLaVue(vue.haut)} disabled={busy} onChange={(event) => onHaut(vue.id, event.target.value as HautDeVue)}>
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
