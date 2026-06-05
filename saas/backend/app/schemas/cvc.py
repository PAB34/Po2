from datetime import datetime

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


class CvcApplySiteMappingsRequest(BaseModel):
    mappings: list[CvcSiteMapping]


class CvcApplySiteMappingsResult(BaseModel):
    updated: int
    mappings_applied: int


class CvcImportBatchSummary(BaseModel):
    import_batch: str
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
    site_raw: str | None = None
    batiment: str | None = None
    niveau: str | None = None
    local_name: str | None = None
    designation: str
    statut: str | None = None
    etat_sante: str | None = None
    quantite_relevee: int | None = None
    famille: str | None = None
    marque: str | None = None
    modele: str | None = None
    date_mis_en_service: int | None = None
    duree_vie_restante: float | None = None
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
    quantite_fluide_frigorigene: float | None = None


class CvcImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
    import_batch: str
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
    match_status: str
    match_method: str | None = None
    match_score: float | None = None
    matched_inventory_item: CvcInventoryItemCompact | None = None
    candidates: list[CvcRefrigerantMatchCandidate] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CvcRefrigerantItemUpdate(BaseModel):
    cvc_inventory_item_id: int | None = None
