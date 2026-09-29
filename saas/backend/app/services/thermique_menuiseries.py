"""Baies et hauteur des menuiseries lue en élévation (S5e : D193, D194, D196 à D200).

**Baie (D199).** Des menuiseries contiguës de même composant, sans rien entre elles, même de part et d'autre
d'une jonction de tronçons, forment une baie : c'est la fusion d'office de D174. Le relevé garde ses morceaux
(leur identité porte les corrections du thermicien) ; la baie est l'unité qui se compte et reçoit une hauteur.

**Hauteur par composant (D200).** Une hauteur confirmée sur une élévation, par deux coins opposés d'une
menuiserie (D193), vaut pour toutes les baies du composant, sur tous les niveaux ; une baie peut recevoir sa
propre hauteur, qui l'emporte. Un mur-rideau prend la hauteur sous plafond du local qu'il borde (D196).

Les confirmations sont gardées avec la vue d'élévation (`lecture_json["menuiseries"]`) : pas de table nouvelle.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.thermique import ThermiqueEtude, ThermiqueSheet, ThermiqueVue
from app.services import thermique_coupes as coupes
from app.services import thermique_elements as elements_releve
from app.services.thermique import ThermiqueError

CONTIGU_M = 0.02  # deux morceaux d'une même baie se touchent à 2 cm près
MORCEAU_CM = 40.0  # une baie seule plus étroite est à vérifier
IDENTIQUES_CM = 1.0  # D176 : une largeur de baie à ± 1 cm
PROPOSITION_CM = 5.0  # D194
HAUTEUR_MIN_M = 0.3
HAUTEUR_MAX_M = 12.0


def _mur_rideau(element: dict[str, Any]) -> bool:
    return "rideau" in str(element.get("menuiserie_type") or "").lower()


def baies_du_releve(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Les baies d'un niveau (D199), dans l'ordre du parcours de l'enveloppe.

    Les abscisses `debut_m` / `fin_m` du relevé sont globales au parcours : deux morceaux qui se suivent d'un
    tronçon au suivant se touchent. Un élément actif quelconque entre eux (poteau, about, angle) sépare.
    """
    actifs = sorted(
        (e for e in elements if elements_releve.est_actif(e)),
        key=lambda e: (float(e["debut_m"]), float(e["fin_m"])),
    )
    baies: list[dict[str, Any]] = []
    courante: dict[str, Any] | None = None
    for element in actifs:
        if element.get("type") != "menuiserie":
            courante = None
            continue
        composant = str(element.get("composant") or "?")
        if (
            courante is not None
            and courante["composant"] == composant
            and abs(courante["fin_m"] - float(element["debut_m"])) <= CONTIGU_M
        ):
            courante["fin_m"] = float(element["fin_m"])
            courante["morceaux"].append({"troncon": element["troncon"], "debut_m": element["debut_m"], "fin_m": element["fin_m"]})
            courante["mur_rideau"] = courante["mur_rideau"] or _mur_rideau(element)
            continue
        courante = {
            "composant": composant,
            "debut_m": float(element["debut_m"]),
            "fin_m": float(element["fin_m"]),
            "mur_rideau": _mur_rideau(element),
            "morceaux": [{"troncon": element["troncon"], "debut_m": element["debut_m"], "fin_m": element["fin_m"]}],
        }
        baies.append(courante)
    for baie in baies:
        baie["largeur_cm"] = round((baie["fin_m"] - baie["debut_m"]) * 100, 1)
        baie["morceau_a_verifier"] = baie["largeur_cm"] < MORCEAU_CM
    return baies


def _confirmations(db: Session, project_id: int) -> list[dict[str, Any]]:
    """Toutes les hauteurs confirmées sur les vues du projet, de la plus ancienne à la plus récente."""
    resultat = []
    for vue in db.scalars(select(ThermiqueVue).where(ThermiqueVue.project_id == project_id).order_by(ThermiqueVue.id)).all():
        for rang, confirmation in enumerate(json.loads(vue.lecture_json).get("menuiseries", [])):
            resultat.append({**confirmation, "vue_id": vue.id, "vue": vue.nom, "rang": rang})
    return sorted(resultat, key=lambda c: (c.get("horodatage") or "", c["vue_id"], c["rang"]))


def _hauteur_de_la_baie(baie: dict[str, Any], confirmations: list[dict[str, Any]]) -> dict[str, Any]:
    """Hauteur propre à la baie si elle en a une, sinon celle du composant, sinon mur-rideau ou à lire."""
    du_composant = [c for c in confirmations if c.get("composant") == baie["composant"]]
    propres = [
        c for c in du_composant
        if c.get("largeur_cm") is not None and abs(float(c["largeur_cm"]) - baie["largeur_cm"]) <= IDENTIQUES_CM
    ]
    generales = [c for c in du_composant if c.get("largeur_cm") is None]
    retenue = (propres or generales or [None])[-1]
    if retenue is not None:
        return {
            "hauteur_m": retenue["hauteur_m"],
            "source": "baie" if propres else "composant",
            "vue_id": retenue["vue_id"],
            "vue": retenue["vue"],
        }
    if baie["mur_rideau"]:
        return {"hauteur_m": None, "source": "hauteur_du_local", "vue_id": None, "vue": None}
    return {"hauteur_m": None, "source": "a_lire", "vue_id": None, "vue": None}


def menuiseries_du_projet(db: Session, project_id: int) -> dict[str, Any]:
    """Les composants de menuiserie du projet, leurs baies sur tous les niveaux étudiés, et leur hauteur."""
    confirmations = _confirmations(db, project_id)
    planches = db.scalars(
        select(ThermiqueSheet)
        .join(ThermiqueEtude, ThermiqueEtude.sheet_id == ThermiqueSheet.id)
        .where(ThermiqueSheet.project_id == project_id)
        .order_by(ThermiqueSheet.id)
    ).all()
    composants: dict[str, dict[str, Any]] = {}
    for planche in planches:
        etude = db.scalar(select(ThermiqueEtude).where(ThermiqueEtude.sheet_id == planche.id))
        contenu = json.loads(etude.content_json) if etude else {}
        elements = contenu.get("enveloppe", {}).get("releve_brut", {}).get("elements", [])
        for baie in baies_du_releve(elements):
            fiche = composants.setdefault(
                baie["composant"],
                {"composant": baie["composant"], "mur_rideau": False, "baies": []},
            )
            fiche["mur_rideau"] = fiche["mur_rideau"] or baie["mur_rideau"]
            fiche["baies"].append(
                {**baie, "sheet_id": planche.id, "niveau": planche.level_label or planche.label,
                 **_hauteur_de_la_baie(baie, confirmations)}
            )
    for fiche in composants.values():
        generales = [c for c in confirmations if c.get("composant") == fiche["composant"] and c.get("largeur_cm") is None]
        fiche["hauteur_m"] = generales[-1]["hauteur_m"] if generales else None
        fiche["confirmation"] = (
            {"vue_id": generales[-1]["vue_id"], "vue": generales[-1]["vue"],
             "largeur_mesuree_cm": generales[-1].get("largeur_mesuree_cm")}
            if generales else None
        )
        fiche["a_lire"] = sum(1 for b in fiche["baies"] if b["source"] == "a_lire")
    liste = sorted(composants.values(), key=lambda f: f["composant"])
    return {
        "composants": liste,
        "morceaux_a_verifier": [
            {"composant": b["composant"], "largeur_cm": b["largeur_cm"], "niveau": b["niveau"], "morceaux": b["morceaux"]}
            for f in liste for b in f["baies"] if b["morceau_a_verifier"]
        ],
    }


def mesurer(vue: ThermiqueVue, echelle: float, coin_a: Any, coin_b: Any) -> tuple[float, float]:
    """Largeur et hauteur (m) d'une menuiserie à partir de deux coins opposés cliqués sur l'élévation."""
    lecture = json.loads(vue.lecture_json)
    hx, hy = coupes._unitaire(lecture.get("haut") or [0, 1])
    dx, dy = hy, -hx
    (ax, ay), (bx, by) = ([float(v) for v in p] for p in (coin_a, coin_b))
    m = coupes.metres_par_point(echelle)
    return abs((bx - ax) * dx + (by - ay) * dy) * m, abs((bx - ax) * hx + (by - ay) * hy) * m


def proposer(composants: list[dict[str, Any]], largeur_cm: float) -> list[dict[str, Any]]:
    """Les composants qui ont une baie à ± 5 cm de la largeur mesurée, le plus proche d'abord (D194)."""
    proches = []
    for fiche in composants:
        ecarts = [abs(b["largeur_cm"] - largeur_cm) for b in fiche["baies"]]
        if ecarts and min(ecarts) <= PROPOSITION_CM:
            proches.append({"composant": fiche["composant"], "ecart_cm": round(min(ecarts), 1)})
    return sorted(proches, key=lambda p: p["ecart_cm"])


def confirmer(
    db: Session,
    vue: ThermiqueVue,
    coins: Any,
    composant: str,
    largeur_cm: float | None,
    horodatage: str,
) -> dict[str, Any]:
    """Garde la hauteur mesurée pour tout un composant (`largeur_cm` absent) ou pour une baie (D193, D200)."""
    planche = db.get(ThermiqueSheet, vue.sheet_id)
    if planche is None or not planche.scale_denominator:
        raise ThermiqueError("L'échelle de la planche n'est pas définie : la menuiserie ne se mesure pas.")
    if not isinstance(coins, list) or len(coins) != 2:
        raise ThermiqueError("Cliquez deux coins opposés de la menuiserie.")
    largeur_m, hauteur_m = mesurer(vue, planche.scale_denominator, coins[0], coins[1])
    if not HAUTEUR_MIN_M <= hauteur_m <= HAUTEUR_MAX_M:
        raise ThermiqueError(f"Les deux coins donnent une hauteur de {hauteur_m:.2f} m : cliquez deux coins opposés.")
    fiche = next((f for f in menuiseries_du_projet(db, vue.project_id)["composants"] if f["composant"] == composant), None)
    if fiche is None:
        raise ThermiqueError(f"Aucune baie « {composant} » dans les niveaux étudiés.")
    largeurs = [b["largeur_cm"] for b in fiche["baies"]] if largeur_cm is None else [float(largeur_cm)]
    ecart = min(abs(largeur_m * 100 - l) for l in largeurs)
    if ecart > PROPOSITION_CM:
        raise ThermiqueError(
            f"La menuiserie cliquée mesure {largeur_m * 100:.0f} cm de large : aucune baie « {composant} » "
            f"{'' if largeur_cm is None else f'de {largeur_cm:.0f} cm '}à ± {PROPOSITION_CM:.0f} cm. "
            "Ce n'est sans doute pas la même menuiserie."
        )
    confirmation = {
        "composant": composant,
        "largeur_cm": None if largeur_cm is None else round(float(largeur_cm), 1),
        "hauteur_m": round(hauteur_m, 3),
        "largeur_mesuree_cm": round(largeur_m * 100, 1),
        "coins": [[float(v) for v in p] for p in coins],
        "horodatage": horodatage,
    }
    lecture = json.loads(vue.lecture_json)
    lecture.setdefault("menuiseries", []).append(confirmation)
    vue.lecture_json = json.dumps(lecture, ensure_ascii=False, separators=(",", ":"))
    db.commit()
    return {k: v for k, v in confirmation.items() if k != "coins"}


def retirer(db: Session, vue: ThermiqueVue, composant: str) -> None:
    """Retire les hauteurs confirmées sur cette vue pour ce composant (générale et par baie)."""
    lecture = json.loads(vue.lecture_json)
    lecture["menuiseries"] = [c for c in lecture.get("menuiseries", []) if c.get("composant") != composant]
    vue.lecture_json = json.dumps(lecture, ensure_ascii=False, separators=(",", ":"))
    db.commit()
