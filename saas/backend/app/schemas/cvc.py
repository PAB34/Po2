from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CvcPreviewResponse(BaseModel):
    columns: list[str]
    total_rows: int
    unique_sites: list[str]
    unique_families: list[str]
    sample_rows: list[dict]


class BuildingMatchSuggestion(BaseModel):
    building_id: int
    site_id: int | None = None
    nom_batiment: str | None
    adresse: str | None
    score: float


class PatrimoineSiteSuggestion(BaseModel):
    site_id: int
    nom_site: str
    adresse: str | None
    score: float


class SiteMatchResult(BaseModel):
    site_raw: str
    suggestions: list[BuildingMatchSuggestion]
    auto_selected_id: int | None = None


class CvcMatchBuildingsRequest(BaseModel):
    sites: list[str]


class CvcMatchBuildingsResponse(BaseModel):
    matches: list[SiteMatchResult]


class CvcImportSiteMatchResult(BaseModel):
    site_raw: str
    item_count: int
    current_site_id: int | None = None
    current_building_id: int | None = None
    current_building_ids: list[int] = Field(default_factory=list)
    site_suggestions: list[PatrimoineSiteSuggestion]
    building_suggestions: list[BuildingMatchSuggestion]
    auto_site_id: int | None = None
    auto_building_id: int | None = None


class CvcImportSiteMatchResponse(BaseModel):
    matches: list[CvcImportSiteMatchResult]


class CvcBuildingMapping(BaseModel):
    site_raw: str
    building_id: int


class CvcSiteMapping(BaseModel):
    site_raw: str
    site_id: int | None = None
    building_id: int | None = None
    building_ids: list[int] | None = None
    create_building: bool = False
    create_building_name: str | None = None
    create_building_names: list[str] | None = None


class CvcApplySiteMappingsRequest(BaseModel):
    mappings: list[CvcSiteMapping]


class CvcApplySiteMappingsResult(BaseModel):
    updated: int
    mappings_applied: int


class CvcImportBatchSummary(BaseModel):
    import_batch: str
    provider: str = "DALKIA"
    imported: int
    mapped_items: int
    reference_mapped_items: int
    refrigerant_items: int
    created_at: datetime | None = None


class CvcEquipmentReferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_ligne: int
    code_niveau_1: str
    libelle_niveau_1: str
    code_niveau_2: str
    libelle_niveau_2: str
    niveau_3: str | None = None
    niveau_4: str | None = None
    niveau_5: str | None = None
    equipement: str
    sypemi_mini_annees: float | None = None
    sypemi_reference_annees: float | None = None
    sypemi_maxi_annees: float | None = None
    fiche_cee: str | None = None


class CvcInventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city_id: int | None = None
    site_id: int | None = None
    building_id: int | None = None
    local_id: int | None = None
    equipment_ref_id: int | None = None
    provider: str = "DALKIA"
    site_raw: str | None = None
    batiment: str | None = None
    niveau: str | None = None
    local_name: str | None = None
    designation: str
    type_equipement: str | None = None
    statut: str | None = None
    etat_sante: str | None = None
    quantite_relevee: int | None = None
    famille: str | None = None
    marque: str | None = None
    modele: str | None = None
    numero_serie: str | None = None
    puissance: str | None = None
    puissance_frigorifique: float | None = None
    puissance_calorifique: float | None = None
    capacite: float | None = None
    date_mis_en_service: int | None = None
    duree_vie_restante: float | None = None
    duree_vie_restante_source: str | None = None
    duree_vie_restante_calculee: float | None = None
    lifecycle_age_years: float | None = None
    lifecycle_age_source: str = "missing"
    lifecycle_age_label: str | None = None
    quantite_fluide_frigorigene: float | None = None
    import_batch: str | None = None
    criticite_pct: float | None = None
    sypemi_reference_annees: float | None = None
    sypemi_mini_annees: float | None = None
    sypemi_maxi_annees: float | None = None
    equipment_ref: CvcEquipmentReferenceRead | None = None
    requires_refrigerant_quantity: bool = False
    created_at: datetime
    updated_at: datetime


class CvcInventoryItemUpdate(BaseModel):
    site_id: int | None = None
    building_id: int | None = None
    local_id: int | None = None
    equipment_ref_id: int | None = None
    date_mis_en_service: int | None = None
    quantite_fluide_frigorigene: float | None = None


class CvcImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
    import_batch: str
    provider: str = "DALKIA"
    sypemi_matched: int
    sypemi_unmatched: int


class CvcRecomputeReferencesResult(BaseModel):
    import_batch: str
    updated: int
    matched: int
    unmatched: int
    changed: int


class CvcRefrigerantImportResult(BaseModel):
    import_batch: str
    imported: int
    auto_matched: int
    pending: int
    ambiguous: int
    total_fluide_kg: float
    total_teqco2: float


class CvcRefrigerantBatchSummary(BaseModel):
    import_batch: str
    source_filename: str | None = None
    imported: int
    matched_items: int
    pending_items: int
    total_fluide_kg: float
    total_teqco2: float
    created_at: datetime | None = None


class CvcInventoryItemCompact(BaseModel):
    id: int
    site_raw: str | None = None
    designation: str
    famille: str | None = None
    marque: str | None = None
    modele: str | None = None
    date_mis_en_service: int | None = None
    import_batch: str | None = None


class CvcRefrigerantMatchCandidate(BaseModel):
    item: CvcInventoryItemCompact
    score: float
    method: str


class CvcRefrigerantItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city_id: int | None = None
    site_id: int | None = None
    building_id: int | None = None
    cvc_inventory_item_id: int | None = None
    import_batch: str
    source_filename: str | None = None
    row_number: int | None = None
    site_raw: str | None = None
    designation: str
    quantite_relevee: int | None = None
    famille: str | None = None
    marque: str | None = None
    modele: str | None = None
    fluide_frigorigene: str | None = None
    quantite_fluide_kg: float | None = None
    puissance_froid_kw: float | None = None
    date_mis_en_service: int | None = None
    gwp: float | None = None
    teqco2: float | None = None
    esp_status: str | None = None
    cout_desp_date_eur: float | None = None
    cumul_5_ans_eur: float | None = None
    schedule: dict[str, str] = Field(default_factory=dict)
    detection_permanente: bool | None = None
    dernier_controle_etancheite: date | None = None
    prochaine_echeance: date | None = None
    titulaire: str | None = None
    responsable_collectivite: str | None = None
    statut_action: str | None = None
    commentaire_gmao: str | None = None
    fgas_status: str = "Données à compléter"
    frequence_controle_mois: int | None = None
    statut_conformite: str = "Données à compléter"
    action_prioritaire: str = "Compléter fluide / charge kg / GWP"
    preuve_attendue: str = "Fiche équipement / plaque signalétique"
    priorite: str = "Haute"
    match_status: str
    match_method: str | None = None
    match_score: float | None = None
    matched_inventory_item: CvcInventoryItemCompact | None = None
    candidates: list[CvcRefrigerantMatchCandidate] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CvcRefrigerantItemUpdate(BaseModel):
    cvc_inventory_item_id: int | None = None
    site_id: int | None = None
    building_id: int | None = None
    detection_permanente: bool | None = None
    dernier_controle_etancheite: date | None = None
    prochaine_echeance: date | None = None
    titulaire: str | None = None
    responsable_collectivite: str | None = None
    statut_action: str | None = None
    commentaire_gmao: str | None = None


class CvcRefrigerantDashboardKpi(BaseModel):
    key: str
    label: str
    value: int | float | str
    tone: str = "neutral"
    helper: str | None = None


class CvcRefrigerantActionSummary(BaseModel):
    item_id: int
    priority: str
    theme: str
    site: str | None = None
    equipment: str
    constat: str
    action: str
    preuve_attendue: str
    responsable: str | None = None
    echeance_cible: date | None = None
    statut_action: str


class CvcRefrigerantDashboard(BaseModel):
    total_items: int
    latest_batch: str | None = None
    latest_batch_label: str | None = None
    kpis: list[CvcRefrigerantDashboardKpi]
    status_counts: dict[str, int]
    conformity_counts: dict[str, int]
    priority_counts: dict[str, int]
    open_actions: list[CvcRefrigerantActionSummary]
    esp_signals: list[CvcRefrigerantActionSummary]


class CvcSourceBuildingMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city_id: int | None = None
    source_type: str
    import_batch: str
    source_site_raw: str
    site_id: int | None = None
    building_id: int | None = None
    building_ids: list[int] = Field(default_factory=list)
    status: str
    notes: str | None = None
    match_score: float | None = None
    match_method: str | None = None
    site_suggestions: list[PatrimoineSiteSuggestion] = Field(default_factory=list)
    building_suggestions: list[BuildingMatchSuggestion] = Field(default_factory=list)
    item_count: int = 0
    refrigerant_count: int = 0
    created_at: datetime
    updated_at: datetime


class CvcSourceBuildingMappingUpdate(BaseModel):
    site_id: int | None = None
    building_id: int | None = None
    building_ids: list[int] | None = None
    status: str = "to_review"
    notes: str | None = None


class CvcTechnicalCoverageReport(BaseModel):
    patrimoine_buildings: int
    cvc_inventory_items: int
    cvc_refrigerant_items: int
    inventory_without_building: int
    refrigerants_without_building: int
    refrigerants_without_inventory_item: int
    source_mappings_to_review: int
    source_mappings_not_found: int
    patrimoine_buildings_without_cvc: list[BuildingMatchSuggestion]
    inventory_unmapped_by_source: list[dict]
    refrigerants_unmapped_by_source: list[dict]


# ---------------------------------------------------------------------------
# État du parc technique — agrégation du cycle de vie des équipements
# ---------------------------------------------------------------------------

class CvcParcBucket(BaseModel):
    """Tranche d'un histogramme (âges, criticité, prestataire)."""

    key: str
    label: str
    count: int
    share_pct: float


class CvcParcFamille(BaseModel):
    famille: str
    count: int
    age_moyen: float | None = None
    fin_de_vie_5ans: int = 0
    depasses: int = 0


class CvcParcBatiment(BaseModel):
    building_id: int
    nom_batiment: str | None = None
    count: int
    age_moyen: float | None = None
    criticite_moyenne: float | None = None
    fin_de_vie_5ans: int = 0
    depasses: int = 0


class CvcParcCompletude(BaseModel):
    """Part des équipements dont la donnée nécessaire au calcul est présente."""

    rattachement_pct: float
    date_mes_pct: float
    reference_pct: float
    duree_vie_pct: float


class CvcParcTechniqueReport(BaseModel):
    equipements_total: int
    equipements_rattaches: int
    batiments_couverts: int
    age_moyen: float | None = None
    depasses: int = 0
    fin_de_vie_5ans: int = 0
    ages: list[CvcParcBucket] = []
    criticites: list[CvcParcBucket] = []
    par_provider: list[CvcParcBucket] = []
    par_famille: list[CvcParcFamille] = []
    par_batiment: list[CvcParcBatiment] = []
    completude: CvcParcCompletude
