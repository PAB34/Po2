import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import BpuTimelineChart from "../components/BpuTimelineChart";
import { useAuth } from "../providers/AuthProvider";
import {
  fetchBpuDocuments,
  fetchBpuFormula,
  fetchBpuTimeline,
  triggerBpuImport,
  BpuDocumentSummary,
  BpuFormula,
  BpuImportResponse,
  BpuTimelineFilters,
  BpuTimelinePoint,
} from "../lib/api";

const STATUS_BADGE_CLASS: Record<string, string> = {
  ok: "badge-green",
  ocr_ok: "badge-blue",
  ocr_review: "badge-orange",
  manual: "badge-gray",
  pending: "badge-gray",
  error: "badge-red",
};

const STATUS_LABEL: Record<string, string> = {
  ok: "OK (texte)",
  ocr_ok: "OK (OCR)",
  ocr_review: "À revoir",
  manual: "Saisie manuelle",
  pending: "Non importé",
  error: "Erreur",
};

function uniq<T extends string | number>(values: (T | null | undefined)[]): T[] {
  const set = new Set<T>();
  for (const v of values) {
    if (v == null) continue;
    set.add(v);
  }
  return Array.from(set).sort((a, b) => String(a).localeCompare(String(b)));
}

export default function EnergieBpuPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  // Filtres du graphique (séparés des filtres de liste pour clarté)
  const [chartFilters, setChartFilters] = useState<BpuTimelineFilters>({
    segment_code: "C4",
    period_code: "HPH",
  });

  // Filtres de la liste documents
  const [docSupplier, setDocSupplier] = useState<string>("");
  const [docYear, setDocYear] = useState<string>("");
  const [docLot, setDocLot] = useState<string>("");
  const [docStatus, setDocStatus] = useState<string>("");

  const formulaQuery = useQuery<BpuFormula>({
    queryKey: ["bpu", "formula"],
    queryFn: () => fetchBpuFormula(token ?? ""),
    enabled: !!token,
  });

  const docsQuery = useQuery<BpuDocumentSummary[]>({
    queryKey: ["bpu", "documents", docSupplier, docYear, docLot, docStatus],
    queryFn: () =>
      fetchBpuDocuments(token ?? "", {
        supplier: docSupplier || undefined,
        valid_year: docYear ? Number(docYear) : undefined,
        lot_number: docLot ? Number(docLot) : undefined,
        extraction_status: docStatus || undefined,
      }),
    enabled: !!token,
  });

  const timelineQuery = useQuery<BpuTimelinePoint[]>({
    queryKey: ["bpu", "timeline", chartFilters],
    queryFn: () => fetchBpuTimeline(token ?? "", chartFilters),
    enabled: !!token,
  });

  const importMutation = useMutation<BpuImportResponse, Error, { force: boolean }>({
    mutationFn: ({ force }) =>
      triggerBpuImport(token ?? "", { force, enable_ocr: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bpu"] });
    },
  });

  const segmentChoices = useMemo(
    () => formulaQuery.data?.segments ?? [],
    [formulaQuery.data],
  );
  const periodChoices = useMemo(
    () => formulaQuery.data?.periods ?? [],
    [formulaQuery.data],
  );

  const supplierOptions = useMemo(
    () => uniq((docsQuery.data ?? []).map((d) => d.supplier)),
    [docsQuery.data],
  );
  const yearOptions = useMemo(
    () => uniq((docsQuery.data ?? []).map((d) => d.valid_year)),
    [docsQuery.data],
  );

  const stats = useMemo(() => {
    const docs = docsQuery.data ?? [];
    const byStatus: Record<string, number> = {};
    for (const d of docs) byStatus[d.extraction_status] = (byStatus[d.extraction_status] ?? 0) + 1;
    return { total: docs.length, byStatus };
  }, [docsQuery.data]);

  if (!token) {
    return (
      <div className="p-8 text-sm text-slate-500">
        Vous devez être connecté pour consulter les BPU.
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <header className="space-y-1">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Link to="/energie" className="underline hover:text-slate-700 dark:hover:text-slate-300">
            Énergie
          </Link>
          <span>›</span>
          <span>Historique des BPU</span>
        </div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
          Bordereaux de Prix Unitaires — suivi temporel
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Évolution des composantes de la formule de tarification (Fourniture, Capacité,
          CEE, Garanties d'Origine) sur les marchés subséquents Hérault Énergies
          de 2021 à 2026. Les valeurs alimentent le même calcul que la page
          <Link to="/energie/preconisations" className="underline ml-1">préconisations</Link>.
        </p>
      </header>

      {/* Stats import */}
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="BPU stockés" value={stats.total} />
        <StatCard
          label="OK texte"
          value={stats.byStatus.ok ?? 0}
          tone="green"
        />
        <StatCard
          label="OK OCR"
          value={stats.byStatus.ocr_ok ?? 0}
          tone="blue"
        />
        <StatCard
          label="À revoir"
          value={(stats.byStatus.ocr_review ?? 0) + (stats.byStatus.error ?? 0)}
          tone="orange"
        />
      </section>

      {/* Graphique évolution */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-lg font-medium text-slate-900 dark:text-slate-100">
              Évolution de la formule de prix
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Une courbe par composante × année. Filtrez par segment tarifaire et poste
              pour comparer un même profil d'année en année.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Select
              label="Segment"
              value={chartFilters.segment_code ?? ""}
              onChange={(v) => setChartFilters((f) => ({ ...f, segment_code: v || undefined }))}
              options={[
                { value: "", label: "Tous" },
                ...segmentChoices.map((s) => ({ value: s.code, label: `${s.code} — ${s.label}` })),
              ]}
            />
            <Select
              label="Poste"
              value={chartFilters.period_code ?? ""}
              onChange={(v) => setChartFilters((f) => ({ ...f, period_code: v || undefined }))}
              options={[
                { value: "", label: "Tous" },
                ...periodChoices.map((p) => ({ value: p.code, label: `${p.code} — ${p.label}` })),
              ]}
            />
            <Select
              label="Fournisseur"
              value={chartFilters.supplier ?? ""}
              onChange={(v) => setChartFilters((f) => ({ ...f, supplier: v || undefined }))}
              options={[
                { value: "", label: "Tous" },
                { value: "EDF", label: "EDF" },
                { value: "ENGIE", label: "ENGIE" },
              ]}
            />
            <Select
              label="Lot"
              value={chartFilters.lot_number?.toString() ?? ""}
              onChange={(v) =>
                setChartFilters((f) => ({ ...f, lot_number: v ? Number(v) : undefined }))
              }
              options={[
                { value: "", label: "Tous" },
                { value: "1", label: "Lot 1" },
                { value: "2", label: "Lot 2" },
                { value: "3", label: "Lot 3" },
              ]}
            />
          </div>
        </div>

        {timelineQuery.isLoading ? (
          <div className="py-12 text-center text-sm text-slate-500">Chargement…</div>
        ) : timelineQuery.isError ? (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            Erreur : {(timelineQuery.error as Error).message}
          </div>
        ) : (
          <BpuTimelineChart
            points={timelineQuery.data ?? []}
            formula={formulaQuery.data}
            includeTotal
          />
        )}
      </section>

      {/* Légende formule */}
      {formulaQuery.data && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-3 text-lg font-medium text-slate-900 dark:text-slate-100">
            Composantes de la formule
          </h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
            {formulaQuery.data.components.map((c) => (
              <div
                key={c.code}
                className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-700 dark:bg-slate-800/50"
              >
                <div className="font-medium text-slate-900 dark:text-slate-100">
                  {c.label}
                </div>
                <div className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                  {c.description}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Liste documents */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-lg font-medium text-slate-900 dark:text-slate-100">
              Documents BPU importés
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Un BPU = un PDF source identifié par fournisseur × année × marché × lot × avenant.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Select
              label="Fournisseur"
              value={docSupplier}
              onChange={setDocSupplier}
              options={[
                { value: "", label: "Tous" },
                ...supplierOptions.map((s) => ({ value: s, label: s })),
              ]}
            />
            <Select
              label="Année"
              value={docYear}
              onChange={setDocYear}
              options={[
                { value: "", label: "Toutes" },
                ...yearOptions.map((y) => ({ value: String(y), label: String(y) })),
              ]}
            />
            <Select
              label="Lot"
              value={docLot}
              onChange={setDocLot}
              options={[
                { value: "", label: "Tous" },
                { value: "1", label: "Lot 1" },
                { value: "2", label: "Lot 2" },
                { value: "3", label: "Lot 3" },
              ]}
            />
            <Select
              label="Statut"
              value={docStatus}
              onChange={setDocStatus}
              options={[
                { value: "", label: "Tous" },
                { value: "ok", label: "OK (texte)" },
                { value: "ocr_ok", label: "OK (OCR)" },
                { value: "ocr_review", label: "À revoir" },
                { value: "error", label: "Erreur" },
              ]}
            />
          </div>
        </div>

        {docsQuery.isLoading ? (
          <div className="py-8 text-center text-sm text-slate-500">Chargement…</div>
        ) : docsQuery.isError ? (
          <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {(docsQuery.error as Error).message}
          </div>
        ) : (docsQuery.data ?? []).length === 0 ? (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-400">
            Aucun BPU importé. Cliquez « Importer depuis le serveur » pour ingérer les PDFs.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500 dark:bg-slate-800/50 dark:text-slate-400">
                <tr>
                  <th className="px-3 py-2">Fournisseur</th>
                  <th className="px-3 py-2">Année</th>
                  <th className="px-3 py-2">MS</th>
                  <th className="px-3 py-2">Lot</th>
                  <th className="px-3 py-2">Avenant</th>
                  <th className="px-3 py-2">Statut</th>
                  <th className="px-3 py-2">Confiance</th>
                  <th className="px-3 py-2">Fichier source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                {(docsQuery.data ?? []).map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    <td className="px-3 py-2 font-medium text-slate-900 dark:text-slate-100">
                      {d.supplier}
                    </td>
                    <td className="px-3 py-2">{d.valid_year}</td>
                    <td className="px-3 py-2">{d.market_subsequent ?? "—"}</td>
                    <td className="px-3 py-2">{d.lot_number}</td>
                    <td className="px-3 py-2">
                      {d.amendment_number != null
                        ? `Avenant ${d.amendment_number}`
                        : d.amendment_label ?? "—"}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-flex rounded px-2 py-0.5 text-xs ${
                          STATUS_BADGE_CLASS[d.extraction_status] ?? "badge-gray"
                        }`}
                      >
                        {STATUS_LABEL[d.extraction_status] ?? d.extraction_status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-600 dark:text-slate-400">
                      {d.extraction_confidence != null
                        ? `${(Number(d.extraction_confidence) * 100).toFixed(0)} %`
                        : "—"}
                    </td>
                    <td
                      className="max-w-[280px] truncate px-3 py-2 text-xs text-slate-500 dark:text-slate-400"
                      title={d.pdf_filename}
                    >
                      {d.pdf_filename}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Actions admin */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        <h2 className="mb-2 text-lg font-medium text-slate-900 dark:text-slate-100">
          Import des PDFs côté serveur
        </h2>
        <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
          Lance l'ingestion du répertoire <code>saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/</code>.
          Les PDFs textuels sont parsés directement, les scans passent par OCR
          (tesseract + français). Les imports sont idempotents : un BPU déjà
          présent est mis à jour (raw_text + statut) sans toucher aux corrections
          manuelles éventuelles, sauf si « Forcer le remplacement » est coché.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => importMutation.mutate({ force: false })}
            disabled={importMutation.isPending}
            className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {importMutation.isPending ? "Import en cours…" : "Importer depuis le serveur"}
          </button>
          <button
            type="button"
            onClick={() => importMutation.mutate({ force: true })}
            disabled={importMutation.isPending}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Forcer le remplacement
          </button>
        </div>
        {importMutation.isError && (
          <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {(importMutation.error as Error).message}
          </div>
        )}
        {importMutation.data && (
          <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-700 dark:bg-slate-800/50">
            <div className="mb-1 font-medium text-slate-700 dark:text-slate-200">
              Résultat de l'import
            </div>
            <div className="text-slate-600 dark:text-slate-300">
              {importMutation.data.total} fichiers · {importMutation.data.succeeded} OK ·{" "}
              {importMutation.data.failed} erreurs · {importMutation.data.skipped} skippés
            </div>
            <details className="mt-2 cursor-pointer">
              <summary className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
                Détails par fichier
              </summary>
              <ul className="mt-2 space-y-1 font-mono text-[11px]">
                {importMutation.data.results.map((r) => (
                  <li key={r.filename}>
                    <span
                      className={`mr-2 inline-block w-16 ${
                        r.status === "error" ? "text-red-600" : "text-slate-500"
                      }`}
                    >
                      [{r.status}]
                    </span>
                    {r.filename}
                    {r.segments_count > 0 &&
                      ` — ${r.segments_count} segments, ${r.components_count} prix`}
                    {r.error && <span className="text-red-600"> · {r.error}</span>}
                  </li>
                ))}
              </ul>
            </details>
          </div>
        )}
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sous-composants UI locaux
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: number;
  tone?: "default" | "green" | "blue" | "orange";
}) {
  const toneClasses: Record<string, string> = {
    default: "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900",
    green:
      "border-emerald-200 bg-emerald-50 dark:border-emerald-700/50 dark:bg-emerald-900/20",
    blue: "border-blue-200 bg-blue-50 dark:border-blue-700/50 dark:bg-blue-900/20",
    orange:
      "border-amber-200 bg-amber-50 dark:border-amber-700/50 dark:bg-amber-900/20",
  };
  return (
    <div className={`rounded-lg border p-3 ${toneClasses[tone]}`}>
      <div className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
        {value}
      </div>
      <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="flex flex-col gap-0.5 text-xs text-slate-600 dark:text-slate-400">
      <span>{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-w-[140px] rounded-md border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
