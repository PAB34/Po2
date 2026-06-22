from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PatrimoineMatchItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    external_id: str
    label: str | None = None
    candidate_target_type: str | None = None
    candidate_target_id: int | None = None
    candidate_label: str | None = None
    candidate_score: float | None = None
    candidate_reason: str | None = None
    status: str
    resolved_target_type: str | None = None
    resolved_target_id: int | None = None
    notes: str | None = None
    updated_at: datetime | None = None


class PatrimoineMatchUpdateIn(BaseModel):
    status: str
    resolved_target_type: str | None = None
    resolved_target_id: int | None = None
    notes: str | None = None


class PatrimoineMatchCollectOut(BaseModel):
    prm: int
    pce: int
    created: int
    linked_detected: int


class PatrimoineMatchBulkOut(BaseModel):
    linked: int


class PatrimoineTargetOut(BaseModel):
    target_type: str
    target_id: int
    label: str
