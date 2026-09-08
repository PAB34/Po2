"""Classeur agrégé : tout ce que le SIG sait de chaque local, sur une feuille.

Part du classeur à la maille local (`sig_agglo_classeur_local.py`) et y rattache
toutes les couches du SIG qui peuvent l'être. Deux mécanismes, et deux seulement :

  1. **par référence de parcelle** — l'inventaire (`sig_agglo_inventaire.py`) a
     sondé les 1 069 couches du catalogue : 559 sont lisibles par ce compte, et
     **23 portent un identifiant de parcelle**. Ce sont les seules qui se
     joignent sans approximation ;
  2. **par adresse, puis par proximité en dernier recours** — les logements
     vacants (LOVAC) ne portent ni référence de parcelle ni adresse structurée,
     seulement un libellé de voie et un point. On rapproche d'abord sur
     l'adresse exacte (commune + numéro + voie), et on ne retombe sur « la
     parcelle dont le centre est le plus proche » que pour le reste, en
     inscrivant la méthode et la distance dans le classeur.

La couche des copropriétés, elle, **n'a pas besoin d'approximation** : son champ
`idtup` est une référence de parcelle en bonne et due forme. C'est le nom de la
colonne qui trompe, pas la donnée — d'où la détection par forme des valeurs dans
`sig_agglo_inventaire.py`.

Le reste du catalogue (réseaux d'eau, routes, fonds de plan) n'a aucune clé
parcellaire : le rattacher supposerait un calcul d'intersection de polygones,
que ce poste ne peut pas faire (ni `shapely` ni `geopandas`). Ces couches ne
décrivent pas les biens de toute façon.

Une seconde feuille, `Dictionnaire`, dit d'où vient chaque colonne et combien de
lignes elle remplit réellement : sur une feuille aussi large, savoir ce qui est
du signal et ce qui est du décor fait partie du livrable.

⚠️ Données personnelles — la sortie reste dans `sig_agglo_data/`, hors git.

Usage :
    python scripts/sig_agglo_classeur_total.py
    python scripts/sig_agglo_classeur_total.py --seuil 40
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sig_agglo_classeur import parser_point, wgs84_vers_lambert93  # noqa: E402
from sig_agglo_classeur_local import construire, sans_accent  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

# Colonnes techniques : identifiants internes, géométries, libellés de recherche
# du client cartographique. Elles n'apprennent rien sur le bien.
BRUIT = re.compile(
    r"^(geom|gid|id|recherche|localisation|etiquettes?|etq_|remonter_tps|"
    r"date_rafraichissement|infobulle|dt_maj|date_reg)",
    re.I,
)

# Nom court donné à chaque couche dans le classeur, pour préfixer ses colonnes.
LIBELLES = {
    "604": "Historique cadastral",
    "532": "Unité foncière",
    "442": "Jardin > 50 m²",
    "128": "Jardin > 200 m²",
    "317": "Foncier public",
    "226": "Adresse Sète",
    "505": "Ravalement",
    "1456": "Ravalement Mèze",
    "328": "Parcelle communale",
    "309": "Parcelle mise à dispo",
    "140": "Foncier communal zone A",
    "516": "Foncier communal zone A",
    "77": "Départ de feu",
    "346": "Contour de feu",
    "1151": "Signalement cadastre",
    "1137": "Signalement cadastre",
    "731": "Foncier agglo zone A",
    "677": "Ravalement réalisé",
    "694": "Gestion foncière",
    "964": "ORI",
    "1370": "Sans info foncière",
    "1461": "Copropriété",
    "758": "Espace protégé",
    "320": "Couche 320",
    "104": "Couche 104",
    "230": "Couche 230",
}

# Colonnes conservées pour les couches très larges, afin que le classeur ne se
# remplisse pas d'identifiants internes du Cerema.
RETENUES = {
    "1461": ["nom_usage", "nom_syndic", "typ_syndic", "email_syndic", "telephone_standard",
             "telephone_portable", "contact_nom", "num_immat", "date_immat", "mandat",
             "adress_ref", "com_rl"],
}

# Fonds cadastraux : trois vues du même fond que la couche 943, déjà jointe.
# Les garder n'ajouterait que des colonnes redondantes sur 170 000 lignes.
REDONDANTES = {"320", "104", "230"}

# Couches dont la clé n'est pas un id_par mais peut être reconstituée :
# `section` + `parcelle` dans la commune indiquée.
RECONSTRUCTIBLES = {"226": "code_insee", "964": "34301"}

PARCELLES_XY = "943_agglo_s_cadastre_vmap_fond_cadastral_parcelle.csv"
COPROFF = "1461_layer_1461.csv"
LOVAC = "1162_layer_1162.csv"


def lire(chemin: Path) -> pd.DataFrame:
    return pd.read_csv(chemin, dtype=str, encoding="utf-8-sig", low_memory=False).fillna("")


def colonnes_utiles(cadre: pd.DataFrame, cle: str) -> list[str]:
    return [c for c in cadre.columns if c != cle and not BRUIT.match(c)]


def reconstruire_id_par(cadre: pd.DataFrame, commune: str) -> pd.Series:
    """`34301` + `AS` + `261` → `34301000AS0261`.

    Certaines couches ne portent que la section et le numéro de parcelle. Le
    format MAJIC est figé : commune (5), préfixe (3), section (2), numéro (4).
    """

    insee = cadre[commune] if commune in cadre.columns else pd.Series(commune, index=cadre.index)
    section = cadre["section"].str.strip().str.upper().str.rjust(2, "0")
    numero = cadre["parcelle"].str.strip().str.zfill(4)
    return insee.str.strip() + "000" + section + numero


def joindre_par_parcelle(base: pd.DataFrame, data_dir: Path, journal: list[dict]) -> pd.DataFrame:
    """Rattache toutes les couches portant un identifiant de parcelle."""

    inventaire = lire(data_dir / "inventaire_couches.csv")
    inventaire["n"] = pd.to_numeric(inventaire["lignes"], errors="coerce").fillna(0)
    couches = inventaire[
        (inventaire["http"] == "200")
        & (inventaire["cle_parcelle"] != "")
        & (inventaire["n"] > 0)
    ].drop_duplicates(subset=["table"])

    id_par = base["Réf. cadastrale (id_par)"]
    for _, couche in couches.iterrows():
        layer_id = couche["layer_id"]
        fichiers = sorted(data_dir.glob(f"{layer_id}_*.csv"))
        if not fichiers:
            continue
        if layer_id in REDONDANTES:
            continue
        cadre = lire(fichiers[0])
        cle = couche["cle_parcelle"]
        if layer_id in RECONSTRUCTIBLES and {"section", "parcelle"} <= set(cadre.columns):
            cadre["id_par_reconstruit"] = reconstruire_id_par(cadre, RECONSTRUCTIBLES[layer_id])
            cle = "id_par_reconstruit"
        if cle not in cadre.columns or (cadre[cle].str.strip() == "").all():
            print(f"    {LIBELLES.get(layer_id, layer_id):26} écartée — clé « {cle} » inutilisable")
            continue
        libelle = LIBELLES.get(layer_id, f"Couche {layer_id}")
        # Une parcelle peut apparaître plusieurs fois (plusieurs signalements,
        # plusieurs feux) : on garde la première et on compte les autres.
        occurrences = cadre.groupby(cle).size()
        cadre = cadre.drop_duplicates(subset=[cle]).set_index(cle)

        base[f"{libelle} — présent"] = id_par.isin(cadre.index).map({True: "Oui", False: ""})
        if (occurrences > 1).any():
            base[f"{libelle} — occurrences"] = id_par.map(occurrences).fillna("")
        gardees = RETENUES.get(layer_id) or colonnes_utiles(cadre.reset_index(), cle)
        for colonne in [c for c in gardees if c in cadre.columns]:
            nom = f"{libelle} — {colonne}"
            base[nom] = id_par.map(cadre[colonne]).fillna("")
            journal.append(
                {
                    "Colonne": nom,
                    "Origine": f"couche {layer_id} ({couche['table']})",
                    "Rattachement": f"référence de parcelle ({cle})",
                }
            )
        print(f"    {libelle:26} {int(id_par.isin(cadre.index).sum()):>7} locaux touchés")
    return base


def adresses_parcelles(data_dir: Path) -> pd.Series | None:
    """Index (commune, numéro, voie) → référence de parcelle.

    Sert à rattacher par l'adresse ce qui ne porte pas de référence cadastrale.
    Les adresses ambiguës — une même voie et un même numéro sur deux parcelles —
    sont écartées : mieux vaut retomber sur le rapprochement géographique que
    d'attribuer un bien à la mauvaise parcelle.
    """

    chemin = data_dir / "cadastre_description_parcelles.csv"
    if not chemin.is_file():
        return None
    cadre = lire(chemin)
    cle = pd.DataFrame(
        {
            "com": cadre["ID_COM"].str.strip(),
            "num": cadre["DNVOIRI"].str.strip().str.lstrip("0"),
            "voie": sans_accent(cadre["DVOILIB"]),
            "id_par": cadre["ID_PAR"],
        }
    )
    cle = cle[(cle["num"] != "") & (cle["voie"] != "")]
    unique = cle.groupby(["com", "num", "voie"])["id_par"].nunique()
    cle = cle[cle.set_index(["com", "num", "voie"]).index.map(unique).fillna(0) == 1]
    return cle.drop_duplicates(subset=["com", "num", "voie"]).set_index(
        ["com", "num", "voie"]
    )["id_par"]


def centres_parcelles(data_dir: Path) -> pd.DataFrame:
    """Centre de chaque parcelle, en Lambert-93.

    La couche du fond cadastral porte déjà x/y en degrés : pas de polygone à
    découper, seulement une projection — celle validée en §5 du document de
    décisions (écart médian 31 m sur les données réelles).
    """

    cadre = lire(data_dir / PARCELLES_XY)
    cadre = cadre[(cadre["x"] != "") & (cadre["y"] != "")].drop_duplicates(subset=["id_par"])
    lon = pd.to_numeric(cadre["x"], errors="coerce").to_numpy()
    lat = pd.to_numeric(cadre["y"], errors="coerce").to_numpy()
    x, y = wgs84_vers_lambert93(lon, lat)
    return pd.DataFrame({"id_par": cadre["id_par"].to_numpy(), "x": x, "y": y}).dropna()


def joindre_par_proximite(
    base: pd.DataFrame,
    data_dir: Path,
    centres: pd.DataFrame,
    journal: list[dict],
    seuil: float,
) -> pd.DataFrame:
    """Rattache COPROFF et LOVAC à la parcelle dont le centre est le plus proche."""

    arbre = cKDTree(centres[["x", "y"]].to_numpy())
    id_par = base["Réf. cadastrale (id_par)"]

    # Le rattachement est à la maille PARCELLE : tous les lots d'une parcelle
    # héritent de ce qui lui est rattaché. C'est juste pour une copropriété —
    # tous ses lots en font partie — mais faux pour un logement vacant : un
    # appartement vide n'en rend pas 1 480 autres vacants. La vacance est donc
    # comptée au niveau de la parcelle, et nommée comme telle.
    for fichier, libelle, garder in [
        (LOVAC, "Parcelle — vacance", ["nature", "annee", "debutvacan", "ff_jannath",
                                       "ff_stoth", "ff_npiece_", "libvoie", "libcom"]),
    ]:
        chemin = data_dir / fichier
        if not chemin.is_file():
            continue
        cadre = lire(chemin)
        points = parser_point(cadre["geom"])
        valides = points.dropna()
        distances, indices = arbre.query(valides[["x", "y"]].to_numpy(), k=1)
        cadre = cadre.loc[valides.index].copy()
        cadre["id_par"] = centres["id_par"].to_numpy()[indices]
        cadre["distance"] = distances.round(1)
        cadre["methode"] = f"parcelle la plus proche (≤ {seuil:.0f} m)"

        # L'adresse d'abord : `0005   AV   RAOUL BONNECAZE` porte le numéro et le
        # nom de la voie, que le cadastre range dans DNVOIRI et DVOILIB. Quand
        # les deux concordent dans la même commune, le rattachement est exact et
        # remplace celui du plus proche voisin.
        exact = adresses_parcelles(data_dir)
        if "libvoie" in cadre.columns and exact is not None:
            morceaux = cadre["libvoie"].str.strip().str.split(r"\s+", n=2, regex=True)
            numero = morceaux.str[0].fillna("").str.lstrip("0")
            voie = sans_accent(morceaux.str[2].fillna(""))
            cle = pd.MultiIndex.from_arrays([cadre["ff_idcom"].str.strip(), numero, voie])
            trouve = pd.Series(exact.reindex(cle).to_numpy(), index=cadre.index)
            cadre.loc[trouve.notna(), "methode"] = "adresse exacte (numéro + voie)"
            cadre.loc[trouve.notna(), "distance"] = ""
            cadre["id_par"] = trouve.fillna(cadre["id_par"])
            print(f"      {int(trouve.notna().sum())} rapprochements par adresse exacte")

        approche = cadre["methode"] != "adresse exacte (numéro + voie)"
        cadre = cadre[~approche | (pd.to_numeric(cadre["distance"], errors="coerce") <= seuil)]
        # Combien de points tombent sur la parcelle : pour la vacance, c'est
        # l'information utile — « cette parcelle compte 3 logements vacants ».
        occurrences = cadre.groupby("id_par").size()
        # Quand plusieurs points tombent sur une parcelle, le meilleur gagne :
        # un rattachement par adresse exacte d'abord (rang 0), puis le plus
        # proche géographiquement.
        cadre["rang"] = pd.to_numeric(cadre["distance"], errors="coerce").fillna(0)
        cadre = cadre.sort_values("rang").drop_duplicates(subset=["id_par"]).set_index("id_par")

        base[f"{libelle} — nombre"] = id_par.map(occurrences).fillna("")
        base[f"{libelle} — rattachée"] = id_par.isin(cadre.index).map({True: "Oui", False: ""})
        base[f"{libelle} — méthode"] = id_par.map(cadre["methode"]).fillna("")
        base[f"{libelle} — distance (m)"] = id_par.map(cadre["distance"]).fillna("")
        for colonne in garder:
            if colonne not in cadre.columns:
                continue
            nom = f"{libelle} — {colonne}"
            base[nom] = id_par.map(cadre[colonne]).fillna("")
            journal.append(
                {
                    "Colonne": nom,
                    "Origine": fichier,
                    "Rattachement": f"parcelle la plus proche (≤ {seuil:.0f} m)",
                }
            )
        print(f"    {libelle:26} {int(id_par.isin(cadre.index).sum()):>7} locaux touchés")
    return base


def joindre_parcelle_xy(base: pd.DataFrame, centres: pd.DataFrame, data_dir: Path,
                        journal: list[dict]) -> pd.DataFrame:
    """Surface réelle et coordonnées de la parcelle."""

    cadre = lire(data_dir / PARCELLES_XY).drop_duplicates(subset=["id_par"]).set_index("id_par")
    id_par = base["Réf. cadastrale (id_par)"]
    for source, nom in [
        ("sup_m2", "Parcelle — surface (m²)"),
        ("sup_fiscale", "Parcelle — surface fiscale (m²)"),
        ("x", "Longitude"),
        ("y", "Latitude"),
        ("jdatat", "Parcelle — dernière mutation"),
    ]:
        if source in cadre.columns:
            base[nom] = id_par.map(cadre[source]).fillna("")
            journal.append(
                {"Colonne": nom, "Origine": "couche 943 (fond cadastral)",
                 "Rattachement": "référence de parcelle (id_par)"}
            )
    return base


def ecrire(base: pd.DataFrame, journal: pd.DataFrame, cible: Path) -> None:
    print(f"[5/5] écriture de {len(base)} lignes × {len(base.columns)} colonnes")
    workbook = Workbook(write_only=True)
    workbook._named_styles["Normal"].font = Font(name="Arial", size=10)

    feuille = workbook.create_sheet("Locaux agglo")
    feuille.freeze_panes = "A2"
    police = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    fond = PatternFill("solid", fgColor="1F4E79")
    entete = []
    for nom in base.columns:
        cellule = WriteOnlyCell(feuille, value=nom)
        cellule.font, cellule.fill = police, fond
        cellule.alignment = Alignment(vertical="center", wrap_text=True)
        entete.append(cellule)
    feuille.append(entete)
    for index in range(1, len(base.columns) + 1):
        feuille.column_dimensions[get_column_letter(index)].width = 18
    for valeurs in base.itertuples(index=False, name=None):
        feuille.append(
            ["" if v is None or (isinstance(v, float) and math.isnan(v)) else v for v in valeurs]
        )
    feuille.auto_filter.ref = f"A1:{get_column_letter(len(base.columns))}{len(base) + 1}"

    dico = workbook.create_sheet("Dictionnaire")
    dico.freeze_panes = "A2"
    entete = []
    for nom in journal.columns:
        cellule = WriteOnlyCell(dico, value=nom)
        cellule.font, cellule.fill = police, fond
        entete.append(cellule)
    dico.append(entete)
    for index, largeur in enumerate([46, 44, 34, 14, 12], start=1):
        dico.column_dimensions[get_column_letter(index)].width = largeur
    for valeurs in journal.itertuples(index=False, name=None):
        dico.append(list(valeurs))

    workbook.save(cible)


def main() -> int:
    parser = argparse.ArgumentParser(description="Classeur agrégé du SIG, maille local.")
    parser.add_argument("--data-dir", default="sig_agglo_data")
    parser.add_argument("--sortie", default="locaux-agglo-complet.xlsx")
    parser.add_argument(
        "--seuil", type=float, default=60.0,
        help="distance maximale, en mètres, d'un rattachement géographique",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    journal: list[dict] = []

    base = construire(data_dir)
    for colonne in base.columns:
        journal.append(
            {"Colonne": colonne, "Origine": "cadastre MAJIC (module openmajic)",
             "Rattachement": "maille local"}
        )

    print("[+] couches rattachées par référence de parcelle")
    centres = centres_parcelles(data_dir)
    base = joindre_parcelle_xy(base, centres, data_dir, journal)
    base = joindre_par_parcelle(base, data_dir, journal)

    print(f"[+] couches rattachées par proximité (seuil {args.seuil:.0f} m)")
    base = joindre_par_proximite(base, data_dir, centres, journal, args.seuil)

    remplissage = {
        c: int((base[c].astype(str).str.strip() != "").sum()) for c in base.columns
    }
    # Une colonne vide sur 176 695 lignes n'est pas une donnée, c'est du décor :
    # elle sort de la feuille et reste au dictionnaire, qui dit ce qui a été tenté.
    vides = [c for c, n in remplissage.items() if n == 0]
    base = base.drop(columns=vides)
    print(f"[+] {len(vides)} colonnes entièrement vides retirées de la feuille")

    dictionnaire = pd.DataFrame(journal).drop_duplicates(subset=["Colonne"])
    dictionnaire["Lignes remplies"] = dictionnaire["Colonne"].map(remplissage).fillna(0).astype(int)
    dictionnaire["Dans la feuille"] = dictionnaire["Colonne"].map(
        lambda c: "non — colonne vide" if c in set(vides) else "oui"
    )
    dictionnaire["% rempli"] = (100 * dictionnaire["Lignes remplies"] / len(base)).round(1)
    dictionnaire = dictionnaire.sort_values("Lignes remplies", ascending=False)

    cible = data_dir / args.sortie
    ecrire(base, dictionnaire, cible)

    print(f"\nClasseur : {cible.resolve()}")
    print(f"  {len(base)} lignes × {len(base.columns)} colonnes, toutes renseignées au moins une fois")
    print(f"  {len(vides)} colonnes tentées mais vides, listées au dictionnaire")
    print("  feuille « Dictionnaire » : origine et taux de remplissage de chaque colonne")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
