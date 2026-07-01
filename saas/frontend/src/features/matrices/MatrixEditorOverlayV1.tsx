import { useState } from "react";
import { Button, StatusBadge } from "../../design-system";
import type { AccountingMatrixRuleUpdateV1, AccountingMatrixRuleV1, AccountingMatrixVersionV1 } from "../../lib/api";
import {
  useCommitMatrixImportV1,
  useCreateMatrixRuleV1,
  useDeleteMatrixRuleV1,
  useExportMatrixVersionV1,
  useMatrixContractDetailV1,
  useMatrixVersionRulesV1,
  usePreviewMatrixImportV1,
  useUpdateMatrixRuleV1,
} from "./useMatricesV1";

type Props = {
  contractId: number;
  canWrite: boolean;
  onClose: () => void;
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

// Colonnes éditables retenues (décision 2026-07-01) : axes comptables uniquement.
type EditableField =
  | "billed_item_pattern"
  | "accounting_service"
  | "accounting_function"
  | "accounting_antenna"
  | "operation_number"
  | "accounting_nature"
  | "accounting_label";

const TEXT_COLS: { field: EditableField; label: string }[] = [
  { field: "billed_item_pattern", label: "Poste facturé" },
  { field: "accounting_service", label: "Service" },
  { field: "accounting_function", label: "Fonction" },
  { field: "accounting_antenna", label: "Antenne" },
  { field: "operation_number", label: "Opération" },
  { field: "accounting_nature", label: "Nature" },
  { field: "accounting_label", label: "Libellé nature" },
];

export function MatrixEditorOverlayV1({ contractId, canWrite, onClose }: Props) {
  const detail = useMatrixContractDetailV1(contractId);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [importVersionLabel, setImportVersionLabel] = useState("");

  const versions = detail.data?.versions ?? [];
  const activeVersionId = detail.data?.active_version_id ?? null;
  const versionId = selectedVersionId ?? activeVersionId ?? versions[0]?.id ?? null;
  const currentVersion = versions.find((v) => v.id === versionId) ?? null;
  const editable = canWrite && currentVersion != null && currentVersion.status !== "archived";

  const rules = useMatrixVersionRulesV1(versionId);
  const createRule = useCreateMatrixRuleV1(versionId);
  const updateRule = useUpdateMatrixRuleV1(versionId);
  const deleteRule = useDeleteMatrixRuleV1(versionId);
  const exportVersion = useExportMatrixVersionV1();
  const importPreview = usePreviewMatrixImportV1();
  const importCommit = useCommitMatrixImportV1();

  function commitField(rule: AccountingMatrixRuleV1, field: EditableField, raw: string) {
    const value = raw.trim() === "" ? null : raw.trim();
    if ((rule[field] ?? null) === value) return;
    const payload = { [field]: value } as AccountingMatrixRuleUpdateV1;
    updateRule.mutate({ ruleId: rule.id, payload });
  }

  function commitPercent(rule: AccountingMatrixRuleV1, raw: string) {
    const value = Number(raw);
    if (Number.isNaN(value) || value === rule.allocation_percent) return;
    updateRule.mutate({ ruleId: rule.id, payload: { allocation_percent: value } });
  }

  function handleAddRule() {
    if (!versionId) return;
    createRule.mutate({ stable_rule_key: `manuel-${Date.now()}`, scope: "billed_item", allocation_percent: 100 });
  }

  function handleImportFile(file: File | null) {
    if (!file || !contractId) return;
    importPreview.mutate({ contractId, file });
  }

  function handleCommitImport(file: File | null) {
    if (!file || !contractId) return;
    importCommit.mutate(
      { contractId, file, versionLabel: importVersionLabel.trim() || `Import ${new Date().toISOString().slice(0, 10)}` },
      { onSuccess: () => setImportVersionLabel("") },
    );
  }

  const title = detail.data
    ? `${detail.data.supplier}${detail.data.contract_code ? " · " + detail.data.contract_code : ""}`
    : "Matrice comptable";

  return (
    <div className="po2-matrix-editor-backdrop" role="dialog" aria-modal="true">
      <div className="po2-matrix-editor">
        <header className="po2-matrix-editor__head">
          <div>
            <span className="po2-eyebrow">Édition matrice comptable</span>
            <h2>{title}</h2>
            {detail.data?.contract_label ? <small className="po2-muted-line">{detail.data.contract_label}</small> : null}
          </div>
          <div className="po2-matrix-editor__head-actions">
            <label className="po2-matrix-editor__version">
              <span>Version</span>
              <select
                value={versionId ?? ""}
                onChange={(e) => setSelectedVersionId(Number(e.currentTarget.value) || null)}
              >
                {versions.map((v: AccountingMatrixVersionV1) => (
                  <option key={v.id} value={v.id}>
                    {v.version_label} ({v.status})
                  </option>
                ))}
              </select>
            </label>
            {currentVersion ? <StatusBadge tone={versionTone(currentVersion.status)}>{currentVersion.status}</StatusBadge> : null}
            <Button variant="ghost" onClick={onClose}>Fermer</Button>
          </div>
        </header>

        <div className="po2-matrix-editor__toolbar">
          <Button
            variant="ghost"
            onClick={() => versionId && exportVersion.mutate({ versionId, label: detail.data?.contract_code ?? detail.data?.supplier })}
            disabled={!versionId || exportVersion.isPending}
          >
            {exportVersion.isPending ? "Export..." : "Exporter XLSX"}
          </Button>
          <label className="po2-matrix-editor__import">
            <span>Importer une mise à jour (XLSX)</span>
            <input
              type="file"
              accept=".xlsx"
              disabled={!canWrite}
              onChange={(e) => handleImportFile(e.currentTarget.files?.[0] ?? null)}
            />
          </label>
          {importPreview.data ? (
            <span className="po2-muted-line">
              Aperçu : {importPreview.data.summary?.ajout ?? 0} ajout(s), {importPreview.data.summary?.modifie ?? 0} modif.
              {importPreview.data.can_commit ? (
                <>
                  {" "}
                  <input
                    type="text"
                    placeholder="Nom version"
                    value={importVersionLabel}
                    onChange={(e) => setImportVersionLabel(e.currentTarget.value)}
                  />
                  <Button
                    variant="secondary"
                    onClick={() => {
                      const input = document.querySelector<HTMLInputElement>(".po2-matrix-editor__import input");
                      handleCommitImport(input?.files?.[0] ?? null);
                    }}
                    disabled={importCommit.isPending}
                  >
                    {importCommit.isPending ? "Création..." : "Créer version brouillon"}
                  </Button>
                </>
              ) : (
                " (commit bloqué)"
              )}
            </span>
          ) : null}
          {canWrite ? (
            <Button variant="primary" onClick={handleAddRule} disabled={!editable || createRule.isPending}>
              {createRule.isPending ? "Ajout..." : "+ Ajouter une règle"}
            </Button>
          ) : null}
        </div>

        {!editable && currentVersion ? (
          <p className="po2-muted-line po2-matrix-editor__note">
            {!canWrite
              ? "Lecture seule : ton rôle ne permet pas d'éditer la matrice."
              : "Version archivée (historique figé) : sélectionne la version active pour éditer."}
          </p>
        ) : null}
        {updateRule.isError ? <p className="po2-muted-line">Enregistrement impossible : {errorMessage(updateRule.error)}</p> : null}
        {createRule.isError ? <p className="po2-muted-line">Ajout impossible : {errorMessage(createRule.error)}</p> : null}
        {importPreview.isError ? <p className="po2-muted-line">Aperçu impossible : {errorMessage(importPreview.error)}</p> : null}
        {importCommit.isSuccess ? <p className="po2-muted-line">Version brouillon créée : {importCommit.data.version_label}.</p> : null}

        <div className="po2-matrix-editor__table-wrap">
          {rules.isFetching && !rules.data ? (
            <p className="po2-muted-line">Chargement des règles...</p>
          ) : (
            <table className="po2-matrix-editor__table">
              <thead>
                <tr>
                  {TEXT_COLS.map((c) => (
                    <th key={c.field}>{c.label}</th>
                  ))}
                  <th>%</th>
                  <th>Actif</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {(rules.data ?? []).map((rule) => (
                  <tr key={rule.id}>
                    {TEXT_COLS.map((c) => (
                      <td key={c.field}>
                        <input
                          type="text"
                          defaultValue={rule[c.field] ?? ""}
                          disabled={!editable}
                          onBlur={(e) => commitField(rule, c.field, e.currentTarget.value)}
                        />
                      </td>
                    ))}
                    <td className="po2-matrix-editor__pct">
                      <input
                        type="number"
                        defaultValue={rule.allocation_percent}
                        disabled={!editable}
                        onBlur={(e) => commitPercent(rule, e.currentTarget.value)}
                      />
                    </td>
                    <td>
                      <input
                        type="checkbox"
                        checked={rule.is_active}
                        disabled={!editable}
                        onChange={(e) => updateRule.mutate({ ruleId: rule.id, payload: { is_active: e.currentTarget.checked } })}
                      />
                    </td>
                    <td>
                      <Button
                        variant="ghost"
                        onClick={() => deleteRule.mutate(rule.id)}
                        disabled={!editable || deleteRule.isPending}
                      >
                        Suppr.
                      </Button>
                    </td>
                  </tr>
                ))}
                {(rules.data ?? []).length === 0 && !rules.isFetching ? (
                  <tr>
                    <td colSpan={TEXT_COLS.length + 3} className="po2-muted-line">
                      Aucune règle. {editable ? "Ajoute une première règle ci-dessus." : ""}
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
