import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";
import {
  fetchCvcRefrigerantBatches,
  fetchCvcRefrigerantItems,
  postCvcRefrigerantImport,
  updateCvcRefrigerantItem,
  type CvcRefrigerantBatchSummary,
  type CvcRefrigerantItem,
} from "../lib/api";

const SUBTLE_TEXT = "#94a3b8";
const NEUTRAL_BORDER = "rgba(148, 163, 184, 0.25)";

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("fr-FR", {
    maximumFractionDigits: digits,
    minimumFractionDigits: value % 1 === 0 ? 0 : Math.min(digits, 2),
  }).format(value);
}

function compactLabel(parts: Array<string | null | undefined>): string {
  return parts.filter(Boolean).join(" - ");
}

function matchLabel(item: CvcRefrigerantItem): string {
  if (item.matched_inventory_item) {
    return compactLabel([
      item.matched_inventory_item.designation,
      item.matched_inventory_item.marque,
      item.matched_inventory_item.modele,
    ]);
  }
  if (item.match_status === "ambiguous") return "A valider";
  return "Non rattache";
}

function scheduleLabel(schedule: Record<string, string>): string {
  const entries = Object.entries(schedule);
  if (entries.length === 0) return "-";
  return entries
    .slice(0, 4)
    .map(([year, action]) => `${year}: ${action}`)
    .join(" | ");
}

type RowProps = {
  item: CvcRefrigerantItem;
  saving: boolean;
  onAttach: (item: CvcRefrigerantItem, cvcInventoryItemId: number | null) => void;
};

function RefrigerantRow({ item, saving, onAttach }: RowProps) {
  const candidateOptions = item.candidates.map((candidate) => ({
    value: candidate.item.id,
    label: `${candidate.item.designation} - ${compactLabel([
      candidate.item.marque,
      candidate.item.modele,
      candidate.item.import_batch,
    ])} (${Math.round(candidate.score * 100)}%)`,
  }));

  return (
    <tr>
      <td>
        <strong>{item.designation}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {compactLabel([item.famille, item.marque, item.modele]) || "Famille non renseignee"}
        </div>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {compactLabel([item.site_raw, item.date_mis_en_service ? String(item.date_mis_en_service) : null])}
        </div>
      </td>
      <td>
        <strong>{item.fluide_frigorigene ?? "-"}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {formatNumber(item.quantite_fluide_kg)} kg | {formatNumber(item.puissance_froid_kw, 1)} kW
        </div>
      </td>
      <td>
        <strong>{formatNumber(item.teqco2, 3)}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          GWP {formatNumber(item.gwp, 0)}
        </div>
      </td>
      <td>
        <strong>{item.esp_status ?? "-"}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {formatNumber(item.cout_desp_date_eur, 0)} EUR | 5 ans {formatNumber(item.cumul_5_ans_eur, 0)} EUR
        </div>
      </td>
      <td style={{ fontSize: "0.78rem", color: "#cbd5e1" }}>{scheduleLabel(item.schedule)}</td>
      <td>
        <strong>{matchLabel(item)}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {compactLabel([item.match_status, item.match_method, item.match_score ? `${Math.round(item.match_score * 100)}%` : null])}
        </div>
        <select
          value={item.cvc_inventory_item_id ?? ""}
          disabled={saving}
          onChange={(e) => onAttach(item, e.target.value ? Number(e.target.value) : null)}
          style={{
            width: "100%",
            marginTop: 6,
            padding: "6px 8px",
            borderRadius: 6,
            border: `1px solid ${NEUTRAL_BORDER}`,
            background: "rgba(15,23,42,0.9)",
            color: "#e2e8f0",
            fontSize: "0.78rem",
          }}
        >
          <option value="">Aucun rattachement</option>
          {candidateOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </td>
      <td style={{ color: saving ? "#fbbf24" : "#4ade80", fontSize: "0.74rem" }}>
        {saving ? "Sauvegarde..." : "Enregistre"}
      </td>
    </tr>
  );
}

export function CvcRefrigerantsPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [activeBatch, setActiveBatch] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const batchesQuery = useQuery<CvcRefrigerantBatchSummary[]>({
    queryKey: ["cvc-refrigerant-batches", token],
    queryFn: () => fetchCvcRefrigerantBatches(token ?? ""),
    enabled: !!token,
  });

  const itemsQuery = useQuery<CvcRefrigerantItem[]>({
    queryKey: ["cvc-refrigerant-items", token, activeBatch],
    queryFn: () => fetchCvcRefrigerantItems(token ?? "", activeBatch ?? ""),
    enabled: !!token && !!activeBatch,
  });

  const importMutation = useMutation({
    mutationFn: async () => {
      if (!token || !file) throw new Error("Selectionne un fichier ESP.");
      return postCvcRefrigerantImport(token, file);
    },
    onSuccess: (result) => {
      setActiveBatch(result.import_batch);
      setFile(null);
      setError(null);
      if (fileRef.current) fileRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["cvc-refrigerant-batches"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-refrigerant-items"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-import-items"] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Erreur import ESP."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ item, cvcInventoryItemId }: { item: CvcRefrigerantItem; cvcInventoryItemId: number | null }) => {
      if (!token) throw new Error("Session expiree.");
      return updateCvcRefrigerantItem(token, item.id, { cvc_inventory_item_id: cvcInventoryItemId });
    },
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["cvc-refrigerant-items"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-refrigerant-batches"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-import-items"] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Erreur de sauvegarde."),
  });

  const items = itemsQuery.data ?? [];
  const activeSummary = (batchesQuery.data ?? []).find((batch) => batch.import_batch === activeBatch);
  const matchedCount = items.filter((item) => item.cvc_inventory_item_id !== null).length;
  const ambiguousCount = items.filter((item) => item.match_status === "ambiguous").length;
  const missingDataCount = items.filter((item) => !item.fluide_frigorigene || item.quantite_fluide_kg === null).length;
  const statusCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of items) {
      const status = item.esp_status ?? "Non renseigne";
      counts.set(status, (counts.get(status) ?? 0) + 1);
    }
    return Array.from(counts.entries());
  }, [items]);

  if (!token) {
    return (
      <section className="panel stack-lg">
        <h2>Fluides frigorigenes</h2>
        <p>Connecte-toi pour acceder a cette page.</p>
      </section>
    );
  }

  return (
    <section className="panel stack-lg cvc-workspace-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Gestion technique</p>
          <h2>Fluides frigorigenes &amp; ESP</h2>
          <p>Importe le registre ESP, suis les obligations DESP et rattache chaque ligne a l'equipement CVC correspondant.</p>
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
            <span>Fichier ESP .xlsx</span>
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setError(null);
              }}
            />
          </label>
          <button
            type="button"
            className="primary-button"
            onClick={() => importMutation.mutate()}
            disabled={!file || importMutation.isPending}
          >
            {importMutation.isPending ? "Import..." : "Importer le registre ESP"}
          </button>
        </div>
        {file && (
          <p style={{ color: SUBTLE_TEXT, fontSize: "0.85rem", marginTop: 8 }}>
            Fichier pret : <strong style={{ color: "#e2e8f0" }}>{file.name}</strong>
          </p>
        )}
      </div>

      <div className="section-block">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <h3>Lots ESP importes</h3>
            <p style={{ color: SUBTLE_TEXT, fontSize: "0.86rem" }}>
              Les rattachements restent independants de l'inventaire CVC terrain.
            </p>
          </div>
          <select
            value={activeBatch ?? ""}
            onChange={(e) => setActiveBatch(e.target.value || null)}
            style={{
              minWidth: 320,
              padding: "8px 10px",
              borderRadius: 6,
              border: `1px solid ${NEUTRAL_BORDER}`,
              background: "rgba(15,23,42,0.9)",
              color: "#e2e8f0",
            }}
          >
            <option value="">Choisir un lot ESP</option>
            {(batchesQuery.data ?? []).map((batch) => (
              <option key={batch.import_batch} value={batch.import_batch}>
                {batch.import_batch} - {batch.imported} lignes - {batch.matched_items} rattachees
              </option>
            ))}
          </select>
        </div>
      </div>

      {activeBatch && (
        <div className="section-block">
          <div className="cvc-preview-grid cvc-refrigerant-kpis">
            {[
              ["Lignes ESP", items.length || activeSummary?.imported || 0],
              ["Rattachees CVC", matchedCount || activeSummary?.matched_items || 0],
              ["Ambigues", ambiguousCount],
              ["Donnees manquantes", missingDataCount],
              ["Fluide kg", formatNumber(activeSummary?.total_fluide_kg, 2)],
              ["tEqCO2", formatNumber(activeSummary?.total_teqco2, 3)],
            ].map(([label, value]) => (
              <div key={label}>
                <strong>{value}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>

          {statusCounts.length > 0 && (
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12 }}>
              {statusCounts.map(([status, count]) => (
                <span key={status} style={{ padding: "6px 10px", border: `1px solid ${NEUTRAL_BORDER}`, borderRadius: 6, color: "#cbd5e1", fontSize: "0.8rem" }}>
                  {status} : {count}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {activeBatch && (
        <div className="section-block">
          {itemsQuery.isLoading && <p>Chargement du registre ESP...</p>}
          {!itemsQuery.isLoading && items.length === 0 && <p>Aucune ligne ESP trouvee pour ce lot.</p>}
          {items.length > 0 && (
            <div className="table-wrapper cvc-table-wrapper">
              <table className="data-table cvc-refrigerant-table">
                <thead>
                  <tr>
                    <th>Equipement ESP</th>
                    <th>Fluide</th>
                    <th>Impact</th>
                    <th>ESP / couts</th>
                    <th>Planning</th>
                    <th>Rattachement CVC</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <RefrigerantRow
                      key={item.id}
                      item={item}
                      saving={updateMutation.isPending && updateMutation.variables?.item.id === item.id}
                      onAttach={(row, cvcInventoryItemId) => updateMutation.mutate({ item: row, cvcInventoryItemId })}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
