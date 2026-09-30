import { angleDeg, ecartEchellePct, type Alignement } from "./alignement";

// Guide du calage « comme AutoCAD » (D201, D202) : point de base, rotation, longueur — le calque bouge après
// chaque temps, et le bandeau dit ce que fait le prochain clic.

export type EtapeCalage = { titre: string; texte: string; etat: "faite" | "en_cours" | "a_venir" };

const RANG = { base: 0, rotation: 1, longueur: 2, enregistre: 3 } as const;

export function etapesDuCalage(al: Alignement, voisin: string, plan: string, couleur: string): EtapeCalage[] {
  const attente = Boolean(al.enAttente);
  const etapes = [
    {
      titre: "1. Point de base",
      texte: attente
        ? `Cliquez maintenant ce même point sur le ${plan} (plan noir) : le calque va glisser dessus.`
        : `Cliquez un point précis du ${voisin} sur le calque ${couleur} (poteau, angle de mur), puis le même point sur le ${plan} (plan noir).`,
    },
    {
      titre: "2. Rotation",
      texte: attente
        ? `Cliquez sur le ${plan} (plan noir) la direction où ce point doit aller : le calque va tourner autour du point de base.`
        : `Loin du point de base, cliquez un point du calque ${couleur}, puis la direction où il doit aller sur le ${plan}. Alt : sans aimant. Si le calque est déjà dans le bon sens, passez.`,
    },
    {
      titre: "3. Longueur",
      texte: attente
        ? `Cliquez sur le ${plan} (plan noir) l'endroit exact où ce point doit tomber : le calque va s'étirer depuis le point de base.`
        : `Si le calque est trop grand ou trop petit : cliquez un point du calque ${couleur}, loin du point de base, puis l'endroit exact où il doit tomber sur le ${plan}. Sinon, enregistrez.`,
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
  echelle,
  onEnregistrer,
  onGarderRotation,
  onRefaire,
}: {
  al: Alignement;
  voisin: string;
  plan: string;
  couleur: string;
  // Rapport des échelles déclarées : l'écart s'y mesure.
  echelle: number;
  onEnregistrer: () => void;
  onGarderRotation: () => void;
  onRefaire: () => void;
}) {
  const rotation = ((angleDeg(al.sim) % 360) + 360) % 360;
  const ecart = ecartEchellePct(al, echelle);
  return (
    <>
      <strong>
        Caler le {voisin} sur le {plan}
      </strong>
      <p className="th-calage__but">
        Comme la commande Aligner d'AutoCAD : un point commun pour poser le calque, un second pour le tourner, un
        troisième pour ajuster sa longueur.
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
      {(al.etape === "longueur" || al.etape === "enregistre") && (
        <p className="th-calage__but">
          Rotation {format(rotation, 2)}°{al.aimante ? " (aimantée à l'angle droit)" : ""}.{" "}
          {Math.abs(ecart) < 0.05
            ? "Échelle : celle déclarée sur les deux planches."
            : `Échelle : ${ecart > 0 ? "+" : "−"}${format(Math.abs(ecart), 2)} % par rapport aux échelles déclarées${
                Math.abs(ecart) >= 0.3 ? " — l'échelle de l'une des planches est sans doute arrondie (ex. 1/100 au lieu de 1/99,3)" : ""
              }.`}
        </p>
      )}
      <span className="th-calage__actions">
        {al.etape === "rotation" && !al.enAttente && (
          <button type="button" className="po2-button po2-button--ghost" onClick={onGarderRotation}>
            La rotation est déjà bonne
          </button>
        )}
        {al.etape === "longueur" && !al.enAttente && (
          <button type="button" className="po2-button po2-button--primary" disabled={al.busy} onClick={onEnregistrer}>
            {al.busy ? "Enregistrement…" : "Enregistrer le calage"}
          </button>
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
