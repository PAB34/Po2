"""Service CRUD des contacts fournisseurs (un par ville × fournisseur)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supplier_contact import SupplierContact

_FIELDS = ("contact_name", "email", "phone", "role", "notes")


def list_contacts(db: Session, city_id: int | None) -> list[SupplierContact]:
    query = select(SupplierContact)
    if city_id is not None:
        query = query.where(SupplierContact.city_id == city_id)
    return list(db.scalars(query.order_by(SupplierContact.supplier)).all())


def upsert_contact(db: Session, city_id: int | None, supplier: str, payload: dict[str, Any]) -> SupplierContact:
    existing = db.scalar(
        select(SupplierContact).where(
            SupplierContact.city_id == city_id,
            SupplierContact.supplier == supplier,
        )
    )
    if existing is None:
        existing = SupplierContact(city_id=city_id, supplier=supplier)
        db.add(existing)
    for field in _FIELDS:
        if field in payload:
            value = payload[field]
            setattr(existing, field, (value.strip() or None) if isinstance(value, str) else value)
    db.commit()
    db.refresh(existing)
    return existing
