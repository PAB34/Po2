import type { ModeleMenuiserie, StudyContent, StudyCouche, StudyParoiLocal, StudyReleveElement, StudyRoom } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";
import { EditeurComposition } from "./ElementPanel";
import {
  LIBELLES_ADJACENCE,
  etatParoi,
  paroisDeperditives,
  paroisDuLocal,
  paroisSemblables,
  surfacesParoi,
  type ParoiRef,
} from "./paroisLocaux";

// Option C (D262) : à l'étape Parois, on compose les parois des locaux. Vert = validée, orange = proposée par le
// relevé de l'IA, rouge = rien de proposé, bleu = vitrée (traitée à l'étape Menuiseries).

const LIBELLES_ETAT = { validee: "validée", proposee: "proposée, à valider", vide: "à composer", vitree: "vitrée (étape Menuiseries)" } as const;
const LONGUEUR_ETIQUETTE_PX = 60;

function etiquette(paroi: StudyParoiLocal): string {
  const composition = paroi.composition ?? paroi.proposition;
  if (!composition) return paroi.vitree ? "vitrée" : "à composer";
  return `${composition.composant ?? "paroi"} · ${composition.epaisseur_cm} cm`;
}

/** Les parois déperditives de tous les locaux, dessinées sur le plan et colorées selon leur état. */
export function ParoisDesLocaux({
  content,
  choisie,
  toScreen,
}: {
  content: StudyContent;
  choisie: ParoiRef | null;
  toScreen: ToScreen;
}) {
  return (
    <g className="th-parois-locaux">
      {paroisDeperditives(content).map(({ room, paroi }) => {
        const trace = paroi.trace_pdf ?? [];
        if (trace.length < 2) return null;
        const [ax, ay] = toScreen(trace[0]);
        const [bx, by] = toScreen(trace[trace.length - 1]);
        const vise = choisie?.local === room.id && choisie.rang === paroi.rang;
        const etat = etatParoi(paroi);
        return (
          <g key={`${room.id}-${paroi.rang}`} className={`th-paroi-local is-${etat}${vise ? " is-choisie" : ""}`}>
            {vise && <line className="th-paroi-local__halo" x1={ax} y1={ay} x2={bx} y2={by} />}
            <line className="th-paroi-local__trait" x1={ax} y1={ay} x2={bx} y2={by} />
            {/* D270 : les menuiseries posées sur la paroi, en bleu sur sa ligne. */}
            {(paroi.menuiseries ?? []).map((pose, rang) => {
              const t = pose.trace_pdf ?? [];
              if (t.length < 2) return null;
              const [mx0, my0] = toScreen(t[0]);
              const [mx1, my1] = toScreen(t[t.length - 1]);
              return <line key={rang} className="th-paroi-local__baie" x1={mx0} y1={my0} x2={mx1} y2={my1} />;
            })}
            {Math.hypot(bx - ax, by - ay) >= LONGUEUR_ETIQUETTE_PX && (
              <text className="th-paroi-local__etiquette" x={(ax + bx) / 2} y={(ay + by) / 2 - 6} textAnchor="middle">
                {etiquette(paroi)}
              </text>
            )}
            <title>{`${room.nom} · ${paroi.longueur_m} m · ${LIBELLES_ETAT[etat]}`}</title>
          </g>
        );
      })}
      {/* D264 : les coupures posées, clic droit dessus pour les retirer. */}
      {(content.coupures_parois ?? []).map((coupure, rang) => {
        if (!coupure.point_pdf) return null;
        const [x, y] = toScreen(coupure.point_pdf);
        return (
          <circle key={`coupure-${rang}`} className="th-coupure-paroi" cx={x} cy={y} r={5}>
            <title>Coupure de paroi : clic droit pour la retirer</title>
          </circle>
        );
      })}
    </g>
  );
}

/** La fiche d'une paroi : ce qu'il y a derrière, sa longueur, sa composition à valider (D262). */
export function FicheParoi({
  content,
  room,
  paroi,
  busy,
  onValider,
  onRetour,
  hauteurLocal = null,
  modeles = [],
}: {
  content: StudyContent;
  room: StudyRoom;
  paroi: StudyParoiLocal;
  busy: boolean;
  /** Hauteur sous plafond du local (coupes ou saisie), pour les surfaces (D269). */
  hauteurLocal?: number | null;
  /** Modèles de menuiserie du projet : leur hauteur donne la surface des baies. */
  modeles?: ModeleMenuiserie[];
  onValider: (couches: StudyCouche[], composant: string | null, aussi: { room: StudyRoom; paroi: StudyParoiLocal }[]) => void;
  onRetour: () => void;
}) {
  const semblables = paroisSemblables(content, room, paroi);
  const source = paroi.composition ?? paroi.proposition;
  // Le formulaire de composition des murs sert tel quel : il lit `couches`, `composant` et l'état validé.
  const commeUnMur = {
    couches: source?.couches ?? [],
    composant: source?.composant ?? null,
    corrige: Boolean(paroi.composition),
  } as unknown as StudyReleveElement;
  const derriere = paroi.adjacence === "non_chauffe" && paroi.voisin ? `« ${paroi.voisin} » (non chauffé)` : LIBELLES_ADJACENCE[paroi.adjacence] ?? paroi.adjacence;
  return (
    <section className="th-elements th-elements--seul">
      <button type="button" className="th-link th-element-retour" onClick={onRetour}>
        ← Revenir à « {room.nom} »
      </button>
      <article className="th-element-detail">
        <header>
          <strong>
            Paroi de « {room.nom} » · {paroi.longueur_m.toLocaleString("fr-FR")} m
          </strong>
          <span className={`th-badge th-paroi-badge is-${etatParoi(paroi)}`}>{LIBELLES_ETAT[etatParoi(paroi)]}</span>
        </header>
        <p className="th-muted">
          Derrière : <strong>{derriere}</strong>
          {paroi.orientation ? ` · orientation ${paroi.orientation}` : ""} · épaisseur lue sur le plan {paroi.epaisseur_cm} cm
        </p>
        <MenuiseriesEtSurfaces paroi={paroi} hauteurLocal={hauteurLocal} modeles={modeles} />
        {!paroi.composition && paroi.vitree && (
          <p className="th-muted">
            Le relevé voit ici une menuiserie et aucun mur : cette paroi est vitrée, elle se traite à l'étape Menuiseries.
            S'il y a bien un mur opaque, composez-le ci-dessous.
          </p>
        )}
        {paroi.composition?.reprise && (
          <p className="th-muted">Composition reprise du mur que vous aviez déjà validé dans le relevé.</p>
        )}
        {!paroi.composition && paroi.proposition && (
          <p className="th-muted">Proposition tirée du relevé de l'IA : vérifiez les couches, puis validez.</p>
        )}
        <EditeurComposition
          key={`${room.id}-${paroi.rang}-${paroi.composition?.id ?? "p"}`}
          element={commeUnMur}
          autres={semblables.length}
          busy={busy}
          onValider={(couches, partout) => onValider(couches, source?.composant ?? null, partout ? semblables : [])}
        />
      </article>
    </section>
  );
}

const m2 = (valeur: number) => `${valeur.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m²`;

/** D269 : les menuiseries posées sur la paroi et ses surfaces (brute, baies, opaque), ce qui manque dit en clair. */
function MenuiseriesEtSurfaces({
  paroi,
  hauteurLocal,
  modeles,
}: {
  paroi: StudyParoiLocal;
  hauteurLocal: number | null;
  modeles: ModeleMenuiserie[];
}) {
  const poses = paroi.menuiseries ?? [];
  const surfaces = surfacesParoi(paroi, hauteurLocal, modeles);
  return (
    <div className="th-paroi-surfaces">
      {poses.length > 0 ? (
        <ul className="th-paroi-surfaces__baies">
          {poses.map((pose, rang) => (
            <li key={rang}>
              Menuiserie {pose.composant ?? ""} · {pose.largeur_m.toLocaleString("fr-FR")} m
              {pose.modele ? ` · modèle ${pose.modele}` : " · sans modèle"}
            </li>
          ))}
        </ul>
      ) : (
        <p className="th-muted">Aucune menuiserie posée sur cette paroi.</p>
      )}
      <p>
        Surface : {surfaces.brute_m2 != null ? m2(surfaces.brute_m2) : "—"} brute
        {poses.length > 0 && ` − ${m2(surfaces.baies_m2)} de baies`}
        {surfaces.opaque_m2 != null && (
          <>
            {" "}= <strong>{m2(surfaces.opaque_m2)} opaques</strong>
          </>
        )}
      </p>
      {surfaces.manques.length > 0 && <p className="th-muted">À compléter : {surfaces.manques.join(" ; ")}.</p>}
    </div>
  );
}

/** Les parois à composer du local ouvert, cliquables. */
export function ListeParoisDuLocal({
  room,
  onChoisir,
}: {
  room: StudyRoom;
  onChoisir: (ref: ParoiRef) => void;
}) {
  const parois = paroisDuLocal(room).filter((paroi) => paroi.deperditif);
  return (
    <section className="th-elements">
      <h2 className="th-panel__title">{room.nom}</h2>
      {parois.length === 0 ? (
        <p className="th-muted">Ce local n'a aucune paroi déperditive : rien à composer ici.</p>
      ) : (
        <ul className="th-element-liste">
          {parois.map((paroi) => (
            <li key={paroi.rang}>
              <button type="button" onClick={() => onChoisir({ local: room.id, rang: paroi.rang })}>
                <span className="th-element-nom">
                  {LIBELLES_ADJACENCE[paroi.adjacence] ?? paroi.adjacence}
                  {paroi.orientation ? ` · ${paroi.orientation}` : ""}
                </span>
                <span className="th-element-mesure">
                  {paroi.longueur_m.toLocaleString("fr-FR")} m · {etiquette(paroi)}
                </span>
                <span className={`th-badge th-paroi-badge is-${etatParoi(paroi)}`}>{LIBELLES_ETAT[etatParoi(paroi)]}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
