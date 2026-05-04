import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useAuth } from "../providers/AuthProvider";

const apiBaseUrl = (import.meta as ImportMeta & { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? "/api";

// ── Types ─────────────────────────────────────────────────────────────────

type SupplierGroup = {
  supplier: string;
  prm_count: number;
  prm_ids: string[];
  tariff_codes: string[];
  config_id: number | null;
  lot: string | null;
  has_hphc: boolean;
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

type PriceEntry = { id: number; config_id: number; year: number | null; component: string; value: number; unit: string | null };
type HphcSlot = { id: number; config_id: number; day_type: string; start_time: string; end_time: string; period: string };

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

const COMPONENTS_BASE = ["abo", "base", "turpe_fix", "turpe_kwh", "cta", "cspe", "tva"] as const;
const COMPONENTS_HPHC = ["abo", "hp", "hc", "turpe_fix", "turpe_kwh", "cta", "cspe", "tva"] as const;
type Component = (typeof COMPONENTS_BASE)[number] | (typeof COMPONENTS_HPHC)[number];

const COMPONENT_LABELS: Record<string, string> = {
  abo: "Abonnement",
  base: "Énergie base",
  hp: "Énergie Heures Pleines",
  hc: "Énergie Heures Creuses",
  turpe_fix: "TURPE fixe",
  turpe_kwh: "TURPE variable",
  cta: "CTA",
  cspe: "CSPE / TICFE",
  tva: "TVA",
};

const COMPONENT_UNITS: Record<string, string> = {
  abo: "€/mois",
  base: "€/kWh",
  hp: "€/kWh",
  hc: "€/kWh",
  turpe_fix: "€/mois",
  turpe_kwh: "€/kWh",
  cta: "%",
  cspe: "€/MWh",
  tva: "%",
};

const DAY_TYPE_LABELS: Record<string, string> = {
  lun_ven: "Lun–Ven",
  sam_dim: "Sam–Dim",
  tous: "Tous les jours",
};

const CHART_COLORS = ["#2563eb", "#f97316", "#16a34a", "#a855f7", "#06b6d4"];

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

async function apiPatch<T>(token: string, path: string, body: unknown): Promise<T> {
  const r = await fetch(`${apiBaseUrl}${path}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// ── Sub-components ────────────────────────────────────────────────────────

function HistoricalChart({ prices, components }: { prices: PriceEntry[]; components: readonly string[] }) {
  const historical = prices.filter((p) => p.year !== null);
  const years = [...new Set(historical.map((p) => p.year))].sort() as number[];
  if (years.length === 0) return null;

  const byYear: Record<number, Record<string, number>> = {};
  historical.forEach((p) => {
    if (p.year !== null) {
      byYear[p.year] = byYear[p.year] ?? {};
      byYear[p.year][p.component] = p.value;
    }
  });
  const data = years.map((y) => ({ year: String(y), ...byYear[y] }));
  const shown = [...components].filter((c) => years.some((y) => byYear[y]?.[c] !== undefined));

  return (
    <div style={{ height: 220, marginBottom: 20 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="year" />
          <YAxis />
          <Tooltip formatter={(v: number, name: string) => [`${v} ${COMPONENT_UNITS[name] ?? ""}`, COMPONENT_LABELS[name] ?? name]} />
          <Legend formatter={(name) => COMPONENT_LABELS[name] ?? name} />
          {shown.map((comp, i) => (
            <Line key={comp} type="monotone" dataKey={comp} stroke={CHART_COLORS[i % CHART_COLORS.length]} dot={{ r: 4 }} connectNulls />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Wizard ────────────────────────────────────────────────────────────────

function BillingWizard({
  group,
  onClose,
}: {
  group: SupplierGroup;
  onClose: () => void;
}) {
  const { token } = useAuth();
  const qc = useQueryClient();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [cfg, setCfg] = useState<BillingConfigOut | null>(null);

  const configId = cfg?.id ?? group.config_id;

  // ── Step 1 ───────────────────────────────────────────────────────────
  const [lot, setLot] = useState(group.lot ?? "");
  const [selectedPrm, setSelectedPrm] = useState("");
  const [hasHphc, setHasHphc] = useState(group.has_hphc);

  // Load existing config details
  const configQuery = useQuery({
    queryKey: ["billing-config", group.config_id],
    queryFn: () => apiGet<BillingConfigOut>(token!, `/billing/configs/${group.config_id}`),
    enabled: !!token && !!group.config_id,
  });

  useEffect(() => {
    if (configQuery.data) {
      setCfg(configQuery.data);
      setSelectedPrm(configQuery.data.representative_prm_id ?? "");
      setHasHphc(configQuery.data.has_hphc);
      setLot(configQuery.data.lot ?? "");
    }
  }, [configQuery.data]);

  const upsertMut = useMutation({
    mutationFn: () =>
      apiPut<BillingConfigOut>(token!, `/billing/configs/supplier/${encodeURIComponent(group.supplier)}`, {
        lot: lot || null,
        has_hphc: hasHphc,
        representative_prm_id: selectedPrm || null,
      }),
    onSuccess: (data) => {
      setCfg(data);
      qc.invalidateQueries({ queryKey: ["billing-supplier-groups"] });
      setStep(2);
    },
  });

  // ── Step 2 ───────────────────────────────────────────────────────────
  const components: readonly Component[] = hasHphc ? COMPONENTS_HPHC : COMPONENTS_BASE;

  const pricesQuery = useQuery({
    queryKey: ["billing-prices", configId],
    queryFn: () => apiGet<PriceEntry[]>(token!, `/billing/configs/${configId}/prices`),
    enabled: !!token && !!configId,
  });

  const currentPrices: Record<string, number> = {};
  (pricesQuery.data ?? []).filter((e) => e.year === null).forEach((e) => { currentPrices[e.component] = e.value; });

  const [priceInputs, setPriceInputs] = useState<Record<string, string>>({});
  const priceVal = (comp: string) =>
    priceInputs[comp] !== undefined ? priceInputs[comp] : currentPrices[comp] !== undefined ? String(currentPrices[comp]) : "";

  const setPricesMut = useMutation({
    mutationFn: () => {
      const historical = (pricesQuery.data ?? [])
        .filter((e) => e.year !== null)
        .map((e) => ({ year: e.year, component: e.component, value: e.value, unit: e.unit }));
      const current = [...components]
        .filter((c) => priceVal(c) !== "")
        .map((c) => ({ year: null, component: c, value: parseFloat(priceVal(c)), unit: COMPONENT_UNITS[c] ?? null }));
      return apiPut<PriceEntry[]>(token!, `/billing/configs/${configId}/prices`, [...current, ...historical]);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["billing-prices", configId] });
      setStep(3);
    },
  });

  // HP/HC slots
  const slotsQuery = useQuery({
    queryKey: ["billing-hphc-slots", configId],
    queryFn: () => apiGet<HphcSlot[]>(token!, `/billing/configs/${configId}/hphc-slots`),
    enabled: !!token && !!configId && hasHphc,
  });

  const [slotRows, setSlotRows] = useState<{ day_type: string; start_time: string; end_time: string; period: string }[]>([]);
  const [slotsInit, setSlotsInit] = useState(false);
  useEffect(() => {
    if (!slotsInit && slotsQuery.data && slotsQuery.data.length > 0) {
      setSlotRows(slotsQuery.data.map(({ day_type, start_time, end_time, period }) => ({ day_type, start_time, end_time, period })));
      setSlotsInit(true);
    }
  }, [slotsQuery.data, slotsInit]);

  const addSlot = () => setSlotRows((r) => [...r, { day_type: "tous", start_time: "06:00", end_time: "22:00", period: "HP" }]);
  const removeSlot = (i: number) => setSlotRows((r) => r.filter((_, idx) => idx !== i));
  const updateSlot = (i: number, field: string, value: string) =>
    setSlotRows((r) => r.map((s, idx) => (idx === i ? { ...s, [field]: value } : s)));

  const setSlotsMut = useMutation({
    mutationFn: () => apiPut(token!, `/billing/configs/${configId}/hphc-slots`, slotRows),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["billing-hphc-slots", configId] }),
  });

  // ── Step 3 ───────────────────────────────────────────────────────────
  const historicalPrices = (pricesQuery.data ?? []).filter((e) => e.year !== null);
  const [newHistYear, setNewHistYear] = useState("");
  const [newHistInputs, setNewHistInputs] = useState<Record<string, string>>({});

  const addHistMut = useMutation({
    mutationFn: () => {
      const existing = (pricesQuery.data ?? [])
        .filter((e) => e.year !== parseInt(newHistYear))
        .map((e) => ({ year: e.year, component: e.component, value: e.value, unit: e.unit }));
      const newEntries = [...components]
        .filter((c) => newHistInputs[c])
        .map((c) => ({ year: parseInt(newHistYear), component: c, value: parseFloat(newHistInputs[c]), unit: COMPONENT_UNITS[c] ?? null }));
      return apiPut<PriceEntry[]>(token!, `/billing/configs/${configId}/prices`, [...existing, ...newEntries]);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["billing-prices", configId] });
      setNewHistYear("");
      setNewHistInputs({});
    },
  });

  const canGoNext = configId && step < 3;

  return (
    <div className="wizard-overlay" onClick={onClose}>
      <div className="wizard-panel" onClick={(e) => e.stopPropagation()}>
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
              {s === 1 ? "Lot & référent" : s === 2 ? "BPU & prix" : "Historique"}
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
                  <span>Contrat HP/HC (Heures Pleines / Heures Creuses)</span>
                </label>
              </div>
              <p style={{ fontSize: 12, color: "#64748b", marginTop: 6 }}>
                Activer si le BPU distingue HP et HC (typique pour les contrats CU4, MU4).
              </p>

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
            </div>
          )}

          {/* ── Step 2 ── */}
          {step === 2 && configId && (
            <div>
              <p className="field-label" style={{ marginBottom: 8 }}>
                Prix unitaires {hasHphc ? "(HP/HC)" : "(Base)"}
              </p>
              <p style={{ fontSize: 12, color: "#64748b", marginBottom: 12 }}>
                Ces prix s'appliquent à tous les PRMs de <strong>{group.supplier}</strong>.
                {hasHphc && " La plateforme appliquera HP aux PRMs avec tarif CU4/MU4, et base aux autres."}
              </p>

              <table className="data-table">
                <thead>
                  <tr><th>Composante</th><th>Valeur</th><th>Unité</th></tr>
                </thead>
                <tbody>
                  {[...components].map((comp) => (
                    <tr key={comp}>
                      <td>{COMPONENT_LABELS[comp]}</td>
                      <td>
                        <input
                          type="number"
                          step="any"
                          className="form-input"
                          style={{ width: 120, padding: "4px 8px" }}
                          value={priceVal(comp)}
                          onChange={(e) => setPriceInputs((p) => ({ ...p, [comp]: e.target.value }))}
                        />
                      </td>
                      <td style={{ color: "#64748b", fontSize: 13 }}>{COMPONENT_UNITS[comp]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {hasHphc && (
                <div style={{ marginTop: 20 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <p className="field-label" style={{ margin: 0 }}>Plages HP/HC</p>
                    <button className="secondary-button" style={{ padding: "4px 10px" }} onClick={addSlot}>+ Ajouter</button>
                  </div>
                  {slotRows.length === 0 && (
                    <p style={{ color: "#64748b", fontSize: 13 }}>Aucune plage définie.</p>
                  )}
                  {slotRows.map((slot, i) => (
                    <div key={i} className="hphc-slot-row">
                      <select className="form-input" style={{ flex: "1 1 110px" }} value={slot.day_type} onChange={(e) => updateSlot(i, "day_type", e.target.value)}>
                        {Object.entries(DAY_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                      <input type="time" className="form-input" style={{ flex: "0 0 90px" }} value={slot.start_time} onChange={(e) => updateSlot(i, "start_time", e.target.value)} />
                      <span>→</span>
                      <input type="time" className="form-input" style={{ flex: "0 0 90px" }} value={slot.end_time} onChange={(e) => updateSlot(i, "end_time", e.target.value)} />
                      <select className="form-input" style={{ flex: "0 0 70px" }} value={slot.period} onChange={(e) => updateSlot(i, "period", e.target.value)}>
                        <option value="HP">HP</option>
                        <option value="HC">HC</option>
                      </select>
                      <button className="secondary-button" style={{ padding: "4px 8px" }} onClick={() => removeSlot(i)}>✕</button>
                    </div>
                  ))}
                  {slotRows.length > 0 && (
                    <button className="secondary-button" style={{ marginTop: 8 }} disabled={setSlotsMut.isPending} onClick={() => setSlotsMut.mutate()}>
                      {setSlotsMut.isPending ? "Enregistrement…" : "Enregistrer les plages"}
                    </button>
                  )}
                </div>
              )}

              <div style={{ marginTop: 20, display: "flex", gap: 8 }}>
                <button className="btn-primary" disabled={setPricesMut.isPending} onClick={() => setPricesMut.mutate()}>
                  {setPricesMut.isPending ? "Enregistrement…" : "Enregistrer et continuer →"}
                </button>
                <button className="secondary-button" onClick={() => setStep(3)}>Passer à l'historique</button>
              </div>
            </div>
          )}

          {/* ── Step 3 ── */}
          {step === 3 && configId && (
            <div>
              {historicalPrices.length > 0 ? (
                <HistoricalChart prices={pricesQuery.data ?? []} components={components} />
              ) : (
                <p style={{ color: "#64748b", fontSize: 13, marginBottom: 16 }}>
                  Aucune donnée historique. Ajoutez des années passées pour visualiser l'évolution des prix.
                </p>
              )}

              <div className="hist-add-form">
                <p className="field-label">Ajouter une année historique</p>
                <div style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <span style={{ fontSize: 11, color: "#64748b" }}>Année</span>
                    <input
                      type="number"
                      className="form-input"
                      style={{ width: 90, padding: "4px 8px" }}
                      placeholder="2024"
                      value={newHistYear}
                      onChange={(e) => setNewHistYear(e.target.value)}
                    />
                  </div>
                  {[...components].map((comp) => (
                    <div key={comp} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <span style={{ fontSize: 11, color: "#64748b" }}>{COMPONENT_LABELS[comp]}</span>
                      <input
                        type="number"
                        step="any"
                        className="form-input"
                        style={{ width: 90, padding: "4px 8px" }}
                        placeholder={COMPONENT_UNITS[comp]}
                        value={newHistInputs[comp] ?? ""}
                        onChange={(e) => setNewHistInputs((p) => ({ ...p, [comp]: e.target.value }))}
                      />
                    </div>
                  ))}
                </div>
                <button
                  className="btn-primary"
                  style={{ marginTop: 12 }}
                  disabled={!newHistYear || addHistMut.isPending}
                  onClick={() => addHistMut.mutate()}
                >
                  {addHistMut.isPending ? "Enregistrement…" : "Ajouter"}
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

  // Lot assignment inline (without opening wizard)
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
          Configurez les prix BPU par fournisseur pour estimer les coûts de chaque PRM.
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
                            <span key={tc} className="badge badge-gray" style={{ fontSize: 11 }}>{tc}</span>
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
                <li>Cliquez sur <em>Configurer BPU</em> pour saisir les prix unitaires du BPU.</li>
                <li>Optionnel : ajoutez les prix des années passées pour suivre l'évolution.</li>
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
