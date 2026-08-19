from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LegacyAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code_bien: str
    designation: str | None = None
    nomcourt: str | None = None
    genre: str | None = None
    categ_des: str | None = None
    souscat_des: str | None = None
    horsparc: str | None = None
    code_parent: str | None = None
    source_norue: str | None = None
    source_bister: str | None = None
    source_libelvoie: str | None = None
    source_codpost: str | None = None
    source_ville: str | None = None
    source_commune: str | None = None
    source_refcad: str | None = None
    building_id: int | None = None
    local_id: int | None = None
    target_type: str = "building"
    status: str
    link_origin: str | None = None
    candidate_building_id: int | None = None
    candidate_label: str | None = None
    candidate_score: float | None = None
    candidate_reason: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    resolved_housenumber: str | None = None
    resolved_street: str | None = None
    resolved_postcode: str | None = None
    resolved_city: str | None = None
    resolved_citycode: str | None = None
    resolved_label: str | None = None
    resolved_source: str | None = None
    resolved_name: str | None = None
    resolved_section: str | None = None
    resolved_numero_plan: str | None = None
    resolved_refcad: str | None = None
    import_batch: str | None = None
    notes: str | None = None
    updated_at: datetime | None = None


class LegacyImportResult(BaseModel):
    batch: str
    sheet_name: str
    header_row: int
    columns: int
    total_rows: int
    created: int
    updated: int
    skipped_scope: int
    skipped_no_key: int
    out_of_scope_commune: int


class LegacyCandidatesResult(BaseModel):
    scanned: int
    proposed: int
    auto_linked: int
    # Biens dont le batiment avait disparu (patrimoine purge) et qui repassent a traiter.
    repaired: int = 0


class LegacyAssetUpdateIn(BaseModel):
    """Décision utilisateur. Le `code_bien` est volontairement absent : il ne doit
    jamais être modifié, c'est la clé de mise à jour d'ASTECH."""

    status: str | None = Field(default=None, max_length=20)
    building_id: int | None = None
    local_id: int | None = None
    clear_building: bool = False
    latitude: float | None = None
    longitude: float | None = None
    notes: str | None = None


class LegacyConfirmIn(BaseModel):
    """Vide = confirmer toutes les propositions en attente."""

    asset_ids: list[int] | None = None
