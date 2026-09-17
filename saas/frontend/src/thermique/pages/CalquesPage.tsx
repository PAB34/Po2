import { useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type PdfPoint } from "../api";
import { NATURE_COLORS, calquesApi, type CalquePick, type CalqueRect, type CalqueZone, type CalquesProject } from "../calques";
import { TileSheetViewer, type ToScreen } from "../components/TileSheetViewer";
import { allSheets, projectQueryKey } from "../projectCache";
import { ProjectTabs } from "./ProjectLibraryPage";

const RASTER_STALE_MS = 6 * 3600 * 1000;
const PICK_PX = 8;
const countFormat = new Intl.NumberFormat("fr-FR");
const plural = (count: number, word: string) => `${countFormat.format(count)} ${word}${count > 1 ? "s" : ""}`;
const natureColor = (nature: string) => NATURE_COLORS[nature] ?? "#5f6b73";
const ZONE_MIN_PX = 6;
const rectOf = (a: PdfPoint, b: PdfPoint): CalqueRect => ({ x0: a[0], y0: a[1], x1: b[0], y1: b[1] });

// Étape E1 : le thermicien clique un élément du plan et donne sa nature ; tous ses semblables, sur tous les
// plans, la prennent. Ce qui n'est pas désigné est ignoré.
export function CalquesPage() {
  const { token } = useAuth();
  const projectId = Number(useParams().projectId);
  const queryClient = useQueryClient();
  const enabled = Boolean(token) && Number.isFinite(projectId);
  const listKey = ["thermique", "calques", projectId] as const;

  const [sheetId, setSheetId] = useState<number | null>(null);
  const [pick, setPick] = useState<CalquePick | null>(null);
  const [scope, setScope] = useState("");
  const [nature, setNature] = useState("mur");
  const [shownRule, setShownRule] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const pixelsPerPt = useRef(1);
  // Zone : tracé en cours (Maj + glisser), puis rectangle retenu, son contenu et les calques cochés.
  const draftRef = useRef<[PdfPoint, PdfPoint] | null>(null);
  const [draft, setDraft] = useState<[PdfPoint, PdfPoint] | null>(null);
  const [zoneRect, setZoneRect] = useState<CalqueRect | null>(null);
  const [zone, setZone] = useState<CalqueZone | null>(null);
  const [zoneRules, setZoneRules] = useState<number[]>([]);

  const projectQuery = useQuery({
    queryKey: projectQueryKey(projectId),
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled,
  });
  const list = useQuery({ queryKey: listKey, queryFn: () => calquesApi.list(token!, projectId), enabled, retry: false });
  const data = list.data;
  const sheets = projectQuery.data ? allSheets(projectQuery.data) : [];
  const currentSheetId = sheetId ?? data?.planches[0]?.id ?? null;
  const sheet = sheets.find((item) => item.id === currentSheetId);
  const rotation = sheet?.rotation_deg ?? 0;

  const raster = useQuery({
    queryKey: ["thermique", "raster", sheet?.id ?? 0, rotation],
    queryFn: () => thermiqueApi.getRaster(token!, sheet!.id, rotation),
    enabled: Boolean(token && sheet),
    staleTime: RASTER_STALE_MS,
  });
  const designated = useQuery({
    queryKey: ["thermique", "calques-designes", projectId, currentSheetId ?? 0],
    queryFn: () => calquesApi.designated(token!, currentSheetId!),
    enabled: Boolean(token && currentSheetId),
    staleTime: Infinity,
  });

  const shown = shownRule !== null ? data?.regles.find((rule) => rule.id === shownRule) ?? null : null;
  const familySignature = pick ? pick.element.signature : shown?.signature ?? null;
  const familyForme = pick ? scope : shown?.forme ?? null;
  const family = useQuery({
    queryKey: ["thermique", "calques-famille", currentSheetId ?? 0, familySignature ?? "", familyForme ?? ""],
    queryFn: () => calquesApi.family(token!, currentSheetId!, familySignature!, familyForme!),
    enabled: Boolean(token && currentSheetId && familySignature && familyForme),
    staleTime: Infinity,
  });

  function refresh(next: CalquesProject) {
    queryClient.setQueryData(listKey, next);
    void queryClient.invalidateQueries({ queryKey: ["thermique", "calques-designes", projectId] });
  }

  const pickMutation = useMutation({
    mutationFn: (point: PdfPoint) => calquesApi.pick(token!, currentSheetId!, point, PICK_PX / pixelsPerPt.current),
    onSuccess: (result) => {
      setPick(result);
      setShownRule(null);
      setScope(result.familles[0].forme);
      setNature(result.regle?.nature ?? "mur");
      setNotice(null);
      closeZone();
    },
    onError: () => setPick(null),
  });
  const selectedFamily = pick?.familles.find((item) => item.forme === scope) ?? pick?.familles[0] ?? null;
  const saveMutation = useMutation({
    mutationFn: () => calquesApi.save(token!, projectId, { signature: pick!.element.signature, forme: scope, nature }),
    onSuccess: (next) => {
      refresh(next);
      setNotice(`${plural(selectedFamily?.total ?? 0, "élément")} désigné${(selectedFamily?.total ?? 0) > 1 ? "s" : ""} « ${next.natures[nature]} ».`);
      setPick(null);
    },
  });
  const removeMutation = useMutation({
    mutationFn: (ruleId: number) => calquesApi.remove(token!, projectId, ruleId),
    onSuccess: (next) => {
      refresh(next);
      setShownRule(null);
      setPick(null);
    },
  });
  const excludeMutation = useMutation({
    mutationFn: ({ ruleId, planche, element }: { ruleId: number; planche: number; element: number }) =>
      calquesApi.toggleExclusion(token!, projectId, ruleId, { planche_id: planche, element }),
    onSuccess: (next) => {
      refresh(next);
      setPick((current) => (current?.regle ? { ...current, regle: { ...current.regle, exclu: !current.regle.exclu } } : current));
    },
  });
  const zoneMutation = useMutation({
    mutationFn: (rect: CalqueRect) => calquesApi.zone(token!, currentSheetId!, rect),
    onSuccess: (result, rect) => {
      setZoneRect(rect);
      setZone(result);
      setZoneRules((current) => {
        const ids = result.calques.map((item) => item.id);
        const kept = current.filter((id) => ids.includes(id));
        return kept.length ? kept : ids;
      });
    },
  });
  const applyZoneMutation = useMutation({
    mutationFn: (action: "retirer" | "remettre") => calquesApi.applyZone(token!, currentSheetId!, zoneRect!, zoneRules, action),
    onSuccess: (next, action) => {
      refresh(next);
      setNotice(action === "retirer" ? "Éléments de la zone retirés." : "Éléments de la zone remis.");
      zoneMutation.mutate(zoneRect!);
    },
  });
  function closeZone() {
    setZone(null);
    setZoneRect(null);
    zoneMutation.reset();
  }
  const busy = saveMutation.isPending || removeMutation.isPending || excludeMutation.isPending || applyZoneMutation.isPending;
  const actionError =
    pickMutation.error ?? saveMutation.error ?? removeMutation.error ?? excludeMutation.error ?? zoneMutation.error ?? applyZoneMutation.error;
  const zoneChosen = zone?.calques.filter((item) => zoneRules.includes(item.id)) ?? [];
  const zoneActive = zoneChosen.reduce((sum, item) => sum + item.actifs, 0);
  const zoneRemoved = zoneChosen.reduce((sum, item) => sum + item.retires, 0);

  const rect = draft ? rectOf(draft[0], draft[1]) : zoneRect;

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
        {designated.data &&
          Object.entries(designated.data.natures).map(([key, group]) => (
            <g key={key} className="th-calque" style={{ "--nature": natureColor(key) } as CSSProperties}>
              {group.remplissages.map((coords, index) => (
                <polygon key={`r${index}`} points={points(coords)} />
              ))}
              {group.traits.map((coords, index) => (
                <polyline key={index} points={points(coords)} />
              ))}
            </g>
          ))}
        {family.data && (
          <g className="th-calque-famille">
            {family.data.remplissages.map((coords, index) => (
              <polygon key={`r${index}`} points={points(coords)} />
            ))}
            {family.data.traits.map((coords, index) => (
              <polyline key={index} points={points(coords)} />
            ))}
          </g>
        )}
        {pick && <polyline className="th-calque-choisi" points={points(pick.element.coords)} />}
        {zone && (
          <g className="th-calque-zone">
            {zone.remplissages.map((coords, index) => (
              <polygon key={`r${index}`} points={points(coords)} />
            ))}
            {zone.traits.map((coords, index) => (
              <polyline key={index} points={points(coords)} />
            ))}
          </g>
        )}
        {rect && <polygon className="th-calque-rect" points={points([rect.x0, rect.y0, rect.x1, rect.y0, rect.x1, rect.y1, rect.x0, rect.y1])} />}
      </>
    );
  }

  const naturesShown = Object.keys(designated.data?.natures ?? {});

  return (
    <div className="th-viewer-layout">
      {sheet && raster.data ? (
        <TileSheetViewer
          manifest={raster.data}
          tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
          tool="designer"
          onAddPoint={(point) => {
            if (currentSheetId !== null && !pickMutation.isPending) {
              pickMutation.mutate(point);
            }
          }}
          onHover={(_, scale) => {
            pixelsPerPt.current = scale;
          }}
          onGrab={(point, scale, event) => {
            if (!event.shiftKey || currentSheetId === null) {
              return false;
            }
            pixelsPerPt.current = scale;
            draftRef.current = [point, point];
            setDraft(draftRef.current);
            setPick(null);
            setShownRule(null);
            return true;
          }}
          onGrabMove={(point) => {
            if (draftRef.current) {
              draftRef.current = [draftRef.current[0], point];
              setDraft(draftRef.current);
            }
          }}
          onGrabEnd={() => {
            const current = draftRef.current;
            draftRef.current = null;
            setDraft(null);
            if (!current) {
              return;
            }
            const [a, b] = current;
            const sizePx = Math.min(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1])) * pixelsPerPt.current;
            if (sizePx >= ZONE_MIN_PX) {
              zoneMutation.mutate(rectOf(a, b));
            }
          }}
          renderOverlay={renderOverlay}
        />
      ) : (
        <div className="th-viewer th-viewer--empty">
          <p className="th-viewer__status">
            {raster.error
              ? `Affichage impossible : ${raster.error.message}`
              : list.isLoading
                ? "Lecture des plans…"
                : sheet
                  ? "Préparation de la planche…"
                  : "Aucune planche de plan à afficher."}
          </p>
        </div>
      )}

      <aside className="th-panel">
        <div>
          <p className="po2-eyebrow">
            <Link to="/">Projets</Link> · <Link to={`/projets/${projectId}`}>{projectQuery.data?.name ?? "Projet"}</Link>
          </p>
          <h1 className="th-panel__title">Calques</h1>
        </div>
        <ProjectTabs projectId={projectId} />
        <p className="th-muted">
          Cliquez un trait du plan (mur, isolant, fenêtre…) et donnez sa nature : tous les éléments semblables, sur tous les plans, la
          prennent. Ce que vous ne désignez pas est ignoré. Glissez pour déplacer le plan, molette pour zoomer.
        </p>
        <p className="th-muted">
          <strong>Maj + glisser</strong> : sélectionner une zone (un escalier, un meuble…) pour en retirer d'un coup les éléments désignés à
          tort.
        </p>

        {list.isLoading && <p className="th-muted">Lecture des plans du projet… (quelques secondes par plan la première fois)</p>}
        {list.error && <p className="th-alert th-alert--error">{list.error.message}</p>}
        {actionError && <p className="th-alert th-alert--error">{actionError.message}</p>}
        {notice && <p className="th-alert th-alert--ok">{notice}</p>}

        {data && data.planches.length === 0 && (
          <p className="th-alert th-alert--warn">
            Aucune planche de plan à l'échelle définie : dans « Plans et planches », classez vos plans et renseignez leur échelle.
          </p>
        )}
        {data && data.planches.length > 0 && (
          <label className="th-field">
            <span>Plan affiché</span>
            <select
              value={currentSheetId ?? ""}
              onChange={(event) => {
                setSheetId(Number(event.target.value));
                setPick(null);
                closeZone();
              }}
            >
              {data.planches.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.libelle}
                </option>
              ))}
            </select>
          </label>
        )}
        {pickMutation.isPending && <p className="th-muted">Recherche de l'élément…</p>}
        {zoneMutation.isPending && !zone && <p className="th-muted">Lecture de la zone…</p>}

        {zone && (
          <section className="th-edgebox th-calque-panel">
            <strong>Zone sélectionnée</strong>
            {zone.calques.length === 0 ? (
              <span className="th-muted">Aucun élément désigné entièrement dans cette zone.</span>
            ) : (
              <fieldset className="th-calque-scope">
                <legend>Calques concernés</legend>
                {zone.calques.map((item) => (
                  <label key={item.id} className="th-check">
                    <input
                      type="checkbox"
                      checked={zoneRules.includes(item.id)}
                      onChange={(event) =>
                        setZoneRules((current) =>
                          event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id),
                        )
                      }
                    />
                    <span className="th-calque-dot" style={{ background: natureColor(item.nature) }} />
                    <span>
                      <strong>{item.nature_libelle}</strong> ({item.libelle} · {item.forme_libelle}) : {plural(item.actifs, "élément")}
                      {item.retires ? `, ${countFormat.format(item.retires)} déjà retiré${item.retires > 1 ? "s" : ""}` : ""}
                    </span>
                  </label>
                ))}
              </fieldset>
            )}
            {zone.tronque && <small className="th-muted">Zone très chargée : une partie des éléments n'est pas surlignée.</small>}
            <div className="th-inline">
              {zoneActive > 0 && (
                <button type="button" className="po2-button po2-button--primary" disabled={busy} onClick={() => applyZoneMutation.mutate("retirer")}>
                  Retirer {plural(zoneActive, "élément")}
                </button>
              )}
              {zoneRemoved > 0 && (
                <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={() => applyZoneMutation.mutate("remettre")}>
                  Remettre {plural(zoneRemoved, "élément")}
                </button>
              )}
              <button type="button" className="po2-button po2-button--ghost" onClick={closeZone}>
                Fermer
              </button>
            </div>
          </section>
        )}

        {data && pick && selectedFamily && (
          <section className="th-edgebox th-calque-panel">
            <strong>Élément choisi</strong>
            <span>
              {pick.element.libelle} · {pick.element.forme_libelle}
            </span>
            {pick.regle && (
              <span className="th-muted">
                Déjà désigné : {pick.regle.nature_libelle}
                {pick.regle.exclu ? " (cet élément en est retiré)" : ""}.
              </span>
            )}
            <fieldset className="th-calque-scope">
              <legend>Éléments concernés</legend>
              {pick.familles.map((item) => (
                <label key={item.forme} className="th-check">
                  <input type="radio" name="calque-scope" checked={scope === item.forme} onChange={() => setScope(item.forme)} />
                  <span>
                    {item.forme === "*" ? (pick.element.genre === "trait" ? "Tout le trait" : "Tout le remplissage") : `Même trait, ${item.forme_libelle}`} :{" "}
                    <strong>{plural(item.total, "élément")}</strong> sur {plural(item.par_planche.length, "plan")}
                  </span>
                </label>
              ))}
              <small className="th-muted">
                {selectedFamily.par_planche.map((item) => `${item.libelle} : ${countFormat.format(item.nombre)}`).join(" · ")}
              </small>
            </fieldset>
            <label className="th-field">
              <span>Nature</span>
              <select value={nature} onChange={(event) => setNature(event.target.value)}>
                {Object.entries(data.natures).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <div className="th-inline">
              <button type="button" className="po2-button po2-button--primary" disabled={busy} onClick={() => saveMutation.mutate()}>
                Désigner {plural(selectedFamily.total, "élément")}
              </button>
              <button type="button" className="po2-button po2-button--ghost" onClick={() => setPick(null)}>
                Annuler
              </button>
            </div>
            {pick.regle && (
              <button
                type="button"
                className="th-link"
                disabled={busy}
                onClick={() => excludeMutation.mutate({ ruleId: pick.regle!.id, planche: pick.element.planche, element: pick.element.index })}
              >
                {pick.regle.exclu
                  ? `Remettre cet élément dans « ${pick.regle.nature_libelle} »`
                  : `Retirer seulement cet élément de « ${pick.regle.nature_libelle} »`}
              </button>
            )}
          </section>
        )}

        {data && (
          <section>
            <h2>Calques désignés</h2>
            {data.regles.length === 0 && <p className="th-muted">Aucun calque désigné pour l'instant : cliquez un trait sur le plan.</p>}
            <ul className="th-sig-list">
              {data.regles.map((rule) => {
                const isShown = shownRule === rule.id;
                return (
                  <li
                    key={rule.id}
                    className={`th-sig is-validated${isShown ? " is-selected" : ""}`}
                    style={{ borderLeftColor: natureColor(rule.nature) }}
                  >
                    <button
                      type="button"
                      className="th-sig__main"
                      aria-pressed={isShown}
                      onClick={() => {
                        setPick(null);
                        setShownRule(isShown ? null : rule.id);
                      }}
                    >
                      <span className="th-calque-dot" style={{ background: natureColor(rule.nature) }} />
                      <span className="th-sig__text">
                        <strong>{rule.nature_libelle}</strong>
                        <small>
                          {rule.libelle} · {rule.forme_libelle}
                        </small>
                        <small>
                          {plural(rule.total, "élément")} sur {plural(rule.par_planche.length, "plan")}
                          {rule.exclusions.length ? ` · ${rule.exclusions.length} retiré${rule.exclusions.length > 1 ? "s" : ""}` : ""}
                        </small>
                      </span>
                      <span className="th-sig__state is-ok">{isShown ? "Affiché" : "Voir"}</span>
                    </button>
                    <div className="th-sig__role">
                      <button type="button" className="th-link th-link--danger" disabled={busy} onClick={() => removeMutation.mutate(rule.id)}>
                        Supprimer
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
        )}

        {naturesShown.length > 0 && (
          <section>
            <h2>Légende du plan</h2>
            <ul className="th-calque-legend">
              {naturesShown.map((key) => (
                <li key={key}>
                  <span className="th-calque-dot" style={{ background: natureColor(key) }} />
                  {data?.natures[key] ?? key}
                </li>
              ))}
              <li>
                <span className="th-calque-dot th-calque-dot--famille" />
                Sélection en cours
              </li>
            </ul>
            {designated.data?.tronque && <p className="th-muted">Plan très chargé : une partie des éléments désignés n'est pas dessinée.</p>}
          </section>
        )}
      </aside>
    </div>
  );
}
