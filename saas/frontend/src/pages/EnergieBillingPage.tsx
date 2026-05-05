import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";

const apiBaseUrl = (import.meta as ImportMeta & { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? "/api";

// ── Types ─────────────────────────────────────────────────────────────────

type SupplierGroup = {
  supplier: string;
  prm_count: number;
  prm_ids: string[];
  tariff_codes: string[];
  tariff_prm_counts: Record<string, number>;
  config_id: number | null;
  lot: string | null;
  has_hphc: boolean;
  representative_prm_id: string | null;
  is_configured: boolean;
};

type BillingConfigOut = {
  id: number;
  city_id: number;
  supplier: string;
  tariff_code: string | null;
  lot: string | null;
  has_hphc: boolean;
  representative_prm_id: string | null;
  created_at: string;
  updated_at: string;
};

type BpuLine = {
  id: number;
  config_id: number;
  year: number | null;
  tariff_code: string;
  poste: string;
  pu_fourniture: number | null;
  pu_capacite: number | null;
  pu_cee: number | null;
  pu_go: number | null;
  pu_total: number | null;
  observation: string | null;
};

type BpuLineIn = {
  year: number | null;
  tariff_code: string;
  poste: string;
  pu_fourniture: number | null;
  pu_capacite: number | null;
  pu_cee: number | null;
  pu_go: number | null;
  pu_total: number | null;
};

type ComposanteInputs = { fourniture: string; capacite: string; cee: string; go: string };

// ── Constants ─────────────────────────────────────────────────────────────

const LOT_OPTIONS = [
  { value: "lot1", label: "Lot 1 — Électricité Bâtiments" },
  { value: "lot2", label: "Lot 2 — Éclairage Public" },
  { value: "lot7", label: "Lot 7 — Gaz" },
  { value: "autre", label: "Autre" },
];

const LOT_LABEL: Record<string, string> = {
  lot1: "Lot 1 — Bâtiments",
  lot2: "Lot 2 — Éclairage Public",
  lot7: "Lot 7 — Gaz",
  autre: "Autre",
};

// Ordre d'affichage des postes dans chaque section tarifaire
const POSTES_BY_TARIFF: Record<string, string[]> = {
  CU:   ["base"],
  LU:   ["base"],
  CU4:  ["hph", "hch", "hpe", "hce"],
  MU4:  ["hph", "hch", "hpe", "hce"],
  MUDT: ["hp", "hc"],
  C4:   ["hph", "hch", "hpe", "hce"],
  C2:   ["pointe", "hph", "hch", "hpe", "hce"],
};

const POSTE_LABELS: Record<string, string> = {
  base:   "Base",
  hph:    "HPH — Heures Pleines Saison Haute",
  hch:    "HCH — Heures Creuses Saison Haute",
  hpe:    "HPE — Heures Pleines Saison Basse",
  hce:    "HCE — Heures Creuses Saison Basse",
  hp:     "HP — Heures Pleines",
  hc:     "HC — Heures Creuses",
  pointe: "POINTE — Heure de Pointe",
};

const TARIFF_LABELS: Record<string, string> = {
  CU:   "SDT CU — BT≤36kVA Courte Utilisation (base)",
  LU:   "SDT LU — BT≤36kVA Longue Utilisation (base)",
  CU4:  "CU4 — BT≤36kVA Courte Utilisation 4 postes",
  MU4:  "MU4 — BT≤36kVA Moyenne Utilisation 4 postes",
  MUDT: "MUDT — BT>36kVA Moyenne Utilisation",
  C4:   "C4 — BT>36kVA Courte/Longue Utilisation",
  C2:   "C2 — HTA Courte/Longue Utilisation",
};

// ── API helpers ───────────────────────────────────────────────────────────

function buildHeaders(token: string) {
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

async function apiGet<T>(token: string, path: string): Promise<T> {
  const r = await fetch(`${apiBaseUrl}${path}`, { headers: buildHeaders(token) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function apiPut<T>(token: string, path: string, body: unknown): Promise<T> {
  const r = await fetch(`${apiBaseUrl}${path}`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// ── BPU Section ───────────────────────────────────────────────────────────

function BpuTariffSection({
  tariffCode,
  prmCount,
  bpuInputs,
  onChange,
}: {
  tariffCode: string;
  prmCount: number;
  bpuInputs: Record<string, Record<string, ComposanteInputs>>;
  onChange: (tc: string, poste: string, field: keyof ComposanteInputs, value: string) => void;
}) {
  const postes = POSTES_BY_TARIFF[tariffCode] ?? ["base"];

  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <span className="badge badge-gray" style={{ fontFamily: "monospace", fontSize: 13, letterSpacing: "0.03em" }}>
          {tariffCode}
        </span>
        <span style={{ fontWeight: 600, fontSize: 13, color: "#1e293b" }}>
          {TARIFF_LABELS[tariffCode] ?? tariffCode}
        </span>
        <span style={{ fontSize: 12, color: "#94a3b8" }}>
          — {prmCount} PRM{prmCount > 1 ? "s" : ""}
        </span>
      </div>
      <table className="data-table" style={{ tableLayout: "fixed" }}>
        <colgroup>
          <col style={{ width: "28%" }} />
          <col style={{ width: "15%" }} />
          <col style={{ width: "15%" }} />
          <col style={{ width: "15%" }} />
          <col style={{ width: "12%" }} />
          <col style={{ width: "15%" }} />
        </colgroup>
        <thead>
          <tr>
            <th>Poste</th>
            <th>Fourniture (€/MWh)</th>
            <th>Capacité (€/MWh)</th>
            <th>CEE (€/MWh)</th>
            <th>GO (€/MWh)</th>
            <th>Total calculé</th>
          </tr>
        </thead>
        <tbody>
          {postes.map((poste) => {
            const vals = bpuInputs[tariffCode]?.[poste] ?? { fourniture: "", capacite: "", cee: "", go: "" };
            const nums = [vals.fourniture, vals.capacite, vals.cee, vals.go].map((v) => parseFloat(v));
            const hasAny = nums.some((n) => !isNaN(n));
            const total = nums.reduce((acc, n) => acc + (isNaN(n) ? 0 : n), 0);

            return (
              <tr key={poste}>
                <td style={{ fontSize: 13, whiteSpace: "nowrap" }}>{POSTE_LABELS[poste] ?? poste}</td>
                {(["fourniture", "capacite", "cee", "go"] as const).map((field) => (
                  <td key={field}>
                    <input
                      type="number"
                      step="any"
                      className="form-input"
                      style={{ width: "100%", padding: "3px 6px", fontSize: 13 }}
                      value={vals[field]}
                      onChange={(e) => onChange(tariffCode, poste, field, e.target.value)}
                      placeholder="—"
                    />
                  </td>
                ))}
                <td style={{ fontWeight: 600, fontSize: 13, color: hasAny ? "#1e40af" : "#cbd5e1" }}>
                  {hasAny ? total.toFixed(2) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Wizard ────────────────────────────────────────────────────────────────

function BillingWizard({ group, onClose }: { group: SupplierGroup; onClose: () => void }) {
  const { token } = useAuth();
  const qc = useQueryClient();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [configId, setConfigId] = useState<number | null>(group.config_id);

  // ── Step 1 ───────────────────────────────────────────────────────────
  const [lot, setLot] = useState(group.lot ?? "");
  const [selectedPrm, setSelectedPrm] = useState(group.representative_prm_id ?? "");
  const [hasHphc, setHasHphc] = useState(group.has_hphc);

  const upsertMut = useMutation({
    mutationFn: () =>
      apiPut<BillingConfigOut>(token!, `/billing/configs/supplier/${encodeURIComponent(group.supplier)}`, {
        lot: lot || null,
        has_hphc: hasHphc,
        representative_prm_id: selectedPrm || null,
      }),
    onSuccess: (data) => {
      setConfigId(data.id);
      qc.invalidateQueries({ queryKey: ["billing-supplier-groups"] });
      setStep(2);
    },
  });

  // ── Step 2 ───────────────────────────────────────────────────────────
  const [bpuInputs, setBpuInputs] = useState<Record<string, Record<string, ComposanteInputs>>>({});
  const [bpuInitDone, setBpuInitDone] = useState(false);

  const bpuLinesQuery = useQuery({
    queryKey: ["billing-bpu-lines", configId],
    queryFn: () => apiGet<BpuLine[]>(token!, `/billing/configs/${configId}/bpu-lines`),
    enabled: !!token && !!configId,
  });

  // Pré-remplir les inputs depuis les données existantes (une seule fois)
  useEffect(() => {
    if (!bpuInitDone && bpuLinesQuery.data && bpuLinesQuery.data.length > 0) {
      const inputs: Record<string, Record<string, ComposanteInputs>> = {};
      for (const line of bpuLinesQuery.data.filter((l) => l.year === null)) {
        if (!inputs[line.tariff_code]) inputs[line.tariff_code] = {};
        inputs[line.tariff_code][line.poste] = {
          fourniture: line.pu_fourniture != null ? String(line.pu_fourniture) : "",
          capacite: line.pu_capacite != null ? String(line.pu_capacite) : "",
          cee: line.pu_cee != null ? String(line.pu_cee) : "",
          go: line.pu_go != null ? String(line.pu_go) : "",
        };
      }
      setBpuInputs(inputs);
      setBpuInitDone(true);
    }
  }, [bpuLinesQuery.data, bpuInitDone]);

  const handleBpuChange = (tc: string, poste: string, field: keyof ComposanteInputs, value: string) => {
    setBpuInputs((prev) => ({
      ...prev,
      [tc]: {
        ...(prev[tc] ?? {}),
        [poste]: { ...(prev[tc]?.[poste] ?? { fourniture: "", capacite: "", cee: "", go: "" }), [field]: value },
      },
    }));
  };

  const setBpuLinesMut = useMutation({
    mutationFn: () => {
      const historical = (bpuLinesQuery.data ?? [])
        .filter((l) => l.year !== null)
        .map((l) => ({
          year: l.year,
          tariff_code: l.tariff_code,
          poste: l.poste,
          pu_fourniture: l.pu_fourniture,
          pu_capacite: l.pu_capacite,
          pu_cee: l.pu_cee,
          pu_go: l.pu_go,
          pu_total: l.pu_total,
        }));

      const current: BpuLineIn[] = [];
      for (const [tc, postes] of Object.entries(bpuInputs)) {
        for (const [poste, vals] of Object.entries(postes)) {
          const f = parseFloat(vals.fourniture);
          const c = parseFloat(vals.capacite);
          const cee = parseFloat(vals.cee);
          const go = parseFloat(vals.go);
          const nums = [f, c, cee, go];
          if (nums.some((n) => !isNaN(n))) {
            const total = nums.reduce((acc, n) => acc + (isNaN(n) ? 0 : n), 0);
            current.push({
              year: null,
              tariff_code: tc,
              poste,
              pu_fourniture: isNaN(f) ? null : f,
              pu_capacite: isNaN(c) ? null : c,
              pu_cee: isNaN(cee) ? null : cee,
              pu_go: isNaN(go) ? null : go,
              pu_total: total,
            });
          }
        }
      }
      return apiPut<BpuLine[]>(token!, `/billing/configs/${configId}/bpu-lines`, [...current, ...historical]);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["billing-bpu-lines", configId] });
      setStep(3);
    },
  });

  // ── Step 3 — Récapitulatif ────────────────────────────────────────────
  const savedLines = (bpuLinesQuery.data ?? []).filter((l) => l.year === null);
  const linesByTariff: Record<string, BpuLine[]> = {};
  for (const line of savedLines) {
    if (!linesByTariff[line.tariff_code]) linesByTariff[line.tariff_code] = [];
    linesByTariff[line.tariff_code].push(line);
  }

  return (
    <div className="wizard-overlay" onClick={onClose}>
      <div className="wizard-panel" style={{ maxWidth: 820 }} onClick={(e) => e.stopPropagation()}>
        <div className="wizard-header">
          <div>
            <h2 className="wizard-title">{group.supplier}</h2>
            <p className="wizard-subtitle">
              {group.prm_count} PRM(s) · Tarifs : {group.tariff_codes.join(", ")}
              {group.lot && ` · ${LOT_LABEL[group.lot] ?? group.lot}`}
            </p>
          </div>
          <button className="wizard-close" onClick={onClose}>✕</button>
        </div>

        <div className="wizard-steps">
          {([1, 2, 3] as const).map((s) => (
            <button
              key={s}
              className={`wizard-step-btn ${step === s ? "active" : ""} ${s > 1 && !configId ? "disabled" : ""}`}
              onClick={() => (s === 1 || configId) && setStep(s)}
            >
              {s === 1 ? "Lot & référent" : s === 2 ? "BPU par tarif" : "Récapitulatif"}
            </button>
          ))}
        </div>

        <div className="wizard-body">

          {/* ── Step 1 ── */}
          {step === 1 && (
            <div>
              <p className="field-label" style={{ marginBottom: 8 }}>Lot contractuel</p>
              <select className="form-input" value={lot} onChange={(e) => setLot(e.target.value)}>
                <option value="">-- Sélectionner un lot --</option>
                {LOT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>

              <p className="field-label" style={{ marginTop: 20, marginBottom: 8 }}>PRM représentatif</p>
              <p style={{ fontSize: 12, color: "#64748b", marginBottom: 8 }}>
                Utilisé pour extraire les données de référence de ce fournisseur.
              </p>
              <select className="form-input" value={selectedPrm} onChange={(e) => setSelectedPrm(e.target.value)}>
                <option value="">-- Choisir un PRM --</option>
                {group.prm_ids.map((id) => (
                  <option key={id} value={id}>{id}</option>
                ))}
              </select>

              <div className="toggle-row" style={{ marginTop: 20 }}>
                <label className="toggle-label">
                  <input type="checkbox" checked={hasHphc} onChange={(e) => setHasHphc(e.target.checked)} />
                  <span>Contrat avec postes horosaisonniers</span>
                </label>
              </div>

              <div style={{ marginTop: 24, display: "flex", gap: 8 }}>
                <button
                  className="btn-primary"
                  disabled={!lot || !selectedPrm || upsertMut.isPending}
                  onClick={() => upsertMut.mutate()}
                >
                  {upsertMut.isPending ? "Enregistrement…" : "Enregistrer et continuer →"}
                </button>
                {configId && (
                  <button className="secondary-button" onClick={() => setStep(2)}>Aller au BPU</button>
                )}
              </div>
              {upsertMut.isError && (
                <p style={{ color: "#dc2626", fontSize: 12, marginTop: 8 }}>
                  Erreur : {String(upsertMut.error)}
                </p>
              )}
            </div>
          )}

          {/* ── Step 2 — BPU par tarif ── */}
          {step === 2 && configId && (
            <div>
              <p className="field-label" style={{ marginBottom: 4 }}>Prix unitaires BPU par tarif TURPE</p>
              <p style={{ fontSize: 12, color: "#64748b", marginBottom: 20 }}>
                Saisissez les prix du BPU pour chaque tarif détecté sur les PRMs de{" "}
                <strong>{group.supplier}</strong>. Le total est calculé automatiquement.
                Les prix sont en €/MWh HTT.
              </p>

              {bpuLinesQuery.isLoading && <p style={{ color: "#64748b", fontSize: 13 }}>Chargement…</p>}

              {group.tariff_codes.map((tc) => (
                <BpuTariffSection
                  key={tc}
                  tariffCode={tc}
                  prmCount={group.tariff_prm_counts[tc] ?? 0}
                  bpuInputs={bpuInputs}
                  onChange={handleBpuChange}
                />
              ))}

              <div style={{ marginTop: 20, display: "flex", gap: 8 }}>
                <button
                  className="btn-primary"
                  disabled={setBpuLinesMut.isPending}
                  onClick={() => setBpuLinesMut.mutate()}
                >
                  {setBpuLinesMut.isPending ? "Enregistrement…" : "Enregistrer et continuer →"}
                </button>
                <button className="secondary-button" onClick={() => setStep(3)}>
                  Voir le récapitulatif
                </button>
              </div>
              {setBpuLinesMut.isError && (
                <p style={{ color: "#dc2626", fontSize: 12, marginTop: 8 }}>
                  Erreur : {String(setBpuLinesMut.error)}
                </p>
              )}
            </div>
          )}

          {/* ── Step 3 — Récapitulatif ── */}
          {step === 3 && configId && (
            <div>
              <p className="field-label" style={{ marginBottom: 12 }}>BPU enregistré — tarifs et prix actuels</p>

              {savedLines.length === 0 && (
                <p style={{ color: "#64748b", fontSize: 13, marginBottom: 16 }}>
                  Aucune ligne BPU enregistrée. Revenez à l'étape 2 pour saisir les prix.
                </p>
              )}

              {Object.entries(linesByTariff).map(([tc, lines]) => (
                <div key={tc} style={{ marginBottom: 20 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                    <span className="badge badge-gray" style={{ fontFamily: "monospace", fontSize: 12 }}>{tc}</span>
                    <span style={{ fontSize: 13, color: "#475569" }}>{TARIFF_LABELS[tc] ?? tc}</span>
                  </div>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Poste</th>
                        <th>Fourniture</th>
                        <th>Capacité</th>
                        <th>CEE</th>
                        <th>GO</th>
                        <th>Total (€/MWh)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lines
                        .sort((a, b) => {
                          const order = POSTES_BY_TARIFF[tc] ?? [];
                          return order.indexOf(a.poste) - order.indexOf(b.poste);
                        })
                        .map((line) => (
                          <tr key={line.poste}>
                            <td style={{ fontSize: 13 }}>{POSTE_LABELS[line.poste] ?? line.poste}</td>
                            <td>{line.pu_fourniture?.toFixed(2) ?? "—"}</td>
                            <td>{line.pu_capacite?.toFixed(2) ?? "—"}</td>
                            <td>{line.pu_cee?.toFixed(2) ?? "—"}</td>
                            <td>{line.pu_go?.toFixed(2) ?? "—"}</td>
                            <td style={{ fontWeight: 600, color: "#1e40af" }}>
                              {line.pu_total?.toFixed(2) ?? "—"}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              ))}

              <div style={{ marginTop: 20, display: "flex", gap: 8 }}>
                <button className="secondary-button" onClick={() => setStep(2)}>
                  ← Modifier le BPU
                </button>
                <button className="btn-primary" onClick={onClose}>
                  Fermer
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────

export function EnergieBillingPage() {
  const { token } = useAuth();
  const qc = useQueryClient();
  const [selectedGroup, setSelectedGroup] = useState<SupplierGroup | null>(null);

  const groupsQuery = useQuery({
    queryKey: ["billing-supplier-groups"],
    queryFn: () => apiGet<SupplierGroup[]>(token!, "/billing/supplier-groups"),
    enabled: !!token,
  });

  const groups = groupsQuery.data ?? [];
  const configured = groups.filter((g) => g.is_configured).length;

  const lotMut = useMutation({
    mutationFn: ({ supplier, lot }: { supplier: string; lot: string }) =>
      apiPut(token!, `/billing/configs/supplier/${encodeURIComponent(supplier)}`, { lot }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["billing-supplier-groups"] }),
  });

  const handleClose = () => {
    setSelectedGroup(null);
    groupsQuery.refetch();
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Facturation ENEDIS</h2>
        <p className="page-subtitle">
          Configurez les prix BPU par fournisseur et par tarif TURPE pour chaque PRM.
        </p>
      </div>

      {groupsQuery.isLoading && <p className="loading-text">Chargement des fournisseurs…</p>}
      {groupsQuery.isError && <p className="error-text">Erreur lors du chargement.</p>}

      {!groupsQuery.isLoading && (
        <>
          <div className="kpi-row">
            <div className="kpi-card">
              <span className="kpi-value">{groups.length}</span>
              <span className="kpi-label">Fournisseurs détectés</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-value">{configured}</span>
              <span className="kpi-label">Configurés</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-value">{groups.reduce((s, g) => s + g.prm_count, 0)}</span>
              <span className="kpi-label">PRMs couverts</span>
            </div>
          </div>

          {groups.length === 0 ? (
            <p style={{ color: "#64748b" }}>
              Aucun contrat importé. Lancez une synchronisation depuis la page Énergie.
            </p>
          ) : (
            <div className="billing-supplier-table">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Fournisseur</th>
                    <th>Lot contractuel</th>
                    <th>PRMs</th>
                    <th>Tarifs détectés</th>
                    <th>Statut</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {groups.map((g) => (
                    <tr key={g.supplier}>
                      <td><strong>{g.supplier}</strong></td>
                      <td>
                        <select
                          className="form-input"
                          style={{ padding: "4px 8px", width: "auto", minWidth: 200 }}
                          value={g.lot ?? ""}
                          onChange={(e) => lotMut.mutate({ supplier: g.supplier, lot: e.target.value })}
                        >
                          <option value="">-- Choisir un lot --</option>
                          {LOT_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                          ))}
                        </select>
                      </td>
                      <td>{g.prm_count}</td>
                      <td>
                        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                          {g.tariff_codes.map((tc) => (
                            <span key={tc} className="badge badge-gray" style={{ fontSize: 11, fontFamily: "monospace" }}>
                              {tc}
                              {g.tariff_prm_counts[tc] ? (
                                <span style={{ marginLeft: 4, opacity: 0.7 }}>×{g.tariff_prm_counts[tc]}</span>
                              ) : null}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${g.is_configured ? "badge-green" : "badge-gray"}`}>
                          {g.is_configured ? "Configuré" : "Non configuré"}
                        </span>
                      </td>
                      <td>
                        <button
                          className="secondary-button"
                          style={{ padding: "4px 12px" }}
                          onClick={() => setSelectedGroup(g)}
                        >
                          {g.is_configured ? "Modifier" : "Configurer BPU"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {groups.length > 0 && configured < groups.length && (
            <div className="billing-help-box">
              <strong>Comment configurer ?</strong>
              <ol style={{ margin: "8px 0 0", paddingLeft: 20, fontSize: 13, color: "#94a3b8" }}>
                <li>Attribuez un lot à chaque fournisseur via le menu déroulant.</li>
                <li>Cliquez sur <em>Configurer BPU</em> pour saisir les prix par tarif TURPE.</li>
                <li>Chaque tarif (CU, CU4, LU…) affiche les postes horosaisonniers applicables.</li>
              </ol>
            </div>
          )}
        </>
      )}

      {selectedGroup && (
        <BillingWizard group={selectedGroup} onClose={handleClose} />
      )}
    </div>
  );
}
