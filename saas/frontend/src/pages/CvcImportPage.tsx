import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";
import {
  fetchBuildings,
  fetchCvcImportBatches,
  fetchCvcImportItems,
  fetchEquipmentReferences,
  fetchAllLocals,
  fetchSites,
  postCvcImport,
  updateCvcItem,
  type Building,
  type CvcImportBatchSummary,
  type CvcInventoryItem,
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
  return ref.code_niveau_2 === "A.2.3" || ref.niveau_3 === "Production de froid :" || ref.niveau_3 === "Pompes à chaleur Air/Air, Air/Eau, Eau/Eau";
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
        minWidth: 180,
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
  const siteOptions = sites.map((site) => ({
    id: site.id,
    label: compactLabel([site.nom_site, site.adresse]),
  }));
  const buildingOptions = buildings.map((b) => ({
    id: b.id,
    label: compactLabel([b.nom_batiment ?? `Bâtiment #${b.id}`, b.adresse_reconstituee]),
  }));
  const localOptions = locals
    .filter((local) => !item.building_id || local.building_id === item.building_id)
    .map((local) => ({
      id: local.id,
      label: compactLabel([local.nom_local, local.niveau, local.type_local]),
    }));
  const referenceOptions = references.map((ref) => ({ id: ref.id, label: referenceLabel(ref) }));

  const updateBuilding = (buildingId: number | null) => {
    const nextBuilding = buildings.find((b) => b.id === buildingId);
    onPatch(item, {
      building_id: buildingId,
      site_id: nextBuilding?.site_id ?? item.site_id ?? null,
      local_id: null,
    });
  };

  return (
    <tr>
      <td>
        <strong>{item.designation}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {compactLabel([item.famille, item.marque, item.modele]) || "Famille non renseignée"}
        </div>
      </td>
      <td>
        <div>{item.site_raw ?? "-"}</div>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {compactLabel([item.batiment, item.niveau, item.local_name])}
        </div>
      </td>
      <td>
        <RowSelect
          value={item.site_id}
          options={siteOptions}
          placeholder="Site patrimoine"
          disabled={saving}
          onChange={(site_id) => onPatch(item, { site_id })}
        />
      </td>
      <td>
        <RowSelect
          value={item.building_id}
          options={buildingOptions}
          placeholder="Bâtiment patrimoine"
          disabled={saving}
          onChange={updateBuilding}
        />
      </td>
      <td>
        <RowSelect
          value={item.local_id}
          options={localOptions}
          placeholder={building ? "Local optionnel" : "Choisir un bâtiment"}
          disabled={saving || !item.building_id}
          onChange={(local_id) => onPatch(item, { local_id })}
        />
      </td>
      <td>
        <RowSelect
          value={item.equipment_ref_id}
          options={referenceOptions}
          placeholder="Référence durée de vie"
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
              ? `${Math.abs(item.duree_vie_restante)} ans dépassé`
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
              width: 110,
              padding: "6px 8px",
              borderRadius: 6,
              border: `1px solid ${NEUTRAL_BORDER}`,
              background: "rgba(15,23,42,0.9)",
              color: "#e2e8f0",
            }}
          />
        ) : (
          <span style={{ color: "#475569" }}>Non concerné</span>
        )}
      </td>
      <td style={{ color: saving ? "#fbbf24" : "#4ade80", fontSize: "0.74rem" }}>
        {saving ? "Sauvegarde..." : "Enregistré"}
      </td>
    </tr>
  );
}

export function CvcImportPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
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

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file || !token) throw new Error("Sélectionne un fichier Excel avant l'import.");
      return postCvcImport(token, file, []);
    },
    onSuccess: (result) => {
      setActiveBatch(result.import_batch);
      setFile(null);
      setError(null);
      if (fileRef.current) fileRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["cvc-import-batches"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-import-items"] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Erreur lors de l'import."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ item, payload }: { item: CvcInventoryItem; payload: UpdateCvcInventoryItemPayload }) => {
      if (!token) throw new Error("Session expirée.");
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
        <p>Connecte-toi pour accéder à cette page.</p>
      </section>
    );
  }

  return (
    <section className="panel stack-lg">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Gestion technique</p>
          <h2>Inventaire CVC terrain</h2>
          <p>Charge le fichier terrain, puis complète les rattachements patrimoine et les durées de vie dans le tableau.</p>
        </div>
        <div className="buildings-header-actions">
          <Link className="secondary-link" to="/buildings/technique">Retour à la gestion technique</Link>
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
            <input ref={fileRef} type="file" accept=".xlsx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
          <button
            type="button"
            className="primary-button"
            onClick={() => uploadMutation.mutate()}
            disabled={!file || uploadMutation.isPending}
          >
            {uploadMutation.isPending ? "Enregistrement..." : "Uploader et enregistrer l'inventaire"}
          </button>
        </div>
        {file && (
          <p style={{ color: SUBTLE_TEXT, fontSize: "0.85rem", marginTop: 8 }}>
            Fichier prêt : <strong style={{ color: "#e2e8f0" }}>{file.name}</strong>
          </p>
        )}
      </div>

      <div className="section-block">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <h3>Imports enregistrés</h3>
            <p style={{ color: SUBTLE_TEXT, fontSize: "0.86rem" }}>
              Les listes sites, bâtiments et locaux sont relues depuis le patrimoine.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <button type="button" className="secondary-button" onClick={refreshPatrimoineLists}>
              Rafraîchir patrimoine
            </button>
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
                  {batch.import_batch} - {batch.imported} lignes - {batch.mapped_items} patrimoine
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
              ["Rattachées patrimoine", mappedCount],
              ["Référence durée de vie", refMappedCount],
              ["Fluides frigorigènes", refrigerantCount],
            ].map(([label, value]) => (
              <div key={label} style={{ padding: "10px 14px", border: `1px solid ${NEUTRAL_BORDER}`, borderRadius: 8, background: "rgba(15,23,42,0.35)" }}>
                <div style={{ color: "#e2e8f0", fontWeight: 700 }}>{value}</div>
                <div style={{ color: SUBTLE_TEXT, fontSize: "0.74rem" }}>{label}</div>
              </div>
            ))}
          </div>

          {itemsQuery.isLoading && <p>Chargement de l'inventaire...</p>}
          {!itemsQuery.isLoading && items.length === 0 && <p>Aucune ligne trouvée pour cet import.</p>}
          {items.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table className="data-table" style={{ minWidth: 1480 }}>
                <thead>
                  <tr>
                    <th>Équipement terrain</th>
                    <th>Localisation source</th>
                    <th>Site patrimoine</th>
                    <th>Bâtiment patrimoine</th>
                    <th>Local patrimoine</th>
                    <th>Durée de vie attachée</th>
                    <th>Mini / Réf. / Maxi</th>
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
