"""Planchers repérés sur une coupe (lot M3) : hauteurs d'étage et épaisseurs de plancher.

Sur une coupe d'architecte, un plancher coupé est dessiné par **deux traits épais parallèles**
(dessus et dessous de dalle) sur toute sa portée. On regroupe les traits épais longs par position,
on apparie les lignes voisines espacées de 10 à 60 cm qui se recouvrent, puis on sépare les dessins
d'une même planche (coupe AB et coupe CD côte à côte) par les grands écarts.

Vérifié sur le projet d'essai (2026-09-14) : écarts entre dessus de planchers 4,16 / 3,84 / 3,84 m,
identiques aux cotes imprimées ; le dessin est tourné de 90° sur la feuille, d'où l'essai des deux
orientations. Le sens « vers le haut » n'est pas lisible géométriquement : il est choisi par le
thermicien (ou lu par l'IA, voir docs/thermique/agent-verification-decisions.md).
"""
from __future__ import annotations

from thermique_moteur.metre import pt_en_m

LONGUEUR_MIN_M = 1.0
# Une ligne de plancher cumule au moins 3 m ; un plancher porte sur au moins 2,5 m (écarte escaliers,
# acrotères, menuiseries et petits éléments parallèles).
LONGUEUR_LIGNE_MIN_M = 3.0
PORTEE_MIN_M = 2.5
REGROUPEMENT_M = 0.03
EPAISSEUR_MIN_M = 0.10
EPAISSEUR_MAX_M = 0.60
RECOUVREMENT_MIN = 0.5
ECART_ENTRE_DESSINS_M = 8.0


def _lignes(traits: list, seuil: float, axe: str, m: float) -> list[dict]:
    """Traits épais longs parallèles à l'axe des planchers, regroupés par position (en pt)."""
    lignes: list[dict] = []
    candidats = []
    for x1, y1, x2, y2, largeur, *_ in traits:
        if largeur < seuil - 1e-6:
            continue
        if axe == "horizontal":
            position, debut, fin, travers = (y1 + y2) / 2, min(x1, x2), max(x1, x2), abs(y2 - y1)
        else:
            position, debut, fin, travers = (x1 + x2) / 2, min(y1, y2), max(y1, y2), abs(x2 - x1)
        if travers > 0.3 or fin - debut < LONGUEUR_MIN_M * m:
            continue
        candidats.append((position, debut, fin))
    for position, debut, fin in sorted(candidats):
        if lignes and position - lignes[-1]["position"] <= REGROUPEMENT_M * m:
            ligne = lignes[-1]
            ligne["debut"], ligne["fin"] = min(ligne["debut"], debut), max(ligne["fin"], fin)
            ligne["longueur"] += fin - debut
        else:
            lignes.append({"position": position, "debut": debut, "fin": fin, "longueur": fin - debut})
    return [ligne for ligne in lignes if ligne["longueur"] >= LONGUEUR_LIGNE_MIN_M * m]


def _planchers(lignes: list[dict], m: float) -> list[dict]:
    planchers = []
    i = 0
    while i < len(lignes) - 1:
        a, b = lignes[i], lignes[i + 1]
        epaisseur = b["position"] - a["position"]
        commun = min(a["fin"], b["fin"]) - max(a["debut"], b["debut"])
        plus_court = min(a["fin"] - a["debut"], b["fin"] - b["debut"])
        if EPAISSEUR_MIN_M * m <= epaisseur <= EPAISSEUR_MAX_M * m and plus_court > 0 and commun / plus_court >= RECOUVREMENT_MIN and commun >= PORTEE_MIN_M * m:
            planchers.append(
                {
                    "face_1": a["position"],
                    "face_2": b["position"],
                    "epaisseur_m": round(epaisseur / m, 3),
                    "portee_m": round(commun / m, 2),
                }
            )
            i += 2
        else:
            i += 1
    return planchers


def detecter_planchers(traits: list, seuil: float, echelle: float) -> dict:
    """Planchers de chaque dessin de la coupe, dans l'orientation qui en trouve le plus.

    Positions en points PDF le long de l'axe perpendiculaire aux planchers ; distances en mètres,
    du premier plancher (plus petite coordonnée) au dernier.
    """
    m = 1.0 / pt_en_m(echelle)
    meilleur = {"axe": None, "dessins": []}
    for axe in ("horizontal", "vertical"):
        planchers = _planchers(_lignes(traits, seuil, axe, m), m)
        dessins: list[list[dict]] = []
        for plancher in planchers:
            if dessins and plancher["face_1"] - dessins[-1][-1]["face_2"] <= ECART_ENTRE_DESSINS_M * m:
                dessins[-1].append(plancher)
            else:
                dessins.append([plancher])
        dessins = [dessin for dessin in dessins if len(dessin) >= 2]
        total = sum(p["portee_m"] for dessin in dessins for p in dessin)
        if total > sum(p["portee_m"] for d in meilleur["dessins"] for p in d["planchers"]):
            meilleur = {
                "axe": axe,
                "pt_par_m": m,
                "dessins": [
                    {
                        "planchers": [
                            {**p, "position_m": round((p["face_1"] - dessin[0]["face_1"]) / m, 3)} for p in dessin
                        ],
                        # Écart entre faces homologues de deux planchers successifs = hauteur d'étage.
                        "hauteurs_etage_m": [round((b["face_2"] - a["face_2"]) / m, 2) for a, b in zip(dessin, dessin[1:])],
                        "hauteurs_libres_m": [round((b["face_1"] - a["face_2"]) / m, 2) for a, b in zip(dessin, dessin[1:])],
                    }
                    for dessin in dessins
                ],
            }
    return meilleur


def niveaux_depuis_coupe(dessin: dict, pt_par_m: float, sens_montant: bool) -> list[dict]:
    """Un intervalle par niveau, du bas vers le haut. `sens_montant` : la coordonnée PDF croît vers
    le haut du bâtiment (sinon on lit les planchers dans l'autre sens).

    Pour chaque niveau : épaisseur de son plancher, hauteur d'étage (dessus de dalle à dessus de la
    dalle suivante) et hauteur sous plafond brute (dessus de dalle à dessous de la dalle suivante)."""
    planchers = dessin["planchers"] if sens_montant else list(reversed(dessin["planchers"]))

    def dessus(p):
        return p["face_2"] if sens_montant else p["face_1"]

    def dessous(p):
        return p["face_1"] if sens_montant else p["face_2"]

    return [
        {
            "epaisseur_plancher_m": round(bas["epaisseur_m"], 2),
            "hauteur_etage_m": round(abs(dessus(haut) - dessus(bas)) / pt_par_m, 2),
            "hauteur_sous_plafond_m": round(abs(dessous(haut) - dessus(bas)) / pt_par_m, 2),
        }
        for bas, haut in zip(planchers, planchers[1:])
    ]
