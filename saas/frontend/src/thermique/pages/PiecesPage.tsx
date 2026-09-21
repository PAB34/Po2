import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type PdfPoint } from "../api";
import { calquesApi } from "../calques";
import { TileSheetViewer, type ToScreen } from "../components/TileSheetViewer";
import { nearestEdge, nearestVertex, pdfTolerance } from "../metre";
import { ROOM_COLORS, insideRoom, piecesApi, type Room, type RoomClass, type SheetRooms } from "../pieces";
import { allSheets, projectQueryKey } from "../projectCache";
import { superpositionApi } from "../superposition";
import { ProjectTabs } from "./ProjectLibraryPage";

const RASTER_STALE_MS = 6 * 3600 * 1000;
const READING_POLL_MS = 4000;
const VERTEX_HIT_PX = 12;
const CLASS_ORDER: RoomClass[] = ["chauffe", "non_chauffe", "exterieur"];
const numberFormat = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });
const area = (value: number) => `${numberFormat.format(value)} m²`;

// Étape E3 : les pièces sont proposées d'après les calques désignés, nommées par lecture du plan et pré-classées ;
// le thermicien corrige (clic, fusion, découpe, nom, classe).
export function PiecesPage() {
  const { token } = useAuth();
  const projectId = Number(useParams().projectId);
  const queryClient = useQueryClient();
  const enabled = Boolean(token) && Number.isFinite(projectId);

  const [sheetId, setSheetId] = useState<number | null>(null);
  const [selection, setSelection] = useState<number[]>([]);
  const [pending, setPending] = useState<PdfPoint | null>(null);
  const [fermetureCm, setFermetureCm] = useState(40);
  const [nameDraft, setNameDraft] = useState("");
  const [cut, setCut] = useState<[PdfPoint, PdfPoint] | null>(null);
  const cutRef = useRef<[PdfPoint, PdfPoint] | null>(null);
  // correction du contour à la main (étape 2 du parcours) : sommets déplacés, ajoutés ou retirés
  const [draft, setDraft] = useState<PdfPoint[] | null>(null);
  const [redrawing, setRedrawing] = useState(false);
  const [creating, setCreating] = useState(false);
  const dragRef = useRef<number | null>(null);
  const pixelsPerPtRef = useRef(1);

  const projectQuery = useQuery({
    queryKey: projectQueryKey(projectId),
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled,
  });
  const plans = useQuery({
    queryKey: ["thermique", "superposition", projectId],
    queryFn: () => superpositionApi.overview(token!, projectId),
    enabled,
  });
  const sheets = projectQuery.data ? allSheets(projectQuery.data) : [];
  const currentSheetId = sheetId ?? plans.data?.planches[0]?.id ?? null;
  const sheet = sheets.find((item) => item.id === currentSheetId);
  const rotation = sheet?.rotation_deg ?? 0;
  const roomsKey = ["thermique", "pieces", currentSheetId ?? 0] as const;

  const raster = useQuery({
    queryKey: ["thermique", "raster", sheet?.id ?? 0, rotation],
    queryFn: () => thermiqueApi.getRaster(token!, sheet!.id, rotation),
    enabled: Boolean(token && sheet),
    staleTime: RASTER_STALE_MS,
  });
  const rooms = useQuery({
    queryKey: roomsKey,
    queryFn: () => piecesApi.list(token!, currentSheetId!),
    enabled: Boolean(token && currentSheetId),
    refetchInterval: (query) => (query.state.data?.lecture_noms === "en_cours" ? READING_POLL_MS : false),
  });
  const limits = useQuery({
    queryKey: ["thermique", "calques-designes", projectId, currentSheetId ?? 0],
    queryFn: () => calquesApi.designated(token!, currentSheetId!),
    enabled: Boolean(token && currentSheetId),
    staleTime: Infinity,
  });
  const data = rooms.data;
  const selected = data?.pieces.filter((room) => selection.includes(room.id)) ?? [];
  const single = selected.length === 1 ? selected[0] : null;

  useEffect(() => {
    setNameDraft(single?.nom ?? "");
  }, [single?.id, single?.nom]);

  function done(next: SheetRooms) {
    queryClient.setQueryData(roomsKey, next);
    setSelection((current) => current.filter((id) => next.pieces.some((room) => room.id === id)));
  }

  const detectMutation = useMutation({
    mutationFn: () => piecesApi.detect(token!, currentSheetId!, fermetureCm),
    onSuccess: (next) => {
      done(next);
      setSelection([]);
      setPending(null);
    },
  });
  const addMutation = useMutation({
    mutationFn: (point: PdfPoint) => piecesApi.add(token!, currentSheetId!, point, fermetureCm),
    onSuccess: (next) => {
      done(next);
      setPending(null);
      const added = next.pieces[next.pieces.length - 1];
      setSelection(added ? [added.id] : []);
    },
  });
  const traceMutation = useMutation({
    mutationFn: (contour: PdfPoint[]) => piecesApi.trace(token!, currentSheetId!, contour),
    onSuccess: (next) => {
      done(next);
      setDraft(null);
      setRedrawing(false);
      setCreating(false);
      const added = next.pieces[next.pieces.length - 1];
      setSelection(added ? [added.id] : []);
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { nom?: string; classe?: RoomClass; contour?: number[] } }) =>
      piecesApi.update(token!, id, payload),
    onSuccess: (next) => {
      done(next);
      setDraft(null);
      setRedrawing(false);
      setCreating(false);
    },
  });
  const components = useQuery({
    queryKey: ["thermique", "composants", single?.id ?? 0],
    queryFn: () => piecesApi.components(token!, single!.id),
    enabled: Boolean(token && single),
  });
  const natureMutation = useMutation({
    mutationFn: ({ signature, forme, nature }: { signature: string; forme: string; nature: string }) =>
      calquesApi.save(token!, projectId, { signature, forme, nature, perimetre: "partout" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["thermique", "composants"] });
      void queryClient.invalidateQueries({ queryKey: ["thermique", "calques-designes", projectId] });
      void queryClient.invalidateQueries({ queryKey: ["thermique", "calques", projectId] });
    },
  });
  const removeMutation = useMutation({ mutationFn: (id: number) => piecesApi.remove(token!, id), onSuccess: done });
  const mergeMutation = useMutation({
    mutationFn: (ids: number[]) => piecesApi.merge(token!, currentSheetId!, ids),
    onSuccess: (next) => {
      done(next);
      const merged = next.pieces[next.pieces.length - 1];
      setSelection(merged ? [merged.id] : []);
    },
  });
  const splitMutation = useMutation({
    mutationFn: ({ id, line }: { id: number; line: [PdfPoint, PdfPoint] }) => piecesApi.split(token!, id, line[0], line[1]),
    onSuccess: (next) => {
      done(next);
      setSelection([]);
    },
  });
  const mutations = [detectMutation, addMutation, traceMutation, updateMutation, removeMutation, mergeMutation, splitMutation];
  const busy = mutations.some((mutation) => mutation.isPending);
  const actionError = mutations.find((mutation) => mutation.error)?.error ?? null;

  function reset() {
    setSelection([]);
    setPending(null);
    setDraft(null);
    setRedrawing(false);
    setCreating(false);
    mutations.forEach((mutation) => mutation.reset());
  }

  function startTrace(firstPoint?: PdfPoint) {
    setSelection([]);
    setPending(null);
    addMutation.reset();
    setDraft(firstPoint ? [firstPoint] : []);
    setRedrawing(true);
    setCreating(true);
  }

  function cancelDraft() {
    setDraft(null);
    setRedrawing(false);
    setCreating(false);
  }

  function contourPoints(room: Room): PdfPoint[] {
    const out: PdfPoint[] = [];
    for (let k = 0; k + 1 < room.contour.length; k += 2) {
      out.push([room.contour[k], room.contour[k + 1]]);
    }
    return out;
  }

  function saveDraft() {
    if (creating && draft && draft.length >= 3) {
      traceMutation.mutate(draft);
    } else if (single && draft && draft.length >= 3) {
      updateMutation.mutate({ id: single.id, payload: { contour: draft.flat() } });
    }
  }

  function saveName(room: Room) {
    const name = nameDraft.trim();
    if (name !== room.nom) {
      updateMutation.mutate({ id: room.id, payload: { nom: name } });
    }
  }

  function renderOverlay(toScreen: ToScreen): ReactNode {
    const points = (coords: number[]) => {
      const out: string[] = [];
      for (let k = 0; k + 1 < coords.length; k += 2) {
        out.push(
          toScreen([coords[k], coords[k + 1]])
            .map((value) => value.toFixed(1))
            .join(","),
        );
      }
      return out.join(" ");
    };
    return (
      <>
        {limits.data && (
          <g className="th-sup-reference">
            {Object.values(limits.data.natures).map((group, index) => (
              <g key={index}>
                {group.traits.map((coords, k) => (
                  <polyline key={k} points={points(coords)} />
                ))}
              </g>
            ))}
          </g>
        )}
        {data?.pieces.map((room) => {
          const [cx, cy] = toScreen(room.centre);
          return (
            <g
              key={room.id}
              className={`th-room${selection.includes(room.id) ? " is-selected" : ""}`}
              style={{ "--room": ROOM_COLORS[room.classe] } as CSSProperties}
            >
              <polygon points={points(room.contour)} />
              <text x={cx} y={cy} textAnchor="middle">
                {room.nom || "?"}
              </text>
              <text x={cx} y={cy + 14} textAnchor="middle" className="th-room__area">
                {area(room.surface_m2)}
              </text>
            </g>
          );
        })}
        {draft && (
          <g className="th-room-draft">
            <polygon points={points(draft.flat())} />
            {draft.map((point, index) => {
              const [x, y] = toScreen(point);
              return <circle key={index} cx={x} cy={y} r={5} />;
            })}
          </g>
        )}
        {pending &&
          (() => {
            const [x, y] = toScreen(pending);
            return <circle className="th-room-pending" cx={x} cy={y} r={6} />;
          })()}
        {cut && <polyline className="th-room-cut" points={points([...cut[0], ...cut[1]])} />}
      </>
    );
  }

  return (
    <div className="th-viewer-layout">
      {sheet && raster.data ? (
        <TileSheetViewer
          manifest={raster.data}
          tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
          tool="pieces"
          onHover={(_point, scale) => {
            pixelsPerPtRef.current = scale;
          }}
          onAddPoint={(point, event) => {
            if (draft) {
              if (redrawing) {
                setDraft([...draft, point]);
                return;
              }
              // en correction : Alt + clic retire un sommet, un clic sur un côté en ajoute un
              const tolerance = pdfTolerance(VERTEX_HIT_PX, pixelsPerPtRef.current);
              const vertex = nearestVertex(draft, point, tolerance);
              if (vertex !== null) {
                if (event.altKey && draft.length > 3) {
                  setDraft(draft.filter((_, index) => index !== vertex));
                }
                return;
              }
              const edge = nearestEdge(draft, point, tolerance);
              if (edge) {
                setDraft([...draft.slice(0, edge.index + 1), edge.point, ...draft.slice(edge.index + 1)]);
              }
              return;
            }
            const room = data?.pieces.find((item) => insideRoom(point, item.contour));
            if (!room) {
              // Sans limite connue, le premier clic démarre le tracé manuel au lieu d'imposer un passage par Calques.
              if (!data?.limites.elements) {
                startTrace(point);
                return;
              }
              // Avec des limites connues, un clic dans un espace libre tente une proposition automatique.
              setSelection([]);
              setPending(point);
              addMutation.reset();
              addMutation.mutate(point);
              return;
            }
            setPending(null);
            setSelection((current) =>
              event.shiftKey
                ? current.includes(room.id)
                  ? current.filter((id) => id !== room.id)
                  : [...current, room.id]
                : [room.id],
            );
          }}
          onGrab={(point, scale, event) => {
            if (draft) {
              const vertex = nearestVertex(draft, point, pdfTolerance(VERTEX_HIT_PX, scale));
              dragRef.current = vertex;
              return vertex !== null;
            }
            if (!event.altKey || !single) {
              return false;
            }
            cutRef.current = [point, point];
            setCut(cutRef.current);
            return true;
          }}
          onGrabMove={(point) => {
            if (dragRef.current !== null) {
              setDraft((current) => (current ? current.map((p, index) => (index === dragRef.current ? point : p)) : current));
              return;
            }
            if (cutRef.current) {
              cutRef.current = [cutRef.current[0], point];
              setCut(cutRef.current);
            }
          }}
          onGrabEnd={() => {
            if (dragRef.current !== null) {
              dragRef.current = null;
              return;
            }
            const line = cutRef.current;
            cutRef.current = null;
            setCut(null);
            if (line && single && Math.hypot(line[1][0] - line[0][0], line[1][1] - line[0][1]) > 2) {
              splitMutation.mutate({ id: single.id, line });
            }
          }}
          renderOverlay={renderOverlay}
        />
      ) : (
        <div className="th-viewer th-viewer--empty">
          <p className="th-viewer__status">
            {raster.error ? `Affichage impossible : ${raster.error.message}` : sheet ? "Préparation de la planche…" : "Aucune planche de plan à afficher."}
          </p>
        </div>
      )}

      <aside className="th-panel">
        <div>
          <p className="po2-eyebrow">
            <Link to="/">Projets</Link> · <Link to={`/projets/${projectId}`}>{projectQuery.data?.name ?? "Projet"}</Link>
          </p>
          <h1 className="th-panel__title">Pièces</h1>
        </div>
        <ProjectTabs projectId={projectId} />
        <p className="th-muted">
          Définissez d'abord les pièces, par détection assistée ou en cliquant leurs angles. Cliquez ensuite une pièce pour la nommer,
          la classer et identifier tous les composants qui longent son contour ;{" "}
          <strong>Maj + clic</strong> pour en choisir plusieurs (fusion) ; <strong>Alt + glisser</strong> sur une pièce choisie pour la couper ;
          un clic hors des pièces propose d'en ajouter une quand des limites sont déjà connues.
        </p>

        {plans.data && plans.data.planches.length > 0 && (
          <label className="th-field">
            <span>Plan affiché</span>
            <select
              value={currentSheetId ?? ""}
              onChange={(event) => {
                setSheetId(Number(event.target.value));
                reset();
              }}
            >
              {plans.data.planches.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.libelle}
                </option>
              ))}
            </select>
          </label>
        )}

        {actionError && <p className="th-alert th-alert--error">{actionError.message}</p>}
        {rooms.error && <p className="th-alert th-alert--error">{rooms.error.message}</p>}

        {data && (
          <section className="th-edgebox th-calque-panel">
            <strong>Créer les pièces</strong>
            <span className="th-muted">
              Le tracé par points fonctionne immédiatement, sans identifier les portes ni les menuiseries. La détection automatique est une aide
              optionnelle fondée sur les {data.limites.elements} limites déjà connues.
            </span>
            <label className="th-field">
              <span>Tolérance de la détection automatique (cm)</span>
              <input
                type="number"
                min={0}
                max={300}
                step={10}
                value={fermetureCm}
                onChange={(event) => setFermetureCm(Math.max(0, Math.min(300, Number(event.target.value) || 0)))}
              />
            </label>
            <div className="th-inline">
              <button type="button" className="po2-button po2-button--primary" disabled={busy} onClick={() => startTrace()}>
                Tracer une pièce
              </button>
              <button
                type="button"
                className="po2-button po2-button--ghost"
                disabled={busy || data.limites.elements === 0}
                onClick={() => detectMutation.mutate()}
              >
                {data.pieces.length ? "Relancer la détection assistée" : "Détection assistée"}
              </button>
            </div>
            {data.pieces.length > 0 && (
              <small className="th-muted">La relance remplace les pièces détectées ; celles ajoutées, fusionnées ou coupées à la main restent.</small>
            )}
            {data.lecture_noms === "en_cours" && <span className="th-muted">Lecture des noms sur le plan… (environ une minute)</span>}
          </section>
        )}

        {pending && addMutation.isPending && (
          <section className="th-edgebox th-calque-panel">
            <strong>Tracé du contour…</strong>
          </section>
        )}
        {pending && addMutation.error && (
          <section className="th-edgebox th-calque-panel">
            <strong>Pas de contour ici</strong>
            <span className="th-alert th-alert--error">{addMutation.error.message}</span>
            <span className="th-muted">
              La pièce peut être définie tout de suite en cliquant ses angles ; les composants de bord seront identifiés ensuite.
            </span>
            <div className="th-inline">
              <button type="button" className="po2-button po2-button--primary" onClick={() => startTrace(pending)}>
                Tracer depuis ce point
              </button>
              <button type="button" className="po2-button po2-button--ghost" onClick={() => { setPending(null); addMutation.reset(); }}>
                Fermer
              </button>
            </div>
          </section>
        )}

        {creating && draft && (
          <section className="th-edgebox th-calque-panel">
            <strong>Nouvelle pièce</strong>
            <span className="th-muted">
              Cliquez successivement les angles réels de la pièce. Le dernier point sera relié au premier. {draft.length} sommets.
            </span>
            <div className="th-inline">
              <button type="button" className="po2-button po2-button--primary" disabled={busy || draft.length < 3} onClick={saveDraft}>
                Créer la pièce
              </button>
              {draft.length > 0 && (
                <button type="button" className="po2-button po2-button--ghost" onClick={() => setDraft(draft.slice(0, -1))}>
                  Annuler le dernier point
                </button>
              )}
              <button type="button" className="po2-button po2-button--ghost" onClick={cancelDraft}>
                Annuler
              </button>
            </div>
          </section>
        )}

        {single && !creating && (
          <section className="th-edgebox th-calque-panel">
            <strong>
              {area(single.surface_m2)}
              {single.repere ? ` · repère ${single.repere}` : ""}
            </strong>
            <label className="th-field">
              <span>Nom {single.nom_source === "lu" ? "(lu sur le plan)" : ""}</span>
              <input
                value={nameDraft}
                maxLength={120}
                placeholder="Nom de la pièce"
                onChange={(event) => setNameDraft(event.target.value)}
                onBlur={() => saveName(single)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    saveName(single);
                  }
                }}
              />
            </label>
            <div className="th-segmented" role="group" aria-label="Classement thermique">
              {CLASS_ORDER.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={single.classe === key ? "is-active" : ""}
                  aria-pressed={single.classe === key}
                  disabled={busy}
                  onClick={() => updateMutation.mutate({ id: single.id, payload: { classe: key } })}
                >
                  {data?.classes[key]}
                </button>
              ))}
            </div>
            {single.classe_source === "propose" && <small className="th-muted">Classement proposé d'après le nom.</small>}

            {draft ? (
              <>
                <span className="th-muted">
                  {redrawing
                    ? "Cliquez successivement les angles réels de la pièce sur le plan. Le dernier point sera relié au premier."
                    : "Glissez un sommet pour le déplacer, cliquez sur un côté pour en ajouter un, Alt + clic sur un sommet pour le retirer."}
                  {` ${draft.length} sommets.`}
                </span>
                <div className="th-inline">
                  <button type="button" className="po2-button po2-button--primary" disabled={busy || draft.length < 3} onClick={saveDraft}>
                    Enregistrer le contour
                  </button>
                  {redrawing && draft.length > 0 && (
                    <button type="button" className="po2-button po2-button--ghost" onClick={() => setDraft(draft.slice(0, -1))}>
                      Annuler le dernier point
                    </button>
                  )}
                  <button type="button" className="po2-button po2-button--ghost" onClick={() => { setDraft(null); setRedrawing(false); }}>
                    Annuler
                  </button>
                </div>
              </>
            ) : (
              <>
                {single.contour.length / 2 > 12 && (
                  <span className="th-alert th-alert--warn">
                    Ce contour comporte {single.contour.length / 2} sommets : un retracé rapide est conseillé.
                  </span>
                )}
                <div className="th-inline">
                  <button type="button" className="th-link" disabled={busy} onClick={() => { setDraft(contourPoints(single)); setRedrawing(false); }}>
                    Ajuster les sommets
                  </button>
                  <button type="button" className="th-link" disabled={busy} onClick={() => { setDraft([]); setRedrawing(true); }}>
                    Retracer par points
                  </button>
                </div>
              </>
            )}
            <button type="button" className="th-link th-link--danger" disabled={busy} onClick={() => removeMutation.mutate(single.id)}>
              Supprimer la pièce
            </button>
          </section>
        )}

        {single && !draft && (
          <section className="th-edgebox th-calque-panel">
            <strong>Ce qui borde ce local</strong>
            {components.isPending && <span className="th-muted">Relevé en cours…</span>}
            {components.error && <span className="th-alert th-alert--error">{components.error.message}</span>}
            {components.data && (
              <>
                <span className="th-muted">
                  {components.data.cotes.length} côtés, {numberFormat.format(components.data.cotes.reduce((total, value) => total + value, 0))} m de
                  périmètre. Nommez chaque famille une fois : la réponse vaut pour tous ses exemplaires du projet.
                </span>
                <ul className="th-calque-list">
                  {components.data.familles.map((famille) => (
                    <li key={`${famille.signature}|${famille.forme}`}>
                      <div className="th-calque-line">
                        <span>
                          <strong>{numberFormat.format(famille.longueur_m)} m</strong> · {famille.libelle} · {famille.forme_libelle}
                        </span>
                        <span className="th-muted">
                          {famille.nombre} trait{famille.nombre > 1 ? "s" : ""} · {famille.cotes.length} côté
                          {famille.cotes.length > 1 ? "s" : ""}
                        </span>
                      </div>
                      {famille.nature ? (
                        <span className="th-badge">{famille.nature_libelle}</span>
                      ) : (
                        <select
                          className="th-select"
                          value=""
                          disabled={natureMutation.isPending}
                          onChange={(event) =>
                            event.target.value &&
                            natureMutation.mutate({ signature: famille.signature, forme: famille.forme, nature: event.target.value })
                          }
                        >
                          <option value="">À identifier…</option>
                          {Object.entries(components.data!.natures).map(([key, label]) => (
                            <option key={key} value={key}>
                              {label}
                            </option>
                          ))}
                        </select>
                      )}
                    </li>
                  ))}
                </ul>
                {components.data.familles.length === 0 && <span className="th-muted">Rien ne borde ce contour.</span>}
                {natureMutation.error && <span className="th-alert th-alert--error">{natureMutation.error.message}</span>}
              </>
            )}
          </section>
        )}

        {selected.length > 1 && (
          <section className="th-edgebox th-calque-panel">
            <strong>{selected.length} pièces choisies</strong>
            <div className="th-inline">
              <button type="button" className="po2-button po2-button--primary" disabled={busy} onClick={() => mergeMutation.mutate(selection)}>
                Fusionner
              </button>
              <button type="button" className="po2-button po2-button--ghost" onClick={() => setSelection([])}>
                Annuler
              </button>
            </div>
          </section>
        )}

        {data && data.pieces.length > 0 && (
          <section>
            <h2>Pièces du plan</h2>
            <p className="th-muted">
              {CLASS_ORDER.map((key) => `${data.classes[key]} : ${area(data.totaux[key] ?? 0)}`).join(" · ")}
            </p>
            <ul className="th-sup-list">
              {data.pieces.map((room) => (
                <li key={room.id}>
                  <button
                    type="button"
                    className={`th-sup-item${selection.includes(room.id) ? " is-selected" : ""}`}
                    onClick={() => {
                      setPending(null);
                      setSelection([room.id]);
                    }}
                  >
                    <span>
                      <span className="th-calque-dot" style={{ background: ROOM_COLORS[room.classe] }} /> {room.nom || "Sans nom"}
                    </span>
                    <span className="th-sup-state is-ok">{area(room.surface_m2)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}
      </aside>
    </div>
  );
}
