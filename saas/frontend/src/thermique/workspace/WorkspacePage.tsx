import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type PdfPoint, type ProjectDetail, type Sheet, type Study } from "../api";
import { TileSheetViewer, type ViewerTool, type ViewerView } from "../components/TileSheetViewer";
import { STATUS_LABELS } from "../natures";
import { allSheets, projectQueryKey, projectsQueryKey } from "../projectCache";
import { DocumentsPanel } from "./DocumentsPanel";
import { InfoPanel } from "./InfoPanel";
import { groupSheets, referenceSheet, sheetTitle } from "./levels";
import { LibraryPanel } from "./LibraryPanel";
import { SheetPanel, sheetSegments } from "./SheetPanel";
import { NorthOverlay } from "./NorthOverlay";
import { PlanMenu, type PlanAction } from "./PlanMenu";
import { METRICS_DEFAUT, StudyMetrics, type MetricsShow } from "./StudyMetrics";
import { StudyCoherenceReport, StudyCoverageBanner, StudyOverlay, StudyRoomCreationPanel, StudyRoomList, StudyRoomPanel } from "./StudyPanel";
import { ElementPanel } from "./ElementPanel";
import { PontsPanel } from "./PontsPanel";
import { pontDeElement, trouverElement, viserSurLePlan } from "./elements";
import { etapeCourante, parcours, type EtapeId } from "./parcours";
import { useStudyEdition } from "./useStudyEdition";
import { useStudyElements } from "./useStudyElements";
import { cibleEditable } from "./elementsHistory";
import { NATURE_LABELS, otherLocalNatures, roomAt, studyQueryKey } from "./study";

type Panel = "planche" | "fiche" | "documents" | "bibliotheque" | "infos";

const PANELS: { id: Panel; label: string }[] = [
  { id: "planche", label: "Planche" },
  { id: "fiche", label: "Fiche" },
  { id: "documents", label: "Documents" },
  { id: "bibliotheque", label: "Bibliothèque" },
  { id: "infos", label: "Infos" },
];

// Les adresses de tuiles signées valent 12 h : on redemande la fiche avant.
const RASTER_STALE_MS = 6 * 3600 * 1000;

// Ancienne persistance locale du plan de référence : E2 la migre une fois vers le projet côté serveur.
const referenceKey = (projectId: number) => `thermique.reference.${projectId}`;

function readReference(projectId: number): number | null {
  try {
    const value = window.localStorage.getItem(referenceKey(projectId));
    return value ? Number(value) : null;
  } catch {
    return null;
  }
}

function writeReference(projectId: number, sheetId: number) {
  try {
    window.localStorage.setItem(referenceKey(projectId), String(sheetId));
  } catch {
    // stockage indisponible : le choix vaut pour la session en cours
  }
}

function removeReference(projectId: number) {
  try {
    window.localStorage.removeItem(referenceKey(projectId));
  } catch {
    // stockage indisponible
  }
}

// Affichage des métrés : mémorisé par planche, pour ne pas le reposer à chaque local (Q6).
const metricsKey = (sheetId: number) => `thermique.metres.${sheetId}`;
// Rayon de saisie d'un élément d'enveloppe, en pixels d'écran : un trait fin doit rester attrapable.
const PRISE_ELEMENT_PX = 6;
// La pastille d'un pont fait 5 px de rayon : on vise un peu plus large pour l'attraper sans peine.
const PRISE_PONT_PX = 8;
// Serrage du plan sur le pont en cours, en multiple du cadrage ajusté : de quoi voir le coin et ses
// voisins, sans perdre le bâtiment de vue (Q4).
const ZOOM_PONT = 5;

function readMetrics(sheetId: number | null): MetricsShow {
  if (sheetId == null) {
    return METRICS_DEFAUT;
  }
  try {
    const brut = window.localStorage.getItem(metricsKey(sheetId));
    return brut ? { ...METRICS_DEFAUT, ...(JSON.parse(brut) as Partial<MetricsShow>) } : METRICS_DEFAUT;
  } catch {
    return METRICS_DEFAUT;
  }
}

function writeMetrics(sheetId: number, show: MetricsShow) {
  try {
    window.localStorage.setItem(metricsKey(sheetId), JSON.stringify(show));
  } catch {
    // stockage indisponible : le choix vaut pour la session en cours
  }
}

const METRICS_CASES: { cle: keyof MetricsShow; label: string; titre: string }[] = [
  { cle: "metres", label: "Métrés", titre: "Coter tous les locaux du niveau, pas seulement celui sélectionné" },
  { cle: "ponts", label: "Ponts", titre: "Montrer les ponts thermiques de tout le niveau" },
  { cle: "elements", label: "Éléments", titre: "Montrer les éléments d'enveloppe relevés sur tout le niveau" },
  { cle: "toutesCotes", label: "Côtés intérieurs", titre: "Coter aussi les côtés qui ne déperdent pas" },
];

function SheetMenu({ label, sheets, currentId, onPick }: { label: string; sheets: Sheet[]; currentId: number | null; onPick: (id: number) => void }) {
  if (sheets.length === 0) {
    return null;
  }
  const current = sheets.find((sheet) => sheet.id === currentId);
  return (
    <select
      className={current ? "th-ws__menu is-active" : "th-ws__menu"}
      aria-label={label}
      value={current ? current.id : ""}
      onChange={(event) => event.target.value && onPick(Number(event.target.value))}
    >
      <option value="">
        {label} ({sheets.length})
      </option>
      {sheets.map((sheet) => (
        <option key={sheet.id} value={sheet.id}>
          {sheetTitle(sheet)}
        </option>
      ))}
    </select>
  );
}

// Espace de travail du thermicien (D47) : un projet, ses plans, sa bibliothèque et ses infos, sans quitter l'écran.
export function WorkspacePage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const projectId = Number(useParams().projectId);
  const [searchParams, setSearchParams] = useSearchParams();
  const [referenceId, setReferenceId] = useState<number | null>(() => readReference(projectId));
  const [tool, setTool] = useState<ViewerTool>("pan");
  const [points, setPoints] = useState<PdfPoint[]>([]);
  const views = useRef(new Map<string, ViewerView>());
  const referenceMigration = useRef<number | null>(null);
  const [metrics, setMetrics] = useState<MetricsShow>(METRICS_DEFAUT);
  const [menu, setMenu] = useState<{ x: number; y: number; actions: PlanAction[] } | null>(null);
  // Dès que le thermicien touche une case d'affichage, l'étape rend la main : c'est lui qui décide (Q6).
  const [calquesLibres, setCalquesLibres] = useState(false);
  // Niveau qu'on cherche à quitter alors que des corrections attendent (D111) : pas de départ silencieux.
  const [departEnAttente, setDepartEnAttente] = useState<number | null>(null);

  const { data: project, error } = useQuery({
    queryKey: projectQueryKey(projectId),
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled: Boolean(token) && Number.isFinite(projectId),
  });
  const { data: projects } = useQuery({
    queryKey: projectsQueryKey,
    queryFn: () => thermiqueApi.listProjects(token!),
    enabled: Boolean(token),
  });

  const sheets = project ? allSheets(project) : [];
  const groups = groupSheets(sheets);
  const reference = referenceSheet(sheets, project?.reference_sheet_id ?? referenceId);
  const requestedId = Number(searchParams.get("planche")) || null;
  const sheet = sheets.find((item) => item.id === requestedId) ?? reference;
  const panel = (PANELS.find((item) => item.id === searchParams.get("panneau"))?.id ?? (sheets.length ? "planche" : "documents")) as Panel;

  const setParams = useCallback(
    (changes: { planche?: number; panneau?: Panel; local?: string | null; etape?: EtapeId }) => {
      const next = new URLSearchParams(searchParams);
      if (changes.planche !== undefined) {
        next.set("planche", String(changes.planche));
      }
      if (changes.panneau !== undefined) {
        next.set("panneau", changes.panneau);
      }
      if (changes.etape !== undefined) {
        next.set("etape", changes.etape);
      }
      if (changes.local !== undefined) {
        if (changes.local === null) next.delete("local");
        else next.set("local", changes.local);
      }
      setSearchParams(next);
    },
    [searchParams, setSearchParams],
  );

  const sheetId = sheet?.id ?? null;
  useEffect(() => {
    setPoints([]);
  }, [sheetId, tool]);

  // Les réglages d'affichage suivent la planche : on reprend ceux qu'elle avait à la dernière visite.
  useEffect(() => {
    setMetrics(readMetrics(sheetId));
  }, [sheetId]);

  const basculerMetrique = useCallback(
    (cle: keyof MetricsShow, depart: MetricsShow) => {
      setCalquesLibres(true);
      setMetrics(() => {
        const suivant = { ...depart, [cle]: !depart[cle] };
        if (sheetId != null) {
          writeMetrics(sheetId, suivant);
        }
        return suivant;
      });
    },
    [sheetId],
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPoints([]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const rotation = sheet?.rotation_deg ?? 0;
  const raster = useQuery({
    queryKey: ["thermique", "raster", sheetId, rotation],
    queryFn: () => thermiqueApi.getRaster(token!, sheetId!, rotation),
    enabled: Boolean(token && sheetId),
    staleTime: RASTER_STALE_MS,
  });
  const viewKey = `${sheetId}|${rotation}`;
  const studyQuery = useQuery({
    queryKey: studyQueryKey(sheetId),
    queryFn: () => thermiqueApi.getStudy(token!, sheetId!),
    enabled: Boolean(token && sheetId),
  });
  const study = studyQuery.data;
  const selectedLocalId = searchParams.get("local");
  const selectRoom = useCallback((id: string) => setParams({ local: id, panneau: "fiche" }), [setParams]);
  // Les corrections d'éléments s'appliquent d'abord : l'édition des contours travaille ensuite sur
  // l'étude qu'elles montrent, pour que les deux aperçus ne se contredisent jamais.
  const elementsState = useStudyElements({ token: token ?? null, sheetId, study: study ?? undefined });
  const natureBlockedReason =
    elementsState.pending > 0
      ? "Enregistrez ou abandonnez d'abord les corrections d'éléments en attente."
      : null;
  const editionState = useStudyEdition({
    token: token ?? null,
    sheetId,
    study: elementsState.shown,
    selectedRoom: study?.content.locaux.find((room) => room.id === selectedLocalId) ?? null,
    onSelectRoom: selectRoom,
    natureBlockedReason,
  });

  useEffect(() => {
    const gererHistorique = (event: KeyboardEvent) => {
      if (editionState.draft || cibleEditable(event.target)) return;
      const modificateur = event.ctrlKey || event.metaKey;
      if (!modificateur) return;
      const touche = event.key.toLowerCase();
      const retablir = (touche === "z" && event.shiftKey) || touche === "y";
      const annuler = touche === "z" && !event.shiftKey;
      if ((!annuler && !retablir) || (annuler && !elementsState.canUndo) || (retablir && !elementsState.canRedo)) {
        return;
      }
      event.preventDefault();
      if (retablir) elementsState.redo();
      else elementsState.undo();
    };
    window.addEventListener("keydown", gererHistorique, true);
    return () => window.removeEventListener("keydown", gererHistorique, true);
  }, [editionState.draft, elementsState.canRedo, elementsState.canUndo, elementsState.redo, elementsState.undo]);
  // Tant qu'un aperçu n'est pas enregistré, c'est lui qui est affiché sur le plan et dans la fiche.
  const shownStudy = editionState.shown;
  const selectedRoom = shownStudy?.content.locaux.find((room) => room.id === selectedLocalId) ?? null;

  // Le parcours (F2, D106) : il se déduit de l'étude, et c'est lui qui règle le panneau et les calques.
  const etapes = parcours(sheet ?? null, shownStudy);
  const demandee = searchParams.get("etape");
  const etape = (etapes.find((item) => item.id === demandee)?.id ?? etapeCourante(etapes)) as EtapeId;
  const etapeActive = etapes.find((item) => item.id === etape) ?? etapes[0];
  // Les calques de l'étape s'appliquent jusqu'à ce qu'une case soit touchée ; la mention le dit (Q6).
  const calquesPilotes = !calquesLibres && etapeActive.calques !== null;
  const metricsAffiches = calquesPilotes ? (etapeActive.calques as MetricsShow) : metrics;

  const allerEtape = (cible: EtapeId) => {
    const trouvee = etapes.find((item) => item.id === cible);
    setCalquesLibres(false);
    elementsState.select(null);
    setParams({ etape: cible, panneau: trouvee?.panneau ?? "fiche" });
  };

  // Le pont en cours amène le plan à lui : l'étape sert à les distinguer un à un (Q4).
  const elementCourant = shownStudy ? trouverElement(shownStudy.content, elementsState.selected) : null;
  const pontCourant =
    etape === "ponts" && shownStudy && elementCourant ? pontDeElement(shownStudy.content, elementCourant) : null;
  const focusPlan = pontCourant?.point_pdf
    ? { point: pontCourant.point_pdf, cle: `${pontCourant.troncon}|${pontCourant.abscisse_m}`, zoom: ZOOM_PONT }
    : null;

  useEffect(() => {
    if (!project || !token || referenceMigration.current === project.id) return;
    referenceMigration.current = project.id;
    if (project.reference_sheet_id !== null) {
      setReferenceId(project.reference_sheet_id);
      removeReference(project.id);
      return;
    }
    const stored = readReference(project.id);
    if (stored !== null && allSheets(project).some((item) => item.id === stored)) {
      setReferenceId(stored);
      void thermiqueApi.updateProject(token, project.id, { reference_sheet_id: stored }).then(() => {
        removeReference(project.id);
        void queryClient.invalidateQueries({ queryKey: projectQueryKey(project.id) });
        void queryClient.invalidateQueries({ queryKey: projectsQueryKey });
      });
    } else {
      setReferenceId(null);
    }
  }, [project, queryClient, token]);

  useEffect(() => {
    if (selectedLocalId && study !== undefined && !study?.content.locaux.some((room) => room.id === selectedLocalId)) {
      setParams({ local: null, panneau: panel === "fiche" ? "planche" : panel });
    }
  }, [panel, selectedLocalId, setParams, study]);

  if (error) {
    return <p className="th-alert th-alert--error th-main">{error.message}</p>;
  }
  if (!project || !token) {
    return <p className="th-muted th-main">Chargement du projet…</p>;
  }

  const makeReference = async (id: number) => {
    writeReference(project.id, id);
    setReferenceId(id);
    try {
      await thermiqueApi.updateProject(token, project.id, { reference_sheet_id: id });
      removeReference(project.id);
      queryClient.setQueryData<ProjectDetail>(projectQueryKey(project.id), (current) =>
        current ? { ...current, reference_sheet_id: id } : current,
      );
      void queryClient.invalidateQueries({ queryKey: projectsQueryKey });
    } catch {
      // Le choix reste dans le navigateur et sera migré à la prochaine ouverture.
    }
  };
  const levelTitle = sheet ? sheetTitle(sheet) : "";
  const changerDeNiveau = (id: number) => {
    editionState.reset();
    elementsState.select(null);
    setCalquesLibres(false);
    setParams({ planche: id, local: null, panneau: panel === "fiche" ? "planche" : panel });
  };
  const selectSheet = (id: number) => {
    // Des corrections en attente disparaîtraient sans un mot : on demande d'abord (D111).
    if (elementsState.pending > 0 && id !== sheetId) {
      setDepartEnAttente(id);
      return;
    }
    changerDeNiveau(id);
  };

  return (
    <div className="th-ws">
      <div className="th-ws__bar">
        <select
          className="th-ws__project"
          aria-label="Projet"
          value={project.id}
          onChange={(event) => navigate(`/projets/${event.target.value}`)}
        >
          {(projects ?? [project]).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <nav className="th-ws__levels" aria-label="Niveaux">
          {groups.levels.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={item.id === sheetId}
              className={item.id === sheetId ? "is-active" : undefined}
              onClick={() => selectSheet(item.id)}
              title={item.label}
            >
              {sheetTitle(item)}
              {item.id === reference?.id && <span className="th-ws__ref" aria-label="plan de référence"> ★</span>}
            </button>
          ))}
          {groups.levels.length === 0 && sheets.length > 0 && <span className="th-muted">Aucune planche classée en plan</span>}
        </nav>
        <SheetMenu label="Coupes" sheets={groups.sections} currentId={sheetId} onPick={selectSheet} />
        <SheetMenu label="Façades" sheets={groups.elevations} currentId={sheetId} onPick={selectSheet} />
        <SheetMenu label="Autres" sheets={groups.others} currentId={sheetId} onPick={selectSheet} />
        <div className="th-ws__tabs" role="tablist" aria-label="Panneau">
          {PANELS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={panel === item.id}
              className={panel === item.id ? "is-active" : undefined}
              onClick={() => setParams({ panneau: item.id })}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className={`th-ws__body th-ws__body--${panel}`}>
        <aside className="th-ws__side" aria-label="Étude du niveau">
          <section>
            <h2>Étude {levelTitle ? `· ${levelTitle}` : ""}</h2>
            {/* D106 : le parcours pilote. Cliquer une étape change le panneau de droite et les calques
                du plan. Rien n'est verrouillé : une étape en retard ne barre pas la suivante (D109). */}
            <ol className="th-ws-steps">
              {etapes.map((item) => (
                <li
                  key={item.id}
                  className={`th-ws-step--${item.etat}${item.id === etape ? " is-current" : ""}`}
                  aria-current={item.id === etape ? "step" : undefined}
                >
                  <button type="button" onClick={() => allerEtape(item.id)}>
                    {item.titre}
                  </button>
                  <small>
                    {item.id === "planche" && sheet ? `${STATUS_LABELS[sheet.status]} · ` : ""}
                    {item.reste}
                  </small>
                </li>
              ))}
            </ol>
            {/* D111 : pas de départ silencieux. On ne change pas de niveau sans le dire. */}
            {departEnAttente !== null && (
              <div className="th-alert th-alert--warn th-ws-depart">
                <p>
                  {elementsState.pending} correction{elementsState.pending > 1 ? "s" : ""} ne sont pas
                  encore enregistrée{elementsState.pending > 1 ? "s" : ""} sur ce niveau.
                </p>
                <div className="th-inline">
                  <button
                    type="button"
                    className="po2-button po2-button--primary"
                    disabled={elementsState.busy}
                    onClick={() => {
                      const cible = departEnAttente;
                      elementsState.save();
                      setDepartEnAttente(null);
                      if (cible !== null) changerDeNiveau(cible);
                    }}
                  >
                    Enregistrer puis changer de niveau
                  </button>
                  <button
                    type="button"
                    className="po2-button po2-button--ghost"
                    onClick={() => {
                      const cible = departEnAttente;
                      elementsState.cancel();
                      setDepartEnAttente(null);
                      if (cible !== null) changerDeNiveau(cible);
                    }}
                  >
                    Abandonner les corrections
                  </button>
                  <button type="button" className="th-link" onClick={() => setDepartEnAttente(null)}>
                    Rester ici
                  </button>
                </div>
              </div>
            )}
          </section>
          <section>
            <h2>Locaux</h2>
            <StudyCoverageBanner coverage={shownStudy?.content.couverture ?? null} />
            <StudyCoherenceReport coherence={shownStudy?.content.coherence ?? null} />
            {shownStudy ? (
              <StudyRoomList study={shownStudy} selectedId={selectedRoom?.id ?? null} onSelect={selectRoom} />
            ) : (
              <p className="th-muted">Les locaux du niveau, chauffés d'abord, apparaîtront ici une fois l'étude importée.</p>
            )}
          </section>
        </aside>

        <div className="th-ws__plan">
          {!sheet ? (
            <div className="th-viewer th-viewer--empty">
              <p className="th-viewer__status">Déposez les plans du projet dans le panneau « Documents » pour commencer.</p>
            </div>
          ) : raster.data ? (
            <TileSheetViewer
              key={viewKey}
              manifest={raster.data}
              tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
              tool={editionState.draft ? "edition" : tool}
              points={points}
              segments={editionState.draft ? [] : sheetSegments(sheet, tool, points)}
              onAddPoint={(point) => {
                if (editionState.handlers.onAddPoint(point)) return;
                setPoints((current) => (current.length >= 2 ? [point] : [...current, point]));
              }}
              onPick={(point, pixelsPerPt) => {
                // Dans le local ouvert, un clic sur un élément d'enveloppe l'attrape en priorité : c'est
                // le geste de l'étape 5. Le reste du temps, le clic ouvre ou referme un local.
                if (shownStudy) {
                  // On cherche l'élément dans tout le niveau, et non dans le seul local ouvert : un mur
                  // est en dehors du contour de son local, donc introuvable autrement. Le pont passe en
                  // premier, sinon le mur qui le porte l'emporterait toujours.
                  const vise = viserSurLePlan(shownStudy.content, shownStudy.content.locaux, point, {
                    element: PRISE_ELEMENT_PX / pixelsPerPt,
                    pont: PRISE_PONT_PX / pixelsPerPt,
                  });
                  if (vise) {
                    elementsState.select(vise.ref);
                    setParams({ local: vise.room?.id ?? selectedLocalId, panneau: "fiche" });
                    return;
                  }
                }
                const room = shownStudy ? roomAt(shownStudy.content.locaux, point) : null;
                if (room) {
                  if (room.id !== selectedRoom?.id) {
                    elementsState.select(null);
                  }
                  selectRoom(room.id);
                } else if (selectedLocalId) {
                  elementsState.select(null);
                  setParams({ local: null, panneau: panel === "fiche" ? "planche" : panel });
                }
              }}
              onContextPick={(point, pixelsPerPt, ecran) => {
                // Clic droit : les gestes du contour en cours d'édition, sinon ceux du local visé.
                const actions: PlanAction[] = editionState.draft
                  ? editionState.contextActions(point, pixelsPerPt)
                  : (() => {
                      const room = shownStudy ? roomAt(shownStudy.content.locaux, point) : null;
                      if (!room) {
                        if (!shownStudy) return [];
                        return [
                          {
                            cle: "creer-local",
                            label: "Créer un local ici",
                            disabled: editionState.natureChangeDisabled,
                            title: editionState.natureBlockedReason ?? undefined,
                            faire: () => {
                              elementsState.select(null);
                              setParams({ local: null, panneau: "fiche" });
                              editionState.startNew(point);
                            },
                          },
                        ];
                      }
                      const actionsNature: PlanAction[] = otherLocalNatures(room.nature).map((nature) => ({
                        cle: `nature-${nature}`,
                        label: `Classer : ${NATURE_LABELS[nature]}`,
                        disabled: editionState.natureChangeDisabled,
                        title:
                          editionState.natureBlockedReason ??
                          (editionState.natureChangeDisabled ? "Un calcul est déjà en cours." : undefined),
                        faire: () => {
                          selectRoom(room.id);
                          void editionState.changeNature(room.id, nature);
                        },
                      }));
                      return [
                        { cle: "fiche", label: `Ouvrir « ${room.nom} »`, faire: () => selectRoom(room.id) },
                        ...actionsNature,
                        {
                          cle: "contour",
                          label: "Reprendre le contour",
                          faire: () => {
                            selectRoom(room.id);
                            editionState.startOn(room.id, "contour");
                          },
                        },
                        {
                          cle: "couper",
                          label: "Couper en deux",
                          faire: () => {
                            selectRoom(room.id);
                            editionState.startOn(room.id, "couper");
                          },
                        },
                        {
                          cle: "supprimer-local",
                          label: `Supprimer définitivement « ${room.nom} »`,
                          disabled: editionState.natureChangeDisabled,
                          title: editionState.natureBlockedReason ?? undefined,
                          faire: () => {
                            if (!window.confirm(
                              `Supprimer définitivement le local « ${room.nom} » ?\n\nSes contours et métrés disparaîtront de la version courante. Une ancienne version de l'étude permettra de le récupérer.`,
                            )) return;
                            void editionState.deleteRoom(room.id).then((supprime) => {
                              if (supprime) {
                                elementsState.select(null);
                                setParams({ local: null, panneau: "fiche" });
                              }
                            });
                          },
                        },
                      ];
                    })();
                setMenu(actions.length ? { x: ecran.x, y: ecran.y, actions } : null);
              }}
              onGrab={editionState.handlers.onGrab}
              onGrabMove={editionState.handlers.onGrabMove}
              onGrabEnd={editionState.handlers.onGrabEnd}
              initialView={views.current.get(viewKey) ?? null}
              onViewChange={(view) => views.current.set(viewKey, view)}
              focus={focusPlan}
              renderTools={
                shownStudy ? (
                  <div className="th-viewer__display" role="group" aria-label="Ce qui s'affiche sur le plan">
                    {METRICS_CASES.map((item) => (
                      <label key={item.cle} title={item.titre}>
                        <input
                          type="checkbox"
                          checked={metricsAffiches[item.cle]}
                          onChange={() => basculerMetrique(item.cle, metricsAffiches)}
                        />
                        {item.label}
                      </label>
                    ))}
                    {/* Dire qui commande, sinon une case cochée par l'étape passe pour un bug (Q6). */}
                    {calquesPilotes && <small className="th-viewer__pilote">réglés par l'étape</small>}
                  </div>
                ) : undefined
              }
              renderOverlay={(toScreen) => (
                <>
                  <NorthOverlay nord={sheet.nord} enCours={points} toScreen={toScreen} actif={tool === "nord"} />
                  {shownStudy && (
                    <>
                        <StudyOverlay
                          rooms={shownStudy.content.locaux}
                          selectedId={selectedRoom?.id ?? null}
                          toScreen={toScreen}
                          onSelect={selectRoom}
                          draft={editionState.draft}
                          locked={tool !== "pan"}
                          gaps={shownStudy.content.couverture?.zones_non_affectees_pdf ?? []}
                        />
                        {!editionState.draft && (
                          <StudyMetrics
                            rooms={shownStudy.content.locaux}
                            selected={selectedRoom}
                            shapes={shownStudy.content.enveloppe.objets ?? []}
                            bridges={shownStudy.content.enveloppe.liaisons ?? []}
                            show={metricsAffiches}
                            toScreen={toScreen}
                            selectedElement={elementsState.selected}
                            grouperPonts={etape !== "ponts"}
                          />
                      )}
                    </>
                  )}
                </>
              )}
            />
          ) : (
            <div className="th-viewer th-viewer--empty">
              <p className="th-viewer__status">
                {raster.error ? `Affichage impossible : ${raster.error.message}` : "Préparation de la planche… (quelques secondes à la première ouverture)"}
              </p>
            </div>
          )}
          {menu && <PlanMenu x={menu.x} y={menu.y} actions={menu.actions} onClose={() => setMenu(null)} />}
        </div>

        <aside className="th-panel th-ws__panel" aria-label={PANELS.find((item) => item.id === panel)?.label}>
          {panel === "planche" &&
            (sheet ? (
              <SheetPanel
                key={sheet.id}
                projectId={project.id}
                sheet={sheet}
                isReference={sheet.id === reference?.id}
                onMakeReference={() => makeReference(sheet.id)}
                tool={tool}
                onTool={setTool}
                points={points}
                study={study}
                transform={raster.data?.transform ?? null}
                onStudyImported={(imported) => queryClient.setQueryData<Study>(studyQueryKey(sheet.id), imported)}
              />
            ) : (
              <p className="th-muted">Aucune planche : déposez les plans dans « Documents ».</p>
            ))}
          {panel === "documents" && (
            <DocumentsPanel project={project} currentSheetId={sheetId} onShowSheet={(id) => setParams({ planche: id })} />
          )}
          {panel === "bibliotheque" && <LibraryPanel projectId={project.id} />}
          {panel === "infos" && <InfoPanel key={project.id} project={project} referenceId={reference?.id ?? null} onReference={makeReference} />}
          {panel === "fiche" && (
            <>
              {editionState.creation ? (
                <StudyRoomCreationPanel creation={editionState.creation} />
              ) : (
                <>
              {/* Une chose à la fois (D107) : l'étape « ponts thermiques » est une passe sur le niveau,
                  et la fiche du local n'a rien à y faire. */}
              {etape === "ponts" && shownStudy && !editionState.draft ? (
                <PontsPanel
                  content={shownStudy.content}
                  selected={elementsState.selected}
                  onSelect={elementsState.select}
                  busy={elementsState.busy}
                  message={elementsState.message}
                  onOperation={elementsState.apply}
                />
              ) : (
                <>
                  {/* Un élément désigné prend tout le bandeau : voir la fiche du local par-dessus noyait
                      l'information qu'on venait justement de demander. */}
                  {!elementsState.selected && (
                    <StudyRoomPanel
                      room={selectedRoom}
                      state={selectedRoom ? study?.local_states[selectedRoom.id] : undefined}
                      edition={editionState.edition}
                    />
                  )}
                  {/* Les éléments du local, sous sa fiche et jamais en carte flottante (F4, Q8). */}
                  {shownStudy && !editionState.draft && (
                    <ElementPanel
                      content={shownStudy.content}
                      room={selectedRoom}
                      selected={elementsState.selected}
                      onSelect={elementsState.select}
                      busy={elementsState.busy}
                      message={elementsState.message}
                      onOperation={elementsState.apply}
                    />
                  )}
                </>
              )}
              {(elementsState.pending > 0 || elementsState.canRedo) && (
                <div className="th-element-enregistrer">
                  {/* D105 : le geste est immédiat, seul le plan attend un recalcul. On le dit. */}
                  {elementsState.pending > 0 ? (
                    <p className="th-alert th-alert--warn">
                      {elementsState.pending} correction{elementsState.pending > 1 ? "s" : ""} en attente —
                      recalculez pour les voir sur le plan.
                    </p>
                  ) : (
                    <p className="th-alert">Aucune correction en attente. Une action peut encore être rétablie.</p>
                  )}
                  <div className="th-inline">
                    <button
                      type="button"
                      className="po2-button po2-button--ghost"
                      disabled={elementsState.busy || !elementsState.canUndo}
                      onClick={elementsState.undo}
                    >
                      Annuler (Ctrl+Z)
                    </button>
                    <button
                      type="button"
                      className="po2-button po2-button--ghost"
                      disabled={elementsState.busy || !elementsState.canRedo}
                      onClick={elementsState.redo}
                    >
                      Rétablir
                    </button>
                    <button
                      type="button"
                      className="po2-button po2-button--primary"
                      disabled={elementsState.busy || elementsState.pending === 0}
                      onClick={elementsState.save}
                    >
                      Enregistrer les corrections
                    </button>
                    <button
                      type="button"
                      className="po2-button po2-button--ghost"
                      disabled={elementsState.busy || elementsState.pending === 0}
                      onClick={elementsState.recompute}
                    >
                      {elementsState.busy ? "Recalcul…" : "Recalculer le plan"}
                    </button>
                    <button type="button" className="th-link" disabled={elementsState.busy || elementsState.pending === 0} onClick={elementsState.cancel}>
                      Tout annuler
                    </button>
                  </div>
                </div>
              )}
                </>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
