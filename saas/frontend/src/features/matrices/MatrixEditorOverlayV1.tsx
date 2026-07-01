import { useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
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

type EditableField =
  | "billed_item_pattern"
  | "accounting_service"
  | "accounting_function"
  | "accounting_antenna"
  | "operation_number"
  | "accounting_nature"
  | "accounting_label";

type ColId = "site_designation" | EditableField | "allocation_percent" | "is_active";

const COLUMNS: { id: ColId; label: string; width: number; kind: "ro" | "text" | "number" | "bool" }[] = [
  { id: "site_designation", label: "Désignation site (facture)", width: 220, kind: "ro" },
  { id: "billed_item_pattern", label: "Poste facturé", width: 130, kind: "text" },
  { id: "accounting_service", label: "Service", width: 110, kind: "text" },
  { id: "accounting_function", label: "Fonction", width: 100, kind: "text" },
  { id: "accounting_antenna", label: "Antenne", width: 130, kind: "text" },
  { id: "operation_number", label: "Opération", width: 110, kind: "text" },
  { id: "accounting_nature", label: "Nature", width: 100, kind: "text" },
  { id: "accounting_label", label: "Libellé nature", width: 160, kind: "text" },
  { id: "allocation_percent", label: "%", width: 70, kind: "number" },
  { id: "is_active", label: "Actif", width: 60, kind: "bool" },
];

const WIDTHS_KEY = "po2-matrix-editor-widths";

function loadWidths(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(WIDTHS_KEY) || "{}");
  } catch {
    return {};
  }
}

function ruleValue(rule: AccountingMatrixRuleV1, id: ColId): string | number {
  if (id === "allocation_percent") return rule.allocation_percent;
  if (id === "is_active") return rule.is_active ? 1 : 0;
  const v = (rule as unknown as Record<string, unknown>)[id];
  return typeof v === "string" ? v : v == null ? "" : String(v);
}

export function MatrixEditorOverlayV1({ contractId, canWrite, onClose }: Props) {
  const detail = useMatrixContractDetailV1(contractId);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [sort, setSort] = useState<{ id: ColId; dir: "asc" | "desc" } | null>(null);
  const [widths, setWidths] = useState<Record<string, number>>(loadWidths);
  const resizing = useRef<{ id: string; startX: number; startW: number } | null>(null);

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

  const sortedRules = useMemo(() => {
    const data = rules.data ?? [];
    if (!sort) return data;
    const factor = sort.dir === "asc" ? 1 : -1;
    return [...data].sort((a, b) => {
      const va = ruleValue(a, sort.id);
      const vb = ruleValue(b, sort.id);
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * factor;
      return String(va).localeCompare(String(vb)) * factor;
    });
  }, [rules.data, sort]);

  function commitField(rule: AccountingMatrixRuleV1, field: EditableField, raw: string) {
    const value = raw.trim() === "" ? null : raw.trim();
    if (((rule as unknown as Record<string, unknown>)[field] ?? null) === value) return;
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

  function applySuggestedAntennas() {
    for (const rule of rules.data ?? []) {
      if (!rule.accounting_antenna && rule.suggested_antenna) {
        updateRule.mutate({ ruleId: rule.id, payload: { accounting_antenna: rule.suggested_antenna } });
      }
    }
  }

  function toggleSort(id: ColId) {
    setSort((prev) => (prev && prev.id === id ? { id, dir: prev.dir === "asc" ? "desc" : "asc" } : { id, dir: "asc" }));
  }

  function startResize(id: string, event: ReactMouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    const startW = widths[id] ?? COLUMNS.find((c) => c.id === id)?.width ?? 120;
    resizing.current = { id, startX: event.clientX, startW };
    function onMove(e: MouseEvent) {
      if (!resizing.current) return;
      const next = Math.max(50, resizing.current.startW + (e.clientX - resizing.current.startX));
      setWidths((w) => ({ ...w, [resizing.current!.id]: next }));
    }
    function onUp() {
      if (resizing.current) {
        setWidths((w) => {
          localStorage.setItem(WIDTHS_KEY, JSON.stringify(w));
          return w;
        });
      }
      resizing.current = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }

  const suggestionCount = (rules.data ?? []).filter((r) => !r.accounting_antenna && r.suggested_antenna).length;
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
              <select value={versionId ?? ""} onChange={(e) => setSelectedVersionId(Number(e.currentTarget.value) || null)}>
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
            <input type="file" accept=".xlsx" disabled={!canWrite} onChange={(e) => { const f = e.currentTarget.files?.[0]; if (f) importPreview.mutate({ contractId, file: f }); }} />
          </label>
          {importPreview.data ? (
            <span className="po2-muted-line">
              Aperçu : {importPreview.data.summary?.ajout ?? 0} ajout(s), {importPreview.data.summary?.modifie ?? 0} modif.
              {importPreview.data.can_commit ? (
                <Button
                  variant="secondary"
                  onClick={() => {
                    const input = document.querySelector<HTMLInputElement>(".po2-matrix-editor__import input");
                    const file = input?.files?.[0];
                    if (file) importCommit.mutate({ contractId, file, versionLabel: `Import ${new Date().toISOString().slice(0, 10)}` });
                  }}
                  disabled={importCommit.isPending}
                >
                  {importCommit.isPending ? "Création..." : "Créer version brouillon"}
                </Button>
              ) : " (commit bloqué)"}
            </span>
          ) : null}
          {editable && suggestionCount > 0 ? (
            <Button variant="secondary" onClick={applySuggestedAntennas}>
              Appliquer {suggestionCount} antenne(s) suggérée(s)
            </Button>
          ) : null}
          {canWrite ? (
            <Button variant="primary" onClick={handleAddRule} disabled={!editable || createRule.isPending}>
              {createRule.isPending ? "Ajout..." : "+ Ajouter une règle"}
            </Button>
          ) : null}
        </div>

        {!editable && currentVersion ? (
          <p className="po2-muted-line po2-matrix-editor__note">
            {!canWrite ? "Lecture seule : ton rôle ne permet pas d'éditer la matrice." : "Version archivée (historique figé) : sélectionne la version active pour éditer."}
          </p>
        ) : null}
        {updateRule.isError ? <p className="po2-muted-line">Enregistrement impossible : {errorMessage(updateRule.error)}</p> : null}
        {importPreview.isError ? <p className="po2-muted-line">Aperçu impossible : {errorMessage(importPreview.error)}</p> : null}
        {importCommit.isSuccess ? <p className="po2-muted-line">Version brouillon créée : {importCommit.data.version_label}.</p> : null}

        <div className="po2-matrix-editor__table-wrap">
          {rules.isFetching && !rules.data ? (
            <p className="po2-muted-line">Chargement des règles...</p>
          ) : (
            <table className="po2-matrix-editor__table">
              <thead>
                <tr>
                  {COLUMNS.map((col) => (
                    <th key={col.id} style={{ width: widths[col.id] ?? col.width }}>
                      <button type="button" className="po2-matrix-editor__sort" onClick={() => toggleSort(col.id)}>
                        {col.label}
                        {sort?.id === col.id ? (sort.dir === "asc" ? " ▲" : " ▼") : ""}
                      </button>
                      <span className="po2-matrix-editor__resizer" onMouseDown={(e) => startResize(col.id, e)} />
                    </th>
                  ))}
                  <th aria-label="Actions" style={{ width: 70 }} />
                </tr>
              </thead>
              <tbody>
                {sortedRules.map((rule) => (
                  <tr key={rule.id}>
                    <td className="po2-matrix-editor__ro" title={rule.site_designation ?? ""}>{rule.site_designation ?? "—"}</td>
                    {COLUMNS.filter((c) => c.kind === "text").map((col) => (
                      <td key={col.id}>
                        <input
                          type="text"
                          defaultValue={(rule as unknown as Record<string, string | null>)[col.id] ?? ""}
                          placeholder={col.id === "accounting_antenna" ? rule.suggested_antenna ?? "" : ""}
                          disabled={!editable}
                          onBlur={(e) => commitField(rule, col.id as EditableField, e.currentTarget.value)}
                        />
                      </td>
                    ))}
                    <td className="po2-matrix-editor__pct">
                      <input type="number" defaultValue={rule.allocation_percent} disabled={!editable} onBlur={(e) => commitPercent(rule, e.currentTarget.value)} />
                    </td>
                    <td>
                      <input type="checkbox" checked={rule.is_active} disabled={!editable} onChange={(e) => updateRule.mutate({ ruleId: rule.id, payload: { is_active: e.currentTarget.checked } })} />
                    </td>
                    <td>
                      <Button variant="ghost" onClick={() => deleteRule.mutate(rule.id)} disabled={!editable || deleteRule.isPending}>Suppr.</Button>
                    </td>
                  </tr>
                ))}
                {sortedRules.length === 0 && !rules.isFetching ? (
                  <tr>
                    <td colSpan={COLUMNS.length + 1} className="po2-muted-line">Aucune règle. {editable ? "Ajoute une première règle ci-dessus." : ""}</td>
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
