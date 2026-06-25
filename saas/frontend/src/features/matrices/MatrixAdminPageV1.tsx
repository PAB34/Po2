import { useMemo, useState } from "react";
import { Button, Card, DataTable, Drawer, FilterBar, KpiCard, StatusBadge } from "../../design-system";
import type { AccountingMatrixContractV1, AccountingMatrixVersionV1 } from "../../lib/api";
import {
  useMatrixContractDetailV1,
  useMatrixContractsV1,
  useMatrixVersionRulesV1,
  useSeedMatricesV1,
} from "./useMatricesV1";

function versionTone(status: string) {
  if (status === "active") return "ok" as const;
  if (status === "candidate") return "warn" as const;
  if (status === "archived") return "neutral" as const;
  return "info" as const; // draft
}

export function MatrixAdminPageV1() {
  const [query, setQuery] = useState("");
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);

  const { data: contracts = [], isFetching, isError } = useMatrixContractsV1();
  const detail = useMatrixContractDetailV1(selectedContractId);
  const rules = useMatrixVersionRulesV1(selectedVersionId);
  const seed = useSeedMatricesV1();

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return contracts;
    return contracts.filter((c) => `${c.supplier} ${c.contract_code ?? ""} ${c.contract_label ?? ""} ${c.domain}`.toLowerCase().includes(q));
  }, [query, contracts]);

  const activeVersions = contracts.filter((c) => c.active_version_id != null).length;

  function openContract(contract: AccountingMatrixContractV1) {
    setSelectedContractId(contract.id);
    setSelectedVersionId(contract.active_version_id);
  }
  function closeDrawer() {
    setSelectedContractId(null);
    setSelectedVersionId(null);
  }

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">Matrices comptables · référentiel versionné</span>
        <h1>Matrices comptables par contrat</h1>
        <p>Référentiel versionné branché sur l’API <code>/api/accounting-matrices</code> : contrats, versions datées, règles et snapshots immuables.</p>
      </header>

      <div className="po2-kpi-grid">
        <KpiCard label="Contrats matrices" value={String(contracts.length)} detail={isFetching ? "synchronisation…" : "depuis l’API"} />
        <KpiCard label="Versions actives" value={String(activeVersions)} detail="une seule version active par contrat" />
        <KpiCard label="Source" value={isError ? "indisponible" : "API"} detail="données réelles, pas de mock" tone={isError ? "warning" : undefined} />
      </div>

      <Card
        title="Contrats matrices"
        eyebrow={isError ? "API indisponible" : isFetching ? "Synchronisation API" : "Données API"}
        action={
          <Button variant="ghost" onClick={() => seed.mutate()} disabled={seed.isPending}>
            {seed.isPending ? "Seed en cours…" : "Seed depuis l’existant"}
          </Button>
        }
      >
        {seed.isSuccess ? (
          <p className="po2-muted-line">
            Seed terminé : {seed.data.versions_created} version(s) créée(s) — énergie {seed.data.energy.contracts_created}, CPE {seed.data.cpe.contracts_created}.
          </p>
        ) : null}
        {contracts.length === 0 && !isFetching ? (
          <p className="po2-muted-line">Aucune matrice. Lance « Seed depuis l’existant » pour générer les matrices à partir des codifications énergie/CPE.</p>
        ) : (
          <>
            <FilterBar searchPlaceholder="Fournisseur, contrat ou domaine" searchValue={query} onSearchChange={setQuery} />
            <DataTable
              rows={rows}
              getRowKey={(c) => c.id}
              onRowClick={openContract}
              columns={[
                { key: "domain", header: "Domaine", render: (c) => c.domain },
                { key: "supplier", header: "Fournisseur", render: (c) => <strong>{c.supplier}</strong> },
                { key: "contract", header: "Contrat / lot", render: (c) => <span>{c.contract_code ?? "—"}<small className="po2-muted-line">{c.contract_label ?? ""}</small></span> },
                { key: "versions", header: "Versions", render: (c) => String(c.versions_count) },
                { key: "active", header: "Version active", render: (c) => c.active_version_label ? <StatusBadge tone="ok">{c.active_version_label}</StatusBadge> : <StatusBadge tone="info">aucune active</StatusBadge> },
              ]}
            />
          </>
        )}
      </Card>

      <Drawer
        open={selectedContractId != null}
        title={detail.data ? `${detail.data.supplier} · ${detail.data.contract_code ?? "contrat"}` : "Matrice"}
        eyebrow="Détail matrice"
        description={detail.data?.contract_label ?? undefined}
        onClose={closeDrawer}
      >
        {detail.isFetching ? <p className="po2-muted-line">Chargement…</p> : null}
        {detail.data ? (
          <div className="po2-invoice-proof">
            <Card title="Versions" eyebrow="Cliquer pour voir les règles">
              <div className="po2-decision-list">
                {detail.data.versions.map((v: AccountingMatrixVersionV1) => (
                  <button
                    key={v.id}
                    type="button"
                    className={selectedVersionId === v.id ? "po2-decision-item po2-decision-item--active" : "po2-decision-item"}
                    onClick={() => setSelectedVersionId(v.id)}
                  >
                    <StatusBadge tone={versionTone(v.status)}>{v.status}</StatusBadge>
                    <strong>{v.version_label}</strong>
                    <small>{v.rules_count} règles · source {v.source}</small>
                  </button>
                ))}
              </div>
            </Card>
            <Card title="Règles de la version" eyebrow={selectedVersionId ? `Version #${selectedVersionId}` : "Sélectionner une version"}>
              {selectedVersionId == null ? (
                <p className="po2-muted-line">Choisis une version ci-dessus.</p>
              ) : rules.isFetching ? (
                <p className="po2-muted-line">Chargement des règles…</p>
              ) : (
                <DataTable
                  rows={rules.data ?? []}
                  getRowKey={(r) => r.id}
                  columns={[
                    { key: "key", header: "Clé stable", render: (r) => <small>{r.stable_rule_key}</small> },
                    { key: "scope", header: "Scope", render: (r) => r.scope },
                    { key: "item", header: "Poste / périmètre", render: (r) => r.billed_item_pattern ?? r.site_code ?? r.meter_id ?? "—" },
                    { key: "nature", header: "Nature", render: (r) => <strong>{r.accounting_nature ?? "—"}</strong> },
                    { key: "alloc", header: "%", render: (r) => `${r.allocation_percent}` },
                  ]}
                />
              )}
            </Card>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
