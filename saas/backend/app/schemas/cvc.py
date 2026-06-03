from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CvcPreviewResponse(BaseModel):
    columns: list[str]
    total_rows: int
    unique_sites: list[str]
    unique_families: list[str]
    sample_rows: list[dict]


class BuildingMatchSuggestion(BaseModel):
    building_id: int
    nom_batiment: str | None
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


class CvcBuildingMapping(BaseModel):
    site_raw: str
    building_id: int


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
