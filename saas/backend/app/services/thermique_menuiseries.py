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
import logging
import re
import unicodedata
from pathlib import Path
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
        modele = element.get("modele") or None
        if (
            courante is not None
            and courante["composant"] == composant
            # D220 : deux menuiseries de modèles différents ne forment plus une seule baie.
            and courante["modele"] == modele
            and abs(courante["fin_m"] - float(element["debut_m"])) <= CONTIGU_M
        ):
            courante["fin_m"] = float(element["fin_m"])
            courante["morceaux"].append({"troncon": element["troncon"], "debut_m": element["debut_m"], "fin_m": element["fin_m"]})
            courante["mur_rideau"] = courante["mur_rideau"] or _mur_rideau(element)
            continue
        courante = {
            "composant": composant,
            "modele": modele,
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


def modeles(confirmations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Les modèles de menuiserie mesurés (D219) : la dernière mesure de chaque nom fait foi."""
    resultat: dict[str, dict[str, Any]] = {}
    for confirmation in confirmations:
        if confirmation.get("modele"):
            resultat[confirmation["modele"]] = confirmation
    return resultat


def _hauteur_de_la_baie(
    baie: dict[str, Any], confirmations: list[dict[str, Any]], par_modele: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Modèle posé (D220, D221) ; sinon hauteur propre à la baie, puis celle du composant, puis mur-rideau ou à lire."""
    modele = (par_modele or {}).get(baie.get("modele") or "")
    if modele is not None:
        return {
            "hauteur_m": modele["hauteur_m"],
            "source": "modele",
            "vue_id": modele["vue_id"],
            "vue": modele["vue"],
            "largeur_modele_cm": modele["largeur_mesuree_cm"],
        }
    du_composant = [c for c in confirmations if not c.get("modele") and c.get("composant") == baie["composant"]]
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
    par_modele = modeles(confirmations)
    poses: dict[str, int] = {}
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
            hauteur = _hauteur_de_la_baie(baie, confirmations, par_modele)
            # D221 : une baie posée hérite de la largeur du modèle mesuré ; l'écart avec le plan est signalé.
            largeur = hauteur.get("largeur_modele_cm") or baie["largeur_cm"]
            if baie.get("modele") in par_modele:
                poses[baie["modele"]] = poses.get(baie["modele"], 0) + 1
            fiche["baies"].append(
                {**baie, "sheet_id": planche.id, "niveau": planche.level_label or planche.label, **hauteur,
                 "largeur_retenue_cm": largeur,
                 "surface_m2": None if hauteur["hauteur_m"] is None else round(largeur / 100 * hauteur["hauteur_m"], 2),
                 "ecart_modele_cm": None if "largeur_modele_cm" not in hauteur
                 else round(baie["largeur_cm"] - hauteur["largeur_modele_cm"], 1)}
            )
    for fiche in composants.values():
        generales = [
            c for c in confirmations
            if not c.get("modele") and c.get("composant") == fiche["composant"] and c.get("largeur_cm") is None
        ]
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
        # D222 : la bibliothèque des modèles du projet.
        "modeles": [
            {"nom": nom, "largeur_cm": m["largeur_mesuree_cm"], "hauteur_m": m["hauteur_m"], "vue_id": m["vue_id"],
             "vue": m["vue"], "capture": bool(m.get("capture")), "horodatage": m.get("horodatage"),
             "poses": poses.get(nom, 0)}
            for nom, m in sorted(par_modele.items())
        ],
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


LARGEUR_MIN_M = 0.2
MARGE_CAPTURE = 0.3  # D222 : la capture déborde de 30 % autour de la menuiserie
MARGE_CAPTURE_MIN_PT = 12.0
COTE_CAPTURE_PX = 900


def dossier_des_captures(project_id: int) -> Path:
    from app.core.config import settings

    return Path(settings.thermique_storage_dir) / f"projet_{project_id}" / "modeles"


def nom_de_capture(nom: str, horodatage: str) -> str:
    """Nom de fichier sûr : le nom du modèle en clair, puis l'horodatage de la mesure."""
    propre = re.sub(r"[^A-Za-z0-9_-]+", "-", unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()).strip("-")
    instant = re.sub(r"[^0-9]", "", horodatage)[:14]
    return f"{propre or 'modele'}-{instant}.png"


def cadre_de_capture(coins: list[list[float]]) -> list[float]:
    """Le cadre (points PDF) de la capture : la menuiserie et une marge autour."""
    (ax, ay), (bx, by) = coins
    x0, x1, y0, y1 = min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)
    mx = max((x1 - x0) * MARGE_CAPTURE, MARGE_CAPTURE_MIN_PT)
    my = max((y1 - y0) * MARGE_CAPTURE, MARGE_CAPTURE_MIN_PT)
    return [x0 - mx, y0 - my, x1 + mx, y1 + my]


def capturer(pdf: Path, page_index: int, cadre: list[float], destination: Path) -> Path:
    """Découpe la planche autour de la menuiserie, en PNG (D222)."""
    import pypdfium2 as pdfium

    from app.services.thermique_raster import VERROU_PDFIUM

    x0, y0, x1, y1 = cadre
    echelle = COTE_CAPTURE_PX / max(x1 - x0, y1 - y0, 1.0)
    with VERROU_PDFIUM:
        document = pdfium.PdfDocument(str(pdf))
        try:
            page = document[page_index]
            gauche, bas, droite, haut = page.get_mediabox()
            image = page.render(
                scale=echelle,
                crop=(max(0.0, x0 - gauche), max(0.0, y0 - bas), max(0.0, droite - x1), max(0.0, haut - y1)),
            ).to_pil()
        finally:
            document.close()
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "PNG")
    return destination


def enregistrer_modele(
    db: Session,
    vue: ThermiqueVue,
    coins: Any,
    nom: str,
    horodatage: str,
    pdf: Path | None = None,
) -> dict[str, Any]:
    """Mesure un modèle de menuiserie par deux coins opposés et le garde avec sa capture (D219, D222).

    Une nouvelle mesure du même nom remplace l'ancienne pour toutes les menuiseries posées.
    """
    planche = db.get(ThermiqueSheet, vue.sheet_id)
    if planche is None or not planche.scale_denominator:
        raise ThermiqueError("L'échelle de la planche n'est pas définie : la menuiserie ne se mesure pas.")
    if not isinstance(coins, list) or len(coins) != 2:
        raise ThermiqueError("Cliquez deux coins opposés de la menuiserie.")
    propre = str(nom or "").strip()
    if not propre or len(propre) > 60:
        raise ThermiqueError("Donnez au modèle un nom de 1 à 60 caractères.")
    largeur_m, hauteur_m = mesurer(vue, planche.scale_denominator, coins[0], coins[1])
    if not HAUTEUR_MIN_M <= hauteur_m <= HAUTEUR_MAX_M or largeur_m < LARGEUR_MIN_M:
        raise ThermiqueError(
            f"Les deux coins donnent {largeur_m * 100:.0f} × {hauteur_m * 100:.0f} cm : cliquez deux coins opposés "
            "de la baie (en diagonale), cadre compris."
        )
    points = [[float(v) for v in p] for p in coins]
    capture = None
    if pdf is not None:
        try:
            fichier = nom_de_capture(propre, horodatage)
            capturer(pdf, planche.page_index, cadre_de_capture(points), dossier_des_captures(vue.project_id) / fichier)
            capture = fichier
        except Exception:  # Une capture ratée ne doit pas faire perdre la mesure.
            logging.getLogger(__name__).exception("Capture du modèle « %s » impossible", propre)
    confirmation = {
        "modele": propre,
        "largeur_mesuree_cm": round(largeur_m * 100, 1),
        "hauteur_m": round(hauteur_m, 3),
        "coins": points,
        "capture": capture,
        "horodatage": horodatage,
    }
    lecture = json.loads(vue.lecture_json)
    lecture.setdefault("menuiseries", []).append(confirmation)
    vue.lecture_json = json.dumps(lecture, ensure_ascii=False, separators=(",", ":"))
    db.commit()
    return {k: v for k, v in confirmation.items() if k != "coins"} | {"vue_id": vue.id, "vue": vue.nom}


def capture_du_modele(db: Session, project_id: int, nom: str) -> Path | None:
    modele = modeles(_confirmations(db, project_id)).get(nom)
    if modele is None or not modele.get("capture"):
        return None
    chemin = dossier_des_captures(project_id) / modele["capture"]
    return chemin if chemin.is_file() else None


def retirer_modele(db: Session, project_id: int, nom: str) -> None:
    """Retire un modèle de la bibliothèque (toutes ses mesures). Les menuiseries posées perdent sa hauteur."""
    for vue in db.scalars(select(ThermiqueVue).where(ThermiqueVue.project_id == project_id)).all():
        lecture = json.loads(vue.lecture_json)
        gardees = [c for c in lecture.get("menuiseries", []) if c.get("modele") != nom]
        if len(gardees) != len(lecture.get("menuiseries", [])):
            lecture["menuiseries"] = gardees
            vue.lecture_json = json.dumps(lecture, ensure_ascii=False, separators=(",", ":"))
    db.commit()


def retirer(db: Session, vue: ThermiqueVue, composant: str) -> None:
    """Retire les hauteurs confirmées sur cette vue pour ce composant (générale et par baie)."""
    lecture = json.loads(vue.lecture_json)
    lecture["menuiseries"] = [c for c in lecture.get("menuiseries", []) if c.get("composant") != composant]
    vue.lecture_json = json.dumps(lecture, ensure_ascii=False, separators=(",", ":"))
    db.commit()
