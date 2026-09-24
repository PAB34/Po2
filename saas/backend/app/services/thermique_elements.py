"""Corriger, confirmer et écarter un élément d'enveloppe relevé (F4, D99 à D104).

Sur le R+1 réel, **92 des 227 éléments** arrivent marqués « à vérifier ». Sans moyen de les traiter, ce
compteur ne descend jamais et l'étude reste douteuse. Ce service donne les quatre gestes qui le font
descendre : confirmer, corriger, écarter, réactiver.

Règle qui gouverne tout le reste (D99) : **une correction s'écrit dans le relevé brut, jamais dans le
dessin**. Les 289 formes de `enveloppe.objets` sont régénérées à chaque recalcul depuis ce relevé ; une
correction posée sur elles disparaîtrait au premier recalcul.
"""
from __future__ import annotations

import copy
from typing import Any

from app.services.thermique import ThermiqueError

# Un élément est désigné par sa position sur l'enveloppe. Sur le R+1, ce triplet distingue les 227
# éléments sans un seul doublon, et `objets[].source_parcours` le porte déjà : le dessin sait donc
# remonter à son relevé sans qu'on ajoute d'identifiant.
CLES_REFERENCE = ("troncon", "debut_m", "fin_m")

# Types lus par l'agent sur le R+1. Refuser un type inconnu évite qu'une faute de frappe fasse sortir
# l'élément de tous les calculs sans que personne ne le voie.
TYPES_CONNUS = (
    "paroi",
    "menuiserie",
    "poteau",
    "garde_corps",
    "angle_sortant",
    "angle_rentrant",
    "about_refend",
    "indetermine",
)

# Ce que F4 laisse corriger : les trois familles qui changent le calcul (Q1). Les couches, le type de
# menuiserie, le cadre et les bornes sur le tronçon sont reportés — voir D104.
CHAMPS_CORRIGEABLES = (
    "type",
    "composant",
    "nu_exterieur_cm",
    "nu_interieur_cm",
    "nu_exterieur_fin_cm",
    "nu_interieur_fin_cm",
)

NUS = ("nu_exterieur_cm", "nu_interieur_cm", "nu_exterieur_fin_cm", "nu_interieur_fin_cm")

# Portées d'une correction de composant (Q3) : jamais implicite, toujours demandée.
PORTEE_CET_ELEMENT = "cet_element"
PORTEE_PARTOUT = "partout"
PORTEES = (PORTEE_CET_ELEMENT, PORTEE_PARTOUT)


def reference(element: dict[str, Any]) -> dict[str, Any]:
    return {cle: element.get(cle) for cle in CLES_REFERENCE}


def _cle(source: dict[str, Any]) -> tuple:
    return tuple(source.get(cle) for cle in CLES_REFERENCE)


def _elements(contenu: dict[str, Any]) -> list[dict[str, Any]]:
    releve = contenu.get("enveloppe", {}).get("releve_brut", {})
    elements = releve.get("elements")
    if not isinstance(elements, list):
        raise ThermiqueError("L'étude ne porte pas de relevé d'enveloppe.")
    return elements


def trouver(contenu: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any]:
    cherche = _cle(ref)
    for element in _elements(contenu):
        if _cle(element) == cherche:
            return element
    raise ThermiqueError(
        f"Aucun élément relevé en {ref.get('troncon')} entre {ref.get('debut_m')} et {ref.get('fin_m')} m."
    )


def est_actif(element: dict[str, Any]) -> bool:
    return not element.get("exclu")


def releve_actif(releve_brut: dict[str, Any]) -> dict[str, Any]:
    """Le relevé tel que le calcul doit le voir : sans les éléments écartés (D100).

    Les écartés restent dans l'étude, avec leur motif, pour rester visibles et réactivables ; ils ne
    sortent que de la chaîne de mesure.
    """
    actif = copy.deepcopy(releve_brut)
    actif["elements"] = [element for element in actif.get("elements", []) if est_actif(element)]
    return actif


def _memoriser_origine(element: dict[str, Any], champs: list[str]) -> None:
    """Garde ce que l'agent avait lu à côté de ce que le thermicien corrige (Q7).

    C'est ce qui permettra de mesurer la qualité de la lecture niveau après niveau. On ne mémorise que
    la **première** valeur : une correction d'une correction ne doit pas effacer la lecture d'origine.
    """
    origine = element.setdefault("releve_origine", {})
    for champ in champs:
        origine.setdefault(champ, element.get(champ))


def confirmer(contenu: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any]:
    """Le geste le plus fréquent — 92 fois sur le R+1 — et il ne change rien d'autre (D101)."""
    element = trouver(contenu, ref)
    element["a_verifier"] = False
    element["confirme"] = True
    return element


def _controler(element: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    propres: dict[str, Any] = {}
    for champ, valeur in changes.items():
        if champ not in CHAMPS_CORRIGEABLES:
            raise ThermiqueError(f"Le champ « {champ} » ne se corrige pas dans ce lot.")
        if champ == "type":
            if valeur not in TYPES_CONNUS:
                raise ThermiqueError(f"Type d'élément inconnu : « {valeur} ».")
            propres[champ] = valeur
        elif champ == "composant":
            texte = str(valeur or "").strip()
            if not texte:
                raise ThermiqueError("Le composant ne peut pas être vide.")
            propres[champ] = texte
        else:
            if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
                raise ThermiqueError(f"« {champ} » doit être un nombre de centimètres.")
            propres[champ] = float(valeur)

    futur = {**element, **propres}
    # Le nu intérieur est toujours en deçà du nu extérieur : sur les 227 éléments du R+1, pas une
    # exception. Une saisie inversée passerait sinon inaperçue et fausserait toutes les épaisseurs.
    for debut, fin in (("nu_exterieur_cm", "nu_interieur_cm"), ("nu_exterieur_fin_cm", "nu_interieur_fin_cm")):
        if futur.get(fin) is not None and futur.get(debut) is not None and futur[fin] > futur[debut]:
            raise ThermiqueError(
                f"Le nu intérieur ({futur[fin]} cm) ne peut pas dépasser le nu extérieur ({futur[debut]} cm)."
            )
    return propres


def porteurs_du_composant(contenu: dict[str, Any], composant: str) -> list[dict[str, Any]]:
    """Les éléments actifs qui portent ce composant : le nombre à annoncer avant de corriger (Q3)."""
    return [
        element
        for element in _elements(contenu)
        if est_actif(element) and element.get("composant") == composant
    ]


def corriger(
    contenu: dict[str, Any],
    ref: dict[str, Any],
    changes: dict[str, Any],
    portee: str = PORTEE_CET_ELEMENT,
) -> list[dict[str, Any]]:
    """Corrige un élément, et éventuellement tous ceux qui partagent son composant (Q3).

    La portée n'est jamais implicite : `partout` n'existe que si l'appelant l'a demandée, après avoir vu
    combien d'éléments seraient touchés. Sur le R+1, `L1` est porté par 34 éléments, `M1` par 29 et `P1`
    par 27 : un choix deviné dans un sens ou dans l'autre ferait des dégâts silencieux.
    """
    if portee not in PORTEES:
        raise ThermiqueError(f"Portée inconnue : « {portee} ».")
    element = trouver(contenu, ref)
    propres = _controler(element, changes)
    if not propres:
        return []

    cibles = [element]
    if portee == PORTEE_PARTOUT:
        composant = element.get("composant")
        if not composant:
            raise ThermiqueError("Cet élément ne porte aucun composant : la correction ne peut viser que lui.")
        # On ne corrige « partout » que ce qui décrit le composant, pas la position de chaque élément.
        cibles = porteurs_du_composant(contenu, composant)

    champs = list(propres)
    for cible in cibles:
        _memoriser_origine(cible, champs)
        cible.update(propres)
        cible["a_verifier"] = False
        cible["corrige"] = True
    return cibles


def ecarter(contenu: dict[str, Any], ref: dict[str, Any], motif: str) -> dict[str, Any]:
    """Écarter n'est pas supprimer (D100) : l'élément reste, avec la raison, et peut revenir."""
    texte = str(motif or "").strip()
    if not texte:
        raise ThermiqueError("Dites pourquoi vous écartez cet élément : la raison sera relue plus tard.")
    element = trouver(contenu, ref)
    element["exclu"] = True
    element["motif_exclusion"] = texte[:300]
    element["a_verifier"] = False
    return element


def reactiver(contenu: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any]:
    element = trouver(contenu, ref)
    element.pop("exclu", None)
    element.pop("motif_exclusion", None)
    return element


def compter(contenu: dict[str, Any]) -> dict[str, int]:
    """Compteurs du niveau : ce qui reste à regarder, et ce qui a été traité."""
    elements = _elements(contenu)
    return {
        "total": len(elements),
        "a_verifier": sum(1 for element in elements if est_actif(element) and element.get("a_verifier")),
        "confirmes": sum(1 for element in elements if element.get("confirme")),
        "corriges": sum(1 for element in elements if element.get("corrige")),
        "ecartes": sum(1 for element in elements if not est_actif(element)),
    }


def a_verifier_par_piece(contenu: dict[str, Any]) -> dict[str, int]:
    """Éléments douteux rattachés à chaque local : on prévient, on ne bloque pas la validation (Q5).

    Le rattachement d'un élément à une pièce n'existe que sur le tracé reprojeté ; c'est donc lui qu'on
    lit, et non le relevé, qui ignore les pièces.

    **Un élément donne plusieurs formes** — une paroi en couches en produit une par couche, d'où 289
    formes pour 227 éléments sur le R+1. Compter les formes annonçait 147 éléments douteux répartis sur
    les locaux, pour 92 dans le relevé. On dédoublonne donc sur la position de l'élément, la même clé
    que partout ailleurs ici, ce qui ramène le R+1 à 97.

    La somme par local reste **légèrement supérieure** au compteur du niveau, et c'est normal : un
    élément porté par un mur entre deux locaux est signalé dans les deux. Sur le R+1, 92 éléments
    douteux donnent 97 signalements, soit cinq éléments mitoyens. Ne pas « corriger » cet écart.
    """
    objets = contenu.get("enveloppe", {}).get("objets", []) or []
    vus: dict[str, set[tuple]] = {}
    for objet in objets:
        if not objet.get("review_required"):
            continue
        source = objet.get("source_parcours") or {}
        piece = source.get("piece")
        if piece:
            vus.setdefault(piece, set()).add(_cle(source))
    return {piece: len(refs) for piece, refs in vus.items()}
