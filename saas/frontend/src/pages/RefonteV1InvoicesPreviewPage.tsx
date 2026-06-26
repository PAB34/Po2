import { useMemo, useState } from "react";
import { Button, StatusBadge } from "../design-system";

type PreviewInvoiceStatus = "new" | "review" | "dispute" | "validated" | "exported" | "history";
type PreviewMatrixStatus = "complete" | "partial" | "missing" | "manual";
type PreviewTone = "ok" | "warn" | "bad" | "info" | "neutral";

type PreviewInvoice = {
  id: string;
  supplier: string;
  invoiceNumber: string;
  domain: string;
  site: string;
  contract: string;
  amount: string;
  dueDate: string;
  issueDate: string;
  status: PreviewInvoiceStatus;
  matrixStatus: PreviewMatrixStatus;
  control: { label: string; detail: string; tone: PreviewTone };
  decision: string;
  accounting: Array<{ axis: string; value: string; tone: PreviewTone }>;
  proofs: Array<{ label: string; value: string; detail: string; tone: PreviewTone }>;
  actions: string[];
  history: string[];
};

const invoices: PreviewInvoice[] = [
  {
    id: "dalkia-2026-0618",
    supplier: "DALKIA",
    invoiceNumber: "DK-2026-0618",
    domain: "CPE / P1 gaz",
    site: "Centre sportif Fonquerne",
    contract: "CPE DALKIA - P1/P2/P3",
    amount: "38 125,40 EUR",
    dueDate: "05/07/2026",
    issueDate: "18/06/2026",
    status: "review",
    matrixStatus: "partial",
    control: { label: "A controler", detail: "P1 coherent, ventilation comptable incomplete", tone: "warn" },
    decision: "Confirmer la ventilation P1 avant export finance.",
    accounting: [
      { axis: "Service", value: "Sports", tone: "ok" },
      { axis: "Fonction", value: "Equipements sportifs", tone: "ok" },
      { axis: "Nature", value: "A completer", tone: "warn" },
      { axis: "Operation", value: "CPE - exploitation", tone: "ok" },
    ],
    proofs: [
      { label: "Quantite P1", value: "OK", detail: "Cible + DJU coherents", tone: "ok" },
      { label: "Prix", value: "OK", detail: "BPU DALKIA applique", tone: "ok" },
      { label: "Matrice", value: "Partielle", detail: "Nature comptable manquante", tone: "warn" },
    ],
    actions: ["Corriger imputation", "Demander correction matrice", "Valider avec commentaire"],
    history: ["Import finance detecte", "Controle P1 calcule", "Snapshot matrice propose"],
  },
  {
    id: "engie-260621-18",
    supplier: "ENGIE",
    invoiceNumber: "EN-260621-18",
    domain: "Electricite",
    site: "Hotel de Ville",
    contract: "Electricite - Lot 1",
    amount: "12 408,72 EUR",
    dueDate: "01/07/2026",
    issueDate: "21/06/2026",
    status: "new",
    matrixStatus: "complete",
    control: { label: "Conforme", detail: "BPU, TURPE et taxes sans ecart bloquant", tone: "ok" },
    decision: "Facture prete pour validation comptable.",
    accounting: [
      { axis: "Service", value: "Administration generale", tone: "ok" },
      { axis: "Fonction", value: "Batiments administratifs", tone: "ok" },
      { axis: "Nature", value: "60612 - Electricite", tone: "ok" },
      { axis: "Antenne", value: "Centre-ville", tone: "ok" },
    ],
    proofs: [
      { label: "BPU", value: "OK", detail: "Prix unitaires conformes", tone: "ok" },
      { label: "TURPE", value: "OK", detail: "Referentiel date applique", tone: "ok" },
      { label: "Historique", value: "Nouvelle", detail: "Aucune decision anterieure", tone: "info" },
    ],
    actions: ["Valider", "Exporter finance", "Voir fiche detaillee"],
    history: ["Import ENGIE", "Parsing facture", "Controle automatique"],
  },
  {
    id: "total-tg-88412",
    supplier: "TotalEnergies",
    invoiceNumber: "TG-88412",
    domain: "Gaz",
    site: "Ecole des Beaux-Arts",
    contract: "Gaz - Lot 7",
    amount: "8 742,18 EUR",
    dueDate: "02/07/2026",
    issueDate: "20/06/2026",
    status: "dispute",
    matrixStatus: "partial",
    control: { label: "Litige fournisseur", detail: "CTA superieure a la reference", tone: "bad" },
    decision: "Preparer une reclamation fournisseur avant validation.",
    accounting: [
      { axis: "Service", value: "Culture", tone: "ok" },
      { axis: "Fonction", value: "Enseignement artistique", tone: "ok" },
      { axis: "Nature", value: "60613 - Gaz", tone: "ok" },
      { axis: "Exception", value: "CTA a justifier", tone: "bad" },
    ],
    proofs: [
      { label: "ATRD", value: "OK", detail: "Acheminement date", tone: "ok" },
      { label: "Accise", value: "OK", detail: "Taux en vigueur", tone: "ok" },
      { label: "CTA", value: "+126,40 EUR", detail: "Ecart fournisseur", tone: "bad" },
    ],
    actions: ["Generer mail fournisseur", "Mettre en attente", "Corriger commentaire"],
    history: ["Import TotalEnergies", "Fiche controle gaz construite", "Ecart CTA detecte"],
  },
  {
    id: "edf-784521",
    supplier: "EDF",
    invoiceNumber: "EDF-784521",
    domain: "Electricite / voirie",
    site: "Eclairage public - secteur 3",
    contract: "EDF - Voirie",
    amount: "24 816,09 EUR",
    dueDate: "30/06/2026",
    issueDate: "12/06/2026",
    status: "history",
    matrixStatus: "complete",
    control: { label: "Deja traitee", detail: "Reimport identique, decision conservee", tone: "info" },
    decision: "Aucune nouvelle action : facture deja dans l'historique.",
    accounting: [
      { axis: "Service", value: "Voirie", tone: "ok" },
      { axis: "Fonction", value: "Eclairage public", tone: "ok" },
      { axis: "Nature", value: "60612 - Electricite", tone: "ok" },
      { axis: "Historique", value: "Decision preservee", tone: "info" },
    ],
    proofs: [
      { label: "Empreinte", value: "Identique", detail: "Facture deja importee", tone: "info" },
      { label: "Decision", value: "Validee", detail: "Aucune modification", tone: "ok" },
      { label: "Export", value: "Finance", detail: "Deja transmis", tone: "ok" },
    ],
    actions: ["Voir historique", "Comparer imports", "Reouvrir si besoin"],
    history: ["Import initial", "Validation comptabilite", "Export finance", "Reimport identique detecte"],
  },
];

const navItems = [
  ["Cockpit", "Vue direction"],
  ["Sites 360", "Patrimoine"],
  ["Fluides", "ENEDIS / GRDF / eau"],
  ["Factures & decisions", "Preview active"],
  ["Matrices comptables", "Preview publique"],
  ["Marches & contrats", "A dessiner"],
  ["Maintenance", "A dessiner"],
  ["Technique & PPT", "A dessiner"],
  ["Budget & finances", "A dessiner"],
];

const workflow = [
  ["1", "Importer", "Export fournisseur ou espace client"],
  ["2", "Dedoublonner", "Nouvelles vs deja traitees"],
  ["3", "Parser", "Lignes, sites, compteurs, montants"],
  ["4", "Controler", "Contrat, BPU, taxes, DJU"],
  ["5", "Imputer", "Matrice comptable versionnee"],
  ["6", "Decider", "Valider, litige, exporter"],
];

const matrixCards = [
  ["ENGIE", "Electricite - Lot 1", "98 %", "Active", "ok"],
  ["EDF", "Voirie / electricite", "100 %", "Active", "ok"],
  ["TotalEnergies", "Gaz - Lot 7", "82 %", "A valider", "warn"],
  ["DALKIA", "CPE P1/P2/P3", "76 %", "A completer", "warn"],
];

function statusTone(status: PreviewInvoiceStatus): PreviewTone {
  if (status === "validated" || status === "exported") return "ok";
  if (status === "dispute") return "bad";
  if (status === "history") return "info";
  return "warn";
}

function statusLabel(status: PreviewInvoiceStatus) {
  return {
    new: "Nouvelle",
    review: "A controler",
    dispute: "Litige",
    validated: "Validee",
    exported: "Exportee",
    history: "Historique",
  }[status];
}

function matrixTone(status: PreviewMatrixStatus): PreviewTone {
  if (status === "complete") return "ok";
  if (status === "partial" || status === "manual") return "warn";
  return "bad";
}

function matrixLabel(status: PreviewMatrixStatus) {
  return {
    complete: "Validee",
    partial: "Proposee",
    missing: "Manquante",
    manual: "A arbitrer",
  }[status];
}

function supplierInitials(supplier: string) {
  if (supplier === "TotalEnergies") return "TE";
  if (supplier === "DALKIA") return "DK";
  return supplier.slice(0, 2).toUpperCase();
}

export function RefonteV1InvoicesPreviewPage() {
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(invoices[0].id);
  const selected = invoices.find((invoice) => invoice.id === selectedId) ?? invoices[0];

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return invoices;
    return invoices.filter((invoice) => Object.values(invoice).join(" ").toLowerCase().includes(q));
  }, [query]);

  return (
    <div className="po2-prototype-shell">
      <aside className="po2-prototype-sidebar">
        <div className="po2-prototype-brand">
          <span className="po2-prototype-logo">PO²</span>
          <div>
            <strong>Patrimoine</strong>
            <b>Au Carre</b>
          </div>
        </div>

        <div className="po2-prototype-workspace">
          <span>V</span>
          <div>
            <small>Collectivite</small>
            <strong>Ville de Sete</strong>
          </div>
        </div>

        <nav className="po2-prototype-nav" aria-label="Navigation prototype">
          {navItems.map(([label, detail]) => {
            const active = label === "Factures & decisions";
            const href = label === "Matrices comptables" ? "/refonte-v1/matrices-preview" : undefined;
            const item = (
              <>
                <span>{label}</span>
                <small>{detail}</small>
              </>
            );
            return href ? (
              <a key={label} className="po2-prototype-nav-item" href={href}>{item}</a>
            ) : (
              <button key={label} type="button" className={`po2-prototype-nav-item${active ? " po2-prototype-nav-item--active" : ""}`}>{item}</button>
            );
          })}
        </nav>

        <div className="po2-prototype-help">
          <strong>Prototype V1</strong>
          <small>Preview publique sans auth. Les autres entrees sont volontairement non branchees ici.</small>
        </div>
      </aside>

      <div className="po2-prototype-main">
        <header className="po2-prototype-topbar">
          <button className="po2-prototype-search" type="button">⌕ Rechercher un site, une facture, un compteur… <kbd>Ctrl K</kbd></button>
          <div className="po2-prototype-top-actions">
            <label>
              <span>Voir comme</span>
              <select defaultValue="finances" aria-label="Profil simule">
                <option value="direction">Direction</option>
                <option value="finances">Comptabilite</option>
                <option value="energie">Energie</option>
                <option value="technique">Technique</option>
              </select>
            </label>
            <Button variant="secondary">+ Importer</Button>
          </div>
        </header>

        <main className="po2-prototype-content">
          <header className="po2-prototype-page-head">
            <div>
              <span className="po2-eyebrow">Preview UX sans backend</span>
              <h1>Factures & decisions</h1>
              <p>Importer, controler, imputer, decider. Une chaine unique relie la facture a son contrat, sa matrice comptable et la transmission aux finances.</p>
            </div>
            <div className="po2-prototype-actions">
              <Button variant="ghost">Rapports d'import</Button>
              <Button>Importer des factures</Button>
            </div>
          </header>

          <section className="po2-proto-panel po2-proto-flow-panel">
            <div className="po2-proto-flow-batch">
              <div>
                <span className="po2-eyebrow">Dernier lot traite</span>
                <h2>ENGIE · Juin 2026</h2>
                <p>Import annuel autorise : les factures deja closes sont reconnues et conservees dans l'historique.</p>
              </div>
              <StatusBadge tone="ok">Traitement termine</StatusBadge>
            </div>
            <div className="po2-proto-invoice-steps">
              {workflow.map(([num, label, detail], index) => (
                <article key={label} className={index < 5 ? "done" : "current"}>
                  <span>{index < 5 ? "✓" : num}</span>
                  <div>
                    <b>{label}</b>
                    <small>{detail}</small>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <div className="po2-proto-kpi-grid">
            <article><span>Nouvelles</span><strong>12</strong><small>184 320 EUR depuis le dernier import</small></article>
            <article><span>Imputation complete</span><strong>52</strong><small>sur 58 factures</small></article>
            <article><span>Exceptions comptables</span><strong>6</strong><small>4 regles · 2 contrats</small></article>
            <article><span>Transmises aux finances</span><strong>16</strong><small>172 480 EUR ce mois</small></article>
          </div>

          <section className="po2-proto-panel po2-proto-matrix-overview">
            <div className="po2-proto-panel-head">
              <div>
                <span className="po2-eyebrow">Referentiel contractuel</span>
                <h2>Matrices comptables par contrat</h2>
                <p>La facture herite de la version active ; seules les exceptions sont corrigees par la comptabilite.</p>
              </div>
              <div className="po2-prototype-actions">
                <Button variant="ghost">↑ Importer XLSX</Button>
                <Button variant="ghost">↓ Exporter XLSX</Button>
              </div>
            </div>
            <div className="po2-proto-matrix-contracts">
              {matrixCards.map(([supplier, contract, coverage, status, tone]) => (
                <article key={supplier}>
                  <div className="po2-proto-matrix-card-top">
                    <span className="po2-proto-supplier-logo">{supplierInitials(supplier)}</span>
                    <div>
                      <strong>{supplier}</strong>
                      <small>{contract}</small>
                    </div>
                    <StatusBadge tone={tone as PreviewTone}>{status}</StatusBadge>
                  </div>
                  <div className="po2-proto-matrix-stats">
                    <span><b>{coverage}</b> couverture</span>
                    <span><b>Version active</b></span>
                  </div>
                  <a href="/refonte-v1/matrices-preview">Editer la matrice →</a>
                </article>
              ))}
            </div>
          </section>

          <div className="po2-proto-toolbar-row">
            <label>
              <span>⌕</span>
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Numero, fournisseur, site ou marche" />
            </label>
            <select defaultValue="all" aria-label="Filtrer fournisseur"><option value="all">Tous les fournisseurs</option><option>ENGIE</option><option>EDF</option><option>TotalEnergies</option><option>DALKIA</option></select>
            <select defaultValue="all" aria-label="Filtrer imputation"><option value="all">Toutes les imputations</option><option>Validee</option><option>Proposee</option><option>A completer</option></select>
          </div>

          <div className="po2-proto-workspace-grid">
            <section className="po2-proto-panel po2-proto-table-panel">
              <table>
                <thead>
                  <tr>
                    <th>Fournisseur / facture</th>
                    <th>Site</th>
                    <th>Marche</th>
                    <th>Montant TTC</th>
                    <th>Emission</th>
                    <th>Matrice</th>
                    <th>Decision</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((invoice) => (
                    <tr key={invoice.id} className={invoice.id === selected.id ? "active" : ""} onClick={() => setSelectedId(invoice.id)}>
                      <td>
                        <div className="po2-proto-supplier">
                          <span className="po2-proto-supplier-logo">{supplierInitials(invoice.supplier)}</span>
                          <span><b>{invoice.supplier}</b><small>{invoice.invoiceNumber}</small></span>
                        </div>
                      </td>
                      <td>{invoice.site}</td>
                      <td>{invoice.contract}</td>
                      <td><strong>{invoice.amount}</strong></td>
                      <td>{invoice.issueDate}</td>
                      <td><StatusBadge tone={matrixTone(invoice.matrixStatus)}>{matrixLabel(invoice.matrixStatus)}</StatusBadge></td>
                      <td><StatusBadge tone={statusTone(invoice.status)}>{statusLabel(invoice.status)}</StatusBadge></td>
                      <td className="po2-proto-open-cell">Ouvrir →</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <aside className="po2-proto-panel po2-proto-dossier">
              <span className="po2-eyebrow">Dossier facture</span>
              <h2>{selected.supplier} · {selected.invoiceNumber}</h2>
              <p>{selected.site} · {selected.contract}</p>
              <div className="po2-proto-dossier-kpis">
                <div><span>Montant TTC</span><b>{selected.amount}</b></div>
                <div><span>Echeance</span><b>{selected.dueDate}</b></div>
                <div><span>Statut</span><b>{statusLabel(selected.status)}</b></div>
              </div>
              <div className="po2-proto-verdict">
                <span>{selected.control.tone === "bad" ? "!" : "✓"}</span>
                <p><b>Verdict :</b> {selected.control.detail}</p>
              </div>
              <h3>Trace de controle</h3>
              <div className="po2-proto-control-list">
                {selected.proofs.map((proof) => (
                  <article key={proof.label}>
                    <StatusBadge tone={proof.tone}>{proof.value}</StatusBadge>
                    <div><strong>{proof.label}</strong><small>{proof.detail}</small></div>
                  </article>
                ))}
              </div>
              <h3>Imputation proposee</h3>
              <div className="po2-proto-accounting-grid">
                {selected.accounting.map((axis) => (
                  <article key={axis.axis}>
                    <span>{axis.axis}</span>
                    <strong>{axis.value}</strong>
                  </article>
                ))}
              </div>
              <div className="po2-proto-decision-box">
                <span>Decision recommandee</span>
                <strong>{selected.decision}</strong>
              </div>
              <div className="po2-proto-action-stack">
                {selected.actions.map((action) => <Button key={action} variant={action.includes("mail") || action.includes("attente") ? "danger" : "ghost"}>{action}</Button>)}
              </div>
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
}
