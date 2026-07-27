import { useMemo, useRef, useState, type ReactNode } from "react";
import { Button, Card, DataTable, Drawer, FilterBar, KpiCard, SegmentControl, StatusBadge } from "../../design-system";
import type {
  CpeAccountingNatureRule,
  CpeAccountingSiteMapping,
  EnergyAccountingNatureRule,
  EnergyAccountingSiteMapping,
} from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";
import {
  useBootstrapEnergySites,
  useCpeNatureRules,
  useCpeSiteMappings,
  useDeleteCpeNatureRule,
  useDeleteCpeSiteMapping,
  useDeleteEnergyNatureRule,
  useDeleteEnergySiteMapping,
  useEnergyNatureRules,
  useEnergySiteMappings,
  useExportCpeCodification,
  useImportCpeCodification,
  useSaveCpeNatureRule,
  useSaveCpeSiteMapping,
  useSaveEnergyNatureRule,
  useSaveEnergySiteMapping,
} from "./useCodificationV1";

const WRITE_DENIED_ROLES = new Set(["FLUIDES", "FLUIDE", "RESPONSABLE_FLUIDES", "TECHNICIEN_CVC", "TECHNICIEN CVC"]);
const WRITE_ALLOWED_ROLES = new Set([
  "ADMIN", "SUPERADMIN", "DIRECTION", "RESPONSABLE_MAINTENANCE", "RESPONSABLE MAINTENANCE",
  "PATRIMOINE", "FINANCE", "COMPTA", "COMPTABILITE",
]);

function normalizeRole(role: string | undefined) {
  return (role ?? "").trim().toUpperCase().replace("-", "_");
}
function canWriteCodification(role: string | undefined) {
  const r = normalizeRole(role);
  return WRITE_ALLOWED_ROLES.has(r) && !WRITE_DENIED_ROLES.has(r);
}
function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Une erreur est survenue.";
}

type FormValues = Record<string, string | boolean>;
type FieldDef = { key: string; label: string; required?: boolean; kind?: "text" | "bool"; help?: string };
type Column<T> = { key: string; header: string; render: (row: T) => ReactNode; sortValue?: (row: T) => string | number | null | undefined };

function s(v: string | boolean | undefined): string | null {
  if (typeof v !== "string") return null;
  const t = v.trim();
  return t === "" ? null : t;
}

// ----------------------------------------------------------------------------
// Section generique : table + drawer d'edition, pour un jeu de codification.
// ----------------------------------------------------------------------------
function CodifSection<T extends { id: number }, P>({
  eyebrow, description, rows, isFetching, isError, canWrite, columns, fields, newLabel,
  searchText, toForm, emptyForm, buildPayload, onSave, savePending, onDelete, deletePending,
  headerAction,
}: {
  eyebrow: string;
  description: string;
  rows: T[];
  isFetching: boolean;
  isError: boolean;
  canWrite: boolean;
  columns: Column<T>[];
  fields: FieldDef[];
  newLabel: string;
  searchText: (row: T) => string;
  toForm: (row: T) => FormValues;
  emptyForm: FormValues;
  buildPayload: (values: FormValues, editing: T | null) => P;
  onSave: (payload: P) => void;
  savePending: boolean;
  onDelete: (id: number) => void;
  deletePending: boolean;
  headerAction?: ReactNode;
}) {
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<T | null | undefined>(undefined); // undefined = ferme, null = creation
  const [values, setValues] = useState<FormValues>(emptyForm);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => searchText(r).toLowerCase().includes(q));
  }, [query, rows, searchText]);

  function openNew() {
    setValues(emptyForm);
    setEditing(null);
  }
  function openEdit(row: T) {
    setValues(toForm(row));
    setEditing(row);
  }
  function close() {
    setEditing(undefined);
  }
  function submit() {
    onSave(buildPayload(values, editing ?? null));
    close();
  }

  const missingRequired = fields.some((f) => f.required && !s(values[f.key]));

  return (
    <Card
      title={eyebrow}
      eyebrow={isError ? "API indisponible" : isFetching ? "Synchronisation API" : `${rows.length} ligne(s)`}
      action={
        <div style={{ display: "flex", gap: ".5rem", alignItems: "center" }}>
          {headerAction}
          {canWrite ? <Button onClick={openNew}>{newLabel}</Button> : null}
        </div>
      }
    >
      <p className="po2-muted-line">{description}</p>
      {!canWrite ? <p className="po2-muted-line">Lecture seule : ton rôle ne permet pas de modifier la codification.</p> : null}
      {isError ? <p className="po2-muted-line">API indisponible : vérifie le backend ou les migrations.</p> : null}
      <FilterBar searchPlaceholder="Rechercher…" searchValue={query} onSearchChange={setQuery} />
      {filtered.length === 0 && !isFetching ? (
        <p className="po2-muted-line">Aucune ligne. {canWrite ? "Importe le classeur ou ajoute une entrée." : ""}</p>
      ) : (
        <DataTable
          rows={filtered}
          getRowKey={(r) => r.id}
          onRowClick={canWrite ? openEdit : undefined}
          columns={columns}
        />
      )}

      <Drawer
        open={editing !== undefined}
        title={editing ? "Modifier la codification" : "Nouvelle codification"}
        eyebrow={eyebrow}
        wide
        onClose={close}
        footer={
          <div style={{ display: "flex", justifyContent: "space-between", width: "100%", gap: ".5rem" }}>
            {editing ? (
              <Button
                variant="ghost"
                disabled={deletePending}
                onClick={() => {
                  onDelete(editing.id);
                  close();
                }}
              >
                {deletePending ? "Suppression…" : "Supprimer"}
              </Button>
            ) : <span />}
            <div style={{ display: "flex", gap: ".5rem" }}>
              <Button variant="ghost" onClick={close}>Annuler</Button>
              <Button disabled={savePending || missingRequired} onClick={submit}>
                {savePending ? "Enregistrement…" : "Enregistrer"}
              </Button>
            </div>
          </div>
        }
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: ".75rem 1rem" }}>
          {fields.map((f) =>
            f.kind === "bool" ? (
              <label key={f.key} style={{ display: "flex", alignItems: "center", gap: ".5rem", fontSize: ".85rem" }}>
                <input
                  type="checkbox"
                  checked={Boolean(values[f.key])}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.currentTarget.checked }))}
                />
                {f.label}
              </label>
            ) : (
              <label key={f.key} style={{ display: "flex", flexDirection: "column", gap: ".2rem", fontSize: ".8rem" }}>
                <span>
                  {f.label}
                  {f.required ? <span style={{ color: "#b91c1c" }}> *</span> : null}
                </span>
                <input
                  type="text"
                  value={typeof values[f.key] === "string" ? (values[f.key] as string) : ""}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.currentTarget.value }))}
                  style={{ padding: ".4rem .5rem", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: ".85rem" }}
                />
                {f.help ? <small className="po2-muted-line">{f.help}</small> : null}
              </label>
            ),
          )}
        </div>
      </Drawer>
    </Card>
  );
}

// ----------------------------------------------------------------------------
// Boutons d'import (haut de section).
// ----------------------------------------------------------------------------
function ImportButton({ label, accept, pending, onFile }: { label: string; accept: string; pending: boolean; onFile: (file: File) => void }) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <>
      <input
        ref={ref}
        type="file"
        accept={accept}
        style={{ display: "none" }}
        onChange={(e) => {
          const f = e.currentTarget.files?.[0];
          if (f) onFile(f);
          e.currentTarget.value = "";
        }}
      />
      <Button variant="ghost" disabled={pending} onClick={() => ref.current?.click()}>
        {pending ? "Import…" : label}
      </Button>
    </>
  );
}

// ----------------------------------------------------------------------------
type TierKey = "dalkia" | "energie";
type ViewKey = "sites" | "postes";

export function MatrixCodificationPageV1() {
  const { user } = useAuth();
  const canWrite = canWriteCodification(user?.role);
  const [tier, setTier] = useState<TierKey>("dalkia");
  const [view, setView] = useState<ViewKey>("sites");

  const cpeSites = useCpeSiteMappings();
  const cpeNatures = useCpeNatureRules();
  const energySites = useEnergySiteMappings();
  const energyNatures = useEnergyNatureRules();

  const saveCpeSite = useSaveCpeSiteMapping();
  const deleteCpeSite = useDeleteCpeSiteMapping();
  const saveCpeNature = useSaveCpeNatureRule();
  const deleteCpeNature = useDeleteCpeNatureRule();
  const saveEnergySite = useSaveEnergySiteMapping();
  const deleteEnergySite = useDeleteEnergySiteMapping();
  const saveEnergyNature = useSaveEnergyNatureRule();
  const deleteEnergyNature = useDeleteEnergyNatureRule();

  const importCpe = useImportCpeCodification();
  const exportCpe = useExportCpeCodification();
  const bootstrapEnergy = useBootstrapEnergySites();

  const activeTone = (active: boolean) => (active ? <StatusBadge tone="ok">actif</StatusBadge> : <StatusBadge tone="neutral">inactif</StatusBadge>);

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">Codification comptable — matrice de rapprochement</span>
        <h1>Lier chaque élément facturé à l'écriture comptable Ville</h1>
        <p>
          Cette matrice pilote directement le rapport de contrôle comptable : elle associe chaque site/point et chaque
          poste facturé à sa codification Ville (service, fonction, nature, opération si investissement, antenne).
          Édition en direct et import du classeur de codification.
        </p>
      </header>

      <div className="po2-kpi-grid">
        <KpiCard label="Sites DALKIA" value={String(cpeSites.data?.length ?? 0)} detail="Sites → codes" />
        <KpiCard label="Postes DALKIA" value={String(cpeNatures.data?.length ?? 0)} detail="Poste → nature" />
        <KpiCard label="Points ENGIE/EDF" value={String(energySites.data?.length ?? 0)} detail="PRM → codes" />
        <KpiCard label="Postes ENGIE/EDF" value={String(energyNatures.data?.length ?? 0)} detail="Poste → nature" />
      </div>

      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
        <SegmentControl
          value={tier}
          onChange={(v) => setTier(v)}
          options={[
            { value: "dalkia", label: "DALKIA (CPE)" },
            { value: "energie", label: "ENGIE / EDF (fluides)" },
          ]}
        />
        <SegmentControl
          value={view}
          onChange={(v) => setView(v)}
          options={[
            { value: "sites", label: tier === "dalkia" ? "Sites → codes" : "Points (PRM) → codes" },
            { value: "postes", label: "Postes → nature" },
          ]}
        />
      </div>

      {/* DALKIA — Sites */}
      {tier === "dalkia" && view === "sites" ? (
        <CodifSection<CpeAccountingSiteMapping, Partial<CpeAccountingSiteMapping> & { id?: number; code_site: string; site_name: string }>
          eyebrow="DALKIA — Sites vers codes"
          description="Un site DALKIA (code_site) porte les axes analytiques Ville. L'opération n'est utilisée par le rapport que pour un poste P3/P3.4."
          rows={cpeSites.data ?? []}
          isFetching={cpeSites.isFetching}
          isError={cpeSites.isError}
          canWrite={canWrite}
          newLabel="Nouveau site"
          headerAction={
            <>
              <Button variant="ghost" disabled={exportCpe.isPending} onClick={() => exportCpe.mutate()}>
                {exportCpe.isPending ? "Export…" : "Exporter (gabarit finance)"}
              </Button>
              {canWrite ? <ImportButton label="Importer (V2 ou gabarit finance)" accept=".xlsx" pending={importCpe.isPending} onFile={(f) => importCpe.mutate(f)} /> : null}
            </>
          }
          searchText={(r) => `${r.code_site} ${r.site_name} ${r.service_code ?? ""} ${r.antenna_code ?? ""} ${r.function_code ?? ""}`}
          columns={[
            { key: "code_site", header: "Code site", render: (r) => <strong>{r.code_site}</strong>, sortValue: (r) => r.code_site },
            { key: "site_name", header: "Désignation", render: (r) => r.site_name, sortValue: (r) => r.site_name },
            { key: "service", header: "Service", render: (r) => r.service_code ?? "—", sortValue: (r) => r.service_code },
            { key: "function", header: "Fonction", render: (r) => r.function_code ?? "—", sortValue: (r) => r.function_code },
            { key: "antenna", header: "Antenne", render: (r) => r.antenna_code ?? "—", sortValue: (r) => r.antenna_code },
            { key: "operation", header: "Opération", render: (r) => r.operation_code ?? "—", sortValue: (r) => r.operation_code },
            { key: "active", header: "Statut", render: (r) => activeTone(r.active) },
          ]}
          fields={[
            { key: "code_site", label: "Code site", required: true },
            { key: "site_name", label: "Désignation", required: true },
            { key: "family", label: "Famille" },
            { key: "manager", label: "Gestionnaire" },
            { key: "alternate_manager", label: "Gestionnaire suppléant" },
            { key: "service_code", label: "Service (code)" },
            { key: "service_label", label: "Service (libellé)" },
            { key: "function_code", label: "Fonction (code)" },
            { key: "function_label", label: "Fonction (libellé)" },
            { key: "antenna_code", label: "Antenne (code)" },
            { key: "antenna_label", label: "Antenne (libellé)" },
            { key: "operation_code", label: "Opération (P3 uniquement)", help: "Utilisé par le rapport seulement pour un poste P3/P3.4." },
            { key: "operation_label", label: "Opération (libellé)" },
            { key: "notes", label: "Notes" },
            { key: "active", label: "Actif", kind: "bool" },
          ]}
          emptyForm={{ active: true }}
          toForm={(r) => ({
            code_site: r.code_site ?? "", site_name: r.site_name ?? "", family: r.family ?? "", manager: r.manager ?? "",
            alternate_manager: r.alternate_manager ?? "", service_code: r.service_code ?? "", service_label: r.service_label ?? "",
            function_code: r.function_code ?? "", function_label: r.function_label ?? "", antenna_code: r.antenna_code ?? "",
            antenna_label: r.antenna_label ?? "", operation_code: r.operation_code ?? "", operation_label: r.operation_label ?? "",
            notes: r.notes ?? "", active: r.active,
          })}
          buildPayload={(v, editing) => ({
            id: editing?.id, code_site: s(v.code_site) ?? "", site_name: s(v.site_name) ?? "",
            family: s(v.family), manager: s(v.manager), alternate_manager: s(v.alternate_manager),
            service_code: s(v.service_code), service_label: s(v.service_label), function_code: s(v.function_code),
            function_label: s(v.function_label), antenna_code: s(v.antenna_code), antenna_label: s(v.antenna_label),
            operation_code: s(v.operation_code), operation_label: s(v.operation_label), notes: s(v.notes),
            active: Boolean(v.active),
          })}
          onSave={(p) => saveCpeSite.mutate(p)}
          savePending={saveCpeSite.isPending}
          onDelete={(id) => deleteCpeSite.mutate(id)}
          deletePending={deleteCpeSite.isPending}
        />
      ) : null}

      {/* DALKIA — Postes */}
      {tier === "dalkia" && view === "postes" ? (
        <CodifSection<CpeAccountingNatureRule, Partial<CpeAccountingNatureRule> & { id?: number; market: string; billed_item: string; accounting_nature: string }>
          eyebrow="DALKIA — Poste facturé vers nature"
          description="Marché Ville EN COURS uniquement (contrats C00190116O / C00190155J). Chaque poste facturé (P1/P2/P3…) est rattaché à une nature comptable."
          rows={cpeNatures.data ?? []}
          isFetching={cpeNatures.isFetching}
          isError={cpeNatures.isError}
          canWrite={canWrite}
          newLabel="Nouvelle règle"
          headerAction={
            <>
              <Button variant="ghost" disabled={exportCpe.isPending} onClick={() => exportCpe.mutate()}>
                {exportCpe.isPending ? "Export…" : "Exporter (gabarit finance)"}
              </Button>
              {canWrite ? <ImportButton label="Importer (V2 ou gabarit finance)" accept=".xlsx" pending={importCpe.isPending} onFile={(f) => importCpe.mutate(f)} /> : null}
            </>
          }
          searchText={(r) => `${r.contract_code ?? ""} ${r.market} ${r.service_sold ?? ""} ${r.billed_item} ${r.accounting_nature}`}
          columns={[
            { key: "contract", header: "Contrat", render: (r) => r.contract_code ?? "—", sortValue: (r) => r.contract_code },
            { key: "market", header: "Marché", render: (r) => r.market, sortValue: (r) => r.market },
            { key: "billed_item", header: "Poste facturé", render: (r) => <strong>{r.billed_item}</strong>, sortValue: (r) => r.billed_item },
            { key: "service_sold", header: "Service vendu", render: (r) => r.service_sold ?? "—", sortValue: (r) => r.service_sold },
            { key: "frequency", header: "Fréquence", render: (r) => r.frequency ?? "—", sortValue: (r) => r.frequency },
            { key: "nature", header: "Nature", render: (r) => <strong>{r.accounting_nature}</strong>, sortValue: (r) => r.accounting_nature },
            { key: "active", header: "Statut", render: (r) => activeTone(r.active) },
          ]}
          fields={[
            { key: "contract_code", label: "Code contrat" },
            { key: "market", label: "Marché", required: true },
            { key: "service_sold", label: "Service vendu" },
            { key: "billed_item", label: "Poste facturé", required: true },
            { key: "frequency", label: "Fréquence" },
            { key: "accounting_nature", label: "Nature comptable", required: true },
            { key: "accounting_label", label: "Libellé nature" },
            { key: "notes", label: "Notes" },
            { key: "active", label: "Actif", kind: "bool" },
          ]}
          emptyForm={{ active: true, market: "" }}
          toForm={(r) => ({
            contract_code: r.contract_code ?? "", market: r.market ?? "", service_sold: r.service_sold ?? "",
            billed_item: r.billed_item ?? "", frequency: r.frequency ?? "", accounting_nature: r.accounting_nature ?? "",
            accounting_label: r.accounting_label ?? "", notes: r.notes ?? "", active: r.active,
          })}
          buildPayload={(v, editing) => ({
            id: editing?.id, contract_code: s(v.contract_code), market: s(v.market) ?? "",
            service_sold: s(v.service_sold), billed_item: s(v.billed_item) ?? "", frequency: s(v.frequency),
            accounting_nature: s(v.accounting_nature) ?? "", accounting_label: s(v.accounting_label),
            notes: s(v.notes), active: Boolean(v.active),
          })}
          onSave={(p) => saveCpeNature.mutate(p)}
          savePending={saveCpeNature.isPending}
          onDelete={(id) => deleteCpeNature.mutate(id)}
          deletePending={deleteCpeNature.isPending}
        />
      ) : null}

      {/* ENERGIE — Sites (PRM) */}
      {tier === "energie" && view === "sites" ? (
        <CodifSection<EnergyAccountingSiteMapping, Partial<EnergyAccountingSiteMapping> & { id?: number; prm_id: string }>
          eyebrow="ENGIE / EDF — Points (PRM) vers codes"
          description="Chaque PRM porte les axes Ville. Attention : l'enregistrement remplace tous les champs du point (édition complète)."
          rows={energySites.data ?? []}
          isFetching={energySites.isFetching}
          isError={energySites.isError}
          canWrite={canWrite}
          newLabel="Nouveau point"
          headerAction={canWrite ? <Button variant="ghost" disabled={bootstrapEnergy.isPending} onClick={() => bootstrapEnergy.mutate()}>{bootstrapEnergy.isPending ? "Génération…" : "Générer les PRM depuis les factures"}</Button> : undefined}
          searchText={(r) => `${r.prm_id} ${r.site_name ?? ""} ${r.service_code ?? ""} ${r.antenna_code ?? ""}`}
          columns={[
            { key: "prm_id", header: "PRM", render: (r) => <strong>{r.prm_id}</strong>, sortValue: (r) => r.prm_id },
            { key: "site_name", header: "Désignation", render: (r) => r.site_name ?? "—", sortValue: (r) => r.site_name },
            { key: "service", header: "Service", render: (r) => r.service_code ?? "—", sortValue: (r) => r.service_code },
            { key: "function", header: "Fonction", render: (r) => r.function_code ?? "—", sortValue: (r) => r.function_code },
            { key: "antenna", header: "Antenne", render: (r) => r.antenna_code ?? "—", sortValue: (r) => r.antenna_code },
            { key: "active", header: "Statut", render: (r) => activeTone(r.active) },
          ]}
          fields={[
            { key: "prm_id", label: "PRM", required: true },
            { key: "site_name", label: "Désignation" },
            { key: "regroupement", label: "Regroupement" },
            { key: "manager", label: "Gestionnaire" },
            { key: "service_code", label: "Service (code)" },
            { key: "service_label", label: "Service (libellé)" },
            { key: "function_code", label: "Fonction (code)" },
            { key: "function_label", label: "Fonction (libellé)" },
            { key: "antenna_code", label: "Antenne (code)" },
            { key: "antenna_label", label: "Antenne (libellé)" },
            { key: "operation_code", label: "Opération" },
            { key: "operation_label", label: "Opération (libellé)" },
            { key: "notes", label: "Notes" },
            { key: "active", label: "Actif", kind: "bool" },
          ]}
          emptyForm={{ active: true }}
          toForm={(r) => ({
            prm_id: r.prm_id ?? "", site_name: r.site_name ?? "", regroupement: r.regroupement ?? "", manager: r.manager ?? "",
            service_code: r.service_code ?? "", service_label: r.service_label ?? "", function_code: r.function_code ?? "",
            function_label: r.function_label ?? "", antenna_code: r.antenna_code ?? "", antenna_label: r.antenna_label ?? "",
            operation_code: r.operation_code ?? "", operation_label: r.operation_label ?? "", notes: r.notes ?? "", active: r.active,
          })}
          buildPayload={(v, editing) => ({
            id: editing?.id, prm_id: s(v.prm_id) ?? "", site_name: s(v.site_name), regroupement: s(v.regroupement),
            manager: s(v.manager), service_code: s(v.service_code), service_label: s(v.service_label),
            function_code: s(v.function_code), function_label: s(v.function_label), antenna_code: s(v.antenna_code),
            antenna_label: s(v.antenna_label), operation_code: s(v.operation_code), operation_label: s(v.operation_label),
            notes: s(v.notes), active: Boolean(v.active),
          })}
          onSave={(p) => saveEnergySite.mutate(p)}
          savePending={saveEnergySite.isPending}
          onDelete={(id) => deleteEnergySite.mutate(id)}
          deletePending={deleteEnergySite.isPending}
        />
      ) : null}

      {/* ENERGIE — Postes */}
      {tier === "energie" && view === "postes" ? (
        <CodifSection<EnergyAccountingNatureRule, Partial<EnergyAccountingNatureRule> & { id?: number; billed_item: string; accounting_nature: string }>
          eyebrow="ENGIE / EDF — Poste facturé vers nature"
          description="Postes élec (abonnement / consommation / acheminement / taxes) rattachés à leur nature comptable (souvent 60612)."
          rows={energyNatures.data ?? []}
          isFetching={energyNatures.isFetching}
          isError={energyNatures.isError}
          canWrite={canWrite}
          newLabel="Nouvelle règle"
          searchText={(r) => `${r.supplier} ${r.market ?? ""} ${r.billed_item} ${r.accounting_nature}`}
          columns={[
            { key: "supplier", header: "Fournisseur", render: (r) => r.supplier, sortValue: (r) => r.supplier },
            { key: "market", header: "Marché", render: (r) => r.market ?? "—", sortValue: (r) => r.market },
            { key: "billed_item", header: "Poste facturé", render: (r) => <strong>{r.billed_item}</strong>, sortValue: (r) => r.billed_item },
            { key: "frequency", header: "Fréquence", render: (r) => r.frequency ?? "—", sortValue: (r) => r.frequency },
            { key: "nature", header: "Nature", render: (r) => <strong>{r.accounting_nature}</strong>, sortValue: (r) => r.accounting_nature },
            { key: "active", header: "Statut", render: (r) => activeTone(r.active) },
          ]}
          fields={[
            { key: "supplier", label: "Fournisseur", required: true },
            { key: "market", label: "Marché" },
            { key: "billed_item", label: "Poste facturé", required: true },
            { key: "frequency", label: "Fréquence" },
            { key: "accounting_nature", label: "Nature comptable", required: true },
            { key: "accounting_label", label: "Libellé nature" },
            { key: "notes", label: "Notes" },
            { key: "active", label: "Actif", kind: "bool" },
          ]}
          emptyForm={{ active: true, supplier: "ENGIE" }}
          toForm={(r) => ({
            supplier: r.supplier ?? "", market: r.market ?? "", billed_item: r.billed_item ?? "", frequency: r.frequency ?? "",
            accounting_nature: r.accounting_nature ?? "", accounting_label: r.accounting_label ?? "", notes: r.notes ?? "", active: r.active,
          })}
          buildPayload={(v, editing) => ({
            id: editing?.id, supplier: s(v.supplier) ?? "ENGIE", market: s(v.market), billed_item: s(v.billed_item) ?? "",
            frequency: s(v.frequency), accounting_nature: s(v.accounting_nature) ?? "", accounting_label: s(v.accounting_label),
            notes: s(v.notes), active: Boolean(v.active),
          })}
          onSave={(p) => saveEnergyNature.mutate(p)}
          savePending={saveEnergyNature.isPending}
          onDelete={(id) => deleteEnergyNature.mutate(id)}
          deletePending={deleteEnergyNature.isPending}
        />
      ) : null}

      {(importCpe.isSuccess || importCpe.isError || bootstrapEnergy.isSuccess) ? (
        <Card title="Dernière opération d'import" eyebrow="journal">
          {importCpe.isSuccess ? (
            <p className="po2-muted-line">
              Classeur DALKIA importé : {importCpe.data.site_mappings_created} site(s) créé(s), {importCpe.data.site_mappings_updated} mis à jour ;
              {" "}{importCpe.data.nature_rules_created} règle(s) créée(s), {importCpe.data.nature_rules_updated} mise(s) à jour.
            </p>
          ) : null}
          {importCpe.isError ? <p className="po2-muted-line">Import DALKIA impossible : {errorMessage(importCpe.error)}</p> : null}
          {bootstrapEnergy.isSuccess ? (
            <p className="po2-muted-line">PRM générés : {bootstrapEnergy.data.created} créé(s), {bootstrapEnergy.data.existing} déjà présent(s).</p>
          ) : null}
        </Card>
      ) : null}
    </div>
  );
}
