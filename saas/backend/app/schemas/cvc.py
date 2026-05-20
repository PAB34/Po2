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


class CvcInventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
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
    import_batch: str | None = None
    criticite_pct: float | None = None
    sypemi_reference_annees: float | None = None
    created_at: datetime
    updated_at: datetime


class CvcImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
    import_batch: str
    sypemi_matched: int
    sypemi_unmatched: int
