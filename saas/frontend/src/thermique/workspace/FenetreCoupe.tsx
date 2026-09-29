import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";

import { thermiqueApi, type PdfPoint, type Sheet, type VueCoupe } from "../api";
import { TileSheetViewer } from "../components/TileSheetViewer";
import { hauteursQueryKey } from "./study";

const M_PAR_PT = 0.0254 / 72;

/** Hauteur (m) entre deux clics, mesurée le long du haut de la vue, à l'échelle de sa planche (D191). */
export function hauteurEntreClics(sol: PdfPoint, plafond: PdfPoint, haut: [number, number], echelle: number): number {
  const norme = Math.hypot(haut[0], haut[1]) || 1;
  const hx = haut[0] / norme;
  const hy = haut[1] / norme;
  return ((plafond[0] - sol[0]) * hx + (plafond[1] - sol[1]) * hy) * M_PAR_PT * echelle;
}

/** Cadrage d'une vue : son centre, et le zoom (multiple du cadrage ajusté) qui la fait tenir dans la fenêtre. */
export function cadrageDeLaVue(vue: VueCoupe, planche: Sheet): { point: PdfPoint; zoom: number } {
  const [x0, y0, x1, y1] = vue.cadre;
  const tourne = planche.rotation_deg % 180 !== 0;
  const largeur = tourne ? planche.page_height_pt : planche.page_width_pt;
  const hauteur = tourne ? planche.page_width_pt : planche.page_height_pt;
  const w = Math.abs(x1 - x0) || 1;
  const h = Math.abs(y1 - y0) || 1;
  const zoom = Math.max(1, Math.min(largeur / (tourne ? h : w), hauteur / (tourne ? w : h)) * 0.9);
  return { point: [(x0 + x1) / 2, (y0 + y1) / 2], zoom };
}

type Etat = { etape: "aucune" } | { etape: "sol" } | { etape: "plafond"; sol: PdfPoint };

/** La coupe dans une fenêtre flottante au-dessus du plan (D183) ; deux clics y confirment la hauteur (D191). */
export function FenetreCoupe({
  token,
  vue,
  planche,
  planSheetId,
  onClose,
}: {
  token: string;
  vue: VueCoupe;
  planche: Sheet;
  planSheetId: number | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const raster = useQuery({
    queryKey: ["thermique", "raster", planche.id, planche.rotation_deg],
    queryFn: () => thermiqueApi.getRaster(token, planche.id, planche.rotation_deg),
  });
  const [etat, setEtat] = useState<Etat>({ etape: "aucune" });
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [position, setPosition] = useState({ x: 80, y: 90 });
  const glisse = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const cadrage = cadrageDeLaVue(vue, planche);
  const echelle = planche.scale_denominator;

  const cliquer = async (point: PdfPoint) => {
    if (etat.etape === "sol") {
      setEtat({ etape: "plafond", sol: point });
      setMessage("Cliquez maintenant le plafond fini de la même pièce.");
      return;
    }
    if (etat.etape !== "plafond" || !echelle) return;
    const hauteur = hauteurEntreClics(etat.sol, point, vue.haut, echelle);
    setBusy(true);
    try {
      await thermiqueApi.confirmerHauteur(token, vue.id, etat.sol, point);
      setMessage(`Hauteur de l'étage confirmée : ${hauteur.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} m.`);
      void queryClient.invalidateQueries({ queryKey: hauteursQueryKey(planSheetId) });
      void queryClient.invalidateQueries({ queryKey: ["thermique", "vues"] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "La confirmation a échoué.");
    } finally {
      setBusy(false);
      setEtat({ etape: "aucune" });
    }
  };

  const deplacer = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!glisse.current) return;
    setPosition({ x: glisse.current.px + event.clientX - glisse.current.x, y: glisse.current.py + event.clientY - glisse.current.y });
  };

  return (
    <div className="th-fenetre-coupe" style={{ left: position.x, top: position.y }} role="dialog" aria-label={`Coupe ${vue.nom}`}>
      <div
        className="th-fenetre-coupe__titre"
        onPointerDown={(event) => {
          glisse.current = { x: event.clientX, y: event.clientY, px: position.x, py: position.y };
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={deplacer}
        onPointerUp={() => {
          glisse.current = null;
        }}
      >
        <strong>{vue.nom}</strong>
        <span className="th-muted"> · {planche.label}</span>
        <button type="button" className="po2-button po2-button--ghost" onClick={onClose} aria-label="Fermer la coupe">
          ×
        </button>
      </div>
      <div className="th-fenetre-coupe__outils">
        <button
          type="button"
          className="po2-button po2-button--ghost"
          disabled={busy || !echelle}
          title={echelle ? undefined : "L'échelle de la planche de coupes n'est pas définie."}
          onClick={() => {
            setEtat({ etape: "sol" });
            setMessage("Cliquez le sol fini d'une pièce coupée, puis son plafond fini.");
          }}
        >
          Confirmer la hauteur
        </button>
        {(vue.corrections ?? []).length > 0 && (
          <small className="th-muted">
            Confirmé : {(vue.corrections ?? []).map((c) => `${c.hauteur_m.toLocaleString("fr-FR")} m`).join(", ")}
          </small>
        )}
      </div>
      {message && <p className="th-fenetre-coupe__message">{message}</p>}
      <div className="th-fenetre-coupe__plan">
        {raster.data ? (
          <TileSheetViewer
            manifest={raster.data}
            tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
            tool={etat.etape === "aucune" ? "pan" : "measure"}
            points={etat.etape === "plafond" ? [etat.sol] : []}
            onAddPoint={(point) => void cliquer(point)}
            focus={{ point: cadrage.point, cle: `vue-${vue.id}`, zoom: cadrage.zoom }}
          />
        ) : (
          <p className="th-muted">Chargement de la coupe…</p>
        )}
      </div>
    </div>
  );
}
