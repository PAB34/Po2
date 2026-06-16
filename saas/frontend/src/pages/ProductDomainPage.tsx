import { Link } from "react-router-dom";

type DomainKey = "patrimoine" | "marches" | "technique" | "administration";

type DomainAction = {
  title: string;
  meta: string;
  to: string;
  tone?: "energie" | "patrimoine" | "marches" | "technique" | "admin";
};

type DomainSection = {
  title: string;
  actions: DomainAction[];
};

type DomainConfig = {
  eyebrow: string;
  title: string;
  lead: string;
  primary: DomainAction;
  sections: DomainSection[];
};

const DOMAINS: Record<DomainKey, DomainConfig> = {
  patrimoine: {
    eyebrow: "Base maitre",
    title: "Patrimoine",
    lead: "Sites, batiments, locaux, compteurs et rattachements.",
    primary: { title: "Sites et batiments", meta: "Referentiel central", to: "/buildings/list", tone: "patrimoine" },
    sections: [
      {
        title: "Parcours quotidiens",
        actions: [
          { title: "Sites et batiments", meta: "liste, filtres, fiches", to: "/buildings/list", tone: "patrimoine" },
          { title: "Rattachements compteurs", meta: "PRM, PCE, eau", to: "/buildings/compteurs", tone: "energie" },
          { title: "Carte du patrimoine", meta: "vue geographique", to: "/buildings", tone: "patrimoine" },
        ],
      },
      {
        title: "Actions expertes",
        actions: [
          { title: "Import patrimoine", meta: "DGFiP, IGN, OSM", to: "/buildings/create-edit", tone: "admin" },
          { title: "Fiches batiments", meta: "locaux, compteurs, equipements", to: "/buildings/list", tone: "patrimoine" },
        ],
      },
    ],
  },
  marches: {
    eyebrow: "Contrats et finances",
    title: "Marches & contrats",
    lead: "CPE DALKIA, factures marche, performance et futurs contrats de maintenance.",
    primary: { title: "CPE DALKIA", meta: "P1, P2, P3, factures, performance", to: "/cpe", tone: "marches" },
    sections: [
      {
        title: "CPE DALKIA",
        actions: [
          { title: "Vue marche", meta: "sites, bilan, atterrissage", to: "/cpe", tone: "marches" },
          { title: "Factures et controle", meta: "decision, liaison finance", to: "/cpe", tone: "marches" },
          { title: "Sites CPE", meta: "consommations et detail site", to: "/cpe", tone: "marches" },
        ],
      },
      {
        title: "Referentiels",
        actions: [
          { title: "Import referentiel DALKIA", meta: "acte, DPGF, versions", to: "/cpe/dalkia-import", tone: "admin" },
          { title: "Travaux P3/P6", meta: "devis et engagements", to: "/cpe", tone: "marches" },
          { title: "SPIE", meta: "maintenance a cadrer", to: "/technique", tone: "technique" },
        ],
      },
    ],
  },
  technique: {
    eyebrow: "Terrain et conformite",
    title: "Technique",
    lead: "Inventaires CVC, equipements, fluides, ESP et couverture technique.",
    primary: { title: "Inventaire & CVC", meta: "equipements terrain", to: "/buildings/technique", tone: "technique" },
    sections: [
      {
        title: "Inventaires",
        actions: [
          { title: "Inventaire & CVC", meta: "DALKIA, SPIE, equipements", to: "/buildings/technique", tone: "technique" },
          { title: "Import CVC terrain", meta: "lots et items", to: "/buildings/cvc-import", tone: "admin" },
          { title: "Rattachement CVC", meta: "source terrain vers patrimoine", to: "/buildings/cvc-import/batiments", tone: "technique" },
        ],
      },
      {
        title: "Conformite",
        actions: [
          { title: "Fluides & ESP", meta: "F-Gaz, CO2eq, actions", to: "/buildings/cvc-fluides", tone: "technique" },
          { title: "Rapport technique", meta: "couverture par batiment", to: "/buildings/cvc-rapport-technique", tone: "technique" },
        ],
      },
    ],
  },
  administration: {
    eyebrow: "Pilotage expert",
    title: "Administration",
    lead: "Imports, referentiels, connecteurs, matrices comptables et compte utilisateur.",
    primary: { title: "Mon compte", meta: "profil et mot de passe", to: "/account", tone: "admin" },
    sections: [
      {
        title: "Referentiels",
        actions: [
          { title: "Prix fournisseurs", meta: "configuration tarifaire", to: "/energie/facturation", tone: "energie" },
          { title: "BPU et TURPE", meta: "prix contractuels", to: "/energie/bpu", tone: "energie" },
          { title: "Referentiel DALKIA", meta: "acte et versions", to: "/cpe/dalkia-import", tone: "marches" },
        ],
      },
      {
        title: "Imports et connecteurs",
        actions: [
          { title: "Patrimoine", meta: "DGFiP, IGN, OSM", to: "/buildings/create-edit", tone: "patrimoine" },
          { title: "Donnees ENEDIS", meta: "sync et qualite", to: "/energie/donnees", tone: "energie" },
          { title: "Import CVC", meta: "terrain DALKIA/SPIE", to: "/buildings/cvc-import", tone: "technique" },
        ],
      },
    ],
  },
};

export function ProductDomainPage({ domain }: { domain: DomainKey }) {
  const config = DOMAINS[domain];

  return (
    <section className="product-domain">
      <header className="product-domain-hero">
        <div>
          <p className="product-domain-eyebrow">{config.eyebrow}</p>
          <h2>{config.title}</h2>
          <p>{config.lead}</p>
        </div>
        <Link className={`product-domain-primary product-domain-card--${config.primary.tone}`} to={config.primary.to}>
          <span>{config.primary.meta}</span>
          <strong>{config.primary.title}</strong>
        </Link>
      </header>

      <div className="product-domain-grid">
        {config.sections.map((section) => (
          <section key={section.title} className="product-domain-section">
            <h3>{section.title}</h3>
            <div className="product-domain-actions">
              {section.actions.map((action) => (
                <Link
                  key={`${action.title}-${action.to}`}
                  className={`product-domain-card product-domain-card--${action.tone ?? "admin"}`}
                  to={action.to}
                >
                  <span>{action.meta}</span>
                  <strong>{action.title}</strong>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
