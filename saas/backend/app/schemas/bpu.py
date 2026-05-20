"""
Schémas Pydantic pour l'API BPU (Bordereaux de Prix Unitaires).

Le modèle SQL est normalisé sur 5 tables ; ces schémas exposent la même
structure côté API plus quelques agrégats utiles à l'UI (timeline).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# --- Constantes exposées au frontend ----------------------------------------

EXTRACTION_STATUSES = (
    "ok", "ocr_ok", "ocr_review", "manual", "pending", "error",
)
SEGMENT_TYPES = ("tension", "site", "usage")
COMPONENT_TYPES = (
    "fourniture", "capacite", "cee", "go", "renouvelable", "autre",
)
PERIOD_CODES = (
    "BASE", "POINTE",
    "HPH", "HCH", "HPE", "HCE",
    "HPB", "HCB", "HP", "HC",
)
CHARGE_TYPES = (
    "abonnement", "branchement_provisoire", "contrat_temporaire", "autre",
)


# --- Read schemas (nested) --------------------------------------------------

class BpuPriceComponentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period_id: int
    component_type: str
    component_label: str | None = None
    price_value: Decimal
    price_unit: str
    price_value_eur_per_mwh: Decimal | None = None
    is_negative: bool = False
    extraction_confidence: Decimal | None = None
    notes: str | None = None


class BpuTimePeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    segment_id: int
    period_code: str
    period_label: str | None = None
    components: list[BpuPriceComponentRead] = []


class BpuSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    segment_type: str
    segment_code: str
    segment_label: str | None = None
    tension_category: str | None = None
    turpe_tariff: str | None = None
    usage_label: str | None = None
    notes: str | None = None
    periods: list[BpuTimePeriodRead] = []


class BpuFixedChargeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    segment_id: int | None = None
    charge_type: str
    charge_label: str | None = None
    charge_value: Decimal
    charge_unit: str
    charge_value_eur_per_month: Decimal | None = None
    applicable_from: date | None = None
    applicable_to: date | None = None
    notes: str | None = None


class BpuDocumentSummary(BaseModel):
    """Résumé pour la liste (sans relations imbriquées)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier: str
    valid_year: int
    valid_from: date | None = None
    valid_to: date | None = None
    market_subsequent: int | None = None
    lot_number: int
    amendment_number: int | None = None
    amendment_label: str | None = None
    pdf_filename: str
    pdf_relative_path: str | None = None
    signature_date: date | None = None
    extraction_status: str
    extraction_method: str | None = None
    extraction_confidence: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class BpuDocumentDetail(BpuDocumentSummary):
    """Détail complet : doc + segments imbriqués + frais fixes."""

    segments: list[BpuSegmentRead] = []
    fixed_charges: list[BpuFixedChargeRead] = []
    extraction_notes: str | None = None
    signatory_name: str | None = None
    signatory_role: str | None = None
    docusign_envelope_id: str | None = None


# --- Filters & queries ------------------------------------------------------

class BpuDocumentFilters(BaseModel):
    supplier: str | None = None
    valid_year: int | None = None
    lot_number: int | None = None
    market_subsequent: int | None = None
    extraction_status: str | None = None


class BpuTimelinePoint(BaseModel):
    """Un point pour le graphique d'évolution temporelle."""

    document_id: int
    supplier: str
    valid_year: int
    valid_from: date | None = None
    market_subsequent: int | None = None
    lot_number: int
    amendment_number: int | None = None
    segment_code: str
    period_code: str
    component_type: str
    price_value_eur_per_mwh: Decimal | None = None
    price_value: Decimal
    price_unit: str


class BpuTimelineQuery(BaseModel):
    component_type: str | None = None
    period_code: str | None = None
    segment_code: str | None = None
    supplier: str | None = None
    lot_number: int | None = None


# --- Import / write schemas (admin) -----------------------------------------

class BpuImportRequest(BaseModel):
    """Body pour POST /api/bpu/import."""

    source_dir: str | None = Field(
        default=None,
        description="Répertoire source côté serveur. Si vide, utilise le défaut du service.",
    )
    only_filename: str | None = Field(
        default=None,
        description="Si fourni, n'importe que ce fichier (debug).",
    )
    force: bool = Field(
        default=False,
        description="Si True, ré-importe même les BPU déjà présents (replace).",
    )
    enable_ocr: bool = Field(
        default=True,
        description="Si False, skip les PDFs scannés et marque-les pending.",
    )


class BpuImportResult(BaseModel):
    filename: str
    status: str  # ok | ocr_ok | ocr_review | error | skipped
    document_id: int | None = None
    segments_count: int = 0
    components_count: int = 0
    fixed_charges_count: int = 0
    extraction_method: str | None = None
    extraction_confidence: float | None = None
    error: str | None = None


# --- Update / Create schemas pour le tableau editable -----------------------

class BpuPriceComponentUpdate(BaseModel):
    """Mise à jour partielle d'un composant de prix."""

    component_type: str | None = None
    component_label: str | None = None
    price_value: Decimal | None = None
    price_unit: str | None = None
    price_value_eur_per_mwh: Decimal | None = None
    is_negative: bool | None = None
    notes: str | None = None


class BpuPriceComponentCreate(BaseModel):
    period_id: int
    component_type: str
    component_label: str | None = None
    price_value: Decimal
    price_unit: str
    price_value_eur_per_mwh: Decimal | None = None
    is_negative: bool = False
    notes: str | None = None


class BpuTimePeriodUpdate(BaseModel):
    period_code: str | None = None
    period_label: str | None = None


class BpuTimePeriodCreate(BaseModel):
    segment_id: int
    period_code: str
    period_label: str | None = None


class BpuSegmentUpdate(BaseModel):
    segment_type: str | None = None
    segment_code: str | None = None
    segment_label: str | None = None
    tension_category: str | None = None
    turpe_tariff: str | None = None
    usage_label: str | None = None
    notes: str | None = None


class BpuSegmentCreate(BaseModel):
    document_id: int
    segment_type: str
    segment_code: str
    segment_label: str | None = None
    tension_category: str | None = None
    turpe_tariff: str | None = None
    usage_label: str | None = None
    notes: str | None = None


class BpuFixedChargeUpdate(BaseModel):
    segment_id: int | None = None
    charge_type: str | None = None
    charge_label: str | None = None
    charge_value: Decimal | None = None
    charge_unit: str | None = None
    charge_value_eur_per_month: Decimal | None = None
    applicable_from: date | None = None
    applicable_to: date | None = None
    notes: str | None = None


class BpuFixedChargeCreate(BaseModel):
    document_id: int
    segment_id: int | None = None
    charge_type: str
    charge_label: str | None = None
    charge_value: Decimal
    charge_unit: str
    charge_value_eur_per_month: Decimal | None = None
    applicable_from: date | None = None
    applicable_to: date | None = None
    notes: str | None = None


class BpuDocumentUpdate(BaseModel):
    """Mise à jour partielle des métadonnées d'un BPU."""

    supplier: str | None = None
    valid_year: int | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    market_subsequent: int | None = None
    lot_number: int | None = None
    amendment_number: int | None = None
    amendment_label: str | None = None
    signature_date: date | None = None
    signatory_name: str | None = None
    signatory_role: str | None = None
    extraction_status: str | None = None
    extraction_notes: str | None = None


class BpuEditableRow(BaseModel):
    """Une ligne "wide" prête pour le tableau éditable (jointure pré-calculée)."""

    # Identifiants pour PATCH
    component_id: int
    period_id: int
    segment_id: int
    document_id: int

    # Métadonnées document
    supplier: str
    valid_year: int
    market_subsequent: int | None = None
    lot_number: int
    amendment_number: int | None = None
    amendment_label: str | None = None
    pdf_filename: str

    # Segment
    segment_type: str
    segment_code: str
    segment_label: str | None = None
    tension_category: str | None = None
    turpe_tariff: str | None = None

    # Poste
    period_code: str
    period_label: str | None = None

    # Composante
    component_type: str
    component_label: str | None = None
    price_value: Decimal
    price_unit: str
    price_value_eur_per_mwh: Decimal | None = None
    is_negative: bool = False
    notes: str | None = None


class BpuImportResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    skipped: int
    results: list[BpuImportResult]
