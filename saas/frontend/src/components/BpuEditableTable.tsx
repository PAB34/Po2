import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../providers/AuthProvider";
import {
  fetchBpuEditableRows,
  updateBpuComponent,
  BpuEditableRow,
} from "../lib/api";

/**
 * Tableau éditable des composants de prix BPU.
 *
 * UX type Excel : cliquer une cellule, la modifier, cliquer "Enregistrer".
 * Modifications stockées localement (`pendingEdits`), envoyées en batch
 * via `updateBpuComponent` au clic du bouton.
 */
type ColumnKey =
  | "price_value"
  | "price_unit"
  | "component_label"
  | "notes";

type PendingEdit = Partial<Record<ColumnKey, string>>;

const EDITABLE_COLUMNS: { key: ColumnKey; label: string; width: string; numeric?: boolean }[] = [
  { key: "price_value", label: "Prix", width: "w-24", numeric: true },
  { key: "price_unit", label: "Unité", width: "w-32" },
  { key: "component_label", label: "Libellé composante", width: "w-48" },
  { key: "notes", label: "Notes", width: "w-64" },
];

const COMPONENT_COLORS: Record<string, string> = {
  fourniture: "bg-blue-50 dark:bg-blue-900/20",
  capacite: "bg-amber-50 dark:bg-amber-900/20",
  cee: "bg-emerald-50 dark:bg-emerald-900/20",
  go: "bg-violet-50 dark:bg-violet-900/20",
  renouvelable: "bg-violet-50 dark:bg-violet-900/20",
  autre: "bg-slate-50 dark:bg-slate-800/30",
};

export default function BpuEditableTable() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  // Filtres
  const [filterSupplier, setFilterSupplier] = useState<string>("");
  const [filterYear, setFilterYear] = useState<string>("");

  // Modifications en attente : map (rowId -> { col -> nouvelle valeur })
  const [pendingEdits, setPendingEdits] = useState<Map<number, PendingEdit>>(new Map());
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<{ ok: number; fail: number } | null>(null);

  const rowsQuery = useQuery<BpuEditableRow[]>({
    queryKey: ["bpu", "editable", filterSupplier, filterYear],
    queryFn: () =>
      fetchBpuEditableRows(token ?? "", {
        supplier: filterSupplier || undefined,
        valid_year: filterYear ? Number(filterYear) : undefined,
      }),
    enabled: !!token,
  });

  // Reset modifs si filtres changent (= dataset différent)
  useEffect(() => {
    setPendingEdits(new Map());
    setSaveSuccess(null);
    setSaveError(null);
  }, [filterSupplier, filterYear]);

  const supplierOptions = useMemo(() => {
    const set = new Set<string>();
    for (const r of rowsQuery.data ?? []) set.add(r.supplier);
    return Array.from(set).sort();
  }, [rowsQuery.data]);

  const yearOptions = useMemo(() => {
    const set = new Set<number>();
    for (const r of rowsQuery.data ?? []) set.add(r.valid_year);
    return Array.from(set).sort();
  }, [rowsQuery.data]);

  const hasPending = pendingEdits.size > 0;
  const pendingCount = useMemo(() => {
    let n = 0;
    for (const edit of pendingEdits.values()) n += Object.keys(edit).length;
    return n;
  }, [pendingEdits]);

  function setCellValue(rowId: number, key: ColumnKey, value: string) {
    setPendingEdits((prev) => {
      const next = new Map(prev);
      const current = next.get(rowId) ?? {};
      next.set(rowId, { ...current, [key]: value });
      return next;
    });
    setSaveSuccess(null);
  }

  function getDisplayValue(row: BpuEditableRow, key: ColumnKey): string {
    const pending = pendingEdits.get(row.component_id)?.[key];
    if (pending !== undefined) return pending;
    const raw = (row as unknown as Record<string, string | null>)[key];
    return raw ?? "";
  }

  function isDirty(rowId: number, key: ColumnKey): boolean {
    const pending = pendingEdits.get(rowId);
    return pending !== undefined && pending[key] !== undefined;
  }

  async function saveAll() {
    if (!token || !hasPending) return;
    setIsSaving(true);
    setSaveError(null);
    let ok = 0;
    let fail = 0;
    const errors: string[] = [];

    for (const [rowId, edit] of pendingEdits.entries()) {
      try {
        const payload: Record<string, unknown> = {};
        for (const [k, v] of Object.entries(edit)) {
          if (k === "price_value") {
            const num = Number(String(v).replace(",", "."));
            if (Number.isFinite(num)) payload.price_value = num;
          } else {
            payload[k] = v === "" ? null : v;
          }
        }
        await updateBpuComponent(token, rowId, payload);
        ok += 1;
      } catch (e) {
        fail += 1;
        errors.push(`#${rowId}: ${(e as Error).message}`);
      }
    }

    setIsSaving(false);
    setSaveSuccess({ ok, fail });
    if (errors.length > 0) setSaveError(errors.join(" · "));
    if (fail === 0) setPendingEdits(new Map());
    queryClient.invalidateQueries({ queryKey: ["bpu", "editable"] });
    queryClient.invalidateQueries({ queryKey: ["bpu", "timeline"] });
    queryClient.invalidateQueries({ queryKey: ["bpu", "documents"] });
  }

  function cancelAll() {
    setPendingEdits(new Map());
    setSaveSuccess(null);
    setSaveError(null);
  }

  if (rowsQuery.isLoading) {
    return <div className="p-6 text-sm text-slate-500">Chargement…</div>;
  }
  if (rowsQuery.isError) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {(rowsQuery.error as Error).message}
      </div>
    );
  }
  const rows = rowsQuery.data ?? [];

  return (
    <div className="space-y-3">
      {/* Barre filtres + actions */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          <label className="flex flex-col gap-0.5 text-xs text-slate-600 dark:text-slate-400">
            <span>Fournisseur</span>
            <select
              value={filterSupplier}
              onChange={(e) => setFilterSupplier(e.target.value)}
              className="min-w-[140px] rounded-md border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="">Tous</option>
              {supplierOptions.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-0.5 text-xs text-slate-600 dark:text-slate-400">
            <span>Année</span>
            <select
              value={filterYear}
              onChange={(e) => setFilterYear(e.target.value)}
              className="min-w-[100px] rounded-md border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="">Toutes</option>
              {yearOptions.map((y) => (
                <option key={y} value={String(y)}>{y}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="flex items-center gap-2">
          {hasPending && (
            <span className="rounded-md bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
              {pendingCount} modif{pendingCount > 1 ? "s" : ""} non enregistrée{pendingCount > 1 ? "s" : ""}
            </span>
          )}
          <button
            type="button"
            onClick={cancelAll}
            disabled={!hasPending || isSaving}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Annuler
          </button>
          <button
            type="button"
            onClick={saveAll}
            disabled={!hasPending || isSaving}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isSaving ? "Enregistrement…" : "Enregistrer"}
          </button>
        </div>
      </div>

      {saveError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          Erreurs : {saveError}
        </div>
      )}
      {saveSuccess && !saveError && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 p-2 text-xs text-emerald-700 dark:border-emerald-700/40 dark:bg-emerald-900/20 dark:text-emerald-200">
          {saveSuccess.ok} composante{saveSuccess.ok > 1 ? "s" : ""} enregistrée{saveSuccess.ok > 1 ? "s" : ""}
          {saveSuccess.fail > 0 && ` · ${saveSuccess.fail} en erreur`}
        </div>
      )}

      {/* Stats compteur */}
      <div className="text-xs text-slate-500 dark:text-slate-400">
        {rows.length} composantes affichées
      </div>

      {/* Tableau éditable */}
      {rows.length === 0 ? (
        <div className="rounded-md border border-slate-200 bg-slate-50 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-400">
          Aucune composante avec ces filtres.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
          <table className="min-w-full text-xs">
            <thead className="bg-slate-50 text-left text-[10px] uppercase tracking-wide text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
              <tr>
                <th className="px-2 py-2">BPU</th>
                <th className="px-2 py-2">Segment</th>
                <th className="px-2 py-2">Poste</th>
                <th className="px-2 py-2">Composante</th>
                {EDITABLE_COLUMNS.map((c) => (
                  <th key={c.key} className={`px-2 py-2 ${c.width}`}>{c.label}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {rows.map((row) => (
                <tr
                  key={row.component_id}
                  className={`${COMPONENT_COLORS[row.component_type] ?? ""} hover:brightness-95 dark:hover:brightness-110`}
                >
                  <td className="px-2 py-1.5 align-top text-slate-600 dark:text-slate-300">
                    <div className="font-medium text-slate-900 dark:text-slate-100">
                      {row.supplier} {row.valid_year}
                    </div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400">
                      lot{row.lot_number}
                      {row.market_subsequent ? ` · MS${row.market_subsequent}` : ""}
                      {row.amendment_number ? ` · av${row.amendment_number}` : ""}
                    </div>
                  </td>
                  <td className="px-2 py-1.5 align-top">
                    <div className="font-mono text-slate-700 dark:text-slate-200">{row.segment_code}</div>
                    {row.segment_label && (
                      <div className="text-[10px] text-slate-500 dark:text-slate-400" title={row.segment_label}>
                        {row.segment_label.length > 35 ? row.segment_label.slice(0, 35) + "…" : row.segment_label}
                      </div>
                    )}
                  </td>
                  <td className="px-2 py-1.5 align-top font-mono text-slate-700 dark:text-slate-200">
                    {row.period_code}
                  </td>
                  <td className="px-2 py-1.5 align-top font-medium capitalize text-slate-800 dark:text-slate-100">
                    {row.component_type}
                  </td>
                  {EDITABLE_COLUMNS.map((col) => {
                    const dirty = isDirty(row.component_id, col.key);
                    return (
                      <td key={col.key} className="px-1 py-1 align-top">
                        <input
                          type={col.numeric ? "text" : "text"}
                          value={getDisplayValue(row, col.key)}
                          onChange={(e) => setCellValue(row.component_id, col.key, e.target.value)}
                          inputMode={col.numeric ? "decimal" : undefined}
                          className={`w-full rounded border px-2 py-1 text-xs ${
                            dirty
                              ? "border-amber-400 bg-amber-50 dark:border-amber-500 dark:bg-amber-900/30"
                              : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800"
                          } text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:text-slate-100`}
                        />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
