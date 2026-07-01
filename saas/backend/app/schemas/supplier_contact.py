from datetime import datetime

from pydantic import BaseModel


class SupplierContactIn(BaseModel):
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    notes: str | None = None


class SupplierContactOut(BaseModel):
    id: int
    supplier: str
    contact_name: str | None
    email: str | None
    phone: str | None
    role: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
