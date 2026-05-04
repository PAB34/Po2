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
import {
  BillingConfigOut,
  BillingGroupItem,
  BillingHphcSlotIn,
  BillingPriceEntryIn,
  createBillingConfig,
  fetchBillingConfigs,
  fetchBillingGroups,
  fetchBillingHphcSlots,
  fetchBillingPrices,
  patchBillingConfig,
  setBillingHphcSlots,
  setBillingPrices,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

// ── Constants ─────────────────────────────────────────────────────────────

const COMPONENTS_BASE = ["abo", "base", "turpe_fix", "turpe_kwh", "cta", "cspe", "tva"] as const;
const COMPONENTS_HPHC = ["abo", "hp", "hc", "turpe_fix", "turpe_kwh", "cta", "cspe", "tva"] as const;
type Component = (typeof COMPONENTS_BASE)[number] | (typeof COMPONENTS_HPHC)[number];

const COMPONENT_LABELS: Record<string, string> = {
  abo: "Abonnement",
  base: "Énergie base",
  hp: "Énergie HP",
  hc: "Énergie HC",
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
  ferie: "Jours fériés",
};

const CHART_COLORS = ["#2563eb", "#f97316", "#16a34a", "#a855f7", "#06b6d4"];

// ── Sub-components ────────────────────────────────────────────────────────

function StatusBadge({ configured }: { configured: boolean }) {
  return (
    <span className={`badge ${configured ? "badge-green" : "badge-gray"}`}>
      {configured ? "Configuré" : "Non configuré"}
    </span>
  );
}

function GroupsTable({
  groups,
  onConfigure,
}: {
  groups: BillingGroupItem[];
  onConfigure: (g: BillingGroupItem) => void;
}) {
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Fournisseur</th>
          <th>Tarif</th>
          <th>PRMs</th>
          <th>Statut</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {groups.map((g) => (
          <tr key={`${g.supplier}|${g.tariff_code}`}>
            <td>{g.supplier}</td>
            <td>
              <strong>{g.tariff_code}</strong>
              <span style={{ marginLeft: 8, color: "#94a3b8", fontSize: 12 }}>
                {g.tariff_label.length > 60 ? g.tariff_label.slice(0, 57) + "…" : g.tariff_label}
              </span>
            </td>
            <td>{g.prm_count}</td>
            <td>
              <StatusBadge configured={g.is_configured} />
            </td>
            <td>
              <button
                className="secondary-button"
                style={{ padding: "4px 12px" }}
                onClick={() => onConfigure(g)}
              >
                {g.config_id ? "Modifier" : "Configurer"}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ── Historical Chart ──────────────────────────────────────────────────────

function HistoricalChart({
  prices,
  components,
}: {
  prices: { year: number | null; component: string; value: number }[];
  components: readonly string[];
}) {
  const years = [...new Set(prices.map((p) => p.year).filter(Boolean))].sort() as number[];
  const byYear: Record<number, Record<string, number>> = {};
  prices.forEach((p) => {
    if (p.year !== null) {
      byYear[p.year] = byYear[p.year] ?? {};
      byYear[p.year][p.component] = p.value;
    }
  });
  const data = years.map((y) => ({ year: String(y), ...byYear[y] }));
  const shownComponents = [...components].filter((c) =>
    years.some((y) => byYear[y]?.[c] !== undefined)
  );

  if (shownComponents.length === 0 || years.length === 0) return null;

  return (
    <div style={{ height: 240, marginBottom: 20 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="year" />
          <YAxis />
          <Tooltip
            formatter={(v: number, name: string) => [
              `${v} ${COMPONENT_UNITS[name] ?? ""}`,
              COMPONENT_LABELS[name] ?? name,
            ]}
          />
          <Legend formatter={(name) => COMPONENT_LABELS[name] ?? name} />
          {shownComponents.map((comp, i) => (
            <Line
              key={comp}
              type="monotone"
              dataKey={comp}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              dot={{ r: 4 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Billing Wizard ────────────────────────────────────────────────────────

type WizardProps = {
  group: BillingGroupItem;
  initialConfig: BillingConfigOut | null;
  onClose: () => void;
};

function BillingWizard({ group, initialConfig, onClose }: WizardProps) {
  const { token } = useAuth();
  const qc = useQueryClient();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  // cfg is the live config object; starts from initialConfig, updated after step-1 save
  const [cfg, setCfg] = useState<BillingConfigOut | null>(initialConfig);

  const configId = cfg?.id;

  // ── Step 1 ───────────────────────────────────────────────────────────
  const [selectedPrm, setSelectedPrm] = useState(initialConfig?.representative_prm_id ?? "");
  const [hasHphc, setHasHphc] = useState(initialConfig?.has_hphc ?? false);

  const createMut = useMutation({
    mutationFn: () =>
      createBillingConfig(token!, {
        supplier: group.supplier,
        tariff_code: group.tariff_code,
        tariff_label: group.tariff_label,
        has_hphc: hasHphc,
        representative_prm_id: selectedPrm || undefined,
      }),
    onSuccess: (created) => {
      setCfg(created);
      qc.invalidateQueries({ queryKey: ["billing-groups"] });
      setStep(2);
    },
  });

  const patchMut = useMutation({
    mutationFn: () =>
      patchBillingConfig(token!, cfg!.id, {
        has_hphc: hasHphc,
        representative_prm_id: selectedPrm || undefined,
      }),
    onSuccess: (updated) => {
      setCfg(updated);
      qc.invalidateQueries({ queryKey: ["billing-groups"] });
      setStep(2);
    },
  });

  const step1Save = () => {
    if (!selectedPrm) return;
    if (cfg) patchMut.mutate();
    else createMut.mutate();
  };

  // ── Step 2 ───────────────────────────────────────────────────────────
  const effectiveHasHphc = cfg?.has_hphc ?? hasHphc;
  const components: readonly Component[] = effectiveHasHphc ? COMPONENTS_HPHC : COMPONENTS_BASE;

  const pricesQuery = useQuery({
    queryKey: ["billing-prices", configId],
    queryFn: () => fetchBillingPrices(token!, configId!),
    enabled: !!configId,
  });

  const currentPrices: Record<string, number> = {};
  (pricesQuery.data ?? [])
    .filter((e) => e.year === null)
    .forEach((e) => { currentPrices[e.component] = e.value; });

  const [priceInputs, setPriceInputs] = useState<Record<string, string>>({});
  const effectivePriceValue = (comp: string) =>
    priceInputs[comp] !== undefined ? priceInputs[comp] : currentPrices[comp] !== undefined ? String(currentPrices[comp]) : "";

  const setPricesMut = useMutation({
    mutationFn: (entries: BillingPriceEntryIn[]) => setBillingPrices(token!, configId!, entries),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["billing-prices", configId] });
      setStep(3);
    },
  });

  const step2Save = () => {
    if (!configId) return;
    const historical: BillingPriceEntryIn[] = (pricesQuery.data ?? [])
      .filter((e) => e.year !== null)
      .map((e) => ({ year: e.year, component: e.component, value: e.value, unit: e.unit }));
    const current: BillingPriceEntryIn[] = [...components]
      .filter((c) => effectivePriceValue(c) !== "")
      .map((c) => ({
        year: null,
        component: c,
        value: parseFloat(effectivePriceValue(c)),
        unit: COMPONENT_UNITS[c] ?? null,
      }));
    setPricesMut.mutate([...current, ...historical]);
  };

  // ── HP/HC Slots ──────────────────────────────────────────────────────
  const slotsQuery = useQuery({
    queryKey: ["billing-hphc-slots", configId],
    queryFn: () => fetchBillingHphcSlots(token!, configId!),
    enabled: !!configId && effectiveHasHphc,
  });

  const [slotRows, setSlotRows] = useState<BillingHphcSlotIn[]>([]);
  const [slotsInitialized, setSlotsInitialized] = useState(false);
  useEffect(() => {
    if (!slotsInitialized && slotsQuery.data && slotsQuery.data.length > 0) {
      setSlotRows(
        slotsQuery.data.map(({ day_type, start_time, end_time, period }) => ({
          day_type, start_time, end_time, period,
        }))
      );
      setSlotsInitialized(true);
    }
  }, [slotsQuery.data, slotsInitialized]);

  const addSlot = () =>
    setSlotRows((r) => [...r, { day_type: "tous", start_time: "06:00", end_time: "22:00", period: "HP" }]);
  const removeSlot = (i: number) => setSlotRows((r) => r.filter((_, idx) => idx !== i));
  const updateSlot = (i: number, field: keyof BillingHphcSlotIn, value: string) =>
    setSlotRows((r) => r.map((s, idx) => (idx === i ? { ...s, [field]: value } : s)));

  const setSlotsMut = useMutation({
    mutationFn: () => setBillingHphcSlots(token!, configId!, slotRows),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["billing-hphc-slots", configId] }),
  });

  // ── Step 3 ───────────────────────────────────────────────────────────
  const historicalPrices = (pricesQuery.data ?? []).filter((e) => e.year !== null);
  const [newHistYear, setNewHistYear] = useState("");
  const [newHistInputs, setNewHistInputs] = useState<Record<string, string>>({});

  const addHistoryMut = useMutation({
    mutationFn: () => {
      const existing: BillingPriceEntryIn[] = (pricesQuery.data ?? [])
        .filter((e) => e.year !== parseInt(newHistYear))
        .map((e) => ({ year: e.year, component: e.component, value: e.value, unit: e.unit }));
      const newEntries: BillingPriceEntryIn[] = [...components]
        .filter((c) => newHistInputs[c])
        .map((c) => ({
          year: parseInt(newHistYear),
          component: c,
          value: parseFloat(newHistInputs[c]),
          unit: COMPONENT_UNITS[c] ?? null,
        }));
      return setBillingPrices(token!, configId!, [...existing, ...newEntries]);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["billing-prices", configId] });
      setNewHistYear("");
      setNewHistInputs({});
    },
  });

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div className="wizard-overlay" onClick={onClose}>
      <div className="wizard-panel" onClick={(e) => e.stopPropagation()}>
        <div className="wizard-header">
          <div>
            <h2 className="wizard-title">
              {group.supplier} · {group.tariff_code}
            </h2>
            <p className="wizard-subtitle">
              {group.prm_count} PRM(s) · {group.tariff_label}
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
              {s === 1 ? "PRM référent" : s === 2 ? "BPU & prix" : "Historique"}
            </button>
          ))}
        </div>

        <div className="wizard-body">
          {/* ── Step 1 ── */}
          {step === 1 && (
            <div>
              <p className="field-label">PRM représentatif de ce groupe tarifaire</p>
              <select
                className="form-input"
                value={selectedPrm}
                onChange={(e) => setSelectedPrm(e.target.value)}
              >
                <option value="">-- Choisir un PRM --</option>
                {group.prm_ids.map((id) => (
                  <option key={id} value={id}>{id}</option>
                ))}
              </select>

              <div className="toggle-row" style={{ marginTop: 16 }}>
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    checked={hasHphc}
                    onChange={(e) => setHasHphc(e.target.checked)}
                  />
                  <span>Tarif HP/HC (heures pleines / heures creuses)</span>
                </label>
              </div>

              <div style={{ marginTop: 20, display: "flex", gap: 8 }}>
                <button
                  className="btn-primary"
                  disabled={!selectedPrm || createMut.isPending || patchMut.isPending}
                  onClick={step1Save}
                >
                  {createMut.isPending || patchMut.isPending
                    ? "Enregistrement…"
                    : "Enregistrer et continuer"}
                </button>
                {configId && (
                  <button className="secondary-button" onClick={() => setStep(2)}>
                    Passer au BPU
                  </button>
                )}
              </div>
            </div>
          )}

          {/* ── Step 2 ── */}
          {step === 2 && configId && (
            <div>
              <p className="field-label" style={{ marginBottom: 8 }}>
                Prix unitaires actuels{effectiveHasHphc ? " (tarif HP/HC)" : " (tarif base)"}
              </p>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Composante</th>
                    <th>Valeur</th>
                    <th>Unité</th>
                  </tr>
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
                          value={effectivePriceValue(comp)}
                          onChange={(e) =>
                            setPriceInputs((p) => ({ ...p, [comp]: e.target.value }))
                          }
                        />
                      </td>
                      <td style={{ color: "#94a3b8", fontSize: 13 }}>
                        {COMPONENT_UNITS[comp]}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {effectiveHasHphc && (
                <div style={{ marginTop: 20 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: 8,
                    }}
                  >
                    <p className="field-label" style={{ margin: 0 }}>Plages HP/HC</p>
                    <button
                      className="secondary-button"
                      style={{ padding: "4px 10px" }}
                      onClick={addSlot}
                    >
                      + Ajouter
                    </button>
                  </div>
                  {slotRows.length === 0 && (
                    <p style={{ color: "#94a3b8", fontSize: 13 }}>
                      Aucune plage définie.
                    </p>
                  )}
                  {slotRows.map((slot, i) => (
                    <div key={i} className="hphc-slot-row">
                      <select
                        className="form-input"
                        style={{ flex: "1 1 110px" }}
                        value={slot.day_type}
                        onChange={(e) => updateSlot(i, "day_type", e.target.value)}
                      >
                        {Object.entries(DAY_TYPE_LABELS).map(([k, v]) => (
                          <option key={k} value={k}>{v}</option>
                        ))}
                      </select>
                      <input
                        type="time"
                        className="form-input"
                        style={{ flex: "0 0 90px" }}
                        value={slot.start_time}
                        onChange={(e) => updateSlot(i, "start_time", e.target.value)}
                      />
                      <span>→</span>
                      <input
                        type="time"
                        className="form-input"
                        style={{ flex: "0 0 90px" }}
                        value={slot.end_time}
                        onChange={(e) => updateSlot(i, "end_time", e.target.value)}
                      />
                      <select
                        className="form-input"
                        style={{ flex: "0 0 70px" }}
                        value={slot.period}
                        onChange={(e) => updateSlot(i, "period", e.target.value)}
                      >
                        <option value="HP">HP</option>
                        <option value="HC">HC</option>
                      </select>
                      <button
                        className="secondary-button"
                        style={{ padding: "4px 8px" }}
                        onClick={() => removeSlot(i)}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  {slotRows.length > 0 && (
                    <button
                      className="secondary-button"
                      style={{ marginTop: 8 }}
                      disabled={setSlotsMut.isPending}
                      onClick={() => setSlotsMut.mutate()}
                    >
                      {setSlotsMut.isPending ? "Enregistrement…" : "Enregistrer les plages"}
                    </button>
                  )}
                </div>
              )}

              <div style={{ marginTop: 20, display: "flex", gap: 8 }}>
                <button
                  className="btn-primary"
                  disabled={setPricesMut.isPending}
                  onClick={step2Save}
                >
                  {setPricesMut.isPending ? "Enregistrement…" : "Enregistrer et continuer"}
                </button>
                <button className="secondary-button" onClick={() => setStep(3)}>
                  Passer à l'historique
                </button>
              </div>
            </div>
          )}

          {/* ── Step 3 ── */}
          {step === 3 && configId && (
            <div>
              {historicalPrices.length > 0 && (
                <HistoricalChart prices={historicalPrices} components={components} />
              )}
              {historicalPrices.length === 0 && (
                <p style={{ color: "#94a3b8", fontSize: 13, marginBottom: 16 }}>
                  Aucune donnée historique saisie pour l'instant.
                </p>
              )}

              <div className="hist-add-form">
                <p className="field-label">Ajouter une année</p>
                <div
                  style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <span style={{ fontSize: 11, color: "#94a3b8" }}>Année</span>
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
                    <div
                      key={comp}
                      style={{ display: "flex", flexDirection: "column", gap: 4 }}
                    >
                      <span style={{ fontSize: 11, color: "#94a3b8" }}>
                        {COMPONENT_LABELS[comp]}
                      </span>
                      <input
                        type="number"
                        step="any"
                        className="form-input"
                        style={{ width: 90, padding: "4px 8px" }}
                        placeholder={COMPONENT_UNITS[comp]}
                        value={newHistInputs[comp] ?? ""}
                        onChange={(e) =>
                          setNewHistInputs((p) => ({ ...p, [comp]: e.target.value }))
                        }
                      />
                    </div>
                  ))}
                </div>
                <button
                  className="btn-primary"
                  style={{ marginTop: 12 }}
                  disabled={!newHistYear || addHistoryMut.isPending}
                  onClick={() => addHistoryMut.mutate()}
                >
                  {addHistoryMut.isPending ? "Enregistrement…" : "Ajouter l'année"}
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
  const [selectedGroup, setSelectedGroup] = useState<BillingGroupItem | null>(null);

  const groupsQuery = useQuery({
    queryKey: ["billing-groups"],
    queryFn: () => fetchBillingGroups(token!),
    enabled: !!token,
  });

  const configsQuery = useQuery({
    queryKey: ["billing-configs"],
    queryFn: () => fetchBillingConfigs(token!),
    enabled: !!token,
  });

  const groups = groupsQuery.data ?? [];
  const configs = configsQuery.data ?? [];

  const getInitialConfig = (g: BillingGroupItem): BillingConfigOut | null =>
    configs.find((c) => c.id === g.config_id) ?? null;

  const handleConfigure = (g: BillingGroupItem) => setSelectedGroup(g);
  const handleClose = () => {
    setSelectedGroup(null);
    groupsQuery.refetch();
    configsQuery.refetch();
  };

  const configured = groups.filter((g) => g.is_configured).length;
  const total = groups.length;

  return (
    <div className="page">
      <div className="page-header">
        <h2>Facturation ENEDIS</h2>
        <p className="page-subtitle">
          Configuration des prix unitaires par groupe fournisseur × tarif
        </p>
      </div>

      {groupsQuery.isLoading && <p className="loading-text">Chargement des groupes tarifaires…</p>}
      {groupsQuery.isError && <p className="error-text">Erreur lors du chargement.</p>}

      {!groupsQuery.isLoading && (
        <>
          <div className="kpi-row" style={{ marginBottom: 24 }}>
            <div className="kpi-card">
              <span className="kpi-value">{total}</span>
              <span className="kpi-label">Groupes tarifaires détectés</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-value">{configured}</span>
              <span className="kpi-label">Configurés</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-value">{total - configured}</span>
              <span className="kpi-label">En attente</span>
            </div>
          </div>

          {groups.length === 0 ? (
            <p style={{ color: "#94a3b8" }}>
              Aucun contrat ENEDIS importé. Lancez une synchronisation depuis la page Énergie.
            </p>
          ) : (
            <GroupsTable groups={groups} onConfigure={handleConfigure} />
          )}
        </>
      )}

      {selectedGroup && (
        <BillingWizard
          group={selectedGroup}
          initialConfig={getInitialConfig(selectedGroup)}
          onClose={handleClose}
        />
      )}
    </div>
  );
}
