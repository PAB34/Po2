import { useMemo, useState, type CSSProperties } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../providers/AuthProvider";
import {
  bulkLinkPatrimoineMatches,
  collectPatrimoineMatches,
  fetchPatrimoineMatchCounts,
  fetchPatrimoineMatches,
  searchPatrimoineTargets,
  updatePatrimoineMatch,
  type PatrimoineMatchItem,
} from "../lib/api";

const SOURCE_LABEL: Record<string, string> = {
  ENEDIS_PRM: "PRM ENEDIS",
  GRDF_PCE: "PCE GRDF",
};

const STATUS_LABEL: Record<string, string> = {
  a_traiter: "À traiter",
  lie: "Lié",
  a_creer: "À créer",
  ignore: "Ignoré",
};

const STATUS_ORDER = ["a_traiter", "lie", "a_creer", "ignore"] as const;

function scoreColor(score: number | null): string {
  if (score === null) return "#64748b";
  if (score >= 90) return "#0f6e56";
  if (score >= 60) return "#854f0b";
  return "#a32d2d";
}

export default function PatrimoineMatchPage() {
  const { token } = useAuth();
  const qc = useQueryClient();
  const [source, setSource] = useState<string>("");
  const [status, setStatus] = useState<string>("a_traiter");
  const [pickerForId, setPickerForId] = useState<number | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  const countsQuery = useQuery({
    queryKey: ["patrimoine-match-counts"],
    queryFn: () => fetchPatrimoineMatchCounts(token!),
    enabled: !!token,
  });

  const listQuery = useQuery({
    queryKey: ["patrimoine-matches", source, status],
    queryFn: () => fetchPatrimoineMatches(token!, { source: source || undefined, status: status || undefined }),
    enabled: !!token,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["patrimoine-matches"] });
    qc.invalidateQueries({ queryKey: ["patrimoine-match-counts"] });
  };

  const collectMut = useMutation({
    mutationFn: () => collectPatrimoineMatches(token!),
    onSuccess: (res) => {
      setFlash(`Collecte : ${res.prm ?? 0} PRM, ${res.pce ?? 0} PCE (${res.created ?? 0} nouveaux, ${res.linked_detected ?? 0} déjà liés).`);
      invalidate();
    },
    onError: (e) => setFlash(`Erreur collecte : ${(e as Error).message}`),
  });

  const bulkMut = useMutation({
    mutationFn: () => bulkLinkPatrimoineMatches(token!, 90),
    onSuccess: (res) => {
      setFlash(`${res.linked} rapprochement(s) évident(s) lié(s) automatiquement (score ≥ 90).`);
      invalidate();
    },
    onError: (e) => setFlash(`Erreur : ${(e as Error).message}`),
  });

  const updateMut = useMutation({
    mutationFn: (vars: { id: number; status: string; resolved_target_type?: string | null; resolved_target_id?: number | null }) =>
      updatePatrimoineMatch(token!, vars.id, {
        status: vars.status,
        resolved_target_type: vars.resolved_target_type,
        resolved_target_id: vars.resolved_target_id,
      }),
    onSuccess: () => {
      setPickerForId(null);
      invalidate();
    },
    onError: (e) => setFlash(`Erreur : ${(e as Error).message}`),
  });

  const counts = countsQuery.data ?? {};
  const items = listQuery.data ?? [];

  return (
    <section style={{ maxWidth: 980 }}>
      <p style={{ fontSize: 12, letterSpacing: ".05em", textTransform: "uppercase", color: "#94a3b8", margin: 0 }}>
        Patrimoine
      </p>
      <h2 style={{ margin: "4px 0 16px" }}>Rapprochements — compteurs &amp; sites externes</h2>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 16 }}>
        {STATUS_ORDER.map((key) => (
          <div key={key} style={card}>
            <div style={{ fontSize: 13, color: "#64748b" }}>{STATUS_LABEL[key]}</div>
            <div style={{ fontSize: 24, fontWeight: 500 }}>{counts[key] ?? 0}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 12 }}>
        <select value={source} onChange={(e) => setSource(e.target.value)} style={select}>
          <option value="">Toutes sources</option>
          <option value="ENEDIS_PRM">PRM ENEDIS</option>
          <option value="GRDF_PCE">PCE GRDF</option>
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={select}>
          <option value="">Tous statuts</option>
          {STATUS_ORDER.map((key) => (
            <option key={key} value={key}>{STATUS_LABEL[key]}</option>
          ))}
        </select>
        <button onClick={() => collectMut.mutate()} disabled={collectMut.isPending} style={btnPrimary}>
          {collectMut.isPending ? "Collecte…" : "Collecter les compteurs"}
        </button>
        <button onClick={() => bulkMut.mutate()} disabled={bulkMut.isPending} style={btnSecondary}>
          {bulkMut.isPending ? "…" : "Lier les évidences (score ≥ 90)"}
        </button>
      </div>

      {flash && <div style={{ fontSize: 13, color: "#0369a1", marginBottom: 12 }}>{flash}</div>}

      {listQuery.isLoading ? (
        <p style={{ color: "#64748b" }}>Chargement…</p>
      ) : items.length === 0 ? (
        <p style={{ color: "#64748b" }}>
          Aucun objet pour ce filtre. Lance « Collecter les compteurs » pour alimenter la file depuis les factures et les PCE.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {items.map((item) => (
            <MatchRow
              key={item.id}
              item={item}
              picking={pickerForId === item.id}
              onPick={() => setPickerForId(pickerForId === item.id ? null : item.id)}
              onLinkCandidate={() =>
                updateMut.mutate({
                  id: item.id,
                  status: "lie",
                  resolved_target_type: item.candidate_target_type,
                  resolved_target_id: item.candidate_target_id,
                })
              }
              onLinkTarget={(targetType, targetId) =>
                updateMut.mutate({ id: item.id, status: "lie", resolved_target_type: targetType, resolved_target_id: targetId })
              }
              onSetStatus={(s) => updateMut.mutate({ id: item.id, status: s })}
            />
          ))}
        </div>
      )}

      <p style={{ fontSize: 12, color: "#94a3b8", marginTop: 16 }}>
        Règle : aucun objet n'est jamais supprimé. « Lier » écrit le rattachement réel (compteur ↔ bâtiment). Les ignorés
        restent listés et rétablissables.
      </p>
    </section>
  );
}

function MatchRow({
  item,
  picking,
  onPick,
  onLinkCandidate,
  onLinkTarget,
  onSetStatus,
}: {
  item: PatrimoineMatchItem;
  picking: boolean;
  onPick: () => void;
  onLinkCandidate: () => void;
  onLinkTarget: (targetType: string, targetId: number) => void;
  onSetStatus: (status: string) => void;
}) {
  const isLinked = item.status === "lie";
  const isIgnored = item.status === "ignore";
  return (
    <div style={{ border: "0.5px solid #e2e8f0", borderRadius: 10, padding: "10px 12px", opacity: isIgnored ? 0.6 : 1 }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <span style={sourceBadge}>{SOURCE_LABEL[item.source] ?? item.source}</span>
        <div style={{ flex: 1, minWidth: 220 }}>
          <div style={{ fontSize: 13 }}>
            <code>{item.external_id}</code>{" "}
            <span style={{ color: "#64748b" }}>{item.label || "(sans libellé)"}</span>
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>
            {isLinked ? (
              <span style={{ color: "#0f6e56" }}>lié → {item.resolved_target_type} #{item.resolved_target_id}</span>
            ) : item.candidate_target_id ? (
              <>
                candidat : <strong style={{ color: "#1e293b" }}>{item.candidate_label}</strong>{" "}
                <span style={{ color: scoreColor(item.candidate_score) }}>
                  · score {Math.round(item.candidate_score ?? 0)} ({item.candidate_reason})
                </span>
              </>
            ) : (
              <span style={{ color: "#a32d2d" }}>aucun candidat fiable</span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {!isLinked && item.candidate_target_id && (
            <button style={btnPrimarySm} onClick={onLinkCandidate}>Lier</button>
          )}
          {!isLinked && <button style={btnSm} onClick={onPick}>{picking ? "Fermer" : "Choisir…"}</button>}
          {!isIgnored && !isLinked && <button style={btnSm} onClick={() => onSetStatus("a_creer")}>À créer</button>}
          {!isIgnored ? (
            <button style={btnSm} onClick={() => onSetStatus("ignore")}>Ignorer</button>
          ) : (
            <button style={btnSm} onClick={() => onSetStatus("a_traiter")}>Rétablir</button>
          )}
          {isLinked && <button style={btnSm} onClick={() => onSetStatus("a_traiter")}>Délier</button>}
        </div>
      </div>
      {picking && <TargetPicker onSelect={(t, id) => onLinkTarget(t, id)} />}
    </div>
  );
}

function TargetPicker({ onSelect }: { onSelect: (targetType: string, targetId: number) => void }) {
  const { token } = useAuth();
  const [query, setQuery] = useState("");
  const targetsQuery = useQuery({
    queryKey: ["patrimoine-targets", query],
    queryFn: () => searchPatrimoineTargets(token!, query),
    enabled: !!token && query.trim().length >= 2,
  });
  const results = targetsQuery.data ?? [];
  return (
    <div style={{ marginTop: 10, borderTop: "0.5px solid #f1f5f9", paddingTop: 10 }}>
      <input
        autoFocus
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Rechercher un bâtiment ou un site…"
        style={{ width: "100%", border: "1px solid #cbd5e1", borderRadius: 6, padding: "6px 10px", fontSize: 13 }}
      />
      {query.trim().length >= 2 && (
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 4, maxHeight: 220, overflow: "auto" }}>
          {results.length === 0 ? (
            <span style={{ fontSize: 12, color: "#94a3b8" }}>{targetsQuery.isLoading ? "Recherche…" : "Aucun résultat."}</span>
          ) : (
            results.map((r) => (
              <button
                key={`${r.target_type}-${r.target_id}`}
                style={{ ...btnSm, justifyContent: "space-between", display: "flex", width: "100%", textAlign: "left" }}
                onClick={() => onSelect(r.target_type, r.target_id)}
              >
                <span>{r.label}</span>
                <span style={{ fontSize: 11, color: "#94a3b8" }}>{r.target_type === "building" ? "Bâtiment" : "Site"}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

const card: CSSProperties = { background: "#f8fafc", borderRadius: 8, padding: "12px 14px" };
const select: CSSProperties = { border: "1px solid #cbd5e1", borderRadius: 7, padding: "6px 10px", fontSize: 13 };
const sourceBadge: CSSProperties = { fontSize: 11, padding: "3px 8px", borderRadius: 10, background: "#e6f1fb", color: "#0c447c", whiteSpace: "nowrap" };
const btnPrimary: CSSProperties = { padding: "7px 14px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 7, fontSize: 13, cursor: "pointer" };
const btnSecondary: CSSProperties = { padding: "7px 14px", background: "transparent", color: "#475569", border: "1px solid #cbd5e1", borderRadius: 7, fontSize: 13, cursor: "pointer" };
const btnPrimarySm: CSSProperties = { padding: "5px 10px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, fontSize: 12, cursor: "pointer" };
const btnSm: CSSProperties = { padding: "5px 10px", background: "transparent", color: "#475569", border: "1px solid #cbd5e1", borderRadius: 6, fontSize: 12, cursor: "pointer" };
