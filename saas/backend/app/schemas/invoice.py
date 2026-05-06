from datetime import date, datetime

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
    control_issues: list[EnergyInvoiceControlIssueOut]
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EnergyInvoiceUploadResponse(BaseModel):
    invoice_import: EnergyInvoiceImportOut
    is_duplicate: bool
    message: str
