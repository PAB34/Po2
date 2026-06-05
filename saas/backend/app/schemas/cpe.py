"""Schemas Pydantic pour le module CPE DALKIA."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# ── CpeSite ──────────────────────────────────────────────────────────────────

class CpeSiteBase(BaseModel):
    code_site: str
    nom_site: str
    categorie: str
    nb_mwh_pci: float
    ecs_ref_m3_an: float
    q_ecs_mwh_pci_per_m3: float | None = None
    dju_reference: float = 1426.0
    cible_elec_mwh: float | None = None
    tarif: str | None = None   # T1 | T2 | T3 (OS N°3)
    pce: str | None = None     # PCE GRDF
    actif: bool = True
    notes: str | None = None


class CpeSiteCreate(CpeSiteBase):
    city_id: int | None = None


class CpeSiteUpdate(BaseModel):
    nb_mwh_pci: float | None = None
    ecs_ref_m3_an: float | None = None
    q_ecs_mwh_pci_per_m3: float | None = None
    cible_elec_mwh: float | None = None
    tarif: str | None = None
    pce: str | None = None
    actif: bool | None = None
    notes: str | None = None


class CpeSiteOut(CpeSiteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    city_id: int | None
    created_at: datetime
    updated_at: datetime


# ── CpeGazReleve ─────────────────────────────────────────────────────────────

class CpeGazReleve(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cpe_site_id: int
    annee: int
    mois: int
    qt_mwh_pci: float | None
    volume_ecs_m3: float | None
    etat_chauffe: bool | None
    source: str
    date_import: datetime
    notes: str | None


class CpeGazReleveCreate(BaseModel):
    annee: int
    mois: int
    qt_mwh_pci: float | None = None
    volume_ecs_m3: float | None = None
    etat_chauffe: bool | None = None
    notes: str | None = None


class CpeGazReleveUpdate(BaseModel):
    qt_mwh_pci: float | None = None
    volume_ecs_m3: float | None = None
    etat_chauffe: bool | None = None
    notes: str | None = None


# ── CpePrixGaz ───────────────────────────────────────────────────────────────

class CpePrixGazOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    annee: int
    tarif: str | None
    pu_eur_mwh_pci: float
    source: str
    notes: str | None
    updated_at: datetime


class CpePrixGazCreate(BaseModel):
    annee: int
    tarif: str | None = None  # T1 | T2 | T3 — None pour saisie manuelle globale
    pu_eur_mwh_pci: float
    source: str = "saisie_manuelle"
    notes: str | None = None


# ── CpeResultatAnnuel ────────────────────────────────────────────────────────

class CpeResultatAnnuelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cpe_site_id: int
    annee: int
    dju_reels: float | None
    dju_reference: float
    nb: float
    n_prime_b: float | None
    qt_total: float | None
    m_ecs_total: float | None
    nc: float | None
    pu_mwh: float | None
    ecart: float | None
    type_resultat: str | None
    montant_ht: float | None
    p2_4_taux: float
    ecart_pct: float | None
    alerte_revision_nb: bool
    statut: str
    nb_mois_renseignes: int
    computed_at: datetime


# ── Bilan annuel (vue d'ensemble multi-sites) ─────────────────────────────────

class CpeSiteBilanItem(BaseModel):
    """Résultat synthétique d'un site pour le bilan annuel."""
    site: CpeSiteOut
    resultat: CpeResultatAnnuelOut | None
    nb_mois_releves: int
    nb_exercice: float            # NB effectivement utilisé pour le calcul de l'exercice
    nb_source: str                # "dalkia" (cible importée de l'année) | "site" (scalaire de secours)
    qt_cumul: float | None
    nc_cumul: float | None
    n_prime_b: float | None
    ecart: float | None
    type_resultat: str | None
    montant_ht: float | None
    statut: str


class CpeBilanAnnuel(BaseModel):
    """Vue d'ensemble du bilan CPE pour un exercice."""
    annee: int
    dju_reels: float | None
    dju_reference: float
    pu_mwh: float | None          # prix T2 par défaut (affichage KPI)
    prix_tarifs: dict[str, float]  # {T1: ..., T2: ..., T3: ...} — prix PCI par tarif
    nb_sites_actifs: int
    nb_sites_complets: int
    total_interessement_ht: float
    total_penalite_ht: float
    solde_ht: float  # positif = facture DALKIA, négatif = avoir DALKIA
    sites: list[CpeSiteBilanItem]


class CpeConsoFluideSummary(BaseModel):
    fluide: str
    total: float
    unite: str
    nb_sites: int
    nb_mois: int
    nb_releves: int
    nb_estimes: int


class CpeConsoUnknownSite(BaseModel):
    code_site: str
    contract_code: str | None
    fluides: list[str]
    nb_mois: int
    total_energie_mwh: float | None
    total_volume: float | None
    nb_estimes: int


class CpeConsoCoverageSite(BaseModel):
    site_id: int
    code_site: str
    nom_site: str
    categorie: str
    mois_couverts: int
    fluides: list[str]


class CpeConsoSynthese(BaseModel):
    annee: int
    nb_sites_actifs: int
    nb_sites_couverts: int
    nb_sites_sans_conso: int
    nb_sites_inconnus: int
    fluides: list[CpeConsoFluideSummary]
    sites_sans_conso: list[CpeConsoCoverageSite]
    sites_inconnus: list[CpeConsoUnknownSite]


# ── Import CSV ────────────────────────────────────────────────────────────────

class CpeImportResult(BaseModel):
    nb_lignes: int
    nb_inseres: int
    nb_mis_a_jour: int
    nb_erreurs: int
    erreurs: list[str]
    sites_inconnus: list[str]


# ── Export finances DALKIA ───────────────────────────────────────────────────

class CpeFinanceGroupSummary(BaseModel):
    code: str
    nb_lignes: int
    nb_factures: int
    montant_ht: float


class CpeFinanceContractSummary(BaseModel):
    code_contrat: str
    libelle_contrat: str | None
    nb_lignes: int
    nb_factures: int
    montant_ht: float
    periode_debut_min: str | None
    periode_fin_max: str | None
    marches: list[str]
    types_marche: list[str]
    nb_lignes_code_site_cpe: int
    nb_sites_cpe_distincts: int
    nb_lignes_consommation: int
    nb_lignes_index_releve: int


class CpeFinancePreview(BaseModel):
    filename: str | None
    nb_lignes: int
    nb_factures: int
    nb_contrats: int
    montant_ht: float
    nb_lignes_p1_p2_p3: int
    nb_lignes_code_site_cpe: int
    nb_sites_cpe_distincts: int
    nb_lignes_consommation: int
    nb_lignes_index_releve: int
    marches: list[CpeFinanceGroupSummary]
    types_facture: list[CpeFinanceGroupSummary]
    contrats: list[CpeFinanceContractSummary]
    sites_cpe_detectes: list[str]
    alertes: list[str]


# ── Référentiel comptable DALKIA ─────────────────────────────────────────────

class CpeAccountingNatureRuleBase(BaseModel):
    contract_code: str | None = None
    market: str
    service_sold: str | None = None
    billed_item: str
    frequency: str | None = None
    accounting_nature: str
    accounting_label: str | None = None
    active: bool = True
    notes: str | None = None


class CpeAccountingNatureRuleCreate(CpeAccountingNatureRuleBase):
    city_id: int | None = None


class CpeAccountingNatureRuleUpdate(BaseModel):
    contract_code: str | None = None
    market: str | None = None
    service_sold: str | None = None
    billed_item: str | None = None
    frequency: str | None = None
    accounting_nature: str | None = None
    accounting_label: str | None = None
    active: bool | None = None
    notes: str | None = None


class CpeAccountingNatureRuleOut(CpeAccountingNatureRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    city_id: int | None
    created_at: datetime
    updated_at: datetime


class CpeAccountingSiteMappingBase(BaseModel):
    code_site: str
    site_name: str
    family: str | None = None
    manager: str | None = None
    alternate_manager: str | None = None
    service_code: str | None = None
    service_label: str | None = None
    function_code: str | None = None
    function_label: str | None = None
    antenna_code: str | None = None
    antenna_label: str | None = None
    operation_code: str | None = None
    operation_label: str | None = None
    active: bool = True
    notes: str | None = None


class CpeAccountingSiteMappingCreate(CpeAccountingSiteMappingBase):
    city_id: int | None = None


class CpeAccountingSiteMappingUpdate(BaseModel):
    code_site: str | None = None
    site_name: str | None = None
    family: str | None = None
    manager: str | None = None
    alternate_manager: str | None = None
    service_code: str | None = None
    service_label: str | None = None
    function_code: str | None = None
    function_label: str | None = None
    antenna_code: str | None = None
    antenna_label: str | None = None
    operation_code: str | None = None
    operation_label: str | None = None
    active: bool | None = None
    notes: str | None = None


class CpeAccountingSiteMappingOut(CpeAccountingSiteMappingBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    city_id: int | None
    created_at: datetime
    updated_at: datetime


class CpeAccountingImportResult(BaseModel):
    filename: str | None
    nature_rules_created: int
    nature_rules_updated: int
    site_mappings_created: int
    site_mappings_updated: int
    errors: list[str]


class CpeContractReferenceBase(BaseModel):
    contract_code: str
    contract_label: str | None = None
    reference_kind: str = "p1_gaz_acompte"
    year: int
    market: str
    billed_item: str
    annual_amount_ht: float | None = None
    expected_amount_ht: float | None = None
    installment_count: int | None = None
    expected_period_months: str | None = None
    included_billed_items: str | None = None
    formula: str | None = None
    tolerance_pct: float | None = None
    tolerance_eur: float | None = None
    active: bool = True
    notes: str | None = None


class CpeContractReferenceCreate(CpeContractReferenceBase):
    city_id: int | None = None


class CpeContractReferenceUpdate(BaseModel):
    contract_code: str | None = None
    contract_label: str | None = None
    reference_kind: str | None = None
    year: int | None = None
    market: str | None = None
    billed_item: str | None = None
    annual_amount_ht: float | None = None
    expected_amount_ht: float | None = None
    installment_count: int | None = None
    expected_period_months: str | None = None
    included_billed_items: str | None = None
    formula: str | None = None
    tolerance_pct: float | None = None
    tolerance_eur: float | None = None
    active: bool | None = None
    notes: str | None = None


class CpeContractReferenceOut(CpeContractReferenceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    city_id: int | None
    created_at: datetime
    updated_at: datetime


# ── Registre factures finances DALKIA ────────────────────────────────────────

class CpeFinanceImportBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    city_id: int | None
    filename: str | None
    source: str
    status: str
    line_count: int
    invoice_count: int
    total_ht: float
    notes: str | None
    created_at: datetime


class CpeFinanceInvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    batch_id: int
    city_id: int | None
    invoice_number: str
    contract_code: str | None
    contract_label: str | None
    invoice_type: str | None
    supplier: str | None
    customer_code: str | None
    customer_name: str | None
    invoice_date: date | None
    due_date: date | None
    period_start: date | None
    period_end: date | None
    markets: str | None = None
    billed_items: str | None = None
    recipient_reference_1: str | None = None
    evidence_id: int | None = None
    evidence_status: str | None = None
    evidence_revision_date: date | None = None
    evidence_declared_factor: float | None = None
    evidence_declared_icht_ime: float | None = None
    evidence_declared_fsd2: float | None = None
    evidence_declared_bt40: float | None = None
    total_ht: float
    status: str
    finance_exported_at: datetime | None
    billing_days: int | None = None
    issue_delay_days: int | None = None
    due_in_days: int | None = None
    deadline_status: str | None = None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CpeFinanceInvoiceUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


class CpeRevisionIndexBase(BaseModel):
    index_code: str
    year: int
    quarter: int
    value: float
    source: str | None = None
    verification_status: str = "to_verify"
    evidence_id: int | None = None
    notes: str | None = None


class CpeRevisionIndexCreate(CpeRevisionIndexBase):
    city_id: int | None = None


class CpeRevisionIndexOut(CpeRevisionIndexBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    city_id: int | None
    created_at: datetime
    updated_at: datetime


class CpeRevisionObservationOut(BaseModel):
    market: str
    year: int
    quarter: int
    observed_factor: float
    expected_factor: float | None
    delta_factor: float | None
    status: str
    line_count: int
    invoice_numbers: list[str]
    required_indices: list[str]
    message: str


class CpeInvoiceEvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    city_id: int | None
    invoice_id: int | None
    uploaded_by_user_id: int
    original_filename: str
    sha256: str
    extraction_status: str
    validation_status: str
    evidence_kind: str
    market: str | None
    contract_code: str | None
    year: int | None
    quarter: int | None
    effective_date: date | None
    declared_invoice_number: str | None
    revision_date: date | None
    declared_factor: float | None
    declared_icht_ime: float | None
    declared_fsd2: float | None
    declared_bt40: float | None
    notes: str | None
    created_at: datetime


class CpeFinanceLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    batch_id: int
    invoice_id: int
    row_number: int
    contract_code: str | None
    invoice_number: str | None
    market: str | None
    market_type: str | None
    service_sold: str | None
    billed_item: str | None
    vat_rate: float | None
    amount_ht: float
    consumption: float | None
    unit: str | None
    base_price: float | None
    revised_price: float | None
    detail: str | None
    site_code_detected: str | None
    accounting_site_id: int | None
    accounting_rule_id: int | None
    accounting_nature: str | None
    accounting_label: str | None
    period_start: date | None
    period_end: date | None


class CpeFinanceControlOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    city_id: int | None
    batch_id: int
    invoice_id: int
    line_id: int
    control_type: str
    status: str
    severity: str
    message: str
    formula: str | None
    index_year: int | None
    index_quarter: int | None
    icht_ime_value: float | None
    bt40_value: float | None
    fsd2_value: float | None
    expected_factor: float | None
    base_price: float | None
    expected_revised_price: float | None
    actual_revised_price: float | None
    delta_abs: float | None
    delta_pct: float | None
    computed_at: datetime


class CpeFinanceControlTypeSummary(BaseModel):
    control_type: str
    ok: int
    error: int
    blocked: int
    total: int


class CpeFinanceControlInvoiceSummary(BaseModel):
    invoice_id: int
    invoice_number: str
    contract_code: str | None
    contract_label: str | None
    invoice_type: str | None
    recipient_ref: str | None = None
    market: str | None = None
    billed_items: str | None = None
    total_ht: float
    invoice_status: str
    finance_exported_at: datetime | None
    due_date: date | None
    due_in_days: int | None
    deadline_status: str
    ok: int
    error: int
    blocked: int
    controls_total: int
    control_types: list[str]


class CpeFinanceControlReportOut(BaseModel):
    generated_at: datetime
    scope: str
    invoice_count: int
    total_ht: float
    invoices_ok: int
    invoices_with_errors: int
    invoices_blocked: int
    controls_ok: int
    controls_error: int
    controls_blocked: int
    control_types: list[CpeFinanceControlTypeSummary]
    invoices: list[CpeFinanceControlInvoiceSummary]


class CpeMarketTrackingCell(BaseModel):
    year: int
    prevu: float
    recu: float
    ecart: float
    ecart_pct: float | None
    taux: float | None


class CpeMarketTrackingTotal(BaseModel):
    prevu: float
    recu: float
    ecart: float
    ecart_pct: float | None
    taux: float | None


class CpeMarketTrackingPoste(BaseModel):
    poste: str
    label: str
    by_year: list[CpeMarketTrackingCell]
    total: CpeMarketTrackingTotal


class CpeP1DpgfLevelYear(BaseModel):
    year: int
    total: float


class CpeP1DpgfLevel(BaseModel):
    level: str
    label: str
    by_year: list[CpeP1DpgfLevelYear]
    total: float


class CpeP1Dpgf(BaseModel):
    levels: list[CpeP1DpgfLevel] = []
    has_data: bool = False


class CpeMarketTrackingQuarters(BaseModel):
    year: int
    billed: int
    expected: int


class CpeMarketTrackingLot(BaseModel):
    lot: int
    label: str
    contract_codes: list[str]
    postes: list[CpeMarketTrackingPoste]
    totals_by_year: list[CpeMarketTrackingCell]
    grand_total: CpeMarketTrackingTotal
    has_reference: bool
    p1_dpgf: CpeP1Dpgf = CpeP1Dpgf()
    quarters_billed: list[CpeMarketTrackingQuarters] = []


class CpeMarketTrackingOut(BaseModel):
    years: list[int]
    postes: list[CpeMarketTrackingPoste]
    totals_by_year: list[CpeMarketTrackingCell]
    grand_total: CpeMarketTrackingTotal
    p1_source: str
    has_reference: bool
    by_lot: list[CpeMarketTrackingLot] = []
    p1_dpgf: CpeP1Dpgf = CpeP1Dpgf()
    quarters_billed: list[CpeMarketTrackingQuarters] = []
    installments_per_year: int = 4


class CpeFinanceImportResult(BaseModel):
    batch: CpeFinanceImportBatchOut
    invoices: list[CpeFinanceInvoiceOut]
    line_count: int
    matched_accounting_rules: int
    matched_site_mappings: int
    warnings: list[str]


# ── DJU ──────────────────────────────────────────────────────────────────────

class CpeDjuAnnuel(BaseModel):
    annee: int
    dju_total: float
    nb_jours: int
    source: str


# ── Devis petits travaux P3 (type P6 DALKIA) ─────────────────────────────────

class CpeP3DevisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    devis_date: date | None
    localisation: str | None
    site_code: str | None
    libelle: str | None
    domaine: str | None
    type_devis: str | None
    destinataire: str | None
    etat: str | None
    montant_ht: float | None
    montant_ttc: float | None
    in_scope: bool


class CpeP3DevisImportResult(BaseModel):
    created: int
    updated: int
    in_scope: int
    out_of_scope: int
    skipped: int
    errors: list[str] = []


class CpeP3AtterrissageEtat(BaseModel):
    etat: str
    count: int
    montant_ht: float


class CpeP3AtterrissageOut(BaseModel):
    year: int
    provision_p3: float
    provision_p3_4: float
    provision_total: float
    engage_total: float
    reste_provision: float
    taux_engagement: float | None
    devis_count: int
    by_etat: list[CpeP3AtterrissageEtat]
    has_provision: bool
