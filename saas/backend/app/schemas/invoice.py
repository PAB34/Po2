from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel


class EnergyInvoiceControlIssueOut(BaseModel):
    severity: str
    code: str
    message: str
    scope: str | None = None


class EnergyInvoiceImportOut(BaseModel):
    id: int
    city_id: int
    uploaded_by_user_id: int
    source: str
    original_filename: str
    content_type: str | None
    file_size_bytes: int
    sha256: str
    supplier_guess: str | None
    invoice_number: str | None
    invoice_date: date | None
    period_start: date | None
    period_end: date | None
    regroupement: str | None
    total_ttc: float | None
    total_consumption_kwh: float | None
    site_count: int | None
    status: str
    analysis_status: str
    control_status: str
    control_errors_count: int
    control_warnings_count: int
    decision_status: str
    decision_comment: str | None
    decision_by_user_id: int | None
    decision_updated_at: datetime | None
    control_issues: list[EnergyInvoiceControlIssueOut]
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EnergyInvoiceImportDetailOut(EnergyInvoiceImportOut):
    analysis_result: dict[str, Any] | None
    control_report: dict[str, Any] | None


class EnergyInvoiceDecisionIn(BaseModel):
    decision_status: Literal["to_review", "approved", "rejected", "dispute_sent"]
    decision_comment: str | None = None


class EnergyInvoiceUploadResponse(BaseModel):
    invoice_import: EnergyInvoiceImportOut
    is_duplicate: bool
    message: str
