import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";

import { thermiqueApi, type HautDeVue, type MenuiseriesDuProjet, type PdfPoint, type Sheet, type VueCoupe } from "../api";
import { TileSheetViewer } from "../components/TileSheetViewer";
import { mesureDeDeuxCoins, proposerComposants } from "./baies";
import { avisSurLaHauteur, avisSurLaMenuiserie, rectangleDeMenuiserie, segmentDeHauteur } from "./mesuresVue";
import { modelesDeLaVue } from "./CadresDesVues";
import { ModeleDeMenuiserie } from "./ModelesMenuiseries";
import { pageDuCoteEcran, rotationALEndroit } from "./orientation";
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
export function cadrageDeLaVue(vue: VueCoupe, planche: Sheet, rotation = planche.rotation_deg): { point: PdfPoint; zoom: number } {
  const [x0, y0, x1, y1] = vue.cadre;
  const tourne = rotation % 180 !== 0;
  const largeur = tourne ? planche.page_height_pt : planche.page_width_pt;
  const hauteur = tourne ? planche.page_width_pt : planche.page_height_pt;
  const w = Math.abs(x1 - x0) || 1;
  const h = Math.abs(y1 - y0) || 1;
  const zoom = Math.max(1, Math.min(largeur / (tourne ? h : w), hauteur / (tourne ? w : h)) * 0.9);
  return { point: [(x0 + x1) / 2, (y0 + y1) / 2], zoom };
}

/** Après deux coins sur une façade : la mesure, et à quoi l'appliquer (D193, D194, D200). */
export function ChoixMenuiserie({
  largeurM,
  hauteurM,
  menuiseries,
  busy = false,
  onChoisir,
  onAnnuler,
}: {
  largeurM: number;
  hauteurM: number;
  menuiseries?: MenuiseriesDuProjet;
  busy?: boolean;
  onChoisir: (composant: string, largeurCm: number | null) => void;
  onAnnuler: () => void;
}) {
  const propositions = proposerComposants(menuiseries, largeurM * 100);
  const format = (v: number) => v.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
  return (
    <div className="th-fenetre-coupe__choix">
      <p>
        Menuiserie mesurée : <strong>{format(largeurM)} m</strong> de large, <strong>{format(hauteurM)} m</strong> de haut.
      </p>
      {avisSurLaMenuiserie(largeurM, hauteurM) && <p className="th-alert th-alert--warn">{avisSurLaMenuiserie(largeurM, hauteurM)}</p>}
      {propositions.length === 0 ? (
        <p className="th-alert th-alert--warn">
          Aucune baie du projet n'a cette largeur à ± 5 cm : vérifiez les deux coins, ou la baie dans le relevé.
        </p>
      ) : (
        <ul>
          {propositions.map((p) => (
            <li key={p.composant}>
              <span>
                {p.composant} (baie de {p.baie.largeur_cm.toLocaleString("fr-FR")} cm, écart {p.ecart_cm.toLocaleString("fr-FR")} cm)
              </span>
              <button type="button" className="po2-button po2-button--primary" disabled={busy} onClick={() => onChoisir(p.composant, null)}>
                Pour toutes les {p.composant}
              </button>
              <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={() => onChoisir(p.composant, p.baie.largeur_cm)}>
                Pour cette baie seule
              </button>
            </li>
          ))}
        </ul>
      )}
      <button type="button" className="th-link" onClick={onAnnuler}>
        Annuler
      </button>
    </div>
  );
}

type Etat =
  | { etape: "aucune" }
  | { etape: "sol" }
  | { etape: "plafond"; sol: PdfPoint }
  // Façade (S5e, D193) : deux coins opposés d'une menuiserie, puis le choix de ce à quoi la hauteur s'applique.
  | { etape: "coin1" }
  | { etape: "coin2"; a: PdfPoint }
  | { etape: "choix"; coins: [PdfPoint, PdfPoint]; largeur_m: number; hauteur_m: number }
  // Hauteur mesurée, montrée avant d'être appliquée (D211) : on la vérifie, puis on choisit où la poser.
  | { etape: "hauteur"; sol: PdfPoint; plafond: PdfPoint; hauteur_m: number };

/** Ce qui se mesure dans la fenêtre (D214) : une hauteur d'étage ou une menuiserie, sur n'importe quelle vue. */
export type OutilDeMesure = "hauteur" | "menuiserie";

const CONSIGNES: Record<OutilDeMesure, string> = {
  hauteur: "Cliquez le sol fini d'une pièce coupée, puis son plafond fini.",
  menuiserie: "Cliquez un coin d'une menuiserie, puis le coin opposé.",
};

/** La liste des vues du projet, rangées en coupes et élévations (D214). */
export function ChoixDeLaVue({ vues, vueId, onChoisir }: { vues: VueCoupe[]; vueId: number; onChoisir: (vueId: number) => void }) {
  const groupes: { label: string; vues: VueCoupe[] }[] = [
    { label: "Coupes", vues: vues.filter((v) => v.nature === "coupe") },
    { label: "Élévations", vues: vues.filter((v) => v.nature === "facade") },
  ];
  return (
    <select
      className="th-fenetre-coupe__choix-vue"
      aria-label="Vue affichée"
      value={vueId}
      onChange={(event) => onChoisir(Number(event.target.value))}
    >
      {groupes
        .filter((groupe) => groupe.vues.length > 0)
        .map((groupe) => (
          <optgroup key={groupe.label} label={groupe.label}>
            {groupe.vues.map((v) => (
              <option key={v.id} value={v.id}>
                {v.nom}
              </option>
            ))}
          </optgroup>
        ))}
    </select>
  );
}

/** La fenêtre « Coupes et élévations » au-dessus du plan (D183, D214) : choisir une vue, y mesurer. */
export function FenetreCoupe({
  token,
  vue,
  vues = [],
  onChoisirVue,
  planche,
  planSheetId,
  menuiseries,
  outilPrefere,
  outilArme = null,
  onPoserHauteur,
  onPoserModele,
  onClose,
}: {
  token: string;
  vue: VueCoupe;
  /** Toutes les vues du projet, au choix (D214). */
  vues?: VueCoupe[];
  onChoisirVue?: (vueId: number) => void;
  planche: Sheet;
  planSheetId: number | null;
  /** Baies du projet, pour proposer le composant de la menuiserie mesurée sur une façade (S5e). */
  menuiseries?: MenuiseriesDuProjet;
  /** La mesure de l'étape en cours, mise en avant (D214). */
  outilPrefere?: OutilDeMesure;
  /** Ouverte depuis une fiche : la mesure démarre aussitôt ; `fois` change à chaque demande. */
  outilArme?: { outil: OutilDeMesure; fois: number } | null;
  /** Pose la hauteur mesurée sur les locaux que le thermicien cliquera sur le plan (D211). */
  onPoserHauteur?: (hauteur: number) => void;
  /** Pose le modèle mesuré sur les menuiseries que le thermicien cliquera sur le plan (D220). */
  onPoserModele?: (modele: { nom: string; largeur_cm: number; hauteur_m: number }) => void;
  onClose: () => void;
}) {
  const [survol, setSurvol] = useState<PdfPoint | null>(null);
  const facade = vue.nature === "facade";
  const queryClient = useQueryClient();
  const base = useQuery({
    queryKey: ["thermique", "raster", planche.id, planche.rotation_deg],
    queryFn: () => thermiqueApi.getRaster(token, planche.id, planche.rotation_deg),
  });
  // La vue s'ouvre à l'endroit, son haut en haut de l'écran (D208) : largeur à l'horizontale, hauteur à la verticale.
  const rotation = base.data ? rotationALEndroit(vue.haut, base.data.transform, planche.rotation_deg) : planche.rotation_deg;
  const tournee = useQuery({
    queryKey: ["thermique", "raster", planche.id, rotation],
    queryFn: () => thermiqueApi.getRaster(token, planche.id, rotation),
    enabled: Boolean(base.data) && rotation !== planche.rotation_deg,
  });
  const raster = rotation === planche.rotation_deg ? base : tournee;
  const [etat, setEtat] = useState<Etat>({ etape: "aucune" });
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [position, setPosition] = useState({ x: 80, y: 90 });
  const glisse = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const cadrage = cadrageDeLaVue(vue, planche, rotation);
  const echelle = planche.scale_denominator;

  const demarrer = (outil: OutilDeMesure) => {
    setEtat(outil === "hauteur" ? { etape: "sol" } : { etape: "coin1" });
    setMessage(CONSIGNES[outil]);
  };
  // Demandée depuis une fiche, la mesure démarre aussitôt (D214).
  useEffect(() => {
    if (outilArme) demarrer(outilArme.outil);
  }, [outilArme?.fois]); // eslint-disable-line react-hooks/exhaustive-deps
  // Une autre vue choisie : la mesure commencée repart de zéro, avec le même outil.
  const vuePrecedente = useRef(vue.id);
  useEffect(() => {
    if (vuePrecedente.current === vue.id) return;
    vuePrecedente.current = vue.id;
    setSurvol(null);
    if (etat.etape === "sol" || etat.etape === "plafond" || etat.etape === "hauteur") demarrer("hauteur");
    else if (etat.etape === "coin1" || etat.etape === "coin2" || etat.etape === "choix") demarrer("menuiserie");
    else setMessage(null);
  }, [vue.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const redresser = async (cote: HautDeVue) => {
    if (!raster.data || cote === "haut") return;
    if (!facade && !window.confirm("Changer le haut d'une coupe efface les pièces lues : elle devra être relue. Continuer ?")) return;
    setBusy(true);
    try {
      await thermiqueApi.corrigerVue(token, vue.id, { haut: pageDuCoteEcran(cote, raster.data.transform) });
      await queryClient.invalidateQueries({ queryKey: ["thermique", "vues"] });
      void queryClient.invalidateQueries({ queryKey: ["thermique", "hauteurs"] });
      setMessage("Vue remise à l'endroit.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Le haut n'a pas été enregistré.");
    } finally {
      setBusy(false);
      setEtat({ etape: "aucune" });
    }
  };

  // D219 : la mesure devient un modèle nommé, capturé, puis posé sur les menuiseries du plan (D220).
  const enregistrerModele = async (coins: [PdfPoint, PdfPoint], nom: string) => {
    setBusy(true);
    try {
      const modele = await thermiqueApi.enregistrerModele(token, vue.id, coins, nom);
      await queryClient.invalidateQueries({ queryKey: ["thermique", "menuiseries"] });
      void queryClient.invalidateQueries({ queryKey: ["thermique", "vues"] });
      onPoserModele?.({ nom: modele.modele, largeur_cm: modele.largeur_mesuree_cm, hauteur_m: modele.hauteur_m });
      setMessage(
        `Modèle « ${modele.modele} » enregistré (${Math.round(modele.largeur_mesuree_cm)} × ${Math.round(modele.hauteur_m * 100)} cm)` +
          (onPoserModele ? " : cliquez sur le plan les menuiseries de ce modèle." : "."),
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "L'enregistrement du modèle a échoué.");
    } finally {
      setBusy(false);
      setEtat({ etape: "aucune" });
    }
  };

  const cliquer = async (point: PdfPoint) => {
    if (etat.etape === "coin1") {
      setEtat({ etape: "coin2", a: point });
      setMessage("Cliquez maintenant le coin opposé de la même menuiserie.");
      return;
    }
    if (etat.etape === "coin2") {
      if (!echelle) return;
      const mesure = mesureDeDeuxCoins(etat.a, point, vue.haut, echelle);
      setEtat({ etape: "choix", coins: [etat.a, point], ...mesure });
      setMessage(null);
      return;
    }
    if (etat.etape === "sol") {
      setEtat({ etape: "plafond", sol: point });
      setMessage("Cliquez maintenant le plafond fini de la même pièce.");
      return;
    }
    if (etat.etape !== "plafond" || !echelle) return;
    setEtat({ etape: "hauteur", sol: etat.sol, plafond: point, hauteur_m: hauteurEntreClics(etat.sol, point, vue.haut, echelle) });
    setMessage(null);
  };

  // La hauteur corrige la lecture de la coupe : les pièces lues posées sur ce sol (D191).
  const corrigerLaCoupe = async (sol: PdfPoint, plafond: PdfPoint, hauteur: number) => {
    setBusy(true);
    try {
      await thermiqueApi.confirmerHauteur(token, vue.id, sol, plafond);
      setMessage(`Hauteur de l'étage confirmée dans la coupe : ${hauteur.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} m.`);
      void queryClient.invalidateQueries({ queryKey: hauteursQueryKey(planSheetId) });
      void queryClient.invalidateQueries({ queryKey: ["thermique", "vues"] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "La confirmation a échoué.");
    } finally {
      setBusy(false);
      setEtat({ etape: "aucune" });
    }
  };

  // Ce qui se dessine pendant la mesure (D211).
  const apercu =
    !echelle
      ? []
      : etat.etape === "coin2" && survol
        ? rectangleDeMenuiserie(etat.a, survol, vue.haut, echelle)
        : etat.etape === "choix"
          ? rectangleDeMenuiserie(etat.coins[0], etat.coins[1], vue.haut, echelle)
          : etat.etape === "plafond" && survol
            ? [segmentDeHauteur(etat.sol, survol, vue.haut, echelle)]
            : etat.etape === "hauteur"
              ? [segmentDeHauteur(etat.sol, etat.plafond, vue.haut, echelle)]
              : [];
  // D232 : les menuiseries déjà mesurées sur cette vue restent dessinées, avec le nom de leur modèle.
  const mesurees = echelle
    ? modelesDeLaVue(vue).flatMap((modele) =>
        rectangleDeMenuiserie(modele.coins[0], modele.coins[1], vue.haut, echelle).map((segment, rang) => ({
          ...segment,
          tone: "reference" as const,
          label: rang === 0 ? modele.nom : undefined,
        })),
      )
    : [];
  const avis = etat.etape === "hauteur" ? avisSurLaHauteur(etat.hauteur_m) : null;
  const piecesLues = (vue.pieces ?? []).length > 0;

  const deplacer = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!glisse.current) return;
    setPosition({ x: glisse.current.px + event.clientX - glisse.current.x, y: glisse.current.py + event.clientY - glisse.current.y });
  };

  return (
    <div className="th-fenetre-coupe" style={{ left: position.x, top: position.y }} role="dialog" aria-label="Coupes et élévations">
      <div
        className="th-fenetre-coupe__titre"
        onPointerDown={(event) => {
          // Capturer le pointeur sur un bouton (la croix) ou la liste volerait son clic.
          if ((event.target as HTMLElement).closest("button, select")) return;
          glisse.current = { x: event.clientX, y: event.clientY, px: position.x, py: position.y };
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={deplacer}
        onPointerUp={() => {
          glisse.current = null;
        }}
      >
        {vues.length > 1 && onChoisirVue ? (
          <ChoixDeLaVue vues={vues} vueId={vue.id} onChoisir={onChoisirVue} />
        ) : (
          <strong>{vue.nom}</strong>
        )}
        <span className="th-muted"> · {planche.label}</span>
        <button type="button" className="po2-button po2-button--ghost" onClick={onClose} aria-label="Fermer la fenêtre">
          ×
        </button>
      </div>
      <div className="th-fenetre-coupe__outils">
        {(["hauteur", "menuiserie"] as OutilDeMesure[]).map((outil) => {
          const prefere = outilPrefere ? outil === outilPrefere : outil === (facade ? "menuiserie" : "hauteur");
          return (
            <button
              key={outil}
              type="button"
              className={`po2-button ${prefere ? "po2-button--primary" : "po2-button--ghost"}`}
              disabled={busy || !echelle}
              title={echelle ? undefined : "L'échelle de la planche n'est pas définie."}
              onClick={() => demarrer(outil)}
            >
              {outil === "hauteur" ? "Mesurer une hauteur" : "Mesurer une menuiserie"}
            </button>
          );
        })}
        <label className="th-inline" title="Si le dessin s'affiche couché ou à l'envers, dites où se trouve son haut : la vue se redresse.">
          Dessin de travers ? Son haut est
          <select value="haut" disabled={busy || !raster.data} onChange={(event) => void redresser(event.target.value as HautDeVue)}>
            <option value="haut">en haut (bon sens)</option>
            <option value="droite">à droite</option>
            <option value="bas">en bas</option>
            <option value="gauche">à gauche</option>
          </select>
        </label>
        {!facade && (vue.corrections ?? []).length > 0 && (
          <small className="th-muted">
            Confirmé : {(vue.corrections ?? []).map((c) => `${c.hauteur_m.toLocaleString("fr-FR")} m`).join(", ")}
          </small>
        )}
      </div>
      {message && <p className="th-fenetre-coupe__message">{message}</p>}
      {etat.etape === "hauteur" && (
        <div className="th-fenetre-coupe__choix">
          {avis?.bloquant ? (
            <p className="th-alert th-alert--error">{avis.texte}</p>
          ) : (
            <>
              <p>
                Hauteur mesurée : <strong>{etat.hauteur_m.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} m</strong>.
              </p>
              {avis && <p className="th-alert th-alert--warn">{avis.texte}</p>}
              <div className="th-fenetre-coupe__actions">
                {onPoserHauteur && (
                  <button
                    type="button"
                    className="po2-button po2-button--primary"
                    disabled={busy}
                    onClick={() => {
                      onPoserHauteur(Math.round(etat.hauteur_m * 1000) / 1000);
                      setEtat({ etape: "aucune" });
                      setMessage("Cliquez maintenant, sur le plan, les locaux qui ont cette hauteur.");
                    }}
                  >
                    Poser sur des locaux du plan
                  </button>
                )}
                <button
                  type="button"
                  className="po2-button po2-button--ghost"
                  disabled={busy || !piecesLues}
                  title={piecesLues ? "Corrige les pièces lues de la coupe posées sur ce sol." : "La coupe n'a pas de pièces lues : posez la hauteur sur les locaux du plan."}
                  onClick={() => void corrigerLaCoupe(etat.sol, etat.plafond, etat.hauteur_m)}
                >
                  Corriger les pièces lues de la coupe
                </button>
              </div>
            </>
          )}
          <button
            type="button"
            className="th-link"
            onClick={() => {
              setEtat({ etape: "sol" });
              setMessage("Cliquez le sol fini d'une pièce coupée, puis son plafond fini.");
            }}
          >
            Refaire la mesure
          </button>
        </div>
      )}
      {etat.etape === "choix" && (
        <ModeleDeMenuiserie
          key={`${etat.coins[0].join()}-${etat.coins[1].join()}`}
          largeurM={etat.largeur_m}
          hauteurM={etat.hauteur_m}
          menuiseries={menuiseries}
          busy={busy}
          onEnregistrer={(nom) => void enregistrerModele(etat.coins, nom)}
          onAnnuler={() => {
            setEtat({ etape: "aucune" });
            setMessage(null);
          }}
        />
      )}
      <div className="th-fenetre-coupe__plan">
        {raster.data ? (
          <TileSheetViewer
            manifest={raster.data}
            tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
            tool={etat.etape === "aucune" || etat.etape === "choix" || etat.etape === "hauteur" ? "pan" : "measure"}
            points={
              etat.etape === "plafond"
                ? [etat.sol]
                : etat.etape === "coin2"
                  ? [etat.a]
                  : etat.etape === "choix"
                    ? etat.coins
                    : etat.etape === "hauteur"
                      ? [etat.sol, etat.plafond]
                      : []
            }
            segments={[...mesurees, ...apercu]}
            onHover={(point) => setSurvol(point)}
            onAddPoint={(point) => void cliquer(point)}
            focus={{ point: cadrage.point, cle: `vue-${vue.id}-${rotation}`, zoom: cadrage.zoom }}
          />
        ) : (
          <p className="th-muted">Chargement de la coupe…</p>
        )}
      </div>
    </div>
  );
}
