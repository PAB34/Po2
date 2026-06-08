import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";
import {
  fetchCvcRefrigerantBatches,
  fetchCvcRefrigerantDashboard,
  fetchCvcRefrigerantItems,
  postCvcRefrigerantImport,
  updateCvcRefrigerantItem,
  type CvcRefrigerantActionSummary,
  type CvcRefrigerantBatchSummary,
  type CvcRefrigerantDashboard,
  type CvcRefrigerantItem,
  type UpdateCvcRefrigerantItemPayload,
} from "../lib/api";

const SUBTLE_TEXT = "#94a3b8";
const NEUTRAL_BORDER = "rgba(148, 163, 184, 0.25)";
const ACTION_STATUSES = ["À créer", "Demandé", "Planifié", "Reçu", "Clos", "Sans objet"];
const TABS = ["Cockpit", "Registre F-Gaz", "Actions", "ESP/DESP", "Import"] as const;
type Tab = (typeof TABS)[number];

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("fr-FR", {
    maximumFractionDigits: digits,
    minimumFractionDigits: value % 1 === 0 ? 0 : Math.min(digits, 2),
  }).format(value);
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("fr-FR").format(new Date(value));
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
  if (item.match_status === "ambiguous") return "À valider";
  return "Non rattaché";
}

function badgeClass(value: string | null | undefined): string {
  if (!value) return "badge-gray";
  const normalized = value.toLowerCase();
  if (normalized.includes("retard") || normalized.includes("haute") || normalized.includes("compléter")) return "badge-red";
  if (normalized.includes("programmer") || normalized.includes("demander") || normalized.includes("moyenne")) return "badge-orange";
  if (normalized.includes("ok") || normalized.includes("clos") || normalized.includes("basse")) return "badge-green";
  return "badge-gray";
}

function KpiGrid({ dashboard }: { dashboard: CvcRefrigerantDashboard | undefined }) {
  const kpis = dashboard?.kpis ?? [];
  if (kpis.length === 0) {
    return (
      <div className="empty-state">
        Aucun registre fluide importé pour l'instant.
      </div>
    );
  }
  return (
    <div className="cvc-refrigerant-command-grid">
      {kpis.map((kpi) => (
        <div key={kpi.key} className={`cvc-command-kpi cvc-command-kpi-${kpi.tone}`}>
          <strong>{kpi.value}</strong>
          <span>{kpi.label}</span>
          {kpi.helper && <small>{kpi.helper}</small>}
        </div>
      ))}
    </div>
  );
}

function DistributionPanel({ title, counts }: { title: string; counts: Record<string, number> | undefined }) {
  const entries = Object.entries(counts ?? {}).sort((a, b) => b[1] - a[1]);
  return (
    <div className="cvc-command-panel">
      <h3>{title}</h3>
      {entries.length === 0 ? (
        <p style={{ color: SUBTLE_TEXT }}>Aucune donnée.</p>
      ) : (
        <div className="cvc-chip-list">
          {entries.map(([label, count]) => (
            <span key={label} className={`badge ${badgeClass(label)}`}>
              {label} : {count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function ActionTable({
  actions,
  onStatus,
  savingId,
}: {
  actions: CvcRefrigerantActionSummary[];
  onStatus: (itemId: number, status: string) => void;
  savingId: number | null;
}) {
  if (actions.length === 0) {
    return <p style={{ color: SUBTLE_TEXT }}>Aucune action ouverte dans le périmètre importé.</p>;
  }
  return (
    <div className="table-wrapper cvc-table-wrapper">
      <table className="data-table cvc-action-table">
        <thead>
          <tr>
            <th>Priorité</th>
            <th>Site / équipement</th>
            <th>Constat</th>
            <th>Action</th>
            <th>Preuve attendue</th>
            <th>Responsable</th>
            <th>Échéance</th>
            <th>Statut</th>
          </tr>
        </thead>
        <tbody>
          {actions.map((action) => (
            <tr key={`${action.theme}-${action.item_id}-${action.constat}`}>
              <td><span className={`badge ${badgeClass(action.priority)}`}>{action.priority}</span></td>
              <td>
                <strong>{action.site ?? "Site non renseigné"}</strong>
                <div style={{ color: SUBTLE_TEXT, fontSize: "0.74rem" }}>{action.equipment}</div>
                <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>{action.theme}</div>
              </td>
              <td>{action.constat}</td>
              <td>{action.action}</td>
              <td>{action.preuve_attendue}</td>
              <td>{action.responsable ?? "-"}</td>
              <td>{formatDate(action.echeance_cible)}</td>
              <td>
                <select
                  className="cvc-inline-select"
                  value={action.statut_action}
                  disabled={savingId === action.item_id}
                  onChange={(e) => onStatus(action.item_id, e.target.value)}
                >
                  {ACTION_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type RowProps = {
  item: CvcRefrigerantItem;
  saving: boolean;
  onPatch: (itemId: number, payload: UpdateCvcRefrigerantItemPayload) => void;
};

function RefrigerantRow({ item, saving, onPatch }: RowProps) {
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
          {compactLabel([item.famille, item.marque, item.modele]) || "Famille non renseignée"}
        </div>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {compactLabel([item.site_raw, item.date_mis_en_service ? String(item.date_mis_en_service) : null])}
        </div>
      </td>
      <td>
        <strong>{item.fluide_frigorigene ?? "-"}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {formatNumber(item.quantite_fluide_kg)} kg | GWP {formatNumber(item.gwp, 0)}
        </div>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>{formatNumber(item.teqco2, 3)} t éq. CO2</div>
      </td>
      <td>
        <span className={`badge ${badgeClass(item.fgas_status)}`}>{item.fgas_status}</span>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem", marginTop: 6 }}>
          Fréquence : {item.frequence_controle_mois ? `${item.frequence_controle_mois} mois` : "-"}
        </div>
      </td>
      <td>
        <span className={`badge ${badgeClass(item.statut_conformite)}`}>{item.statut_conformite}</span>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem", marginTop: 6 }}>{item.action_prioritaire}</div>
      </td>
      <td>
        <label className="cvc-mini-field">
          <span>Dernier contrôle</span>
          <input
            type="date"
            value={item.dernier_controle_etancheite ?? ""}
            disabled={saving}
            onChange={(e) => onPatch(item.id, { dernier_controle_etancheite: e.target.value || null })}
          />
        </label>
        <label className="cvc-mini-field">
          <span>Prochaine échéance</span>
          <input
            type="date"
            value={item.prochaine_echeance ?? ""}
            disabled={saving}
            onChange={(e) => onPatch(item.id, { prochaine_echeance: e.target.value || null })}
          />
        </label>
      </td>
      <td>
        <label className="cvc-mini-field">
          <span>Titulaire</span>
          <input
            type="text"
            key={`${item.id}-${item.titulaire ?? ""}`}
            defaultValue={item.titulaire ?? ""}
            disabled={saving}
            onBlur={(e) => onPatch(item.id, { titulaire: e.target.value.trim() || null })}
            placeholder="Titulaire CVC"
          />
        </label>
        <label className="cvc-mini-field">
          <span>Action</span>
          <select
            value={item.statut_action ?? "À créer"}
            disabled={saving}
            onChange={(e) => onPatch(item.id, { statut_action: e.target.value })}
          >
            {ACTION_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </label>
      </td>
      <td>
        <strong>{matchLabel(item)}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {compactLabel([item.match_status, item.match_method, item.match_score ? `${Math.round(item.match_score * 100)}%` : null])}
        </div>
        <select
          className="cvc-inline-select"
          value={item.cvc_inventory_item_id ?? ""}
          disabled={saving}
          onChange={(e) => onPatch(item.id, { cvc_inventory_item_id: e.target.value ? Number(e.target.value) : null })}
        >
          <option value="">Aucun rattachement</option>
          {candidateOptions.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
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
  const [activeTab, setActiveTab] = useState<Tab>("Cockpit");
  const [error, setError] = useState<string | null>(null);

  const dashboardQuery = useQuery<CvcRefrigerantDashboard>({
    queryKey: ["cvc-refrigerant-dashboard", token],
    queryFn: () => fetchCvcRefrigerantDashboard(token ?? ""),
    enabled: !!token,
  });

  const batchesQuery = useQuery<CvcRefrigerantBatchSummary[]>({
    queryKey: ["cvc-refrigerant-batches", token],
    queryFn: () => fetchCvcRefrigerantBatches(token ?? ""),
    enabled: !!token,
  });

  useEffect(() => {
    if (!activeBatch && dashboardQuery.data?.latest_batch) {
      setActiveBatch(dashboardQuery.data.latest_batch);
    }
  }, [activeBatch, dashboardQuery.data?.latest_batch]);

  const itemsQuery = useQuery<CvcRefrigerantItem[]>({
    queryKey: ["cvc-refrigerant-items", token, activeBatch],
    queryFn: () => fetchCvcRefrigerantItems(token ?? "", activeBatch ?? ""),
    enabled: !!token && !!activeBatch,
  });

  const importMutation = useMutation({
    mutationFn: async () => {
      if (!token || !file) throw new Error("Sélectionne un fichier ESP.");
      return postCvcRefrigerantImport(token, file);
    },
    onSuccess: (result) => {
      setActiveBatch(result.import_batch);
      setActiveTab("Cockpit");
      setFile(null);
      setError(null);
      if (fileRef.current) fileRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["cvc-refrigerant-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-refrigerant-batches"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-refrigerant-items"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-import-items"] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Erreur import ESP."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ itemId, payload }: { itemId: number; payload: UpdateCvcRefrigerantItemPayload }) => {
      if (!token) throw new Error("Session expirée.");
      return updateCvcRefrigerantItem(token, itemId, payload);
    },
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["cvc-refrigerant-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-refrigerant-items"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-refrigerant-batches"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-import-items"] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Erreur de sauvegarde."),
  });

  const items = itemsQuery.data ?? [];
  const activeSummary = (batchesQuery.data ?? []).find((batch) => batch.import_batch === activeBatch);
  const currentSavingId = updateMutation.isPending ? updateMutation.variables?.itemId ?? null : null;
  const highPriorityItems = useMemo(
    () => items.filter((item) => item.priorite === "Haute" || !["OK", "Non prioritaire"].includes(item.statut_conformite)).slice(0, 12),
    [items],
  );

  if (!token) {
    return (
      <section className="panel stack-lg">
        <h2>Fluides frigorigènes</h2>
        <p>Connecte-toi pour accéder à cette page.</p>
      </section>
    );
  }

  return (
    <section className="panel stack-lg cvc-workspace-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Gestion technique</p>
          <h2>Centrale de pilotage F-Gaz / ESP</h2>
          <p>Pilote les équipements à fluide, les contrôles d'étanchéité, les preuves et les signaux ESP/DESP.</p>
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

      <div className="cvc-command-tabs">
        {TABS.map((tab) => (
          <button key={tab} type="button" className={activeTab === tab ? "active" : ""} onClick={() => setActiveTab(tab)}>
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "Cockpit" && (
        <>
          <KpiGrid dashboard={dashboardQuery.data} />
          <div className="cvc-command-layout">
            <DistributionPanel title="Statuts F-Gaz" counts={dashboardQuery.data?.status_counts} />
            <DistributionPanel title="Conformité opérationnelle" counts={dashboardQuery.data?.conformity_counts} />
            <DistributionPanel title="Priorités" counts={dashboardQuery.data?.priority_counts} />
          </div>
          <div className="section-block">
            <div className="cvc-section-title">
              <div>
                <h3>File d'actions priorisée</h3>
                <p>Actions calculées depuis les données de fluide, les échéances et les signaux ESP.</p>
              </div>
              <button type="button" className="secondary-button" onClick={() => setActiveTab("Actions")}>
                Voir tout
              </button>
            </div>
            <ActionTable
              actions={(dashboardQuery.data?.open_actions ?? []).slice(0, 10)}
              savingId={currentSavingId}
              onStatus={(itemId, status) => {
                updateMutation.mutate({ itemId, payload: { statut_action: status } });
              }}
            />
          </div>
          {highPriorityItems.length > 0 && (
            <div className="section-block">
              <h3>Équipements à reprendre en priorité</h3>
              <div className="table-wrapper cvc-table-wrapper">
                <table className="data-table cvc-priority-table">
                  <thead>
                    <tr>
                      <th>Équipement</th>
                      <th>F-Gaz</th>
                      <th>Conformité</th>
                      <th>Preuve</th>
                    </tr>
                  </thead>
                  <tbody>
                    {highPriorityItems.map((item) => (
                      <tr key={item.id}>
                        <td><strong>{item.designation}</strong><div style={{ color: SUBTLE_TEXT }}>{item.site_raw}</div></td>
                        <td>{item.fgas_status}<div style={{ color: SUBTLE_TEXT }}>{formatNumber(item.teqco2, 3)} t éq. CO2</div></td>
                        <td><span className={`badge ${badgeClass(item.statut_conformite)}`}>{item.statut_conformite}</span></td>
                        <td>{item.preuve_attendue}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {activeTab === "Registre F-Gaz" && (
        <div className="section-block">
          <div className="cvc-section-title">
            <div>
              <h3>Registre F-Gaz éditable</h3>
              <p>
                {activeSummary
                  ? `${activeSummary.imported} lignes dans le lot ${activeSummary.import_batch}`
                  : "Choisis un lot importé pour afficher le registre."}
              </p>
            </div>
            <select className="filter-select" value={activeBatch ?? ""} onChange={(e) => setActiveBatch(e.target.value || null)}>
              <option value="">Choisir un lot ESP</option>
              {(batchesQuery.data ?? []).map((batch) => (
                <option key={batch.import_batch} value={batch.import_batch}>
                  {batch.import_batch} - {batch.imported} lignes - {batch.matched_items} rattachées
                </option>
              ))}
            </select>
          </div>
          {itemsQuery.isLoading && <p>Chargement du registre ESP...</p>}
          {!itemsQuery.isLoading && activeBatch && items.length === 0 && <p>Aucune ligne ESP trouvée pour ce lot.</p>}
          {items.length > 0 && (
            <div className="table-wrapper cvc-table-wrapper">
              <table className="data-table cvc-refrigerant-table">
                <thead>
                  <tr>
                    <th>Équipement</th>
                    <th>Fluide</th>
                    <th>Statut F-Gaz</th>
                    <th>Conformité</th>
                    <th>Contrôles</th>
                    <th>Pilotage</th>
                    <th>Rattachement CVC</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <RefrigerantRow
                      key={item.id}
                      item={item}
                      saving={currentSavingId === item.id}
                      onPatch={(itemId, payload) => updateMutation.mutate({ itemId, payload })}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "Actions" && (
        <div className="section-block">
          <h3>Plan d'action initial conformité</h3>
          <ActionTable
            actions={dashboardQuery.data?.open_actions ?? []}
            savingId={currentSavingId}
            onStatus={(itemId, status) => {
              updateMutation.mutate({ itemId, payload: { statut_action: status } });
            }}
          />
        </div>
      )}

      {activeTab === "ESP/DESP" && (
        <div className="section-block">
          <h3>Signaux ESP / DESP à suivre séparément</h3>
          <ActionTable
            actions={dashboardQuery.data?.esp_signals ?? []}
            savingId={currentSavingId}
            onStatus={(itemId, status) => {
              updateMutation.mutate({ itemId, payload: { statut_action: status } });
            }}
          />
        </div>
      )}

      {activeTab === "Import" && (
        <>
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
              <button type="button" className="primary-button" onClick={() => importMutation.mutate()} disabled={!file || importMutation.isPending}>
                {importMutation.isPending ? "Import..." : "Importer le registre ESP"}
              </button>
            </div>
            {file && (
              <p style={{ color: SUBTLE_TEXT, fontSize: "0.85rem", marginTop: 8 }}>
                Fichier prêt : <strong style={{ color: "#e2e8f0" }}>{file.name}</strong>
              </p>
            )}
          </div>
          <div className="section-block">
            <h3>Lots ESP importés</h3>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Lot</th>
                    <th>Fichier</th>
                    <th>Lignes</th>
                    <th>Rattachées</th>
                    <th>Fluide kg</th>
                    <th>t éq. CO2</th>
                  </tr>
                </thead>
                <tbody>
                  {(batchesQuery.data ?? []).map((batch) => (
                    <tr key={batch.import_batch} className="clickable-row" onClick={() => {
                      setActiveBatch(batch.import_batch);
                      setActiveTab("Registre F-Gaz");
                    }}>
                      <td>{batch.import_batch}</td>
                      <td>{batch.source_filename ?? "-"}</td>
                      <td>{batch.imported}</td>
                      <td>{batch.matched_items}</td>
                      <td>{formatNumber(batch.total_fluide_kg)}</td>
                      <td>{formatNumber(batch.total_teqco2, 3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
