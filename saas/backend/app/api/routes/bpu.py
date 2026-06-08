"""
Endpoints HTTP pour le suivi temporel des BPU (Bordereaux de Prix Unitaires).

Cette API expose la même structure de formule que le calcul de tarification
déjà implémenté dans /energie/preconisations (cf. BillingBpuLine) :

    PU_total (€HTT/MWh) = PU_fourniture + PU_capacité + PU_CEE + PU_GO

Par tranche tarifaire TURPE (CU / CU4 / MU4 / MUDT / C4 / C2 / EP ...) et par
poste horosaisonnier (base / pointe / hph / hch / hpe / hce / hp / hc).

L'objectif est de pouvoir suivre l'évolution **dans le temps** (2021 → 2026)
de chaque composante de la formule, pour chaque (segment, poste).

Endpoints :

- GET    /api/bpu/formula             → définition de la formule + nomenclature
- GET    /api/bpu/documents           → liste filtrable des BPU
- GET    /api/bpu/documents/{id}      → détail complet d'un BPU
- DELETE /api/bpu/documents/{id}      → supprime un BPU (admin)
- GET    /api/bpu/timeline            → série temporelle pour un graphique
- POST   /api/bpu/import              → re-déclenche l'import (admin)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.bpu import (
    BpuDocument,
    BpuFixedCharge,
    BpuPriceComponent,
    BpuSegment,
    BpuTimePeriod,
    COMPONENT_TYPES,
    PERIOD_CODES,
)
from app.models.user import User
from app.schemas.bpu import (
    BpuDocumentDetail,
    BpuDocumentSummary,
    BpuDocumentUpdate,
    BpuEditableRow,
    BpuFixedChargeCreate,
    BpuFixedChargeRead,
    BpuFixedChargeUpdate,
    BpuImportRequest,
    BpuImportResponse,
    BpuImportResult,
    BpuPriceComponentCreate,
    BpuPriceComponentRead,
    BpuPriceComponentUpdate,
    BpuSegmentCreate,
    BpuSegmentRead,
    BpuSegmentUpdate,
    BpuTurpeEvolutionPoint,
    BpuTimelinePoint,
    BpuTimePeriodCreate,
    BpuTimePeriodRead,
    BpuTimePeriodUpdate,
    BpuXlsxImportRequest,
    BpuXlsxImportResponse,
)
from app.services.bpu import (
    DEFAULT_BPU_SOURCE_DIR,
    import_directory,
)
from app.services.turpe import list_turpe_evolution_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bpu", tags=["bpu"])


# ---------------------------------------------------------------------------
# Formule de calcul (constantes exposées au frontend pour la légende du graphe)
# ---------------------------------------------------------------------------

# Doit rester aligné avec BillingBpuLine côté facturation
# (pu_fourniture + pu_capacite + pu_cee + pu_go = pu_total)
PRICING_FORMULA = {
    "expression": "PU_total = PU_fourniture + PU_capacite + PU_cee + PU_go",
    "unit_target": "€HTT/MWh",
    "components": [
        {
            "code": "fourniture",
            "label": "Fourniture",
            "description": (
                "Prix de l'énergie pure facturée par le fournisseur "
                "(EDF/ENGIE). C'est la composante la plus volatile, suit "
                "le marché de gros."
            ),
        },
        {
            "code": "capacite",
            "label": "Capacité",
            "description": (
                "Mécanisme de capacité — coût du droit à soutirer en pointe. "
                "Fixé par RTE chaque année."
            ),
        },
        {
            "code": "cee",
            "label": "CEE",
            "description": (
                "Certificats d'Économies d'Énergie — coût de l'obligation "
                "réglementaire portée par le fournisseur."
            ),
        },
        {
            "code": "go",
            "label": "Garanties d'Origine",
            "description": (
                "Option Renouvelable — surcoût pour énergie verte certifiée. "
                "Optionnel mais souscrit par défaut sur les marchés Hérault "
                "Énergies."
            ),
        },
    ],
    "segments": [
        {"code": "CU", "label": "Courte Utilisation (BT ≤ 36 kVA, base)"},
        {"code": "LU", "label": "Longue Utilisation (BT ≤ 36 kVA, base)"},
        {"code": "CU4", "label": "Courte Utilisation 4 plages (HPH/HCH/HPE/HCE)"},
        {"code": "MU4", "label": "Moyenne Utilisation 4 plages"},
        {"code": "MUDT", "label": "Moyenne Utilisation Double Tarif (HP/HC)"},
        {"code": "C4", "label": "BT > 36 kVA 4 plages"},
        {"code": "C2", "label": "HTA 5 plages (Pointe + 4 plages)"},
        {"code": "T1", "label": "Gaz T1 - moins de 6 000 kWh/an"},
        {"code": "T2", "label": "Gaz T2 - 6 000 a 300 000 kWh/an"},
        {"code": "T3", "label": "Gaz T3 - 300 000 a 5 000 000 kWh/an"},
        {"code": "T4", "label": "Gaz T4 - plus de 5 000 000 kWh/an"},
        {"code": "EP", "label": "Éclairage Public"},
    ],
    "periods": [
        {"code": "BASE", "label": "Base (toute heure)"},
        {"code": "POINTE", "label": "Pointe (heures de tension réseau)"},
        {"code": "HPH", "label": "Heures Pleines Hiver"},
        {"code": "HCH", "label": "Heures Creuses Hiver"},
        {"code": "HPE", "label": "Heures Pleines Été"},
        {"code": "HCE", "label": "Heures Creuses Été"},
        {"code": "HP", "label": "Heures Pleines (double tarif)"},
        {"code": "HC", "label": "Heures Creuses (double tarif)"},
    ],
}


@router.get("/formula")
def get_formula(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Définition de la formule de tarification + nomenclature.

    Sert au frontend pour rendre la légende et les filtres du graphique
    d'évolution temporelle.
    """
    return PRICING_FORMULA


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@router.get("/documents", response_model=list[BpuDocumentSummary])
def list_documents(
    supplier: str | None = Query(None, description="Filtre fournisseur (EDF, ENGIE)"),
    valid_year: int | None = Query(None, ge=2020, le=2030),
    lot_number: int | None = Query(None, ge=1, le=10),
    market_subsequent: int | None = Query(None, ge=1, le=10),
    extraction_status: str | None = Query(None, description="ok|ocr_ok|ocr_review|manual|pending|error"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BpuDocumentSummary]:
    q = db.query(BpuDocument)
    if supplier:
        q = q.filter(BpuDocument.supplier == supplier.upper())
    if valid_year is not None:
        q = q.filter(BpuDocument.valid_year == valid_year)
    if lot_number is not None:
        q = q.filter(BpuDocument.lot_number == lot_number)
    if market_subsequent is not None:
        q = q.filter(BpuDocument.market_subsequent == market_subsequent)
    if extraction_status:
        q = q.filter(BpuDocument.extraction_status == extraction_status)

    q = q.order_by(
        BpuDocument.valid_year.desc(),
        BpuDocument.supplier.asc(),
        BpuDocument.lot_number.asc(),
        BpuDocument.amendment_number.asc().nullsfirst(),
    )

    return [BpuDocumentSummary.model_validate(d) for d in q.all()]


@router.get("/documents/{document_id}", response_model=BpuDocumentDetail)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BpuDocumentDetail:
    doc = (
        db.query(BpuDocument)
        .options(
            joinedload(BpuDocument.segments)
            .joinedload(BpuSegment.periods)
            .joinedload(BpuTimePeriod.components),
            joinedload(BpuDocument.fixed_charges),
        )
        .filter(BpuDocument.id == document_id)
        .one_or_none()
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BPU introuvable")
    return BpuDocumentDetail.model_validate(doc)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    doc = db.query(BpuDocument).filter(BpuDocument.id == document_id).one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BPU introuvable")
    db.delete(doc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Timeline (évolution temporelle des composantes de la formule)
# ---------------------------------------------------------------------------


@router.get("/timeline", response_model=list[BpuTimelinePoint])
def get_timeline(
    component_type: str | None = Query(
        None,
        description=(
            "Filtre composante (fourniture, capacite, cee, go, renouvelable). "
            "Si vide, retourne toutes les composantes — le frontend filtre."
        ),
    ),
    period_code: str | None = Query(
        None, description="Filtre poste (BASE, HPH, HCH, HPE, HCE, POINTE, HP, HC)"
    ),
    segment_code: str | None = Query(
        None, description="Filtre tarif TURPE (CU, CU4, MU4, MUDT, C4, C2, EP)"
    ),
    supplier: str | None = Query(None, description="EDF ou ENGIE"),
    lot_number: int | None = Query(None, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BpuTimelinePoint]:
    """Série temporelle d'évolution des composantes de la formule de prix.

    Retourne une ligne par (BPU, segment, période, composante). Le frontend
    agrège ensuite par année/composante pour tracer une courbe par
    composante (Fourniture, Capacité, CEE, GO) — et optionnellement la
    somme = PU_total.

    Tri : par année croissante puis par fournisseur — facilite le binding
    direct dans Recharts (axe X = valid_year).
    """
    # Validations
    if component_type and component_type not in COMPONENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"component_type doit être l'un de {sorted(COMPONENT_TYPES)}",
        )
    if period_code and period_code.upper() not in PERIOD_CODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"period_code doit être l'un de {sorted(PERIOD_CODES)}",
        )

    q = (
        db.query(BpuDocument, BpuSegment, BpuTimePeriod, BpuPriceComponent)
        .join(BpuSegment, BpuSegment.document_id == BpuDocument.id)
        .join(BpuTimePeriod, BpuTimePeriod.segment_id == BpuSegment.id)
        .join(BpuPriceComponent, BpuPriceComponent.period_id == BpuTimePeriod.id)
    )

    if supplier:
        q = q.filter(BpuDocument.supplier == supplier.upper())
    if lot_number is not None:
        q = q.filter(BpuDocument.lot_number == lot_number)
    if segment_code:
        q = q.filter(BpuSegment.segment_code == segment_code.upper())
    if period_code:
        q = q.filter(BpuTimePeriod.period_code == period_code.upper())
    if component_type:
        q = q.filter(BpuPriceComponent.component_type == component_type)

    q = q.order_by(
        BpuDocument.valid_year.asc(),
        BpuDocument.supplier.asc(),
        BpuDocument.lot_number.asc(),
        BpuSegment.segment_code.asc(),
        BpuTimePeriod.period_code.asc(),
        BpuPriceComponent.component_type.asc(),
    )

    rows = q.all()

    return [
        BpuTimelinePoint(
            document_id=d.id,
            supplier=d.supplier,
            valid_year=d.valid_year,
            valid_from=d.valid_from,
            market_subsequent=d.market_subsequent,
            lot_number=d.lot_number,
            amendment_number=d.amendment_number,
            segment_code=s.segment_code,
            period_code=p.period_code,
            component_type=c.component_type,
            price_value_eur_per_mwh=c.price_value_eur_per_mwh,
            price_value=c.price_value,
            price_unit=c.price_unit,
        )
        for d, s, p, c in rows
    ]


@router.get("/turpe-evolution", response_model=list[BpuTurpeEvolutionPoint])
def get_turpe_evolution(
    current_user: User = Depends(get_current_user),
) -> list[BpuTurpeEvolutionPoint]:
    """Evolution moyenne du niveau TURPE HTA-BT issue des decisions CRE.

    Cette serie ne remplace pas le bareme detaille utilise pour controler les
    factures. Elle sert a visualiser le contexte reglementaire qui influence la
    part acheminement des prix d'electricite.
    """
    return [BpuTurpeEvolutionPoint(**event) for event in list_turpe_evolution_events()]


# ---------------------------------------------------------------------------
# Import (admin)
# ---------------------------------------------------------------------------


@router.post("/import", response_model=BpuImportResponse)
def trigger_import(
    payload: BpuImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BpuImportResponse:
    """Re-déclenche l'import depuis le répertoire serveur.

    Réservé aux admins : tout user connecté peut le lancer pour l'instant
    (à durcir si nécessaire avec un `if not current_user.is_admin`).
    """
    source = Path(payload.source_dir) if payload.source_dir else DEFAULT_BPU_SOURCE_DIR
    if not source.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Répertoire introuvable côté serveur : {source}",
        )

    try:
        results = import_directory(
            db,
            source_dir=source,
            only_filename=payload.only_filename,
            enable_ocr=payload.enable_ocr,
            force=payload.force,
            imported_by_user_id=current_user.id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Import BPU a échoué")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur d'import : {type(exc).__name__}: {exc}",
        )

    payload_results = [
        BpuImportResult(
            filename=r.filename,
            status=r.status,
            document_id=r.document_id,
            segments_count=r.segments_count,
            components_count=r.components_count,
            fixed_charges_count=r.fixed_charges_count,
            extraction_method=r.extraction_method,
            extraction_confidence=r.extraction_confidence,
            error=r.error,
        )
        for r in results
    ]

    succeeded = sum(1 for r in results if r.status in {"ok", "ocr_ok", "ocr_review"})
    failed = sum(1 for r in results if r.status == "error")
    skipped = sum(1 for r in results if r.status == "skipped")

    return BpuImportResponse(
        total=len(results),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        results=payload_results,
    )


@router.post("/import-xlsx", response_model=BpuXlsxImportResponse)
def trigger_xlsx_import(
    payload: BpuXlsxImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BpuXlsxImportResponse:
    """Importe le fichier de référence `extraction_tarifs_electricite_BPU.xlsx`.

    C'est la **source de vérité** (extraction manuelle validée, confiance 1.0),
    à privilégier sur l'ingestion PDF/OCR. Le fichier est lu côté serveur depuis
    le dépôt monté en read-only (`/workspace`). `force=True` (défaut) remplace
    les BPU déjà présents pour les PDFs listés dans l'onglet `Sources_PDF`.
    """
    # Import différé : la dépendance pandas n'est tirée qu'à l'appel.
    from app.scripts.import_bpu_xlsx import DEFAULT_XLSX, import_xlsx

    if not DEFAULT_XLSX.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fichier xlsx introuvable côté serveur : {DEFAULT_XLSX}",
        )

    try:
        counters = import_xlsx(DEFAULT_XLSX, force=payload.force)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Import BPU xlsx a échoué")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur d'import xlsx : {type(exc).__name__}: {exc}",
        )

    return BpuXlsxImportResponse(**counters)


# ---------------------------------------------------------------------------
# Tableau éditable — endpoint dédié qui aplatit la hiérarchie 5 tables en
# 1 ligne par BpuPriceComponent. Utilisé par le sous-onglet "Édition" de
# /energie/bpu côté frontend.
# ---------------------------------------------------------------------------


@router.get("/editable-rows", response_model=list[BpuEditableRow])
def get_editable_rows(
    document_id: int | None = Query(None, description="Filtre sur un BPU précis"),
    supplier: str | None = Query(None),
    valid_year: int | None = Query(None, ge=2020, le=2030),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BpuEditableRow]:
    """Retourne le tableau éditable : 1 ligne par BpuPriceComponent, déjà joint
    avec son document/segment/période. Tri par year/supplier/lot/segment/poste
    pour un affichage cohérent en tableau Excel-like.
    """
    q = (
        db.query(BpuDocument, BpuSegment, BpuTimePeriod, BpuPriceComponent)
        .join(BpuSegment, BpuSegment.document_id == BpuDocument.id)
        .join(BpuTimePeriod, BpuTimePeriod.segment_id == BpuSegment.id)
        .join(BpuPriceComponent, BpuPriceComponent.period_id == BpuTimePeriod.id)
    )
    if document_id is not None:
        q = q.filter(BpuDocument.id == document_id)
    if supplier:
        q = q.filter(BpuDocument.supplier == supplier.upper())
    if valid_year is not None:
        q = q.filter(BpuDocument.valid_year == valid_year)

    q = q.order_by(
        BpuDocument.valid_year.asc(),
        BpuDocument.supplier.asc(),
        BpuDocument.lot_number.asc(),
        BpuDocument.amendment_number.asc().nullsfirst(),
        BpuSegment.segment_code.asc(),
        BpuTimePeriod.period_code.asc(),
        BpuPriceComponent.component_type.asc(),
    )

    rows = q.all()
    return [
        BpuEditableRow(
            component_id=c.id,
            period_id=p.id,
            segment_id=s.id,
            document_id=d.id,
            supplier=d.supplier,
            valid_year=d.valid_year,
            market_subsequent=d.market_subsequent,
            lot_number=d.lot_number,
            amendment_number=d.amendment_number,
            amendment_label=d.amendment_label,
            pdf_filename=d.pdf_filename,
            segment_type=s.segment_type,
            segment_code=s.segment_code,
            segment_label=s.segment_label,
            tension_category=s.tension_category,
            turpe_tariff=s.turpe_tariff,
            period_code=p.period_code,
            period_label=p.period_label,
            component_type=c.component_type,
            component_label=c.component_label,
            price_value=c.price_value,
            price_unit=c.price_unit,
            price_value_eur_per_mwh=c.price_value_eur_per_mwh,
            is_negative=c.is_negative,
            notes=c.notes,
        )
        for d, s, p, c in rows
    ]


# ---------------------------------------------------------------------------
# CRUD BpuDocument
# ---------------------------------------------------------------------------


@router.patch("/documents/{document_id}", response_model=BpuDocumentSummary)
def update_document(
    document_id: int,
    payload: BpuDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BpuDocumentSummary:
    doc = db.query(BpuDocument).filter(BpuDocument.id == document_id).one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BPU introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(doc, field, value)
    db.commit()
    db.refresh(doc)
    return BpuDocumentSummary.model_validate(doc)


# ---------------------------------------------------------------------------
# CRUD BpuSegment
# ---------------------------------------------------------------------------


@router.post("/segments", response_model=BpuSegmentRead, status_code=status.HTTP_201_CREATED)
def create_segment(
    payload: BpuSegmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BpuSegmentRead:
    doc = db.query(BpuDocument).filter(BpuDocument.id == payload.document_id).one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BPU document introuvable")
    seg = BpuSegment(**payload.model_dump())
    db.add(seg)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    db.refresh(seg)
    return BpuSegmentRead.model_validate(seg)


@router.patch("/segments/{segment_id}", response_model=BpuSegmentRead)
def update_segment(
    segment_id: int,
    payload: BpuSegmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BpuSegmentRead:
    seg = db.query(BpuSegment).filter(BpuSegment.id == segment_id).one_or_none()
    if seg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(seg, field, value)
    db.commit()
    db.refresh(seg)
    return BpuSegmentRead.model_validate(seg)


@router.delete("/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_segment(
    segment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    seg = db.query(BpuSegment).filter(BpuSegment.id == segment_id).one_or_none()
    if seg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment introuvable")
    db.delete(seg)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# CRUD BpuTimePeriod
# ---------------------------------------------------------------------------


@router.post("/periods", response_model=BpuTimePeriodRead, status_code=status.HTTP_201_CREATED)
def create_period(
    payload: BpuTimePeriodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BpuTimePeriodRead:
    seg = db.query(BpuSegment).filter(BpuSegment.id == payload.segment_id).one_or_none()
    if seg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment introuvable")
    period = BpuTimePeriod(**payload.model_dump())
    db.add(period)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    db.refresh(period)
    return BpuTimePeriodRead.model_validate(period)


@router.patch("/periods/{period_id}", response_model=BpuTimePeriodRead)
def update_period(
    period_id: int,
    payload: BpuTimePeriodUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BpuTimePeriodRead:
    period = db.query(BpuTimePeriod).filter(BpuTimePeriod.id == period_id).one_or_none()
    if period is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Periode introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(period, field, value)
    db.commit()
    db.refresh(period)
    return BpuTimePeriodRead.model_validate(period)


@router.delete("/periods/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    period = db.query(BpuTimePeriod).filter(BpuTimePeriod.id == period_id).one_or_none()
    if period is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Periode introuvable")
    db.delete(period)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# CRUD BpuPriceComponent (le plus important pour le tableau éditable)
# ---------------------------------------------------------------------------


@router.post("/components", response_model=BpuPriceComponentRead, status_code=status.HTTP_201_CREATED)
def create_component(
    payload: BpuPriceComponentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BpuPriceComponentRead:
    period = db.query(BpuTimePeriod).filter(BpuTimePeriod.id == payload.period_id).one_or_none()
    if period is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Periode introuvable")
    comp = BpuPriceComponent(**payload.model_dump())
    db.add(comp)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    db.refresh(comp)
    return BpuPriceComponentRead.model_validate(comp)


@router.patch("/components/{component_id}", response_model=BpuPriceComponentRead)
def update_component(
    component_id: int,
    payload: BpuPriceComponentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BpuPriceComponentRead:
    comp = db.query(BpuPriceComponent).filter(BpuPriceComponent.id == component_id).one_or_none()
    if comp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Composante introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(comp, field, value)
    # Auto-recalcul price_value_eur_per_mwh si l'unité ou la valeur change et si pas explicitement fourni
    if (
        "price_value_eur_per_mwh" not in payload.model_dump(exclude_unset=True)
        and (payload.price_value is not None or payload.price_unit is not None)
    ):
        unit = (comp.price_unit or "").lower().replace(" ", "")
        try:
            v = float(comp.price_value)
            if "c€/kwh" in unit or "ce/kwh" in unit:
                comp.price_value_eur_per_mwh = v * 10.0
            elif "€/mwh" in unit or "eur/mwh" in unit:
                comp.price_value_eur_per_mwh = v
        except (ValueError, TypeError):
            pass
    if payload.price_value is not None:
        comp.is_negative = comp.price_value < 0
    db.commit()
    db.refresh(comp)
    return BpuPriceComponentRead.model_validate(comp)


@router.delete("/components/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_component(
    component_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    comp = db.query(BpuPriceComponent).filter(BpuPriceComponent.id == component_id).one_or_none()
    if comp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Composante introuvable")
    db.delete(comp)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# CRUD BpuFixedCharge
# ---------------------------------------------------------------------------


@router.post("/charges", response_model=BpuFixedChargeRead, status_code=status.HTTP_201_CREATED)
def create_charge(
    payload: BpuFixedChargeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BpuFixedChargeRead:
    doc = db.query(BpuDocument).filter(BpuDocument.id == payload.document_id).one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BPU document introuvable")
    charge = BpuFixedCharge(**payload.model_dump())
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return BpuFixedChargeRead.model_validate(charge)


@router.patch("/charges/{charge_id}", response_model=BpuFixedChargeRead)
def update_charge(
    charge_id: int,
    payload: BpuFixedChargeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BpuFixedChargeRead:
    charge = db.query(BpuFixedCharge).filter(BpuFixedCharge.id == charge_id).one_or_none()
    if charge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frais fixe introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(charge, field, value)
    db.commit()
    db.refresh(charge)
    return BpuFixedChargeRead.model_validate(charge)


@router.delete("/charges/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_charge(
    charge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    charge = db.query(BpuFixedCharge).filter(BpuFixedCharge.id == charge_id).one_or_none()
    if charge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frais fixe introuvable")
    db.delete(charge)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
