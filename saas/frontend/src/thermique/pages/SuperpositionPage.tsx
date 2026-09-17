import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type PdfPoint } from "../api";
import { NATURE_COLORS, calquesApi } from "../calques";
import { TileSheetViewer, type ToScreen } from "../components/TileSheetViewer";
import { allSheets, projectQueryKey } from "../projectCache";
import { rasterToPdf } from "../raster";
import { superpositionApi, type SuperpositionOverview, type SuperpositionProposal } from "../superposition";
import { ProjectTabs } from "./ProjectLibraryPage";

const RASTER_STALE_MS = 6 * 3600 * 1000;
const PT_EN_M = 25.4 / 72 / 1000;
const natureColor = (nature: string) => NATURE_COLORS[nature] ?? "#5f6b73";
const cm = (value: number) => new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(value);

type Offset = [number, number];

function proposalLabel(proposal: SuperpositionProposal): string {
  if (proposal.etat === "superpose") {
    return "Déjà superposé au niveau de référence.";
  }
  if (proposal.etat === "decale") {
    return "Décalé : la position proposée superpose les deux plans.";
  }
  return "Correspondance incertaine : vérifiez et calez à la main (Maj + glisser).";
}

// Étape E2 : chaque plan est posé sur le niveau de référence (translation proposée, vérifiée en transparence,
// corrigée en glissant) ; la superposition validée devient le calage du niveau.
export function SuperpositionPage() {
  const { token } = useAuth();
  const projectId = Number(useParams().projectId);
  const queryClient = useQueryClient();
  const enabled = Boolean(token) && Number.isFinite(projectId);
  const overviewKey = ["thermique", "superposition", projectId] as const;

  const [selectedId, setSelectedId] = useState<number | null>(null);
  // référence choisie tant qu'aucune superposition n'est validée (ensuite, celle du serveur)
  const [referenceChoice, setReferenceChoice] = useState<number | null>(null);
  const [offset, setOffset] = useState<Offset | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const dragRef = useRef<{ start: PdfPoint; offset: Offset } | null>(null);

  const projectQuery = useQuery({
    queryKey: projectQueryKey(projectId),
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled,
  });
  const overview = useQuery({ queryKey: overviewKey, queryFn: () => superpositionApi.overview(token!, projectId), enabled });
  const data = overview.data;
  const anyValidated = data?.planches.some((item) => item.valide) ?? false;
  const referenceId = (anyValidated ? null : referenceChoice) ?? data?.reference_id ?? null;
  const sheets = projectQuery.data ? allSheets(projectQuery.data) : [];
  const reference = sheets.find((item) => item.id === referenceId);
  const selected = data?.planches.find((item) => item.id === selectedId) ?? null;
  const aligning = selected !== null && selected.id !== referenceId;
  const selectedSheet = sheets.find((item) => item.id === selectedId);
  const rotation = reference?.rotation_deg ?? 0;
  const metresPerPt = PT_EN_M * (selectedSheet?.scale_denominator ?? reference?.scale_denominator ?? 0);

  // première planche à caler, sinon la première autre que la référence
  useEffect(() => {
    if (!data || selectedId !== null) {
      return;
    }
    const others = data.planches.filter((item) => item.id !== referenceId);
    setSelectedId((others.find((item) => !item.valide) ?? others[0])?.id ?? null);
  }, [data, selectedId, referenceId]);

  const raster = useQuery({
    queryKey: ["thermique", "raster", reference?.id ?? 0, rotation],
    queryFn: () => thermiqueApi.getRaster(token!, reference!.id, rotation),
    enabled: Boolean(token && reference),
    staleTime: RASTER_STALE_MS,
  });
  const proposal = useQuery({
    queryKey: ["thermique", "superposition-proposition", projectId, selectedId ?? 0, referenceId ?? 0],
    queryFn: () => superpositionApi.proposal(token!, projectId, selectedId!, referenceId!),
    enabled: Boolean(token && aligning && referenceId),
    staleTime: Infinity,
    retry: false,
  });
  const referenceDrawing = useQuery({
    queryKey: ["thermique", "calques-designes", projectId, referenceId ?? 0],
    queryFn: () => calquesApi.designated(token!, referenceId!),
    enabled: Boolean(token && referenceId),
    staleTime: Infinity,
  });
  const levelDrawing = useQuery({
    queryKey: ["thermique", "calques-designes", projectId, selectedId ?? 0],
    queryFn: () => calquesApi.designated(token!, selectedId!),
    enabled: Boolean(token && aligning),
    staleTime: Infinity,
  });

  // position de départ : la superposition validée, sinon la proposition
  useEffect(() => {
    if (!aligning || offset !== null) {
      return;
    }
    if (selected?.valide && selected.decalage) {
      setOffset(selected.decalage);
    } else if (proposal.data) {
      setOffset([proposal.data.dx, proposal.data.dy]);
    }
  }, [aligning, offset, selected, proposal.data]);

  function select(id: number) {
    setSelectedId(id);
    setOffset(null);
    setNotice(null);
  }

  function refresh(next: SuperpositionOverview) {
    queryClient.setQueryData(overviewKey, next);
    void queryClient.invalidateQueries({ queryKey: ["thermique", "metre"] });
    void queryClient.invalidateQueries({ queryKey: projectQueryKey(projectId) });
  }

  const validateMutation = useMutation({
    mutationFn: (payload: { reference: number; sheet: number; offset: Offset }) =>
      superpositionApi.validate(token!, projectId, {
        reference_id: payload.reference,
        planche_id: payload.sheet,
        dx: payload.offset[0],
        dy: payload.offset[1],
      }),
    onSuccess: (next, payload) => {
      refresh(next);
      setReferenceChoice(null);
      if (payload.sheet === payload.reference) {
        setNotice("Niveau de référence enregistré.");
        setSelectedId(null);
        setOffset(null);
        return;
      }
      const label = next.planches.find((item) => item.id === payload.sheet)?.libelle ?? "";
      const others = next.planches.filter((item) => item.id !== next.reference_id);
      const following = others.find((item) => !item.valide);
      setNotice(`Superposition de « ${label} » validée.${following ? "" : " Tous les plans sont superposés."}`);
      if (following) {
        select(following.id);
      }
    },
  });
  const resetMutation = useMutation({
    mutationFn: (sheetId: number) => superpositionApi.reset(token!, projectId, sheetId),
    onSuccess: (next) => {
      refresh(next);
      setOffset(null);
      setNotice("Validation annulée.");
    },
  });
  const busy = validateMutation.isPending || resetMutation.isPending;
  const actionError = validateMutation.error ?? resetMutation.error;

  // un clic sur une flèche déplace le niveau d'un point, dans le sens de l'écran
  function nudge(screenX: number, screenY: number) {
    if (!raster.data || !offset) {
      return;
    }
    const origin = rasterToPdf(raster.data.transform, 0, 0);
    const moved = rasterToPdf(raster.data.transform, screenX, screenY);
    const length = Math.hypot(moved[0] - origin[0], moved[1] - origin[1]) || 1;
    setOffset([offset[0] + Math.round((moved[0] - origin[0]) / length), offset[1] + Math.round((moved[1] - origin[1]) / length)]);
  }

  function renderOverlay(toScreen: ToScreen): ReactNode {
    const points = (coords: number[], shift: Offset) => {
      const out: string[] = [];
      for (let k = 0; k + 1 < coords.length; k += 2) {
        out.push(
          toScreen([coords[k] + shift[0], coords[k + 1] + shift[1]])
            .map((value) => value.toFixed(1))
            .join(","),
        );
      }
      return out.join(" ");
    };
    const drawing = (group: { traits: number[][]; remplissages: number[][] }, shift: Offset) => (
      <>
        {group.remplissages.map((coords, index) => (
          <polygon key={`r${index}`} points={points(coords, shift)} />
        ))}
        {group.traits.map((coords, index) => (
          <polyline key={index} points={points(coords, shift)} />
        ))}
      </>
    );
    return (
      <>
        {referenceDrawing.data && (
          <g className="th-sup-reference">
            {Object.entries(referenceDrawing.data.natures).map(([key, group]) => (
              <g key={key}>{drawing(group, [0, 0])}</g>
            ))}
          </g>
        )}
        {aligning && offset && levelDrawing.data && (
          <g className="th-sup-niveau">
            {Object.entries(levelDrawing.data.natures).map(([key, group]) => (
              <g key={key} className="th-calque" style={{ "--nature": natureColor(key) } as CSSProperties}>
                {drawing(group, offset)}
              </g>
            ))}
          </g>
        )}
      </>
    );
  }

  const proposed = proposal.data;
  const offsetM = offset ? [offset[0] * metresPerPt * 100, offset[1] * metresPerPt * 100] : null;

  return (
    <div className="th-viewer-layout">
      {reference && raster.data ? (
        <TileSheetViewer
          manifest={raster.data}
          tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
          tool="superposer"
          onAddPoint={() => undefined}
          onGrab={(point, _scale, event) => {
            if (!event.shiftKey || !aligning || !offset) {
              return false;
            }
            dragRef.current = { start: point, offset };
            return true;
          }}
          onGrabMove={(point) => {
            const drag = dragRef.current;
            if (drag) {
              setOffset([
                Math.round(drag.offset[0] + point[0] - drag.start[0]),
                Math.round(drag.offset[1] + point[1] - drag.start[1]),
              ]);
            }
          }}
          onGrabEnd={() => {
            dragRef.current = null;
          }}
          renderOverlay={renderOverlay}
        />
      ) : (
        <div className="th-viewer th-viewer--empty">
          <p className="th-viewer__status">
            {raster.error
              ? `Affichage impossible : ${raster.error.message}`
              : overview.isLoading
                ? "Lecture des plans…"
                : reference
                  ? "Préparation de la planche…"
                  : "Aucune planche de plan à l'échelle définie."}
          </p>
        </div>
      )}

      <aside className="th-panel">
        <div>
          <p className="po2-eyebrow">
            <Link to="/">Projets</Link> · <Link to={`/projets/${projectId}`}>{projectQuery.data?.name ?? "Projet"}</Link>
          </p>
          <h1 className="th-panel__title">Superposition</h1>
        </div>
        <ProjectTabs projectId={projectId} />
        <p className="th-muted">
          Chaque plan est posé sur le niveau de référence (en gris). Le plan choisi apparaît par-dessus, avec les couleurs de ses
          calques : vérifiez que les murs coïncident, corrigez avec <strong>Maj + glisser</strong> ou les flèches, puis validez.
        </p>

        {overview.error && <p className="th-alert th-alert--error">{overview.error.message}</p>}
        {actionError && <p className="th-alert th-alert--error">{actionError.message}</p>}
        {notice && <p className="th-alert th-alert--ok">{notice}</p>}

        {data && data.planches.length > 0 && (
          <label className="th-field">
            <span>Niveau de référence</span>
            <select
              value={referenceId ?? ""}
              disabled={busy}
              onChange={(event) => {
                const next = Number(event.target.value);
                if (!anyValidated) {
                  setReferenceChoice(next);
                  setSelectedId(null);
                  setOffset(null);
                  return;
                }
                validateMutation.mutate({ reference: next, sheet: next, offset: [0, 0] });
              }}
            >
              {data.planches.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.libelle}
                </option>
              ))}
            </select>
            {anyValidated && <small className="th-muted">Changer de référence recale les plans déjà validés sur la nouvelle.</small>}
          </label>
        )}

        {data && (
          <section>
            <h2>Plans</h2>
            <ul className="th-sup-list">
              {data.planches.map((item) => {
                const isReference = item.id === referenceId;
                const state = isReference ? "Référence" : item.valide ? "Validé" : item.cale_main ? "Calé à la main" : "À vérifier";
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={`th-sup-item${item.id === selectedId ? " is-selected" : ""}`}
                      disabled={isReference}
                      aria-pressed={item.id === selectedId}
                      onClick={() => select(item.id)}
                    >
                      <span>
                        <strong>{item.libelle}</strong>
                        {item.niveau && item.niveau !== item.libelle ? <small> · niveau {item.niveau}</small> : null}
                      </span>
                      <span className={`th-sup-state${isReference || item.valide ? " is-ok" : ""}`}>{state}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        )}

        {aligning && selected && (
          <section className="th-edgebox th-calque-panel">
            <strong>{selected.libelle} sur {data?.planches.find((item) => item.id === referenceId)?.libelle}</strong>
            {proposal.isLoading && !selected.valide && <span className="th-muted">Recherche de la position… (quelques secondes)</span>}
            {proposal.error && <span className="th-alert th-alert--error">{proposal.error.message}</span>}
            {proposal.data && !selected.valide && (
              <span className={proposal.data.etat === "incertain" ? "th-alert th-alert--warn" : "th-muted"}>
                {proposalLabel(proposal.data)} ({Math.round(proposal.data.score * 100)} % des traits retrouvés)
              </span>
            )}
            {levelDrawing.data && Object.keys(levelDrawing.data.natures).length === 0 && (
              <span className="th-alert th-alert--warn">Aucun calque désigné sur ce plan : désignez ses murs dans l'onglet Calques.</span>
            )}
            {offset && offsetM && (
              <>
                <span>
                  Décalage : {cm(offsetM[0])} cm ; {cm(offsetM[1])} cm <small className="th-muted">({offset[0]} ; {offset[1]} pt)</small>
                </span>
                <div className="th-sup-nudge" aria-label="Déplacer le plan d'un point">
                  <button type="button" className="po2-button po2-button--ghost" onClick={() => nudge(0, -1)} aria-label="Vers le haut">
                    ↑
                  </button>
                  <button type="button" className="po2-button po2-button--ghost" onClick={() => nudge(-1, 0)} aria-label="Vers la gauche">
                    ←
                  </button>
                  <button type="button" className="po2-button po2-button--ghost" onClick={() => nudge(1, 0)} aria-label="Vers la droite">
                    →
                  </button>
                  <button type="button" className="po2-button po2-button--ghost" onClick={() => nudge(0, 1)} aria-label="Vers le bas">
                    ↓
                  </button>
                </div>
                <div className="th-inline">
                  <button
                    type="button"
                    className="po2-button po2-button--primary"
                    disabled={busy || referenceId === null}
                    onClick={() => validateMutation.mutate({ reference: referenceId!, sheet: selected.id, offset })}
                  >
                    {selected.valide ? "Enregistrer la correction" : "Valider la superposition"}
                  </button>
                  {proposed && (offset[0] !== proposed.dx || offset[1] !== proposed.dy) && (
                    <button type="button" className="po2-button po2-button--ghost" onClick={() => setOffset([proposed.dx, proposed.dy])}>
                      Revenir à la proposition
                    </button>
                  )}
                </div>
                {selected.cale_main && (
                  <small className="th-muted">Ce niveau a un calage A-B posé dans « Métré » : la validation le remplace.</small>
                )}
                {selected.valide && (
                  <button type="button" className="th-link th-link--danger" disabled={busy} onClick={() => resetMutation.mutate(selected.id)}>
                    Annuler la validation
                  </button>
                )}
              </>
            )}
          </section>
        )}

        {data && !aligning && data.planches.length > 1 && (
          <p className="th-muted">Choisissez un plan dans la liste pour le superposer à la référence.</p>
        )}
      </aside>
    </div>
  );
}
