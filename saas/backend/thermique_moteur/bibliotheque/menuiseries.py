"""Bibliothèque des menuiseries (lot B1).

Extraction automatique des valeurs tabulées des règles Th-Bât (RE2020), applications du
fascicule « parois vitrées », puis contrôles automatiques (décision utilisateur : validation
automatique seulement). Chaque valeur garde sa page d'origine.

Règles d'usage reprises des documents :
- fenêtres et portes-fenêtres : valeurs par défaut, ni interpolées ni extrapolées ; les
  facteurs S et TL se multiplient par les correctifs d'intégration CS et CTL ;
- Ujour-nuit et Uws : valeurs intermédiaires par interpolation.
"""
from __future__ import annotations

import json
import re
import unicodedata
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path
from typing import Any

DONNEES_DIR = Path(__file__).resolve().parent.parent / "donnees"

VITRAGES = ("triple", "double", "double_controle_solaire")

# Cas de protection solaire des tableaux §2.1 à §2.7. Les lettres grecques des intitulés
# (τ, α) sont perdues à l'extraction : les libellés sont donc fixés ici, et un contrôle
# vérifie qu'ils concordent avec les mots de l'intitulé du document.
PROTECTIONS: dict[str, dict[str, Any]] = {
    "2.1": {"code": "sans", "libelle": "Sans protection solaire", "opaque": None, "teinte": None, "position": None},
    "2.2": {"code": "opaque_claire_exterieur", "libelle": "Protection opaque et claire, à l'extérieur", "opaque": True, "teinte": "claire", "position": "exterieur"},
    "2.3": {"code": "opaque_sombre_exterieur", "libelle": "Protection opaque et sombre, à l'extérieur", "opaque": True, "teinte": "sombre", "position": "exterieur"},
    "2.4": {"code": "non_opaque_claire_exterieur", "libelle": "Protection non opaque et claire, à l'extérieur", "opaque": False, "teinte": "claire", "position": "exterieur"},
    "2.5": {"code": "non_opaque_sombre_exterieur", "libelle": "Protection non opaque et sombre, à l'extérieur", "opaque": False, "teinte": "sombre", "position": "exterieur"},
    "2.6": {"code": "non_opaque_claire_interieur", "libelle": "Protection non opaque et claire, à l'intérieur", "opaque": False, "teinte": "claire", "position": "interieur"},
    "2.7": {"code": "non_opaque_sombre_interieur", "libelle": "Protection non opaque et sombre, à l'intérieur", "opaque": False, "teinte": "sombre", "position": "interieur"},
}

CORRECTIFS: dict[str, tuple[str, str]] = {
    "3.1": ("cs_ete", "Correctif CS des facteurs solaires, conditions d'été (E)"),
    "3.2": ("cs_conso_non_climatise", "Correctif CS, conditions de consommation, bâtiment non climatisé"),
    "3.3": ("cs_conso_climatise", "Correctif CS, conditions de consommation, bâtiment climatisé"),
    "3.4": ("ctl", "Correctif CTL de la transmission lumineuse, toutes conditions"),
}
ORIENTATIONS = ("sud", "nord", "est_ouest")
POSITIONS = ("nu_interieur", "nu_exterieur")
EPAISSEURS_CM = (20, 50)
COLONNES_CORRECTIFS = [
    {"orientation": o, "position": p, "epaisseur_cm": e} for o in ORIENTATIONS for p in POSITIONS for e in EPAISSEURS_CM
]
LIGNES_CORRECTIFS = (
    ("fenetre un vantail", "fenetre", 1),
    ("fenetre deux vantaux", "fenetre", 2),
    ("porte fenetre un vantail", "porte_fenetre", 1),
    ("porte fenetre deux vantaux", "porte_fenetre", 2),
)

# Ordre du tableau 1 du document « Coefficient Ud des portes courantes ».
PORTES = (
    ("bois_opaque_pleine", "Porte simple en bois", "Opaque, pleine"),
    ("bois_opaque_montants_45", "Porte simple en bois", "Opaque, pleine avec montants de 45 mm"),
    ("bois_vitrage_simple_moins_30", "Porte simple en bois", "Vitrage simple, moins de 30 % de vitrage"),
    ("bois_vitrage_simple_30_60", "Porte simple en bois", "Vitrage simple, 30 à 60 % de vitrage"),
    ("bois_vitrage_double", "Porte simple en bois", "Vitrage double à lame d'air de 6 mm, toute proportion"),
    ("metal_opaque", "Porte simple en métal", "Opaque"),
    ("metal_vitrage_simple", "Porte simple en métal", "Vitrage simple, toute proportion"),
    ("metal_vitrage_double_moins_30", "Porte simple en métal", "Vitrage double, moins de 30 % de vitrage"),
    ("metal_vitrage_double_30_60", "Porte simple en métal", "Vitrage double, 30 à 60 % de vitrage"),
    ("verre_sans_menuiserie", "Porte en verre sans menuiserie", "Vitrage simple"),
    ("element_souple_battant", "Élément souple battant", "Toutes"),
)

# Ordre du tableau 1 du document « Résistance additionnelle de protection mobile ».
FERMETURES = (
    ("ajours_lames_orientables", "Jalousie accordéon, lames orientables (dont vénitiens extérieurs tout métal), volets battants ou persiennes à ajours fixes"),
    ("sans_ajours_volet_roulant_alu", "Fermeture sans ajours en position déployée, volet roulant aluminium"),
    ("volet_roulant_pvc_mince", "Volet roulant PVC, tablier de 12 mm ou moins"),
    ("persienne_volet_pvc_bois_mince", "Persienne coulissante ou volet battant PVC, volet battant bois, tablier de 22 mm ou moins"),
    ("persienne_pvc_volet_bois_epais", "Persienne coulissante PVC et volet battant bois, tablier de plus de 22 mm"),
    ("volet_roulant_pvc_epais", "Volet roulant PVC, tablier de plus de 12 mm"),
)

REGLES_USAGE = {
    "fenetres": (
        "Valeurs par défaut, à retenir en l'absence de données précises sur les baies ; elles ne "
        "s'interpolent ni ne s'extrapolent. Les facteurs S et TL se multiplient par les correctifs "
        "d'intégration CS et CTL."
    ),
    "ujn_uws": "Les valeurs intermédiaires s'obtiennent par interpolation.",
}

Pages = list[tuple[int, str]]
DECIMAL = re.compile(r"\d+[.,]\d+")


def _normaliser(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte)
    sans_accent = "".join(c for c in decompose if not unicodedata.combining(c)).lower()
    sans_accent = sans_accent.replace("-", " ").replace("’", "'")
    return " ".join(sans_accent.split())


def _decimaux(texte: str) -> list[float]:
    return [float(m.replace(",", ".")) for m in DECIMAL.findall(texte)]


def _lignes(pages: Pages):
    for page, texte in pages:
        for brut in texte.splitlines():
            ligne = " ".join(brut.split())
            if ligne:
                yield page, ligne


# --- Extraction ---------------------------------------------------------------------


def _entete_tableau(texte: str, code: str, page: int, anomalies: list[str]) -> dict[str, Any]:
    norm = _normaliser(texte)
    menuiserie = "porte_fenetre" if "porte fenetre" in norm else "fenetre"
    vantaux = 2 if "deux vantaux" in norm else 1 if "un vantail" in norm else None
    trouve = re.search(r"σ\s*=\s*(\d+[.,]\d+)", texte) or re.search(r"=\s*(\d+[.,]\d+)\s*:?\s*$", texte)
    sigma = float(trouve.group(1).replace(",", ".")) if trouve else None
    if vantaux is None or sigma is None:
        anomalies.append(f"§{code} p. {page} : intitulé de tableau non reconnu « {texte} »")
    return {"code": code, "menuiserie": menuiserie, "vantaux": vantaux, "sigma": sigma}


def extraire_fenetres(pages: Pages) -> tuple[list[dict], list[dict], list[str]]:
    """Tableaux §2.1 à §2.7 : une ligne par (protection, menuiserie, σ, vitrage)."""
    lignes: list[dict] = []
    protections: dict[str, dict[str, Any]] = {}
    anomalies: list[str] = []
    section: str | None = None
    tableau: dict[str, Any] | None = None
    for page, ligne in _lignes(pages):
        sous_tableau = re.match(r"^2\.([1-7])\.(\d+)\s+(.*)$", ligne)
        nouvelle_section = re.match(r"^2\.([1-7])\s+(.*)$", ligne)
        if sous_tableau:
            section = f"2.{sous_tableau.group(1)}"
            tableau = _entete_tableau(sous_tableau.group(3), f"{section}.{sous_tableau.group(2)}", page, anomalies)
            continue
        if nouvelle_section:
            section = nouvelle_section and f"2.{nouvelle_section.group(1)}"
            protections[section] = {"page": page, "intitule": ligne}
            tableau = None
            continue
        if re.match(r"^3(\.\d)?\s", ligne):
            section, tableau = None, None
            continue
        if section and tableau is None and section in protections and len(protections[section]["intitule"]) < 220:
            protections[section]["intitule"] += " " + ligne  # suite de l'intitulé (« située à l'extérieur »)
            continue
        if tableau is None or section is None:
            continue
        norm = _normaliser(ligne)
        jetons = re.findall(r"\d+(?:[.,]\d+)?", ligne)
        decimaux = [j for j in jetons if re.fullmatch(r"\d+[.,]\d+", j)]
        if norm.startswith("triple"):
            vitrage = "triple"
        elif "controle solaire" in norm or (norm.startswith("double avec") and len(jetons) == 9):
            vitrage = "double_controle_solaire"
        elif norm.startswith("double avec"):
            continue  # valeurs sur la ligne suivante (« contrôle solaire … »)
        elif norm.startswith("double"):
            vitrage = "double"
        else:
            continue
        correction = None
        if len(jetons) == 9 and len(decimaux) == 8 and re.fullmatch(r"\d{2}", jetons[0]) and 5 <= int(jetons[0]) <= 65:
            # Virgule absente dans le document pour U (« 18 » imprimé au §2.5.3 pour 1,8, lu à
            # l'identique par deux extracteurs) : corrigé et signalé, jamais en silence.
            valeur_u = int(jetons[0]) / 10
            correction = f"le document imprime « {jetons[0]} » sans virgule ; valeur retenue {valeur_u:.1f}".replace(".", ",")
            valeurs = [valeur_u] + [float(j.replace(",", ".")) for j in decimaux]
        else:
            valeurs = [float(j.replace(",", ".")) for j in decimaux]
        if len(valeurs) != 9:
            anomalies.append(f"§{tableau['code']} p. {page} : ligne {vitrage} avec {len(valeurs)} valeurs au lieu de 9")
            continue
        ligne_fenetre = {
            "id": f"{tableau['code']}-{vitrage}",
            "section": tableau["code"],
            "protection": PROTECTIONS[section]["code"],
            "menuiserie": tableau["menuiserie"],
            "vantaux": tableau["vantaux"],
            "sigma": tableau["sigma"],
            "vitrage": vitrage,
            "avec_protection": section != "2.1",
            "u": valeurs[0],
            "s_c": valeurs[1:4],
            "s_e": valeurs[4:7],
            "tl": valeurs[7],
            "tl_dif": valeurs[8],
            "page": page,
            "statut": "valide",
        }
        if correction:
            ligne_fenetre["correction"] = correction
        lignes.append(ligne_fenetre)
    liste_protections = []
    for code, infos in PROTECTIONS.items():
        trouve = protections.get(code, {})
        intitule = trouve.get("intitule", "")
        facteurs = [float(x.replace(",", ".")) for x in re.findall(r"=\s*(\d+(?:[.,]\d+)?)", intitule)]
        liste_protections.append({"section": code, **infos, "intitule_document": intitule, "facteurs": facteurs, "page": trouve.get("page")})
    return lignes, liste_protections, anomalies


def extraire_correctifs(pages: Pages) -> tuple[list[dict], list[str]]:
    """Tableaux §3.1 à §3.4 : 4 menuiseries × 12 colonnes (orientation × position × épaisseur)."""
    tables: dict[str, dict[str, Any]] = {}
    anomalies: list[str] = []
    courant: dict[str, Any] | None = None
    for page, ligne in _lignes(pages):
        entete = re.match(r"^(3\.[1-4])\s", ligne)
        if entete:
            code, libelle = CORRECTIFS[entete.group(1)]
            courant = {"section": entete.group(1), "code": code, "libelle": libelle, "colonnes": COLONNES_CORRECTIFS, "lignes": [], "page": page}
            tables[entete.group(1)] = courant
            continue
        if courant is None:
            continue
        norm = _normaliser(ligne)
        for prefixe, menuiserie, vantaux in LIGNES_CORRECTIFS:
            if norm.startswith(prefixe):
                valeurs = _decimaux(ligne)
                if len(valeurs) != len(COLONNES_CORRECTIFS):
                    anomalies.append(f"§{courant['section']} p. {page} : ligne « {prefixe} » avec {len(valeurs)} valeurs au lieu de 12")
                else:
                    courant["lignes"].append({"menuiserie": menuiserie, "vantaux": vantaux, "valeurs": valeurs, "page": page})
                break
    return [tables[k] for k in sorted(tables)], anomalies


def _valeurs_apres(pages: Pages, repere: str, motif: str) -> tuple[list[float], int]:
    texte = "\n".join(t for _, t in pages)
    position = _normaliser(texte).find(_normaliser(repere))
    # Le repère est cherché dans le texte normalisé ; on découpe le texte d'origine à la même
    # longueur de ligne près en repartant du repère brut quand il est présent tel quel.
    debut = texte.find(repere) if repere in texte else max(position, 0)
    valeurs = [float(m.replace(",", ".")) for m in re.findall(motif, texte[debut:])]
    return valeurs, pages[0][0] if pages else 1


def extraire_portes(pages: Pages) -> tuple[list[dict], list[str]]:
    valeurs, page = _valeurs_apres(pages, "Coefficient Ud", r"(?<![\d,.])\d,\d(?![\d,.])")
    anomalies = []
    if len(valeurs) != len(PORTES):
        anomalies.append(f"Portes : {len(valeurs)} valeurs Ud lues au lieu de {len(PORTES)}")
    portes = [
        {"id": ident, "nature": nature, "type": genre, "ud": valeur, "page": page, "statut": "valide"}
        for (ident, nature, genre), valeur in zip(PORTES, valeurs)
    ]
    return portes, anomalies


def extraire_fermetures(pages: Pages) -> tuple[list[dict], list[str]]:
    valeurs, page = _valeurs_apres(pages, "Tableau 1", r"(?<![\d,.])0,\d\d(?![\d,.])")
    anomalies = []
    if len(valeurs) != len(FERMETURES):
        anomalies.append(f"Fermetures : {len(valeurs)} résistances lues au lieu de {len(FERMETURES)}")
    fermetures = [
        {"id": ident, "libelle": libelle, "r": valeur, "page": page, "statut": "valide"}
        for (ident, libelle), valeur in zip(FERMETURES, valeurs)
    ]
    return fermetures, anomalies


def extraire_table_fermeture(pages: Pages, nom: str) -> tuple[dict[str, Any], list[str]]:
    """Tableaux Ujour-nuit et Uws : lignes Uw de la paroi nue, colonnes R de la fermeture."""
    anomalies: list[str] = []
    resistances: list[float] = []
    lignes: list[dict[str, Any]] = []
    for page, ligne in _lignes(pages):
        valeurs = _decimaux(ligne)
        if not resistances and len(valeurs) == 4 and all(v < 1 for v in valeurs):
            resistances = valeurs
            continue
        if resistances and len(valeurs) == len(resistances) + 1 and valeurs[0] >= 1:
            lignes.append({"uw": valeurs[0], "valeurs": valeurs[1:], "page": page})
    if not resistances or not lignes:
        anomalies.append(f"{nom} : tableau non reconnu")
    return {"r": resistances, "lignes": lignes}, anomalies


# --- Contrôles automatiques ---------------------------------------------------------------


def _marquer(element: dict, niveau: str) -> None:
    if niveau == "erreur" or element.get("statut") == "valide":
        element["statut"] = niveau


def controler(edition: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Erreurs (valeur exclue des calculs) et alertes (valeur utilisable, à surveiller)."""
    erreurs: list[str] = []
    alertes: list[str] = []
    fenetres = edition["fenetres"]

    # Structure : chaque tableau a ses trois vitrages, chaque cas de protection les mêmes menuiseries.
    par_tableau: dict[str, dict[str, dict]] = {}
    for ligne in fenetres:
        par_tableau.setdefault(ligne["section"], {})[ligne["vitrage"]] = ligne
    for code, lignes in sorted(par_tableau.items()):
        manquants = [v for v in VITRAGES if v not in lignes]
        if manquants:
            erreurs.append(f"Fenêtres §{code} : vitrage(s) manquant(s) {', '.join(manquants)}")
    configurations: dict[str, set] = {}
    for ligne in fenetres:
        configurations.setdefault(ligne["protection"], set()).add((ligne["menuiserie"], ligne["vantaux"], ligne["sigma"]))
    reference = configurations.get("sans", set())
    for protection in edition["protections"]:
        trouvees = configurations.get(protection["code"], set())
        if not trouvees:
            erreurs.append(f"Fenêtres : aucun tableau pour « {protection['libelle']} » (§{protection['section']})")
        elif trouvees != reference:
            erreurs.append(f"Fenêtres §{protection['section']} : menuiseries différentes de celles du §2.1")
        intitule = _normaliser(protection["intitule_document"])
        attendus = []
        if protection["opaque"] is not None:
            attendus.append("non opaque" if not protection["opaque"] else "opaque")
            attendus += [protection["teinte"], protection["position"]]
        elif intitule and "sans protection" not in intitule:
            alertes.append(f"§{protection['section']} : intitulé inattendu « {protection['intitule_document']} »")
        for mot in attendus:
            if mot not in intitule or (mot == "opaque" and "non opaque" in intitule):
                erreurs.append(f"§{protection['section']} : l'intitulé du document ne correspond pas à « {protection['libelle']} »")
                break

    # Plages de valeurs (et valeurs corrigées à l'extraction, toujours signalées).
    for ligne in fenetres:
        source = f"Fenêtres §{ligne['section']} {ligne['vitrage']} (p. {ligne['page']})"
        if ligne.get("correction"):
            alertes.append(f"{source} : {ligne['correction']}")
            _marquer(ligne, "alerte")
        if not 0.5 <= ligne["u"] <= 6.5:
            erreurs.append(f"{source} : U = {ligne['u']} hors de la plage 0,5 à 6,5")
            _marquer(ligne, "erreur")
        facteurs = ligne["s_c"] + ligne["s_e"] + [ligne["tl"], ligne["tl_dif"]]
        if any(not 0 <= v <= 1 for v in facteurs) or sum(ligne["s_c"]) > 1 or sum(ligne["s_e"]) > 1:
            erreurs.append(f"{source} : facteur solaire ou lumineux hors de 0 à 1")
            _marquer(ligne, "erreur")
        if ligne["tl_dif"] > ligne["tl"]:
            erreurs.append(f"{source} : TL diffus supérieur à TL")
            _marquer(ligne, "erreur")

    # Cohérence physique.
    for code, lignes in par_tableau.items():
        triple, double, controle = lignes.get("triple"), lignes.get("double"), lignes.get("double_controle_solaire")
        if triple and double and triple["u"] > double["u"]:
            alertes.append(f"Fenêtres §{code} : U du triple vitrage supérieur à celui du double")
            _marquer(triple, "alerte")
        if controle and double and controle["s_c"][0] > double["s_c"][0]:
            alertes.append(f"Fenêtres §{code} : facteur solaire du vitrage à contrôle solaire supérieur au double courant")
            _marquer(controle, "alerte")
    sans_protection = {(l["menuiserie"], l["vantaux"], l["sigma"], l["vitrage"]): l for l in fenetres if l["protection"] == "sans"}
    for ligne in fenetres:
        base = sans_protection.get((ligne["menuiserie"], ligne["vantaux"], ligne["sigma"], ligne["vitrage"]))
        if ligne["avec_protection"] and base:
            if ligne["u"] > base["u"]:
                alertes.append(f"Fenêtres §{ligne['section']} {ligne['vitrage']} : Uws supérieur au Uw sans protection")
                _marquer(ligne, "alerte")
            if sum(ligne["s_c"]) > sum(base["s_c"]) + 1e-9:
                alertes.append(f"Fenêtres §{ligne['section']} {ligne['vitrage']} : Sws supérieur au Sw sans protection")
                _marquer(ligne, "alerte")

    # Correctifs d'intégration.
    if len(edition["correctifs"]) != len(CORRECTIFS):
        erreurs.append(f"Correctifs : {len(edition['correctifs'])} tableaux au lieu de {len(CORRECTIFS)}")
    for table in edition["correctifs"]:
        if len(table["lignes"]) != len(LIGNES_CORRECTIFS):
            erreurs.append(f"Correctifs §{table['section']} : {len(table['lignes'])} lignes au lieu de 4")
        for ligne in table["lignes"]:
            if any(not 0 < v <= 1 for v in ligne["valeurs"]):
                erreurs.append(f"Correctifs §{table['section']} : coefficient hors de 0 à 1 (p. {ligne['page']})")
            for i in range(0, len(ligne["valeurs"]), 2):  # paroi de 50 cm : au plus autant de lumière qu'à 20 cm
                if ligne["valeurs"][i + 1] > ligne["valeurs"][i]:
                    alertes.append(f"Correctifs §{table['section']} {ligne['menuiserie']} : valeur à 50 cm supérieure à celle à 20 cm")
                    break

    for porte in edition["portes"]:
        if not 1 <= porte["ud"] <= 7:
            erreurs.append(f"Portes « {porte['type']} » : Ud = {porte['ud']} hors de 1 à 7")
            _marquer(porte, "erreur")
    for fermeture in edition["fermetures"]:
        if not 0.01 <= fermeture["r"] <= 0.5:
            erreurs.append(f"Fermetures « {fermeture['libelle']} » : R = {fermeture['r']} hors de 0,01 à 0,5")
            _marquer(fermeture, "erreur")

    for nom, table in (("Ujour-nuit", edition["ujn"]), ("Uws", edition["uws"])):
        resistances, lignes = table["r"], table["lignes"]
        if resistances != sorted(resistances) or [l["uw"] for l in lignes] != sorted(l["uw"] for l in lignes):
            erreurs.append(f"{nom} : lignes ou colonnes non ordonnées")
        for precedente, ligne in zip([None] + lignes[:-1], lignes):
            if any(v > ligne["uw"] for v in ligne["valeurs"]):
                erreurs.append(f"{nom} : valeur supérieure au Uw de la paroi nue (Uw = {ligne['uw']})")
            if any(b > a + 1e-9 for a, b in zip(ligne["valeurs"], ligne["valeurs"][1:])):
                alertes.append(f"{nom} Uw = {ligne['uw']} : la valeur augmente quand la résistance de la fermeture augmente")
            if precedente and any(b + 1e-9 < a for a, b in zip(precedente["valeurs"], ligne["valeurs"])):
                alertes.append(f"{nom} Uw = {ligne['uw']} : valeur plus faible que pour un Uw plus faible")
    ujn = {l["uw"]: l["valeurs"] for l in edition["ujn"]["lignes"]}
    for ligne in edition["uws"]["lignes"]:
        reference_ujn = ujn.get(ligne["uw"])
        if reference_ujn and any(uws > u + 1e-9 for uws, u in zip(ligne["valeurs"], reference_ujn)):
            alertes.append(f"Uws Uw = {ligne['uw']} : supérieur au Ujour-nuit correspondant")
    return erreurs, alertes


def assembler_edition(
    pages: dict[str, Pages],
    sources: dict[str, dict[str, Any]],
    edition: str,
    historique: list[str],
    extrait_le: str,
) -> dict[str, Any]:
    fenetres, protections, anomalies = extraire_fenetres(pages["fenetres"])
    correctifs, a_correctifs = extraire_correctifs(pages["fenetres"])
    portes, a_portes = extraire_portes(pages["portes"])
    fermetures, a_fermetures = extraire_fermetures(pages["fermetures"])
    ujn, a_ujn = extraire_table_fermeture(pages["ujn"], "Ujour-nuit")
    uws, a_uws = extraire_table_fermeture(pages["uws"], "Uws")
    resultat: dict[str, Any] = {
        "bibliotheque": "menuiseries",
        "regles": "Règles Th-Bât (RE2020), applications du fascicule parois vitrées",
        "edition": edition,
        "historique_edition": historique,
        "extrait_le": extrait_le,
        "sources": sources,
        "regles_usage": REGLES_USAGE,
        "protections": protections,
        "fenetres": fenetres,
        "correctifs": correctifs,
        "portes": portes,
        "fermetures": fermetures,
        "ujn": ujn,
        "uws": uws,
    }
    erreurs, alertes = controler(resultat)
    resultat["controles"] = {
        "methode": "Contrôles automatiques : structure des tableaux, plages de valeurs, cohérence physique.",
        "erreurs": anomalies + a_correctifs + a_portes + a_fermetures + a_ujn + a_uws + erreurs,
        "alertes": alertes,
        "comptes": {
            "fenetres": len(fenetres),
            "correctifs": sum(len(t["lignes"]) for t in correctifs),
            "portes": len(portes),
            "fermetures": len(fermetures),
            "ujn": len(ujn["lignes"]),
            "uws": len(uws["lignes"]),
        },
    }
    return resultat


# --- Consultation et calcul ---------------------------------------------------------------


@lru_cache(maxsize=1)
def charger_edition() -> dict[str, Any]:
    """Dernière édition publiée (fichiers `donnees/menuiseries_<édition>.json`)."""
    fichiers = sorted(DONNEES_DIR.glob("menuiseries_*.json"))
    if not fichiers:
        raise FileNotFoundError("Aucune édition de la bibliothèque des menuiseries.")
    return json.loads(fichiers[-1].read_text(encoding="utf-8"))


def interpoler(table: dict[str, Any], uw: float, r: float, nom: str) -> float:
    """Interpolation bilinéaire, sans extrapolation."""
    resistances = table["r"]
    lignes = table["lignes"]
    valeurs_uw = [ligne["uw"] for ligne in lignes]
    if not valeurs_uw or not resistances:
        raise ValueError(f"Tableau {nom} indisponible.")
    if not valeurs_uw[0] <= uw <= valeurs_uw[-1]:
        raise ValueError(f"Uw = {uw:g} hors du tableau {nom} ({valeurs_uw[0]:g} à {valeurs_uw[-1]:g} W/(m².K)).")
    if not resistances[0] <= r <= resistances[-1]:
        raise ValueError(f"R = {r:g} hors du tableau {nom} ({resistances[0]:g} à {resistances[-1]:g} m².K/W).")
    i = min(max(bisect_right(valeurs_uw, uw) - 1, 0), len(valeurs_uw) - 2) if len(valeurs_uw) > 1 else 0
    j = min(max(bisect_right(resistances, r) - 1, 0), len(resistances) - 2) if len(resistances) > 1 else 0

    def colonne(ligne: dict[str, Any]) -> float:
        if len(resistances) == 1:
            return ligne["valeurs"][0]
        r0, r1 = resistances[j], resistances[j + 1]
        t = (r - r0) / (r1 - r0)
        return ligne["valeurs"][j] + t * (ligne["valeurs"][j + 1] - ligne["valeurs"][j])

    if len(valeurs_uw) == 1:
        return colonne(lignes[0])
    u0, u1 = valeurs_uw[i], valeurs_uw[i + 1]
    t = (uw - u0) / (u1 - u0)
    return colonne(lignes[i]) + t * (colonne(lignes[i + 1]) - colonne(lignes[i]))


def calcul_fermeture(uw: float, r: float, edition: dict[str, Any] | None = None) -> dict[str, Any]:
    """Ujour-nuit et Uws d'une fenêtre de Uw donné, équipée d'une fermeture de résistance R."""
    edition = edition or charger_edition()
    ujn = interpoler(edition["ujn"], uw, r, "Ujour-nuit")
    remarque = None
    try:
        uws: float | None = round(interpoler(edition["uws"], uw, r, "Uws"), 2)
    except ValueError as exc:
        uws, remarque = None, str(exc)
    return {"uw": uw, "r": r, "ujn": round(ujn, 2), "uws": uws, "remarque": remarque}
