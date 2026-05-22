"""Routes API CPE DALKIA — Contrat de Performance Énergétique."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.cpe import (
    CpeBilanAnnuel,
    CpeDjuAnnuel,
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
from app.services.cpe_import import import_releves_csv

router = APIRouter(prefix="/cpe", tags=["cpe"])


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


# ── Prix gaz ──────────────────────────────────────────────────────────────────

@router.get("/prix-gaz/{annee}", response_model=CpePrixGazOut)
def get_prix_gaz(
    annee: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpePrixGazOut:
    prix = svc.get_prix_gaz(db, annee)
    if prix is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prix gaz {annee} non renseigné")
    return CpePrixGazOut.model_validate(prix)


@router.post("/prix-gaz", response_model=CpePrixGazOut)
def set_prix_gaz(
    payload: CpePrixGazCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpePrixGazOut:
    """Saisit ou met à jour le prix unitaire gaz d'un exercice (Pu en €/MWhPCI).

    Ce Pu est issu du décompte définitif P1 (facture DALKIA au 15/02/N+1).
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
