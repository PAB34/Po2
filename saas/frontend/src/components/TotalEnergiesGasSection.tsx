import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { useAuth } from "../providers/AuthProvider";
import {
  exportGasInvoices,
  fetchGasBpu,
  fetchGasInvoices,
  fetchGasPortfolio,
  importGasInvoices,
  recomputeGasControls,
  setGasInvoiceDecision,
  type GasInvoice,
  type GasInvoiceIssue,
} from "../lib/api";

const CONTROL_LABEL: Record<string, string> = {
  valid: "Valide",
  review: "À contrôler",
  invalid: "Invalide",
  not_checked: "Non contrôlée",
};

const DECISION_LABEL: Record<string, string> = {
  to_review: "À vérifier",
  approved: "Validée",
  rejected: "Refusée",
  dispute_sent: "Contestation",
};

function eur(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v);
}
function int(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return new Intl.NumberFormat("fr-FR").format(v);
}
function controlTone(status: string): "ok" | "warn" | "danger" | "neutral" {
  if (status === "valid") return "ok";
  if (status === "review") return "warn";
  if (status === "invalid") return "danger";
  return "neutral";
}
function issuesOf(inv: GasInvoice): GasInvoiceIssue[] {
  if (!inv.control_issues_json) return [];
  try {
    return JSON.parse(inv.control_issues_json) as GasInvoiceIssue[];
  } catch {
    return [];
  }
}

export default function TotalEnergiesGasSection() {
  const { token } = useAuth();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [controlFilter, setControlFilter] = useState<string>("");

  const portfolioQuery = useQuery({
    queryKey: ["gas-portfolio"],
    queryFn: () => fetchGasPortfolio(token!),
    enabled: !!token,
  });
  const invoicesQuery = useQuery({
    queryKey: ["gas-invoices", controlFilter],
    queryFn: () => fetchGasInvoices(token!, { control_status: controlFilter || undefined }),
    enabled: !!token,
  });
  const bpuQuery = useQuery({
    queryKey: ["gas-bpu"],
    queryFn: () => fetchGasBpu(token!),
    enabled: !!token,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["gas-portfolio"] });
    qc.invalidateQueries({ queryKey: ["gas-invoices"] });
  };

  const importMut = useMutation({
    mutationFn: (file: File) => importGasInvoices(token!, file, true),
    onSuccess: (res) => {
      setFlash(
        `Import : ${res.created ?? 0} créées, ${res.updated ?? 0} mises à jour, ${res.skipped ?? 0} ignorées · ` +
          `contrôle ${res.valid ?? 0} OK / ${res.review ?? 0} à voir / ${res.invalid ?? 0} KO.`,
      );
      invalidate();
    },
    onError: (e) => setFlash(`Erreur import : ${(e as Error).message}`),
  });

  const recomputeMut = useMutation({
    mutationFn: () => recomputeGasControls(token!),
    onSuccess: () => invalidate(),
  });

  const decisionMut = useMutation({
    mutationFn: (v: { id: number; status: string }) => setGasInvoiceDecision(token!, v.id, v.status),
    onSuccess: () => invalidate(),
  });

  const exportMut = useMutation({
    mutationFn: () => exportGasInvoices(token!),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "liaison_finance_gaz_totalenergies.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setFlash("Fiche de liaison finance exportée (transmission horodatée).");
      invalidate();
    },
    onError: (e) => setFlash(`Erreur export : ${(e as Error).message}`),
  });

  const pf = portfolioQuery.data;
  const invoices = invoicesQuery.data ?? [];

  return (
    <div className="fct-market-body">
      <div className="fct-etat">
        <div className="fct-etat-head">
          <strong>TotalEnergies — gaz bâtiments (marché Hérault Énergie)</strong>
          <span className="cockpit-badge cockpit-badge--ok">contrôle structure v1</span>
        </div>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "10px 0" }}>
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) importMut.mutate(f);
              e.target.value = "";
            }}
          />
          <button type="button" className="btn-primary" onClick={() => fileRef.current?.click()} disabled={importMut.isPending}>
            {importMut.isPending ? "Import…" : "Importer l'export TotalEnergies (.xlsx)"}
          </button>
          <button type="button" className="btn-secondary btn-compact" onClick={() => recomputeMut.mutate()} disabled={recomputeMut.isPending}>
            Recontrôler
          </button>
          <button type="button" className="btn-secondary btn-compact" onClick={() => exportMut.mutate()} disabled={exportMut.isPending}>
            {exportMut.isPending ? "Export…" : "Exporter fiche liaison (XLSX)"}
          </button>
          <Link to="/patrimoine/rapprochements" className="cockpit-queue-action">
            Rattacher les PCE aux bâtiments <span aria-hidden="true">↗</span>
          </Link>
        </div>

        {flash && <div style={{ fontSize: 13, color: "#0369a1", marginBottom: 10 }}>{flash}</div>}

        <div className="fct-overview-grid">
          <div className="fct-overview-card">
            <span>Factures</span>
            <strong>{int(pf?.count)}</strong>
            <small>{int(pf?.by_control?.valid ?? 0)} valides · {int(pf?.by_control?.invalid ?? 0)} invalides</small>
          </div>
          <div className="fct-overview-card">
            <span>Montant HT suivi</span>
            <strong>{eur(pf?.total_ht)}</strong>
            <small>{eur(pf?.total_ttc)} TTC</small>
          </div>
          <div className="fct-overview-card">
            <span>Consommation</span>
            <strong>{int(pf?.total_kwh)} kWh</strong>
            <small>{pf?.by_site?.length ?? 0} sites / PCE</small>
          </div>
        </div>

        {(() => {
          const ref = (bpuQuery.data ?? []).find((b) => b.annee === new Date().getFullYear()) ?? (bpuQuery.data ?? [])[0];
          if (!ref) return null;
          return (
            <p className="fct-etat-note">
              <strong>BPU gaz Lot 7 {ref.annee}</strong> (réf. contrôle prix) : fourniture ferme{" "}
              <strong>{ref.fourniture_ht_mwh} €/MWh</strong> · CEE {ref.cee_ht_mwh} · CEE précarité {ref.cee_precarite_ht_mwh} · CPB {ref.cpb_ht_mwh} · GO {ref.go_ht_mwh} (€ HT/MWh).
            </p>
          );
        })()}

        <p className="fct-etat-note">
          Contrôle : cohérence (prix×kWh, somme = HT, HT+TVA = TTC, conversion m³→kWh, TVA), <strong>prix fourniture vs BPU
          Lot 7</strong> (PCE à prix révisable PEG signalés) et <strong>cohérence de l'acheminement ATRD</strong> (taux €/MWh
          stable par tarif). À venir : barème GRDF absolu et CEE définitifs.
        </p>
      </div>

      {pf && pf.by_site.length > 0 && (
        <div className="fct-etat">
          <div className="fct-etat-head"><strong>Par site / PCE</strong></div>
          <table className="fct-etat-table">
            <thead>
              <tr><th>Site</th><th>PCE</th><th>Factures</th><th>HT</th><th>kWh</th><th>Bâtiment</th></tr>
            </thead>
            <tbody>
              {pf.by_site.map((s) => (
                <tr key={s.pce}>
                  <td>{s.site}</td>
                  <td className="fct-etat-muted">{s.pce}</td>
                  <td>{int(s.count)}</td>
                  <td>{eur(s.ht)}</td>
                  <td>{int(s.kwh)}</td>
                  <td>
                    {s.linked ? (
                      <span className="cockpit-badge cockpit-badge--ok">rattaché</span>
                    ) : (
                      <span className="cockpit-badge cockpit-badge--neutral">à rattacher</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="fct-etat">
        <div className="fct-etat-head">
          <strong>Factures</strong>
          <select value={controlFilter} onChange={(e) => setControlFilter(e.target.value)} className="form-input" style={{ width: "auto" }}>
            <option value="">Tous contrôles</option>
            <option value="valid">Valides</option>
            <option value="review">À contrôler</option>
            <option value="invalid">Invalides</option>
          </select>
        </div>
        {invoicesQuery.isLoading ? (
          <p className="fct-etat-note">Chargement…</p>
        ) : invoices.length === 0 ? (
          <p className="fct-etat-note">Aucune facture. Importe l'export TotalEnergies pour démarrer.</p>
        ) : (
          <table className="fct-etat-table">
            <thead>
              <tr><th>Facture</th><th>Site</th><th>Période</th><th>HT</th><th>TTC</th><th>Contrôle</th><th>Décision</th></tr>
            </thead>
            <tbody>
              {invoices.map((inv) => {
                const iss = issuesOf(inv);
                return (
                  <tr key={inv.id}>
                    <td>
                      {inv.num_facture}
                      {inv.type_detail === "AVOIR" && <span className="cockpit-badge cockpit-badge--neutral" style={{ marginLeft: 6 }}>avoir</span>}
                    </td>
                    <td>{inv.lib_regroupement || inv.nom_site || "—"}</td>
                    <td className="fct-etat-muted">{inv.debut_conso} → {inv.fin_conso}</td>
                    <td>{eur(inv.total_hors_tva)}</td>
                    <td>{eur(inv.total_ttc)}</td>
                    <td>
                      <span className={`cockpit-badge cockpit-badge--${controlTone(inv.control_status)}`} title={iss.map((i) => i.message).join(" · ")}>
                        {CONTROL_LABEL[inv.control_status] ?? inv.control_status}
                        {iss.length > 0 ? ` (${iss.length})` : ""}
                      </span>
                    </td>
                    <td>
                      <select
                        value={inv.decision_status}
                        onChange={(e) => decisionMut.mutate({ id: inv.id, status: e.target.value })}
                        className="form-input"
                        style={{ width: "auto" }}
                      >
                        {Object.entries(DECISION_LABEL).map(([k, v]) => (
                          <option key={k} value={k}>{v}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
