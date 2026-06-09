"""
GDA — Gestion des Droits d'Accès GRDF ADICT.

`list_droits()` lit l'API ``GET /droits_acces`` (flux ndjson) — c'est la source
de vérité du référentiel PCE (préférable au fichier xlsx, qui ne sert qu'à
l'amorçage). `sync_droits()` upsert ces droits dans `gas_pces`. `revoke_droit()`
révoque un droit via ``PATCH /droit_acces/{id}`` (corps vide).

Les périmètres et états gardent les libellés GRDF ; un droit `Active` avec
``perim_donnees_publiees`` vrai est collectable côté consommations.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.gas import GasPce
from app.services.grdf_client import get_ndjson

LOG = logging.getLogger(__name__)


def _truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"vrai", "oui", "true", "1"}


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    txt = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(txt[:19], fmt).date()
        except ValueError:
            continue
    return None


def _normalize_droit(raw: dict) -> dict | None:
    """Mappe un objet droit GRDF (GET /droits_acces) vers les champs `GasPce`.

    Tolérant : GET et PUT n'emploient pas exactement les mêmes noms de champs.
    """
    id_pce = raw.get("id_pce") or raw.get("pce") or raw.get("id_pce_titulaire")
    if not id_pce:
        return None
    return {
        "id_pce": str(id_pce).strip(),
        "nom_site": raw.get("nom_site") or raw.get("libelle_site"),
        "nom_titulaire": raw.get("raison_sociale") or raw.get("nom_titulaire"),
        "courriel_titulaire": raw.get("courriel_titulaire") or raw.get("email"),
        "code_postal": raw.get("code_postal"),
        "role_tiers": raw.get("role_tiers") or "AUTORISE_CONTRAT_FOURNITURE",
        "id_droit_acces": raw.get("id_droit_acces") or raw.get("id_accreditation"),
        "etat_droit_acces": raw.get("etat_droit_acces") or raw.get("etat"),
        "date_debut_droit_acces": _as_date(
            raw.get("date_debut_autorisation") or raw.get("date_debut_droit_acces")
        ),
        "date_fin_droit_acces": _as_date(
            raw.get("date_fin_autorisation") or raw.get("date_fin_droit_acces")
        ),
        "perim_publiees": _truthy(raw.get("perim_donnees_publiees")),
        "perim_informatives": _truthy(raw.get("perim_donnees_informatives")),
        "perim_contractuelles": _truthy(raw.get("perim_donnees_contractuelles")),
        "perim_techniques": _truthy(raw.get("perim_donnees_techniques")),
    }


def list_droits(filtre: dict | None = None) -> list[dict]:
    """Retourne tous les droits du Tiers (champs normalisés `GasPce`).

    Le flux ndjson peut émettre soit un objet droit par ligne, soit un objet
    enveloppe contenant ``liste_acces`` — les deux sont gérés.
    """
    droits: list[dict] = []
    for obj in get_ndjson("/droits_acces", params=filtre):
        items = obj.get("liste_acces") if isinstance(obj, dict) and "liste_acces" in obj else [obj]
        for item in items:
            if not isinstance(item, dict):
                continue
            norm = _normalize_droit(item)
            if norm:
                droits.append(norm)
    return droits


def sync_droits(db: Session, city_id: int | None = None) -> dict:
    """Upsert le référentiel des droits depuis l'API GRDF dans `gas_pces`.

    Source de vérité = l'API (remplace l'import xlsx). Retourne un compteur.
    """
    droits = list_droits()
    created = updated = 0
    for d in droits:
        existing = (
            db.query(GasPce)
            .filter(GasPce.city_id == city_id, GasPce.id_pce == d["id_pce"])
            .one_or_none()
        )
        if existing is None:
            db.add(GasPce(city_id=city_id, last_synced_at=datetime.utcnow(), **d))
            created += 1
        else:
            for k, v in d.items():
                if k != "id_pce" and getattr(existing, k) != v:
                    setattr(existing, k, v)
            existing.last_synced_at = datetime.utcnow()
            updated += 1
    db.commit()
    LOG.info("GRDF sync droits : %d créés, %d mis à jour (total API %d)", created, updated, len(droits))
    return {"total_api": len(droits), "created": created, "updated": updated}


def revoke_droit(id_droit_acces: str) -> dict:
    """Révoque un droit d'accès (PATCH /droit_acces/{id}, corps vide)."""
    import requests  # noqa: PLC0415

    from app.core.config import settings  # noqa: PLC0415
    from app.services.grdf_auth import get_rate_limiter, get_token_manager  # noqa: PLC0415

    tm = get_token_manager()
    rl = get_rate_limiter()
    rl.acquire()
    try:
        resp = requests.patch(
            f"{settings.grdf_base_url.rstrip('/')}/droit_acces/{id_droit_acces}",
            json={},
            headers={"Authorization": f"Bearer {tm.get()}"},
            timeout=60,
        )
    finally:
        rl.release()
    return {"status_code": resp.status_code, "body": resp.text[:300]}
