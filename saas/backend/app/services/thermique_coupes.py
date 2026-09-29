"""Coupes : rattacher les pièces d'une coupe aux locaux d'un plan, et en tirer la hauteur de chaque local.

Lot S5c + S5d (`docs/thermique/coupes-elevations-S5-decisions.md`, D178 à D185). Aucun agent ici : la lecture
d'une coupe (ses pièces, leurs bornes, leur sol et leur plafond) arrive déjà faite ; ce module ne fait que
de la géométrie.

**Repères.** Tout est en points PDF de la page d'où vient la donnée (origine en bas à gauche, y vers le haut),
comme le reste de l'application.

- Un **trait de coupe** est relevé sur un plan : une ligne brisée (`points`) et le **sens du regard**
  (`sens`, vecteur). Regarder dans le sens d = (dx, dy), c'est avoir la **droite** en (dy, −dx).
- Une **vue** est relevée sur une planche de coupe : le vecteur `haut` de la vue dans la page (une coupe
  peut être tournée d'un quart de tour), puis pour chaque pièce ses bornes gauche/droite (`debut`, `fin`)
  mesurées le long de la **droite de la vue**, et son sol et son plafond (`sol`, `plafond`) mesurés le long
  du **haut de la vue**, tous en points de la page.

Une coupe ne se lit que par projection sur sa droite : les décrochés du trait, parallèles au regard,
n'occupent aucune largeur dans la coupe. L'abscisse d'un point du plan est donc sa projection sur la droite
du regard, en mètres. Entre cette abscisse et celle de la coupe, il ne manque qu'un décalage, que l'on
trouve par les numéros de programme communs (6.1.2, 4.3.4…) puis, à défaut, par le recouvrement.
"""
from __future__ import annotations

import re
import statistics
from typing import Any

from shapely.geometry import LineString, Polygon
from shapely.geometry.base import BaseGeometry

M_PAR_PT_A_L_ECHELLE_1 = 0.0254 / 72

# Un trait de coupe peut passer dans l'épaisseur d'un mur, à quelques centimètres des locaux qu'il
# coupe (projet 1, coupe A : 5 à 7 cm). Un local à moins de cette distance est candidat.
TOLERANCE_TRAIT_M = 0.15
# Une pièce de la coupe se rattache à un local qui en couvre au moins cette part.
RECOUVREMENT_MIN = 0.5
# Deux pièces sont au même étage quand leurs sols diffèrent de moins de ceci.
TOLERANCE_SOL_M = 0.30
# Une pièce qui monte plus haut que ceci au-dessus d'un sol traverse cet étage (double hauteur).
TRAVERSEE_MIN_M = 1.0
# Au-delà de cet écart entre deux lectures d'un même local, la fiche le signale (D180).
ECART_LECTURES_M = 0.05
# Au-delà de cet écart entre le décalage donné par les noms et celui donné par le recouvrement, on
# le dit : l'un des deux est faux.
ECART_DECALAGE_M = 0.30
PAS_RECHERCHE_M = 0.02

NUMERO = re.compile(r"(?<![\d.])(\d+(?:\.\d+)+)(?![\d.])")


def metres_par_point(echelle: float) -> float:
    return M_PAR_PT_A_L_ECHELLE_1 * float(echelle)


def numero_programme(nom: str | None) -> str | None:
    """Le numéro du programme en tête d'un nom (« 6.1.2 B.asst (3) » → « 6.1.2 »), la clé fiable.

    Les noms sont abrégés dans les coupes (« 4.3.4 Jeux vidéo » pour « 4.3.4 et 4.5.2 lecture confort ») :
    seul le premier numéro compte.
    """
    trouve = NUMERO.search(nom or "")
    return trouve.group(1) if trouve else None


def _droite(sens: Any) -> tuple[float, float]:
    dx, dy = (float(v) for v in sens)
    norme = (dx * dx + dy * dy) ** 0.5
    if norme <= 0:
        raise ValueError("Le sens du regard d'une coupe est nul.")
    return dy / norme, -dx / norme


def _unitaire(vecteur: Any) -> tuple[float, float]:
    x, y = (float(v) for v in vecteur)
    norme = (x * x + y * y) ** 0.5
    if norme <= 0:
        raise ValueError("Le haut d'une vue est nul.")
    return x / norme, y / norme


def _projeter(geometrie: BaseGeometry, droite: tuple[float, float]) -> tuple[float, float] | None:
    points = [
        c
        for partie in getattr(geometrie, "geoms", [geometrie])
        for c in (partie.exterior.coords if isinstance(partie, Polygon) else partie.coords)
    ]
    if not points:
        return None
    valeurs = [x * droite[0] + y * droite[1] for x, y in points]
    return min(valeurs), max(valeurs)


def traversees_du_plan(
    trait: dict[str, Any], locaux: list[dict[str, Any]], echelle_plan: float
) -> list[dict[str, Any]]:
    """Les locaux que le trait coupe, ou frôle à moins de `TOLERANCE_TRAIT_M`, avec leur étendue en mètres
    le long de la droite du regard.

    `locaux` : [{"id", "nom", "contour_pdf"}] en points de la page du plan.
    """
    m = metres_par_point(echelle_plan)
    droite = _droite(trait["sens"])
    ligne = LineString([(float(x), float(y)) for x, y in trait["points"]])
    bande = ligne.buffer(TOLERANCE_TRAIT_M / m, cap_style=2)
    resultat = []
    for local in locaux:
        points = local.get("contour_pdf") or []
        if len(points) < 3:
            continue
        forme = Polygon([(float(x), float(y)) for x, y in points]).buffer(0)
        coupe = forme.intersection(ligne)
        direct = not coupe.is_empty and coupe.length > 0
        # Frôlé : on garde la part du local qui est dans la bande, projetée sur la droite du regard.
        partie = coupe if direct else forme.intersection(bande)
        if partie.is_empty or (not direct and partie.area <= 0):
            continue
        etendue = _projeter(partie, droite)
        if etendue is None or etendue[1] - etendue[0] <= 0:
            continue
        resultat.append(
            {
                "local": local["id"],
                "nom": local.get("nom"),
                "numero": numero_programme(local.get("nom")),
                "debut_m": etendue[0] * m,
                "fin_m": etendue[1] * m,
                "direct": direct,
                "distance_m": 0.0 if direct else forme.distance(ligne) * m,
            }
        )
    return resultat


def _altimetrie(vue: dict[str, Any], m: float):
    """Convertit un sol ou un plafond en altitude (m) : un nom de ligne de niveau (« H10 ») donne sa cote
    écrite ; une position (points, le long du haut de la vue) est calée sur les lignes de niveau dont on
    connaît à la fois la position et la cote, sinon laissée dans le repère de la page."""
    niveaux = {str(n["nom"]): n for n in vue.get("niveaux", []) if n.get("nom") is not None}
    reperes = [
        float(n["cote_m"]) - float(n["position"]) * m
        for n in niveaux.values()
        if n.get("cote_m") is not None and n.get("position") is not None
    ]
    origine = statistics.mean(reperes) if reperes else 0.0

    def altitude(valeur: Any) -> float:
        if isinstance(valeur, str):
            niveau = niveaux.get(valeur)
            if niveau is None or niveau.get("cote_m") is None:
                raise ValueError(f"La ligne de niveau « {valeur} » n'a pas de cote dans la vue.")
            return float(niveau["cote_m"])
        return float(valeur) * m + origine

    return altitude


def pieces_de_la_vue(vue: dict[str, Any], echelle_vue: float) -> list[dict[str, Any]]:
    """Les pièces de la vue en mètres : abscisse le long de la droite de la vue, altitude le long de son haut.

    Les bornes arrivent en points de la page, mesurées le long de la droite (`debut`, `fin`) ; le sol et le
    plafond sont une position le long du haut de la vue, ou le nom d'une ligne de niveau de la vue.
    """
    m = metres_par_point(echelle_vue)
    altitude = _altimetrie(vue, m)
    resultat = []
    for index, piece in enumerate(vue.get("pieces", [])):
        debut, fin = sorted((float(piece["debut"]), float(piece["fin"])))
        plafond = piece.get("plafond")
        resultat.append(
            {
                "rang": index,
                "nom": piece.get("nom"),
                "numero": numero_programme(piece.get("nom")),
                "debut_m": debut * m,
                "fin_m": fin * m,
                "sol_m": altitude(piece["sol"]),
                "plafond_m": None if plafond is None else altitude(plafond),
                "hsp_ecrite_m": piece.get("hsp_ecrite_m"),
                "exterieur": bool(piece.get("exterieur")),
            }
        )
    return resultat


def etages(pieces: list[dict[str, Any]]) -> list[float]:
    """Les sols distincts de la coupe, du plus bas au plus haut (à `TOLERANCE_SOL_M` près)."""
    sols: list[float] = []
    for sol in sorted(p["sol_m"] for p in pieces):
        if not sols or sol - sols[-1] > TOLERANCE_SOL_M:
            sols.append(sol)
    return sols


def _a_l_etage(piece: dict[str, Any], sol: float) -> bool:
    if abs(piece["sol_m"] - sol) <= TOLERANCE_SOL_M:
        return True
    # Double hauteur : posée plus bas, elle monte à travers cet étage.
    plafond = piece["plafond_m"]
    return piece["sol_m"] < sol and plafond is not None and plafond - sol >= TRAVERSEE_MIN_M


def _recouvrement(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _decalage_par_les_noms(pieces: list[dict[str, Any]], plan: list[dict[str, Any]]) -> tuple[float | None, int]:
    """Décalage coupe → plan donné par les numéros communs : pour chaque numéro, le centre de ses pièces
    dans la coupe contre le centre de ses locaux dans le plan (plusieurs bureaux 6.1.2 : un bloc)."""
    ecarts = []
    for numero in {p["numero"] for p in pieces if p["numero"] and not p["exterieur"]}:
        dans_coupe = [p for p in pieces if p["numero"] == numero]
        dans_plan = [t for t in plan if t["numero"] == numero]
        if not dans_plan:
            continue
        c_coupe = (min(p["debut_m"] for p in dans_coupe) + max(p["fin_m"] for p in dans_coupe)) / 2
        c_plan = (min(t["debut_m"] for t in dans_plan) + max(t["fin_m"] for t in dans_plan)) / 2
        ecarts.append(c_plan - c_coupe)
    if not ecarts:
        return None, 0
    return statistics.median(ecarts), len(ecarts)


def _score(decalage: float, pieces: list[dict[str, Any]], plan: list[dict[str, Any]]) -> float:
    return sum(
        _recouvrement(p["debut_m"] + decalage, p["fin_m"] + decalage, t["debut_m"], t["fin_m"])
        for p in pieces
        if not p["exterieur"]
        for t in plan
        if t["direct"]
    )


def _decalage_par_recouvrement(pieces: list[dict[str, Any]], plan: list[dict[str, Any]]) -> float | None:
    interieures = [p for p in pieces if not p["exterieur"]]
    if not interieures or not plan:
        return None
    bas = min(t["debut_m"] for t in plan) - max(p["fin_m"] for p in interieures)
    haut = max(t["fin_m"] for t in plan) - min(p["debut_m"] for p in interieures)
    pas = int((haut - bas) / PAS_RECHERCHE_M) + 1
    meilleur, valeur = None, 0.0
    for i in range(pas + 1):
        decalage = bas + i * PAS_RECHERCHE_M
        score = _score(decalage, pieces, plan)
        if score > valeur + 1e-9:
            meilleur, valeur = decalage, score
    return meilleur


def _hauteur(piece: dict[str, Any], sol: float) -> float | None:
    """Hauteur sous plafond fini (D178) : écrite si la coupe la donne, sinon mesurée ; aucune pour un
    volume en double hauteur, qui n'a pas de plafond à cet étage."""
    if abs(piece["sol_m"] - sol) > TOLERANCE_SOL_M:
        return None
    if piece["hsp_ecrite_m"] is not None:
        return round(float(piece["hsp_ecrite_m"]), 3)
    if piece["plafond_m"] is None:
        return None
    return round(piece["plafond_m"] - piece["sol_m"], 3)


def rattacher(
    trait: dict[str, Any],
    echelle_plan: float,
    locaux: list[dict[str, Any]],
    vue: dict[str, Any],
    echelle_vue: float,
) -> dict[str, Any]:
    """Rattache les pièces d'une vue de coupe aux locaux d'un plan, dans le sens du regard qui colle le mieux.

    Le sens lu sur le plan (drapeau, flèche) est une convention graphique que l'agent peut mal lire (essai du
    2026-09-29 : coupe B lue « haut » au lieu de « bas »). Retourner le regard inverse l'ordre des pièces :
    on essaie donc les deux sens et la coupe tranche ; un sens corrigé est signalé.
    """
    direct = _rattacher_dans_un_sens(trait, echelle_plan, locaux, vue, echelle_vue)
    inverse_trait = {**trait, "sens": [-float(v) for v in trait["sens"]]}
    inverse = _rattacher_dans_un_sens(inverse_trait, echelle_plan, locaux, vue, echelle_vue)
    if inverse["score"] > direct["score"] * 1.2 + 1e-9:
        inverse["alertes"].insert(0, "sens du regard lu sur le plan contredit par la coupe : sens retourné")
        inverse["sens_retourne"] = True
        return inverse
    direct["sens_retourne"] = False
    return direct


def _rattacher_dans_un_sens(
    trait: dict[str, Any],
    echelle_plan: float,
    locaux: list[dict[str, Any]],
    vue: dict[str, Any],
    echelle_vue: float,
) -> dict[str, Any]:
    """Rattache les pièces d'une vue de coupe aux locaux d'un plan, à l'étage qui leur ressemble le plus.

    Rend l'étage retenu, le décalage et comment il a été trouvé, une ligne par pièce de la coupe (local
    rattaché, hauteur, et pourquoi), les désaccords entre la position et le nom, et le score de ressemblance.
    """
    plan = traversees_du_plan(trait, locaux, echelle_plan)
    toutes = pieces_de_la_vue(vue, echelle_vue)
    # La vue se lit de gauche à droite comme le trait se lit vers la droite du regard : même orientation.
    candidats = []
    for sol in etages(toutes):
        pieces = [p for p in toutes if _a_l_etage(p, sol)]
        par_noms, nombre = _decalage_par_les_noms(pieces, plan)
        par_recouvrement = _decalage_par_recouvrement(pieces, plan)
        decalage = par_noms if par_noms is not None else par_recouvrement
        if decalage is None:
            continue
        candidats.append(
            {
                "sol_m": sol,
                "pieces": pieces,
                "decalage_m": decalage,
                "par_noms_m": par_noms,
                "numeros_communs": nombre,
                "par_recouvrement_m": par_recouvrement,
                "score": _score(decalage, pieces, plan) + nombre * 100.0,
            }
        )
    if not candidats:
        return {
            "etage_sol_m": None, "decalage_m": None, "lignes": [], "score": 0.0,
            "alertes": ["aucun local du plan ne se retrouve dans cette coupe"],
        }
    retenu = max(candidats, key=lambda c: c["score"])
    decalage = retenu["decalage_m"]
    alertes = []
    if (
        retenu["par_noms_m"] is not None
        and retenu["par_recouvrement_m"] is not None
        and abs(retenu["par_noms_m"] - retenu["par_recouvrement_m"]) > ECART_DECALAGE_M
    ):
        alertes.append(
            "les noms et les positions ne calent pas la coupe au même endroit "
            f"({retenu['par_noms_m'] - retenu['par_recouvrement_m']:+.2f} m) : le calage par les noms est retenu"
        )

    lignes = []
    for piece in retenu["pieces"]:
        debut, fin = piece["debut_m"] + decalage, piece["fin_m"] + decalage
        longueur = fin - debut
        recouverts = [
            (t, _recouvrement(debut, fin, t["debut_m"], t["fin_m"]))
            for t in plan
        ]
        recouverts = [(t, r) for t, r in recouverts if longueur > 0 and r / longueur >= RECOUVREMENT_MIN]
        ligne = {
            "piece": piece["nom"],
            "numero": piece["numero"],
            "local": None,
            "longueur_m": round(longueur, 3),
            "hsp_m": None if piece["exterieur"] else _hauteur(piece, retenu["sol_m"]),
            "double_hauteur": not piece["exterieur"] and abs(piece["sol_m"] - retenu["sol_m"]) > TOLERANCE_SOL_M,
            "par": None,
        }
        if piece["exterieur"]:
            ligne["par"] = "extérieur"
        elif recouverts:
            memes = [(t, r) for t, r in recouverts if piece["numero"] and t["numero"] == piece["numero"]]
            if memes:
                choisi, _ = max(memes, key=lambda tr: tr[1])
                ligne["par"] = "nom et position"
            else:
                # Sans nom commun, le local qui épouse la pièce : recouvrement rapporté à la plus grande des
                # deux étendues. Une circulation qui longe tout le trait ne l'emporte pas sur le bureau
                # dont la largeur est celle de la pièce (projet 1, coupe A).
                choisi, _ = max(
                    recouverts,
                    key=lambda tr: (tr[0]["direct"], tr[1] / max(longueur, tr[0]["fin_m"] - tr[0]["debut_m"])),
                )
                ligne["par"] = "position"
                if piece["numero"] and choisi["numero"] and choisi["numero"] != piece["numero"]:
                    alertes.append(
                        f"« {piece['nom']} » tombe sur « {choisi['nom']} » : le numéro ne correspond pas"
                    )
            ligne["local"] = choisi["local"]
        lignes.append(ligne)
    # Ressemblance : chaque pièce dont le numéro tombe sur son local compte plus que tout recouvrement ;
    # c'est ce qui départage les deux sens du regard (un regard retourné inverse l'ordre des pièces).
    concordants = sum(1 for l in lignes if l["par"] == "nom et position")
    return {
        "etage_sol_m": retenu["sol_m"],
        "decalage_m": round(decalage, 3),
        "calage": "noms" if retenu["par_noms_m"] is not None else "recouvrement",
        "numeros_communs": retenu["numeros_communs"],
        "lignes": lignes,
        "alertes": alertes,
        "score": concordants * 100.0 + _score(decalage, retenu["pieces"], plan),
    }


def hauteurs_des_locaux(
    locaux: list[dict[str, Any]], rattachements: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """La hauteur proposée de chaque local (D178 à D180), et d'où elle vient.

    - lue : une ou plusieurs coupes la donnent ; plusieurs lectures → moyenne pondérée par la longueur
      traversée, signalée si elles diffèrent (D180) ;
    - double hauteur : le local est traversé par un volume sans plafond à cet étage, rien n'est inventé ;
    - déduite : aucune coupe ne le traverse ; il prend la hauteur la plus fréquente des locaux lus du
      niveau (D179), modifiable.
    """
    lectures: dict[str, list[dict[str, Any]]] = {}
    for nom_vue, rattachement in rattachements.items():
        for ligne in rattachement.get("lignes", []):
            if ligne.get("local"):
                lectures.setdefault(ligne["local"], []).append({"vue": nom_vue, **ligne})

    resultat: dict[str, dict[str, Any]] = {}
    lues: list[float] = []
    for local in locaux:
        propres = lectures.get(local["id"], [])
        chiffrees = [l for l in propres if l["hsp_m"] is not None]
        if chiffrees:
            poids = sum(l["longueur_m"] for l in chiffrees) or len(chiffrees)
            moyenne = sum(l["hsp_m"] * (l["longueur_m"] or 1) for l in chiffrees) / poids
            ecart = max(l["hsp_m"] for l in chiffrees) - min(l["hsp_m"] for l in chiffrees)
            resultat[local["id"]] = {
                "hauteur_m": round(moyenne, 2),
                "source": "lue" if len(chiffrees) == 1 else "moyenne",
                "lectures": [{"vue": l["vue"], "hsp_m": l["hsp_m"], "longueur_m": l["longueur_m"]} for l in chiffrees],
                "alerte": f"lectures différentes de {ecart:.2f} m" if ecart > ECART_LECTURES_M else None,
            }
            lues.append(round(moyenne, 2))
        elif any(l["double_hauteur"] for l in propres):
            resultat[local["id"]] = {
                "hauteur_m": None,
                "source": "double_hauteur",
                "lectures": [],
                "alerte": "double hauteur : pas de plafond à cet étage dans la coupe",
            }
    frequente = statistics.mode(lues) if lues else None
    for local in locaux:
        if local["id"] not in resultat:
            resultat[local["id"]] = {
                "hauteur_m": frequente,
                "source": "deduite" if frequente is not None else "absente",
                "lectures": [],
                "alerte": None,
            }
    return resultat
