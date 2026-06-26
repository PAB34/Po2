import { useMemo, useState } from "react";
import { Button, Card, DataTable, Drawer, FilterBar, KpiCard, StatusBadge } from "../../design-system";
import type { AccountingMatrixContractV1, AccountingMatrixVersionV1 } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";
import {
  useCommitMatrixImportV1,
  useExportMatrixVersionV1,
  useMatrixContractDetailV1,
  useMatrixContractsV1,
  useMatrixVersionRulesV1,
  usePreviewMatrixImportV1,
  useSeedMatricesV1,
} from "./useMatricesV1";

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
  {
    label: "1. Import reference",
    detail: "Importer un export facture representatif du tiers facturant.",
    status: "done",
  },
  {
    label: "2. Detection recurrente",
    detail: "Identifier les postes, compteurs, sites, contrats et services vendus qui reviennent.",
    status: "done",
  },
  {
    label: "3. Codification comptable",
    detail: "Completer service, fonction, nature, operation, antenne et ventilation.",
    status: "current",
  },
  {
    label: "4. Controle couverture",
    detail: "Refuser l'activation si une ligne recurrente reste non couverte ou incoherente.",
    status: "next",
  },
  {
    label: "5. Activation version",
    detail: "Activer une version datee, jamais ecrasee, qui alimentera les futures factures.",
    status: "next",
  },
];

const SUPPLIER_GUIDES: Record<string, { pilot: string; detection: string; uxRisk: string; nextAction: string }> = {
  DALKIA: {
    pilot: "Cas complexe a couvrir",
    detection: "Code contrat + poste facture + service vendu + periode de marche.",
    uxRisk: "P3.4, lignes a ventiler, ancien marche avant octobre 2025, prestations en attente fournisseur.",
    nextAction: "Exporter la matrice, faire completer par la compta, puis reimporter en version brouillon.",
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

function versionTone(status: string) {
  if (status === "active") return "ok" as const;
  if (status === "candidate") return "warn" as const;
  if (status === "archived") return "neutral" as const;
  return "info" as const;
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

function defaultImportLabel() {
  return `Retour compta ${new Date().toISOString().slice(0, 10)}`;
}

function numberFromSummary(summary: Record<string, number> | undefined, key: string) {
  return String(summary?.[key] ?? 0);
}

export function MatrixAdminPageV1() {
  const { user } = useAuth();
  const canWriteMatrices = canWriteAccountingMatrices(user?.role);
  const [query, setQuery] = useState("");
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importVersionLabel, setImportVersionLabel] = useState("");

  const { data: contracts = [], isFetching, isError } = useMatrixContractsV1();
  const detail = useMatrixContractDetailV1(selectedContractId);
  const rules = useMatrixVersionRulesV1(selectedVersionId);
  const seed = useSeedMatricesV1();
  const exportVersion = useExportMatrixVersionV1();
  const importPreview = usePreviewMatrixImportV1();
  const importCommit = useCommitMatrixImportV1();

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return contracts;
    return contracts.filter((c) => `${c.supplier} ${c.contract_code ?? ""} ${c.contract_label ?? ""} ${c.domain}`.toLowerCase().includes(q));
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

  function resetImportState() {
    setImportFile(null);
    setImportVersionLabel("");
    importPreview.reset();
    importCommit.reset();
  }

  function openContract(contract: AccountingMatrixContractV1) {
    setSelectedContractId(contract.id);
    setSelectedVersionId(contract.active_version_id);
    resetImportState();
  }

  function closeDrawer() {
    setSelectedContractId(null);
    setSelectedVersionId(null);
    resetImportState();
  }

  function handlePreviewImport() {
    if (!selectedContractId || !importFile) return;
    importPreview.mutate({ contractId: selectedContractId, file: importFile });
  }

  function handleCommitImport() {
    if (!selectedContractId || !importFile || !importPreview.data?.can_commit) return;
    importCommit.mutate({
      contractId: selectedContractId,
      file: importFile,
      versionLabel: importVersionLabel.trim() || defaultImportLabel(),
    });
  }

  const importSummary = importPreview.data?.summary;
  const previewRows = importPreview.data?.rows.slice(0, 12) ?? [];

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
              <StatusBadge tone={setupStatusTone(step.status)}>{step.status === "done" ? "socle" : step.status === "current" ? "a faire" : "ensuite"}</StatusBadge>
              <strong>{step.label}</strong>
              <small>{step.detail}</small>
            </article>
          ))}
        </div>
        <p className="po2-muted-line">
          Lecture produit : l'ecran actuel sait lire contrats/versions/regles. Cette tranche ajoute l'aller-retour XLSX avec la comptabilite.
        </p>
      </Card>

      <Card title="Tiers facturants a raccorder" eyebrow="objectif : exporter vite pour la compta">
        {configuredSuppliers.length === 0 && !isFetching ? (
          <p className="po2-muted-line">Aucun tiers issu de l'API pour le moment. Lance le seed si ton role le permet.</p>
        ) : (
          <div className="po2-matrix-supplier-grid">
            {configuredSuppliers.map((item) => (
              <button
                type="button"
                key={item.supplier}
                className="po2-matrix-supplier-card"
                onClick={() => openContract(item.contracts[0])}
              >
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
          <p className="po2-muted-line">Lecture seule : ton role actuel ne permet pas de modifier ou generer les matrices comptables. Les profils Fluides et Technicien CVC restent volontairement exclus de cette action.</p>
        ) : null}
        {seed.isError ? (
          <p className="po2-muted-line">Seed impossible : {errorMessage(seed.error)}</p>
        ) : null}
        {isError ? (
          <p className="po2-muted-line">API matrices indisponible : verifie le backend ou les migrations.</p>
        ) : null}
        {seed.isSuccess ? (
          <p className="po2-muted-line">
            Seed termine : {seed.data.versions_created} version(s) creee(s) - fluides {seed.data.energy.contracts_created}, CPE {seed.data.cpe.contracts_created}.
          </p>
        ) : null}
        {contracts.length === 0 && !isFetching ? (
          <p className="po2-muted-line">{canWriteMatrices ? "Aucune matrice. Lance le seed pour generer les matrices a partir des codifications fluides/CPE." : "Aucune matrice visible. Demande a un profil habilite de generer les matrices depuis l'existant."}</p>
        ) : (
          <>
            <FilterBar searchPlaceholder="Fournisseur, contrat ou domaine" searchValue={query} onSearchChange={setQuery} />
            <DataTable
              rows={rows}
              getRowKey={(c) => c.id}
              onRowClick={openContract}
              columns={[
                { key: "domain", header: "Domaine", render: (c) => c.domain === "energy" ? "fluides" : c.domain },
                { key: "supplier", header: "Fournisseur", render: (c) => <strong>{c.supplier}</strong> },
                { key: "contract", header: "Contrat / lot", render: (c) => <span>{c.contract_code ?? "-"}<small className="po2-muted-line">{c.contract_label ?? ""}</small></span> },
                { key: "versions", header: "Versions", render: (c) => String(c.versions_count) },
                { key: "active", header: "Version active", render: (c) => c.active_version_label ? <StatusBadge tone="ok">{c.active_version_label}</StatusBadge> : <StatusBadge tone="info">aucune active</StatusBadge> },
              ]}
            />
          </>
        )}
      </Card>

      <Drawer
        open={selectedContractId != null}
        title={detail.data ? `${detail.data.supplier} - ${detail.data.contract_code ?? "contrat"}` : "Matrice"}
        eyebrow="Detail matrice"
        description={detail.data?.contract_label ?? undefined}
        onClose={closeDrawer}
      >
        {detail.isFetching ? <p className="po2-muted-line">Chargement...</p> : null}
        {detail.data ? (
          <div className="po2-invoice-proof">
            <Card title="Modele de detection attendu" eyebrow="a confirmer par l'assistant de configuration">
              <p className="po2-muted-line">
                {SUPPLIER_GUIDES[supplierKey(detail.data)]?.detection ?? "Detection a definir depuis un export facture de reference."}
              </p>
              <p className="po2-muted-line">
                {SUPPLIER_GUIDES[supplierKey(detail.data)]?.nextAction ?? "Importer un export puis controler les lignes recurrentes."}
              </p>
            </Card>

            <Card
              title="Versions"
              eyebrow="Exporter la version puis la faire completer par la compta"
              action={selectedVersionId != null ? (
                <Button
                  variant="ghost"
                  onClick={() => exportVersion.mutate({ versionId: selectedVersionId, label: detail.data?.contract_code ?? detail.data?.supplier })}
                  disabled={exportVersion.isPending}
                >
                  {exportVersion.isPending ? "Export..." : "Exporter XLSX"}
                </Button>
              ) : undefined}
            >
              {exportVersion.isError ? <p className="po2-muted-line">Export impossible : {errorMessage(exportVersion.error)}</p> : null}
              <div className="po2-decision-list">
                {detail.data.versions.map((v: AccountingMatrixVersionV1) => (
                  <button
                    key={v.id}
                    type="button"
                    className={selectedVersionId === v.id ? "po2-decision-item po2-decision-item--active" : "po2-decision-item"}
                    onClick={() => setSelectedVersionId(v.id)}
                  >
                    <StatusBadge tone={versionTone(v.status)}>{v.status}</StatusBadge>
                    <strong>{v.version_label}</strong>
                    <small>{v.rules_count} regles - source {v.source}</small>
                  </button>
                ))}
              </div>
            </Card>

            <Card title="Retour comptabilite XLSX" eyebrow="Preview sans ecriture puis creation d'une version brouillon">
              <div className="po2-matrix-import-form">
                <label>
                  <span>Fichier complete</span>
                  <input
                    type="file"
                    accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    disabled={!canWriteMatrices}
                    onChange={(event) => {
                      const file = event.currentTarget.files?.[0] ?? null;
                      setImportFile(file);
                      if (file && !importVersionLabel.trim()) setImportVersionLabel(defaultImportLabel());
                      importPreview.reset();
                      importCommit.reset();
                    }}
                  />
                </label>
                <label>
                  <span>Nom de version brouillon</span>
                  <input
                    type="text"
                    value={importVersionLabel}
                    disabled={!canWriteMatrices}
                    placeholder={defaultImportLabel()}
                    onChange={(event) => setImportVersionLabel(event.currentTarget.value)}
                  />
                </label>
                <Button variant="ghost" onClick={handlePreviewImport} disabled={!canWriteMatrices || !importFile || importPreview.isPending}>
                  {importPreview.isPending ? "Analyse..." : "Analyser le retour"}
                </Button>
                <Button variant="secondary" onClick={handleCommitImport} disabled={!canWriteMatrices || !importFile || !importPreview.data?.can_commit || importCommit.isPending}>
                  {importCommit.isPending ? "Creation..." : "Creer version brouillon"}
                </Button>
              </div>
              {!canWriteMatrices ? <p className="po2-muted-line">Import reserve aux roles autorises hors Fluides et Technicien CVC.</p> : null}
              {importPreview.isError ? <p className="po2-muted-line">Preview impossible : {errorMessage(importPreview.error)}</p> : null}
              {importCommit.isError ? <p className="po2-muted-line">Creation impossible : {errorMessage(importCommit.error)}</p> : null}
              {importCommit.isSuccess ? <p className="po2-muted-line">Version brouillon creee : {importCommit.data.version_label}. Elle doit encore etre controlee puis activee.</p> : null}
              {importPreview.data ? (
                <div className="po2-matrix-import-preview">
                  <div className="po2-kpi-grid">
                    <KpiCard label="Ajouts" value={numberFromSummary(importSummary, "ajout")} detail="nouvelles regles" />
                    <KpiCard label="Modifiees" value={numberFromSummary(importSummary, "modifie")} detail="ecarts vs reference" tone="warning" />
                    <KpiCard label="Erreurs" value={numberFromSummary(importSummary, "erreurs")} detail={importPreview.data.can_commit ? "aucune bloquante" : "commit bloque"} tone={importPreview.data.can_commit ? "neutral" : "danger"} />
                    <KpiCard label="Absentes" value={numberFromSummary(importSummary, "absentes_du_fichier")} detail="presentes en reference" />
                  </div>
                  {importPreview.data.structural_errors.length ? (
                    <p className="po2-muted-line">Erreurs structurelles : {importPreview.data.structural_errors.join(" | ")}</p>
                  ) : null}
                  {importPreview.data.warnings.length ? (
                    <p className="po2-muted-line">Alertes : {importPreview.data.warnings.slice(0, 3).join(" | ")}</p>
                  ) : null}
                  {importPreview.data.absentes_du_fichier.length ? (
                    <p className="po2-muted-line">Regles absentes du fichier : {importPreview.data.absentes_du_fichier.slice(0, 5).join(", ")}</p>
                  ) : null}
                  <DataTable
                    rows={previewRows}
                    getRowKey={(row) => `${row.line}-${row.stable_rule_key ?? "ligne"}`}
                    columns={[
                      { key: "line", header: "Ligne", render: (row) => row.line },
                      { key: "key", header: "Cle stable", render: (row) => <small>{row.stable_rule_key ?? "-"}</small> },
                      { key: "status", header: "Statut", render: (row) => <StatusBadge tone={row.status === "erreurs" ? "bad" : row.status === "modifie" ? "warn" : row.status === "ajout" ? "info" : "neutral"}>{row.status}</StatusBadge> },
                      { key: "message", header: "Message", render: (row) => row.message ?? "-" },
                    ]}
                  />
                </div>
              ) : null}
            </Card>

            <Card title="Regles de la version" eyebrow={selectedVersionId ? `Version #${selectedVersionId}` : "Selectionner une version"}>
              {selectedVersionId == null ? (
                <p className="po2-muted-line">Choisis une version ci-dessus.</p>
              ) : rules.isFetching ? (
                <p className="po2-muted-line">Chargement des regles...</p>
              ) : (
                <DataTable
                  rows={rules.data ?? []}
                  getRowKey={(r) => r.id}
                  columns={[
                    { key: "key", header: "Cle stable", render: (r) => <small>{r.stable_rule_key}</small> },
                    { key: "scope", header: "Scope", render: (r) => r.scope },
                    { key: "item", header: "Poste / perimetre", render: (r) => r.billed_item_pattern ?? r.site_code ?? r.meter_id ?? "-" },
                    { key: "nature", header: "Nature", render: (r) => <strong>{r.accounting_nature ?? "-"}</strong> },
                    { key: "alloc", header: "%", render: (r) => `${r.allocation_percent}` },
                  ]}
                />
              )}
            </Card>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}