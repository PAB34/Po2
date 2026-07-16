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


class CpeOsAvenantSiteOption(BaseModel):
    code_site: str
    site_name: str | None = None
    lot: int | None
    pce: str | None = None
    tarif: str | None = None
    p1_gaz_annual_ht: float = 0.0
    p1_elec_annual_ht: float = 0.0
    p2_annual_ht: float = 0.0
    p3_annual_ht: float = 0.0
    total_annual_ht: float = 0.0