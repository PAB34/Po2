"""Lectures des coupes : les ranger, les rapprocher des traits des plans, et donner la hauteur des locaux.

Les lectures arrivent du relais (agent `thermicien-coupe`, D181) : les **traits de coupe** d'un plan, et les
**vues** d'une planche de coupes ou de façades. Ce module les contrôle, les range, et calcule à la demande la
hauteur de chaque local d'un niveau (`thermique_coupes.py`, D178 à D189). Rien n'est recopié dans l'étude :
une hauteur n'y entre que quand le thermicien la saisit ou la valide (geste « modifier », `hauteur_m`).
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.thermique import ThermiqueSheet, ThermiqueVue
from app.services import thermique_coupes as coupes
from app.services.thermique import ThermiqueError
from app.services.thermique_etudes import get_etude_for_sheet

NATURES_VUE = ("coupe", "facade", "detail")
HAUTEUR_MIN_M = 1.5
HAUTEUR_MAX_M = 15.0


def _nombre(valeur: Any, etiquette: str) -> float:
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
        raise ThermiqueError(f"{etiquette} n'est pas un nombre.")
    return float(valeur)


def _point(valeur: Any, etiquette: str) -> list[float]:
    if not isinstance(valeur, (list, tuple)) or len(valeur) != 2:
        raise ThermiqueError(f"{etiquette} doit être un couple de nombres.")
    return [_nombre(valeur[0], etiquette), _nombre(valeur[1], etiquette)]


def _nom(valeur: Any, etiquette: str) -> str:
    texte = str(valeur or "").strip()
    if not texte or len(texte) > 80:
        raise ThermiqueError(f"{etiquette} doit avoir un nom de 1 à 80 caractères.")
    return texte


def valider_traits(traits: Any) -> list[dict[str, Any]]:
    if not isinstance(traits, list):
        raise ThermiqueError("Les traits de coupe doivent former une liste.")
    resultat, noms = [], set()
    for index, trait in enumerate(traits, 1):
        if not isinstance(trait, dict):
            raise ThermiqueError(f"Le trait {index} est invalide.")
        nom = _nom(trait.get("nom"), f"Le trait {index}")
        if nom in noms:
            raise ThermiqueError(f"Deux traits s'appellent « {nom} ».")
        noms.add(nom)
        points = trait.get("points")
        if not isinstance(points, list) or len(points) < 2:
            raise ThermiqueError(f"Le trait « {nom} » doit avoir au moins deux points.")
        sens = _point(trait.get("sens"), f"Le sens du trait « {nom} »")
        if sens == [0.0, 0.0]:
            raise ThermiqueError(f"Le sens du trait « {nom} » est nul.")
        resultat.append({"nom": nom, "points": [_point(p, f"Un point du trait « {nom} »") for p in points], "sens": sens})
    return resultat


def valider_vues(vues: Any) -> list[dict[str, Any]]:
    """Contrôle la lecture d'une planche : chaque vue doit pouvoir être convertie en mètres."""
    if not isinstance(vues, list):
        raise ThermiqueError("Les vues doivent former une liste.")
    resultat, noms = [], set()
    for index, vue in enumerate(vues, 1):
        if not isinstance(vue, dict):
            raise ThermiqueError(f"La vue {index} est invalide.")
        nom = _nom(vue.get("nom"), f"La vue {index}")
        if nom in noms:
            raise ThermiqueError(f"Deux vues s'appellent « {nom} » sur la même planche.")
        noms.add(nom)
        nature = vue.get("nature")
        if nature not in NATURES_VUE:
            raise ThermiqueError(f"La nature de la vue « {nom} » est inconnue.")
        cadre = vue.get("cadre")
        if not isinstance(cadre, list) or len(cadre) != 4:
            raise ThermiqueError(f"Le cadre de la vue « {nom} » doit avoir quatre nombres.")
        propre = {
            "nom": nom,
            "nature": nature,
            "cadre": [_nombre(v, f"Le cadre de la vue « {nom} »") for v in cadre],
            "haut": _point(vue.get("haut", [0, 1]), f"Le haut de la vue « {nom} »"),
            "niveaux": vue.get("niveaux") or [],
            "pieces": vue.get("pieces") or [],
        }
        if not isinstance(propre["niveaux"], list) or not isinstance(propre["pieces"], list):
            raise ThermiqueError(f"Les niveaux et les pièces de la vue « {nom} » doivent former des listes.")
        try:
            # Même conversion que le calcul : une lecture qui ne se convertit pas est refusée à l'entrée.
            coupes.pieces_de_la_vue(propre, 100)
        except (KeyError, TypeError, ValueError) as exc:
            raise ThermiqueError(f"La vue « {nom} » est illisible : {exc}") from exc
        resultat.append(propre)
    return resultat


def enregistrer_traits(db: Session, sheet: ThermiqueSheet, traits: Any) -> list[dict[str, Any]]:
    if sheet.nature != "plan":
        raise ThermiqueError("Les traits de coupe se relèvent sur un plan de niveau.")
    propres = valider_traits(traits)
    sheet.traits_coupe_json = json.dumps(propres, ensure_ascii=False, separators=(",", ":"))
    db.commit()
    return propres


def traits_du_plan(sheet: ThermiqueSheet) -> list[dict[str, Any]]:
    if not sheet.traits_coupe_json:
        return []
    try:
        return json.loads(sheet.traits_coupe_json)
    except ValueError:
        return []


def enregistrer_vues(db: Session, sheet: ThermiqueSheet, vues: Any) -> list[ThermiqueVue]:
    """Remplace toutes les vues de la planche par la nouvelle lecture."""
    if sheet.nature not in ("coupe", "facade"):
        raise ThermiqueError("Les vues se lisent sur une planche de coupes ou de façades.")
    propres = valider_vues(vues)
    for ancienne in db.scalars(select(ThermiqueVue).where(ThermiqueVue.sheet_id == sheet.id)).all():
        db.delete(ancienne)
    db.flush()
    rangees = []
    for vue in propres:
        lecture = {k: vue[k] for k in ("haut", "niveaux", "pieces")}
        rangee = ThermiqueVue(
            project_id=sheet.project_id,
            sheet_id=sheet.id,
            nom=vue["nom"],
            nature=vue["nature"],
            cadre_json=json.dumps(vue["cadre"]),
            lecture_json=json.dumps(lecture, ensure_ascii=False, separators=(",", ":")),
        )
        db.add(rangee)
        rangees.append(rangee)
    db.commit()
    return rangees


def serialize_vue(vue: ThermiqueVue) -> dict[str, Any]:
    return {
        "id": vue.id,
        "sheet_id": vue.sheet_id,
        "nom": vue.nom,
        "nature": vue.nature,
        "cadre": json.loads(vue.cadre_json),
        **json.loads(vue.lecture_json),
    }


def _cle(nom: str) -> str:
    """« COUPE CC », « Coupe C », « C » → « C » ; « coupe A-A » → « A »."""
    sans_accent = unicodedata.normalize("NFD", nom.upper())
    texte = "".join(c for c in sans_accent if unicodedata.category(c) != "Mn")
    texte = re.sub(r"\bCOUPES?\b", "", texte)
    texte = re.sub(r"[^A-Z0-9]", "", texte)
    if len(texte) > 1 and len(set(texte)) == 1:
        texte = texte[0]
    return texte


def meme_coupe(trait: str, vue: str) -> bool:
    return bool(_cle(trait)) and _cle(trait) == _cle(vue)


def hauteurs_du_plan(db: Session, sheet: ThermiqueSheet) -> dict[str, Any]:
    """Hauteur de chaque local du niveau : saisie par le thermicien, sinon lue dans les coupes (D178 à D180)."""
    etude = get_etude_for_sheet(db, sheet.id)
    if etude is None:
        raise ThermiqueError("Ce plan n'a pas encore d'étude : rien à rattacher aux coupes.")
    contenu = json.loads(etude.content_json)
    locaux = [
        {"id": l["id"], "nom": l.get("nom"), "contour_pdf": l.get("contour_pdf") or []}
        for l in contenu.get("locaux", [])
        if l.get("nature") in ("chauffe", "circulation", "non_chauffe", "gaine_technique")
    ]
    traits = traits_du_plan(sheet)
    vues = db.scalars(
        select(ThermiqueVue).where(ThermiqueVue.project_id == sheet.project_id, ThermiqueVue.nature == "coupe")
    ).all()
    echelles = {
        s.id: s.scale_denominator
        for s in db.scalars(select(ThermiqueSheet).where(ThermiqueSheet.project_id == sheet.project_id)).all()
    }
    rattachements: dict[str, dict[str, Any]] = {}
    lectures: list[dict[str, Any]] = []
    sans_vue: list[str] = []
    non_situees: list[str] = []
    releves = [t for t in traits if not t.get("deduit")]
    deduits = {t.get("vue_id"): t for t in traits if t.get("deduit")}
    nouveaux = False
    for vue in vues:
        echelle_vue = echelles.get(vue.sheet_id)
        if not echelle_vue or not sheet.scale_denominator:
            continue
        # Le trait relevé sur le plan fait foi ; sinon celui déduit de la coupe (D190), calculé une fois.
        trait = next((t for t in releves if meme_coupe(t["nom"], vue.nom)), None) or deduits.get(vue.id)
        if trait is None:
            trait = coupes.deduire_trait(serialize_vue(vue), locaux, sheet.scale_denominator, echelle_vue)
            trait = {**trait, "nom": vue.nom, "vue_id": vue.id} if trait else {"nom": vue.nom, "vue_id": vue.id, "deduit": True, "points": None}
            deduits[vue.id] = trait
            nouveaux = True
        if not trait.get("points"):
            non_situees.append(vue.nom)
            continue
        r = coupes.rattacher(trait, sheet.scale_denominator, locaux, serialize_vue(vue), echelle_vue)
        rattachements[vue.nom] = r
        lectures.append({"trait": trait["nom"], "deduit": bool(trait.get("deduit")), "vue_id": vue.id,
                         "vue_sheet_id": vue.sheet_id, "vue": vue.nom, **r})
    sans_vue = [t["nom"] for t in releves if not any(meme_coupe(t["nom"], v.nom) for v in vues)]
    if nouveaux:
        # Un trait déduit est gardé avec la planche : la recherche prend plusieurs secondes par coupe.
        # Seuls restent les traits déduits de vues encore présentes (une relecture de planche change les vues).
        presentes = {vue.id for vue in vues}
        gardes = [t for vue_id, t in deduits.items() if vue_id in presentes]
        sheet.traits_coupe_json = json.dumps(releves + gardes, ensure_ascii=False, separators=(",", ":"))
        db.commit()
    traits = releves + [t for t in deduits.values() if t.get("points")]

    proposees = coupes.hauteurs_des_locaux(locaux, rattachements)
    saisies = {l["id"]: l.get("hauteur_m") for l in contenu.get("locaux", [])}
    par_local = {}
    for local in locaux:
        proposee = proposees[local["id"]]
        saisie = saisies.get(local["id"])
        par_local[local["id"]] = {
            **proposee,
            "proposee_m": proposee["hauteur_m"],
            "hauteur_m": saisie if saisie is not None else proposee["hauteur_m"],
            "source": "saisie" if saisie is not None else proposee["source"],
        }
    return {
        "sheet_id": sheet.id,
        "locaux": par_local,
        "coupes": lectures,
        "traits_sans_vue": sans_vue,
        "coupes_non_situees": non_situees,
        "traits": traits,
    }


def confirmer_hauteur(db: Session, vue: ThermiqueVue, sol: Any, plafond: Any) -> ThermiqueVue:
    """Deux clics dans la coupe, sol fini puis plafond fini d'une pièce (D191) : corrige la lecture de cet
    étage de la coupe. Une nouvelle confirmation au même étage remplace l'ancienne."""
    sheet = db.get(ThermiqueSheet, vue.sheet_id)
    if sheet is None or not sheet.scale_denominator:
        raise ThermiqueError("L'échelle de la planche de coupes n'est pas définie : la hauteur ne se mesure pas.")
    lecture = json.loads(vue.lecture_json)
    hx, hy = coupes._unitaire(lecture.get("haut") or [0, 1])
    bas, haut = (_point(p, "Un point cliqué") for p in (sol, plafond))
    position_sol = bas[0] * hx + bas[1] * hy
    position_plafond = haut[0] * hx + haut[1] * hy
    m = coupes.metres_par_point(sheet.scale_denominator)
    hauteur = (position_plafond - position_sol) * m
    if not HAUTEUR_MIN_M <= hauteur <= HAUTEUR_MAX_M:
        raise ThermiqueError(
            f"Les deux clics donnent {hauteur:.2f} m : cliquez d'abord le sol fini, puis le plafond fini, "
            f"d'une même pièce (entre {HAUTEUR_MIN_M:.2f} et {HAUTEUR_MAX_M:.0f} m)."
        )
    gardees = [
        c for c in lecture.get("corrections", [])
        if abs(float(c["sol"]) - position_sol) * m > coupes.CORRECTION_PORTEE_M
    ]
    lecture["corrections"] = gardees + [{"sol": position_sol, "plafond": position_plafond, "hauteur_m": round(hauteur, 3)}]
    vue.lecture_json = json.dumps(lecture, ensure_ascii=False, separators=(",", ":"))
    db.commit()
    db.refresh(vue)
    return vue


def retirer_confirmations(db: Session, vue: ThermiqueVue) -> ThermiqueVue:
    lecture = json.loads(vue.lecture_json)
    lecture.pop("corrections", None)
    vue.lecture_json = json.dumps(lecture, ensure_ascii=False, separators=(",", ":"))
    db.commit()
    db.refresh(vue)
    return vue


def preparer_hauteurs(project_id: int) -> None:
    """Déduit et garde les traits de coupe de chaque plan étudié du projet (D190), en tâche de fond.

    La recherche d'un trait prend plusieurs secondes par coupe : faite dès que les coupes sont lues, elle
    ne se fait pas attendre à l'ouverture d'une fiche.
    """
    import logging

    from app.core.db import SessionLocal
    from app.models.thermique import ThermiqueEtude

    db = SessionLocal()
    try:
        plans = db.scalars(
            select(ThermiqueSheet)
            .join(ThermiqueEtude, ThermiqueEtude.sheet_id == ThermiqueSheet.id)
            .where(ThermiqueSheet.project_id == project_id, ThermiqueSheet.nature == "plan")
        ).all()
        for plan in plans:
            try:
                hauteurs_du_plan(db, plan)
            except Exception:  # Une préparation ratée se refera à la première ouverture.
                logging.getLogger(__name__).exception("Hauteurs non préparées pour la planche %s", plan.id)
    finally:
        db.close()


def controler_hauteur(valeur: Any) -> float | None:
    """Une hauteur saisie par le thermicien : `None` la retire, sinon entre 1,50 m et 15 m."""
    if valeur is None:
        return None
    hauteur = _nombre(valeur, "La hauteur")
    if not HAUTEUR_MIN_M <= hauteur <= HAUTEUR_MAX_M:
        raise ThermiqueError(f"Une hauteur sous plafond se saisit entre {HAUTEUR_MIN_M:.2f} et {HAUTEUR_MAX_M:.0f} m.")
    return round(hauteur, 3)
