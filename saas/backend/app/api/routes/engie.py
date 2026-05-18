"""
Routes FastAPI pour l'API ENGIE Entreprises & Collectivités.

Proxy les appels vers l'API ENGIE avec authentification gérée côté backend.
Nécessite un utilisateur PatrimoineOp authentifié.

⚠️  Les endpoints sont fonctionnels structurellement mais retourneront
une erreur 503 tant que les credentials ENGIE ne sont pas configurés.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.services import engie_client

router = APIRouter(prefix="/engie", tags=["engie"])


def _check_engie_configured() -> None:
    """Vérifie que la clé d'abonnement ENGIE est renseignée."""
    if not settings.engie_subscription_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ENGIE API non configurée. Renseigner ENGIE_SUBSCRIPTION_KEY dans .env.",
        )


# ---------------------------------------------------------------------------
# Profil
# ---------------------------------------------------------------------------


@router.get("/profil")
def engie_profil(current_user: User = Depends(get_current_user)):
    _check_engie_configured()
    try:
        return engie_client.get_profil()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/profils")
def engie_profils(current_user: User = Depends(get_current_user)):
    _check_engie_configured()
    try:
        return engie_client.list_profils()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------


@router.get("/sites")
def engie_sites(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    codePostal: Optional[str] = None,
    referenceClient: Optional[str] = None,
    groupeId: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.list_sites(
            offset=offset,
            limit=limit,
            code_postal=codePostal,
            reference_client=referenceClient,
            groupe_id=groupeId,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/sites/{uid}")
def engie_site(uid: str, current_user: User = Depends(get_current_user)):
    _check_engie_configured()
    try:
        return engie_client.get_site(uid)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/sites/{uid}/details")
def engie_site_details(uid: str, current_user: User = Depends(get_current_user)):
    _check_engie_configured()
    try:
        return engie_client.get_site_details(uid)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/sites/{uid}/details-v2")
def engie_site_details_v2(uid: str, current_user: User = Depends(get_current_user)):
    _check_engie_configured()
    try:
        return engie_client.get_site_details_v2(uid)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/sites/{uid}/programmation-horaire")
def engie_programmation_horaire(
    uid: str,
    dateDebut: Optional[str] = None,
    dateFin: Optional[str] = None,
    pasTemporel: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.get_programmation_horaire(uid, dateDebut, dateFin, pasTemporel)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


# ---------------------------------------------------------------------------
# Groupes
# ---------------------------------------------------------------------------


@router.get("/groupes")
def engie_groupes(current_user: User = Depends(get_current_user)):
    _check_engie_configured()
    try:
        return engie_client.list_groupes()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/groupes/{uid}")
def engie_groupe(uid: str, current_user: User = Depends(get_current_user)):
    _check_engie_configured()
    try:
        return engie_client.get_groupe(uid)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


# ---------------------------------------------------------------------------
# Contrats
# ---------------------------------------------------------------------------


@router.get("/contrats")
def engie_contrats(
    siteId: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.list_contrats(site_id=siteId)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/contrats/{uid}/sites")
def engie_contrat_sites(uid: str, current_user: User = Depends(get_current_user)):
    _check_engie_configured()
    try:
        return engie_client.get_contrat_sites(uid)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


# ---------------------------------------------------------------------------
# Consommations
# ---------------------------------------------------------------------------


@router.get("/consommations")
def engie_consommations(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    groupeId: Optional[str] = None,
    siteId: Optional[str] = None,
    dateDebut: Optional[str] = None,
    dateFin: Optional[str] = None,
    agregationTemporelle: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.list_consommations(
            offset=offset,
            limit=limit,
            groupe_id=groupeId,
            site_id=siteId,
            date_debut=dateDebut,
            date_fin=dateFin,
            agregation_temporelle=agregationTemporelle,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/consommations/foisonne")
def engie_consommation_foisonnee(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    groupeId: Optional[str] = None,
    dateDebut: Optional[str] = None,
    dateFin: Optional[str] = None,
    agregationTemporelle: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.get_consommation_foisonnee(
            offset=offset,
            limit=limit,
            groupe_id=groupeId,
            date_debut=dateDebut,
            date_fin=dateFin,
            agregation_temporelle=agregationTemporelle,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/consommations/site/{uid}/courbe-de-charge")
def engie_courbe_de_charge(
    uid: str,
    dateDebut: Optional[str] = None,
    dateFin: Optional[str] = None,
    pasTemporel: Optional[str] = None,
    unite: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.get_courbe_de_charge(uid, dateDebut, dateFin, pasTemporel, unite)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/consommations/site/{uid}/energie-reactive")
def engie_energie_reactive(
    uid: str,
    dateDebut: Optional[str] = None,
    dateFin: Optional[str] = None,
    pasTemporel: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.get_energie_reactive(uid, dateDebut, dateFin, pasTemporel)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/consommations/site/{uid}/puissance-souscrite")
def engie_puissance_souscrite(
    uid: str,
    dateDebut: Optional[str] = None,
    dateFin: Optional[str] = None,
    pasTemporel: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.get_puissance_souscrite(uid, dateDebut, dateFin, pasTemporel)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/consommations/site/{site_id}/index")
def engie_index_mensuel(
    site_id: str,
    dateDebut: str = Query(...),
    dateFin: str = Query(...),
    calendrier: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.get_index_mensuel(site_id, dateDebut, dateFin, calendrier)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


# ---------------------------------------------------------------------------
# Factures
# ---------------------------------------------------------------------------


@router.get("/factures")
def engie_factures(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    groupeId: Optional[str] = None,
    siteId: Optional[str] = None,
    dateDebut: Optional[str] = None,
    dateFin: Optional[str] = None,
    typePeriode: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.list_factures(
            offset=offset,
            limit=limit,
            groupe_id=groupeId,
            site_id=siteId,
            date_debut=dateDebut,
            date_fin=dateFin,
            type_periode=typePeriode,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/factures/{uid}")
def engie_facture(
    uid: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.get_facture(uid, offset, limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/factures/{uid}/details")
def engie_facture_details(
    uid: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.get_facture_details(uid, offset, limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/factures/{uid}/fichier")
def engie_facture_fichier(uid: str, current_user: User = Depends(get_current_user)):
    _check_engie_configured()
    try:
        pdf_bytes = engie_client.get_facture_fichier(uid)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="facture_{uid}.pdf"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


# ---------------------------------------------------------------------------
# Demandes
# ---------------------------------------------------------------------------


@router.get("/demandes")
def engie_demandes(
    dateDebut: Optional[str] = None,
    dateFin: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    _check_engie_configured()
    try:
        return engie_client.list_demandes(date_debut=dateDebut, date_fin=dateFin)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/demandes/categories")
def engie_categories_demande(current_user: User = Depends(get_current_user)):
    _check_engie_configured()
    try:
        return engie_client.list_categories_demande()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc


@router.get("/demandes/{uid}")
def engie_demande(uid: str, current_user: User = Depends(get_current_user)):
    _check_engie_configured()
    try:
        return engie_client.get_demande(uid)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur ENGIE : {exc}") from exc
