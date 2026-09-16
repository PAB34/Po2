import { useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi } from "../api";
import { TileSheetViewer, type ToScreen } from "../components/TileSheetViewer";
import { allSheets, projectQueryKey } from "../projectCache";
import { formatMeters } from "../scale";
import { signaturesApi, type Signature } from "../signatures";
import { ProjectTabs } from "./ProjectLibraryPage";

const RASTER_STALE_MS = 6 * 3600 * 1000;
const areaFormat = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });
const countFormat = new Intl.NumberFormat("fr-FR");

// Aperçu de la signature : le trait avec sa largeur, sa couleur et ses tirets, ou la teinte du remplissage.
function Swatch({ signature }: { signature: Signature }) {
  if (signature.genre === "aplat") {
    return (
      <svg className="th-sig-swatch" viewBox="0 0 44 16" aria-hidden="true">
        <rect x="1" y="1" width="42" height="14" rx="2" fill={signature.couleur} stroke="#8a94a0" strokeWidth="0.8" />
      </svg>
    );
  }
  const width = Math.min(4, Math.max(0.7, (signature.largeur ?? 0.5) * 1.8));
  const dash = signature.tirets ? signature.tirets.split("-").map((value) => Math.max(1, Number(value) * 1.5)).join(" ") : undefined;
  return (
    <svg className="th-sig-swatch" viewBox="0 0 44 16" aria-hidden="true">
      <rect x="0" y="0" width="44" height="16" rx="2" fill={signature.luminance > 200 ? "#5f6b73" : "#ffffff"} />
      <line x1="4" y1="8" x2="40" y2="8" stroke={signature.couleur} strokeWidth={width} strokeDasharray={dash} />
    </svg>
  );
}

function measure(signature: Signature) {
  const planches = `${signature.planches.length} plan${signature.planches.length > 1 ? "s" : ""}`;
  if (signature.genre === "aplat") {
    return `${countFormat.format(signature.nombre)} facettes · ${areaFormat.format(signature.aire_m2 ?? 0)} m² · ${planches}`;
  }
  return `${countFormat.format(signature.nombre)} traits · ${formatMeters(signature.longueur_m ?? 0)} · ${planches}`;
}

// Étape E1 : l'utilisateur nomme une fois par projet le rôle de chaque « calque » de l'architecte.
export function SignaturesPage() {
  const { token } = useAuth();
  const projectId = Number(useParams().projectId);
  const queryClient = useQueryClient();
  const enabled = Boolean(token) && Number.isFinite(projectId);
  const catalogueKey = ["thermique", "signatures", projectId] as const;

  const [sheetId, setSheetId] = useState<number | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [onlyPending, setOnlyPending] = useState(false);

  const projectQuery = useQuery({
    queryKey: projectQueryKey(projectId),
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled,
  });
  const catalogue = useQuery({
    queryKey: catalogueKey,
    queryFn: () => signaturesApi.get(token!, projectId),
    enabled,
    staleTime: 60_000,
    retry: false,
  });
  const save = useMutation({
    mutationFn: (roles: Record<string, string | null>) => signaturesApi.save(token!, projectId, roles),
    onSuccess: (data) => queryClient.setQueryData(catalogueKey, data),
  });

  const data = catalogue.data;
  const sheets = projectQuery.data ? allSheets(projectQuery.data) : [];
  const currentSheetId = sheetId ?? data?.planches[0]?.id ?? null;
  const sheet = sheets.find((item) => item.id === currentSheetId);
  const rotation = sheet?.rotation_deg ?? 0;
  const selectedSignature = data?.signatures.find((item) => item.cle === selected) ?? null;
  const presentOnSheet = Boolean(selectedSignature && currentSheetId !== null && selectedSignature.planches.includes(currentSheetId));

  const raster = useQuery({
    queryKey: ["thermique", "raster", sheet?.id ?? 0, rotation],
    queryFn: () => thermiqueApi.getRaster(token!, sheet!.id, rotation),
    enabled: Boolean(token && sheet),
    staleTime: RASTER_STALE_MS,
  });
  const elements = useQuery({
    queryKey: ["thermique", "signature-elements", currentSheetId ?? 0, selected ?? ""],
    queryFn: () => signaturesApi.elements(token!, currentSheetId!, selected!),
    enabled: Boolean(token && currentSheetId && selected && presentOnSheet),
    staleTime: Infinity,
  });

  const pending = (data?.signatures ?? []).filter((item) => !item.role);
  const visible = (data?.signatures ?? []).filter((item) => !onlyPending || !item.role);
  const groups: { title: string; items: Signature[] }[] = [
    { title: "Traits", items: visible.filter((item) => item.genre === "trait") },
    { title: "Remplissages", items: visible.filter((item) => item.genre === "aplat") },
  ];

  function renderOverlay(toScreen: ToScreen): ReactNode {
    if (!selected || !elements.data) {
      return null;
    }
    if (elements.data.segments) {
      return (
        <g className="th-sig-lines">
          {elements.data.segments.map((segment, index) => {
            const [x1, y1] = toScreen([segment[0], segment[1]]);
            const [x2, y2] = toScreen([segment[2], segment[3]]);
            return <line key={index} x1={x1} y1={y1} x2={x2} y2={y2} />;
          })}
        </g>
      );
    }
    const path = (elements.data.polygones ?? [])
      .map((ring) => ring.map((point, index) => `${index ? "L" : "M"}${toScreen([point[0], point[1]]).map((v) => v.toFixed(1)).join(" ")}`).join(" ") + " Z")
      .join(" ");
    return <path className="th-sig-fill" d={path} fillRule="evenodd" />;
  }

  return (
    <div className="th-viewer-layout">
      {sheet && raster.data ? (
        <TileSheetViewer
          manifest={raster.data}
          tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
          tool="pan"
          onAddPoint={() => undefined}
          renderOverlay={renderOverlay}
        />
      ) : (
        <div className="th-viewer th-viewer--empty">
          <p className="th-viewer__status">
            {raster.error
              ? `Affichage impossible : ${raster.error.message}`
              : catalogue.isLoading
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
          <h1 className="th-panel__title">Signatures</h1>
        </div>
        <ProjectTabs projectId={projectId} />
        <p className="th-muted">
          Chaque « calque » de l'architecte laisse une signature dans le PDF : épaisseur et couleur du trait, tirets, teinte de remplissage.
          Donnez une fois son rôle à chaque signature : la détection des pièces, des parois et des menuiseries s'appuiera dessus.
        </p>

        {catalogue.isLoading && <p className="th-muted">Lecture des plans du projet… (quelques secondes par plan la première fois)</p>}
        {catalogue.error && <p className="th-alert th-alert--error">{catalogue.error.message}</p>}
        {save.error && <p className="th-alert th-alert--error">{save.error.message}</p>}

        {data && (
          <>
            <section className="th-sig-summary">
              <strong>
                {data.validees} / {data.total} signatures validées
              </strong>
              <div className="th-sig-progress" role="progressbar" aria-valuemin={0} aria-valuemax={data.total} aria-valuenow={data.validees}>
                <span style={{ width: `${data.total ? (100 * data.validees) / data.total : 0}%` }} />
              </div>
              <div className="th-inline">
                <button
                  type="button"
                  className="po2-button po2-button--secondary"
                  disabled={save.isPending || pending.length === 0}
                  onClick={() => save.mutate(Object.fromEntries(pending.map((item) => [item.cle, item.role_propose])))}
                >
                  Valider les {pending.length} propositions restantes
                </button>
                <label className="th-check">
                  <input type="checkbox" checked={onlyPending} onChange={(event) => setOnlyPending(event.target.checked)} />
                  Seulement à valider
                </label>
              </div>
            </section>

            <label className="th-field">
              <span>Plan affiché</span>
              <select value={currentSheetId ?? ""} onChange={(event) => setSheetId(Number(event.target.value))}>
                {data.planches.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.libelle}
                    {selectedSignature && !selectedSignature.planches.includes(item.id) ? " (signature absente)" : ""}
                  </option>
                ))}
              </select>
            </label>
            {selectedSignature && !presentOnSheet && <p className="th-alert th-alert--warn">Cette signature n'apparaît pas sur ce plan.</p>}
            {selectedSignature && presentOnSheet && elements.isFetching && <p className="th-muted">Repérage sur le plan…</p>}
            {elements.data?.tronque && <p className="th-muted">Signature très présente : seuls les traits les plus longs sont montrés.</p>}

            {groups.map((group) =>
              group.items.length ? (
                <section key={group.title}>
                  <h2>{group.title}</h2>
                  <ul className="th-sig-list">
                    {group.items.map((signature) => {
                      const roles = signature.genre === "trait" ? data.roles_traits : data.roles_aplats;
                      const isSelected = signature.cle === selected;
                      return (
                        <li key={signature.cle} className={`th-sig${isSelected ? " is-selected" : ""}${signature.role ? " is-validated" : ""}`}>
                          <button
                            type="button"
                            className="th-sig__main"
                            aria-pressed={isSelected}
                            onClick={() => setSelected(isSelected ? null : signature.cle)}
                          >
                            <Swatch signature={signature} />
                            <span className="th-sig__text">
                              <strong>{signature.libelle}</strong>
                              <small>{measure(signature)}</small>
                            </span>
                            <span className={signature.role ? "th-sig__state is-ok" : "th-sig__state"}>{signature.role ? "Validé" : "À valider"}</span>
                          </button>
                          <div className="th-sig__role">
                            <select
                              value={signature.role ?? signature.role_propose}
                              disabled={save.isPending}
                              aria-label={`Rôle de la signature ${signature.libelle}`}
                              onChange={(event) => save.mutate({ [signature.cle]: event.target.value })}
                            >
                              {Object.entries(roles).map(([key, label]) => (
                                <option key={key} value={key}>
                                  {label}
                                  {key === signature.role_propose ? " (proposé)" : ""}
                                </option>
                              ))}
                            </select>
                            {signature.role ? (
                              <button type="button" className="th-link" disabled={save.isPending} onClick={() => save.mutate({ [signature.cle]: null })}>
                                Annuler
                              </button>
                            ) : (
                              <button
                                type="button"
                                className="th-link"
                                disabled={save.isPending}
                                onClick={() => save.mutate({ [signature.cle]: signature.role_propose })}
                              >
                                Valider
                              </button>
                            )}
                          </div>
                          {!signature.role && <small className="th-muted">Proposé : {signature.raison}.</small>}
                        </li>
                      );
                    })}
                  </ul>
                </section>
              ) : null,
            )}
          </>
        )}
      </aside>
    </div>
  );
}
