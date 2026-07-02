import { useMemo, useState } from "react";
import { Button, Card, DataTable, KpiCard, SegmentControl, StatusBadge } from "../../design-system";
import type { AccountingMatrixContractV1 } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";
import { ContractBudgetLandingV1 } from "./ContractBudgetLandingV1";
import { GasBudgetReviseV1 } from "./GasBudgetReviseV1";
import {
  useBudgetLinesV1,
  useBudgetSuiviV1,
  useCreateBudgetLineV1,
  useDeleteBudgetLineV1,
  useMarketContractsV1,
  useUpdateBudgetLineV1,
} from "./useBudgetV1";

type MarketsViewV1 = "saisi" | "contractuel" | "gaz";

const BUDGET_WRITE_DENIED_ROLES = new Set(["FLUIDES", "FLUIDE", "RESPONSABLE_FLUIDES", "TECHNICIEN_CVC", "TECHNICIEN CVC"]);
const BUDGET_WRITE_ALLOWED_ROLES = new Set([
  "ADMIN", "SUPERADMIN", "DIRECTION", "RESPONSABLE_MAINTENANCE",
  "RESPONSABLE MAINTENANCE", "PATRIMOINE", "FINANCE", "COMPTA", "COMPTABILITE",
]);

function normalizeRole(role: string | undefined) {
  return (role ?? "").trim().toUpperCase().replace("-", "_");
}

function canWriteBudget(role: string | undefined) {
  const normalized = normalizeRole(role);
  return BUDGET_WRITE_ALLOWED_ROLES.has(normalized) && !BUDGET_WRITE_DENIED_ROLES.has(normalized);
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Une erreur est survenue.";
}

function eur(value: number) {
  return value.toLocaleString("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
}

function contractLabel(contract: AccountingMatrixContractV1) {
  const parts = [contract.supplier, contract.contract_code, contract.lot_label].filter(Boolean);
  return parts.join(" - ") || contract.contract_label || `Marché #${contract.id}`;
}

function varianceTone(variance: number) {
  if (variance < 0) return "bad" as const;
  if (variance < 500) return "warn" as const;
  return "ok" as const;
}

export function MarketsBudgetPageV1() {
  const { user } = useAuth();
  const canWrite = canWriteBudget(user?.role);
  const currentYear = new Date().getFullYear();

  const [view, setView] = useState<MarketsViewV1>("saisi");
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);
  const [year, setYear] = useState(currentYear);
  const [newOperation, setNewOperation] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [newAmount, setNewAmount] = useState("");

  const { data: contracts = [], isFetching: contractsFetching } = useMarketContractsV1();
  const cpeContracts = useMemo(() => contracts.filter((c) => c.domain === "cpe"), [contracts]);
  const otherContracts = useMemo(() => contracts.filter((c) => c.domain !== "cpe"), [contracts]);

  const effectiveContractId = selectedContractId ?? cpeContracts[0]?.id ?? contracts[0]?.id ?? null;
  const selectedContract = contracts.find((c) => c.id === effectiveContractId) ?? null;

  const budgetLines = useBudgetLinesV1(effectiveContractId, year);
  const suivi = useBudgetSuiviV1(effectiveContractId, year);
  const createLine = useCreateBudgetLineV1(effectiveContractId, year);
  const updateLine = useUpdateBudgetLineV1(effectiveContractId, year);
  const deleteLine = useDeleteBudgetLineV1(effectiveContractId, year);

  function handleAddLine() {
    if (!effectiveContractId || !newOperation.trim()) return;
    createLine.mutate(
      {
        matrix_contract_id: effectiveContractId,
        year,
        operation_number: newOperation.trim(),
        label: newLabel.trim() || undefined,
        amount_budget: Number(newAmount) || 0,
      },
      {
        onSuccess: () => {
          setNewOperation("");
          setNewLabel("");
          setNewAmount("");
        },
      },
    );
  }

  const suiviRows = suivi.data?.rows ?? [];

  return (
    <>
      <div className="po2-page-v1__viewswitch" style={{ marginBottom: "1rem" }}>
        <SegmentControl
          value={view}
          options={[
            { value: "saisi", label: "Budget saisi (opération)" },
            { value: "contractuel", label: "Budget contractuel (poste)" },
            { value: "gaz", label: "Budget révisé gaz (fixe/variable)" },
          ]}
          onChange={setView}
        />
      </div>
      {view === "contractuel" ? (
        <ContractBudgetLandingV1 />
      ) : view === "gaz" ? (
        <GasBudgetReviseV1 />
      ) : (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">Marchés - budget et suivi financier</span>
        <h1>Budget par marché, à la maille opération</h1>
        <p>
          Objectif v1 (pilote CPE/DALKIA) : saisir le budget annuel par opération pour un marché, comparer au réalisé
          (factures figées) et à un atterrissage pro-rata temporel. L'atterrissage physique/financier (doc 34 §F04)
          viendra en v2.
        </p>
      </header>

      <Card title="Marché suivi" eyebrow="sélectionner le contrat matrice = le marché">
        {contractsFetching && contracts.length === 0 ? (
          <p className="po2-muted-line">Chargement des marchés...</p>
        ) : contracts.length === 0 ? (
          <p className="po2-muted-line">Aucun marché disponible. Configure d'abord une matrice comptable.</p>
        ) : (
          <div className="po2-matrix-supplier-grid">
            {[...cpeContracts, ...otherContracts].map((contract) => (
              <button
                type="button"
                key={contract.id}
                className={
                  contract.id === effectiveContractId
                    ? "po2-matrix-supplier-card po2-matrix-supplier-card--active"
                    : "po2-matrix-supplier-card"
                }
                onClick={() => setSelectedContractId(contract.id)}
              >
                <span className="po2-eyebrow">{contract.domain === "cpe" ? "CPE" : contract.domain}</span>
                <strong>{contractLabel(contract)}</strong>
                <small>{contract.active_version_label ? `Matrice active : ${contract.active_version_label}` : "Aucune version active"}</small>
              </button>
            ))}
          </div>
        )}
        <div className="po2-matrix-import-form">
          <label>
            <span>Année</span>
            <input
              type="number"
              value={year}
              onChange={(event) => setYear(Number(event.currentTarget.value) || currentYear)}
            />
          </label>
        </div>
      </Card>

      {selectedContract && suivi.isError ? (
        <Card eyebrow="erreur">
          <p className="po2-muted-line">Suivi indisponible pour {contractLabel(selectedContract)} : {errorMessage(suivi.error)}</p>
        </Card>
      ) : null}
      {selectedContract && suivi.isFetching && !suivi.data ? (
        <p className="po2-muted-line">Chargement du suivi {contractLabel(selectedContract)}...</p>
      ) : null}

      {selectedContract && suivi.data ? (
        <>
          <div className="po2-kpi-grid">
            <KpiCard label="Budget total" value={eur(suivi.data.total_budget)} detail={`${year} - ${contractLabel(selectedContract)}`} />
            <KpiCard label="Réalisé à date" value={eur(suivi.data.total_realized)} detail={`${suivi.data.snapshots_included} facture(s) figée(s) incluse(s)`} />
            <KpiCard
              label="Atterrissage (pro-rata)"
              value={eur(suivi.data.total_landing)}
              detail={`${suivi.data.year_progress_percent.toFixed(0)}% de l'année écoulée`}
            />
            <KpiCard
              label="Écart au budget"
              value={eur(suivi.data.total_budget - suivi.data.total_landing)}
              tone={suivi.data.total_budget - suivi.data.total_landing < 0 ? "danger" : "good"}
              detail="budget - atterrissage"
            />
          </div>

          {suivi.data.snapshots_excluded_unknown_year > 0 ? (
            <Card eyebrow="fiabilité des données">
              <p className="po2-muted-line">{suivi.data.data_completeness_note}</p>
            </Card>
          ) : null}

          <Card
            title={`Saisie du budget ${contractLabel(selectedContract)}`}
            eyebrow={canWrite ? `étape 1 - une ligne par opération pour ${year}` : "lecture seule"}
          >
            {!canWrite ? (
              <p className="po2-muted-line">Ton rôle actuel ne permet pas de modifier le budget. Les profils Fluides et Technicien CVC restent volontairement exclus.</p>
            ) : (
              <div className="po2-matrix-import-form">
                <label>
                  <span>Opération</span>
                  <input type="text" value={newOperation} onChange={(e) => setNewOperation(e.currentTarget.value)} placeholder="ex: OP-2026-014" />
                </label>
                <label>
                  <span>Libellé</span>
                  <input type="text" value={newLabel} onChange={(e) => setNewLabel(e.currentTarget.value)} placeholder="optionnel" />
                </label>
                <label>
                  <span>Budget annuel (€)</span>
                  <input type="number" value={newAmount} onChange={(e) => setNewAmount(e.currentTarget.value)} placeholder="0" />
                </label>
                <Button variant="secondary" onClick={handleAddLine} disabled={!newOperation.trim() || createLine.isPending}>
                  {createLine.isPending ? "Ajout..." : "Ajouter la ligne"}
                </Button>
              </div>
            )}
            {createLine.isError ? <p className="po2-muted-line">Ajout impossible : {errorMessage(createLine.error)}</p> : null}

            {budgetLines.data && budgetLines.data.length > 0 ? (
              <DataTable
                rows={budgetLines.data}
                getRowKey={(l) => l.id}
                columns={[
                  { key: "operation", header: "Opération", render: (l) => l.operation_number },
                  { key: "label", header: "Libellé", render: (l) => l.label ?? "-" },
                  {
                    key: "amount",
                    header: "Budget",
                    render: (l) =>
                      canWrite ? (
                        <input
                          type="number"
                          className="po2-inline-number-input"
                          defaultValue={l.amount_budget}
                          onBlur={(event) => {
                            const value = Number(event.currentTarget.value);
                            if (!Number.isNaN(value) && value !== l.amount_budget) {
                              updateLine.mutate({ lineId: l.id, payload: { amount_budget: value } });
                            }
                          }}
                        />
                      ) : (
                        eur(l.amount_budget)
                      ),
                  },
                  {
                    key: "actions",
                    header: "",
                    render: (l) =>
                      canWrite ? (
                        <Button variant="ghost" onClick={() => deleteLine.mutate(l.id)} disabled={deleteLine.isPending}>
                          Supprimer
                        </Button>
                      ) : null,
                  },
                ]}
              />
            ) : (
              <p className="po2-muted-line">Aucune ligne de budget saisie pour {year} : ajoute la première ligne ci-dessus.</p>
            )}
          </Card>

          <Card title="Suivi par opération" eyebrow="étape 2 - budget vs réalisé vs atterrissage">
            {suiviRows.length === 0 ? (
              <p className="po2-muted-line">Aucune opération budgétée ni facture rattachée pour {year} : commence par la saisie ci-dessus.</p>
            ) : (
              <DataTable
                rows={suiviRows}
                getRowKey={(r) => r.operation_number}
                columns={[
                  { key: "operation", header: "Opération", render: (r) => <strong>{r.operation_number}</strong> },
                  { key: "budget", header: "Budget", render: (r) => eur(r.amount_budget) },
                  { key: "realized", header: "Réalisé", render: (r) => eur(r.amount_realized) },
                  { key: "landing", header: "Atterrissage", render: (r) => eur(r.amount_landing) },
                  {
                    key: "variance",
                    header: "Écart",
                    render: (r) => <StatusBadge tone={varianceTone(r.variance_to_budget)}>{eur(r.variance_to_budget)}</StatusBadge>,
                  },
                ]}
              />
            )}
            {suivi.data.unassigned_realized_amount > 0 ? (
              <p className="po2-muted-line">
                {eur(suivi.data.unassigned_realized_amount)} de réalisé sans opération rattachée (règle de matrice à compléter).
              </p>
            ) : null}
          </Card>
        </>
      ) : null}
    </div>
      )}
    </>
  );
}
