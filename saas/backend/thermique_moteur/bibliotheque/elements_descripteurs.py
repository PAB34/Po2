"""Descripteurs des tableaux de résistances R lus dans le texte des fascicules (B2b-D1).

Un descripteur dit où trouver le tableau (fascicule, page, numéro « Tableau N » juste au-dessus)
et comment lire sa grille : lignes d'en-tête, colonnes de clés, première colonne de valeurs.
Aucune valeur n'y est recopiée : elles sont lues dans la grille du PDF, et `attendu` (nombre de
valeurs du tableau) fait échouer la construction si une ligne se perd.
"""
from __future__ import annotations

LANGUETTE = "Épaisseur de la languette dL (mm)"
HAUTEUR = "Hauteur des entrevous de (mm)"
TALON = "Largeur du talon lo (mm)"
ENTRAXE_MM = "Entraxe des poutrelles le (mm)"
ENTRAXE_CM = "Entraxe des poutrelles E (cm)"
EPAISSEUR = "Épaisseur (cm)"
DIMENSIONS = "Dimensions (cm)"
RHO_CELLULAIRE = "Masse volumique nominale (kg/m³)"
INTERPOLATION_PSE = (
    "Hauteurs d'entrevous et épaisseurs de languette intermédiaires : interpolation linéaire admise par "
    "le document (§2)."
)


def _blocs(c: dict) -> str:
    return c[DIMENSIONS].replace(" x ", " × ")


def _bloc_plein_ou_perfore(c: dict) -> str:
    diametre, rangees = c["Diamètre maximal (cm)"], c["Rangées d'alvéoles"]
    if diametre in ("", "-", "–"):
        return f"{_blocs(c)}, plein"
    return f"{_blocs(c)}, perforé (Ø {diametre} cm, {rangees} rangée(s))"


def _libelle_entrevous(c: dict) -> str:
    parties = [f"languette {c[LANGUETTE]} mm"] if LANGUETTE in c else []
    return ", ".join(parties + [f"entrevous {c[HAUTEUR]} mm", f"talon {c[TALON]} mm"])


def _libelle_coupe(c: dict) -> str:
    libelle = f"{c['Coupe']}, entraxe {c[ENTRAXE_CM]} cm"
    dalle = c.get("Dalle de compression")
    if dalle:
        prefixe = "dalle en argile ou schiste expansé" if "argile" in dalle else "sans dalle ou dalle en granulats lourds"
        libelle = f"{libelle} ({prefixe})"
    return libelle


def _entrevous(numero: int, page: int, section: str, titre: str, attendu: int, *, languette: bool, rangees: bool, gauche: bool = False) -> dict:
    if languette and not gauche:
        cles, debut = {0: LANGUETTE, 1: HAUTEUR, 2: TALON}, 3
    else:
        cles, debut = {0: HAUTEUR, 1: TALON}, 2
    lignes_cles = [(HAUTEUR, "croissant"), (TALON, "decroissant")] + ([(LANGUETTE, "croissant")] if languette else [])
    return {
        "fascicule": "planchers",
        "numero": numero,
        "page": page,
        "section": section,
        "titre": f"Plancher à entrevous en polystyrène expansé : {titre}",
        "famille": "plancher_entrevous",
        "axe_lignes": "Entrevous et poutrelle",
        "axe_colonnes": ENTRAXE_MM + (" et rangées d'alvéoles" if rangees else ""),
        "entete": 3 if rangees else 2,
        "niveaux": [1, 2] if rangees else [1],
        "format_colonne": "{0} · {1}" if rangees else "{0}",
        "cles": cles,
        "debut": debut,
        "libelle": _libelle_entrevous,
        **({"colonne_gauche": LANGUETTE} if gauche else {}),
        "monotonie": {"colonnes": "croissant", "pas": 2 if rangees else 1, "lignes_cles": lignes_cles},
        "remarques": [INTERPOLATION_PSE],
        "attendu": attendu,
    }


DESCRIPTEURS: list[dict] = [
    # --- Murs : terre cuite -------------------------------------------------------------------
    {
        "fascicule": "murs", "numero": 2, "page": 3, "section": "1.1.1.3",
        "titre": "Briques perforées de terre cuite (format courant 6 × 10,5 × 22 cm)", "famille": "terre_cuite",
        "axe_lignes": "Appareillage (schéma p. 3)", "axe_colonnes": "Épaisseur E de l'élément (cm)",
        "entete": 2, "cles": {0: "Appareillage"}, "debut": 1,
        "noms_lignes": ["Appareillage 1", "Appareillage 2", "Appareillage 3", "Appareillage 4"],
        "monotonie": {"colonnes": "croissant"}, "attendu": 4,
    },
    {
        "fascicule": "murs", "numero": 3, "page": 4, "section": "1.1.2.1.1",
        "titre": "Briques à perforations verticales de faible épaisseur", "famille": "terre_cuite",
        "axe_lignes": "Brique (schéma p. 4)", "axe_colonnes": "Épaisseur E de l'élément (cm)",
        "entete": 2, "cles": {0: "Brique"}, "debut": 1,
        "noms_lignes": ["Brique de faible épaisseur (hauteur 15 à 25 cm, longueur 25 à 50 cm)"],
        "monotonie": {"colonnes": "croissant"}, "attendu": 3,
    },
    # --- Murs : blocs en béton ----------------------------------------------------------------
    {
        "fascicule": "murs", "numero": 7, "page": 8, "section": "1.2.1",
        "titre": "Blocs en béton de granulats courants destinés à rester apparents", "famille": "beton",
        "axe_lignes": "Bloc", "axe_colonnes": "Résistance thermique", "colonnes": ["R"],
        "entete": 1, "cles": {0: "Profil", 1: DIMENSIONS, 2: EPAISSEUR, 3: "Hauteur (cm)", 4: "Longueur (cm)"}, "debut": 5,
        "libelle": lambda c: f"{c['Profil']} {_blocs(c)}",
        "monotonie": {"epaisseur": EPAISSEUR, "groupes": ["Profil"]}, "attendu": 13,
    },
    {
        "fascicule": "murs", "numero": 9, "page": 10, "section": "1.2.3",
        "titre": "Blocs pleins et pleins perforés en béton de granulats courants (NF EN 771-3)", "famille": "beton",
        "axe_lignes": "Bloc", "axe_colonnes": "Résistance thermique", "colonnes": ["R"],
        "entete": 2,
        "cles": {3: DIMENSIONS, 4: EPAISSEUR, 5: "Hauteur (cm)", 6: "Longueur (cm)", 7: "Diamètre maximal (cm)", 8: "Rangées d'alvéoles"},
        "debut": 9,
        "cles_calculees": {"Type": lambda c: "plein" if c["Diamètre maximal (cm)"] in ("", "-", "–") else "perforé"},
        "libelle": _bloc_plein_ou_perfore,
        "monotonie": {"epaisseur": EPAISSEUR, "groupes": ["Type"]}, "attendu": 28,
    },
    {
        "fascicule": "murs", "numero": 10, "page": 11, "section": "1.2.4",
        "titre": "Blocs creux en béton de granulats légers (argile ou schiste expansé)", "famille": "beton",
        "axe_lignes": "Bloc", "axe_colonnes": "Résistance thermique", "colonnes": ["R"],
        "entete": 2, "cles": {1: DIMENSIONS, 2: EPAISSEUR, 3: "Hauteur (cm)", 4: "Longueur (cm)", 5: "Rangées d'alvéoles"}, "debut": 6,
        "diviser_selon": [1], "libelle": _blocs,
        "monotonie": {"epaisseur": EPAISSEUR, "groupes": ["Rangées d'alvéoles"]}, "attendu": 7,
    },
    {
        "fascicule": "murs", "numero": 11, "page": 11, "section": "1.2.5",
        "titre": "Blocs perforés en béton de granulats légers (argile ou schiste expansé)", "famille": "beton",
        "axe_lignes": "Bloc", "axe_colonnes": "Résistance thermique", "colonnes": ["R"],
        "entete": 2, "cles": {1: DIMENSIONS, 2: EPAISSEUR, 3: "Hauteur (cm)", 4: "Longueur (cm)"}, "debut": 5,
        "libelle": _blocs, "monotonie": {"epaisseur": EPAISSEUR}, "attendu": 4,
    },
    # --- Murs : béton cellulaire (R ; les U des tableaux 15 à 17 relèvent du lot B2b-2) -------
    *[
        {
            "fascicule": "murs", "numero": numero, "page": page, "section": "2.1",
            "titre": f"Béton cellulaire : {titre}", "famille": "beton_cellulaire",
            "axe_lignes": RHO_CELLULAIRE, "axe_colonnes": "Épaisseur des blocs (cm)",
            "entete": 2, "cles": {0: RHO_CELLULAIRE}, "debut": 1,
            "libelle": lambda c: f"{c[RHO_CELLULAIRE]} kg/m³",
            "monotonie": {"colonnes": "croissant", "lignes": "decroissant"},
            "remarques": [remarque], "attendu": attendu,
        }
        for numero, page, titre, remarque, attendu in (
            (12, 12, "blocs maçonnés", "Valeurs avant 2012 (bâtiments existants).", 90),
            (13, 12, "blocs « collés »", "Valeurs avant 2012 (bâtiments existants).", 90),
            (14, 13, "maçonnerie montée à joints minces ou collés", "Valeurs à partir de la RT 2012.", 80),
        )
    ],
    # --- Planchers bas : entrevous béton ou terre cuite ---------------------------------------
    {
        "fascicule": "planchers", "numero": 1, "page": 1, "section": "1.1.1",
        "titre": "Plancher à entrevous en terre cuite, sans dalle de compression ou avec dalle en béton de granulats lourds",
        "famille": "plancher_entrevous", "axe_lignes": "Coupe du plancher entre poutrelles (schéma p. 1)",
        "axe_colonnes": "Hauteur des entrevous (cm)",
        "entete": 2, "cles": {0: "Coupe", 2: ENTRAXE_CM}, "debut": 3,
        "noms_lignes": ["Coupe 1", "Coupe 2", "Coupe 3"], "libelle": _libelle_coupe,
        "variantes_calculees": {
            "dalle_argile_expansee": {
                "libelle": "Avec dalle de compression en béton d'argile ou de schiste expansé, ≥ 4 cm (§1.1.2 : + 0,03)",
                "ajout": 0.03,
                "verifier": "est égale à celle du tableau précédent, majorée de 0,03 m2.K/W",
                "page": 2,
            }
        },
        "monotonie": {"colonnes": "croissant", "lignes_cles": [(ENTRAXE_CM, "croissant")]}, "attendu": 18,
    },
    *[
        {
            "fascicule": "planchers", "numero": numero, "page": numero, "section": section,
            "titre": f"Plancher à entrevous en béton {titre}", "famille": "plancher_entrevous",
            "axe_lignes": "Coupe du plancher entre poutrelles (schéma p. 2)", "axe_colonnes": "Hauteur des entrevous (cm)",
            "entete": 2, "groupes": "Dalle de compression", "cles": {0: "Coupe", 1: ENTRAXE_CM}, "debut": 2,
            "noms_lignes": ["Coupe 1", "Coupe 1", "Coupe 2", "Coupe 2"] * 2, "libelle": _libelle_coupe,
            "monotonie": {"colonnes": "croissant", "lignes_cles": [(ENTRAXE_CM, "croissant")]}, "attendu": 36,
        }
        for numero, section, titre in (
            (2, "1.2.1", "de granulats courants (NF EN 15037-2)"),
            (3, "1.2.2", "d'argile expansé ou de schiste expansé"),
        )
    ],
    # --- Planchers bas : entrevous en polystyrène expansé -------------------------------------
    _entrevous(4, 6, "2.1.1.1", "découpés sans languette, type « dérogation couture »", 24, languette=False, rangees=False),
    _entrevous(5, 7, "2.1.1.2", "découpés sans languette, rectangulaires chanfreinés", 24, languette=False, rangees=False),
    _entrevous(6, 8, "2.1.2.1.1", "découpés à languette, fond plat, type « dérogation couture »", 96, languette=True, rangees=False),
    _entrevous(7, 9, "2.1.2.1.2", "découpés à languette, fond plat, rectangulaires chanfreinés", 96, languette=True, rangees=False),
    _entrevous(8, 10, "2.1.2.2.1", "découpés à languette, fond décaissé, type « dérogation couture »", 48, languette=True, rangees=False),
    _entrevous(9, 11, "2.1.2.2.2", "découpés à languette, fond décaissé, rectangulaires chanfreinés", 48, languette=True, rangees=False),
    _entrevous(10, 13, "2.2.1.1", "moulés sans languette, type « dérogation couture »", 12, languette=False, rangees=True),
    _entrevous(11, 14, "2.2.1.2", "moulés sans languette, rectangulaires chanfreinés", 12, languette=False, rangees=True),
    _entrevous(12, 15, "2.2.2.1.1", "moulés à languette, fond plat, type « dérogation couture »", 48, languette=True, rangees=True),
    _entrevous(13, 16, "2.2.2.1.2", "moulés à languette, fond plat, rectangulaires chanfreinés", 48, languette=True, rangees=True),
    _entrevous(14, 17, "2.2.2.2.1", "moulés à languette, fond décaissé, type « dérogation couture »", 24, languette=True, rangees=True, gauche=True),
    _entrevous(15, 18, "2.2.2.2.2", "moulés à languette, fond décaissé, rectangulaires chanfreinés", 24, languette=True, rangees=True),
    # --- Planchers bas : isolant projeté en sous-face -----------------------------------------
    {
        "fascicule": "planchers", "numero": 17, "page": 19, "section": "4.1.1",
        "titre": "Laines minérales projetées en sous-face (liant hydraulique, DTU 27.1)", "famille": "isolant_vrac",
        "axe_lignes": "Isolant et masse volumique en œuvre", "axe_colonnes": "Épaisseur moyenne de la projection (mm)",
        "entete": 2, "niveaux": [0, 1], "format_colonne": "{0} mesurés ({1} réels)",
        "cles": {0: "Isolant", 1: "Masse volumique en œuvre"}, "debut": 2, "isolant": True,
        "monotonie": {"colonnes": "croissant", "lignes_cles": [("Masse volumique en œuvre", "decroissant")]}, "attendu": 20,
    },
    # --- Toitures : isolants en vrac sur plancher de combles perdus ---------------------------
    *[
        {
            "fascicule": "toitures", "numero": numero, "page": 1, "section": section,
            "titre": f"Isolant en vrac {titre} sur plancher plat de combles perdus", "famille": "isolant_vrac",
            "axe_lignes": "Isolant", "axe_colonnes": "Épaisseur minimale de la couche déposée (cm)",
            "entete": 1, "cles": {0: "Isolant"}, "debut": 1, "isolant": True,
            "monotonie": {"colonnes": "croissant"}, "attendu": attendu,
        }
        for numero, section, titre, attendu in ((1, "1.1.1.3.1", "soufflé à la machine", 30), (2, "1.1.1.3.2", "déversé manuellement", 24))
    ],
    # --- Cloisons -----------------------------------------------------------------------------
    *[
        {
            "fascicule": "cloisons", "numero": numero, "page": 1, "section": section, "titre": titre, "famille": "cloison",
            "axe_lignes": "Élément", "axe_colonnes": "Épaisseur (cm)",
            "entete": 1, "cles": {0: "Élément"}, "debut": 1,
            **({"noms_lignes": [nom]} if nom else {}),
            "monotonie": {"colonnes": "croissant"}, "attendu": attendu,
        }
        for numero, section, titre, nom, attendu in (
            (1, "1.1", "Carreaux pleins de plâtre à enduire", None, 4),
            (2, "1.2", "Plaques de plâtre à parements de carton", "Plaque de plâtre (masse volumique 800 à 900 kg/m³)", 2),
            (3, "1.3", "Carreaux de plâtre pleins à parements lisses", "Carreau plein (masse volumique 900 à 1 000 kg/m³)", 4),
            (4, "1.4", "Carreaux et grands éléments de plâtre alvéolés", "Carreau alvéolé (900 à 1 000 kg/m³, 20 à 35 % de vides)", 2),
        )
    ],
    {
        "fascicule": "cloisons", "numero": 6, "page": 2, "section": "2",
        "titre": "Panneaux fibragglo (fibres de bois et liant hydraulique, NF B 56-010)", "famille": "cloison",
        "axe_lignes": "Masse volumique et épaisseur", "axe_colonnes": "Résistance thermique", "colonnes": ["R"],
        "transposer": True, "entete": 1, "cles": {0: "Masse volumique (kg/m³)", 1: EPAISSEUR}, "debut": 2,
        "libelle": lambda c: f"Panneau de {c[EPAISSEUR]} cm ({c['Masse volumique (kg/m³)']} kg/m³)",
        "corrections": [
            (EPAISSEUR, "20,5", "2,5", "épaisseur imprimée « 20,5 » entre 2,0 et 3,0 cm : lue 2,5 (R / e cohérent avec les panneaux voisins)")
        ],
        "remarques": [
            "Si la masse volumique ne correspond pas à l'épaisseur, calculer R à partir de la conductivité du "
            "fascicule Matériaux pour la masse volumique considérée."
        ],
        "monotonie": {"epaisseur": EPAISSEUR}, "attendu": 9,
    },
]
