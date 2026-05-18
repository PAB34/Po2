"""
Client HTTP pour l'API ENGIE Entreprises & Collectivités (ec/v1).

Authentification via Azure API Management (Ocp-Apim-Subscription-Key).
Chaque appel envoie la clé d'abonnement dans le header.

⚠️  Ce client ne fonctionnera pas tant que ENGIE_SUBSCRIPTION_KEY n'est
pas renseigné dans .env.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import requests

from app.core.config import settings
from app.schemas.engie import (
    CategorieDemandeList,
    ConsommationFoisonneeListe,
    ConsommationListe,
    ConsommationsCourbeDeCharge,
    ConsommationsSiteBase,
    Contact,
    ContactsListe,
    ContratSitesResponse,
    ContratsResponse,
    Demande,
    FactureDataListe,
    FactureListe,
    Groupe,
    GroupeListe,
    ProgrammationHoraire,
    Site,
    SiteDetail,
    SiteDetailV2,
    SiteListe,
)

LOG = logging.getLogger(__name__)

_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Authentication (Azure APIM — Ocp-Apim-Subscription-Key)
# ---------------------------------------------------------------------------


def _build_auth_headers() -> dict[str, str]:
    """
    Construit les headers d'authentification ENGIE.
    Utilise le header Ocp-Apim-Subscription-Key (Azure API Management).
    """
    if not settings.engie_subscription_key:
        raise RuntimeError(
            "ENGIE : ENGIE_SUBSCRIPTION_KEY non configuré. "
            "Renseigner la clé d'abonnement dans .env."
        )
    return {"Ocp-Apim-Subscription-Key": settings.engie_subscription_key}


# ---------------------------------------------------------------------------
# Low-level HTTP helpers
# ---------------------------------------------------------------------------


def _get(path: str, params: Optional[dict[str, Any]] = None) -> Any:
    """GET vers l'API ENGIE. Retourne le JSON décodé."""
    url = f"{settings.engie_base_url}{path}"
    headers = _build_auth_headers()
    headers["Accept"] = "application/json"
    headers["Cache-Control"] = "no-cache"
    LOG.debug("ENGIE GET %s params=%s", url, params)
    resp = requests.get(url, headers=headers, params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, json_body: Optional[dict[str, Any]] = None) -> Any:
    """POST vers l'API ENGIE. Retourne le JSON décodé (ou les headers)."""
    url = f"{settings.engie_base_url}{path}"
    headers = _build_auth_headers()
    headers["Content-Type"] = "application/json"
    headers["Cache-Control"] = "no-cache"
    LOG.debug("ENGIE POST %s", url)
    resp = requests.post(url, headers=headers, json=json_body or {}, timeout=_TIMEOUT)
    resp.raise_for_status()
    if resp.status_code == 201:
        return {"location": resp.headers.get("Location", "")}
    return resp.json()


def _get_binary(path: str) -> bytes:
    """GET binaire (ex: PDF facture)."""
    url = f"{settings.engie_base_url}{path}"
    headers = _build_auth_headers()
    headers["Cache-Control"] = "no-cache"
    resp = requests.get(url, headers=headers, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------


def list_sites(
    offset: int = 0,
    limit: int = 50,
    code_postal: Optional[str] = None,
    reference_client: Optional[str] = None,
    groupe_id: Optional[str] = None,
) -> SiteListe:
    params: dict[str, Any] = {"offset": offset, "limit": limit}
    if code_postal:
        params["codePostal"] = code_postal
    if reference_client:
        params["referenceClient"] = reference_client
    if groupe_id:
        params["groupeId"] = groupe_id
    data = _get("/sites", params)
    return SiteListe.model_validate(data)


def get_site(uid: str) -> Site:
    data = _get(f"/sites/{uid}")
    return Site.model_validate(data)


def get_site_details(uid: str) -> SiteDetail:
    data = _get(f"/sites/{uid}/details")
    return SiteDetail.model_validate(data)


def get_site_details_v2(uid: str) -> SiteDetailV2:
    data = _get(f"/sites/details", params={"uid": uid})
    return SiteDetailV2.model_validate(data)


def get_programmation_horaire(
    uid: str,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    pas_temporel: Optional[str] = None,
) -> ProgrammationHoraire:
    params: dict[str, Any] = {}
    if date_debut:
        params["dateDebut"] = date_debut
    if date_fin:
        params["dateFin"] = date_fin
    if pas_temporel:
        params["pasTemporel"] = pas_temporel
    data = _get(f"/sites/{uid}/programmationHoraire", params or None)
    return ProgrammationHoraire.model_validate(data)


# ---------------------------------------------------------------------------
# Groupes
# ---------------------------------------------------------------------------


def list_groupes() -> GroupeListe:
    data = _get("/groupes")
    return GroupeListe.model_validate(data)


def get_groupe(uid: str) -> Groupe:
    data = _get(f"/groupes/{uid}")
    return Groupe.model_validate(data)


# ---------------------------------------------------------------------------
# Contrats
# ---------------------------------------------------------------------------


def list_contrats(site_id: Optional[str] = None) -> ContratsResponse:
    params = {"siteId": site_id} if site_id else None
    data = _get("/contrats", params)
    return ContratsResponse.model_validate(data)


def get_contrat_sites(uid: str) -> ContratSitesResponse:
    data = _get(f"/contrats/{uid}/sites")
    return ContratSitesResponse.model_validate(data)


# ---------------------------------------------------------------------------
# Consommations
# ---------------------------------------------------------------------------


def list_consommations(
    offset: int = 0,
    limit: int = 50,
    groupe_id: Optional[str] = None,
    site_id: Optional[str] = None,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    agregation_temporelle: Optional[str] = None,
) -> ConsommationListe:
    params: dict[str, Any] = {"offset": offset, "limit": limit}
    if groupe_id:
        params["groupeId"] = groupe_id
    if site_id:
        params["siteId"] = site_id
    if date_debut:
        params["dateDebut"] = date_debut
    if date_fin:
        params["dateFin"] = date_fin
    if agregation_temporelle:
        params["agregationTemporelle"] = agregation_temporelle
    data = _get("/consommations", params)
    return ConsommationListe.model_validate(data)


def get_consommation_foisonnee(
    offset: int = 0,
    limit: int = 50,
    groupe_id: Optional[str] = None,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    agregation_temporelle: Optional[str] = None,
) -> ConsommationFoisonneeListe:
    params: dict[str, Any] = {"offset": offset, "limit": limit}
    if groupe_id:
        params["groupeId"] = groupe_id
    if date_debut:
        params["dateDebut"] = date_debut
    if date_fin:
        params["dateFin"] = date_fin
    if agregation_temporelle:
        params["agregationTemporelle"] = agregation_temporelle
    data = _get("/consommations/foisonne", params)
    return ConsommationFoisonneeListe.model_validate(data)


def get_courbe_de_charge(
    uid: str,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    pas_temporel: Optional[str] = None,
    unite: Optional[str] = None,
) -> ConsommationsCourbeDeCharge:
    params: dict[str, Any] = {}
    if date_debut:
        params["dateDebut"] = date_debut
    if date_fin:
        params["dateFin"] = date_fin
    if pas_temporel:
        params["pasTemporel"] = pas_temporel
    if unite:
        params["unite"] = unite
    data = _get(f"/consommations/site/{uid}/courbeDeCharge", params or None)
    return ConsommationsCourbeDeCharge.model_validate(data)


def get_energie_reactive(
    uid: str,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    pas_temporel: Optional[str] = None,
) -> ConsommationsSiteBase:
    params: dict[str, Any] = {}
    if date_debut:
        params["dateDebut"] = date_debut
    if date_fin:
        params["dateFin"] = date_fin
    if pas_temporel:
        params["pasTemporel"] = pas_temporel
    data = _get(f"/consommations/site/{uid}/energieReactive", params or None)
    return ConsommationsSiteBase.model_validate(data)


def get_puissance_souscrite(
    uid: str,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    pas_temporel: Optional[str] = None,
) -> ConsommationsSiteBase:
    params: dict[str, Any] = {}
    if date_debut:
        params["dateDebut"] = date_debut
    if date_fin:
        params["dateFin"] = date_fin
    if pas_temporel:
        params["pasTemporel"] = pas_temporel
    data = _get(f"/consommations/site/{uid}/puissanceSouscrite", params or None)
    return ConsommationsSiteBase.model_validate(data)


def get_index_mensuel(
    site_id: str,
    date_debut: str,
    date_fin: str,
    calendrier: Optional[str] = None,
) -> list[dict]:
    """Retourne les index mensuels (structure complexe, retournée brute)."""
    params: dict[str, Any] = {}
    if calendrier:
        params["calendrier"] = calendrier
    data = _get(
        f"/consommations/site/{site_id}/index?dateDebut={date_debut}&dateFin={date_fin}",
        params or None,
    )
    return data if isinstance(data, list) else [data]


# ---------------------------------------------------------------------------
# Factures
# ---------------------------------------------------------------------------


def list_factures(
    offset: int = 0,
    limit: int = 50,
    groupe_id: Optional[str] = None,
    site_id: Optional[str] = None,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    type_periode: Optional[str] = None,
) -> FactureListe:
    params: dict[str, Any] = {"offset": offset, "limit": limit}
    if groupe_id:
        params["groupeId"] = groupe_id
    if site_id:
        params["siteId"] = site_id
    if date_debut:
        params["dateDebut"] = date_debut
    if date_fin:
        params["dateFin"] = date_fin
    if type_periode:
        params["typePeriode"] = type_periode
    data = _get("/factures", params)
    return FactureListe.model_validate(data)


def get_facture(uid: str, offset: int = 0, limit: int = 50) -> FactureListe:
    data = _get(f"/factures/{uid}", {"offset": offset, "limit": limit})
    return FactureListe.model_validate(data)


def get_facture_details(uid: str, offset: int = 0, limit: int = 50) -> FactureDataListe:
    data = _get(f"/factures/{uid}/details", {"offset": offset, "limit": limit})
    return FactureDataListe.model_validate(data)


def get_facture_fichier(uid: str) -> bytes:
    """Télécharge le PDF d'une facture."""
    return _get_binary(f"/factures/{uid}/fichier")


# ---------------------------------------------------------------------------
# Demandes
# ---------------------------------------------------------------------------


def list_demandes(
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
) -> list[Demande]:
    params: dict[str, Any] = {}
    if date_debut:
        params["dateDebut"] = date_debut
    if date_fin:
        params["dateFin"] = date_fin
    data = _get("/demandes", params or None)
    if isinstance(data, list):
        return [Demande.model_validate(d) for d in data]
    return []


def get_demande(uid: str) -> Demande:
    data = _get(f"/demandes/{uid}")
    return Demande.model_validate(data)


def list_categories_demande() -> CategorieDemandeList:
    data = _get("/demandes/categories")
    return CategorieDemandeList.model_validate(data)


def create_demande(body: dict[str, Any]) -> dict[str, str]:
    return _post("/demandes", body)


# ---------------------------------------------------------------------------
# Profil
# ---------------------------------------------------------------------------


def get_profil(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Contact:
    params: dict[str, Any] = {}
    if session_id:
        params["sessionId"] = session_id
    if user_id:
        params["userId"] = user_id
    data = _get("/profil", params or None)
    return Contact.model_validate(data)


def list_profils() -> ContactsListe:
    data = _get("/profils")
    return ContactsListe.model_validate(data)
