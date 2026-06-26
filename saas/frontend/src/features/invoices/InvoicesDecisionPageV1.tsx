import { useEffect, useMemo, useState } from "react";
import { Button, Card, DataTable, Drawer, FilterBar, KpiCard, StatusBadge } from "../../design-system";
import { useAccountingMatricesV1 } from "./accountingMatrixV1";
import { useInvoiceDecisionsV1 } from "./useInvoiceDecisionsV1";
import { useInvoiceAccountingSnapshotV1, useInvoiceAccountingActionsV1 } from "./useInvoiceAccountingSnapshotsV1";
import { useMatrixContractsV1 } from "../matrices/useMatricesV1";
import type { AccountingMatrixContractV1 } from "../../lib/api";
import type { AccountingMatrixStatus, InvoiceDecision, InvoiceDecisionStatus } from "./invoices.types";

function matrixSupplierKeyword(value: string) {
  const upper = value.toUpperCase();
  if (upper.includes("TOTAL")) return "TOTAL";
  if (upper.includes("DALKIA")) return "DALKIA";
  if (upper.includes("ENGIE")) return "ENGIE";
  if (upper.includes("EDF")) return "EDF";
  return upper;
}

function suggestMatrixContract(invoice: InvoiceDecision | null, contracts: AccountingMatrixContractV1[]) {
  if (!invoice) return null;
  const supplierKey = matrixSupplierKeyword(invoice.supplier);
  const sameSupplier = contracts.filter((c) => matrixSupplierKeyword(c.supplier) === supplierKey);
  const ref = `${invoice.contractLabel ?? ""} ${invoice.invoiceNumber ?? ""}`.toUpperCase();
  const exact = sameSupplier.find((c) => c.contract_code && ref.includes(c.contract_code.toUpperCase()));
  return (exact ?? sameSupplier[0] ?? null)?.id ?? null;
}

function actionError(error: unknown) {
  return error instanceof Error ? error.message : null;
}

function invoiceTone(status: InvoiceDecisionStatus) {
  if (status === "conforme") return "ok" as const;
  if (status === "anomalie") return "bad" as const;
  if (status === "transmise") return "info" as const;
  return "warn" as const;
}

function invoiceLabel(status: InvoiceDecisionStatus) {
  return {
    conforme: "Conforme",
    anomalie: "Anomalie",
    decision: "À décider",
    transmise: "Transmise",
    archivee: "Archivée",
  }[status];
}

function matrixTone(status: AccountingMatrixStatus) {
  if (status === "validee") return "ok" as const;
  if (status === "proposee") return "info" as const;
  if (status === "a_completer") return "warn" as const;
  if (status === "a_arbitrer") return "bad" as const;
  return "neutral" as const;
}

function matrixLabel(status: AccountingMatrixStatus) {
  return {
    validee: "Validée",
    proposee: "Proposée",
    a_completer: "À compléter",
    a_arbitrer: "À arbitrer",
    non_applicable: "Non applicable",
  }[status];
}

function snapshotLabel(status?: string) {
  if (status === "proposed") return "Proposition";
  if (status === "validated") return "Validé";
  if (status === "manual_override") return "Corrigé";
  if (status === "exported") return "Exporté";
  return "Aucun snapshot";
}

function snapshotTone(status?: string) {
  if (status === "validated" || status === "exported") return "ok" as const;
  if (status === "proposed") return "info" as const;
  if (status === "manual_override") return "warn" as const;
  return "neutral" as const;
}

function formatKpiAmount(value: number) {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value);
}

function sumInvoiceAmounts(rows: InvoiceDecision[]) {
  return rows.reduce((total, invoice) => total + (invoice.amountTtc ?? 0), 0);
}

function kpiAmountDetail(rows: InvoiceDecision[], suffix: string) {
  return formatKpiAmount(sumInvoiceAmounts(rows)) + " · " + suffix;
}

const invoiceWorkflowSteps = [
  { label: "Importer", detail: "Export fournisseur, lot annuel ou fichier unitaire" },
  { label: "Dédoublonner", detail: "Nouvelles, historiques, révisions et erreurs" },
  { label: "Contrôler", detail: "BPU, TURPE, taxes, périodes, montants" },
  { label: "Imputer", detail: "Matrice contractuelle et snapshot comptable" },
  { label: "Décider", detail: "Valider, mettre en attente ou réclamer" },
  { label: "Exporter", detail: "Transmission finances et historique figé" },
] as const;

function sourceProfile(invoice: InvoiceDecision) {
  if (invoice.source === "gas-totalenergies") {
    return {
      title: "Dossier gaz TotalEnergies",
      eyebrow: "BPU gaz, taxes et référentiels datés",
      items: [
        ["Contrôle attendu", "ATRD, CTA, accise, TVA et lignes non contrôlées explicites"],
        ["Décision métier", "Valider, réclamer ou historiser avec preuve ligne par ligne"],
        ["Imputation", "Matrice comptable du marché gaz à appliquer avant finances"],
      ],
    };
  }
  if (invoice.source === "cpe-dalkia") {
    return {
      title: "Dossier CPE / DALKIA",
      eyebrow: "Maintenance, P1/P2/P3 et justificatifs",
      items: [
        ["Contrôle attendu", "Contrat, période, prestation facturée, pièces et écarts"],
        ["Décision métier", "Arbitrer la conformité avant validation comptable"],
        ["Imputation", "Matrice CPE par contrat, site, service et nature comptable"],
      ],
    };
  }
  if (invoice.source === "energy-import") {
    return {
      title: "Dossier fournisseur fluides",
      eyebrow: "ENGIE / EDF et futurs fournisseurs",
      items: [
        ["Contrôle attendu", "BPU, TURPE, taxes, abonnement, consommation et doublons"],
        ["Décision métier", "Contrôler les écarts puis préparer la transmission finances"],
        ["Imputation", "Matrice du contrat de fourniture et axes comptables associés"],
      ],
    };
  }
  return {
    title: "Dossier de démonstration",
    eyebrow: "Prototype UX sans écriture",
    items: [
      ["Contrôle attendu", "Valider le parcours avant raccordement complet"],
      ["Décision métier", "Vérifier que les libellés et actions parlent métier"],
      ["Imputation", "Simulation de matrice comptable"],
    ],
  };
}

export function InvoicesDecisionPageV1() {
  const [query, setQuery] = useState("");
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceDecision | null>(null);
  const { invoices, isFetching, isUsingFallback } = useInvoiceDecisionsV1();
  const { matrices, isUsingFallback: isUsingMatrixFallback } = useAccountingMatricesV1();
  const snapshot = useInvoiceAccountingSnapshotV1(selectedInvoice);
  const actions = useInvoiceAccountingActionsV1(selectedInvoice);
  const { data: matrixContracts = [] } = useMatrixContractsV1();
  const [matrixContractId, setMatrixContractId] = useState<number | null>(null);
  useEffect(() => {
    setMatrixContractId(null);
    actions.apply.reset();
    actions.validate.reset();
    actions.exportFinance.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedInvoice?.stableId]);
  const suggestedContractId = useMemo(
    () => suggestMatrixContract(selectedInvoice, matrixContracts),
    [selectedInvoice, matrixContracts],
  );
  const effectiveContractId = matrixContractId ?? suggestedContractId;

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q
      ? invoices.filter((invoice) => Object.values(invoice).join(" ").toLowerCase().includes(q))
      : invoices;
  }, [query, invoices]);

  const invoiceKpis = useMemo(() => {
    const toControl = invoices.filter(
      (invoice) =>
        invoice.status === "decision" ||
        invoice.status === "anomalie" ||
        invoice.matrixStatus === "a_completer" ||
        invoice.matrixStatus === "a_arbitrer",
    );
    const conformes = invoices.filter((invoice) => invoice.status === "conforme");
    const anomalies = invoices.filter(
      (invoice) =>
        invoice.status === "anomalie" ||
        invoice.matrixStatus === "a_completer" ||
        invoice.matrixStatus === "a_arbitrer",
    );
    const ready = invoices.filter((invoice) => invoice.status === "conforme" && invoice.matrixStatus === "validee");
    const newRows = invoices.filter((invoice) => !invoice.alreadyProcessed).length;
    const conformRate = invoices.length > 0 ? Math.round((conformes.length / invoices.length) * 100) : 0;

    return {
      toControl: {
        count: toControl.length,
        detail: kpiAmountDetail(toControl, newRows + " nouvelle(s) non traitée(s)"),
      },
      conformes: {
        count: conformes.length,
        detail: kpiAmountDetail(conformes, conformRate + " % du lot"),
      },
      anomalies: {
        count: anomalies.length,
        detail: kpiAmountDetail(anomalies, "réclamation ou correction proposée"),
      },
      ready: {
        count: ready.length,
        detail: kpiAmountDetail(ready, "vers le service finances"),
      },
    };
  }, [invoices]);

  const snapshotStatus = snapshot.data?.status;
  const snapshotDetail = snapshot.isFetching
    ? "Recherche du snapshot comptable…"
    : snapshot.data?.matrix_version_id
      ? "Version matrice #" + snapshot.data.matrix_version_id
      : selectedInvoice?.source === "mock"
        ? "Donnée de démonstration"
        : "Pas encore imputée via la matrice";


  const sourceTone = isUsingFallback ? "warn" : isFetching ? "info" : "ok";
  const sourceLabel = isUsingFallback ? "Démonstration" : isFetching ? "Synchronisation" : "Données API";
  const matrixSourceLabel = isUsingMatrixFallback ? "Matrices transitoires" : "Matrices API";
  const sourceDetail = isUsingFallback
    ? "Aucune session ou API indisponible : la page montre un jeu de démonstration explicite."
    : "La file agrège les imports ENGIE/EDF, les factures gaz TotalEnergies et les factures CPE/DALKIA disponibles.";
  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head po2-invoices-v1__head">
        <div>
          <span className="po2-eyebrow">Factures & décisions</span>
          <h1>Importer, contrôler, imputer, décider.</h1>
          <p>Une chaîne unique relie la facture à son contrat, sa matrice comptable et la transmission aux finances.</p>
        </div>
        <div className="po2-invoices-v1__head-actions">
          <Button variant="ghost">Rapports d’import</Button>
          <Button>Importer des factures</Button>
        </div>
      </header>

      <section className="po2-invoice-source-strip">
        <StatusBadge tone={sourceTone}>{sourceLabel}</StatusBadge>
        <div>
          <strong>{sourceDetail}</strong>
          <small>{matrixSourceLabel} · {invoices.length} facture(s) dans la file · {filteredRows.length} affichée(s)</small>
        </div>
      </section>

      <div className="po2-kpi-grid">
        <KpiCard label="À contrôler" value={String(invoiceKpis.toControl.count)} detail={invoiceKpis.toControl.detail} icon="▤" />
        <KpiCard label="Conformes" value={String(invoiceKpis.conformes.count)} detail={invoiceKpis.conformes.detail} tone="good" icon="✓" />
        <KpiCard label="Avec anomalie" value={String(invoiceKpis.anomalies.count)} detail={invoiceKpis.anomalies.detail} tone="danger" icon="!" />
        <KpiCard label="Prêtes à transmettre" value={String(invoiceKpis.ready.count)} detail={invoiceKpis.ready.detail} tone="info" icon="→" />
      </div>

      <Card title="Chaîne de traitement" eyebrow="facture -> contrôle -> décision -> finances">
        <div className="po2-invoice-workflow po2-invoice-workflow--compact">
          {invoiceWorkflowSteps.map((step, index) => (
            <article key={step.label} className="po2-invoice-workflow__step">
              <span>{index + 1}</span>
              <strong>{step.label}</strong>
              <small>{step.detail}</small>
            </article>
          ))}
        </div>
      </Card>

      <Card
        title="Matrices comptables par contrat"
        eyebrow={isUsingMatrixFallback ? "Référentiel contractuel · synthèse mockée" : "Référentiel contractuel · synthèse API"}
        action={<Button variant="ghost">Exporter XLSX</Button>}
      >
        <div className="po2-matrix-grid">
          {matrices.map((matrix) => (
            <article key={matrix.id} className="po2-matrix-card">
              <div>
                <strong>{matrix.supplier}</strong>
                <small>{matrix.contract}</small>
              </div>
              <StatusBadge tone={matrix.status === "Active" ? "ok" : matrix.status === "À valider" ? "warn" : "bad"}>{matrix.status}</StatusBadge>
              <p>{matrix.version}</p>
              <dl>
                <div><dt>Couverture</dt><dd>{matrix.coverage}</dd></div>
                <div><dt>Règles</dt><dd>{matrix.rules}</dd></div>
                <div><dt>Exceptions</dt><dd>{matrix.exceptions}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </Card>

      <Card
        title="File factures"
        eyebrow={isUsingFallback ? "Contrôle et décision · données de démonstration" : isFetching ? "Contrôle et décision · synchronisation" : "Contrôle et décision · données API"}
        action={<StatusBadge tone={sourceTone}>{sourceLabel}</StatusBadge>}
      >
        <FilterBar searchPlaceholder="Numéro, fournisseur, site ou marché" searchValue={query} onSearchChange={setQuery} />
        <DataTable
          rows={filteredRows}
          getRowKey={(invoice) => invoice.stableId}
          onRowClick={setSelectedInvoice}
          columns={[
            { key: "supplier", header: "Fournisseur / facture", render: (invoice) => <span><strong>{invoice.supplier}</strong><small className="po2-muted-line">{invoice.invoiceNumber}</small></span> },
            { key: "site", header: "Site", render: (invoice) => invoice.siteLabel },
            { key: "market", header: "Marché", render: (invoice) => invoice.contractLabel },
            { key: "amount", header: "Montant TTC", render: (invoice) => <strong>{invoice.amountTtcLabel}</strong> },
            { key: "matrix", header: "Matrice", render: (invoice) => <StatusBadge tone={matrixTone(invoice.matrixStatus)}>{matrixLabel(invoice.matrixStatus)}</StatusBadge> },
            { key: "decision", header: "Décision", render: (invoice) => <StatusBadge tone={invoiceTone(invoice.status)}>{invoiceLabel(invoice.status)}</StatusBadge> },
          ]}
        />
      </Card>

      <Drawer
        open={Boolean(selectedInvoice)}
        title={selectedInvoice ? selectedInvoice.supplier + " · " + selectedInvoice.invoiceNumber : "Facture"}
        eyebrow="Dossier facture"
        description={selectedInvoice ? selectedInvoice.siteLabel + " · " + selectedInvoice.contractLabel : undefined}
        onClose={() => setSelectedInvoice(null)}
        footer={<Button variant="ghost" disabled title="Génération du courrier de réclamation à venir">Préparer une réclamation (à venir)</Button>}
      >
        {selectedInvoice ? (
          <div className="po2-invoice-proof">
            <div className="po2-kpi-grid">
              <KpiCard label="Montant TTC" value={selectedInvoice.amountTtcLabel} detail={selectedInvoice.issuedAt ?? "Date inconnue"} />
              <KpiCard label="Échéance" value={selectedInvoice.dueAt ?? "À définir"} detail="À traiter avant transmission" />
              <KpiCard label="Statut" value={invoiceLabel(selectedInvoice.status)} detail={selectedInvoice.issue} />
              <KpiCard label="Matrice comptable" value={snapshotLabel(snapshotStatus)} detail={snapshotDetail} />
            </div>

            <Card title={sourceProfile(selectedInvoice).title} eyebrow={sourceProfile(selectedInvoice).eyebrow}>
              <div className="po2-invoice-source-profile">
                <article>
                  <span>Facture</span>
                  <strong>{selectedInvoice.invoiceNumber}</strong>
                  <small>{selectedInvoice.supplier} · {selectedInvoice.contractLabel}</small>
                </article>
                <article>
                  <span>Site / périmètre</span>
                  <strong>{selectedInvoice.siteLabel}</strong>
                  <small>{selectedInvoice.alreadyProcessed ? "Déjà connu dans l'historique" : "Nouveau ou à instruire"}</small>
                </article>
                {sourceProfile(selectedInvoice).items.map(([label, detail]) => (
                  <article key={label}>
                    <span>{label}</span>
                    <strong>{detail}</strong>
                  </article>
                ))}
              </div>
            </Card>

            <Card title="Trace de contrôle" eyebrow="Preuves">
              <div className="po2-decision-list">
                {snapshot.data ? (
                  <article className="po2-decision-item">
                    <StatusBadge tone={snapshotTone(snapshot.data.status)}>{snapshotLabel(snapshot.data.status)}</StatusBadge>
                    <strong>Snapshot comptable</strong>
                    <small>{snapshot.data.exceptions_json ? "Exceptions à analyser avant validation" : "Imputation enregistrée sans exception bloquante"}</small>
                  </article>
                ) : null}
                {selectedInvoice.proofs.length > 0 ? selectedInvoice.proofs.map((proof) => (
                  <article key={proof.label + "-" + proof.method} className="po2-decision-item">
                    <StatusBadge tone={proof.status === "bad" ? "bad" : proof.status === "warn" ? "warn" : proof.status === "ok" ? "ok" : "info"}>{proof.status.toUpperCase()}</StatusBadge>
                    <strong>{proof.label}</strong>
                    <small>{proof.method}{proof.reference ? " · réf. " + proof.reference : ""}</small>
                  </article>
                )) : (
                  <article className="po2-decision-item">
                    <StatusBadge tone="info">INFO</StatusBadge>
                    <strong>Trace à construire</strong>
                    <small>Le raccordement devra fournir les preuves ligne par ligne.</small>
                  </article>
                )}
              </div>
            </Card>

            <Card title="Imputation comptable" eyebrow="Appliquer la matrice → valider → transmettre">
              {selectedInvoice.source === "mock" ? (
                <p className="po2-muted-line">Facture de démonstration : actions comptables désactivées.</p>
              ) : (
                <div className="po2-invoice-actions">
                  <label className="po2-invoice-actions__field">
                    <span>Matrice contrat</span>
                    <select
                      value={effectiveContractId ?? ""}
                      onChange={(event) => setMatrixContractId(event.target.value ? Number(event.target.value) : null)}
                    >
                      <option value="">— choisir une matrice —</option>
                      {matrixContracts.map((contract) => (
                        <option key={contract.id} value={contract.id}>
                          {contract.supplier} · {contract.contract_code ?? contract.contract_label ?? "#" + contract.id}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="po2-invoice-actions__buttons">
                    <Button
                      onClick={() => effectiveContractId && actions.apply.mutate({ matrix_contract_id: effectiveContractId })}
                      disabled={!effectiveContractId || actions.apply.isPending}
                    >
                      {actions.apply.isPending ? "Application…" : "Appliquer la matrice"}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => actions.validate.mutate()}
                      disabled={snapshot.data?.status !== "proposed" || actions.validate.isPending}
                    >
                      {actions.validate.isPending ? "Validation…" : "Valider l’imputation"}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => actions.exportFinance.mutate()}
                      disabled={!(snapshot.data?.status === "validated" || snapshot.data?.status === "manual_override") || actions.exportFinance.isPending}
                    >
                      {actions.exportFinance.isPending ? "Transmission…" : "Exporter aux finances"}
                    </Button>
                  </div>
                  {actionError(actions.apply.error) ? <p className="po2-action-error">Application : {actionError(actions.apply.error)}</p> : null}
                  {actionError(actions.validate.error) ? <p className="po2-action-error">Validation : {actionError(actions.validate.error)}</p> : null}
                  {actionError(actions.exportFinance.error) ? <p className="po2-action-error">Export : {actionError(actions.exportFinance.error)}</p> : null}
                  {actions.exportFinance.isSuccess ? <p className="po2-muted-line">Transmise aux finances ✓</p> : null}
                </div>
              )}
            </Card>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
