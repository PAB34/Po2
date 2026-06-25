"""Schémas Pydantic des matrices comptables versionnées (doc 38)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Règles
# ---------------------------------------------------------------------------
class AccountingMatrixRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matrix_version_id: int
    stable_rule_key: str
    scope: str
    site_code: str | None = None
    building_id: int | None = None
    meter_id: str | None = None
    billed_item_pattern: str | None = None
    supplier_item_code: str | None = None
    accounting_service: str | None = None
    accounting_function: str | None = None
    accounting_antenna: str | None = None
    operation_number: str | None = None
    accounting_nature: str | None = None
    accounting_label: str | None = None
    allocation_percent: float
    priority: int
    is_active: bool
    comment: str | None = None
    updated_at: datetime | None = None


class AccountingMatrixRuleCreateIn(BaseModel):
    stable_rule_key: str
    scope: str = "billed_item"
    site_code: str | None = None
    building_id: int | None = None
    meter_id: str | None = None
    billed_item_pattern: str | None = None
    supplier_item_code: str | None = None
    accounting_service: str | None = None
    accounting_function: str | None = None
    accounting_antenna: str | None = None
    operation_number: str | None = None
    accounting_nature: str | None = None
    accounting_label: str | None = None
    allocation_percent: float = Field(default=100.0, ge=0, le=100)
    priority: int = 0
    is_active: bool = True
    comment: str | None = None


class AccountingMatrixRuleUpdateIn(BaseModel):
    scope: str | None = None
    site_code: str | None = None
    building_id: int | None = None
    meter_id: str | None = None
    billed_item_pattern: str | None = None
    supplier_item_code: str | None = None
    accounting_service: str | None = None
    accounting_function: str | None = None
    accounting_antenna: str | None = None
    operation_number: str | None = None
    accounting_nature: str | None = None
    accounting_label: str | None = None
    allocation_percent: float | None = Field(default=None, ge=0, le=100)
    priority: int | None = None
    is_active: bool | None = None
    comment: str | None = None


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------
class AccountingMatrixVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matrix_contract_id: int
    version_label: str
    status: str
    effective_from: date | None = None
    effective_to: date | None = None
    source: str
    source_filename: str | None = None
    source_sha256: str | None = None
    created_by_user_id: int | None = None
    validated_by_user_id: int | None = None
    validated_at: datetime | None = None
    rules_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AccountingMatrixVersionCreateIn(BaseModel):
    version_label: str
    # Si renseigné, les règles de cette version sont clonées dans la nouvelle.
    clone_from_version_id: int | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    source: str = "manuel"
    status: str = "draft"


# ---------------------------------------------------------------------------
# Contrats matrice
# ---------------------------------------------------------------------------
class AccountingMatrixContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    domain: str
    supplier: str
    contract_code: str | None = None
    contract_label: str | None = None
    lot_label: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    status: str
    active_version_id: int | None = None
    active_version_label: str | None = None
    versions_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AccountingMatrixContractDetailOut(AccountingMatrixContractOut):
    versions: list[AccountingMatrixVersionOut] = []


class AccountingMatrixContractCreateIn(BaseModel):
    domain: str
    supplier: str
    contract_code: str | None = None
    contract_label: str | None = None
    lot_label: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    status: str = "active"


class AccountingMatrixContractUpdateIn(BaseModel):
    contract_label: str | None = None
    lot_label: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    status: str | None = None


# ---------------------------------------------------------------------------
# Snapshot facture (lecture seule pour la tranche minimale)
# ---------------------------------------------------------------------------
class AccountingMatrixSeedDomainOut(BaseModel):
    contracts_created: int
    contracts_skipped: int
    rules: int


class AccountingMatrixSeedOut(BaseModel):
    energy: AccountingMatrixSeedDomainOut
    cpe: AccountingMatrixSeedDomainOut
    versions_created: int


class ApplyInvoiceLineIn(BaseModel):
    billed_item: str | None = None
    site_code: str | None = None
    meter_id: str | None = None
    amount: float | None = None
    line_ref: str | None = None


class ApplyInvoiceIn(BaseModel):
    matrix_contract_id: int
    invoice_lines: list[ApplyInvoiceLineIn] = []


class ManualOverrideIn(BaseModel):
    snapshot_json: str
    motif: str = Field(..., min_length=1)


class InvoiceAccountingSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_source: str
    invoice_id: str
    matrix_contract_id: int | None = None
    matrix_version_id: int | None = None
    status: str
    snapshot_json: str | None = None
    exceptions_json: str | None = None
    validated_by_user_id: int | None = None
    validated_at: datetime | None = None
    exported_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
