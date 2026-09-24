"""Éléments d'enveloppe : confirmer, corriger, écarter, réactiver (F4, D99 à D104).

Le risque du lot n'est pas le geste lui-même, c'est qu'il **ne survive pas au recalcul** : le dessin est
régénéré depuis le relevé brut à chaque fois. Les tests vérifient donc surtout ce qui reste écrit.
"""
from __future__ import annotations

import copy

import pytest

from app.services import thermique_elements as elements
from app.services.thermique import ThermiqueError


def _element(troncon="T02", debut=4.32, fin=7.3, **reste):
    base = {
        "troncon": troncon,
        "debut_m": debut,
        "fin_m": fin,
        "type": "menuiserie",
        "composant": "M1",
        "nu_exterieur_cm": -3,
        "nu_interieur_cm": -26,
        "nu_exterieur_fin_cm": -3,
        "nu_interieur_fin_cm": -26,
        "couches": [],
        "menuiserie_type": "mur-rideau",
        "cadre_cm": -4,
        "confiance": 0.85,
        "indice": "double trait fin vers -4, trait simple -26",
        "a_verifier": True,
    }
    base.update(reste)
    return base


def _etude(*liste):
    return {"enveloppe": {"releve_brut": {"elements": [copy.deepcopy(e) for e in liste], "catalogue": []}}}


def _ref(element):
    return elements.reference(element)


# --- Désigner un élément --------------------------------------------------------


def test_un_element_se_designe_par_sa_position_sur_l_enveloppe():
    """Sur le R+1, ce triplet distingue les 227 éléments sans un doublon ; le dessin le porte déjà."""
    premier = _element()
    second = _element(debut=7.3, fin=9.0)
    contenu = _etude(premier, second)

    assert elements.trouver(contenu, _ref(second))["debut_m"] == 7.3
    with pytest.raises(ThermiqueError, match="Aucun élément relevé"):
        elements.trouver(contenu, {"troncon": "T99", "debut_m": 0, "fin_m": 1})


# --- Confirmer ------------------------------------------------------------------


def test_confirmer_ne_change_que_le_doute():
    """Le geste le plus fréquent — 92 fois sur le R+1 — ne doit toucher à aucune mesure (D101)."""
    element = _element()
    contenu = _etude(element)
    avant = copy.deepcopy(contenu["enveloppe"]["releve_brut"]["elements"][0])

    elements.confirmer(contenu, _ref(element))
    apres = contenu["enveloppe"]["releve_brut"]["elements"][0]

    assert apres["a_verifier"] is False
    assert apres["confirme"] is True
    inchanges = {cle: valeur for cle, valeur in apres.items() if cle not in {"a_verifier", "confirme"}}
    assert inchanges == {cle: valeur for cle, valeur in avant.items() if cle != "a_verifier"}


# --- Corriger -------------------------------------------------------------------


def test_corriger_garde_ce_que_l_agent_avait_lu():
    """Q7 : comparer la lecture de l'agent et la correction humaine, niveau après niveau."""
    element = _element()
    contenu = _etude(element)

    elements.corriger(contenu, _ref(element), {"nu_interieur_cm": -32.0})
    corrige = contenu["enveloppe"]["releve_brut"]["elements"][0]

    assert corrige["nu_interieur_cm"] == -32.0
    assert corrige["releve_origine"]["nu_interieur_cm"] == -26
    assert corrige["a_verifier"] is False
    assert corrige["corrige"] is True


def test_corriger_deux_fois_garde_la_premiere_lecture():
    """Une correction d'une correction ne doit pas effacer ce que l'agent avait lu."""
    element = _element()
    contenu = _etude(element)

    elements.corriger(contenu, _ref(element), {"nu_interieur_cm": -32.0})
    elements.corriger(contenu, _ref(element), {"nu_interieur_cm": -35.0})

    corrige = contenu["enveloppe"]["releve_brut"]["elements"][0]
    assert corrige["nu_interieur_cm"] == -35.0
    assert corrige["releve_origine"]["nu_interieur_cm"] == -26


def test_un_nu_interieur_au_dela_de_l_exterieur_est_refuse():
    """Sur les 227 éléments du R+1, pas une exception : une saisie inversée est une faute de frappe."""
    element = _element()
    contenu = _etude(element)

    with pytest.raises(ThermiqueError, match="ne peut pas dépasser"):
        elements.corriger(contenu, _ref(element), {"nu_interieur_cm": 10.0})
    assert contenu["enveloppe"]["releve_brut"]["elements"][0]["nu_interieur_cm"] == -26


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"type": "fenetre_ronde"}, "Type d'élément inconnu"),
        ({"composant": "  "}, "ne peut pas être vide"),
        ({"nu_interieur_cm": "vingt"}, "nombre de centimètres"),
        ({"couches": []}, "ne se corrige pas dans ce lot"),
        ({"debut_m": 1}, "ne se corrige pas dans ce lot"),
    ],
)
def test_une_correction_invalide_est_refusee(changes, message):
    element = _element()
    contenu = _etude(element)
    with pytest.raises(ThermiqueError, match=message):
        elements.corriger(contenu, _ref(element), changes)


# --- Portée d'une correction de composant (Q3) ----------------------------------


def test_corriger_partout_touche_tous_les_porteurs_du_composant():
    """Sur le R+1, L1 est porté par 34 éléments, M1 par 29 : le choix ne peut pas être implicite."""
    vises = [_element(troncon=f"T{rang:02d}", debut=0, fin=1, composant="M1") for rang in range(1, 4)]
    autre = _element(troncon="T50", debut=0, fin=1, composant="P1")
    contenu = _etude(*vises, autre)

    touches = elements.corriger(
        contenu, _ref(vises[0]), {"type": "paroi"}, portee=elements.PORTEE_PARTOUT
    )

    assert len(touches) == 3
    liste = contenu["enveloppe"]["releve_brut"]["elements"]
    assert [e["type"] for e in liste] == ["paroi", "paroi", "paroi", "menuiserie"]
    assert all(e["releve_origine"]["type"] == "menuiserie" for e in liste[:3])


def test_corriger_ici_seulement_ne_touche_pas_les_voisins():
    vises = [_element(troncon=f"T{rang:02d}", debut=0, fin=1, composant="M1") for rang in range(1, 4)]
    contenu = _etude(*vises)

    touches = elements.corriger(contenu, _ref(vises[0]), {"type": "paroi"})

    assert len(touches) == 1
    assert [e["type"] for e in contenu["enveloppe"]["releve_brut"]["elements"]] == [
        "paroi",
        "menuiserie",
        "menuiserie",
    ]


def test_le_nombre_de_porteurs_est_connaissable_avant_de_choisir():
    """L'écran doit pouvoir annoncer « M1 est porté par 3 éléments » avant de demander la portée."""
    vises = [_element(troncon=f"T{rang:02d}", debut=0, fin=1, composant="M1") for rang in range(1, 4)]
    ecarte = _element(troncon="T09", debut=0, fin=1, composant="M1", exclu=True)
    contenu = _etude(*vises, ecarte)

    assert len(elements.porteurs_du_composant(contenu, "M1")) == 3


def test_une_portee_inconnue_est_refusee():
    element = _element()
    contenu = _etude(element)
    with pytest.raises(ThermiqueError, match="Portée inconnue"):
        elements.corriger(contenu, _ref(element), {"type": "paroi"}, portee="tout_le_projet")


# --- Écarter et réactiver (D100) ------------------------------------------------


def test_ecarter_conserve_l_element_et_sa_raison():
    element = _element()
    contenu = _etude(element)

    elements.ecarter(contenu, _ref(element), "trait de cotation pris pour une menuiserie")
    garde = contenu["enveloppe"]["releve_brut"]["elements"][0]

    assert garde["exclu"] is True
    assert "cotation" in garde["motif_exclusion"]
    # Il reste dans l'étude : on doit pouvoir le revoir grisé et le réactiver.
    assert len(contenu["enveloppe"]["releve_brut"]["elements"]) == 1


def test_ecarter_sans_raison_est_refuse():
    element = _element()
    contenu = _etude(element)
    with pytest.raises(ThermiqueError, match="pourquoi"):
        elements.ecarter(contenu, _ref(element), "   ")


def test_un_element_ecarte_sort_du_calcul_puis_y_revient():
    """Le point qui compte : ce que la chaîne de mesure voit."""
    garde = _element(troncon="T01", debut=0, fin=1)
    ecarte = _element(troncon="T02", debut=0, fin=1)
    contenu = _etude(garde, ecarte)
    elements.ecarter(contenu, _ref(ecarte), "élément fantôme")

    actif = elements.releve_actif(contenu["enveloppe"]["releve_brut"])
    assert [e["troncon"] for e in actif["elements"]] == ["T01"]

    elements.reactiver(contenu, _ref(ecarte))
    revenu = elements.releve_actif(contenu["enveloppe"]["releve_brut"])
    assert [e["troncon"] for e in revenu["elements"]] == ["T01", "T02"]
    assert "motif_exclusion" not in contenu["enveloppe"]["releve_brut"]["elements"][1]


def test_le_releve_actif_ne_modifie_pas_l_original():
    """La chaîne travaille sur une copie : l'étude garde la trace de tout ce qui a été écarté."""
    element = _element()
    contenu = _etude(element)
    elements.ecarter(contenu, _ref(element), "doublon")

    actif = elements.releve_actif(contenu["enveloppe"]["releve_brut"])
    actif["elements"].append({"troncon": "T99"})

    assert len(contenu["enveloppe"]["releve_brut"]["elements"]) == 1


# --- Compteurs ------------------------------------------------------------------


def test_les_compteurs_disent_ce_qui_reste_a_regarder():
    a_voir = _element(troncon="T01", debut=0, fin=1)
    a_voir_aussi = _element(troncon="T02", debut=0, fin=1)
    sur = _element(troncon="T03", debut=0, fin=1, a_verifier=False)
    contenu = _etude(a_voir, a_voir_aussi, sur)

    elements.confirmer(contenu, _ref(a_voir))
    elements.ecarter(contenu, _ref(a_voir_aussi), "fantôme")

    assert elements.compter(contenu) == {
        "total": 3,
        "a_verifier": 0,
        "confirmes": 1,
        "corriges": 0,
        "ecartes": 1,
    }


def test_les_locaux_comptent_des_elements_douteux_et_non_des_formes_dessinees():
    """Q5, et un écart trouvé sur le vrai R+1 : une paroi en couches donne plusieurs formes.

    Sur le R+1, 227 éléments produisent 289 formes. Compter les formes faisait annoncer 147 éléments
    douteux répartis sur les locaux, là où le compteur du niveau en annonce 92 ; le dédoublonnage ramène
    à 97. Les cinq restants sont des éléments mitoyens, signalés dans les deux locaux qu'ils séparent :
    cet écart-là est voulu.
    """
    paroi = {"troncon": "T01", "debut_m": 0.0, "fin_m": 4.2, "piece": "6.1.6 salle de reunion"}
    autre = {"troncon": "T02", "debut_m": 4.2, "fin_m": 9.0, "piece": "6.1.6 salle de reunion"}
    contenu = {
        "enveloppe": {
            "releve_brut": {"elements": []},
            "objets": [
                # Trois couches d'une même paroi : un seul élément douteux, pas trois.
                {"review_required": True, "source_parcours": dict(paroi)},
                {"review_required": True, "source_parcours": dict(paroi)},
                {"review_required": True, "source_parcours": dict(paroi)},
                {"review_required": True, "source_parcours": dict(autre)},
                {"review_required": False, "source_parcours": {**autre, "debut_m": 9.0, "fin_m": 12.0}},
                {"review_required": True, "source_parcours": {"piece": None}},
            ],
        }
    }
    assert elements.a_verifier_par_piece(contenu) == {"6.1.6 salle de reunion": 2}


def test_une_etude_sans_releve_le_dit_clairement():
    with pytest.raises(ThermiqueError, match="ne porte pas de relevé"):
        elements.compter({"enveloppe": {}})


def test_un_element_mitoyen_est_signale_dans_les_deux_locaux_qu_il_separe():
    """L'écart voulu : la somme par local dépasse le compteur du niveau, et c'est juste."""
    mitoyen = {"troncon": "T07", "debut_m": 0.0, "fin_m": 3.0}
    contenu = {
        "enveloppe": {
            "releve_brut": {"elements": []},
            "objets": [
                {"review_required": True, "source_parcours": {**mitoyen, "piece": "Bureau"}},
                {"review_required": True, "source_parcours": {**mitoyen, "piece": "Couloir"}},
            ],
        }
    }
    comptes = elements.a_verifier_par_piece(contenu)
    assert comptes == {"Bureau": 1, "Couloir": 1}
    assert sum(comptes.values()) == 2  # un seul élément, deux signalements
