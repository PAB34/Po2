"""Contrôle de cohérence de fin de chaîne (lot F1, D77).

Deux lectures indépendantes existent pour chaque niveau : les **contours** des locaux, vus par
``thermicien-plan``, et les **nus mesurés** de l'enveloppe, relevés bande par bande par
``thermicien-enveloppe``. Jusqu'ici personne ne les confrontait, et un défaut visible à l'œil nu — toute
l'épaisseur des murs comptée comme surface sans local — a traversé la chaîne sans un mot.

Ce module confronte les deux lectures avant d'écrire le fichier d'étude. Il ne corrige rien et
n'interrompt rien : il rend visible ce qui ne colle pas, dans ``A-FAIRE.md`` et dans le fichier lui-même.
C'est aussi ce qui permettra de mesurer la qualité des agents dans le temps, niveau après niveau.

Tout se calcule dans le repère de la page (``manifeste["page_px"]``), comme le reste du lot.
"""
from __future__ import annotations

from typing import Any

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import unary_union

from app.services import thermique_calage_contours as calage
from app.services import thermique_enveloppe_pieces as pieces_env
from app.services import thermique_etude_geometrie as geo
from app.services import thermique_fiches_locaux as fiches_locaux

# Les six contrôles de D77, dans l'ordre où ils sont rendus.
CONTROLES = (
    ("couverture", "Surface intérieure sans local"),
    ("chevauchement", "Locaux qui se recouvrent"),
    ("morsure_paroi", "Locaux qui mordent dans une paroi mesurée"),
    ("debord_emprise", "Locaux qui débordent du bâtiment"),
    ("ecart_facade", "Écart entre le contour et la façade relevée"),
    ("enveloppe_orpheline", "Côtés et éléments d'enveloppe sans vis-à-vis"),
)

# Sous ces seuils, l'écart n'est que du bruit de tracé et ne mérite pas d'être signalé.
MORSURE_MIN_M2 = 0.10
MORSURE_PROFONDEUR_MIN_M = 0.03
DEBORD_MIN_M2 = 0.50
# Même règle que la fiche de local : 15 % de la façade relevée, jamais moins de 30 cm.
ECART_FACADE_PART = 0.15
ECART_FACADE_MIN_M = 0.30
# Un côté extérieur plus court que cela ne prouve rien sur l'enveloppe.
COTE_EXTERIEUR_MIN_M = 0.50


def _en_px(points: list[list[float]], largeur: float, hauteur: float) -> list[tuple[float, float]]:
    return [(x * largeur / 1000, y * hauteur / 1000) for x, y in points]


def _polygone(contour: list[list[float]], largeur: float, hauteur: float) -> Polygon:
    forme = Polygon(_en_px(contour, largeur, hauteur)).buffer(0)
    if isinstance(forme, MultiPolygon):
        forme = max(forme.geoms, key=lambda part: part.area)
    return forme if isinstance(forme, Polygon) else Polygon()


def _controle(code: str, titre: str, anomalies: list[dict[str, Any]], resume: str) -> dict[str, Any]:
    return {
        "code": code,
        "titre": titre,
        "statut": "attention" if anomalies else "ok",
        "resume": resume,
        "anomalies": anomalies,
    }


def _couverture(contenu: dict[str, Any]) -> dict[str, Any]:
    """1. Zones de l'emprise intérieure qu'aucun local ne couvre (D60)."""
    couverture = contenu.get("couverture") or {}
    manquante = float(couverture.get("surface_non_affectee_m2") or 0.0)
    zones = couverture.get("zones_non_affectees") or []
    anomalies = []
    if manquante > 0:
        anomalies.append(
            {
                "message": f"{manquante:.1f} m² d'intérieur ne sont affectés à aucun local, en {len(zones)} zone(s)",
                "surface_m2": round(manquante, 2),
                "zones": len(zones),
            }
        )
    taux = couverture.get("taux_couverture_pct")
    return _controle(
        "couverture",
        "Surface intérieure sans local",
        anomalies,
        f"{taux} % de l'emprise intérieure est couverte" if taux is not None else "couverture non calculée",
    )


def _chevauchements(contenu: dict[str, Any], noms: dict[str, str]) -> dict[str, Any]:
    """2. Locaux qui se recouvrent : le seul défaut qui fausse vraiment les surfaces."""
    couverture = contenu.get("couverture") or {}
    anomalies = [
        {
            "locaux": paire.get("locaux", []),
            "message": " et ".join(noms.get(identifiant, identifiant) for identifiant in paire.get("locaux", []))
            + f" se recouvrent sur {float(paire.get('surface_m2') or 0):.2f} m²",
            "surface_m2": paire.get("surface_m2"),
        }
        for paire in couverture.get("chevauchements", [])
    ]
    total = float(couverture.get("chevauchement_m2") or 0.0)
    return _controle(
        "chevauchement",
        "Locaux qui se recouvrent",
        anomalies,
        f"{total:.2f} m² de recouvrement" if total else "aucun recouvrement",
    )


def _morsures(analyse: dict[str, Any], manifeste: dict[str, Any], releve: dict[str, Any]) -> dict[str, Any]:
    """3. Locaux dont le contour entre dans une paroi mesurée, avec le déplacement nécessaire.

    C'est le calage lui-même qui répond : rejoué sur un fichier déjà calé, il ne trouve plus rien.
    """
    if not releve.get("elements"):
        return _controle("morsure_paroi", "Locaux qui mordent dans une paroi mesurée", [],
                         "aucun relevé d'enveloppe : contrôle impossible")
    _cale, rapport = calage.caler_locaux(analyse, manifeste, releve)
    anomalies = [
        {
            "local": ligne.get("id"),
            "message": f"« {ligne.get('nom')} » entre de {ligne['deplacement_max_m'] * 100:.0f} cm dans une paroi "
            f"mesurée ({ligne['surface_retiree_m2']:.2f} m²)",
            "surface_m2": ligne["surface_retiree_m2"],
            "deplacement_m": ligne["deplacement_max_m"],
        }
        for ligne in rapport
        if ligne["surface_retiree_m2"] >= MORSURE_MIN_M2 or ligne["deplacement_max_m"] >= MORSURE_PROFONDEUR_MIN_M
    ]
    return _controle(
        "morsure_paroi",
        "Locaux qui mordent dans une paroi mesurée",
        anomalies,
        f"{len(anomalies)} local(aux) à recaler" if anomalies else "tous les contours s'arrêtent au nu intérieur",
    )


def _debords(locaux: list[dict[str, Any]], manifeste: dict[str, Any]) -> dict[str, Any]:
    """4. Locaux qui sortent de l'emprise du bâtiment (l'emprise suit la face extérieure)."""
    largeur, hauteur = (float(valeur) for valeur in manifeste["page_px"])
    m2 = float(manifeste["px_par_m"]) ** 2
    emprise = geo.emprise_interieure(manifeste)
    if emprise.is_empty:
        return _controle("debord_emprise", "Locaux qui débordent du bâtiment", [], "emprise du bâtiment inconnue")
    anomalies = []
    for local in locaux:
        contour = local.get("contour") or []
        if len(contour) < 3:
            continue
        dehors = _polygone(contour, largeur, hauteur).difference(emprise)
        surface = dehors.area / m2
        if surface >= DEBORD_MIN_M2:
            anomalies.append(
                {
                    "local": local.get("id"),
                    "message": f"« {local.get('nom')} » déborde du bâtiment sur {surface:.2f} m²",
                    "surface_m2": round(surface, 2),
                }
            )
    return _controle(
        "debord_emprise",
        "Locaux qui débordent du bâtiment",
        anomalies,
        f"{len(anomalies)} local(aux) hors emprise" if anomalies else "tous les locaux sont dans le bâtiment",
    )


def _ecarts_facade(locaux: list[dict[str, Any]]) -> dict[str, Any]:
    """5. Écart entre la mesure du contour et celle du relevé, local par local.

    Le tour extérieur d'un local vient du plan ; la façade relevée vient du parcours d'enveloppe. Deux
    lectures de la même longueur : quand elles divergent, l'une des deux se trompe.
    """
    anomalies = []
    for local in locaux:
        cotes = (local.get("fiche") or {}).get("cotes") or []
        contour_m = sum(float(cote.get("longueur_m") or 0) for cote in cotes if cote.get("adjacence") == "exterieur")
        facade_m = float((local.get("synthese") or {}).get("facade_m") or 0.0)
        if facade_m <= 0:
            continue
        ecart = abs(contour_m - facade_m)
        if ecart > max(ECART_FACADE_PART * facade_m, ECART_FACADE_MIN_M):
            anomalies.append(
                {
                    "local": local.get("id"),
                    "message": f"« {local.get('nom')} » : {contour_m:.2f} m de côtés extérieurs au contour contre "
                    f"{facade_m:.2f} m de façade relevée",
                    "ecart_m": round(ecart, 2),
                    "contour_m": round(contour_m, 2),
                    "releve_m": round(facade_m, 2),
                }
            )
    return _controle(
        "ecart_facade",
        "Écart entre le contour et la façade relevée",
        anomalies,
        f"{len(anomalies)} local(aux) où les deux lectures divergent" if anomalies else "les deux lectures concordent",
    )


def _orphelins(
    locaux: list[dict[str, Any]],
    analyse: dict[str, Any],
    manifeste: dict[str, Any],
    releve: dict[str, Any],
) -> dict[str, Any]:
    """6. Côtés extérieurs sans élément d'enveloppe en regard, et éléments sans local en regard."""
    anomalies = []
    for local in locaux:
        nus = [
            cote
            for cote in (local.get("fiche") or {}).get("cotes") or []
            if cote.get("adjacence") == "exterieur"
            and not cote.get("enveloppe")
            and float(cote.get("longueur_m") or 0) >= COTE_EXTERIEUR_MIN_M
        ]
        if nus:
            longueur = sum(float(cote["longueur_m"]) for cote in nus)
            anomalies.append(
                {
                    "local": local.get("id"),
                    "sens": "cote_sans_element",
                    "message": f"« {local.get('nom')} » : {longueur:.2f} m de côtés extérieurs sans élément "
                    f"d'enveloppe relevé ({len(nus)} côté(s))",
                    "longueur_m": round(longueur, 2),
                }
            )

    largeur, hauteur = (float(valeur) for valeur in manifeste["page_px"])
    px_par_m = float(manifeste["px_par_m"])
    par_troncon = {troncon["id"]: troncon for troncon in manifeste["troncons"]}
    exclus = {
        composant.get("id")
        for composant in releve.get("catalogue", [])
        if composant.get("decision") == "exclu"
    }
    contours = [forme for _nom, forme in pieces_env.pieces_du_plan(analyse, largeur, hauteur)]
    bords = unary_union([forme.exterior for forme in contours]) if contours else None
    portee = fiches_locaux.RATTACHEMENT_M * px_par_m
    sans_local: dict[str, float] = {}
    for element in releve.get("elements", []):
        troncon = par_troncon.get(element.get("troncon"))
        if troncon is None or element.get("type") not in calage.FACES:
            continue
        if (element.get("composant") or "") in exclus:
            continue
        face = pieces_env.face_interieure(element, troncon, px_par_m)
        if len(face) < 2:
            continue
        milieu = Point(face[len(face) // 2])
        if bords is None or bords.distance(milieu) > portee:
            longueur = float(element["fin_m"]) - float(element["debut_m"])
            sans_local[element["troncon"]] = sans_local.get(element["troncon"], 0.0) + longueur
    for troncon, longueur in sorted(sans_local.items()):
        if longueur >= COTE_EXTERIEUR_MIN_M:
            anomalies.append(
                {
                    "troncon": troncon,
                    "sens": "element_sans_cote",
                    "message": f"tronçon {troncon} : {longueur:.2f} m d'enveloppe relevée sans local en regard",
                    "longueur_m": round(longueur, 2),
                }
            )
    return _controle(
        "enveloppe_orpheline",
        "Côtés et éléments d'enveloppe sans vis-à-vis",
        anomalies,
        f"{len(anomalies)} rapprochement(s) manquant(s)" if anomalies else "chaque côté extérieur a son enveloppe",
    )


def controler_niveau(contenu: dict[str, Any]) -> dict[str, Any]:
    """Les six contrôles de D77 sur un fichier d'étude assemblé ou recalculé.

    Aucune correction, aucun blocage : le rapport dit ce qui ne colle pas et va dans le fichier.
    """
    manifeste = contenu["enveloppe"]["manifeste"]
    releve = contenu["enveloppe"].get("releve_brut") or {}
    analyse = contenu["analyse"]
    locaux = contenu.get("locaux") or []
    noms = {str(local.get("id")): str(local.get("nom") or local.get("id")) for local in locaux}

    controles = [
        _couverture(contenu),
        _chevauchements(contenu, noms),
        _morsures(analyse, manifeste, releve),
        _debords(locaux, manifeste),
        _ecarts_facade(locaux),
        _orphelins(locaux, analyse, manifeste, releve),
    ]
    total = sum(len(controle["anomalies"]) for controle in controles)
    return {
        "version": 1,
        "niveau": contenu.get("niveau"),
        "locaux": len(locaux),
        "anomalies": total,
        "statut": "attention" if total else "ok",
        "controles": controles,
    }


def rapport_markdown(coherence: dict[str, Any]) -> list[str]:
    """Le rapport tel qu'il s'écrit dans ``A-FAIRE.md``, une ligne par anomalie."""
    if coherence.get("statut") == "ok":
        return [
            f"\n## Contrôle de cohérence : rien à signaler ({coherence.get('locaux')} locaux)\n",
            "Les contours du plan et les nus mesurés de l'enveloppe concordent sur les six contrôles.",
        ]
    lignes = [f"\n## Contrôle de cohérence : {coherence.get('anomalies')} point(s) à regarder\n"]
    for controle in coherence.get("controles", []):
        if not controle["anomalies"]:
            continue
        lignes.append(f"### {controle['titre']}\n")
        lignes += [f"- {anomalie['message']}" for anomalie in controle["anomalies"]]
        lignes.append("")
    return lignes
