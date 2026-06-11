import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import {
  fetchEnergieOverview,
  fetchSyncStatus, startSync,
  fetchMaxPowerSyncStatus, startMaxPowerSync,
  fetchLoadCurveSyncStatus, startLoadCurveSync,
  fetchDjuSyncStatus, startDjuSync,
  fetchCustomerSyncStatus, startCustomerSync,
  fetchDataRanges, fetchDataAudit,
  PrmListItem, SupplierDistributionItem, SyncStatus, LoadCurveSyncStatus, DjuSyncStatus, CustomerSyncStatus, DataRanges, EnergyDataAudit,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";
import { EnergieAsyncJobsPanel } from "../components/EnergieAsyncJobsPanel";

const SUPPLIER_COLORS = ["#2563eb", "#f97316", "#16a34a", "#a855f7", "#06b6d4", "#eab308", "#ec4899"];

const STATUS_LABEL: Record<string, string> = { idle: "En attente", running: "En cours…", success: "Succès", error: "Erreur" };
const STATUS_CLASS: Record<string, string> = { idle: "badge-gray", running: "badge-blue", success: "badge-green", error: "badge-red" };
const DATA_SOURCE_LABEL: Record<string, string> = {
  consumption: "Conso",
  load_curve: "CDC",
  max_power: "P max",
};
const AUDIT_SEVERITY_CLASS: Record<string, string> = {
  ok: "badge-green",
  info: "badge-gray",
  warning: "badge-orange",
  critical: "badge-red",
};
const CORRECTABLE_LABEL: Record<string, string> = {
  backfill_consumption: "Backfill conso",
  backfill_load_curve: "Backfill CDC",
  backfill_max_power: "Backfill P max",
  non_communicant_structural: "Non communicant (structurel)",
  cdc_activation_needed: "Activation CDC requise",
  api_rights_issue: "Droits API ENEDIS",
  non_powered_normal: "Non alimenté (normal)",
};
const PROFILE_LABEL: Record<string, string> = {
  non_powered: "Non alimenté",
  non_communicant: "Non communicant",
  communicant_closed: "Communicant non ouvert",
  communicant_open: "Communicant ouvert",
  unknown: "Profil inconnu",
};
const OUTCOME_LABEL: Record<string, string> = {
  ok_data: "OK",
  ok_empty: "Vide",
  access_not_subscribed: "Acces non souscrit",
  forbidden: "403 Refusé",
  not_found: "404 Introuvable",
  not_eligible: "Non éligible",
  cdc_inactive: "CDC inactive",
  invalid_period: "Période invalide",
  invalid_request: "Requete invalide",
  quota_exceeded: "Quota atteint",
  error: "Erreur",
  error_technical: "Erreur tech.",
};
const OUTCOME_CLASS: Record<string, string> = {
  ok_data: "badge-green",
  ok_empty: "badge-gray",
  access_not_subscribed: "badge-orange",
  forbidden: "badge-orange",
  not_found: "badge-orange",
  not_eligible: "badge-gray",
  cdc_inactive: "badge-orange",
  invalid_period: "badge-orange",
  invalid_request: "badge-orange",
  quota_exceeded: "badge-red",
  error: "badge-red",
  error_technical: "badge-red",
};
const AUDIT_FILTER_LABEL: Record<string, string> = {
  all: "Tous",
  anomalies: "Anomalies",
  structural: "Structurels",
  normal: "Normaux",
};

function SubSyncRow({
  label,
  description,
  status,
  lastDate,
  rowsAdded,
  error,
  log,
  isRunning,
  isPending,
  progress,
  actionLabel = "Sync incrémentale",
  backfillLabel = "Backfill 3 ans",
  resultLabel = "nouvelles lignes intégrées",
  onIncremental,
  onBackfill,
  onTest,
  testLabel = "Tester 5 PRM",
}: {
  label: string;
  description?: string;
  status: string | undefined;
  lastDate: string | null | undefined;
  rowsAdded?: number;
  error?: string | null;
  log?: string[];
  isRunning: boolean;
  isPending: boolean;
  progress?: number | null;
  actionLabel?: string;
  backfillLabel?: string;
  resultLabel?: string;
  onIncremental: () => void;
  onBackfill?: () => void;
  onTest?: () => void;
  testLabel?: string;
}) {
  return (
    <div className="sync-sub-row">
      <div className="sync-sub-header">
        <div>
          <span className="sync-sub-label">{label}</span>
          {description && <p className="sync-sub-description">{description}</p>}
        </div>
        <div className="sync-panel-meta">
          {status && (
            <span className={`badge ${STATUS_CLASS[status] ?? "badge-gray"}`}>
              {STATUS_LABEL[status] ?? status}
            </span>
          )}
          {lastDate && <span className="sync-last-date">Dernière sync : {lastDate}</span>}
        </div>
      </div>
      {isRunning && progress != null && (
        <div className="sync-progress-row">
          <div className="sync-progress-bar"><div className="sync-progress-fill" style={{ width: `${progress}%` }} /></div>
          <span className="sync-progress-label">{progress}%</span>
        </div>
      )}
      {status === "success" && rowsAdded != null && rowsAdded > 0 && (
        <p className="sync-result-ok">{rowsAdded.toLocaleString("fr-FR")} {resultLabel}</p>
      )}
      {error && <p className="sync-error">{error}</p>}
      <div className="sync-actions">
        <button type="button" className="btn-primary" disabled={isRunning || isPending} onClick={onIncremental}>
          {isRunning ? "En cours…" : actionLabel}
        </button>
        {onBackfill && (
          <button
            type="button"
            className="btn-secondary"
            disabled={isRunning || isPending}
            onClick={() => {
              if (lastDate && !window.confirm(`Des données existent déjà (dernière sync : ${lastDate}).\n\nRelancer ${backfillLabel.toLowerCase()} va re-télécharger l'historique demandé. Continuer ?`)) return;
              onBackfill();
            }}
            title={backfillLabel}
          >
            {backfillLabel}
          </button>
        )}
        {onTest && (
          <button
            type="button"
            className="btn-secondary"
            disabled={isRunning || isPending}
            onClick={onTest}
          >
            {testLabel}
          </button>
        )}
      </div>
      {log && log.length > 0 && (
        <pre className="sync-log">{log.slice(-10).join("\n")}</pre>
      )}
    </div>
  );
}

function SyncPanel({ token }: { token: string }) {
  const [expanded, setExpanded] = useState(true);
  const [customerRefreshUntil, setCustomerRefreshUntil] = useState(0);

  const { data: consumptionStatus, refetch: refetchConsumption } = useQuery({
    queryKey: ["sync-consumption-status"],
    queryFn: () => fetchSyncStatus(token),
    refetchInterval: (query) => (query.state.data as SyncStatus | undefined)?.status === "running" ? 3000 : false,
  });

  const { data: maxPowerStatus, refetch: refetchMaxPower } = useQuery({
    queryKey: ["sync-max-power-status"],
    queryFn: () => fetchMaxPowerSyncStatus(token),
    refetchInterval: (query) => (query.state.data as SyncStatus | undefined)?.status === "running" ? 3000 : false,
  });

  const { data: loadCurveStatus, refetch: refetchLoadCurve } = useQuery({
    queryKey: ["sync-load-curve-status"],
    queryFn: () => fetchLoadCurveSyncStatus(token),
    refetchInterval: (query) => (query.state.data as LoadCurveSyncStatus | undefined)?.status === "running" ? 5000 : false,
  });

  const { data: djuStatus, refetch: refetchDju } = useQuery({
    queryKey: ["sync-dju-status"],
    queryFn: () => fetchDjuSyncStatus(token),
    refetchInterval: (query) => (query.state.data as DjuSyncStatus | undefined)?.status === "running" ? 2000 : false,
  });

  const customerQuery = useQuery({
    queryKey: ["sync-customer-status"],
    queryFn: () => fetchCustomerSyncStatus(token),
    refetchInterval: (query) => {
      const status = (query.state.data as CustomerSyncStatus | undefined)?.status;
      return status === "running" || Date.now() < customerRefreshUntil ? 2500 : false;
    },
  });
  const { data: customerStatus, refetch: refetchCustomer } = customerQuery;

  const djuMutation = useMutation({
    mutationFn: () => startDjuSync(token),
    onSuccess: () => { setTimeout(() => refetchDju(), 500); },
  });

  const customerMutation = useMutation({
    mutationFn: () => startCustomerSync(token),
    onSuccess: () => {
      setCustomerRefreshUntil(Date.now() + 60_000);
      setTimeout(() => refetchCustomer(), 250);
      setTimeout(() => refetchCustomer(), 1500);
      setTimeout(() => refetchCustomer(), 4000);
    },
  });

  const consumptionMutation = useMutation({
    mutationFn: (options?: { historyDays?: number; prmLimit?: number }) => startSync(token, options),
    onSuccess: () => { setTimeout(() => refetchConsumption(), 500); },
  });

  const maxPowerMutation = useMutation({
    mutationFn: (options?: { historyDays?: number; prmLimit?: number }) => startMaxPowerSync(token, options),
    onSuccess: () => { setTimeout(() => refetchMaxPower(), 500); },
  });

  const loadCurveMutation = useMutation({
    mutationFn: (options?: { historyDays?: number; prmLimit?: number; resetState?: boolean }) => startLoadCurveSync(token, options),
    onSuccess: () => { setTimeout(() => refetchLoadCurve(), 500); },
  });

  const customerProgress = customerStatus && customerStatus.sources_total > 0
    ? Math.round((customerStatus.sources_done / customerStatus.sources_total) * 100)
    : null;
  const customerDisplayStatus = customerMutation.isPending ? "running" : customerStatus?.status;
  const customerDisplayError =
    customerStatus?.error ??
    (customerMutation.isError ? (customerMutation.error as Error).message : null) ??
    (customerQuery.isError ? (customerQuery.error as Error).message : null);

  const consumptionProgress = consumptionStatus && consumptionStatus.prms_total > 0
    ? Math.round((consumptionStatus.prms_done / consumptionStatus.prms_total) * 100)
    : null;
  const maxPowerProgress = maxPowerStatus && maxPowerStatus.prms_total > 0
    ? Math.round((maxPowerStatus.prms_done / maxPowerStatus.prms_total) * 100)
    : null;
  const loadCurveProgress = loadCurveStatus && loadCurveStatus.chunks_total > 0
    ? Math.round((loadCurveStatus.chunks_done / loadCurveStatus.chunks_total) * 100)
    : null;

  const anyRunning =
    djuStatus?.status === "running" ||
    customerStatus?.status === "running" ||
    consumptionStatus?.status === "running" ||
    maxPowerStatus?.status === "running" ||
    loadCurveStatus?.status === "running";
  const anyPending =
    djuMutation.isPending ||
    customerMutation.isPending ||
    consumptionMutation.isPending ||
    maxPowerMutation.isPending ||
    loadCurveMutation.isPending;
  const anyBusy = anyRunning || anyPending;

  return (
    <div className="sync-panel sync-panel--collection">
      <div className="sync-panel-header" onClick={() => setExpanded((v) => !v)}>
        <div>
          <span className="sync-panel-title">Collecte de données ENEDIS</span>
          <p className="sync-panel-subtitle">Mode synchrone de secours pour avancer malgré le blocage async côté ENEDIS.</p>
        </div>
        <div className="sync-panel-meta">
          {anyRunning && <span className="badge badge-blue">En cours…</span>}
          <span className="sync-toggle">{expanded ? "▲" : "▼"}</span>
        </div>
      </div>

      {expanded && (
        <div className="sync-panel-body">
          <div className="sync-section">
            <div className="sync-section-heading">
              <span>1. Prérequis et référentiels</span>
              <small>À lancer avant une reprise large si le périmètre des contrats a changé.</small>
            </div>
            <SubSyncRow
              label="Référentiel contractuel ENEDIS"
              description="Récupère les PRM en contrat, adresses, raccordements, puissances souscrites et niveaux de service. Les collectes ci-dessous partent ensuite de cette liste."
              status={customerDisplayStatus}
              lastDate={customerStatus?.last_sync_at}
              rowsAdded={customerStatus?.changes_detected}
              error={customerDisplayError}
              log={customerStatus?.log}
              isRunning={customerDisplayStatus === "running"}
              isPending={customerMutation.isPending || anyBusy}
              progress={customerProgress}
              actionLabel="Mettre à jour les contrats"
              resultLabel="changement(s) détecté(s)"
              onIncremental={() => customerMutation.mutate()}
            />

            <SubSyncRow
              label="DJU météo"
              description="Met à jour les degrés-jours utiles aux analyses conso x météo."
              status={djuStatus?.status}
              lastDate={djuStatus?.last_sync_date}
              rowsAdded={djuStatus?.rows_added}
              error={djuStatus?.error}
              log={djuStatus?.log}
              isRunning={djuStatus?.status === "running"}
              isPending={djuMutation.isPending || anyBusy}
              actionLabel="Synchroniser les DJU"
              onIncremental={() => djuMutation.mutate()}
            />
          </div>

          <div className="sync-section sync-section--primary">
            <div className="sync-section-heading">
              <span>2. Collecte synchrone de secours</span>
              <small>Conso et P max écrivent en upsert par PRM/date ; la courbe de charge ajoute seulement les points manquants.</small>
            </div>

            <div className="sync-guidance-grid">
              <div>
                <strong>Test conseillé</strong>
                <span>Utiliser “Tester 5 PRM” sur 30 jours pour valider les droits et la forme des réponses sans lancer tout le parc.</span>
              </div>
              <div>
                <strong>Reprise historique</strong>
                <span>Conso et P max remplacent les lignes existantes ; la CDC évite les doublons. En mode test, l’état global de reprise n’est pas avancé.</span>
              </div>
              <div>
                <strong>Ordre logique</strong>
                <span>Contrats ENEDIS, puis consommation et P max. La CDC reste à réserver aux profils fins, car elle est beaucoup plus longue.</span>
              </div>
            </div>

            <SubSyncRow
              label="Consommations journalières"
              description="Alimente enedis_data.csv, utilisé par les pages énergie, les factures et les préconisations."
              status={consumptionStatus?.status}
              lastDate={consumptionStatus?.last_sync_date}
              rowsAdded={consumptionStatus?.rows_added}
              error={consumptionStatus?.error}
              log={consumptionStatus?.log}
              isRunning={consumptionStatus?.status === "running"}
              isPending={consumptionMutation.isPending || anyBusy}
              progress={consumptionProgress}
              actionLabel="Mise à jour incrémentale"
              backfillLabel="Backfill 3 ans"
              onIncremental={() => consumptionMutation.mutate(undefined)}
              onBackfill={() => consumptionMutation.mutate({ historyDays: 1095 })}
              onTest={() => consumptionMutation.mutate({ historyDays: 30, prmLimit: 5 })}
            />

            <SubSyncRow
              label="Puissances max journalières"
              description="Alimente enedis_max_power.csv. C'est le chemin léger à privilégier pour récupérer les pics historiques sans collecter toute la courbe de charge."
              status={maxPowerStatus?.status}
              lastDate={maxPowerStatus?.last_sync_date}
              rowsAdded={maxPowerStatus?.rows_added}
              error={maxPowerStatus?.error}
              log={maxPowerStatus?.log}
              isRunning={maxPowerStatus?.status === "running"}
              isPending={maxPowerMutation.isPending || anyBusy}
              progress={maxPowerProgress}
              actionLabel="Mise à jour incrémentale"
              backfillLabel="Backfill 3 ans"
              onIncremental={() => maxPowerMutation.mutate(undefined)}
              onBackfill={() => maxPowerMutation.mutate({ historyDays: 1095 })}
              onTest={() => maxPowerMutation.mutate({ historyDays: 30, prmLimit: 5 })}
            />

            <SubSyncRow
              label="Courbes de charge"
              description="Collecte fine par pas de mesure. Utile pour analyser les profils, mais à lancer seulement si la Pmax et la conso journalière ne suffisent pas."
              status={loadCurveStatus?.status}
              lastDate={loadCurveStatus?.last_sync_date}
              rowsAdded={loadCurveStatus?.rows_added}
              error={loadCurveStatus?.error}
              log={loadCurveStatus?.log}
              isRunning={loadCurveStatus?.status === "running"}
              isPending={loadCurveMutation.isPending || anyBusy}
              progress={loadCurveProgress}
              actionLabel="Mise à jour incrémentale"
              backfillLabel="Backfill CDC complet"
              onIncremental={() => loadCurveMutation.mutate(undefined)}
              onBackfill={() => loadCurveMutation.mutate({ resetState: true })}
              onTest={() => loadCurveMutation.mutate({ historyDays: 7, prmLimit: 5 })}
              testLabel="Tester 5 PRM / 7j"
            />
          </div>
        </div>
      )}
    </div>
  );
}

function SupplierPieChart({ data }: { data: SupplierDistributionItem[] }) {
  if (data.length === 0) return null;
  const pieData = data.map((s) => ({ name: s.supplier, value: s.total_kva, count: s.prm_count }));
  return (
    <div className="supplier-pie-wrapper">
      <h3 className="supplier-pie-title">Répartition par fournisseur (kVA souscrit)</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={pieData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={80}
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            labelLine={false}
          >
            {pieData.map((_, i) => (
              <Cell key={i} fill={SUPPLIER_COLORS[i % SUPPLIER_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number, name: string, props) => [
              `${value.toLocaleString("fr-FR")} kVA — ${(props.payload as { count: number }).count} PRM`,
              name,
            ]}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

function connectionBadge(state: string | null): string {
  if (!state) return "";
  if (state.toLowerCase().includes("non alimenté")) return "badge-red";
  if (state.toLowerCase().includes("alimenté")) return "badge-green";
  return "badge-gray";
}

function communicantBadge(level: string | null): string {
  if (!level) return "";
  if (level.toLowerCase().includes("communicant")) return "badge-blue";
  return "badge-gray";
}

type CalibStatus = "sous_dimensionne" | "proche_seuil" | "bien_calibre" | "sur_souscrit";

const CALIB_LABEL: Record<CalibStatus, string> = {
  sous_dimensionne: "Sous-dim.",
  proche_seuil: "Proche seuil",
  bien_calibre: "Bien calibré",
  sur_souscrit: "Sur-souscrit",
};

const CALIB_CLASS: Record<CalibStatus, string> = {
  sous_dimensionne: "badge-red",
  proche_seuil: "badge-orange",
  bien_calibre: "badge-green",
  sur_souscrit: "badge-blue",
};

function calibBadge(status: string | null, ratio: number | null) {
  if (!status) return null;
  const s = status as CalibStatus;
  return (
    <span className={`badge ${CALIB_CLASS[s] ?? "badge-gray"}`} title={ratio != null ? `${ratio}%` : undefined}>
      {CALIB_LABEL[s] ?? status}
    </span>
  );
}

function DataCoverageBar({ token }: { token: string }) {
  const [auditExpanded, setAuditExpanded] = useState(false);
  const [auditFilter, setAuditFilter] = useState<"all" | "anomalies" | "structural" | "normal">("anomalies");
  const { data } = useQuery<DataRanges>({
    queryKey: ["energie-data-ranges"],
    queryFn: () => fetchDataRanges(token),
    staleTime: 60_000,
  });
  const auditQuery = useQuery<EnergyDataAudit>({
    queryKey: ["energie-data-audit"],
    queryFn: () => fetchDataAudit(token),
    enabled: auditExpanded,
    staleTime: 60_000,
  });

  const sources: { key: keyof Omit<DataRanges, "contracts">; label: string }[] = [
    { key: "consumption", label: "Conso. journalière" },
    { key: "max_power", label: "Puissance max" },
    { key: "load_curve", label: "Courbe de charge" },
    { key: "dju", label: "DJU météo" },
  ];

  if (!data) return null;
  const audit = auditQuery.data;
  const auditRowsFiltered = (audit?.rows ?? []).filter((row) => {
    if (auditFilter === "all") return true;
    if (auditFilter === "anomalies") return row.severity === "critical" || row.severity === "warning";
    if (auditFilter === "structural") return row.severity === "info" || row.meter_profile === "non_communicant";
    if (auditFilter === "normal") return row.severity === "ok";
    return true;
  });
  const auditRows = auditRowsFiltered.slice(0, 50);
  const profileCounts = audit?.profile_counts ?? { non_powered: 0, non_communicant: 0, communicant_closed: 0, communicant_open: 0, unknown: 0 };
  const correctableEntries = audit ? Object.entries(audit.correctable).filter(([, count]) => count > 0) : [];

  return (
    <div className="data-coverage-bar">
      <span className="data-coverage-title">Couverture des données</span>
      <button type="button" className="secondary-button compact-button" onClick={() => setAuditExpanded((value) => !value)}>
        {auditExpanded ? "Masquer audit" : "Audit PRM"}
      </button>
      <div className="data-coverage-sources">
        {sources.map(({ key, label }) => {
          const src = data[key];
          const hasData = src.first_date != null;
          return (
            <div key={key} className={`data-coverage-chip ${hasData ? "chip-ok" : "chip-empty"}`}>
              <span className="chip-label">{label}</span>
              {hasData ? (
                <span className="chip-dates">{src.first_date} → {src.last_date}</span>
              ) : (
                <span className="chip-dates">Aucune donnée</span>
              )}
              {src.row_count > 0 && (
                <span className="chip-count">{src.row_count.toLocaleString("fr-FR")} lignes</span>
              )}
            </div>
          );
        })}
        <div className="data-coverage-chip chip-ok">
          <span className="chip-label">Contrats</span>
          <span className="chip-dates">{data.contracts.count.toLocaleString("fr-FR")} PRMs</span>
        </div>
      </div>
      {auditExpanded && (
        <div className="data-audit-panel">
          {auditQuery.isLoading && <p className="loading-text">Audit des PRM en cours...</p>}
          {auditQuery.isError && <p className="error-text">{(auditQuery.error as Error).message}</p>}
          {audit && (
            <>
              <div className="data-audit-summary">
                <div>
                  <span>Complets</span>
                  <strong>{audit.summary.all_sources.toLocaleString("fr-FR")}</strong>
                </div>
                <div>
                  <span>Partiels</span>
                  <strong>{audit.summary.partial_sources.toLocaleString("fr-FR")}</strong>
                </div>
                <div>
                  <span>Anomalies à corriger</span>
                  <strong style={{ color: audit.summary.critical > 0 ? "#dc2626" : undefined }}>
                    {audit.summary.critical.toLocaleString("fr-FR")}
                  </strong>
                </div>
                <div>
                  <span>Alertes</span>
                  <strong>{audit.summary.with_warnings.toLocaleString("fr-FR")}</strong>
                </div>
                <div>
                  <span>Vides normaux</span>
                  <strong>{audit.summary.info.toLocaleString("fr-FR")}</strong>
                </div>
              </div>

              <div className="data-audit-source-grid">
                {Object.entries(audit.sources).map(([key, source]) => (
                  <div key={key} className="data-audit-source">
                    <strong>{source.label}</strong>
                    <span>{source.prm_count.toLocaleString("fr-FR")} / {audit.contracts_count.toLocaleString("fr-FR")} PRM</span>
                    <small>{source.missing_prm_count.toLocaleString("fr-FR")} manquant(s), {source.weak_prm_count.toLocaleString("fr-FR")} court(s)</small>
                  </div>
                ))}
              </div>

              <div className="data-audit-source-grid" style={{ marginTop: 12 }}>
                {(["communicant_open", "communicant_closed", "non_communicant", "non_powered", "unknown"] as const).map((profile) => (
                  <div key={profile} className="data-audit-source">
                    <strong>{PROFILE_LABEL[profile]}</strong>
                    <span>{(profileCounts[profile] ?? 0).toLocaleString("fr-FR")} PRM</span>
                  </div>
                ))}
              </div>

              {correctableEntries.length > 0 && (
                <div className="data-audit-actions">
                  {correctableEntries.map(([key, count]) => (
                    <span key={key} className="badge badge-blue">
                      {CORRECTABLE_LABEL[key] ?? key} : {count.toLocaleString("fr-FR")}
                    </span>
                  ))}
                </div>
              )}

              <div className="data-audit-actions" style={{ marginTop: 12 }}>
                {(["all", "anomalies", "structural", "normal"] as const).map((f) => (
                  <button
                    key={f}
                    type="button"
                    className={`badge ${auditFilter === f ? "badge-blue" : "badge-gray"}`}
                    onClick={() => setAuditFilter(f)}
                    style={{ cursor: "pointer", border: "none" }}
                  >
                    {AUDIT_FILTER_LABEL[f]} ({(f === "all"
                      ? audit.rows.length
                      : f === "anomalies"
                      ? audit.summary.critical + audit.summary.with_warnings
                      : f === "structural"
                      ? audit.summary.info + (profileCounts.non_communicant ?? 0)
                      : audit.summary.all_sources
                    ).toLocaleString("fr-FR")})
                  </button>
                ))}
              </div>

              {auditRows.length > 0 ? (
                <div className="data-audit-table-wrapper">
                  <table className="data-table data-audit-table">
                    <thead>
                      <tr>
                        <th>PRM</th>
                        <th>Site</th>
                        <th>Profil</th>
                        <th>Origine ENEDIS</th>
                        <th>Jours</th>
                        <th>Diagnostic & action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditRows.map((row) => (
                        <tr key={row.usage_point_id}>
                          <td>
                            <span className={`badge ${AUDIT_SEVERITY_CLASS[row.severity] ?? "badge-gray"}`}>
                              {row.usage_point_id}
                            </span>
                          </td>
                          <td>
                            <div className="recommendation-power-cell">
                              <strong>{row.name}</strong>
                              <small>{row.connection_state ?? "-"} | {row.service_level ?? "-"}</small>
                            </div>
                          </td>
                          <td>
                            <span className="badge badge-gray">{PROFILE_LABEL[row.meter_profile] ?? row.meter_profile}</span>
                          </td>
                          <td>
                            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                              {(["consumption", "load_curve", "max_power"] as const).map((src) => {
                                const outcome = row.enedis_outcomes?.[src];
                                const cls = outcome ? OUTCOME_CLASS[outcome] ?? "badge-gray" : "badge-gray";
                                const lbl = outcome ? OUTCOME_LABEL[outcome] ?? outcome : "—";
                                return (
                                  <span key={src} className={`badge ${cls}`} title={`${DATA_SOURCE_LABEL[src]} : ${outcome ?? "non testé"}`}>
                                    {DATA_SOURCE_LABEL[src]} : {lbl}
                                  </span>
                                );
                              })}
                            </div>
                          </td>
                          <td>
                            <span className="cell-mono">
                              C {row.coverage_days.consumption ?? 0} / CDC {row.coverage_days.load_curve ?? 0} / P {row.coverage_days.max_power ?? 0}
                            </span>
                          </td>
                          <td>
                            <div className="recommendation-power-cell">
                              <span>{row.probable_reason}</span>
                              <small>{row.correctable_actions.join(" | ") || "-"}</small>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {auditRowsFiltered.length > auditRows.length && (
                    <p className="loading-text">… {(auditRowsFiltered.length - auditRows.length).toLocaleString("fr-FR")} autres lignes (limite d'affichage : 50)</p>
                  )}
                </div>
              ) : (
                <p className="loading-text">Aucun PRM dans cette catégorie.</p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export function EnergiePage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [calibFilter, setCalibFilter] = useState<string>("all");

  const { data, isLoading, error } = useQuery({
    queryKey: ["energie-overview"],
    queryFn: () => fetchEnergieOverview(token!),
    enabled: !!token,
  });

  const filtered: PrmListItem[] = (data?.prms ?? []).filter((prm) => {
    if (calibFilter !== "all" && prm.calibration_status !== calibFilter) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      prm.name.toLowerCase().includes(q) ||
      prm.usage_point_id.includes(q) ||
      prm.address.toLowerCase().includes(q) ||
      (prm.contractor ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="page">
      <div className="page-header page-header-row">
        <div>
          <h2>Énergie</h2>
          <p className="page-subtitle">Électricité ENEDIS — Points de livraison (PRMs)</p>
        </div>
        <div className="page-header-actions">
          <button type="button" className="secondary-button" onClick={() => navigate("/energie/preconisations")}>
            Preconisations
          </button>
          <button type="button" className="secondary-button" onClick={() => navigate("/energie/factures")}>
            Factures
          </button>
        </div>
      </div>

      <DataCoverageBar token={token!} />
      <SyncPanel token={token!} />
      <EnergieAsyncJobsPanel token={token!} />

      {isLoading && <p>Chargement…</p>}
      {error && <p className="error-text">{(error as Error).message}</p>}

      {data && (
        <>
          <div className="kpi-row">
            <div className="kpi-card">
              <span className="kpi-label">PRMs contractuels</span>
              <span className="kpi-value">{data.kpis.total_prms}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Puissance souscrite totale</span>
              <span className="kpi-value">{data.kpis.total_subscribed_kva.toLocaleString("fr-FR")} kVA</span>
            </div>
            {data.kpis.sous_dimensionnes > 0 && (
              <div className="kpi-card kpi-card--alert">
                <span className="kpi-label">Sous-dimensionnés</span>
                <span className="kpi-value">{data.kpis.sous_dimensionnes}</span>
              </div>
            )}
            {data.kpis.proche_seuil > 0 && (
              <div className="kpi-card kpi-card--warn">
                <span className="kpi-label">Proches du seuil</span>
                <span className="kpi-value">{data.kpis.proche_seuil}</span>
              </div>
            )}
            {data.kpis.sur_souscrits > 0 && (
              <div className="kpi-card kpi-card--info">
                <span className="kpi-label">Sur-souscrits</span>
                <span className="kpi-value">{data.kpis.sur_souscrits}</span>
              </div>
            )}
            {data.kpis.calibration_inconnue > 0 && (
              <div className="kpi-card">
                <span className="kpi-label">Calibrage inconnu</span>
                <span className="kpi-value">{data.kpis.calibration_inconnue}</span>
              </div>
            )}
          </div>

          <SupplierPieChart data={data.supplier_distribution} />

          <div className="list-toolbar">
            <input
              type="search"
              placeholder="Rechercher par nom, PRM, adresse…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
            <select
              value={calibFilter}
              onChange={(e) => setCalibFilter(e.target.value)}
              className="filter-select"
            >
              <option value="all">Tous calibrages</option>
              <option value="sous_dimensionne">Sous-dimensionnés</option>
              <option value="proche_seuil">Proches du seuil</option>
              <option value="bien_calibre">Bien calibrés</option>
              <option value="sur_souscrit">Sur-souscrits</option>
            </select>
            <span className="result-count">{filtered.length} résultat{filtered.length !== 1 ? "s" : ""}</span>
          </div>

          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>PRM</th>
                  <th>Adresse</th>
                  <th>Fournisseur</th>
                  <th>Souscrit</th>
                  <th>Pic 3 ans</th>
                  <th>Calibrage</th>
                  <th>État</th>
                  <th>Communicant</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((prm) => (
                  <tr
                    key={prm.usage_point_id}
                    className="clickable-row"
                    onClick={() => navigate(`/energie/${prm.usage_point_id}`)}
                  >
                    <td className="cell-bold">{prm.name}</td>
                    <td className="cell-mono">{prm.usage_point_id}</td>
                    <td>{prm.address}</td>
                    <td>{prm.contractor}</td>
                    <td className="cell-number">{prm.subscribed_power_kva != null ? `${prm.subscribed_power_kva} kVA` : "—"}</td>
                    <td className="cell-number">{prm.peak_kva_3y != null ? `${prm.peak_kva_3y} kVA` : "—"}</td>
                    <td>{calibBadge(prm.calibration_status, prm.calibration_ratio)}</td>
                    <td>
                      {prm.connection_state && (
                        <span className={`badge ${connectionBadge(prm.connection_state)}`}>
                          {prm.connection_state}
                        </span>
                      )}
                    </td>
                    <td>
                      {prm.services_level && (
                        <span className={`badge ${communicantBadge(prm.services_level)}`}>
                          {prm.services_level.includes("Communicant") ? "Communicant" : prm.services_level}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={9} className="cell-empty">Aucun résultat</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
