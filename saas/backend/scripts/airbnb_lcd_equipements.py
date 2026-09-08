#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lexique des équipements Airbnb → colonnes exploitables.

Trois choix qui évitent des contresens mesurés sur les libellés réels :

1. **Trois états, pas deux.** Airbnb distingue un équipement présent, un
   équipement explicitement absent (`available: false`, groupe « Non inclus »)
   et un équipement dont il ne dit rien. Écraser « absent » et « inconnu » sur
   un même `False` fausserait tout ciblage : on rend True / False / None.

2. **Motifs, pas égalité de chaîne.** Les libellés varient beaucoup
   (« Climatiseur portable », « Climatisation centralisée », « AC - split »).

3. **Des distinctions que le vocabulaire Airbnb noie.** « Stationnement gratuit
   dans la rue » n'est pas une place de parking privative ; un ventilateur n'est
   pas une climatisation ; un sèche-cheveux n'est pas un sèche-linge. Ces trois
   confusions sont faciles à commettre avec une recherche naïve de sous-chaîne.
"""

from __future__ import annotations

import re
import unicodedata

# Chaque catégorie : (motifs positifs, motifs d'exclusion)
# Les motifs sont appliqués sur le libellé sans accent et en minuscules.
LEXIQUE: dict[str, tuple[list[str], list[str]]] = {
    "clim": (
        [r"\bclimatis", r"\bclimatiseur", r"\bair conditionn", r"\bac\b.*split",
         r"\bsplit\b", r"pompe a chaleur.*(froid|reversible)"],
        # un ventilateur n'est pas une climatisation
        [r"ventilateur"],
    ),
    "piscine": (
        [r"\bpiscine"],
        # une piscine du voisinage ou payante n'est pas la piscine du logement ;
        # elle est conservée à part dans "piscine_partagee"
        [r"piscine.*(partage|commun|voisinage|payant)"],
    ),
    "piscine_partagee": (
        [r"piscine.*(partage|commun|voisinage)"],
        [],
    ),
    "jacuzzi": (
        [r"\bjacuzzi", r"bain a remous", r"\bhot tub", r"\bspa\b"],
        [r"spa.*(a proximite|payant)"],
    ),
    "sauna": ([r"\bsauna", r"hammam"], []),
    "chauffage": (
        [r"\bchauffage", r"\bradiateur", r"\bchaudiere", r"\bpoele\b",
         r"\bcheminee"],
        [],
    ),
    "chauffage_appoint_seul": ([r"chauffage d.appoint"], []),
    "parking": (
        # place effectivement rattachée au logement
        [r"parking.*(gratuit|payant).*(sur place|sur la propriete)",
         r"\bgarage\b", r"place de parking", r"parking sur place",
         r"stationnement.*(sur place|prive|garage)"],
        [r"dans la rue", r"\bpublic\b"],
    ),
    "parking_rue": (
        [r"stationnement.*dans la rue", r"parking.*dans la rue"],
        [],
    ),
    "borne_recharge": (
        [r"borne de recharge", r"recharge.*vehicule electrique",
         r"\bev charger", r"chargeur.*electrique"],
        [],
    ),
    "wifi": ([r"\bwifi\b", r"\bwi-fi\b", r"internet"], []),
    "ascenseur": ([r"\bascenseur\b"], []),
    "lave_linge": (
        [r"lave-linge", r"machine a laver", r"\blave linge"],
        [r"lave-vaisselle"],
    ),
    "seche_linge": (
        [r"seche-linge", r"\bseche linge", r"\bsechoir\b"],
        # le sèche-cheveux et l'étendoir ne sont pas un sèche-linge
        [r"seche-cheveux", r"etendoir"],
    ),
    "lave_vaisselle": ([r"lave-vaisselle"], []),
    "cuisine": ([r"\bcuisine\b"], [r"cuisine.*(partage|commun)"]),
    "tv": ([r"\btv\b", r"televis"], []),
    "vue_mer": ([r"vue sur la mer", r"vue sur l.ocean", r"vue sur le port",
                 r"vue sur l.etang", r"front de mer"], []),
    "acces_plage": ([r"acces.*plage", r"plage.*(a proximite|accessible)",
                     r"bord de mer"], []),
    "terrasse_balcon": ([r"\bbalcon\b", r"\bterrasse\b", r"\bpatio\b",
                         r"solarium"], []),
    "jardin": ([r"\bjardin\b", r"cour\b", r"arriere-cour"], []),
    "barbecue": ([r"barbecue", r"\bplancha\b"], []),
    "animaux_acceptes": ([r"animaux.*(accept|admis|bienvenu)"], []),
    "acces_handicape": ([r"accessible.*(fauteuil|mobilite)",
                         r"plain-pied", r"sans marche"], []),
    "arrivee_autonome": ([r"arrivee autonome", r"boite a cles",
                          r"serrure connectee", r"self check"], []),
}

# Colonnes explicitement demandées au cahier des charges, dans l'ordre.
COLONNES_PRIORITAIRES = [
    "clim", "piscine", "jacuzzi", "chauffage", "parking", "borne_recharge",
    "wifi", "ascenseur", "lave_linge", "seche_linge",
]


def _normaliser(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


_COMPILE = {
    cat: ([re.compile(p) for p in pos], [re.compile(x) for x in exc])
    for cat, (pos, exc) in LEXIQUE.items()
}


def _correspond(libelle_norm: str, cat: str) -> bool:
    positifs, exclusions = _COMPILE[cat]
    if any(rx.search(libelle_norm) for rx in exclusions):
        return False
    return any(rx.search(libelle_norm) for rx in positifs)


def lister_equipements(fiche: dict) -> list[dict]:
    """
    Aplatit `amenities` en une liste de lignes exploitables.

    Rend : groupe, libellé, sous-titre, disponible (bool), icône.
    """
    lignes = []
    for groupe in fiche.get("amenities") or []:
        titre_groupe = groupe.get("title") or ""
        non_inclus = _normaliser(titre_groupe).startswith("non inclus")
        for val in groupe.get("values") or []:
            libelle = val.get("title") or ""
            if not libelle:
                continue
            dispo = val.get("available")
            if dispo is None:
                dispo = not non_inclus
            lignes.append({
                "groupe": titre_groupe,
                "libelle": libelle,
                "sous_titre": val.get("subtitle") or "",
                "disponible": bool(dispo) and not non_inclus,
                "icone": val.get("icon") or "",
            })
    return lignes


def drapeaux(fiche: dict) -> dict[str, bool | None]:
    """
    Colonnes booléennes à trois états par catégorie du lexique.

    True  : équipement présent
    False : équipement explicitement signalé absent par Airbnb
    None  : Airbnb n'en dit rien (à ne surtout pas confondre avec False)
    """
    lignes = lister_equipements(fiche)
    resultat: dict[str, bool | None] = {cat: None for cat in LEXIQUE}

    for ligne in lignes:
        libelle_norm = _normaliser(f"{ligne['libelle']} {ligne['sous_titre']}")
        for cat in LEXIQUE:
            if not _correspond(libelle_norm, cat):
                continue
            if ligne["disponible"]:
                resultat[cat] = True           # une présence l'emporte
            elif resultat[cat] is None:
                resultat[cat] = False          # absence explicite
    return resultat


def libelles_non_classes(fiche: dict) -> list[str]:
    """
    Équipements présents qu'aucune catégorie ne capte.

    Sert à faire vivre le lexique : ce qui revient souvent ici mérite une
    catégorie. On ne devine pas le lexique une fois pour toutes, on le corrige
    sur les libellés réellement rencontrés.
    """
    orphelins = []
    for ligne in lister_equipements(fiche):
        if not ligne["disponible"]:
            continue
        norm = _normaliser(f"{ligne['libelle']} {ligne['sous_titre']}")
        if not any(_correspond(norm, cat) for cat in LEXIQUE):
            orphelins.append(ligne["libelle"])
    return orphelins


if __name__ == "__main__":
    # Autotest : les confusions que le lexique doit éviter.
    cas = [
        ("Sèche-cheveux", "seche_linge", False),
        ("Sèche-linge", "seche_linge", True),
        ("Étendoir à linge", "seche_linge", False),
        ("Lave-vaisselle", "lave_linge", False),
        ("Lave-linge (Gratuit) dans le logement", "lave_linge", True),
        ("Ventilateurs portables", "clim", False),
        ("Climatiseur portable", "clim", True),
        ("Stationnement gratuit dans la rue", "parking", False),
        ("Stationnement gratuit dans la rue", "parking_rue", True),
        ("Parking gratuit sur place", "parking", True),
        ("Wifi", "wifi", True),
    ]
    echecs = 0
    for libelle, cat, attendu in cas:
        obtenu = _correspond(_normaliser(libelle), cat)
        etat = "ok " if obtenu == attendu else "ÉCHEC"
        if obtenu != attendu:
            echecs += 1
        print(f"  [{etat}] {libelle!r:45} {cat:16} -> {obtenu} (attendu {attendu})")
    print(f"\n{len(cas) - echecs}/{len(cas)} cas passés")
    raise SystemExit(1 if echecs else 0)
