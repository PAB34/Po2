"""Routes pour l'import et la consultation des references contractuelles DALKIA CPE."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.cpe_dalkia_db import (
    build_active_market_summary,
    get_active_imports,
    get_all_imports,
    get_ape_for_import,
    get_bpu_for_import,
    get_cibles_for_import,
    get_import_by_id,
    get_p2p3_for_import,
    get_recap_for_import,
    get_sites_for_import,
    persist_dalkia_import,
    sync_cpe_sites_from_dalkia,
    sync_p1_reference_from_recap,
)
from app.services.cpe_dalkia_import import build_import_preview, parse_dalkia_file
from app.services.cpe_dpgf_p1 import (
    get_active_dpgf_p1_imports,
    get_all_dpgf_p1_imports,
    parse_dpgf_p1_file,
    persist_dpgf_p1_import,
)

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
    classified: dict
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
        classified=preview.classified,
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


class ActiveMarketSummary(BaseModel):
    has_data: bool
    lot: int
    ref_year: int
    import_id: int | None = None
    filename: str | None = None
    import_date: str | None = None
    nb_sites: int | None = None
    nb_ape: int | None = None
    p1_gaz_ref_year_ht: float | None = None
    p1_elec_ref_year_ht: float | None = None
    p2_ref_year_ht: float | None = None
    p3_ref_year_ht: float | None = None
    marche_total_ht: float | None = None


@router.get("/imports/all", response_model=list[ImportBatchResponse])
def list_all_imports(
    lot: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ImportBatchResponse]:
    """Journal des imports maitres : toutes les versions (actives ET remplacees conservees)."""
    return [
        ImportBatchResponse(
            id=b.id, lot=b.lot, filename=b.filename, import_date=b.import_date.isoformat(),
            nb_sites=b.nb_sites, nb_p2p3_rows=b.nb_p2p3_rows, nb_cibles_rows=b.nb_cibles_rows,
            nb_p1_gaz_rows=b.nb_p1_gaz_rows, nb_ape_rows=b.nb_ape_rows, nb_recap_rows=b.nb_recap_rows,
            is_active=b.is_active, notes=b.notes,
        )
        for b in get_all_imports(db, current_user, lot=lot)
    ]


@router.get("/active-summary", response_model=ActiveMarketSummary)
def active_summary(
    lot: int = 1,
    ref_year: int = 2026,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActiveMarketSummary:
    """Synthese de l'etat du marche en vigueur (import maitre actif d'un lot)."""
    if lot not in (1, 2):
        raise HTTPException(status_code=400, detail="Le lot doit etre 1 ou 2.")
    return ActiveMarketSummary.model_validate(
        build_active_market_summary(db, current_user, lot, ref_year)
    )


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


class BpuRow(BaseModel):
    categorie: str
    famille: str | None
    code: str | None
    libelle: str | None
    specificite: str | None
    unite: str | None
    cout_unitaire: float | None
    cout_nuit: float | None
    cout_samedi: float | None
    cout_dimanche: float | None
    coefficient: float | None
    coefficient_max: float | None


@router.get("/imports/{import_id}/bpu", response_model=list[BpuRow])
def get_bpu(
    import_id: int,
    categorie: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BpuRow]:
    batch = get_import_by_id(db, import_id, current_user)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import introuvable.")
    rows = get_bpu_for_import(db, import_id, categorie)
    return [BpuRow(**{k: getattr(r, k) for k in BpuRow.model_fields}) for r in rows]


@router.post("/sync-cpe-sites")
def sync_cpe_sites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Initialise / met à jour les sites CPE (cpe_sites) depuis le référentiel DALKIA actif.

    Alimente le volet performance/intéressement (bilan, NB par année). Réexécutable après avenant.
    """
    return sync_cpe_sites_from_dalkia(db, city_id=current_user.city_id)


# ── DPGF P1 revise (livrable separe, lignee d'import propre) ─────────────────


class DpgfP1PreviewResponse(BaseModel):
    lot: int
    filename: str
    nb_lines: int
    nb_sites: dict[str, int]
    totals: dict[str, dict[str, float]]  # {level: {year: total}}
    warnings: list[str]


class DpgfP1ImportResponse(BaseModel):
    id: int
    lot: int
    filename: str
    import_date: str
    nb_lines: int
    is_active: bool
    notes: str | None


def _dpgf_totals_str_keys(totals: dict[int, dict]) -> dict[str, dict[str, float]]:
    return {lvl: {str(y): round(v, 2) for y, v in by_year.items()} for lvl, by_year in totals.items()}


@router.post("/dpgf-p1/preview", response_model=DpgfP1PreviewResponse)
async def preview_dpgf_p1(
    file: UploadFile = File(...),
    lot: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DpgfP1PreviewResponse:
    """Parse un DPGF P1 revise et renvoie un apercu (totaux par niveau x annee) sans rien ecrire."""
    if lot not in (1, 2):
        raise HTTPException(status_code=400, detail="Le lot doit etre 1 ou 2.")
    raw = await file.read()
    filename = file.filename or f"dpgf_p1_lot{lot}.xlsx"
    try:
        result = parse_dpgf_p1_file(raw, filename, lot)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DpgfP1PreviewResponse(
        lot=result.lot,
        filename=result.filename,
        nb_lines=len(result.lines),
        nb_sites=result.nb_sites,
        totals=_dpgf_totals_str_keys(result.totals),
        warnings=result.warnings,
    )


@router.post("/dpgf-p1/confirm", response_model=DpgfP1ImportResponse, status_code=status.HTTP_201_CREATED)
async def confirm_dpgf_p1(
    file: UploadFile = File(...),
    lot: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DpgfP1ImportResponse:
    """Persiste un DPGF P1 revise dans sa lignee propre.

    Ne desactive que le DPGF P1 precedent du meme lot ; ne touche jamais le referentiel maitre
    (P2/P3/APE/cibles/RECAP) ni cpe_contract_references.
    """
    if lot not in (1, 2):
        raise HTTPException(status_code=400, detail="Le lot doit etre 1 ou 2.")
    raw = await file.read()
    filename = file.filename or f"dpgf_p1_lot{lot}.xlsx"
    try:
        result = parse_dpgf_p1_file(raw, filename, lot)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    batch = persist_dpgf_p1_import(db, result, current_user)
    return DpgfP1ImportResponse(
        id=batch.id,
        lot=batch.lot,
        filename=batch.filename,
        import_date=batch.import_date.isoformat(),
        nb_lines=batch.nb_lines,
        is_active=batch.is_active,
        notes=batch.notes,
    )


def _dpgf_resp(b) -> "DpgfP1ImportResponse":
    return DpgfP1ImportResponse(
        id=b.id, lot=b.lot, filename=b.filename, import_date=b.import_date.isoformat(),
        nb_lines=b.nb_lines, is_active=b.is_active, notes=b.notes,
    )


@router.get("/dpgf-p1/imports", response_model=list[DpgfP1ImportResponse])
def list_dpgf_p1_imports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DpgfP1ImportResponse]:
    """Liste les imports DPGF P1 actifs (un par lot au plus)."""
    return [_dpgf_resp(b) for b in get_active_dpgf_p1_imports(db, current_user)]


@router.get("/dpgf-p1/imports/all", response_model=list[DpgfP1ImportResponse])
def list_all_dpgf_p1_imports(
    lot: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DpgfP1ImportResponse]:
    """Journal des DPGF P1 : toutes les versions (actives ET remplacees conservees)."""
    return [_dpgf_resp(b) for b in get_all_dpgf_p1_imports(db, current_user, lot=lot)]


@router.post("/imports/{import_id}/sync-p1-reference")
def sync_p1_reference(
    import_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Met a jour la reference d'acompte P1 gaz (cpe_contract_references) depuis le RECAP de l'import.

    Le controle d'acompte P1 lit cette reference : la synchro le rend auto-adaptatif aux avenants.
    """
    batch = get_import_by_id(db, import_id, current_user)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import introuvable.")
    return sync_p1_reference_from_recap(db, batch)
