import type { HauteursDuPlan, PdfPoint, VueCoupe } from "../api";

// Le trait d'une coupe tracé à la main sur le plan (D209) : deux clics aux extrémités, un troisième du côté
// regardé. La coupe reste ainsi sur le plan même quand l'IA ne l'a pas (ou plus) située.

export type TraitEnCours = { vueId: number; points: PdfPoint[] };

/** Le sens du regard : perpendiculaire au trait, du côté du troisième clic. */
export function sensDuTrait(a: PdfPoint, b: PdfPoint, cote: PdfPoint): [number, number] {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const norme = Math.hypot(dx, dy) || 1;
  let nx = -dy / norme;
  let ny = dx / norme;
  if ((cote[0] - a[0]) * nx + (cote[1] - a[1]) * ny < 0) {
    nx = -nx;
    ny = -ny;
  }
  return [nx, ny];
}

/** La consigne du clic attendu. */
export function consigneDuTrait(trait: TraitEnCours, nom: string): string {
  if (trait.points.length === 0) return `${nom} : cliquez une extrémité du trait de coupe sur le plan.`;
  if (trait.points.length === 1) return `${nom} : cliquez l'autre extrémité du trait.`;
  return `${nom} : cliquez du côté où regarde la coupe (côté des flèches du trait).`;
}

export type PlaceDeLaCoupe = "a_la_main" | "situee" | "non_situee";

export function placeDeLaCoupe(vue: VueCoupe, hauteurs: HauteursDuPlan | undefined): PlaceDeLaCoupe {
  if (hauteurs?.traits.some((t) => t.manuel && t.vue_id === vue.id)) return "a_la_main";
  if (hauteurs?.coupes.some((c) => c.vue_id === vue.id)) return "situee";
  return "non_situee";
}

const LIBELLES: Record<PlaceDeLaCoupe, string> = {
  a_la_main: "tracée à la main",
  situee: "située",
  non_situee: "non située",
};

export function PlacerCoupes({
  coupes,
  hauteurs,
  enCours,
  busy,
  message,
  onTracer,
  onAnnuler,
}: {
  coupes: VueCoupe[];
  hauteurs: HauteursDuPlan | undefined;
  enCours: TraitEnCours | null;
  busy: boolean;
  message: string | null;
  onTracer: (vueId: number) => void;
  onAnnuler: () => void;
}) {
  const nonSituees = coupes.filter((vue) => placeDeLaCoupe(vue, hauteurs) === "non_situee").length;
  const enTrace = enCours ? coupes.find((vue) => vue.id === enCours.vueId) : undefined;
  return (
    <details className="th-placer-coupes" open={Boolean(enCours) || undefined}>
      <summary>
        Placer les coupes{nonSituees > 0 ? ` (${nonSituees} non située${nonSituees > 1 ? "s" : ""})` : ""}
      </summary>
      {enCours && enTrace && (
        <p className="th-placer-coupes__consigne">
          {consigneDuTrait(enCours, enTrace.nom)}{" "}
          <button type="button" className="th-link" onClick={onAnnuler}>
            Annuler (Échap)
          </button>
        </p>
      )}
      {message && <p className="th-placer-coupes__consigne">{message}</p>}
      {coupes.length === 0 ? (
        <p className="th-muted">Aucune coupe lue dans le projet.</p>
      ) : (
        <ul>
          {coupes.map((vue) => {
            const place = placeDeLaCoupe(vue, hauteurs);
            return (
              <li key={vue.id}>
                <strong>{vue.nom}</strong>
                <span className={`th-placer-coupes__etat is-${place}`}>{LIBELLES[place]}</span>
                <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={() => onTracer(vue.id)}>
                  {place === "non_situee" ? "Tracer" : "Retracer"}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </details>
  );
}
