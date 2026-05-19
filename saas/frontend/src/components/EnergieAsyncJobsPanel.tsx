/**
 * Panneau de monitoring des dossiers async ENEDIS (Phase C).
 *
 * Affiche :
 * - Boutons de lancement : Backfill CDC, Backfill Conso, Backfill complet (CDC 2 ans + Conso 3 ans)
 * - Bouton "Poll FTP maintenant" pour forcer un cycle de récupération
 * - Filtres par type (CDC/ENERGIE) et statut
 * - Tableau des dossiers : ID, type, période, statut, durée d'attente, lignes ingérées, erreur
 * - Polling auto toutes les 30 secondes pour refléter l'avancement
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  EnedisAsyncJob,
  EnedisAsyncJobStatus,
  EnedisAsyncJobType,
  fetchEnedisAsyncJobs,
  startEnedisAsyncJob,
  startEnedisAsyncBackfillFull,
  triggerEnedisAsyncPollNow,
} from "../lib/api";

const STATUS_LABEL: Record<EnedisAsyncJobStatus, string> = {
  requested: "Demandé",
  file_received: "Fichier reçu",
  decrypted: "Déchiffré",
  parsed: "Parsé",
  success: "Succès",
  error: "Erreur",
};

const STATUS_CLASS: Record<EnedisAsyncJobStatus, string> = {
  requested: "badge-blue",
  file_received: "badge-blue",
  decrypted: "badge-blue",
  parsed: "badge-blue",
  success: "badge-green",
  error: "badge-red",
};

function formatDuration(fromIso: string | null, toIso: string | null): string {
  if (!fromIso) return "-";
  const from = new Date(fromIso).getTime();
  const to = toIso ? new Date(toIso).getTime() : Date.now();
  const seconds = Math.max(0, Math.floor((to - from) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remMinutes = minutes % 60;
  return `${hours}h${remMinutes.toString().padStart(2, "0")}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" }).format(new Date(iso));
}

function todayMinus(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export function EnergieAsyncJobsPanel({ token }: { token: string }) {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(true);
  const [typeFilter, setTypeFilter] = useState<EnedisAsyncJobType | "">("");
  const [statusFilter, setStatusFilter] = useState<EnedisAsyncJobStatus | "">("");
  const [showStartForm, setShowStartForm] = useState(false);
  const [formType, setFormType] = useState<EnedisAsyncJobType>("ENERGIE");
  const [formDateStart, setFormDateStart] = useState(todayMinus(7));
  const [formDateEnd, setFormDateEnd] = useState(todayMinus(1));
  const [feedback, setFeedback] = useState<{ kind: "success" | "error"; message: string } | null>(null);

  const jobsQuery = useQuery<EnedisAsyncJob[]>({
    queryKey: ["enedis-async-jobs", typeFilter, statusFilter],
    queryFn: () =>
      fetchEnedisAsyncJobs(token, {
        type: typeFilter || undefined,
        status: statusFilter || undefined,
        limit: 100,
      }),
    enabled: true,
    refetchInterval: expanded ? 30_000 : 60_000,
  });

  const startMut = useMutation({
    mutationFn: () =>
      startEnedisAsyncJob(token, {
        type_donnee: formType,
        date_start: formDateStart,
        date_end: formDateEnd,
      }),
    onSuccess: (resp) => {
      setFeedback({ kind: "success", message: resp.message });
      setShowStartForm(false);
      qc.invalidateQueries({ queryKey: ["enedis-async-jobs"] });
    },
    onError: (err: Error) => setFeedback({ kind: "error", message: err.message }),
  });

  const backfillFullMut = useMutation({
    mutationFn: () => startEnedisAsyncBackfillFull(token),
    onSuccess: (resp) => {
      const expectedDossiers = resp.summary
        ? Object.values(resp.summary).reduce((sum, item) => sum + (item.expected_dossier_count ?? 0), 0)
        : 0;
      if (resp.background) {
        setFeedback({
          kind: "success",
          message: expectedDossiers
            ? `${resp.message} (${expectedDossiers} dossiers prevus par lots de 50 PRM maximum)`
            : resp.message,
        });
        qc.invalidateQueries({ queryKey: ["enedis-async-jobs"] });
        return;
      }
      const errorSuffix = resp.errors?.length
        ? `; ${resp.errors.length} fenêtre(s)/lot(s) rejeté(s)`
        : "";
      setFeedback({
        kind: resp.errors?.length ? "error" : "success",
        message: `${resp.message} (${resp.dossier_ids.ENERGIE.length} ENERGIE + ${resp.dossier_ids.CDC.length} CDC dossiers${errorSuffix})`,
      });
      qc.invalidateQueries({ queryKey: ["enedis-async-jobs"] });
    },
    onError: (err: Error) => setFeedback({ kind: "error", message: err.message }),
  });

  const pollNowMut = useMutation({
    mutationFn: () => triggerEnedisAsyncPollNow(token),
    onSuccess: (resp) => setFeedback({ kind: "success", message: resp.message }),
    onError: (err: Error) => setFeedback({ kind: "error", message: err.message }),
  });

  const jobs = jobsQuery.data ?? [];
  const counters = {
    total: jobs.length,
    success: jobs.filter((j) => j.status === "success").length,
    inflight: jobs.filter((j) => j.status === "requested" || j.status === "file_received").length,
    error: jobs.filter((j) => j.status === "error").length,
  };

  return (
    <div className="data-coverage-bar" style={{ flexDirection: "column", alignItems: "stretch", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <strong>Backfill async ENEDIS / FTP</strong>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <span className="badge badge-gray">Succès : {counters.success}</span>
          <span className="badge badge-blue">En cours : {counters.inflight}</span>
          {counters.error > 0 && <span className="badge badge-red">Erreurs : {counters.error}</span>}
          <button type="button" className="secondary-button compact-button" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "Masquer" : "Afficher"}
          </button>
        </div>
      </div>

      {expanded && (
        <>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              className="primary-button compact-button"
              disabled={backfillFullMut.isPending}
              onClick={() => backfillFullMut.mutate()}
            >
              {backfillFullMut.isPending ? "Lancement…" : "Backfill complet (CDC 2 ans fractionnés + Conso 3 ans)"}
            </button>
            <button
              type="button"
              className="secondary-button compact-button"
              onClick={() => setShowStartForm((v) => !v)}
            >
              {showStartForm ? "Annuler" : "Lancer un backfill personnalisé"}
            </button>
            <button
              type="button"
              className="secondary-button compact-button"
              disabled={pollNowMut.isPending}
              onClick={() => pollNowMut.mutate()}
            >
              Poll FTP maintenant
            </button>
          </div>

          {showStartForm && (
            <div style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap", padding: 12, background: "rgba(15, 23, 42, 0.5)", borderRadius: 12 }}>
              <label className="field">
                <span>Type</span>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value as EnedisAsyncJobType)}
                  className="form-input"
                >
                  <option value="ENERGIE">Conso journalière (ENERGIE)</option>
                  <option value="CDC">Courbe de charge (CDC)</option>
                </select>
              </label>
              <label className="field">
                <span>Date début</span>
                <input
                  type="date"
                  value={formDateStart}
                  onChange={(e) => setFormDateStart(e.target.value)}
                  className="form-input"
                />
              </label>
              <label className="field">
                <span>Date fin</span>
                <input
                  type="date"
                  value={formDateEnd}
                  onChange={(e) => setFormDateEnd(e.target.value)}
                  className="form-input"
                />
              </label>
              <button
                type="button"
                className="primary-button compact-button"
                disabled={startMut.isPending}
                onClick={() => startMut.mutate()}
              >
                {startMut.isPending ? "Envoi…" : "Lancer"}
              </button>
            </div>
          )}

          {feedback && (
            <div className={feedback.kind === "error" ? "error-text" : "success-text"}>
              {feedback.message}
            </div>
          )}

          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as EnedisAsyncJobType | "")}
              className="filter-select"
            >
              <option value="">Tous types</option>
              <option value="CDC">CDC</option>
              <option value="ENERGIE">ENERGIE</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as EnedisAsyncJobStatus | "")}
              className="filter-select"
            >
              <option value="">Tous statuts</option>
              <option value="requested">Demandé</option>
              <option value="file_received">Fichier reçu</option>
              <option value="decrypted">Déchiffré</option>
              <option value="parsed">Parsé</option>
              <option value="success">Succès</option>
              <option value="error">Erreur</option>
            </select>
            <span className="result-count">{jobs.length} dossier{jobs.length !== 1 ? "s" : ""}</span>
          </div>

          {jobsQuery.isLoading && <p>Chargement…</p>}
          {jobsQuery.isError && <p className="error-text">{(jobsQuery.error as Error).message}</p>}

          {!jobsQuery.isLoading && jobs.length === 0 && (
            <p style={{ color: "#94a3b8" }}>Aucun dossier async pour le moment.</p>
          )}

          {jobs.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table className="data-table" style={{ minWidth: 760 }}>
                <thead>
                  <tr>
                    <th>Dossier</th>
                    <th>Type</th>
                    <th>Période</th>
                    <th>PRM</th>
                    <th>Statut</th>
                    <th>Demandé</th>
                    <th>Durée</th>
                    <th>Lignes</th>
                    <th>Erreur</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((j) => (
                    <tr key={j.id}>
                      <td><span className="cell-mono">{j.dossier_id}</span></td>
                      <td>{j.type_donnee}</td>
                      <td>
                        <span className="cell-mono">{j.date_start} → {j.date_end}</span>
                      </td>
                      <td>{j.prm_count}</td>
                      <td>
                        <span className={`badge ${STATUS_CLASS[j.status]}`}>{STATUS_LABEL[j.status]}</span>
                      </td>
                      <td>{formatDate(j.requested_at)}</td>
                      <td>{formatDuration(j.requested_at, j.finished_at)}</td>
                      <td>{j.rows_added ?? "-"}</td>
                      <td>
                        {j.error_message ? (
                          <small style={{ color: "#fca5a5" }} title={j.error_message}>
                            {j.error_message.slice(0, 60)}{j.error_message.length > 60 ? "…" : ""}
                          </small>
                        ) : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
