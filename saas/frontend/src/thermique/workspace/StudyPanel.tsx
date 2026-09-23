import { Fragment, useState } from "react";
import type { CSSProperties, KeyboardEvent } from "react";

import type { PdfPoint, Study, StudyRoom } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";
import { LIMIT_COLORS, LIMIT_LABELS, type StudyDraft } from "./edition";
import { NATURE_COLORS, NATURE_LABELS, sortedStudyRooms } from "./study";

const meters = (value: number | undefined) => (value == null ? "—" : `${value.toLocaleString("fr-FR")} m`);
const squareMeters = (value: number | undefined) => (value == null ? "—" : `${value.toLocaleString("fr-FR")} m²`);

export function StudyOverlay({
  rooms,
  selectedId,
  toScreen,
  onSelect,
  draft,
  gaps,
  locked = false,
}: {
  rooms: StudyRoom[];
  selectedId: string | null;
  toScreen: ToScreen;
  onSelect: (id: string) => void;
  draft?: StudyDraft | null;
  gaps?: PdfPoint[][];
  /** Vrai quand le plan est occupé par un autre geste (mesure, calage, édition) : les locaux s'effacent. */
  locked?: boolean;
}) {
  // Le pointeur n'est jamais retenu ici : il doit atteindre le plan pour pouvoir le déplacer, même posé
  // sur un local. La sélection se fait donc au clic simple, côté visionneuse, qui seule sait distinguer
  // un clic d'un déplacement (voir `onPick`).
  const selectWithKeyboard = (event: KeyboardEvent<SVGGElement>, id: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(id);
    }
  };
  const trace = (points: PdfPoint[]) => points.map(toScreen).map(([x, y]) => `${x},${y}`).join(" ");
  return (
    <>
      {(gaps ?? []).map((zone, index) => (
        <polygon key={`vide-${index}`} className="th-study-gap" points={trace(zone)}>
          <title>Intérieur non affecté à un local</title>
        </polygon>
      ))}
      {rooms.map((room) => {
        const edited = draft?.roomId === room.id ? draft.contour : room.contour_pdf;
        const selected = room.id === selectedId;
        // Pendant une édition, une mesure ou un calage, les polygones laissent passer les clics :
        // ils vont au plan, pas à la sélection.
        const inerte = Boolean(draft) || locked;
        const classes = ["th-study-room", selected ? "is-selected" : "", inerte ? "is-locked" : ""].filter(Boolean);
        return (
          <g
            key={room.id}
            className={classes.join(" ")}
            style={{ "--room-color": NATURE_COLORS[room.nature] } as CSSProperties}
            role="button"
            tabIndex={inerte ? -1 : 0}
            aria-label={`Ouvrir la fiche de ${room.nom}`}
            onKeyDown={(event) => selectWithKeyboard(event, room.id)}
          >
            <polygon points={trace(edited)}>
              <title>{`${room.nom} · ${NATURE_LABELS[room.nature]} · ${squareMeters(room.surface_m2)}`}</title>
            </polygon>
            {selected &&
              edited.map((vertex, index) => {
                const next = edited[(index + 1) % edited.length];
                const limite = room.limites?.[index] ?? "convention";
                const [x1, y1] = toScreen(vertex);
                const [x2, y2] = toScreen(next);
                return (
                  <line
                    key={`cote-${index}`}
                    className="th-study-side"
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={LIMIT_COLORS[limite]}
                    strokeDasharray={limite === "convention" ? "6 4" : undefined}
                  >
                    <title>{`Côté ${index + 1} · ${LIMIT_LABELS[limite]}`}</title>
                  </line>
                );
              })}
          </g>
        );
      })}
      {draft && (
        <g className="th-study-draft">
          {draft.contour.map((vertex, index) => {
            const [x, y] = toScreen(vertex);
            return <circle key={`poignee-${index}`} cx={x} cy={y} r={5} />;
          })}
          {draft.cut.length > 0 && (
            <polyline className="th-study-cut" points={trace(draft.cut)} fill="none" />
          )}
        </g>
      )}
    </>
  );
}

export function StudyRoomList({ study, selectedId, onSelect }: { study: Study; selectedId: string | null; onSelect: (id: string) => void }) {
  return (
    <div className="th-study-list">
      {sortedStudyRooms(study.content.locaux).map((room) => {
        const state = study.local_states[room.id]?.status ?? "a_verifier";
        return (
          <button key={room.id} type="button" className={room.id === selectedId ? "is-active" : undefined} onClick={() => onSelect(room.id)}>
            <span className={`th-study-state th-study-state--${state}`} aria-label={state.replace(/_/g, " ")} />
            <span>
              <strong>{room.nom}</strong>
              <small>{NATURE_LABELS[room.nature]} · {squareMeters(room.surface_m2)} · {(room.fiche.alertes ?? []).length} alerte(s)</small>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function EnvelopeItems({ items }: { items: NonNullable<StudyRoom["synthese"]["parois"]> }) {
  if (!items.length) {
    return <p className="th-muted">Aucun élément rattaché.</p>;
  }
  return (
    <ul className="th-study-items">
      {items.map((item, index) => (
        <li key={`${item.composant ?? item.type ?? "element"}-${index}`}>
          <strong>{item.composant ?? item.type ?? "Élément"}</strong>
          <span>{item.composition ?? item.type ? `${item.composition ?? item.type} · ` : ""}{meters(item.lineaire_m)}</span>
        </li>
      ))}
    </ul>
  );
}

export type StudyEdition = {
  draft: StudyDraft | null;
  busy: boolean;
  message: string | null;
  blocking: string | null;
  neighbours: string[];
  coverage: Study["content"]["couverture"] | null;
  versions: { version_number: number; reason: string; created_at: string }[];
  rooms: StudyRoom[];
  onStart: (mode: "contour" | "couper") => void;
  onCancel: () => void;
  onDraft: (changes: Partial<Pick<StudyDraft, "nature" | "nom" | "noms">>) => void;
  onRecompute: () => void;
  onSave: () => void;
  onMerge: (otherId: string) => void;
  onRestore: (numero: number) => void;
};

function EditionSection({ room, edition }: { room: StudyRoom; edition: StudyEdition }) {
  const { draft } = edition;
  const libres = (room.limites ?? []).filter((limite) => limite === "convention").length;
  return (
    <section className="th-study-edit">
      <h2>Modifier ce local</h2>
      <p className="th-muted">
        {libres > 0
          ? `${libres} côté(s) sans paroi lue : vous pouvez les déplacer librement.`
          : "Tous les côtés suivent une paroi lue ou l'enveloppe."}
      </p>
      {!draft && (
        <div className="th-study-actions">
          <button type="button" className="po2-button po2-button--ghost" onClick={() => edition.onStart("contour")}>
            Reprendre le contour
          </button>
          <button type="button" className="po2-button po2-button--ghost" onClick={() => edition.onStart("couper")}>
            Couper en deux
          </button>
        </div>
      )}
      {draft && (
        <>
          <p className="th-muted">
            {draft.mode === "contour"
              ? "Faites glisser une poignée pour déplacer un sommet, cliquez sur un côté pour en ajouter un, Alt+clic sur une poignée pour la retirer."
              : "Cliquez deux points pour tracer la limite ; le trait est prolongé jusqu'aux bords du local."}
          </p>
          {draft.mode === "couper" ? (
            <>
              <label>
                Nom de la première moitié
                <input value={draft.noms[0]} onChange={(event) => edition.onDraft({ noms: [event.target.value, draft.noms[1]] })} />
              </label>
              <label>
                Nom de la seconde moitié
                <input value={draft.noms[1]} onChange={(event) => edition.onDraft({ noms: [draft.noms[0], event.target.value] })} />
              </label>
            </>
          ) : (
            <label>
              Nom
              <input value={draft.nom} onChange={(event) => edition.onDraft({ nom: event.target.value })} />
            </label>
          )}
          <label hidden={draft.mode === "couper"}>
            Nature
            <select
              value={draft.nature}
              onChange={(event) => edition.onDraft({ nature: event.target.value as StudyRoom["nature"] })}
            >
              {(Object.keys(NATURE_LABELS) as StudyRoom["nature"][]).map((nature) => (
                <option key={nature} value={nature}>
                  {NATURE_LABELS[nature]}
                </option>
              ))}
            </select>
          </label>
          <div className="th-study-actions">
            <button type="button" className="po2-button po2-button--ghost" onClick={edition.onRecompute} disabled={edition.busy}>
              Remodéliser
            </button>
            <button type="button" className="po2-button" onClick={edition.onSave} disabled={edition.busy || Boolean(edition.blocking)}>
              Enregistrer et suivant
            </button>
            <button type="button" className="po2-button po2-button--ghost" onClick={edition.onCancel} disabled={edition.busy}>
              Annuler
            </button>
          </div>
        </>
      )}
      <label>
        Fusionner avec
        <select value="" onChange={(event) => event.target.value && edition.onMerge(event.target.value)}>
          <option value="">choisir un local mitoyen…</option>
          {edition.rooms
            .filter((other) => other.id !== room.id)
            .map((other) => (
              <option key={other.id} value={other.id}>
                {other.nom}
              </option>
            ))}
        </select>
      </label>
      {edition.busy && <p className="th-muted">Calcul en cours… (le rattachement de l'enveloppe prend quelques secondes)</p>}
      {edition.blocking && <p className="th-alert th-alert--error">{edition.blocking}</p>}
      {edition.message && <p className="th-alert th-alert--warn">{edition.message}</p>}
      {edition.neighbours.length > 0 && (
        <p className="th-muted">{edition.neighbours.length} local/locaux voisins repasseront à revoir.</p>
      )}
      {edition.versions.length > 0 && (
        <details className="th-study-versions">
          <summary>Versions ({edition.versions.length})</summary>
          <ul>
            {edition.versions.map((version) => (
              <li key={version.version_number}>
                <span>
                  n° {version.version_number} · {version.reason.replace(/_/g, " ")}
                </span>
                <button type="button" className="po2-button po2-button--ghost" onClick={() => edition.onRestore(version.version_number)}>
                  Revenir ici
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

export function StudyRoomPanel({
  room,
  state,
  edition,
}: {
  room: StudyRoom | null;
  state?: Study["local_states"][string];
  edition?: StudyEdition;
}) {
  if (!room) {
    return <p className="th-muted">Sélectionnez un local sur le plan ou dans la liste pour ouvrir sa fiche.</p>;
  }
  const sheet = room.fiche;
  return (
    <>
      <div>
        <h2 className="th-panel__title">{room.nom}</h2>
        <p className="th-muted">{NATURE_LABELS[room.nature]} · {squareMeters(sheet.surface_m2)} · périmètre {meters(sheet.perimetre_m)}</p>
        <span className={`th-badge th-study-badge--${state?.status ?? "a_verifier"}`}>
          {(state?.status ?? "a_verifier").replace(/_/g, " ")}
        </span>
      </div>

      <section>
        <h2>Côtés et adjacences</h2>
        <div className="th-study-sides">
          {sheet.cotes.map((side, index) => (
            <article key={`${side.adjacence}-${index}`} className={side.deperditif ? "is-loss" : undefined}>
              <div><strong>{side.adjacence.replace(/_/g, " ")}</strong><span>{meters(side.longueur_m)}</span></div>
              <small>{side.voisin || "voisin non identifié"} · {side.epaisseur_cm == null ? "épaisseur inconnue" : `${side.epaisseur_cm} cm`} · {side.orientation || "orientation inconnue"}</small>
              {(side.enveloppe ?? []).length > 0 && <EnvelopeItems items={side.enveloppe ?? []} />}
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2>Parois rattachées</h2>
        <EnvelopeItems items={room.synthese.parois ?? []} />
        {(room.synthese.sur_non_chauffe_m ?? 0) > 0 && <p className="th-alert th-alert--warn">Sur local non chauffé ou vide : {meters(room.synthese.sur_non_chauffe_m)}</p>}
      </section>

      <section>
        <h2>Baies</h2>
        <EnvelopeItems items={sheet.baies ?? room.synthese.menuiseries ?? []} />
      </section>

      <section>
        <h2>Liaisons</h2>
        <ul className="th-ws-facts">
          {/* Un pont est compté, pas mesuré : la valeur est un nombre de liaisons, une demie étant
              partagée avec le local voisin. L'afficher en mètres était faux. */}
          {Object.entries(sheet.ponts ?? room.synthese.ponts ?? {}).map(([type, nombre]) => (
            <li key={type}>
              <span>{type.replace(/_/g, " ")}</span>
              <strong title="Nombre de liaisons relevées ; une demie est partagée avec le local voisin">
                {nombre.toLocaleString("fr-FR")}
              </strong>
            </li>
          ))}
          <li><span>Liaison plancher</span><strong>{meters(sheet.liaison_plancher_m)}</strong></li>
        </ul>
      </section>

      {(sheet.a_completer ?? []).length > 0 && (
        <section><h2>À compléter</h2><ul>{sheet.a_completer?.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></section>
      )}
      {((sheet.alertes ?? []).length > 0 || room.demandes.length > 0) && (
        <section>
          <h2>Alertes et demandes</h2>
          <ul className="th-study-alerts">
            {sheet.alertes?.map((alert, index) => <li key={`${alert}-${index}`}>{alert}</li>)}
            {room.demandes.map((request, index) => <li key={`${request.objet}-${index}`}><strong>{request.objet}</strong> : {request.motif}</li>)}
          </ul>
        </section>
      )}
      {edition && <EditionSection room={room} edition={edition} />}
    </>
  );
}

export function StudyCoverageBanner({ coverage }: { coverage: Study["content"]["couverture"] | null | undefined }) {
  if (!coverage) {
    return null;
  }
  const complet = coverage.surface_non_affectee_m2 < 0.5 && coverage.chevauchement_m2 < 0.5;
  return (
    <div className={complet ? "th-study-coverage is-ok" : "th-study-coverage"}>
      <strong>{coverage.taux_couverture_pct.toLocaleString("fr-FR")} % de l'intérieur affecté</strong>
      {coverage.surface_non_affectee_m2 >= 0.5 && <span>{squareMeters(coverage.surface_non_affectee_m2)} sans local</span>}
      {coverage.chevauchement_m2 >= 0.5 && <span>{squareMeters(coverage.chevauchement_m2)} comptés deux fois</span>}
    </div>
  );
}

/** Ce que la chaîne a trouvé en se relisant : deux lectures du même niveau confrontées (D77). */
export function StudyCoherenceReport({ coherence }: { coherence: Study["content"]["coherence"] | null | undefined }) {
  const [ouvert, setOuvert] = useState(false);
  if (!coherence) {
    return null;
  }
  if (coherence.statut === "ok") {
    return (
      <p className="th-study-coherence is-ok">Contrôle de cohérence : les contours et le relevé concordent.</p>
    );
  }
  const anomalies = coherence.controles.filter((controle) => controle.anomalies.length > 0);
  return (
    <div className="th-study-coherence">
      <button type="button" className="th-link" onClick={() => setOuvert(!ouvert)}>
        Contrôle de cohérence : {coherence.anomalies} point{coherence.anomalies > 1 ? "s" : ""} à regarder
        <span aria-hidden="true">{ouvert ? " ▴" : " ▾"}</span>
      </button>
      {ouvert && (
        <dl>
          {anomalies.map((controle) => (
            <Fragment key={controle.code}>
              <dt>{controle.titre}</dt>
              {controle.anomalies.map((anomalie, rang) => (
                <dd key={`${controle.code}-${rang}`}>{anomalie.message}</dd>
              ))}
            </Fragment>
          ))}
        </dl>
      )}
    </div>
  );
}
