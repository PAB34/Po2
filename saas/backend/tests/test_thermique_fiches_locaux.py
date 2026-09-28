"""Fiche par local : adjacence, épaisseur et caractère déperditif de chaque côté (D29 à D33)."""
import math

from app.services import thermique_fiches_locaux as fiches_locaux

PX_PAR_M = 100.0


def _manifeste():
    # bâtiment de 10 x 5 m (face extérieure) ; un seul tronçon par côté, parcours horaire à l'écran
    coins = [(0, 0), (1000, 0), (1000, 500), (0, 500)]
    troncons, abscisse = [], 0.0
    for rang, (a, b) in enumerate(zip(coins, coins[1:] + coins[:1]), 1):
        longueur = math.dist(a, b) / PX_PAR_M
        u = ((b[0] - a[0]) / (longueur * PX_PAR_M), (b[1] - a[1]) / (longueur * PX_PAR_M))
        troncons.append({"id": f"T{rang:02d}", "origine_px": list(a), "direction": list(u), "normale_ext": [u[1], -u[0]],
                         "debut_m": abscisse, "fin_m": abscisse + longueur, "local_debut_m": 0.0, "piece": ""})
        abscisse += longueur
    return {"px_par_m": PX_PAR_M, "page_px": [1000, 1000], "troncons": troncons, "perimetre_m": abscisse}


def _piece(ident, nom, x0, y0, x1, y1, local="chauffe"):
    return {"id": ident, "category": "piece", "subtype": nom, "local": local,
            "points": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}


def test_adjacences_epaisseurs_et_cotes_deperditifs():
    # murs de façade de 30 cm, refend de 20 cm entre le bureau (chauffé) et le local technique (non chauffé)
    analyse = {"objects": [_piece("piece-001", "Bureau", 30, 30, 490, 470),
                           _piece("piece-002", "Local technique", 510, 30, 970, 470, local="non_chauffe")]}

    resultat = {f["piece"]: f for f in fiches_locaux.fiches(analyse, _manifeste())}

    bureau = resultat["Bureau"]
    exterieurs = [c for c in bureau["cotes"] if c["adjacence"] == "exterieur"]
    assert math.isclose(sum(c["longueur_m"] for c in exterieurs), 4.6 + 4.4 + 4.6, abs_tol=0.15)
    assert all(28 <= c["epaisseur_cm"] <= 35 for c in exterieurs) and all(c["deperditif"] for c in exterieurs)
    technique = next(c for c in bureau["cotes"] if c["adjacence"] == "non_chauffe")
    assert technique["voisin"] == "Local technique" and technique["deperditif"]
    assert 20 <= technique["epaisseur_cm"] <= 26 and math.isclose(technique["longueur_m"], 4.4, abs_tol=0.15)
    # un local non chauffé ne porte pas de déperditions
    assert resultat["Local technique"]["deperditif_m"] == 0
    assert bureau["a_completer"] and bureau["local"] == "chauffe"


def test_une_gaine_se_comporte_comme_un_local_non_chauffe():
    analyse = {"objects": [_piece("piece-001", "Bureau", 30, 30, 490, 470),
                           _piece("piece-002", "Gaine", 510, 30, 970, 470, local="gaine_technique")]}

    resultat = {f["piece"]: f for f in fiches_locaux.fiches(analyse, _manifeste())}

    cote_gaine = next(c for c in resultat["Bureau"]["cotes"] if c["adjacence"] == "gaine_technique")
    assert cote_gaine["voisin"] == "Gaine" and cote_gaine["deperditif"]
    assert resultat["Gaine"]["deperditif_m"] == 0


def test_une_terrasse_classee_exterieur_fait_deperdir_son_voisin_et_porte_une_liaison():
    """Remarque F, D161 : hors volume elle-même, elle rend déperditif le côté commun, qui porte la liaison."""
    analyse = {"objects": [_piece("piece-001", "Bureau", 30, 30, 490, 470),
                           _piece("piece-002", "Terrasse", 510, 30, 970, 470, local="exterieur")]}

    resultat = {f["piece"]: f for f in fiches_locaux.fiches(analyse, _manifeste())}

    commun = next(c for c in resultat["Bureau"]["cotes"] if c["voisin"] == "Terrasse")
    assert commun["adjacence"] == "exterieur" and commun["deperditif"] and commun["liaison_exterieur"]
    assert math.isclose(resultat["Bureau"]["liaison_exterieur_m"], commun["longueur_m"])
    # La façade donne sur l'air libre : déperditive, mais sans dalle attenante, donc sans liaison.
    facade = [c for c in resultat["Bureau"]["cotes"] if c["voisin"] == fiches_locaux.AIR_LIBRE]
    assert facade and all(c["deperditif"] and not c["liaison_exterieur"] for c in facade)
    # La terrasse n'est pas chauffée : ni déperdition, ni liaison à son compte.
    assert resultat["Terrasse"]["deperditif_m"] == 0 and resultat["Terrasse"]["liaison_exterieur_m"] == 0


def test_une_terrasse_relevee_par_l_agent_se_distingue_de_l_air_libre():
    analyse = {"objects": [_piece("piece-001", "Bureau", 30, 30, 490, 470),
                           {"id": "t", "category": "terrasse", "subtype": "terrasse",
                            "points": [[510, 30], [970, 30], [970, 470], [510, 470]]}]}

    bureau = {f["piece"]: f for f in fiches_locaux.fiches(analyse, _manifeste())}["Bureau"]

    commun = next(c for c in bureau["cotes"] if c["voisin"] == fiches_locaux.TERRASSE_OBJET)
    assert commun["adjacence"] == "exterieur" and commun["liaison_exterieur"]


def test_orientation_calee_sur_le_nord():
    assert fiches_locaux.orientation((0, -1), 0) == "N"  # normale vers le haut de la feuille, nord en haut
    assert fiches_locaux.orientation((1, 0), 0) == "E"
    assert fiches_locaux.orientation((0, -1), 90) == "O"  # nord à droite de la feuille
    assert fiches_locaux.orientation((0, -1), None) == "nord à caler"


def test_cotes_courts_rejoignent_leur_voisin_et_se_fusionnent():
    sondages = [{"p": (k, 0), "longueur": 0.1, "adjacence": a, "voisin": v, "epaisseur": 20, "normale": (0, -1)}
                for k, (a, v) in enumerate([("chauffe", "A")] * 10 + [("inconnu", "")] + [("chauffe", "A")] * 10)]
    cotes = fiches_locaux._regrouper(sondages)
    assert len(cotes) == 1 and math.isclose(cotes[0]["longueur"], 2.1)
