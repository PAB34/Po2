"""Classeur unique du foncier de l'agglo : une ligne = un propriétaire sur un bien.

Répond à une demande précise : tout dans **un seul fichier, une seule feuille**,
avec sur chaque ligne l'adresse du **propriétaire** ET l'adresse du **bien** —
deux choses différentes que la source ne fournit pas au même endroit.

  - adresse du propriétaire → couche 474, colonnes `dlign3` à `dlign6` (son
    domicile : pour la Ville de Sète, c'est l'Hôtel de Ville) ;
  - adresse du bien → deux sources, parce qu'aucune ne couvre tout :
      * `adresse.v_sete_adresse` (9 974 adresses) porte `section` + `parcelle` :
        rattachement **exact**, mais Sète seulement ;
      * `referentiels.vmp_ban` (80 514 adresses) couvre le territoire mais n'a
        que des points : rattachement **approché**, par le point le plus proche
        du centre de la parcelle, avec la distance reportée en clair.

La colonne `bien_adresse_source` dit toujours laquelle des deux a servi, et
`bien_adresse_distance_m` permet de juger une adresse approchée plutôt que de
lui faire confiance à l'aveugle.

⚠️ Le classeur produit contient des données à caractère personnel : il est écrit
dans le dossier d'extraction, déjà protégé de git.

Usage :
    python scripts/sig_agglo_classeur.py [--data sig_agglo_data] [--rayon 100]
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
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from scipy.spatial import cKDTree

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

FICHIERS = {
    "proprietaires": "474_agglo_s_cadastre_vmp_uf_proprietaire.csv",
    "parcelles": "943_agglo_s_cadastre_vmap_fond_cadastral_parcelle.csv",
    "public": "317_foncier_vmp_foncier_public.csv",
    "adresses_sete": "226_adresse_v_sete_adresse.csv",
    "ban": "397_referentiels_vmp_ban.csv",
}

# RGF93 / Lambert-93 (EPSG:2154) — les paramètres officiels de l'IGN.
A_GRS80 = 6378137.0
E_GRS80 = 0.081819191042816
LON0, LAT0 = math.radians(3.0), math.radians(46.5)
LAT1, LAT2 = math.radians(44.0), math.radians(49.0)
X0, Y0 = 700000.0, 6600000.0


def _t(lat: np.ndarray | float) -> np.ndarray | float:
    sin = np.sin(lat)
    return np.tan(np.pi / 4 - lat / 2) / np.power(
        (1 - E_GRS80 * sin) / (1 + E_GRS80 * sin), E_GRS80 / 2
    )


def _m(lat: float) -> float:
    return math.cos(lat) / math.sqrt(1 - (E_GRS80 * math.sin(lat)) ** 2)


def wgs84_vers_lambert93(lon_deg: np.ndarray, lat_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Projection conique conforme de Lambert, sécante aux parallèles 44° et 49°.

    Les centroïdes de parcelle sont livrés en degrés, la BAN en Lambert-93 :
    sans cette conversion, aucune distance n'a de sens. `pyproj` ferait l'affaire
    mais n'est pas installé sur le poste ; la formule est standard et le script
    la vérifie sur les données réelles avant de s'en servir (`valider_projection`).
    """

    n = math.log(_m(LAT1) / _m(LAT2)) / math.log(_t(LAT1) / _t(LAT2))
    f = _m(LAT1) / (n * _t(LAT1) ** n)
    rho0 = A_GRS80 * f * _t(LAT0) ** n

    lon, lat = np.radians(lon_deg), np.radians(lat_deg)
    rho = A_GRS80 * f * np.power(_t(lat), n)
    gamma = n * (lon - LON0)
    return X0 + rho * np.sin(gamma), Y0 + rho0 - rho * np.cos(gamma)


def charger(data_dir: Path, cle: str) -> pd.DataFrame:
    chemin = data_dir / FICHIERS[cle]
    if not chemin.is_file():
        raise SystemExit(f"Fichier manquant : {chemin}\nLancer d'abord sig_agglo_extract.py.")
    return pd.read_csv(chemin, dtype=str, encoding="utf-8-sig", low_memory=False).fillna("")


def parser_point(serie: pd.Series) -> pd.DataFrame:
    """Extrait x/y d'un EWKT `SRID=2154;POINT(x y)`."""

    extrait = serie.str.extract(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)")
    return pd.DataFrame(
        {
            "x": pd.to_numeric(extrait[0], errors="coerce"),
            "y": pd.to_numeric(extrait[1], errors="coerce"),
        }
    )


def normaliser_voie(valeur: str) -> str:
    """`0007 RUE PAUL VALERY` → `7 RUE PAUL VALERY`.

    MAJIC cale le numéro sur quatre chiffres avec des zéros devant. Laissés tels
    quels, ils font échouer tout rapprochement d'adresse.
    """

    valeur = valeur.strip()
    return re.sub(r"^0+(?=\d)", "", valeur)


def valider_projection(parcelles: pd.DataFrame, ban_xy: pd.DataFrame) -> float:
    """Vérifie la conversion sur les données réelles, avant de s'y fier.

    On projette les centroïdes de parcelle et on regarde à quelle distance tombe
    le point BAN le plus proche. Si la projection était fausse (mauvais
    paramètres, axes inversés), l'écart se compterait en kilomètres.
    """

    echantillon = parcelles.dropna(subset=["cx", "cy"]).head(5000)
    arbre = cKDTree(ban_xy[["x", "y"]].dropna().to_numpy())
    distances, _ = arbre.query(echantillon[["cx", "cy"]].to_numpy(), k=1)
    return float(np.median(distances))


COMMUNES_AGGLO = {
    "34023", "34024", "34039", "34108", "34113", "34143", "34150",
    "34157", "34159", "34165", "34213", "34301", "34333", "34341",
}


def joindre_adresses(
    id_par: pd.Series,
    exactes: pd.DataFrame,
    proches: pd.DataFrame,
    compte: pd.Series,
) -> dict[str, pd.Series]:
    """Résout l'adresse du bien pour une série de références cadastrales.

    Exact d'abord (Sète), BAN en repli, et toujours la source et la distance :
    une adresse approchée doit pouvoir être jugée, pas subie.
    """

    ex_lib = id_par.map(exactes["libelle"])
    pr_lib = id_par.map(proches["libelle"])
    return {
        "libelle": ex_lib.fillna(pr_lib),
        "code_postal": id_par.map(exactes["code_post"]).fillna(id_par.map(proches["code_postal"])),
        "source": pd.Series(
            np.where(
                ex_lib.notna(), "Exacte (cadastre Sète)",
                np.where(pr_lib.notna(), "Approchée (BAN)", "Non trouvée"),
            ),
            index=id_par.index,
        ),
        "distance": id_par.map(proches["distance"]).where(ex_lib.isna()),
        "nb": id_par.map(compte),
    }


def construire_public(
    public: pd.DataFrame,
    parcelles: pd.DataFrame,
    exactes: pd.DataFrame,
    proches: pd.DataFrame,
    compte: pd.Series,
) -> pd.DataFrame:
    """Feuille « foncier public », disponible sur les 27 communes du SIG.

    Hors des 14 communes de l'agglo (Agde, Florensac, Montagnac…), la couche
    nominative MAJIC est absente : seule cette couche-ci porte un propriétaire,
    et uniquement des personnes morales publiques. C'est donc tout ce qu'on peut
    obtenir sur ces communes — et cela ne pose aucun problème de donnée personnelle.
    """

    ligne = public.merge(
        parcelles[["id_par", "commune", "section", "parcelle", "pre", "sup_m2", "jdatat", "x", "y"]],
        on="id_par",
        how="left",
    )
    adresse = joindre_adresses(ligne["id_par"], exactes, proches, compte)
    return pd.DataFrame(
        {
            "Propriétaire": ligne["ddenom"].str.strip(),
            "Type de propriétaire public": ligne["type"].str.strip(),
            "Nature du droit": ligne["l_ccodro"].str.strip(),
            "Nb de propriétaires sur la parcelle": pd.to_numeric(ligne["nb_proprio"], errors="coerce"),
            "Adresse du bien": adresse["libelle"].fillna(""),
            "Bien — code postal": adresse["code_postal"].fillna(""),
            "Bien — commune": ligne["commune"].str.strip(),
            "Source adresse du bien": adresse["source"],
            "Distance adresse (m)": adresse["distance"].round(0),
            "Nb adresses sur la parcelle": adresse["nb"],
            "Dans l'agglo": np.where(ligne["id_com"].isin(COMMUNES_AGGLO), "Oui", "Non"),
            "Propriétaires nominatifs disponibles": np.where(
                ligne["id_com"].isin(COMMUNES_AGGLO), "Oui", "Non (hors périmètre MAJIC)"
            ),
            "Réf. cadastrale (id_par)": ligne["id_par"],
            "Code INSEE": ligne["id_com"].str.strip(),
            "Préfixe": ligne["pre"],
            "Section": ligne["section"],
            "N° parcelle": ligne["parcelle"],
            "Surface cadastrale (m²)": pd.to_numeric(ligne["surfcad_m2"], errors="coerce"),
            "Surface SIG (m²)": pd.to_numeric(ligne["surfsig_m2"], errors="coerce"),
            "Date d'acte": ligne["jdatat"].str.strip(),
            "Millésime MAJIC": ligne["dtmajic"].str.strip(),
            "Longitude": pd.to_numeric(ligne["x"], errors="coerce"),
            "Latitude": pd.to_numeric(ligne["y"], errors="coerce"),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Classeur unique du foncier de l'agglo.")
    parser.add_argument(
        "--source",
        choices=("proprietaires", "public"),
        default="proprietaires",
        help="« proprietaires » = MAJIC nominatif, 14 communes de l'agglo ; "
        "« public » = foncier public, disponible sur les 27 communes (Agde comprise)",
    )
    parser.add_argument("--data", default="sig_agglo_data", help="dossier d'extraction")
    parser.add_argument("--sortie", default="foncier-agglo.xlsx", help="nom du classeur")
    parser.add_argument(
        "--rayon",
        type=float,
        default=100.0,
        help="distance max (m) pour retenir une adresse BAN approchée (défaut 100)",
    )
    args = parser.parse_args()
    data_dir = Path(args.data)

    print("[1/6] lecture des extractions")
    proprios = charger(data_dir, "proprietaires").rename(columns={"id_uf": "id_par"})
    parcelles = charger(data_dir, "parcelles").drop_duplicates("id_par")
    public = charger(data_dir, "public")
    adr_sete = charger(data_dir, "adresses_sete")
    ban = charger(data_dir, "ban")

    parcelles["cx"], parcelles["cy"] = wgs84_vers_lambert93(
        pd.to_numeric(parcelles["x"], errors="coerce").to_numpy(),
        pd.to_numeric(parcelles["y"], errors="coerce").to_numpy(),
    )
    ban_xy = parser_point(ban["geom"])
    ecart = valider_projection(parcelles, ban_xy)
    print(f"      projection Lambert-93 vérifiée : écart médian parcelle↔adresse = {ecart:.0f} m")
    if ecart > 500:
        raise SystemExit(
            f"Projection suspecte ({ecart:.0f} m d'écart médian) : rattachement d'adresse abandonné."
        )

    # --- Adresse du bien, source exacte (Sète) ------------------------------ #
    print("[2/6] adresses exactes (Sète, via section + parcelle)")
    paires = []
    for suffixe in ("", "2", "3"):
        # Une adresse peut porter jusqu'à trois parcelles (section/parcelle,
        # puis 2 et 3). On sélectionne AVANT de renommer : renommer `section2`
        # en `section` alors que `section` existe déjà créerait un doublon.
        col_section, col_parcelle = f"section{suffixe}", f"parcelle{suffixe}"
        if col_section not in adr_sete.columns or col_parcelle not in adr_sete.columns:
            continue
        bloc = adr_sete[
            [col_section, col_parcelle, "numero", "rep", "nom_voie", "code_post"]
        ].copy()
        bloc.columns = ["section", "parcelle", "numero", "rep", "nom_voie", "code_post"]
        paires.append(bloc[(bloc["section"] != "") & (bloc["parcelle"] != "")])
    exactes = pd.concat(paires, ignore_index=True)
    exactes["parcelle"] = exactes["parcelle"].str.zfill(4)
    exactes["id_com"] = "34301"

    cle_parcelle = parcelles[["id_par", "id_com", "section", "parcelle"]]
    exactes = exactes.merge(cle_parcelle, on=["id_com", "section", "parcelle"], how="inner")
    exactes["libelle"] = (
        exactes["numero"].str.strip()
        + exactes["rep"].str.strip().radd(" ").str.rstrip()
        + " "
        + exactes["nom_voie"].str.strip()
    ).str.strip()
    exactes["numero_tri"] = pd.to_numeric(exactes["numero"], errors="coerce").fillna(99999)
    compte = exactes.groupby("id_par")["libelle"].nunique().rename("bien_nb_adresses")
    exactes = (
        exactes.sort_values("numero_tri").drop_duplicates("id_par").set_index("id_par")
    )
    print(f"      {len(exactes)} parcelles adressées exactement")

    # --- Adresse du bien, source approchée (BAN) ---------------------------- #
    print("[3/6] adresses approchées (BAN, point le plus proche)")
    ban = ban.join(ban_xy).dropna(subset=["x", "y"]).reset_index(drop=True)
    arbre = cKDTree(ban[["x", "y"]].to_numpy())
    valides = parcelles["cx"].notna() & parcelles["cy"].notna()
    distances, indices = arbre.query(parcelles.loc[valides, ["cx", "cy"]].to_numpy(), k=1)
    proches = pd.DataFrame(
        {
            "id_par": parcelles.loc[valides, "id_par"].to_numpy(),
            "distance": distances,
            "libelle": (
                ban.loc[indices, "numero"].str.strip().to_numpy()
                + " "
                + ban.loc[indices, "nom_voie"].str.strip().to_numpy()
            ),
            "code_postal": ban.loc[indices, "code_postal"].to_numpy(),
            "commune": ban.loc[indices, "nom_commune"].to_numpy(),
        }
    ).set_index("id_par")
    proches = proches[proches["distance"] <= args.rayon]
    print(f"      {len(proches)} parcelles adressées à moins de {args.rayon:.0f} m")

    # --- Assemblage --------------------------------------------------------- #
    print("[4/6] assemblage de la ligne unique")
    if args.source == "public":
        classeur = construire_public(public, parcelles, exactes, proches, compte)
        return ecrire(classeur, data_dir, args.sortie, "Foncier public")

    ligne = proprios.merge(
        parcelles[
            ["id_par", "commune", "section", "parcelle", "pre", "sup_m2", "sup_fiscale", "jdatat", "x", "y"]
        ],
        on="id_par",
        how="left",
    )
    droits = (
        public.sort_values("l_ccodro").drop_duplicates("id_par").set_index("id_par")[["type", "l_ccodro"]]
    )

    est_particulier = ligne["dqualp"].str.strip().isin(["M", "MME"])
    cp_commune = ligne["dlign6"].str.strip().str.extract(r"^(\d{5})\s*(.*)$")

    voie_prop = ligne["dlign4"].map(normaliser_voie)
    adresse_prop = (
        ligne["dlign3"].str.strip()
        + " " + voie_prop
        + " " + ligne["dlign5"].str.strip()
        + " " + ligne["dlign6"].str.strip()
    ).str.replace(r"\s+", " ", regex=True).str.strip()

    ex_lib = ligne["id_par"].map(exactes["libelle"])
    ex_cp = ligne["id_par"].map(exactes["code_post"])
    pr_lib = ligne["id_par"].map(proches["libelle"])
    pr_cp = ligne["id_par"].map(proches["code_postal"])
    pr_com = ligne["id_par"].map(proches["commune"])
    pr_dist = ligne["id_par"].map(proches["distance"])

    bien_libelle = ex_lib.fillna(pr_lib)
    source = np.where(
        ex_lib.notna(), "Exacte (cadastre Sète)",
        np.where(pr_lib.notna(), "Approchée (BAN)", "Non trouvée"),
    )

    classeur = pd.DataFrame(
        {
            "Propriétaire": ligne["ddenom"].str.strip(),
            "Type de personne": np.where(est_particulier, "Particulier", "Personne morale"),
            "Civilité": ligne["dqualp"].str.strip(),
            "Nom": ligne["dnomlp"].str.strip(),
            "Prénom": ligne["dprnlp"].str.strip(),
            "Nom d'usage": ligne["dnomus"].str.strip(),
            "Prénom d'usage": ligne["dprnus"].str.strip(),
            "N° personne (dnuper)": ligne["dnuper"].str.strip(),
            "Compte communal (dnupro)": ligne["dnupro"].str.strip(),
            "Adresse propriétaire": adresse_prop,
            "Prop. — complément": ligne["dlign3"].str.strip(),
            "Prop. — n° et voie": voie_prop,
            "Prop. — lieu-dit": ligne["dlign5"].str.strip(),
            "Prop. — code postal": cp_commune[0].fillna(""),
            "Prop. — commune": cp_commune[1].fillna(""),
            "Prop. hors Hérault": np.where(
                cp_commune[0].fillna("").str.startswith("34") | (cp_commune[0].fillna("") == ""),
                "Non", "Oui",
            ),
            "Adresse du bien": bien_libelle.fillna(""),
            "Bien — code postal": ex_cp.fillna(pr_cp).fillna(""),
            "Bien — commune": ligne["commune"].str.strip(),
            "Source adresse du bien": source,
            "Distance adresse (m)": pr_dist.where(ex_lib.isna()).round(0),
            "Nb adresses sur la parcelle": ligne["id_par"].map(compte),
            "Réf. cadastrale (id_par)": ligne["id_par"],
            "Code INSEE": ligne["id_com"].str.strip(),
            "Préfixe": ligne["pre"],
            "Section": ligne["section"],
            "N° parcelle": ligne["parcelle"],
            "Surface parcelle (m²)": pd.to_numeric(ligne["sup_m2"], errors="coerce"),
            "Surface fiscale (m²)": pd.to_numeric(ligne["sup_fiscale"], errors="coerce"),
            "Date d'acte": ligne["jdatat"].str.strip(),
            "Longitude": pd.to_numeric(ligne["x"], errors="coerce"),
            "Latitude": pd.to_numeric(ligne["y"], errors="coerce"),
            "Foncier public — type": ligne["id_par"].map(droits["type"]).fillna(""),
            "Foncier public — droit": ligne["id_par"].map(droits["l_ccodro"]).fillna(""),
        }
    )

    return ecrire(classeur, data_dir, args.sortie, "Foncier agglo")


def ecrire(classeur: pd.DataFrame, data_dir: Path, sortie: str, titre: str) -> int:
    """Écrit une feuille unique, à plat, filtrable — pas de second onglet."""

    print(f"[5/6] écriture de {len(classeur)} lignes × {len(classeur.columns)} colonnes")
    workbook = Workbook(write_only=True)
    # Police par défaut du classeur : évite d'appliquer un style aux 2 millions
    # de cellules une par une.
    workbook._named_styles["Normal"].font = Font(name="Arial", size=10)
    feuille = workbook.create_sheet(titre)
    feuille.freeze_panes = "A2"

    entete_police = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    entete_fond = PatternFill("solid", fgColor="1F4E79")
    from openpyxl.cell import WriteOnlyCell

    entete = []
    for nom in classeur.columns:
        cellule = WriteOnlyCell(feuille, value=nom)
        cellule.font = entete_police
        cellule.fill = entete_fond
        cellule.alignment = Alignment(vertical="center", wrap_text=True)
        entete.append(cellule)
    feuille.append(entete)

    largeurs = {
        "Propriétaire": 38, "Adresse propriétaire": 45, "Adresse du bien": 32,
        "Prop. — n° et voie": 28, "Prop. — complément": 24, "Prop. — commune": 20,
        "Source adresse du bien": 22, "Réf. cadastrale (id_par)": 18, "Bien — commune": 18,
        "Foncier public — type": 20, "Foncier public — droit": 26, "Nom": 18, "Prénom": 16,
    }
    for index, nom in enumerate(classeur.columns, start=1):
        feuille.column_dimensions[get_column_letter(index)].width = largeurs.get(nom, 14)

    for valeurs in classeur.itertuples(index=False, name=None):
        feuille.append(["" if v is None or (isinstance(v, float) and math.isnan(v)) else v for v in valeurs])

    feuille.auto_filter.ref = (
        f"A1:{get_column_letter(len(classeur.columns))}{len(classeur) + 1}"
    )
    cible = data_dir / sortie
    workbook.save(cible)

    print("[6/6] terminé")
    exact_n = int((classeur["Source adresse du bien"] == "Exacte (cadastre Sète)").sum())
    appro_n = int((classeur["Source adresse du bien"] == "Approchée (BAN)").sum())
    absent = len(classeur) - exact_n - appro_n
    print(f"\nClasseur : {cible.resolve()}")
    print(f"  {len(classeur)} lignes, une par couple propriétaire × bien")
    print(f"  adresse du bien : {exact_n} exactes, {appro_n} approchées, {absent} sans adresse")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
