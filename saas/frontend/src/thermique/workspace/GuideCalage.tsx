import { angleDeg, ecartLongueurPct, type Alignement } from "./alignement";

// Guide du calage « comme AutoCAD » (D201) : point de base, rotation, puis vérification — le calque bouge
// après chaque temps, et le bandeau dit ce que fait le prochain clic.

export type EtapeCalage = { titre: string; texte: string; etat: "faite" | "en_cours" | "a_venir" };

const RANG = { base: 0, rotation: 1, verification: 2, enregistre: 3 } as const;

export function etapesDuCalage(al: Alignement, voisin: string, plan: string, couleur: string): EtapeCalage[] {
  const surCalque = `cliquez un point précis du ${voisin} sur le calque ${couleur}`;
  const etapes = [
    {
      titre: "1. Point de base",
      texte: al.etape === "base" && al.enAttente
        ? `Cliquez maintenant ce même point sur le ${plan} (plan noir) : le calque va glisser dessus.`
        : `${surCalque[0].toUpperCase()}${surCalque.slice(1)} (poteau, angle de mur), puis le même point sur le ${plan} (plan noir).`,
    },
    {
      titre: "2. Rotation",
      texte: al.etape === "rotation" && al.enAttente
        ? `Cliquez sur le ${plan} (plan noir) l'endroit où ce point doit aller : le calque va tourner autour du point de base.`
        : `Loin du point de base, ${surCalque}, puis l'endroit où il doit aller sur le ${plan}. Maintenez Alt pour tourner sans aimant.`,
    },
    {
      titre: "3. Vérifier et enregistrer",
      texte: "Les deux points tombent-ils juste ? Ajustez la longueur si besoin, puis enregistrez.",
    },
  ];
  const courant = RANG[al.etape];
  return etapes.map((etape, rang) => ({
    ...etape,
    etat: rang < courant ? "faite" : rang === courant ? "en_cours" : "a_venir",
  }));
}

const format = (valeur: number, chiffres = 1) =>
  valeur.toLocaleString("fr-FR", { minimumFractionDigits: chiffres, maximumFractionDigits: chiffres });

export function GuideCalage({
  al,
  voisin,
  plan,
  couleur,
  onEnregistrer,
  onAjuster,
  onRefaire,
}: {
  al: Alignement;
  voisin: string;
  plan: string;
  couleur: string;
  onEnregistrer: () => void;
  onAjuster: () => void;
  onRefaire: () => void;
}) {
  const ecart = ecartLongueurPct(al);
  const rotation = ((angleDeg(al.sim) % 360) + 360) % 360;
  return (
    <>
      <strong>
        Caler le {voisin} sur le {plan}
      </strong>
      <p className="th-calage__but">
        Comme la commande Aligner d'AutoCAD : un point commun pour poser le calque, un second point pour le
        tourner. L'échelle vient des échelles déclarées des deux planches.
      </p>
      <ol className="th-calage__etapes">
        {etapesDuCalage(al, voisin, plan, couleur).map((etape) => (
          <li key={etape.titre} className={`th-calage__etape is-${etape.etat}`}>
            <b>
              {etape.etat === "faite" ? "✓ " : ""}
              {etape.titre}
            </b>
            {etape.etat === "en_cours" && <span> · {etape.texte}</span>}
          </li>
        ))}
      </ol>
      {(al.etape === "verification" || al.etape === "enregistre") && (
        <p className="th-calage__but">
          Rotation {format(rotation, 2)}°{al.aimante ? " (aimantée à l'angle droit)" : ""}.{" "}
          {al.longueurAjustee
            ? "Longueur ajustée sur le second point."
            : ecart != null && Math.abs(ecart) >= 0.05
              ? `Le second point tombe ${ecart > 0 ? "trop court" : "trop loin"} de ${format(Math.abs(ecart))} %.`
              : "Le second point tombe juste."}
        </p>
      )}
      <span className="th-calage__actions">
        {al.etape === "verification" && (
          <>
            <button type="button" className="po2-button po2-button--primary" disabled={al.busy} onClick={onEnregistrer}>
              {al.busy ? "Enregistrement…" : "Enregistrer le calage"}
            </button>
            {!al.longueurAjustee && ecart != null && Math.abs(ecart) >= 0.05 && (
              <button type="button" className="th-link" disabled={al.busy} onClick={onAjuster}>
                Ajuster aussi la longueur
              </button>
            )}
          </>
        )}
        {al.etape !== "enregistre" && (al.etape !== "base" || al.enAttente) && (
          <button type="button" className="th-link" disabled={al.busy} onClick={onRefaire}>
            Refaire l'étape
          </button>
        )}
      </span>
    </>
  );
}
