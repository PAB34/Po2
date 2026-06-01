"""Routes pour l'import et la consultation des references contractuelles DALKIA CPE."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.cpe_dalkia_db import (
    get_active_imports,
    get_ape_for_import,
    get_cibles_for_import,
    get_import_by_id,
    get_p2p3_for_import,
    get_recap_for_import,
    get_sites_for_import,
    persist_dalkia_import,
)
from app.services.cpe_dalkia_import import build_import_preview, parse_dalkia_file

router = APIRouter(prefix="/cpe/dalkia-ref", tags=["cpe-dalkia"])


# ── Schemas de reponse ──────────────────────────────────────────────────────


class ImportPreviewResponse(BaseModel):
    lot: int
    filename: str
    nb_sites: int
    nb_p2p3_rows: int
    nb_cibles_rows: int
    nb_p1_gaz_rows: int
    nb_ape_rows: int
    nb_recap_rows: int
    recap_summary: dict
    period_labels: list[str]
    sample_sites: list[dict]
    warnings: list[str]


class ImportBatchResponse(BaseModel):
    id: int
    lot: int
    filename: str
    import_date: str
    nb_sites: int
    nb_p2p3_rows: int
    nb_cibles_rows: int
    nb_p1_gaz_rows: int
    nb_ape_rows: int
    nb_recap_rows: int
    is_active: bool
    notes: str | None


class RecapRow(BaseModel):
    section: str
    category: str
    metric: str
    metric_label: str | None
    period_year: int | None
    period_label: str | None
    value: float | None
    unit: str | None


class SiteResponse(BaseModel):
    code_site: str
    nom_batiment: str
    entite: str | None
    lot: int
    lot_label: str | None


class P2P3Row(BaseModel):
    code_site: str
    period_idx: int
    period_label: str
    period_year: int
    p2_1_ht: float | None
    p2_2_ht: float | None
    p2_3_ht: float | None
    p2_4_ht: float | None
    p2_total_ht: float | None
    p3_1_ht: float | None
    p3_2_ht: float | None
    p3_3_ht: float | None
    p3_4_ht: float | None
    p3_total_ht: float | None


class CibleRow(BaseModel):
    code_site: str
    fluid: str
    period_idx: int
    period_label: str
    period_year: int
    ref_globale_mwhpci: float | None
    ref_qt_mwhpci: float | None
    dju_reference: float | None
    qt_global_mwhpci: float | None
    nb_mwhpci: float | None
    q_ecs: float | None
    qt_ecs: float | None


class ApeRow(BaseModel):
    code_site: str
    nom_batiment: str | None
    situation_initiale_mwhpci: float | None
    description_ape: str | None
    annee_achevement: int | None
    montant_ape_ht: float | None
    cee_mwh_cumac: float | None
    cee_eur: float | None
    gain_energetique_mwhpci: float | None
    situation_nouvelle_mwhpci: float | None
    annee_engagement_nouvelle_cible: int | None
    emission_co2_evitee: float | None
    commentaires: str | None


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/preview", response_model=ImportPreviewResponse)
async def preview_import(
    file: UploadFile = File(...),
    lot: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportPreviewResponse:
    """
    Parse le fichier DALKIA et retourne un apercu sans rien sauvegarder.
    Appeler cet endpoint avant /confirm pour valider le contenu.
    """
    if lot not in (1, 2):
        raise HTTPException(status_code=400, detail="Le lot doit etre 1 ou 2.")
    raw = await file.read()
    filename = file.filename or f"dalkia_lot{lot}.xlsx"
    try:
        result = parse_dalkia_file(raw, filename, lot)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    preview = build_import_preview(result)
    return ImportPreviewResponse(
        lot=preview.lot,
        filename=preview.filename,
        nb_sites=preview.nb_sites,
        nb_p2p3_rows=preview.nb_p2p3_rows,
        nb_cibles_rows=preview.nb_cibles_rows,
        nb_p1_gaz_rows=preview.nb_p1_gaz_rows,
        nb_ape_rows=preview.nb_ape_rows,
        nb_recap_rows=preview.nb_recap_rows,
        recap_summary=preview.recap_summary,
        period_labels=preview.period_labels,
        sample_sites=preview.sample_sites,
        warnings=preview.warnings,
    )


@router.post("/confirm", response_model=ImportBatchResponse, status_code=status.HTTP_201_CREATED)
async def confirm_import(
    file: UploadFile = File(...),
    lot: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportBatchResponse:
    """
    Parse et persiste le fichier DALKIA.
    Les imports precedents du meme lot sont marques inactifs.
    """
    if lot not in (1, 2):
        raise HTTPException(status_code=400, detail="Le lot doit etre 1 ou 2.")
    raw = await file.read()
    filename = file.filename or f"dalkia_lot{lot}.xlsx"
    try:
        result = parse_dalkia_file(raw, filename, lot)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    batch = persist_dalkia_import(db, result, current_user, deactivate_previous=True)
    return ImportBatchResponse(
        id=batch.id,
        lot=batch.lot,
        filename=batch.filename,
        import_date=batch.import_date.isoformat(),
        nb_sites=batch.nb_sites,
        nb_p2p3_rows=batch.nb_p2p3_rows,
        nb_cibles_rows=batch.nb_cibles_rows,
        nb_p1_gaz_rows=batch.nb_p1_gaz_rows,
        nb_ape_rows=batch.nb_ape_rows,
        nb_recap_rows=batch.nb_recap_rows,
        is_active=batch.is_active,
        notes=batch.notes,
    )


@router.get("/imports", response_model=list[ImportBatchResponse])
def list_imports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ImportBatchResponse]:
    """Liste tous les imports actifs."""
    batches = get_active_imports(db, current_user)
    return [
        ImportBatchResponse(
            id=b.id,
            lot=b.lot,
            filename=b.filename,
            import_date=b.import_date.isoformat(),
            nb_sites=b.nb_sites,
            nb_p2p3_rows=b.nb_p2p3_rows,
            nb_cibles_rows=b.nb_cibles_rows,
            nb_p1_gaz_rows=b.nb_p1_gaz_rows,
            nb_ape_rows=b.nb_ape_rows,
            nb_recap_rows=b.nb_recap_rows,
            is_active=b.is_active,
            notes=b.notes,
        )
        for b in batches
    ]


@router.get("/imports/{import_id}/sites", response_model=list[SiteResponse])
def get_sites(
    import_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SiteResponse]:
    batch = get_import_by_id(db, import_id, current_user)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import introuvable.")
    return [
        SiteResponse(
            code_site=s.code_site,
            nom_batiment=s.nom_batiment,
            entite=s.entite,
            lot=s.lot,
            lot_label=s.lot_label,
        )
        for s in get_sites_for_import(db, import_id)
    ]


@router.get("/imports/{import_id}/p2p3", response_model=list[P2P3Row])
def get_p2p3(
    import_id: int,
    period_year: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[P2P3Row]:
    batch = get_import_by_id(db, import_id, current_user)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import introuvable.")
    rows = get_p2p3_for_import(db, import_id, period_year)
    return [P2P3Row(**{k: getattr(r, k) for k in P2P3Row.model_fields}) for r in rows]


@router.get("/imports/{import_id}/cibles", response_model=list[CibleRow])
def get_cibles(
    import_id: int,
    fluid: str | None = None,
    period_year: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CibleRow]:
    batch = get_import_by_id(db, import_id, current_user)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import introuvable.")
    rows = get_cibles_for_import(db, import_id, fluid, period_year)
    return [CibleRow(**{k: getattr(r, k) for k in CibleRow.model_fields}) for r in rows]


@router.get("/imports/{import_id}/ape", response_model=list[ApeRow])
def get_ape(
    import_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApeRow]:
    batch = get_import_by_id(db, import_id, current_user)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import introuvable.")
    rows = get_ape_for_import(db, import_id)
    return [ApeRow(**{k: getattr(r, k) for k in ApeRow.model_fields}) for r in rows]


@router.get("/imports/{import_id}/recap", response_model=list[RecapRow])
def get_recap(
    import_id: int,
    section: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RecapRow]:
    batch = get_import_by_id(db, import_id, current_user)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import introuvable.")
    rows = get_recap_for_import(db, import_id, section)
    return [RecapRow(**{k: getattr(r, k) for k in RecapRow.model_fields}) for r in rows]
