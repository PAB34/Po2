from datetime import date, datetime

from pydantic import BaseModel


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
    status: str
    analysis_status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EnergyInvoiceUploadResponse(BaseModel):
    invoice_import: EnergyInvoiceImportOut
    is_duplicate: bool
    message: str
