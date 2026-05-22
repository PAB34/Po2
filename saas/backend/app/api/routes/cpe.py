"""Routes API CPE DALKIA — Contrat de Performance Énergétique."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.cpe import (
    CpeBilanAnnuel,
    CpeDjuAnnuel,
    CpeFinanceImportBatchDetail,
    CpeFinanceImportBatchOut,
    CpeFinanceLineOut,
    CpeFinancePreview,
    CpeGazReleve,
    CpeGazReleveCreate,
    CpeGazReleveUpdate,
    CpeImportResult,
    CpePrixGazCreate,
    CpePrixGazOut,
    CpeResultatAnnuelOut,
    CpeSiteCreate,
    CpeSiteOut,
    CpeSiteUpdate,
)
from app.services import cpe as svc
from app.services.cpe_finance_imports import (
    create_finance_batch_from_bytes,
    finance_batch_detail,
    get_finance_batch,
    list_finance_batches,
    list_finance_lines,
)
from app.services.cpe_finance_preview import preview_finance_export
from app.services.cpe_import import import_releves_csv

router = APIRouter(prefix="/cpe", tags=["cpe"])


def _require_city(current_user: User) -> int:
    if current_user.city_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utilisateur sans ville rattachee")
    return current_user.city_id


# ── Sites ─────────────────────────────────────────────────────────────────────

@router.get("/sites", response_model=list[CpeSiteOut])
def list_sites(
    actifs: bool = Query(default=False, description="Filtrer sur les sites actifs uniquement"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CpeSiteOut]:
    sites = svc.get_sites(db, city_id=current_user.city_id, actifs_seulement=actifs)
    return [CpeSiteOut.model_validate(s) for s in sites]


@router.post("/sites", response_model=CpeSiteOut, status_code=status.HTTP_201_CREATED)
def create_site(
    payload: CpeSiteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpeSiteOut:
    if payload.city_id is None:
        payload = payload.model_copy(update={"city_id": current_user.city_id})
    site = svc.create_site(db, payload)
    return CpeSiteOut.model_validate(site)


@router.get("/sites/{site_id}", response_model=CpeSiteOut)
def get_site(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpeSiteOut:
    site = svc.get_site(db, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site CPE introuvable")
    return CpeSiteOut.model_validate(site)


@router.patch("/sites/{site_id}", response_model=CpeSiteOut)
def update_site(
    site_id: int,
    payload: CpeSiteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpeSiteOut:
    site = svc.get_site(db, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site CPE introuvable")
    site = svc.update_site(db, site, payload)
    return CpeSiteOut.model_validate(site)


# ── Relevés mensuels ──────────────────────────────────────────────────────────

@router.get("/sites/{site_id}/releves", response_model=list[CpeGazReleve])
def list_releves(
    site_id: int,
    annee: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CpeGazReleve]:
    if svc.get_site(db, site_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site CPE introuvable")
    releves = svc.get_releves(db, site_id, annee)
    return [CpeGazReleve.model_validate(r) for r in releves]


@router.post("/sites/{site_id}/releves", response_model=CpeGazReleve, status_code=status.HTTP_201_CREATED)
def create_releve(
    site_id: int,
    payload: CpeGazReleveCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpeGazReleve:
    if svc.get_site(db, site_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site CPE introuvable")
    releve = svc.upsert_releve(db, site_id, payload, source="saisie_manuelle")
    return CpeGazReleve.model_validate(releve)


# ── Import CSV ────────────────────────────────────────────────────────────────

@router.post("/import/csv", response_model=CpeImportResult)
async def import_csv(
    file: UploadFile = File(..., description="Fichier CSV des relevés mensuels DALKIA"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpeImportResult:
    """Importe les relevés mensuels de consommation gaz depuis un fichier CSV.

    Format attendu : colonnes code_site, qt_mwh_pci, date_releve (ou annee + mois),
    volume_ecs_m3 (optionnel), etat_chauffe (optionnel).
    Séparateurs acceptés : virgule, point-virgule, tabulation.
    """
    content = await file.read()
    return import_releves_csv(db, content, source="csv_dalkia")


@router.post("/finances/preview", response_model=CpeFinancePreview)
async def preview_finances_export(
    file: UploadFile = File(..., description="Export finances CSV de l'espace client DALKIA"),
    _current_user: User = Depends(get_current_user),
) -> CpeFinancePreview:
    """Analyse un export finances DALKIA avant ingestion des factures CPE."""
    try:
        return preview_finance_export(await file.read(), filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/finances/imports", response_model=list[CpeFinanceImportBatchOut])
def list_finances_imports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CpeFinanceImportBatchOut]:
    return list_finance_batches(db, _require_city(current_user))


@router.get("/finances/imports/{batch_id}", response_model=CpeFinanceImportBatchDetail)
def get_finances_import(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpeFinanceImportBatchDetail:
    batch = get_finance_batch(db, _require_city(current_user), batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot finances DALKIA introuvable")
    return finance_batch_detail(batch)


@router.get("/finances/imports/{batch_id}/lines", response_model=list[CpeFinanceLineOut])
def list_finances_import_lines(
    batch_id: int,
    site_validation_status: str | None = Query(default=None),
    market: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CpeFinanceLineOut]:
    city_id = _require_city(current_user)
    if get_finance_batch(db, city_id, batch_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot finances DALKIA introuvable")
    return list_finance_lines(
        db,
        city_id,
        batch_id,
        site_validation_status=site_validation_status,
        market=market,
        limit=limit,
    )


@router.post("/finances/imports", response_model=CpeFinanceImportBatchDetail, status_code=status.HTTP_201_CREATED)
async def import_finances_export(
    file: UploadFile = File(..., description="Export finances CSV DALKIA du contrat CPE"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpeFinanceImportBatchDetail:
    try:
        batch = create_finance_batch_from_bytes(
            db,
            _require_city(current_user),
            current_user.id,
            filename=file.filename,
            content_type=file.content_type,
            data=await file.read(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return finance_batch_detail(batch)


# ── Prix gaz ──────────────────────────────────────────────────────────────────

@router.get("/prix-gaz/{annee}", response_model=list[CpePrixGazOut])
def get_prix_gaz(
    annee: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CpePrixGazOut]:
    """Retourne tous les prix gaz de l'exercice (T1/T2/T3 + global si renseigné).

    Depuis OS N°3, 3 tarifs coexistent selon le profil de consommation de chaque site.
    """
    prix_list = svc.get_all_prix_gaz(db, annee)
    if not prix_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prix gaz {annee} non renseigné")
    return [CpePrixGazOut.model_validate(p) for p in prix_list]


@router.post("/prix-gaz", response_model=CpePrixGazOut)
def set_prix_gaz(
    payload: CpePrixGazCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpePrixGazOut:
    """Saisit ou met à jour le prix unitaire gaz (Pu en €/MWhPCI).

    Pour les exercices 2026-2030 : prix fixe par tarif (T1/T2/T3) via OS N°3.
    Utiliser seed_cpe_prix_gaz.py pour l'initialisation automatique.
    Pour la révision P1 dès 2031 : saisir après réception décompte définitif (15/02/N+1).
    """
    prix = svc.upsert_prix_gaz(db, payload)
    return CpePrixGazOut.model_validate(prix)


# ── DJU ──────────────────────────────────────────────────────────────────────

@router.get("/dju/{annee}", response_model=CpeDjuAnnuel)
def get_dju(
    annee: int,
    current_user: User = Depends(get_current_user),
) -> CpeDjuAnnuel:
    """Retourne le cumul de DJU chauffage base 18°C (méthode COSTIC) pour l'exercice demandé.

    Source : Open-Meteo (station la plus proche de Sète), mis à jour quotidiennement.
    Référence contractuelle : 1 426 DJU (Montpellier, 1981-2010).
    """
    return svc.get_dju_annuel(annee)


# ── Calcul et bilan ───────────────────────────────────────────────────────────

@router.post("/bilan/{annee}/calculer", response_model=list[CpeResultatAnnuelOut])
def calculer_bilan(
    annee: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CpeResultatAnnuelOut]:
    """Recalcule et persiste les résultats annuels pour tous les sites actifs."""
    sites = svc.get_sites(db, city_id=current_user.city_id, actifs_seulement=True)
    resultats = []
    for site in sites:
        try:
            r = svc.calculer_resultat_site(db, site.id, annee)
            resultats.append(CpeResultatAnnuelOut.model_validate(r))
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Calcul site %d échoué : %s", site.id, exc)
    return resultats


@router.post("/sites/{site_id}/bilan/{annee}/calculer", response_model=CpeResultatAnnuelOut)
def calculer_resultat_site(
    site_id: int,
    annee: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpeResultatAnnuelOut:
    """Recalcule et persiste le résultat annuel d'un site."""
    if svc.get_site(db, site_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site CPE introuvable")
    r = svc.calculer_resultat_site(db, site_id, annee)
    return CpeResultatAnnuelOut.model_validate(r)


@router.get("/bilan/{annee}", response_model=CpeBilanAnnuel)
def get_bilan(
    annee: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpeBilanAnnuel:
    """Retourne le bilan CPE consolidé pour tous les sites de l'exercice."""
    return svc.get_bilan_annuel(db, annee, city_id=current_user.city_id)
