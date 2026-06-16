import { useRef, useState, type CSSProperties } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../providers/AuthProvider";
import {
  bootstrapEnergySiteMappings,
  fetchEnergyNatureRules,
  fetchEnergySiteMappings,
  importEnergyCodification,
  updateEnergyNatureRule,
  updateEnergySiteMapping,
  type EnergyAccountingNatureRule,
  type EnergyAccountingSiteMapping,
} from "../lib/api";

/**
 * Matrice comptable ENGIE — codification site (PRM) + poste → nature, pour la
 * fiche de liaison finances. Calquée sur la matrice DALKIA. Affichée en modale
 * depuis /energie/factures.
 */
const SITE_COLS: { key: keyof EnergyAccountingSiteMapping; label: string }[] = [
  { key: "service_code", label: "Service" },
  { key: "service_label", label: "Libellé service" },
  { key: "function_code", label: "Fonction" },
  { key: "antenna_code", label: "Antenne" },
  { key: "operation_code", label: "Opération" },
  { key: "manager", label: "Gestionnaire" },
];

export default function EnergieAccountingMatrix({
  onClose,
  variant = "modal",
}: {
  onClose?: () => void;
  variant?: "modal" | "inline";
}) {
  const { token } = useAuth();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [tab, setTab] = useState<"sites" | "natures">("sites");

  const sitesQuery = useQuery({
    queryKey: ["energy-site-mappings"],
    queryFn: () => fetchEnergySiteMappings(token ?? ""),
    enabled: !!token,
  });
  const naturesQuery = useQuery({
    queryKey: ["energy-nature-rules"],
    queryFn: () => fetchEnergyNatureRules(token ?? ""),
    enabled: !!token,
  });

  const importMut = useMutation({
    mutationFn: (file: File) => importEnergyCodification(token ?? "", file),
    onSuccess: (res) => {
      setFlash(
        `Import : ${res.site_mappings_created + res.site_mappings_updated} sites, ` +
          `${res.nature_rules_created + res.nature_rules_updated} postes` +
          (res.errors.length ? ` · ${res.errors.join(" ; ")}` : ""),
      );
      qc.invalidateQueries({ queryKey: ["energy-site-mappings"] });
      qc.invalidateQueries({ queryKey: ["energy-nature-rules"] });
    },
    onError: (e) => setFlash(`Erreur import : ${(e as Error).message}`),
  });

  const bootstrapMut = useMutation({
    mutationFn: () => bootstrapEnergySiteMappings(token ?? ""),
    onSuccess: (res) => {
      setFlash(`Pré-remplissage : ${res.created} PRM ajoutés (${res.existing} déjà présents).`);
      qc.invalidateQueries({ queryKey: ["energy-site-mappings"] });
    },
  });

  const siteCell = (m: EnergyAccountingSiteMapping, key: keyof EnergyAccountingSiteMapping) => (
    <input
      defaultValue={(m[key] as string | null) ?? ""}
      onBlur={(e) => {
        const v = e.target.value.trim() || null;
        if (v !== (m[key] ?? null)) {
          updateEnergySiteMapping(token ?? "", m.id, { ...m, [key]: v }).then(() =>
            qc.invalidateQueries({ queryKey: ["energy-site-mappings"] }),
          );
        }
      }}
      style={inputStyle}
    />
  );

  const natureCell = (r: EnergyAccountingNatureRule, key: keyof EnergyAccountingNatureRule) => (
    <input
      defaultValue={(r[key] as string | null) ?? ""}
      onBlur={(e) => {
        const v = e.target.value.trim() || null;
        if (v !== (r[key] ?? null)) {
          updateEnergyNatureRule(token ?? "", r.id, { ...r, [key]: v }).then(() =>
            qc.invalidateQueries({ queryKey: ["energy-nature-rules"] }),
          );
        }
      }}
      style={inputStyle}
    />
  );

  const sites = sitesQuery.data ?? [];
  const natures = naturesQuery.data ?? [];

  const isInline = variant === "inline";

  return (
    <div style={isInline ? inlineOverlay : overlay} onClick={isInline ? undefined : onClose}>
      <div style={isInline ? inlinePanel : panel} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>
            {isInline ? "Matrice comptable — consolidation finances" : "Matrice comptable ENGIE"}
          </h2>
          {!isInline && (
            <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "#94a3b8" }}>✕</button>
          )}
        </div>
        <p style={{ fontSize: 12, color: "#64748b", margin: "0 0 12px" }}>
          Codification utilisée pour la fiche de liaison finances : PRM → codes analytiques
          (Service/Fonction/Antenne/Opération) et poste facturé → nature comptable. La colonne
          « Marché » rend la matrice transversale (ENGIE, EDF, et marchés à venir).
        </p>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <input ref={fileRef} type="file" accept=".xlsx" style={{ display: "none" }}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) importMut.mutate(f); e.target.value = ""; }} />
          <button onClick={() => fileRef.current?.click()} disabled={importMut.isPending} style={btnPrimary}>
            {importMut.isPending ? "Import…" : "Importer un xlsx de codification"}
          </button>
          <button onClick={() => bootstrapMut.mutate()} disabled={bootstrapMut.isPending} style={btnSecondary}>
            {bootstrapMut.isPending ? "…" : "Pré-remplir les PRM depuis les factures"}
          </button>
        </div>
        {flash && <div style={{ fontSize: 12, color: "#0369a1", marginBottom: 10 }}>{flash}</div>}

        <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
          <button onClick={() => setTab("sites")} style={tab === "sites" ? tabActive : tabInactive}>
            Sites / PRM ({sites.length})
          </button>
          <button onClick={() => setTab("natures")} style={tab === "natures" ? tabActive : tabInactive}>
            Postes → Nature ({natures.length})
          </button>
        </div>

        <div style={{ overflow: "auto", flex: 1, border: "1px solid #e2e8f0", borderRadius: 8 }}>
          {tab === "sites" ? (
            <table style={table}>
              <thead>
                <tr>
                  <th style={th}>PRM</th>
                  <th style={th}>Site</th>
                  {SITE_COLS.map((c) => <th key={c.key} style={th}>{c.label}</th>)}
                </tr>
              </thead>
              <tbody>
                {sites.map((m) => (
                  <tr key={m.id}>
                    <td style={tdMono}>{m.prm_id}</td>
                    <td style={td}>{m.site_name}</td>
                    {SITE_COLS.map((c) => <td key={c.key} style={tdEdit}>{siteCell(m, c.key)}</td>)}
                  </tr>
                ))}
                {sites.length === 0 && <tr><td colSpan={8} style={empty}>Aucun PRM. Importez un xlsx ou pré-remplissez depuis les factures.</td></tr>}
              </tbody>
            </table>
          ) : (
            <table style={table}>
              <thead>
                <tr>
                  <th style={th}>Poste facturé</th>
                  <th style={th}>Nature</th>
                  <th style={th}>Libellé nature</th>
                  <th style={th}>Marché</th>
                </tr>
              </thead>
              <tbody>
                {natures.map((r) => (
                  <tr key={r.id}>
                    <td style={tdMono}>{r.billed_item}</td>
                    <td style={tdEdit}>{natureCell(r, "accounting_nature")}</td>
                    <td style={tdEdit}>{natureCell(r, "accounting_label")}</td>
                    <td style={tdEdit}>{natureCell(r, "market")}</td>
                  </tr>
                ))}
                {natures.length === 0 && <tr><td colSpan={4} style={empty}>Aucune règle. Importez un xlsx de codification.</td></tr>}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

const overlay: CSSProperties = { position: "fixed", inset: 0, background: "rgba(15,23,42,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 24 };
const panel: CSSProperties = { background: "#fff", borderRadius: 12, padding: 20, width: "min(1100px, 96vw)", height: "min(80vh, 760px)", display: "flex", flexDirection: "column", boxShadow: "0 20px 60px rgba(0,0,0,0.3)" };
const inlineOverlay: CSSProperties = {};
const inlinePanel: CSSProperties = { background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 20, display: "flex", flexDirection: "column", maxHeight: 720 };
const inputStyle: CSSProperties = { width: "100%", border: "1px solid #e2e8f0", borderRadius: 4, padding: "3px 6px", fontSize: 12 };
const table: CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: 12 };
const th: CSSProperties = { position: "sticky", top: 0, background: "#f1f5f9", textAlign: "left", padding: "6px 8px", borderBottom: "1px solid #e2e8f0", fontWeight: 600, whiteSpace: "nowrap" };
const td: CSSProperties = { padding: "4px 8px", borderBottom: "1px solid #f1f5f9" };
const tdMono: CSSProperties = { ...td, fontFamily: "monospace", whiteSpace: "nowrap" };
const tdEdit: CSSProperties = { padding: "2px 4px", borderBottom: "1px solid #f1f5f9", minWidth: 90 };
const empty: CSSProperties = { padding: 20, textAlign: "center", color: "#94a3b8" };
const btnPrimary: CSSProperties = { padding: "6px 14px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 7, fontSize: 13, cursor: "pointer" };
const btnSecondary: CSSProperties = { padding: "6px 14px", background: "transparent", color: "#475569", border: "1px solid #cbd5e1", borderRadius: 7, fontSize: 13, cursor: "pointer" };
const tabActive: CSSProperties = { padding: "5px 12px", background: "#1e293b", color: "#fff", border: "none", borderRadius: 6, fontSize: 12, cursor: "pointer" };
const tabInactive: CSSProperties = { padding: "5px 12px", background: "#f1f5f9", color: "#475569", border: "none", borderRadius: 6, fontSize: 12, cursor: "pointer" };
