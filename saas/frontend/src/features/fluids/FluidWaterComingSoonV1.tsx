import { Card } from "../../design-system";

export function FluidWaterComingSoonV1() {
  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">Détail fluide · Eau (SUEZ)</span>
        <h1>Eau — SUEZ</h1>
        <p>Le fluide est visible dans l'architecture, mais aucune donnée n'est inventée.</p>
      </header>
      <Card className="po2-fluid-todo" title="La fenêtre eau est prévue, sans données fictives." eyebrow="À construire">
        <p>
          Même trame que les autres distributeurs : volumes en m³, couverture, détection de fuites
          (talon permanent) et surveillance des contrats. Elle s'activera dès qu'un export ou un
          connecteur distributeur SUEZ réel sera disponible.
        </p>
        <p>
          Sections prévues : volumes m³ &amp; saisonnalité · détection de fuites · couverture &amp;
          rattachement aux sites · surveillance des contrats (diamètre, abonnement, débits de pointe
          vs tarif SUEZ).
        </p>
      </Card>
    </div>
  );
}
