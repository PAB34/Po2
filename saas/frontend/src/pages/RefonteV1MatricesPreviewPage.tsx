import { Button, Card, DataTable, KpiCard, StatusBadge } from "../design-system";

const previewSuppliers = [
  {
    supplier: "DALKIA",
    domain: "Marches / CPE",
    status: "prioritaire",
    detection: "Code contrat + poste facture + service vendu + periode de marche.",
    risk: "P3.4, prestations a ventiler, ancien marche avant octobre 2025.",
    action: "Exporter la matrice, faire completer par la compta, reimporter en brouillon.",
  },
  {
    supplier: "ENGIE",
    domain: "Fluides electricite",
    status: "a raccorder",
    detection: "PRM/site + composante facture + segment C2/C4/C5 + periode.",
    risk: "Ne pas melanger controle BPU/TURPE et imputation comptable.",
    action: "Reutiliser le parser XLSX et les composants normalises existants.",
  },
  {
    supplier: "EDF",
    domain: "Fluides electricite",
    status: "a raccorder",
    detection: "PRM/site + composante facture + lot/marche + avoir ou facture.",
    risk: "Avoirs, periodes anciennes et periodes manquantes dans les exports reels.",
    action: "Securiser historique/reimport avant validation automatique.",
  },
  {
    supplier: "TOTALENERGIES",
    domain: "Fluides gaz",
    status: "bon candidat",
    detection: "PCE/site + composante gaz + taxe/acheminement/fourniture + periode.",
    risk: "Sites sans libelle mais PCE present ; avoirs gaz a isoler.",
    action: "Brancher la trace gaz deja produite par le moteur TotalEnergies.",
  },
];

const previewRows = [
  { line: 14, key: "DALKIA|P1|GAZ|BEAUX-ARTS", status: "modifie", message: "Nature comptable completee par la comptabilite." },
  { line: 27, key: "ENGIE|TURPE|PRM-142", status: "ajout", message: "Nouvelle regle issue d'une ligne recurrente." },
  { line: 41, key: "EDF|ABONNEMENT|PRM-088", status: "ok", message: "Identique a la reference active." },
  { line: 52, key: "TOTAL|ACCISE|PCE-334", status: "erreurs", message: "Service ou fonction comptable manquant." },
];

function toneForStatus(status: string) {
  if (status === "ok") return "ok" as const;
  if (status === "modifie") return "warn" as const;
  if (status === "erreurs") return "bad" as const;
  return "info" as const;
}

export function RefonteV1MatricesPreviewPage() {
  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">Preview UX sans backend</span>
        <h1>Configurer les matrices comptables par tiers facturant</h1>
        <p>
          Cette page sert a valider l'experience utilisateur quand l'API locale n'est pas demarree. La route raccordee aux
          donnees reelles reste <code>/refonte-v1/matrices</code>.
        </p>
      </header>

      <div className="po2-kpi-grid">
        <KpiCard label="Tiers a traiter" value="4" detail="DALKIA, ENGIE, EDF, TotalEnergies" />
        <KpiCard label="Mode" value="preview" detail="aucune ecriture en base" tone="warning" />
        <KpiCard label="Aller-retour XLSX" value="cible" detail="export compta puis import retour" />
        <KpiCard label="Backend" value="absent" detail="API locale non lancee" tone="warning" />
      </div>

      <Card title="Parcours cible" eyebrow="ce que l'ecran doit faire une fois raccorde">
        <div className="po2-matrix-setup-flow">
          {[
            ["1. Import facture", "Importer un export representatif du tiers facturant.", "socle"],
            ["2. Detection recurrente", "Identifier les lignes qui reviennent et doivent etre codifiees.", "socle"],
            ["3. Export compta", "Produire un XLSX lisible et remplissable par le service comptabilite.", "a faire"],
            ["4. Import retour", "Comparer le fichier complete avec la reference et bloquer les erreurs.", "a faire"],
            ["5. Activation", "Activer une version datee qui s'applique aux nouvelles factures.", "ensuite"],
          ].map(([label, detail, status]) => (
            <article key={label} className="po2-matrix-setup-step">
              <StatusBadge tone={status === "socle" ? "ok" : status === "a faire" ? "warn" : "neutral"}>{status}</StatusBadge>
              <strong>{label}</strong>
              <small>{detail}</small>
            </article>
          ))}
        </div>
      </Card>

      <Card title="Tiers facturants" eyebrow="vision refonte V1">
        <div className="po2-matrix-supplier-grid">
          {previewSuppliers.map((item) => (
            <article key={item.supplier} className="po2-matrix-supplier-card">
              <span className="po2-eyebrow">{item.status}</span>
              <strong>{item.supplier}</strong>
              <span>{item.domain}</span>
              <small><b>Detection :</b> {item.detection}</small>
              <small><b>Risque UX :</b> {item.risk}</small>
              <small><b>Action :</b> {item.action}</small>
            </article>
          ))}
        </div>
      </Card>

      <Card
        title="Retour comptabilite XLSX"
        eyebrow="maquette fonctionnelle de la preview"
        action={<Button variant="ghost" disabled>Exporter XLSX</Button>}
      >
        <p className="po2-muted-line">
          En mode raccorde, cette zone permettra d'analyser le fichier complete par la comptabilite avant de creer une version
          brouillon de la matrice.
        </p>
        <DataTable
          rows={previewRows}
          getRowKey={(row) => row.key}
          columns={[
            { key: "line", header: "Ligne", render: (row) => row.line },
            { key: "key", header: "Cle stable", render: (row) => <small>{row.key}</small> },
            { key: "status", header: "Statut", render: (row) => <StatusBadge tone={toneForStatus(row.status)}>{row.status}</StatusBadge> },
            { key: "message", header: "Message", render: (row) => row.message },
          ]}
        />
      </Card>
    </div>
  );
}
