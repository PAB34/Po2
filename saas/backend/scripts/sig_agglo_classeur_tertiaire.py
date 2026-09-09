"""Classeur des cibles tertiaires — prospection AMO performance énergétique.

Une ligne par établissement des 14 communes de l'agglo **et d'Agde**, enrichie de
ce que le cadastre et l'ADEME savent du bâtiment qu'il occupe. Distinct du
classeur résidentiel `locaux-agglo-complet.xlsx`, qui reste inchangé.
Décisions : `docs/refonte-v1/cibles-tertiaires-decisions.md`.

Trois enrichissements, du plus sûr au plus approché :

  1. **parcelle cadastrale** — par les coordonnées de l'établissement, au centre
     de parcelle le plus proche. Le fond cadastral couvre 27 communes, Agde
     comprise : le rattachement y fonctionne, seul le propriétaire manquera ;
  2. **propriétaire du local** — par la parcelle, et **uniquement sur les 14
     communes** : les fichiers MAJIC s'arrêtent au périmètre de l'agglo ;
  3. **DPE tertiaire** — surface, étiquette et consommation, par adresse exacte
     puis par coordonnées.

La surface conditionne l'assujettissement Éco Énergie Tertiaire, donc toute
l'offre OPERAT. Elle est signalée comme **présomption** : le seuil de 1 000 m²
s'apprécie par site en cumulant les activités, quand un DPE ne couvre qu'un
bâtiment. La colonne sert à trier des appels, pas à affirmer une obligation.

⚠️ Données d'entreprises et de propriétaires — sortie dans `sig_agglo_data/`,
hors git.

Usage :
    python scripts/sig_agglo_classeur_tertiaire.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sig_agglo_classeur import COMMUNES_AGGLO, wgs84_vers_lambert93  # noqa: E402
from sig_agglo_classeur_local import annuaire_comptes, annuaire_couche_uf, sans_accent  # noqa: E402
from sig_agglo_classeur_total import centres_parcelles, cle_voie, ecrire, lire  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

SEUIL_EET = 1000.0


def rattacher_parcelle(
    cibles: pd.DataFrame, centres: pd.DataFrame, journal: list[dict], seuil: float
) -> pd.DataFrame:
    """Parcelle la plus proche des coordonnées de l'établissement."""

    lon = pd.to_numeric(cibles["longitude"], errors="coerce")
    lat = pd.to_numeric(cibles["latitude"], errors="coerce")
    utilisables = lon.notna() & lat.notna()
    cibles["Parcelle (id_par)"] = ""
    cibles["Parcelle — distance (m)"] = ""
    if utilisables.any():
        x, y = wgs84_vers_lambert93(lon[utilisables].to_numpy(), lat[utilisables].to_numpy())
        arbre = cKDTree(centres[["x", "y"]].to_numpy())
        distances, indices = arbre.query(np.c_[x, y], k=1)
        lignes = utilisables[utilisables].index
        garde = distances <= seuil
        cibles.loc[lignes[garde], "Parcelle (id_par)"] = centres["id_par"].to_numpy()[
            indices[garde]
        ]
        cibles.loc[lignes[garde], "Parcelle — distance (m)"] = distances[garde].round(1)
    for nom in ["Parcelle (id_par)", "Parcelle — distance (m)"]:
        journal.append(
            {"Colonne": nom, "Origine": "fond cadastral (couche 943)",
             "Rattachement": f"parcelle la plus proche (≤ {seuil:.0f} m)"}
        )
    touches = int((cibles["Parcelle (id_par)"] != "").sum())
    print(f"    parcelle rattachée : {touches} / {len(cibles)}")
    return cibles


def rattacher_proprietaire(
    cibles: pd.DataFrame, data_dir: Path, journal: list[dict]
) -> pd.DataFrame:
    """Propriétaire de la parcelle — 14 communes seulement, jamais Agde."""

    parcelles = lire(data_dir / "cadastre_description_parcelles.csv")
    parcelles = parcelles.drop_duplicates(subset=["ID_PAR"]).set_index("ID_PAR")
    comptes = lire(data_dir / "cadastre_proprietaires_comptes.csv")
    comptes["DNUPRO"] = comptes["DNUPRO"].str.strip()
    comptes = comptes.drop_duplicates(subset=["ID_COM", "DNUPRO"]).set_index(["ID_COM", "DNUPRO"])

    annuaire = annuaire_comptes(lire(data_dir / "fiche_proprietaires.csv"))
    renfort = annuaire_couche_uf(lire(data_dir / "474_agglo_s_cadastre_vmp_uf_proprietaire.csv"))
    manquants = renfort.index.difference(annuaire.index)
    annuaire = pd.concat([annuaire, renfort.loc[manquants].reindex(columns=annuaire.columns)])

    id_par = cibles["Parcelle (id_par)"]
    insee = id_par.str[:5]
    dnupro = id_par.map(parcelles["DNUPRO"]).fillna("").str.strip()
    cle = pd.MultiIndex.from_arrays([insee, dnupro])

    cibles["Propriétaire du bâtiment"] = pd.Series(
        comptes["DDENOM"].reindex(cle).to_numpy(), index=cibles.index
    ).fillna("")
    postale = annuaire.reindex(cle)
    cibles["Propriétaire — adresse"] = pd.Series(
        (postale["DLIGN4"].fillna("") + " " + postale["DLIGN6"].fillna("")).to_numpy(),
        index=cibles.index,
    ).str.strip()
    cibles["Propriétaire — connu"] = np.where(
        ~insee.isin(COMMUNES_AGGLO) & (id_par != ""),
        "Non — hors périmètre MAJIC (Agde)",
        np.where(cibles["Propriétaire du bâtiment"].str.strip() != "", "Oui", "Non"),
    )
    for nom in ["Propriétaire du bâtiment", "Propriétaire — adresse", "Propriétaire — connu"]:
        journal.append(
            {"Colonne": nom, "Origine": "cadastre MAJIC",
             "Rattachement": "par la parcelle ; 14 communes de l'agglo uniquement"}
        )
    connus = int((cibles["Propriétaire du bâtiment"].str.strip() != "").sum())
    print(f"    propriétaire du bâtiment : {connus} / {len(cibles)}")
    return cibles


TYPES_VOIE = (
    r"RUE|AVENUE|AV|BOULEVARD|BD|CHEMIN|CHE|QUAI|IMPASSE|IMP|ALLEE|ALLEES|ROUTE|RTE|"
    r"PLACE|PL|COURS|TRAVERSE|MONTEE|SENTIER|SENTE|SQUARE|ESPLANADE|PROMENADE|RESIDENCE|"
    r"LOTISSEMENT|ZONE|ZA|ZAC|ZI|PARC|VOIE|RAMPE|PASSAGE|CORNICHE|PONT|PORT|MAS|DOMAINE"
)
ADRESSE = re.compile(rf"\b(\d+)\s+(?:BIS|TER|B|A)?\s*((?:{TYPES_VOIE})\b.*)$")


def decouper_adresse(adresses: pd.Series) -> pd.DataFrame:
    """Extrait numéro et voie d'une adresse non structurée.

    L'annuaire des entreprises livre l'adresse d'un bloc, complément compris :
    « BATIPAUME VILLAGE VACANCES 20 CHEMIN RAYMOND FAGES 34300 AGDE ». Le numéro
    n'est ni au début ni seul, et la fin porte le code postal et la ville. On
    retire d'abord le code postal et ce qui suit, puis on cherche le dernier
    couple « numéro + type de voie ». Sans cela, le découpage ne rendait rien
    dans la quasi-totalité des cas.
    """

    nettoyees = (
        adresses.astype(str).str.upper().str.replace(r"\s+\d{5}\s+.*$", "", regex=True).str.strip()
    )
    return nettoyees.str.extract(ADRESSE)


def rattacher_dpe(
    cibles: pd.DataFrame, data_dir: Path, centres: pd.DataFrame,
    journal: list[dict], seuil: float
) -> pd.DataFrame:
    """DPE tertiaire : surface, étiquette, consommation — par adresse puis position."""

    chemin = data_dir / "dpe_tertiaire.csv"
    if not chemin.is_file():
        print("    [!] dpe_tertiaire.csv absent — lancer sig_agglo_dpe.py --tertiaire")
        return cibles
    dpe = lire(chemin)

    decoupe = decouper_adresse(cibles["adresse"])
    cle_etab = pd.MultiIndex.from_arrays(
        [
            cibles["code_commune"].str.strip(),
            decoupe[0].fillna("").str.lstrip("0"),
            cle_voie(decoupe[1].fillna("")),
        ]
    )
    # Une clé vide des deux côtés matcherait tout : sans ce filtre, un DPE dont
    # l'adresse n'a ni numéro ni voie se retrouvait attribué à 6 968
    # établissements. On n'apparie que des adresses réellement renseignées.
    plein = dpe.assign(
        com=dpe["code_insee_ban"].str.strip(),
        num=dpe["numero_voie_ban"].str.strip().str.lstrip("0"),
        voie=cle_voie(dpe["nom_rue_ban"]),
    )
    plein = plein[(plein["com"] != "") & (plein["num"] != "") & (plein["voie"] != "")]
    index_dpe = plein.drop_duplicates(subset=["com", "num", "voie"]).set_index(
        ["com", "num", "voie"]
    )
    cle_valide = pd.Series(
        [bool(c and n and v) for c, n, v in cle_etab], index=cibles.index
    )

    colonnes = {
        "surface_shon": "DPE — surface SHON (m²)",
        "surface_utile": "DPE — surface utile (m²)",
        "etiquette_dpe": "DPE — étiquette",
        "etiquette_ges": "DPE — étiquette GES",
        "conso_kwhep_m2_an": "DPE — conso (kWh/m²/an)",
        "secteur_activite": "DPE — secteur d'activité",
        "categorie_erp": "DPE — catégorie ERP",
        "annee_construction": "DPE — année de construction",
        "date_etablissement_dpe": "DPE — date",
    }
    for source, nom in colonnes.items():
        if source in index_dpe.columns:
            valeurs = pd.Series(
                index_dpe[source].reindex(cle_etab).to_numpy(), index=cibles.index
            ).fillna("")
            cibles[nom] = valeurs.where(cle_valide, "")
        else:
            cibles[nom] = ""
    cibles["DPE — méthode"] = np.where(
        cibles["DPE — surface SHON (m²)"].astype(str).str.strip() != "", "adresse exacte", ""
    )

    # Position, pour les établissements que l'adresse n'a pas résolus.
    reste = cibles["DPE — méthode"] == ""
    geocode = sans_accent(dpe["statut_geocodage"]).str.contains("GEOCODEE BAN A L ADRESSE", na=False)
    dx = pd.to_numeric(dpe.loc[geocode, "coordonnee_cartographique_x_ban"], errors="coerce")
    dy = pd.to_numeric(dpe.loc[geocode, "coordonnee_cartographique_y_ban"], errors="coerce")
    valides = dx.notna() & dy.notna()
    lon = pd.to_numeric(cibles.loc[reste, "longitude"], errors="coerce")
    lat = pd.to_numeric(cibles.loc[reste, "latitude"], errors="coerce")
    utilisables = lon.notna() & lat.notna()
    if valides.any() and utilisables.any():
        arbre = cKDTree(np.c_[dx[valides], dy[valides]])
        ex, ey = wgs84_vers_lambert93(lon[utilisables].to_numpy(), lat[utilisables].to_numpy())
        distances, indices = arbre.query(np.c_[ex, ey], k=1)
        lignes = utilisables[utilisables].index
        garde = distances <= seuil
        source = dpe.loc[geocode].loc[valides].iloc[indices[garde]]
        for champ, nom in colonnes.items():
            if champ in source.columns:
                cibles.loc[lignes[garde], nom] = source[champ].to_numpy()
        cibles.loc[lignes[garde], "DPE — méthode"] = f"coordonnées (≤ {seuil:.0f} m)"

    for nom in list(colonnes.values()) + ["DPE — méthode"]:
        journal.append(
            {"Colonne": nom, "Origine": "ADEME — DPE tertiaire",
             "Rattachement": "adresse exacte, sinon coordonnées"}
        )

    # Plusieurs établissements peuvent légitimement occuper le même bâtiment —
    # un immeuble de bureaux, une galerie marchande. Le DPE décrit alors le
    # bâtiment, pas l'établissement : la colonne le dit au lieu de le taire.
    signature = (
        cibles["DPE — date"].astype(str) + "|" + cibles["DPE — surface SHON (m²)"].astype(str)
    ).where(cibles["DPE — méthode"] != "", "")
    partage = signature[signature != ""].groupby(signature[signature != ""]).transform("size")
    cibles["DPE — établissements sur ce bâtiment"] = partage.reindex(cibles.index).fillna("")
    cibles["DPE — fiabilité"] = np.where(
        cibles["DPE — méthode"] == "", "",
        np.where(
            (partage.reindex(cibles.index).fillna(0) == 1)
            & (cibles["DPE — méthode"] == "adresse exacte"),
            "élevée — un seul établissement à cette adresse",
            np.where(
                cibles["DPE — méthode"] == "adresse exacte",
                "moyenne — bâtiment partagé, DPE du bâtiment",
                "faible — position approchée",
            ),
        ),
    )
    for nom in ["DPE — établissements sur ce bâtiment", "DPE — fiabilité"]:
        journal.append(
            {"Colonne": nom, "Origine": "calculé",
             "Rattachement": "compte les établissements partageant le même DPE"}
        )

    surface = pd.to_numeric(cibles["DPE — surface SHON (m²)"], errors="coerce")
    utile = pd.to_numeric(cibles["DPE — surface utile (m²)"], errors="coerce")
    retenue = surface.fillna(utile)
    cibles["Présomption Éco Énergie Tertiaire"] = np.where(
        retenue.isna(), "",
        np.where(retenue >= SEUIL_EET, "Oui — surface connue ≥ 1 000 m²", "Non — surface < 1 000 m²"),
    )
    journal.append(
        {"Colonne": "Présomption Éco Énergie Tertiaire", "Origine": "calculé",
         "Rattachement": "surface DPE ≥ 1 000 m² — présomption, le seuil s'apprécie par site"}
    )
    touches = int((cibles["DPE — méthode"] != "").sum())
    print(f"    DPE tertiaire rattaché : {touches} / {len(cibles)}")
    return cibles


def feuille_partenaires(data_dir: Path) -> pd.DataFrame:
    """Vivier de partenaires : les entreprises RGE du territoire.

    §6 du business model — la société garde la relation client et confie
    l'exécution à des spécialistes qualifiés et assurés. Le marqueur RGE est un
    filtre officiel de qualification, pas un annuaire commercial.
    """

    chemin = data_dir / "tertiaire_partenaires_rge.csv"
    if not chemin.is_file():
        print("    [!] partenaires RGE absents — lancer sig_agglo_tertiaire.py --rge")
        return pd.DataFrame()
    rge = lire(chemin)
    rge["Activité"] = np.where(
        rge["etat_administratif"].str.strip().str.upper() == "A", "Actif", "Fermé"
    )
    colonnes = [
        "nom_entreprise", "enseigne", "Activité", "naf", "libelle_naf",
        "qualifications_rge", "adresse", "commune", "tranche_effectif",
        "categorie_entreprise", "date_creation", "siret", "siren",
    ]
    return rge[[c for c in colonnes if c in rge.columns]].sort_values(
        ["Activité", "commune", "nom_entreprise"]
    )


def ecrire_trois_feuilles(
    cibles: pd.DataFrame, dictionnaire: pd.DataFrame, partenaires: pd.DataFrame, chemin: Path
) -> None:
    """Cibles, partenaires et dictionnaire dans un seul classeur."""

    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook(write_only=True)
    workbook._named_styles["Normal"].font = Font(name="Arial", size=10)
    police = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    fond = PatternFill("solid", fgColor="1F4E79")

    def feuille(titre: str, cadre: pd.DataFrame, largeur: int = 20) -> None:
        if cadre.empty:
            return
        onglet = workbook.create_sheet(titre)
        onglet.freeze_panes = "A2"
        entete = []
        for nom in cadre.columns:
            cellule = WriteOnlyCell(onglet, value=nom)
            cellule.font, cellule.fill = police, fond
            cellule.alignment = Alignment(vertical="center", wrap_text=True)
            entete.append(cellule)
        onglet.append(entete)
        for index in range(1, len(cadre.columns) + 1):
            onglet.column_dimensions[get_column_letter(index)].width = largeur
        for valeurs in cadre.itertuples(index=False, name=None):
            onglet.append(
                ["" if v is None or (isinstance(v, float) and pd.isna(v)) else v for v in valeurs]
            )
        onglet.auto_filter.ref = f"A1:{get_column_letter(len(cadre.columns))}{len(cadre) + 1}"

    feuille("Cibles tertiaires", cibles)
    feuille("Partenaires RGE", partenaires, largeur=24)
    feuille("Dictionnaire", dictionnaire, largeur=40)

    try:
        workbook.save(chemin)
    except PermissionError:
        secours = chemin.with_name(f"{chemin.stem}-nouveau{chemin.suffix}")
        workbook.save(secours)
        print(f"\n[!] {chemin.name} est ouvert dans Excel — écrit dans {secours.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Classeur des cibles tertiaires.")
    parser.add_argument("--data-dir", default="sig_agglo_data")
    parser.add_argument("--sortie", default="cibles-tertiaires-agglo.xlsx")
    parser.add_argument("--seuil", type=float, default=60.0)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    journal: list[dict] = []

    print("[1/4] lecture des établissements")
    cibles = lire(data_dir / "tertiaire_etablissements.csv")
    print(f"      {len(cibles)} établissements")
    for colonne in cibles.columns:
        journal.append(
            {"Colonne": colonne, "Origine": "API Recherche d'entreprises (data.gouv.fr)",
             "Rattachement": "source directe"}
        )

    # `etat_administratif` vaut A ou F : illisible dans un filtre Excel. La
    # colonne explicite permet de trier sans rien exclure en amont — un
    # établissement fermé signale un local vacant, donc un propriétaire à
    # démarcher.
    cibles.insert(
        0, "Activité",
        np.where(cibles["etat_administratif"].str.strip().str.upper() == "A",
                 "Actif", "Fermé"),
    )
    journal.append(
        {"Colonne": "Activité", "Origine": "API Recherche d'entreprises",
         "Rattachement": "état administratif A/F, rendu lisible"}
    )
    actifs = int((cibles["Activité"] == "Actif").sum())
    print(f"      {actifs} actifs, {len(cibles) - actifs} fermés")

    print("[2/4] rattachement à la parcelle")
    centres = centres_parcelles(data_dir)
    cibles = rattacher_parcelle(cibles, centres, journal, args.seuil)

    print("[3/4] propriétaire du bâtiment")
    cibles = rattacher_proprietaire(cibles, data_dir, journal)

    print("[4/4] DPE tertiaire")
    cibles = rattacher_dpe(cibles, data_dir, centres, journal, args.seuil)

    # Les actifs d'abord : à priorité égale, un établissement fermé n'est pas un
    # prospect, seulement l'indice d'un local vacant.
    cibles = cibles.sort_values(
        ["Activité", "priorite", "segment", "commune", "nom_entreprise"], kind="stable"
    )

    dictionnaire = pd.DataFrame(journal).drop_duplicates(subset=["Colonne"])
    remplissage = {c: int((cibles[c].astype(str).str.strip() != "").sum()) for c in cibles.columns}
    dictionnaire["Lignes remplies"] = dictionnaire["Colonne"].map(remplissage)
    dictionnaire["% rempli"] = (100 * dictionnaire["Lignes remplies"] / len(cibles)).round(1)
    dictionnaire = dictionnaire.sort_values("Lignes remplies", ascending=False)

    cible = data_dir / args.sortie
    partenaires = feuille_partenaires(data_dir)
    ecrire_trois_feuilles(cibles, dictionnaire, partenaires, cible)

    print(f"\nClasseur : {cible.resolve()}")
    print(f"  « Cibles tertiaires » : {len(cibles)} lignes × {len(cibles.columns)} colonnes")
    print(f"  « Partenaires RGE »   : {len(partenaires)} entreprises qualifiées")
    print("  « Dictionnaire »      : origine et remplissage de chaque colonne")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
