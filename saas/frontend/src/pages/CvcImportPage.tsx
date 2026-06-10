import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";
import {
  fetchBuildings,
  fetchCvcImportBatches,
  fetchCvcImportItems,
  fetchEquipmentReferences,
  postCvcImport,
  postCvcPreview,
  recomputeCvcImportReferences,
  updateCvcItem,
  type Building,
  type CvcImportBatchSummary,
  type CvcInventoryItem,
  type CvcPreviewResponse,
  type EquipmentReference,
  type UpdateCvcInventoryItemPayload,
} from "../lib/api";

const SUBTLE_TEXT = "#94a3b8";
const NEUTRAL_BORDER = "rgba(148, 163, 184, 0.25)";
const CURRENT_YEAR = new Date().getFullYear();

function compactLabel(parts: Array<string | null | undefined>): string {
  return parts.filter(Boolean).join(" - ");
}

function yearOrNull(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1900 || parsed > CURRENT_YEAR + 1) return null;
  return parsed;
}

function referenceLabel(ref: EquipmentReference): string {
  return compactLabel([
    ref.code_niveau_2,
    ref.niveau_3,
    ref.niveau_4,
    ref.niveau_5,
    ref.equipement,
  ]);
}

function isCvcRelevant(ref: EquipmentReference): boolean {
  return (
    ref.code_niveau_2 === "A.2.1" ||
    ref.code_niveau_2 === "A.2.2" ||
    ref.code_niveau_2 === "A.2.3"
  );
}

function formatPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "-";
  return `${Math.round(value)}%`;
}

function formatRemainingLife(item: CvcInventoryItem): string {
  if (item.duree_vie_restante === null) return "Non calculable";
  if (item.duree_vie_restante < 0) return `${Math.abs(item.duree_vie_restante)} ans depasses`;
  return `${item.duree_vie_restante} ans restants`;
}

function familyColor(index: number): string {
  return ["#38bdf8", "#22c55e", "#f59e0b", "#f43f5e", "#a78bfa", "#14b8a6"][index % 6];
}

function polarToCartesian(cx: number, cy: number, radius: number, angleDeg: number) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(angleRad),
    y: cy + radius * Math.sin(angleRad),
  };
}

function donutPath(cx: number, cy: number, radius: number, startAngle: number, endAngle: number): string {
  const start = polarToCartesian(cx, cy, radius, endAngle);
  const end = polarToCartesian(cx, cy, radius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return ["M", start.x, start.y, "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y].join(" ");
}

function CvcOverviewCharts({ items }: { items: CvcInventoryItem[] }) {
  const stats = useMemo(() => {
    const withReference = items.filter((item) => item.sypemi_reference_annees !== null);
    const withCriticity = items.filter((item) => item.criticite_pct !== null);
    const avgCriticity = withCriticity.length
      ? withCriticity.reduce((sum, item) => sum + (item.criticite_pct ?? 0), 0) / withCriticity.length
      : null;
    const expired = items.filter((item) => item.duree_vie_restante !== null && item.duree_vie_restante < 0).length;
    const soon = items.filter(
      (item) => item.duree_vie_restante !== null && item.duree_vie_restante >= 0 && item.duree_vie_restante <= 3,
    ).length;
    const sourceCounts = {
      dateMes: items.filter((item) => item.lifecycle_age_source === "date_mes").length,
      estimated: items.filter((item) => item.lifecycle_age_source === "etat_sante").length,
      missing: items.filter((item) => item.lifecycle_age_source === "missing").length,
    };
    const familyMap = new Map<string, number>();
    for (const item of items) {
      const key = item.famille?.trim() || "Non renseignee";
      familyMap.set(key, (familyMap.get(key) ?? 0) + 1);
    }
    const families = [...familyMap.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([label, count], index) => ({ label, count, color: familyColor(index) }));
    return {
      withReference: withReference.length,
      avgCriticity,
      expired,
      soon,
      sourceCounts,
      families,
      sourceTotal: Math.max(1, items.length),
    };
  }, [items]);

  let currentAngle = 0;
  const totalFamilies = Math.max(1, stats.families.reduce((sum, item) => sum + item.count, 0));

  return (
    <div className="cvc-overview-grid">
      <div className="cvc-aging-card">
        <div>
          <p className="eyebrow">Vieillissement global</p>
          <strong>{formatPercent(stats.avgCriticity)}</strong>
          <span>de duree de vie consommee</span>
        </div>
        <div
          className="cvc-aging-ring"
          style={
            { "--age": `${Math.min(100, Math.max(0, stats.avgCriticity ?? 0))}%` } as CSSProperties & Record<"--age", string>
          }
        >
          <span>{formatPercent(stats.avgCriticity)}</span>
        </div>
        <div className="cvc-mini-metrics">
          <span><strong>{stats.expired}</strong> depasses</span>
          <span><strong>{stats.soon}</strong> a 3 ans</span>
          <span><strong>{stats.withReference}</strong> references</span>
        </div>
      </div>

      <div className="cvc-chart-card">
        <div>
          <p className="eyebrow">Familles equipements</p>
          <h3>Repartition</h3>
        </div>
        <div className="cvc-donut-row">
          <svg viewBox="0 0 120 120" className="cvc-donut" aria-hidden="true">
            <circle cx="60" cy="60" r="42" fill="none" stroke="rgba(148,163,184,0.18)" strokeWidth="18" />
            {stats.families.map((entry) => {
              const slice = (entry.count / totalFamilies) * 360;
              if (slice >= 359) {
                return <circle key={entry.label} cx="60" cy="60" r="42" fill="none" stroke={entry.color} strokeWidth="18" />;
              }
              const path = donutPath(60, 60, 42, currentAngle, currentAngle + slice);
              currentAngle += slice;
              return <path key={entry.label} d={path} fill="none" stroke={entry.color} strokeWidth="18" strokeLinecap="round" />;
            })}
          </svg>
          <div className="cvc-chart-legend">
            {stats.families.map((entry) => (
              <span key={entry.label}>
                <i style={{ background: entry.color }} />
                {entry.label} <strong>{entry.count}</strong>
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="cvc-chart-card">
        <div>
          <p className="eyebrow">Qualite du calcul</p>
          <h3>Source de l'age</h3>
        </div>
        <div className="cvc-source-bars">
          <span>
            <strong>DATE MES</strong>
            <i><b style={{ width: `${(stats.sourceCounts.dateMes / stats.sourceTotal) * 100}%` }} /></i>
            {stats.sourceCounts.dateMes}
          </span>
          <span>
            <strong>ETAT SANTE</strong>
            <i><b style={{ width: `${(stats.sourceCounts.estimated / stats.sourceTotal) * 100}%` }} /></i>
            {stats.sourceCounts.estimated}
          </span>
          <span>
            <strong>A completer</strong>
            <i><b style={{ width: `${(stats.sourceCounts.missing / stats.sourceTotal) * 100}%` }} /></i>
            {stats.sourceCounts.missing}
          </span>
        </div>
      </div>
    </div>
  );
}

type RowSelectProps = {
  value: number | null;
  options: { id: number; label: string }[];
  placeholder: string;
  onChange: (value: number | null) => void;
  disabled?: boolean;
};

function RowSelect({ value, options, placeholder, onChange, disabled }: RowSelectProps) {
  return (
    <select
      value={value ?? ""}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
      style={{
        width: "100%",
        minWidth: 0,
        padding: "6px 8px",
        borderRadius: 6,
        border: `1px solid ${NEUTRAL_BORDER}`,
        background: "rgba(15,23,42,0.9)",
        color: disabled ? "#64748b" : "#e2e8f0",
        fontSize: "0.78rem",
      }}
    >
      <option value="">{placeholder}</option>
      {options.map((option) => (
        <option key={option.id} value={option.id}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

type InventoryRowProps = {
  item: CvcInventoryItem;
  buildings: Building[];
  references: EquipmentReference[];
  saving: boolean;
  onPatch: (item: CvcInventoryItem, payload: UpdateCvcInventoryItemPayload) => void;
};

function InventoryRow({ item, buildings, references, saving, onPatch }: InventoryRowProps) {
  const building = buildings.find((b) => b.id === item.building_id);
  const referenceOptions = references.map((ref) => ({ id: ref.id, label: referenceLabel(ref) }));

  return (
    <tr>
      <td>
        <strong>{item.designation}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {compactLabel([item.marque, item.modele]) || "Marque / modele non renseignes"}
        </div>
      </td>
      <td>
        <strong>{item.famille || "-"}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {item.etat_sante ? `Etat : ${item.etat_sante}` : "Etat non renseigne"}
        </div>
      </td>
      <td>
        <div>{item.site_raw ?? "-"}</div>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {compactLabel([item.batiment, item.niveau, item.local_name])}
        </div>
      </td>
      <td>
        <strong>{building?.nom_batiment ?? (item.building_id ? `Batiment #${item.building_id}` : "-")}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {building?.adresse_reconstituee ?? "A matcher dans Sites"}
        </div>
      </td>
      <td>
        <RowSelect
          value={item.equipment_ref_id}
          options={referenceOptions}
          placeholder="Reference duree de vie"
          disabled={saving}
          onChange={(equipment_ref_id) => onPatch(item, { equipment_ref_id })}
        />
        {item.equipment_ref && (
          <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem", marginTop: 4 }}>
            {compactLabel([item.equipment_ref.niveau_3, item.equipment_ref.equipement])}
          </div>
        )}
      </td>
      <td>
        <input
          type="number"
          min="1900"
          max={CURRENT_YEAR + 1}
          defaultValue={item.date_mis_en_service ?? ""}
          disabled={saving}
          onBlur={(e) => onPatch(item, { date_mis_en_service: yearOrNull(e.target.value) })}
          style={{
            width: "100%",
            minWidth: 0,
            padding: "6px 8px",
            borderRadius: 6,
            border: `1px solid ${NEUTRAL_BORDER}`,
            background: "rgba(15,23,42,0.9)",
            color: "#e2e8f0",
          }}
        />
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem", marginTop: 4 }}>
          {item.lifecycle_age_label ?? "Age non determine"}
        </div>
      </td>
      <td style={{ whiteSpace: "nowrap" }}>
        {item.sypemi_mini_annees ?? "-"} / <strong>{item.sypemi_reference_annees ?? "-"}</strong> / {item.sypemi_maxi_annees ?? "-"} ans
        <div style={{ color: item.duree_vie_restante !== null && item.duree_vie_restante < 0 ? "#f87171" : SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {formatRemainingLife(item)}
        </div>
        {item.criticite_pct !== null && (
          <div style={{ color: "#7dd3fc", fontSize: "0.72rem" }}>
            Vie consommee {formatPercent(item.criticite_pct)}
          </div>
        )}
      </td>
    </tr>
  );
}

export function CvcImportPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CvcPreviewResponse | null>(null);
  const [activeBatch, setActiveBatch] = useState<string | null>(null);
  const [familyFilter, setFamilyFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  const batchesQuery = useQuery<CvcImportBatchSummary[]>({
    queryKey: ["cvc-import-batches", token],
    queryFn: () => fetchCvcImportBatches(token ?? ""),
    enabled: !!token,
  });
  const itemsQuery = useQuery<CvcInventoryItem[]>({
    queryKey: ["cvc-import-items", token, activeBatch],
    queryFn: () => fetchCvcImportItems(token ?? "", activeBatch ?? ""),
    enabled: !!token && !!activeBatch,
  });
  const buildingsQuery = useQuery<Building[]>({
    queryKey: ["buildings", token],
    queryFn: () => fetchBuildings(token ?? ""),
    enabled: !!token,
    staleTime: 0,
  });
  const referencesQuery = useQuery<EquipmentReference[]>({
    queryKey: ["equipment-references", token],
    queryFn: () => fetchEquipmentReferences(token ?? ""),
    enabled: !!token,
    staleTime: 10 * 60 * 1000,
  });

  const previewMutation = useMutation({
    mutationFn: async () => {
      if (!file || !token) throw new Error("Selectionne un fichier Excel.");
      return postCvcPreview(token, file);
    },
    onSuccess: (result) => {
      setPreview(result);
      setError(null);
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Erreur lors de l'analyse."),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!file || !token) throw new Error("Selectionne un fichier Excel avant l'import.");
      return postCvcImport(token, file, []);
    },
    onSuccess: (result) => {
      setActiveBatch(result.import_batch);
      setFile(null);
      setPreview(null);
      setError(null);
      if (fileRef.current) fileRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["cvc-import-batches"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-import-items"] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Erreur lors de l'enregistrement."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ item, payload }: { item: CvcInventoryItem; payload: UpdateCvcInventoryItemPayload }) => {
      if (!token) throw new Error("Session expiree.");
      return updateCvcItem(token, item.id, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cvc-import-items"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-import-batches"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-terrain"] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Erreur de sauvegarde."),
  });

  const recomputeMutation = useMutation({
    mutationFn: async () => {
      if (!token || !activeBatch) throw new Error("Choisis un import.");
      return recomputeCvcImportReferences(token, activeBatch);
    },
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["cvc-import-items"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-import-batches"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-terrain"] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Erreur pendant le recalcul des references."),
  });

  const references = useMemo(
    () => (referencesQuery.data ?? []).filter(isCvcRelevant),
    [referencesQuery.data],
  );
  const latestBatch = batchesQuery.data?.[0] ?? null;
  const items = itemsQuery.data ?? [];
  const familyOptions = useMemo(
    () => [...new Set(items.map((item) => item.famille?.trim()).filter((value): value is string => Boolean(value)))].sort(),
    [items],
  );
  const visibleItems = useMemo(
    () => (familyFilter ? items.filter((item) => (item.famille?.trim() || "") === familyFilter) : items),
    [familyFilter, items],
  );
  const mappedCount = items.filter((item) => item.building_id !== null).length;
  const refMappedCount = items.filter((item) => item.equipment_ref_id !== null).length;
  const computedFromHealthCount = items.filter((item) => item.lifecycle_age_source === "etat_sante").length;

  useEffect(() => {
    const batch = batchesQuery.data?.[0]?.import_batch ?? null;
    setActiveBatch((current) => (current === batch ? current : batch));
  }, [batchesQuery.data]);

  function refreshPatrimoineLists() {
    queryClient.invalidateQueries({ queryKey: ["buildings"] });
  }

  if (!token) {
    return (
      <section className="panel stack-lg">
        <h2>Import inventaire CVC</h2>
        <p>Connecte-toi pour acceder a cette page.</p>
      </section>
    );
  }

  return (
    <section className="panel stack-lg cvc-workspace-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Gestion technique</p>
          <h2>Inventaire CVC terrain</h2>
          <p>Charge le fichier terrain, enregistre l'inventaire, puis traite le matching patrimoine dans une page dediee.</p>
        </div>
        <div className="buildings-header-actions">
          <Link className="secondary-link" to="/buildings/technique">Retour a la gestion technique</Link>
        </div>
      </div>

      {error && (
        <div style={{ padding: "10px 14px", background: "rgba(220,38,38,0.15)", border: "1px solid rgba(220,38,38,0.4)", borderRadius: 8, color: "#fca5a5" }}>
          {error}
        </div>
      )}

      <div className="section-block">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-end", flexWrap: "wrap" }}>
          <label className="field" style={{ minWidth: 280, margin: 0 }}>
            <span>Fichier inventaire .xlsx</span>
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setPreview(null);
                setError(null);
              }}
            />
          </label>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              type="button"
              className="secondary-button"
              onClick={() => previewMutation.mutate()}
              disabled={!file || previewMutation.isPending || saveMutation.isPending}
            >
              {previewMutation.isPending ? "Analyse..." : "Uploader le fichier"}
            </button>
            <button
              type="button"
              className="primary-button"
              onClick={() => saveMutation.mutate()}
              disabled={!file || !preview || saveMutation.isPending}
            >
              {saveMutation.isPending ? "Enregistrement..." : "Enregistrer l'inventaire"}
            </button>
          </div>
        </div>
        {file && (
          <p style={{ color: SUBTLE_TEXT, fontSize: "0.85rem", marginTop: 8 }}>
            Fichier pret : <strong style={{ color: "#e2e8f0" }}>{file.name}</strong>
          </p>
        )}
        {preview && (
          <div className="cvc-preview-grid">
            <div>
              <strong>{preview.total_rows}</strong>
              <span>Lignes detectees</span>
            </div>
            <div>
              <strong>{preview.unique_sites.length}</strong>
              <span>Batiments source</span>
            </div>
            <div>
              <strong>{preview.unique_families.length}</strong>
              <span>Familles source</span>
            </div>
          </div>
        )}
      </div>

      <div className="section-block">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <h3>Inventaire courant</h3>
            <p style={{ color: SUBTLE_TEXT, fontSize: "0.86rem" }}>
              Le dernier import remplace l'inventaire CVC terrain precedent.
            </p>
            {latestBatch ? (
              <p style={{ color: "#cbd5e1", fontSize: "0.84rem", marginTop: 6 }}>
                {latestBatch.import_batch} - {latestBatch.imported} lignes - {latestBatch.mapped_items} rattachees
              </p>
            ) : (
              <p style={{ color: SUBTLE_TEXT, fontSize: "0.84rem", marginTop: 6 }}>Aucun inventaire enregistre.</p>
            )}
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <button type="button" className="secondary-button" onClick={refreshPatrimoineLists}>
              Rafraichir patrimoine
            </button>
            {activeBatch && (
              <Link className="secondary-link" to="/buildings/cvc-import/batiments">
                Matcher les batiments
              </Link>
            )}
            {activeBatch && (
              <button
                type="button"
                className="secondary-button"
                onClick={() => recomputeMutation.mutate()}
                disabled={recomputeMutation.isPending}
              >
                {recomputeMutation.isPending ? "Recalcul..." : "Recalculer les references"}
              </button>
            )}
          </div>
        </div>
      </div>

      {activeBatch && (
        <div className="section-block">
          {items.length > 0 && <CvcOverviewCharts items={items} />}

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
            {[
              ["Lignes", items.length],
              ["Rattachees patrimoine", mappedCount],
              ["Reference duree de vie", refMappedCount],
              ["Ages estimes", computedFromHealthCount],
            ].map(([label, value]) => (
              <div key={label} style={{ padding: "10px 14px", border: `1px solid ${NEUTRAL_BORDER}`, borderRadius: 8, background: "rgba(15,23,42,0.35)" }}>
                <div style={{ color: "#e2e8f0", fontWeight: 700 }}>{value}</div>
                <div style={{ color: SUBTLE_TEXT, fontSize: "0.74rem" }}>{label}</div>
              </div>
            ))}
          </div>

          {itemsQuery.isLoading && <p>Chargement de l'inventaire...</p>}
          {!itemsQuery.isLoading && items.length === 0 && <p>Aucune ligne trouvee pour cet import.</p>}
          {items.length > 0 && (
            <>
              <div className="cvc-table-filters">
                <label>
                  <span>Famille</span>
                  <select value={familyFilter} onChange={(e) => setFamilyFilter(e.target.value)}>
                    <option value="">Toutes les familles</option>
                    {familyOptions.map((family) => (
                      <option key={family} value={family}>{family}</option>
                    ))}
                  </select>
                </label>
                <strong>{visibleItems.length} / {items.length} lignes</strong>
              </div>
              <div className="table-wrapper cvc-table-wrapper">
                <table className="data-table cvc-inventory-table">
                  <thead>
                    <tr>
                      <th>Equipement terrain</th>
                      <th>Famille</th>
                      <th>Localisation source</th>
                      <th>Batiment patrimoine</th>
                      <th>Duree de vie attachee</th>
                      <th>DATE MES</th>
                      <th>Mini / Ref. / Maxi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleItems.map((item) => (
                      <InventoryRow
                        key={item.id}
                        item={item}
                        buildings={buildingsQuery.data ?? []}
                        references={references}
                        saving={updateMutation.isPending && updateMutation.variables?.item.id === item.id}
                        onPatch={(row, payload) => updateMutation.mutate({ item: row, payload })}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
