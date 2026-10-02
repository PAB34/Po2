import type { StudyContent, StudyCouche, StudyParoiLocal, StudyReleveElement, StudyRoom } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";
import { EditeurComposition } from "./ElementPanel";
import {
  LIBELLES_ADJACENCE,
  etatParoi,
  paroisDeperditives,
  paroisDuLocal,
  paroisSemblables,
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
            {Math.hypot(bx - ax, by - ay) >= LONGUEUR_ETIQUETTE_PX && (
              <text className="th-paroi-local__etiquette" x={(ax + bx) / 2} y={(ay + by) / 2 - 6} textAnchor="middle">
                {etiquette(paroi)}
              </text>
            )}
            <title>{`${room.nom} · ${paroi.longueur_m} m · ${LIBELLES_ETAT[etat]}`}</title>
          </g>
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
}: {
  content: StudyContent;
  room: StudyRoom;
  paroi: StudyParoiLocal;
  busy: boolean;
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
        {!paroi.composition && paroi.vitree && (
          <p className="th-muted">
            Le relevé voit ici une menuiserie et aucun mur : cette paroi est vitrée, elle se traite à l'étape Menuiseries.
            S'il y a bien un mur opaque, composez-le ci-dessous.
          </p>
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
