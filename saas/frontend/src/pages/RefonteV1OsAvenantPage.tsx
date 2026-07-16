import { useEffect, useMemo, useState } from "react";
import { AppShellV1 } from "../app/AppShellV1";
import type { AppProfileV1 } from "../app/navigationV1";
import { Button, Card, DataTable, KpiCard, StatusBadge } from "../design-system";
import { useAuth } from "../providers/AuthProvider";

type ChangeKind = "add" | "remove" | "modify";

type CpeSiteOption = {
  code_site: string;
  site_name: string;
  lot: number | null;
  pce: string | null;
  tarif: string | null;
  p1_gaz_annual_ht: number;
  p1_elec_annual_ht: number;
  p2_annual_ht: number;
  p3_annual_ht: number;
  total_annual_ht: number;
};

type CpeOsAvenantImpact = {
  p1_gaz_annual_ht: number;
  p1_elec_annual_ht: number;
  p1_annual_ht: number;
  p2_annual_ht: number;
  p3_annual_ht: number;
  total_annual_ht: number;
  first_year_prorata_ht: number;
  remaining_market_ht: number;
  effective_year: number | null;
  first_year_ratio: number;
};

type CpeOsAvenantRequest = {
  id: number;
  title: string;
  change_type: string;
  status: string;
  lot: number | null;
  effective_date: string | null;
  os_number: string | null;
  avenant_number: string | null;
  created_at: string;
  impact: CpeOsAvenantImpact;
};

type OsStep = {
  label: string;
  detail: string;
  status: "done" | "active" | "next";
};

const apiBaseUrl = (import.meta as ImportMeta & { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? "/api";

const FALLBACK_SITE_OPTIONS: CpeSiteOption[] = [
  { code_site: "VDS-SPORT 02.02", site_name: "Le Barrou - Halle Louis Marty", lot: 1, pce: null, tarif: null, p1_gaz_annual_ht: 11800, p1_elec_annual_ht: 0, p2_annual_ht: 4350, p3_annual_ht: 7200, total_annual_ht: 23350 },
  { code_site: "VDS-CULT 05", site_name: "Musee Paul Valery", lot: 1, pce: null, tarif: "T2", p1_gaz_annual_ht: 15400, p1_elec_annual_ht: 0, p2_annual_ht: 5100, p3_annual_ht: 9800, total_annual_ht: 30300 },
  { code_site: "CCAS 04", site_name: "EHPAD Laurent Antoine", lot: 2, pce: null, tarif: "T3", p1_gaz_annual_ht: 22600, p1_elec_annual_ht: 0, p2_annual_ht: 6900, p3_annual_ht: 12600, total_annual_ht: 42100 },
];

const STEPS: OsStep[] = [
  { label: "Expression du besoin", detail: "La collectivite decrit l'entree, la sortie ou la modification de site.", status: "done" },
  { label: "Impact financier", detail: "Po2 chiffre l'effet annuel, le prorata et le reste du marche.", status: "active" },
  { label: "Complement DALKIA", detail: "PCE, tarif, cibles, P2/P3, date d'effet et reserves techniques.", status: "next" },
  { label: "OS de prise en charge", detail: "Generation de l'EXE1 si une execution rapide est necessaire.", status: "next" },
  { label: "Avenant EXE10", detail: "Regroupement des OS et production du dossier d'avenant.", status: "next" },
  { label: "DPGF officiel", detail: "Import du nouveau DPGF puis comparaison prevu vs reel.", status: "next" },
];

function eur(value: number): string {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value);
}

function dateValue(value: string): Date | null {
  const date = value ? new Date(`${value}T00:00:00`) : null;
  return date && Number.isFinite(date.getTime()) ? date : null;
}

function yearProgressFrom(value: string): number {
  const date = dateValue(value);
  if (!date) return 1;
  const year = date.getFullYear();
  const start = new Date(year, 0, 1).getTime();
  const end = new Date(year + 1, 0, 1).getTime();
  return Math.max(0, Math.min(1, (end - date.getTime()) / (end - start)));
}

function stepTone(status: OsStep["status"]) {
  if (status === "done") return "ok";
  if (status === "active") return "warn";
  return "neutral";
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: "Brouillon",
    sent_to_dalkia: "Envoye DALKIA",
    dalkia_completed: "Complete DALKIA",
    pending_collectivity_validation: "A valider",
    os_ready: "OS pret",
    os_signed: "OS signe",
    in_service: "Pris en charge",
    included_in_avenant: "Integre avenant",
    cancelled: "Annule",
  };
  return labels[status] ?? status;
}

function statusTone(status: string) {
  if (["os_signed", "in_service", "included_in_avenant"].includes(status)) return "ok";
  if (["sent_to_dalkia", "pending_collectivity_validation", "os_ready"].includes(status)) return "warn";
  if (status === "cancelled") return "bad";
  return "neutral";
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Erreur HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function headers(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

async function fetchSiteOptions(token: string, year: number): Promise<CpeSiteOption[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/os-avenants/sites?year=${year}`, { headers: { Authorization: `Bearer ${token}` } });
  return parseJson<CpeSiteOption[]>(response);
}

async function fetchRequests(token: string): Promise<CpeOsAvenantRequest[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/os-avenants`, { headers: { Authorization: `Bearer ${token}` } });
  return parseJson<CpeOsAvenantRequest[]>(response);
}

async function createRequest(token: string, payload: unknown): Promise<CpeOsAvenantRequest> {
  const response = await fetch(`${apiBaseUrl}/cpe/os-avenants`, { method: "POST", headers: headers(token), body: JSON.stringify(payload) });
  return parseJson<CpeOsAvenantRequest>(response);
}

export function RefonteV1OsAvenantPage() {
  const { logout, token, user } = useAuth();
  const [profile, setProfile] = useState<AppProfileV1>("direction");
  const userLabel = user ? `${user.prenom} ${user.nom}` : undefined;

  return (
    <AppShellV1 profile={profile} userLabel={userLabel} onProfileChange={setProfile} onLogout={logout} routePrefix="/refonte-v1">
      <OsAvenantWorkspace token={token} />
    </AppShellV1>
  );
}

function OsAvenantWorkspace({ token }: { token: string | null }) {
  const [kind, setKind] = useState<ChangeKind>("add");
  const [siteCode, setSiteCode] = useState(FALLBACK_SITE_OPTIONS[0].code_site);
  const [newSite, setNewSite] = useState("Nouveau site a integrer");
  const [lot, setLot] = useState<"1" | "2">("1");
  const [effectiveDate, setEffectiveDate] = useState("2026-09-01");
  const [p1, setP1] = useState(14000);
  const [p2, setP2] = useState(4800);
  const [p3, setP3] = useState(8500);
  const [siteOptions, setSiteOptions] = useState<CpeSiteOption[]>(FALLBACK_SITE_OPTIONS);
  const [requests, setRequests] = useState<CpeOsAvenantRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const year = dateValue(effectiveDate)?.getFullYear() ?? new Date().getFullYear();

  async function reload() {
    if (!token) return;
    setLoading(true);
    setMessage(null);
    try {
      const [sites, dossiers] = await Promise.all([fetchSiteOptions(token, year), fetchRequests(token)]);
      if (sites.length > 0) {
        setSiteOptions(sites);
        if (!sites.some((site) => site.code_site === siteCode)) setSiteCode(sites[0].code_site);
      }
      setRequests(dossiers);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Chargement impossible.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, year]);

  const selectedSite = siteOptions.find((site) => site.code_site === siteCode) ?? siteOptions[0] ?? FALLBACK_SITE_OPTIONS[0];
  const signedOsCount = requests.filter((request) => ["os_signed", "in_service"].includes(request.status)).length || 3;

  const impact = useMemo(() => {
    const direction = kind === "remove" ? -1 : 1;
    const base = kind === "remove"
      ? { p1: selectedSite.p1_gaz_annual_ht + selectedSite.p1_elec_annual_ht, p2: selectedSite.p2_annual_ht, p3: selectedSite.p3_annual_ht }
      : { p1, p2, p3 };
    const annual = direction * (base.p1 + base.p2 + base.p3);
    const prorata = annual * yearProgressFrom(effectiveDate);
    const remainingYears = 2033 - (dateValue(effectiveDate)?.getFullYear() ?? 2026) + yearProgressFrom(effectiveDate);
    return {
      p1: direction * base.p1,
      p2: direction * base.p2,
      p3: direction * base.p3,
      annual,
      prorata,
      remainingMarket: annual * Math.max(0, remainingYears),
    };
  }, [effectiveDate, kind, p1, p2, p3, selectedSite]);

  const rows = [
    { poste: "P1", current: kind === "remove" ? selectedSite.p1_gaz_annual_ht + selectedSite.p1_elec_annual_ht : 0, delta: impact.p1, after: kind === "remove" ? 0 : impact.p1 },
    { poste: "P2", current: kind === "remove" ? selectedSite.p2_annual_ht : 0, delta: impact.p2, after: kind === "remove" ? 0 : impact.p2 },
    { poste: "P3", current: kind === "remove" ? selectedSite.p3_annual_ht : 0, delta: impact.p3, after: kind === "remove" ? 0 : impact.p3 },
  ];

  const title = kind === "remove" ? `${selectedSite.code_site} - ${selectedSite.site_name}` : newSite;

  async function handleCreate() {
    if (!token) {
      setMessage("Authentification requise.");
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      const line = kind === "remove"
        ? {
            action: kind,
            code_site: selectedSite.code_site,
            site_name: selectedSite.site_name,
            lot: selectedSite.lot,
            pce: selectedSite.pce,
            tarif: selectedSite.tarif,
            current_p1_gaz_annual_ht: selectedSite.p1_gaz_annual_ht,
            current_p1_elec_annual_ht: selectedSite.p1_elec_annual_ht,
            current_p2_annual_ht: selectedSite.p2_annual_ht,
            current_p3_annual_ht: selectedSite.p3_annual_ht,
          }
        : {
            action: kind,
            site_name: newSite,
            lot: Number(lot),
            p1_gaz_annual_ht: p1,
            p1_elec_annual_ht: 0,
            p2_annual_ht: p2,
            p3_annual_ht: p3,
          };
      await createRequest(token, {
        title,
        change_type: kind,
        lot: kind === "remove" ? selectedSite.lot : Number(lot),
        effective_date: effectiveDate,
        reason: "Preparation avenant CPE DALKIA depuis Po2",
        lines: [line],
      });
      setMessage("Dossier cree. Il apparait dans le portefeuille ci-dessous.");
      await reload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Creation impossible.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">CPE DALKIA - OS & avenants</span>
        <h1>Preparer l'avenant, declencher l'OS seulement si besoin.</h1>
        <p>
          L'ecran part du besoin metier: ajouter, supprimer ou modifier un site, chiffrer l'impact,
          collecter les donnees DALKIA, puis produire le dossier OS/EXE10 sans alterer le DPGF officiel.
        </p>
      </header>

      <div className="po2-kpi-grid">
        <KpiCard label="Impact annuel HT" value={eur(impact.annual)} detail="Delta P1 + P2 + P3" tone={impact.annual >= 0 ? "warning" : "good"} />
        <KpiCard label="Impact prorata" value={eur(impact.prorata)} detail={`Date d'effet ${effectiveDate || "non renseignee"}`} />
        <KpiCard label="Reste marche estime" value={eur(impact.remainingMarket)} detail="Projection jusqu'en 2033" />
        <KpiCard label="OS a regrouper" value={String(signedOsCount)} detail={requests.length ? "Selon les dossiers Po2" : "A preparer dans un EXE10"} tone="info" />
      </div>

      <div className="po2-two-columns" style={{ alignItems: "start" }}>
        <Card title="Dossier d'avenant" eyebrow="Formulaire">
          <div style={{ display: "grid", gap: ".85rem" }}>
            <label className="po2-claim__field">
              <span>Type de mouvement</span>
              <select value={kind} onChange={(event) => setKind(event.target.value as ChangeKind)}>
                <option value="add">Creation / entree de site</option>
                <option value="remove">Suppression / sortie de site</option>
                <option value="modify">Modification d'un site existant</option>
              </select>
            </label>

            {kind === "remove" ? (
              <label className="po2-claim__field">
                <span>Site a supprimer</span>
                <select value={siteCode} onChange={(event) => setSiteCode(event.target.value)}>
                  {siteOptions.map((site) => (
                    <option key={site.code_site} value={site.code_site}>{site.code_site} - {site.site_name}</option>
                  ))}
                </select>
              </label>
            ) : (
              <label className="po2-claim__field">
                <span>Site concerne</span>
                <input value={newSite} onChange={(event) => setNewSite(event.target.value)} />
              </label>
            )}

            <div className="po2-contact-card__grid">
              <label className="po2-claim__field">
                <span>Lot</span>
                <select value={kind === "remove" ? String(selectedSite.lot ?? 1) : lot} disabled={kind === "remove"} onChange={(event) => setLot(event.target.value as "1" | "2")}>
                  <option value="1">Lot 1 - Ville</option>
                  <option value="2">Lot 2 - CCAS</option>
                </select>
              </label>
              <label className="po2-claim__field">
                <span>Date d'effet souhaitee</span>
                <input type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} />
              </label>
            </div>

            {kind !== "remove" ? (
              <div className="po2-contact-card__grid">
                <label className="po2-claim__field"><span>P1 annuel HT estime</span><input type="number" value={p1} onChange={(event) => setP1(Number(event.target.value))} /></label>
                <label className="po2-claim__field"><span>P2 annuel HT estime</span><input type="number" value={p2} onChange={(event) => setP2(Number(event.target.value))} /></label>
                <label className="po2-claim__field"><span>P3 annuel HT estime</span><input type="number" value={p3} onChange={(event) => setP3(Number(event.target.value))} /></label>
              </div>
            ) : null}

            <div className="po2-decision-list">
              <article className="po2-decision-item"><StatusBadge tone="warn">A completer</StatusBadge><div><strong>Donnees DALKIA requises</strong><small>PCE, tarif, cible NB, montant P2/P3, reserves techniques.</small></div></article>
              <article className="po2-decision-item"><StatusBadge tone="info">EXE10</StatusBadge><div><strong>Incidence financiere a justifier</strong><small>Montant HT/TTC, pourcentage d'ecart et nouveau montant du marche.</small></div></article>
            </div>

            {message ? <p className="po2-muted-line" style={{ margin: 0 }}>{message}</p> : null}
            <div style={{ display: "flex", gap: ".6rem", flexWrap: "wrap" }}>
              <Button variant="primary" onClick={handleCreate} disabled={saving || !token}>{saving ? "Creation..." : "Creer le dossier"}</Button>
              <Button variant="ghost" disabled>Preparer le mail DALKIA</Button>
            </div>
          </div>
        </Card>

        <Card title="Parcours recommande" eyebrow="Workflow">
          <div className="po2-decision-list">
            {STEPS.map((step) => (
              <article key={step.label} className="po2-decision-item"><StatusBadge tone={stepTone(step.status)}>{step.status === "done" ? "Fait" : step.status === "active" ? "En cours" : "Suivant"}</StatusBadge><div><strong>{step.label}</strong><small>{step.detail}</small></div></article>
            ))}
          </div>
        </Card>
      </div>

      <Card title={title} eyebrow="Impact financier">
        <DataTable rows={rows} getRowKey={(row) => row.poste} columns={[
          { key: "poste", header: "Poste", render: (row) => <strong>{row.poste}</strong> },
          { key: "current", header: "Reference actuelle", render: (row) => eur(row.current) },
          { key: "delta", header: "Impact annuel", render: (row) => <StatusBadge tone={row.delta >= 0 ? "warn" : "ok"}>{eur(row.delta)}</StatusBadge> },
          { key: "after", header: "Projection apres mouvement", render: (row) => eur(row.after) },
        ]} />
      </Card>

      <Card title="Portefeuille des dossiers" eyebrow={loading ? "Chargement" : `${requests.length} dossier(s)`}>
        {requests.length === 0 ? (
          <p className="po2-muted-line">Aucun dossier persiste pour le moment. Cree un premier mouvement pour alimenter le suivi.</p>
        ) : (
          <DataTable rows={requests} getRowKey={(row) => row.id} columns={[
            { key: "title", header: "Dossier", render: (row) => <span><strong>{row.title}</strong><small className="po2-muted-line">Lot {row.lot ?? "-"} - effet {row.effective_date ?? "a preciser"}</small></span> },
            { key: "status", header: "Statut", render: (row) => <StatusBadge tone={statusTone(row.status)}>{statusLabel(row.status)}</StatusBadge> },
            { key: "annual", header: "Impact annuel", render: (row) => eur(row.impact.total_annual_ht), sortValue: (row) => row.impact.total_annual_ht },
            { key: "prorata", header: "Prorata", render: (row) => eur(row.impact.first_year_prorata_ht), sortValue: (row) => row.impact.first_year_prorata_ht },
            { key: "remaining", header: "Reste marche", render: (row) => eur(row.impact.remaining_market_ht), sortValue: (row) => row.impact.remaining_market_ht },
          ]} />
        )}
      </Card>
    </div>
  );
}