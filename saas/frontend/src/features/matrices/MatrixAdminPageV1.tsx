import { useMemo, useState } from "react";
import { Button, Card, DataTable, FilterBar, KpiCard, StatusBadge } from "../../design-system";
import type { AccountingMatrixContractV1 } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";
import { MatrixEditorOverlayV1 } from "./MatrixEditorOverlayV1";
import { useMatrixContractsV1, useSeedMatricesV1 } from "./useMatricesV1";

const MATRIX_WRITE_DENIED_ROLES = new Set(["FLUIDES", "FLUIDE", "RESPONSABLE_FLUIDES", "TECHNICIEN_CVC", "TECHNICIEN CVC"]);
const MATRIX_WRITE_ALLOWED_ROLES = new Set([
  "ADMIN",
  "SUPERADMIN",
  "DIRECTION",
  "RESPONSABLE_MAINTENANCE",
  "RESPONSABLE MAINTENANCE",
  "PATRIMOINE",
  "FINANCE",
  "COMPTA",
  "COMPTABILITE",
]);

const MATRIX_SETUP_STEPS = [
  { label: "1. Import reference", detail: "Importer un export facture representatif du tiers facturant.", status: "done" },
  { label: "2. Detection recurrente", detail: "Identifier postes, compteurs, sites, contrats et services vendus recurrents.", status: "done" },
  { label: "3. Codification comptable", detail: "Completer service, fonction, nature, operation, antenne et ventilation.", status: "current" },
  { label: "4. Controle couverture", detail: "Refuser l'activation si une ligne recurrente reste non couverte.", status: "next" },
  { label: "5. Activation version", detail: "Activer une version datee, jamais ecrasee, qui alimentera les futures factures.", status: "next" },
];

const SUPPLIER_GUIDES: Record<string, { pilot: string; detection: string; uxRisk: string; nextAction: string }> = {
  DALKIA: {
    pilot: "Cas complexe a couvrir",
    detection: "Code contrat + poste facture + service vendu + periode de marche.",
    uxRisk: "P3.4, lignes a ventiler, ancien marche, prestations en attente fournisseur.",
    nextAction: "Editer la matrice ou exporter/reimporter le classeur comptable.",
  },
  ENGIE: {
    pilot: "A traiter aussi pour l'envoi compta",
    detection: "PRM/site + composante facture + segment C2/C4/C5 + periode.",
    uxRisk: "Ne pas melanger controle BPU/TURPE et imputation comptable.",
    nextAction: "Reutiliser le parser XLSX et les composants normalises existants.",
  },
  EDF: {
    pilot: "A traiter aussi pour l'envoi compta",
    detection: "PRM/site + composante facture + lot/marche + avoir ou facture.",
    uxRisk: "Avoirs, periodes anciennes et periodes manquantes dans les exports reels.",
    nextAction: "Securiser historique/reimport avant validation automatique.",
  },
  TOTALENERGIES: {
    pilot: "Bon candidat gaz",
    detection: "PCE/site + composante gaz + taxe/acheminement/fourniture + periode.",
    uxRisk: "Sites sans libelle mais PCE present ; avoirs gaz a isoler.",
    nextAction: "Brancher la trace gaz deja produite par le moteur TotalEnergies.",
  },
};

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Une erreur est survenue.";
}

function setupStatusTone(status: string) {
  if (status === "done") return "ok" as const;
  if (status === "current") return "warn" as const;
  return "neutral" as const;
}

function normalizeRole(role: string | undefined) {
  return (role ?? "").trim().toUpperCase().replace("-", "_");
}

function canWriteAccountingMatrices(role: string | undefined) {
  const normalized = normalizeRole(role);
  return MATRIX_WRITE_ALLOWED_ROLES.has(normalized) && !MATRIX_WRITE_DENIED_ROLES.has(normalized);
}

function supplierKey(contract: AccountingMatrixContractV1) {
  const raw = contract.supplier.toUpperCase();
  if (raw.includes("TOTAL")) return "TOTALENERGIES";
  if (raw.includes("DALKIA")) return "DALKIA";
  if (raw.includes("ENGIE")) return "ENGIE";
  if (raw.includes("EDF")) return "EDF";
  return raw;
}

export function MatrixAdminPageV1() {
  const { user } = useAuth();
  const canWriteMatrices = canWriteAccountingMatrices(user?.role);
  const [query, setQuery] = useState("");
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);

  const { data: contracts = [], isFetching, isError } = useMatrixContractsV1();
  const seed = useSeedMatricesV1();

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return contracts;
    return contracts.filter((c) =>
      `${c.supplier} ${c.contract_code ?? ""} ${c.contract_label ?? ""} ${c.domain}`.toLowerCase().includes(q),
    );
  }, [query, contracts]);

  const activeVersions = contracts.filter((c) => c.active_version_id != null).length;
  const configuredSuppliers = useMemo(() => {
    const bySupplier = new Map<string, AccountingMatrixContractV1[]>();
    for (const contract of contracts) {
      const key = supplierKey(contract);
      bySupplier.set(key, [...(bySupplier.get(key) ?? []), contract]);
    }
    return Array.from(bySupplier.entries()).map(([supplier, supplierContracts]) => {
      const guide = SUPPLIER_GUIDES[supplier] ?? {
        pilot: "A cadrer",
        detection: "A definir depuis les exports factures reels.",
        uxRisk: "Ne pas activer sans analyse des lignes recurrentes.",
        nextAction: "Importer un export de reference puis documenter les composants.",
      };
      const versions = supplierContracts.reduce((sum, c) => sum + c.versions_count, 0);
      const active = supplierContracts.filter((c) => c.active_version_id != null).length;
      return { supplier, contracts: supplierContracts, versions, active, guide };
    });
  }, [contracts]);

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">Matrices comptables - atelier de configuration</span>
        <h1>Configurer les matrices par tiers facturant</h1>
        <p>
          Objectif V1 : partir des factures reelles, detecter les lignes recurrentes, faire valider la codification comptable,
          puis appliquer automatiquement la matrice aux nouvelles factures.
        </p>
      </header>

      <div className="po2-kpi-grid">
        <KpiCard label="Contrats matrices" value={String(contracts.length)} detail={isFetching ? "synchronisation..." : "depuis l'API"} />
        <KpiCard label="Tiers couverts" value={String(configuredSuppliers.length)} detail="regroupement fournisseur" />
        <KpiCard label="Versions actives" value={String(activeVersions)} detail="une seule version active par contrat" />
        <KpiCard label="Source" value={isError ? "indisponible" : "API"} detail="donnees reelles, pas de mock" tone={isError ? "warning" : undefined} />
      </div>

      <Card title="Parcours cible de configuration" eyebrow="UX metier avant application automatique">
        <div className="po2-matrix-setup-flow">
          {MATRIX_SETUP_STEPS.map((step) => (
            <article key={step.label} className="po2-matrix-setup-step">
              <StatusBadge tone={setupStatusTone(step.status)}>
                {step.status === "done" ? "socle" : step.status === "current" ? "a faire" : "ensuite"}
              </StatusBadge>
              <strong>{step.label}</strong>
              <small>{step.detail}</small>
            </article>
          ))}
        </div>
        <p className="po2-muted-line">
          Ouvre un contrat pour editer la matrice en plein ecran (axes comptables) et importer/exporter le classeur.
        </p>
      </Card>

      <Card title="Tiers facturants a raccorder" eyebrow="objectif : exporter vite pour la compta">
        {configuredSuppliers.length === 0 && !isFetching ? (
          <p className="po2-muted-line">Aucun tiers issu de l'API pour le moment. Lance le seed si ton role le permet.</p>
        ) : (
          <div className="po2-matrix-supplier-grid">
            {configuredSuppliers.map((item) => (
              <button type="button" key={item.supplier} className="po2-matrix-supplier-card" onClick={() => setSelectedContractId(item.contracts[0].id)}>
                <span className="po2-eyebrow">{item.guide.pilot}</span>
                <strong>{item.supplier}</strong>
                <span>{item.contracts.length} contrat(s) - {item.versions} version(s) - {item.active} active(s)</span>
                <small><b>Detection :</b> {item.guide.detection}</small>
                <small><b>Risque UX :</b> {item.guide.uxRisk}</small>
                <small><b>Action :</b> {item.guide.nextAction}</small>
              </button>
            ))}
          </div>
        )}
      </Card>

      <Card
        title="Contrats et versions existants"
        eyebrow={isError ? "API indisponible" : isFetching ? "Synchronisation API" : "Donnees API"}
        action={
          <Button variant="ghost" onClick={() => seed.mutate()} disabled={seed.isPending || !canWriteMatrices}>
            {seed.isPending ? "Seed en cours..." : "Seed depuis l'existant"}
          </Button>
        }
      >
        {!canWriteMatrices ? (
          <p className="po2-muted-line">Lecture seule : ton role actuel ne permet pas de modifier ou generer les matrices comptables.</p>
        ) : null}
        {seed.isError ? <p className="po2-muted-line">Seed impossible : {errorMessage(seed.error)}</p> : null}
        {isError ? <p className="po2-muted-line">API matrices indisponible : verifie le backend ou les migrations.</p> : null}
        {seed.isSuccess ? (
          <p className="po2-muted-line">
            Seed termine : {seed.data.versions_created} version(s) creee(s) - fluides {seed.data.energy.contracts_created}, CPE {seed.data.cpe.contracts_created}.
          </p>
        ) : null}
        {contracts.length === 0 && !isFetching ? (
          <p className="po2-muted-line">Aucune matrice. Lance le seed pour generer les matrices a partir des codifications fluides/CPE.</p>
        ) : (
          <>
            <FilterBar searchPlaceholder="Fournisseur, contrat ou domaine" searchValue={query} onSearchChange={setQuery} />
            <DataTable
              rows={rows}
              getRowKey={(c) => c.id}
              onRowClick={(c) => setSelectedContractId(c.id)}
              columns={[
                { key: "domain", header: "Domaine", render: (c) => (c.domain === "energy" ? "fluides" : c.domain) },
                { key: "supplier", header: "Fournisseur", render: (c) => <strong>{c.supplier}</strong> },
                { key: "contract", header: "Contrat / lot", render: (c) => <span>{c.contract_code ?? "-"}<small className="po2-muted-line">{c.contract_label ?? ""}</small></span> },
                { key: "versions", header: "Versions", render: (c) => String(c.versions_count) },
                { key: "active", header: "Version active", render: (c) => (c.active_version_label ? <StatusBadge tone="ok">{c.active_version_label}</StatusBadge> : <StatusBadge tone="info">aucune active</StatusBadge>) },
              ]}
            />
          </>
        )}
      </Card>

      {selectedContractId != null ? (
        <MatrixEditorOverlayV1 contractId={selectedContractId} canWrite={canWriteMatrices} onClose={() => setSelectedContractId(null)} />
      ) : null}
    </div>
  );
}
