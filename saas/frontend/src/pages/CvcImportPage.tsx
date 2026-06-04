import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";
import {
  fetchAllLocals,
  fetchBuildings,
  fetchCvcImportBatches,
  fetchCvcImportItems,
  fetchEquipmentReferences,
  fetchSites,
  postCvcImport,
  postCvcPreview,
  updateCvcItem,
  type Building,
  type CvcImportBatchSummary,
  type CvcInventoryItem,
  type CvcPreviewResponse,
  type EquipmentReference,
  type Local,
  type Site,
  type UpdateCvcInventoryItemPayload,
} from "../lib/api";

const SUBTLE_TEXT = "#94a3b8";
const NEUTRAL_BORDER = "rgba(148, 163, 184, 0.25)";

function compactLabel(parts: Array<string | null | undefined>): string {
  return parts.filter(Boolean).join(" - ");
}

function numberOrNull(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
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
    ref.code_niveau_2 === "A.2.3" ||
    ref.niveau_3 === "Production de froid :" ||
    ref.niveau_3 === "Pompes a chaleur Air/Air, Air/Eau, Eau/Eau"
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
  sites: Site[];
  locals: Local[];
  references: EquipmentReference[];
  saving: boolean;
  onPatch: (item: CvcInventoryItem, payload: UpdateCvcInventoryItemPayload) => void;
};

function InventoryRow({ item, buildings, sites, locals, references, saving, onPatch }: InventoryRowProps) {
  const building = buildings.find((b) => b.id === item.building_id);
  const site = sites.find((s) => s.id === item.site_id);
  const localOptions = locals
    .filter((local) => !item.building_id || local.building_id === item.building_id)
    .map((local) => ({
      id: local.id,
      label: compactLabel([local.nom_local, local.niveau, local.type_local]),
    }));
  const referenceOptions = references.map((ref) => ({ id: ref.id, label: referenceLabel(ref) }));

  return (
    <tr>
      <td>
        <strong>{item.designation}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {compactLabel([item.famille, item.marque, item.modele]) || "Famille non renseignee"}
        </div>
      </td>
      <td>
        <div>{item.site_raw ?? "-"}</div>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {compactLabel([item.batiment, item.niveau, item.local_name])}
        </div>
      </td>
      <td>
        <strong>{site?.nom_site ?? "-"}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {site?.adresse ?? "A matcher dans Sites"}
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
          value={item.local_id}
          options={localOptions}
          placeholder={building ? "Local optionnel" : "Choisir un batiment"}
          disabled={saving || !item.building_id}
          onChange={(local_id) => onPatch(item, { local_id })}
        />
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
      <td style={{ whiteSpace: "nowrap" }}>
        {item.sypemi_mini_annees ?? "-"} / <strong>{item.sypemi_reference_annees ?? "-"}</strong> / {item.sypemi_maxi_annees ?? "-"} ans
        {item.duree_vie_restante !== null && (
          <div style={{ color: item.duree_vie_restante < 0 ? "#f87171" : SUBTLE_TEXT, fontSize: "0.72rem" }}>
            {item.duree_vie_restante < 0
              ? `${Math.abs(item.duree_vie_restante)} ans depasse`
              : `${item.duree_vie_restante} ans restants`}
          </div>
        )}
      </td>
      <td>
        {item.requires_refrigerant_quantity ? (
          <input
            type="number"
            min="0"
            step="0.01"
            defaultValue={item.quantite_fluide_frigorigene ?? ""}
            disabled={saving}
            onBlur={(e) => onPatch(item, { quantite_fluide_frigorigene: numberOrNull(e.target.value) })}
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
        ) : (
          <span style={{ color: "#475569" }}>Non concerne</span>
        )}
      </td>
      <td style={{ color: saving ? "#fbbf24" : "#4ade80", fontSize: "0.74rem" }}>
        {saving ? "Sauvegarde..." : "Enregistre"}
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
  const sitesQuery = useQuery<Site[]>({
    queryKey: ["sites", token],
    queryFn: () => fetchSites(token ?? ""),
    enabled: !!token,
    staleTime: 0,
  });
  const localsQuery = useQuery<Local[]>({
    queryKey: ["locals", token],
    queryFn: () => fetchAllLocals(token ?? ""),
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

  const references = useMemo(
    () => (referencesQuery.data ?? []).filter(isCvcRelevant),
    [referencesQuery.data],
  );
  const items = itemsQuery.data ?? [];
  const mappedCount = items.filter((item) => item.building_id !== null).length;
  const refMappedCount = items.filter((item) => item.equipment_ref_id !== null).length;
  const refrigerantCount = items.filter((item) => item.requires_refrigerant_quantity).length;

  function refreshPatrimoineLists() {
    queryClient.invalidateQueries({ queryKey: ["buildings"] });
    queryClient.invalidateQueries({ queryKey: ["sites"] });
    queryClient.invalidateQueries({ queryKey: ["locals"] });
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
              <span>Sites source</span>
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
            <h3>Imports enregistres</h3>
            <p style={{ color: SUBTLE_TEXT, fontSize: "0.86rem" }}>
              Les listes sites, batiments et locaux sont relues depuis le patrimoine.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <button type="button" className="secondary-button" onClick={refreshPatrimoineLists}>
              Rafraichir patrimoine
            </button>
            {activeBatch && (
              <Link className="secondary-link" to={`/buildings/cvc-import/sites?batch=${encodeURIComponent(activeBatch)}`}>
                Matcher les sites
              </Link>
            )}
            <select
              value={activeBatch ?? ""}
              onChange={(e) => setActiveBatch(e.target.value || null)}
              style={{
                minWidth: 280,
                padding: "8px 10px",
                borderRadius: 6,
                border: `1px solid ${NEUTRAL_BORDER}`,
                background: "rgba(15,23,42,0.9)",
                color: "#e2e8f0",
              }}
            >
              <option value="">Choisir un import</option>
              {(batchesQuery.data ?? []).map((batch) => (
                <option key={batch.import_batch} value={batch.import_batch}>
                  {batch.import_batch} - {batch.imported} lignes - {batch.mapped_items} rattachees
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {activeBatch && (
        <div className="section-block">
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
            {[
              ["Lignes", items.length],
              ["Rattachees patrimoine", mappedCount],
              ["Reference duree de vie", refMappedCount],
              ["Fluides frigorigenes", refrigerantCount],
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
            <div className="table-wrapper cvc-table-wrapper">
              <table className="data-table cvc-inventory-table">
                <thead>
                  <tr>
                    <th>Equipement terrain</th>
                    <th>Localisation source</th>
                    <th>Site patrimoine</th>
                    <th>Batiment patrimoine</th>
                    <th>Local patrimoine</th>
                    <th>Duree de vie attachee</th>
                    <th>Mini / Ref. / Maxi</th>
                    <th>Fluide kg</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <InventoryRow
                      key={item.id}
                      item={item}
                      buildings={buildingsQuery.data ?? []}
                      sites={sitesQuery.data ?? []}
                      locals={localsQuery.data ?? []}
                      references={references}
                      saving={updateMutation.isPending && updateMutation.variables?.item.id === item.id}
                      onPatch={(row, payload) => updateMutation.mutate({ item: row, payload })}
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
