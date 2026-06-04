"""Devis de petits travaux P3 (type DALKIA 'P6') — import CSV et atterrissage P3.

L'export devis (espace client DALKIA, formulaire distinct de l'export finances) ne contient
PAS de code contrat. Le périmètre CPE Ville est déterminé par le destinataire :
``COMMUNE DE SETE`` est dans le périmètre ; ``CA SETE AGGLOPOLE MEDITERRANEE`` (crématorium /
piscine Fonquerne, etc.) en est exclu. Ce filtre est porté par ``in_scope``.

L'« atterrissage P3 » confronte le cumul des devis engagés (in-scope) à la provision P3
annuelle (forfait P3 du suivi marché).
"""
from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cpe import CpeP3Devis
from app.services.cpe_accounting import _clean, _date, _float, _norm_header, _norm_text, _site_code
from app.services.cpe_market_tracking import build_market_tracking

# Destinataire du marché CPE Ville (les autres entités, ex. agglomération, sont hors périmètre).
CPE_VILLE_DESTINATAIRE = "COMMUNE DE SETE"


def _is_in_scope(destinataire: str | None) -> bool:
    return _norm_text(destinataire) == CPE_VILLE_DESTINATAIRE


def _decode_csv(raw_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("latin-1", errors="replace")


def import_p3_devis_csv(db: Session, raw_bytes: bytes, *, city_id: int | None) -> dict[str, Any]:
    """Importe (upsert par numéro) l'export CSV des devis P3/P6 DALKIA."""
    text = _decode_csv(raw_bytes)
    reader = csv.reader(io.StringIO(text), delimiter=";")
    rows = [row for row in reader if any((cell or "").strip() for cell in row)]
    if not rows:
        raise ValueError("Fichier devis vide ou illisible.")

    headers = [_norm_header(cell) for cell in rows[0]]
    created = updated = in_scope = skipped = 0
    errors: list[str] = []

    for line_no, raw in enumerate(rows[1:], start=2):
        record = {headers[i]: raw[i] for i in range(len(headers)) if i < len(raw)}
        numero = _clean(record.get("numero"))
        if not numero:
            skipped += 1
            errors.append(f"Ligne {line_no} : numéro de devis absent, ignorée.")
            continue
        destinataire = _clean(record.get("destinaire") or record.get("destinataire"))
        localisation = _clean(record.get("localisation"))
        payload = {
            "city_id": city_id,
            "numero": numero,
            "devis_date": _date(record.get("date")),
            "localisation": localisation,
            "site_code": _site_code(localisation),
            "libelle": _clean(record.get("libelle")),
            "domaine": _clean(record.get("domaine")),
            "type_devis": _clean(record.get("type")),
            "destinataire": destinataire,
            "etat": _clean(record.get("etat")),
            "montant_ht": _float(record.get("montant_ht")),
            "montant_ttc": _float(record.get("montant_ttc")),
            "in_scope": _is_in_scope(destinataire),
        }
        if payload["in_scope"]:
            in_scope += 1

        existing = db.scalars(
            select(CpeP3Devis).where(CpeP3Devis.city_id == city_id, CpeP3Devis.numero == numero)
        ).first()
        if existing is None:
            db.add(CpeP3Devis(**payload))
            created += 1
        else:
            for key, value in payload.items():
                setattr(existing, key, value)
            updated += 1

    db.commit()
    return {
        "created": created,
        "updated": updated,
        "in_scope": in_scope,
        "out_of_scope": (created + updated) - in_scope,
        "skipped": skipped,
        "errors": errors,
    }


def list_p3_devis(db: Session, city_id: int | None = None, *, in_scope_only: bool = True) -> list[CpeP3Devis]:
    query = select(CpeP3Devis)
    if city_id is not None:
        query = query.where(CpeP3Devis.city_id == city_id)
    if in_scope_only:
        query = query.where(CpeP3Devis.in_scope.is_(True))
    query = query.order_by(CpeP3Devis.devis_date.desc(), CpeP3Devis.numero)
    return list(db.scalars(query).all())


def build_p3_atterrissage(db: Session, city_id: int | None = None, *, year: int) -> dict[str, Any]:
    """Atterrissage P3 de l'année : devis engagés (in-scope) vs provision P3 contractuelle.

    La provision P3 est le prévu P3 (forfait récurrent) + P3.4 du suivi marché pour l'année.
    Les devis sont regroupés par état (terminés / en cours / en attente / autre).
    """
    tracking = build_market_tracking(db, city_id, year_from=year, year_to=year)
    prevu_by_poste = {p["poste"]: p["total"]["prevu"] for p in tracking["postes"]}
    provision_p3 = round(prevu_by_poste.get("P3", 0.0), 2)
    provision_p3_4 = round(prevu_by_poste.get("P3-4", 0.0), 2)
    provision_total = round(provision_p3 + provision_p3_4, 2)

    devis = [
        d
        for d in list_p3_devis(db, city_id, in_scope_only=True)
        if d.devis_date is not None and d.devis_date.year == year
    ]
    by_etat: dict[str, dict[str, Any]] = {}
    engage_total = 0.0
    for d in devis:
        amount = d.montant_ht or 0.0
        engage_total += amount
        label = d.etat or "Non renseigné"
        bucket = by_etat.setdefault(label, {"etat": label, "count": 0, "montant_ht": 0.0})
        bucket["count"] += 1
        bucket["montant_ht"] = round(bucket["montant_ht"] + amount, 2)

    engage_total = round(engage_total, 2)
    return {
        "year": year,
        "provision_p3": provision_p3,
        "provision_p3_4": provision_p3_4,
        "provision_total": provision_total,
        "engage_total": engage_total,
        "reste_provision": round(provision_total - engage_total, 2),
        "taux_engagement": round(engage_total / provision_total, 4) if provision_total else None,
        "devis_count": len(devis),
        "by_etat": sorted(by_etat.values(), key=lambda item: item["montant_ht"], reverse=True),
        "has_provision": provision_total > 0,
    }
