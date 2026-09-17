"""Enveloppe thermique d'un niveau — proposition des deux lignes depuis les calques (docs/thermique/
refondation-parcours-decisions.md §15, D34-D35).

Les lignes sont enregistrées comme zones du niveau (`contour` = nu intérieur, `nu_exterieur`), source
« automatique » : une correction à la main les fait passer en « corrige » (thermique_metre.update_zone) et elles ne
sont plus remplacées sans confirmation.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.thermique import ThermiqueLevel, ThermiqueProject, ThermiqueSheet, ThermiqueZone
from app.services.thermique import ThermiqueError
from app.services.thermique_pieces import _limites
from thermique_moteur import bande as moteur
from thermique_moteur import metre
from thermique_moteur.pieces import PiecesError

GENRES = ("contour", "nu_exterieur")


def propose_envelope(db: Session, level: ThermiqueLevel, fermeture_m: float, replace: bool = False) -> dict:
    sheet = db.get(ThermiqueSheet, level.sheet_id) if level.sheet_id else None
    if sheet is None or not sheet.scale_denominator:
        raise ThermiqueError("Associez à ce niveau une planche de plan à l'échelle définie.")
    if not 0 <= fermeture_m <= 3:
        raise ThermiqueError("Fermeture des ouvertures hors limites (0 à 3 m).")
    if not replace and any(zone.kind in GENRES and zone.source != "automatique" for zone in level.zones):
        raise ThermiqueError(
            "Ce niveau a déjà un nu intérieur ou un nu extérieur tracé ou corrigé à la main : confirmez son remplacement."
        )
    project = db.get(ThermiqueProject, level.project_id)
    elements, indices, _natures = _limites(project, sheet)
    try:
        batiments = moteur.proposer(elements, indices, fermeture_m)
    except PiecesError as exc:
        raise ThermiqueError(str(exc)) from exc
    for zone in [zone for zone in level.zones if zone.kind in GENRES]:
        if zone.source == "automatique" or replace:
            db.delete(zone)
    db.flush()
    for rang, batiment in enumerate(batiments, start=1):
        suffixe = "" if len(batiments) == 1 else f" {rang}"
        for kind, cle, nom in (("nu_exterieur", "nu_exterieur", "Nu extérieur"), ("contour", "nu_interieur", "Nu intérieur")):
            points = metre.nettoyer_points(batiment[cle])
            cotes = [] if kind in metre.ZONES_SANS_COTES else metre.normaliser_cotes(None, len(points), metre.DONNE_SUR_DEFAUT[kind])
            db.add(
                ThermiqueZone(
                    project_id=level.project_id,
                    level_id=level.id,
                    kind=kind,
                    name=f"{nom}{suffixe}",
                    points_json=json.dumps(points, separators=(",", ":")),
                    edges_json=json.dumps(cotes, separators=(",", ":")),
                    source="automatique",
                )
            )
    db.commit()
    db.refresh(level)
    return {
        "batiments": len(batiments),
        "nu_exterieur_m2": round(sum(b["aire_exterieur_m2"] for b in batiments), 2),
        "nu_interieur_m2": round(sum(b["aire_interieur_m2"] for b in batiments), 2),
    }
