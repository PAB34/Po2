"""Schemas for CPE DALKIA OS / avenant preparation dossiers."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CpeOsAvenantLineBase(BaseModel):
    action: str = Field(pattern="^(add|remove|modify)$")
    code_site: str | None = None
    site_name: str | None = None
    lot: int | None = None
    pce: str | None = None
    tarif: str | None = None
    current_p1_gaz_annual_ht: float | None = None
    current_p1_elec_annual_ht: float | None = None
    current_p2_annual_ht: float | None = None
    current_p3_annual_ht: float | None = None
    p1_gaz_annual_ht: float | None = None
    p1_elec_annual_ht: float | None = None
    p2_annual_ht: float | None = None
    p3_annual_ht: float | None = None
    nb_mwh_pci: float | None = None
    cible_elec_mwh: float | None = None
    notes: str | None = None


class CpeOsAvenantLineCreate(CpeOsAvenantLineBase):
    pass


class CpeOsAvenantLineOut(CpeOsAvenantLineBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    city_id: int | None
    created_at: datetime
    updated_at: datetime


class CpeOsAvenantAnnualImpact(BaseModel):
    year: int
    ratio: float
    p1_gaz_ht: float
    p1_elec_ht: float
    p1_ht: float
    p2_ht: float
    p3_ht: float
    total_ht: float


class CpeOsAvenantImpact(BaseModel):
    p1_gaz_annual_ht: float
    p1_elec_annual_ht: float
    p1_annual_ht: float
    p2_annual_ht: float
    p3_annual_ht: float
    total_annual_ht: float
    first_year_prorata_ht: float
    remaining_market_ht: float
    effective_year: int | None
    first_year_ratio: float
    annual_impacts: list[CpeOsAvenantAnnualImpact] = Field(default_factory=list)


class CpeOsAvenantRequestCreate(BaseModel):
    title: str
    change_type: str = "mixed"
    lot: int | None = None
    effective_date: date | None = None
    reason: str | None = None
    requester_name: str | None = None
    dalkia_contact_email: str | None = None
    notes: str | None = None
    lines: list[CpeOsAvenantLineCreate] = Field(default_factory=list)


class CpeOsAvenantRequestUpdate(BaseModel):
    title: str | None = None
    change_type: str | None = None
    status: str | None = None
    lot: int | None = None
    effective_date: date | None = None
    reason: str | None = None
    requester_name: str | None = None
    dalkia_contact_email: str | None = None
    os_number: str | None = None
    avenant_number: str | None = None
    notes: str | None = None


class CpeOsAvenantRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city_id: int | None
    created_by_user_id: int | None
    baseline_import_id: int | None
    title: str
    change_type: str
    status: str
    lot: int | None
    effective_date: date | None
    reason: str | None
    requester_name: str | None
    dalkia_contact_email: str | None
    os_number: str | None
    avenant_number: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    lines: list[CpeOsAvenantLineOut]
    impact: CpeOsAvenantImpact


class CpeOsAvenantP1GazLine(BaseModel):
    pce: str | None = None
    type_tarif: str | None = None
    prix_unitaire_ht: float | None = None
    atrd_ht: float | None = None
    cta_ht: float | None = None
    p10_fixe_ht: float | None = None
    qt_mwhpcs: float | None = None
    p10_var_ht: float | None = None
    p10_total_ht: float | None = None


class CpeOsAvenantP1ElecLine(BaseModel):
    pdl: str | None = None
    prix_unitaire_ht: float | None = None
    qt_mwh: float | None = None
    p10_var_ht: float | None = None
    p10_total_ht: float | None = None


class CpeOsAvenantP2P3Detail(BaseModel):
    p2_1_ht: float = 0.0
    p2_2_ht: float = 0.0
    p2_3_ht: float = 0.0
    p2_4_ht: float = 0.0
    p2_total_ht: float = 0.0
    p3_1_ht: float = 0.0
    p3_2_ht: float = 0.0
    p3_3_ht: float = 0.0
    p3_4_ht: float = 0.0
    p3_total_ht: float = 0.0


class CpeOsAvenantSiteOption(BaseModel):
    code_site: str
    site_name: str | None = None
    lot: int | None
    source_year: int | None = None
    pce: str | None = None
    tarif: str | None = None
    p1_gaz_annual_ht: float = 0.0
    p1_elec_annual_ht: float = 0.0
    p2_annual_ht: float = 0.0
    p3_annual_ht: float = 0.0
    total_annual_ht: float = 0.0
    p1_gaz_lines: list[CpeOsAvenantP1GazLine] = Field(default_factory=list)
    p1_elec_lines: list[CpeOsAvenantP1ElecLine] = Field(default_factory=list)
    p2p3_detail: CpeOsAvenantP2P3Detail = Field(default_factory=CpeOsAvenantP2P3Detail)
