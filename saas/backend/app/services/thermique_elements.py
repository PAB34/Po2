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

from app.services import thermique_ponts_catalogue as ponts_catalogue
from app.services.thermique import ThermiqueError

# Les liaisons du relevé : ce sont elles, les ponts thermiques, et elles seules portent un pont type.
TYPES_PONT = ("angle_sortant", "angle_rentrant", "about_refend")

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
    # Pont thermique : son pont type dans le catalogue NF EN ISO 14683, ou « a_modeliser » (D158).
    "reference_pont",
    # Angle réel d'un angle sortant ou rentrant, quand la mesure du tracé est fausse ou absente (D160).
    "angle_deg",
    "nu_exterieur_cm",
    "nu_interieur_cm",
    "nu_exterieur_fin_cm",
    "nu_interieur_fin_cm",
    # Menuiserie partagée avec d'autres pièces, désignées par leur nom (D217).
    "pieces_en_plus",
    # Modèle de menuiserie mesuré en coupe ou en élévation et posé par le thermicien (D220).
    "modele",
    # Composition copiée d'une paroi de référence (pinceau, D239).
    "couches",
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


def _couches(valeur: Any) -> list[dict[str, Any]]:
    """Une composition copiée (D239) : des couches de nature et d'épaisseur lisibles, gardées telles quelles."""
    if not isinstance(valeur, list) or not valeur:
        raise ThermiqueError("Une composition se donne par au moins une couche.")
    couches = []
    for couche in valeur:
        if not isinstance(couche, dict):
            raise ThermiqueError("Une couche de la composition est illisible.")
        epaisseur = couche.get("epaisseur_cm")
        if isinstance(epaisseur, bool) or not isinstance(epaisseur, (int, float)) or not 0 < epaisseur <= 200:
            raise ThermiqueError("L'épaisseur d'une couche se donne en centimètres, entre 0 et 200.")
        nature = str(couche.get("nature") or "").strip()
        if not nature:
            raise ThermiqueError("Chaque couche de la composition doit avoir une nature.")
        couches.append({**couche, "nature": nature, "epaisseur_cm": float(epaisseur)})
    return couches


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
        elif champ == "angle_deg":
            if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not 0 < valeur <= 180:
                raise ThermiqueError("L'angle se donne en degrés, entre 0 et 180 (90 pour un angle droit).")
            propres[champ] = float(valeur)
        elif champ == "couches":
            propres[champ] = _couches(valeur)
        elif champ == "modele":
            texte = str(valeur or "").strip()
            if len(texte) > 60:
                raise ThermiqueError("Le nom d'un modèle de menuiserie tient en 60 caractères.")
            propres[champ] = texte or None
        elif champ == "pieces_en_plus":
            if not isinstance(valeur, list) or not all(isinstance(nom, str) for nom in valeur):
                raise ThermiqueError("Les pièces à affecter se donnent par leur nom.")
            propres[champ] = sorted({nom.strip() for nom in valeur if nom.strip()})
        elif champ == "reference_pont":
            texte = str(valeur or "").strip()
            if not ponts_catalogue.reference_valide(texte):
                raise ThermiqueError(f"Pont type inconnu du catalogue NF EN ISO 14683 : « {texte} ».")
            propres[champ] = texte
        else:
            if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
                raise ThermiqueError(f"« {champ} » doit être un nombre de centimètres.")
            propres[champ] = float(valeur)

    futur = {**element, **propres}
    # Un pont type ne s'accroche qu'à un pont : un mur « C1 » ne voudrait rien dire au calcul.
    if futur.get("reference_pont") and futur.get("type") not in TYPES_PONT:
        raise ThermiqueError("Seul un pont thermique (angle ou about de refend) porte un pont type du catalogue.")
    if propres.get("pieces_en_plus") and futur.get("type") != "menuiserie":
        raise ThermiqueError("Seule une menuiserie s'affecte en plus à d'autres pièces.")
    if propres.get("modele") and futur.get("type") != "menuiserie":
        raise ThermiqueError("Seule une menuiserie reçoit un modèle de menuiserie.")
    if "angle_deg" in propres and futur.get("type") not in ("angle_sortant", "angle_rentrant"):
        raise ThermiqueError("Seul un angle sortant ou rentrant porte un angle.")
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


REUNION_ECART_M = 0.06  # D223 : deux morceaux à 6 cm au plus forment une seule menuiserie
TYPES_REUNIS = ("menuiserie", "paroi")  # D238 : et une seule paroi
NUS_FIN = ("nu_exterieur_fin_cm", "nu_interieur_fin_cm")


def _reunir(a: dict[str, Any], b: dict[str, Any]) -> None:
    """`b` rejoint `a` : bornes, nus de fin, corrections ; les morceaux d'origine restent notés (D223)."""
    morceaux = a.get("morceaux_reunis") or [reference(a)]
    a["morceaux_reunis"] = morceaux + (b.get("morceaux_reunis") or [reference(b)])
    a["fin_m"] = max(float(a["fin_m"]), float(b["fin_m"]))
    for champ in NUS_FIN:
        if b.get(champ) is not None:
            a[champ] = b[champ]
    a["confirme"] = bool(a.get("confirme")) and bool(b.get("confirme"))
    a["corrige"] = bool(a.get("corrige")) or bool(b.get("corrige"))
    a["a_verifier"] = bool(a.get("a_verifier")) or bool(b.get("a_verifier"))
    if b.get("modele") and not a.get("modele"):
        a["modele"] = b["modele"]
    partagees = sorted(set(a.get("pieces_en_plus") or []) | set(b.get("pieces_en_plus") or []))
    if partagees:
        a["pieces_en_plus"] = partagees
    if b.get("releve_origine"):
        a.setdefault("releve_origine_reunis", []).append(b["releve_origine"])


def reunir_menuiseries(releve_brut: dict[str, Any]) -> int:
    """Réunit dans le relevé les morceaux d'une même menuiserie (D223) ; renvoie le nombre de réunions.

    Sur un même tronçon : même composant, même modèle, écart de 6 cm au plus, rien entre eux qu'un élément
    « indéterminé » (absorbé, écarté avec un motif). Des composants différents ne se réunissent jamais d'office.
    """
    elements = releve_brut.get("elements")
    if not isinstance(elements, list):
        return 0
    reunions = 0
    change = True
    while change:
        change = False
        actifs = sorted(
            # Un pont (about de refend, angle) entre deux morceaux les sépare : il n'est pas ignoré.
            (e for e in elements if est_actif(e)),
            key=lambda e: (str(e.get("troncon")), float(e["debut_m"]), float(e["fin_m"])),
        )
        for rang, a in enumerate(actifs):
            # D238 : les parois se réunissent comme les menuiseries.
            if a.get("type") not in TYPES_REUNIS:
                continue
            entre = []
            for b in actifs[rang + 1:]:
                if b.get("troncon") != a.get("troncon") or float(b["debut_m"]) - float(a["fin_m"]) > REUNION_ECART_M:
                    break
                if b.get("type") == "indetermine":
                    entre.append(b)
                    continue
                if (
                    b.get("type") == a.get("type")
                    # D249, D250 : un mur dessiné ou retouché à la main garde la géométrie voulue (sommet, angle).
                    and not (a.get("geometrie_manuelle") or b.get("geometrie_manuelle"))
                    and (b.get("composant") or "") == (a.get("composant") or "")
                    and (b.get("modele") or None) == (a.get("modele") or None)
                ):
                    _reunir(a, b)
                    elements.remove(b)
                    for parasite in entre:
                        parasite["exclu"] = True
                        parasite["motif_exclusion"] = "absorbé par la réunion de deux morceaux d'une menuiserie (D223)"
                        parasite["a_verifier"] = False
                    reunions += 1
                    change = True
                break
            if change:
                break
    return reunions


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
