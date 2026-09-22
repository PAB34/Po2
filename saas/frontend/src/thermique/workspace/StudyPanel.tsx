import type { CSSProperties, KeyboardEvent, PointerEvent } from "react";

import type { Study, StudyRoom } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";
import { NATURE_COLORS, NATURE_LABELS, sortedStudyRooms } from "./study";

const meters = (value: number | undefined) => (value == null ? "—" : `${value.toLocaleString("fr-FR")} m`);
const squareMeters = (value: number | undefined) => (value == null ? "—" : `${value.toLocaleString("fr-FR")} m²`);

export function StudyOverlay({
  rooms,
  selectedId,
  toScreen,
  onSelect,
}: {
  rooms: StudyRoom[];
  selectedId: string | null;
  toScreen: ToScreen;
  onSelect: (id: string) => void;
}) {
  const stopPointer = (event: PointerEvent<SVGGElement>) => event.stopPropagation();
  const selectWithKeyboard = (event: KeyboardEvent<SVGGElement>, id: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(id);
    }
  };
  return (
    <>
      {rooms.map((room) => {
        const points = room.contour_pdf.map(toScreen).map(([x, y]) => `${x},${y}`).join(" ");
        const selected = room.id === selectedId;
        return (
          <g
            key={room.id}
            className={selected ? "th-study-room is-selected" : "th-study-room"}
            style={{ "--room-color": NATURE_COLORS[room.nature] } as CSSProperties}
            role="button"
            tabIndex={0}
            aria-label={`Ouvrir la fiche de ${room.nom}`}
            onPointerDown={stopPointer}
            onClick={(event) => {
              event.stopPropagation();
              onSelect(room.id);
            }}
            onKeyDown={(event) => selectWithKeyboard(event, room.id)}
          >
            <polygon points={points}>
              <title>{`${room.nom} · ${NATURE_LABELS[room.nature]} · ${squareMeters(room.surface_m2)}`}</title>
            </polygon>
          </g>
        );
      })}
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

export function StudyRoomPanel({ room, state }: { room: StudyRoom | null; state?: Study["local_states"][string] }) {
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
          {Object.entries(sheet.ponts ?? room.synthese.ponts ?? {}).map(([type, length]) => (
            <li key={type}><span>{type.replace(/_/g, " ")}</span><strong>{meters(length)}</strong></li>
          ))}
          <li><span>Liaison plancher</span><strong>{meters(sheet.liaison_plancher_m)}</strong></li>
        </ul>
      </section>

      {(sheet.a_completer ?? []).length > 0 && (
        <section><h2>À compléter</h2><ul>{sheet.a_completer?.map((item) => <li key={item}>{item}</li>)}</ul></section>
      )}
      {((sheet.alertes ?? []).length > 0 || room.demandes.length > 0) && (
        <section>
          <h2>Alertes et demandes</h2>
          <ul className="th-study-alerts">
            {sheet.alertes?.map((alert) => <li key={alert}>{alert}</li>)}
            {room.demandes.map((request, index) => <li key={`${request.objet}-${index}`}><strong>{request.objet}</strong> : {request.motif}</li>)}
          </ul>
        </section>
      )}
      <p className="th-muted">Lecture seule — les corrections et la remodélisation arrivent au lot E3.</p>
    </>
  );
}
