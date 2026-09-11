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


# Déclarations OPERAT relevées par commune sur le jeu ADEME
# `9uk1jf62hz215jablj6tvn71` (agrégé — l'ADEME ne publie rien de nominatif).
# Rapporté au nombre d'établissements actifs, ce ratio dit où le décret
# tertiaire est le moins appliqué, donc où les non-déclarants se concentrent.
OPERAT_COMMUNE = {
    "34301": 94, "34003": 93, "34108": 60, "34023": 24, "34213": 28,
    "34024": 15, "34150": 11, "34157": 8, "34113": 5, "34333": 5,
    "34159": 4, "34039": 0, "34143": 0, "34165": 0, "34341": 0,
}
# Secteurs où l'écart interquartile de consommation est le plus large : c'est
# là que la dispersion — donc le gisement — est la plus forte.
SEGMENTS_DISPERSES = {"Restauration", "Hôtellerie de plein air et hébergement touristique",
                      "Grandes et moyennes surfaces"}


def scorer(cibles: pd.DataFrame, data_dir: Path, journal: list[dict]) -> pd.DataFrame:
    """Note l'absence probable de pilotage technique, établissement par établissement.

    Aucun de ces signaux ne prouve quoi que ce soit isolément. Leur cumul
    désigne un propriétaire qui réunit un gisement et personne pour s'en
    occuper — ce qui est très exactement la cible.

    Les données ont tranché deux idées reçues au passage : l'âge du bâti ne
    prédit pas la consommation (médiane de 132 kWh/m² pour le bâti postérieur à
    2013 contre 151 pour l'avant-1975), et 28 % des bâtiments d'après 2005 sont
    classés D à G — sur du récent, c'est la conduite, pas l'enveloppe.
    """

    # Sur tous les locaux de la parcelle, et non les seuls locaux professionnels :
    # un hôtel ou un commerce en pied d'immeuble n'est pas toujours cadastré en
    # « local professionnel », et s'y limiter ne renseignait que 22 % des cibles.
    locaux = lire(data_dir / "fiche_locaux.csv")
    annee = pd.to_numeric(locaux["JDATAT"].str[4:8], errors="coerce")
    locaux = locaux.assign(mutation=annee.where(annee.between(1900, 2026)))
    detention = locaux.groupby("id_par")["mutation"].min()

    parc = locaux[locaux["DDENOM"].str.strip() != ""].groupby("DDENOM").size()
    proprietaire = (
        locaux[locaux["DDENOM"].str.strip() != ""]
        .drop_duplicates(subset=["id_par"]).set_index("id_par")["DDENOM"]
    )

    id_par = cibles["Parcelle (id_par)"]
    mutation = id_par.map(detention)
    cibles["Détention depuis (années)"] = (2026 - mutation).where(mutation.notna(), "")
    cibles["Parc du propriétaire (locaux)"] = (
        id_par.map(proprietaire).fillna("").map(parc).fillna("")
    )

    surface = pd.to_numeric(cibles["DPE — surface SHON (m²)"], errors="coerce")
    plancher = pd.to_numeric(
        cibles.get("Bâtiment — plancher, ordre de grandeur (m²)", pd.Series(dtype=object)),
        errors="coerce",
    ).reindex(cibles.index)
    etiquette = cibles["DPE — étiquette"].astype(str).str.strip()
    annee_dpe = pd.to_numeric(cibles["DPE — année de construction"], errors="coerce")
    nb_parc = pd.to_numeric(cibles["Parc du propriétaire (locaux)"], errors="coerce")
    creation = pd.to_numeric(cibles["date_creation"].astype(str).str[:4], errors="coerce")
    etablissements = pd.to_numeric(cibles["nombre_etablissements"], errors="coerce")
    operat = cibles["code_commune"].map(OPERAT_COMMUNE)
    actifs_commune = cibles.groupby("code_commune")["siret"].transform("size")
    densite = operat / actifs_commune.replace(0, np.nan)

    # Le score mêle deux choses assumées : des signaux de négligence, et des
    # critères de qualification. Une cible négligée qui n'est pas un vrai site
    # d'exploitation ne vaut pas un appel.
    criteres = {
        "surface > 1 000 m²": ((surface > 1000).fillna(False), 3),
        "grand bâtiment (estimé)": (
            (surface.isna() & (plancher > 1000)).fillna(False), 2
        ),
        "détention > 20 ans": (((2026 - mutation) > 20).fillna(False), 2),
        "propriétaire de 5 locaux ou plus": ((nb_parc >= 5).fillna(False), 2),
        "bâti récent mal classé": (
            ((annee_dpe >= 2005) & etiquette.isin(["D", "E", "F", "G"])).fillna(False), 2
        ),
        "établissement employeur": (cibles["caractere_employeur"].str.upper() == "O", 2),
        "segment prioritaire": (cibles["priorite"].isin(["1", "2"]), 2),
        "secteur dispersé": (cibles["segment"].isin(SEGMENTS_DISPERSES), 1),
        "entreprise installée (avant 2011)": ((creation < 2011).fillna(False), 1),
        "3 établissements ou plus": ((etablissements >= 3).fillna(False), 1),
        "commune peu déclarante": ((densite < 0.006) | densite.isna(), 1),
    }
    score = pd.Series(0, index=cibles.index)
    detail = pd.Series("", index=cibles.index)
    for nom, (masque, poids) in criteres.items():
        score = score + masque.astype(int) * poids
        detail = detail.where(~masque, (detail + " · " + nom).str.strip(" ·"))

    cibles["Score de non-pilotage"] = score
    cibles["Signaux retenus"] = detail
    cibles["Priorité d'appel"] = np.select(
        [score >= 9, score >= 7, score >= 5],
        ["1 — à appeler en premier", "2 — bonne cible", "3 — à qualifier"],
        default="4 — réserve",
    )
    for nom, origine in [
        ("Détention depuis (années)", "cadastre — date de mutation"),
        ("Parc du propriétaire (locaux)", "cadastre — locaux détenus par le propriétaire"),
        ("Score de non-pilotage", "calculé — onze signaux pondérés"),
        ("Signaux retenus", "calculé"),
        ("Priorité d'appel", "calculé — seuils 9 / 7 / 5"),
    ]:
        journal.append({"Colonne": nom, "Origine": origine, "Rattachement": "par la parcelle"})

    actifs = cibles["Activité"] == "Actif"
    print(f"    score ≥ 9 : {int((score >= 9).sum())} établissements "
          f"({int(((score >= 9) & actifs).sum())} actifs)")
    print(f"    score ≥ 7 : {int((score >= 7).sum())} "
          f"({int(((score >= 7) & actifs).sum())} actifs)")
    return cibles


def rattacher_batiment(
    cibles: pd.DataFrame, data_dir: Path, journal: list[dict], seuil: float = 40.0
) -> pd.DataFrame:
    """Bâtiment de la BD TOPO le plus proche, et surface de plancher estimée.

    Le DPE tertiaire ne couvrait que 1 480 bâtiments, d'où 168 présomptions
    d'assujettissement. La BD TOPO en porte 7 865 d'activité sur le territoire,
    dont **1 380 dépassent 1 000 m² de plancher estimé**.

    L'estimation vaut emprise au sol × nombre d'étages, avec la hauteur divisée
    par trois en repli quand les étages manquent. Elle ne remplace pas une
    surface d'activité tertiaire au sens du décret — le seuil s'apprécie par
    site en cumulant les activités, et un bâtiment peut mêler logement et
    activité. C'est un tri d'appels, pas une obligation opposable.

    Le seuil de 40 m est plus serré que pour la parcelle : un bâtiment est un
    objet précis, et un rattachement large collerait la halle voisine.
    """

    chemin = data_dir / "batiments_activite.csv"
    if not chemin.is_file():
        print("    [!] batiments_activite.csv absent — lancer sig_agglo_batiments.py")
        return cibles
    batiments = lire(chemin)
    bx = pd.to_numeric(batiments["x_l93"], errors="coerce")
    by = pd.to_numeric(batiments["y_l93"], errors="coerce")
    emprise = pd.to_numeric(batiments["emprise_m2"], errors="coerce")
    etages = pd.to_numeric(batiments["nombre_d_etages"], errors="coerce")
    hauteur = pd.to_numeric(batiments["hauteur"], errors="coerce")
    # La BD TOPO déclare parfois « 1 étage » sur un immeuble de 20 m — 953
    # bâtiments sont dans ce cas, dont le Grand Hôtel de Sète (734 m² au sol,
    # 20,5 m de haut, 1 étage annoncé). On retient la hauteur quand elle
    # contredit franchement les étages, mais **seulement sur une emprise
    # modeste** : un hangar ou une grande surface de 12 m de haut reste un
    # bâtiment d'un seul niveau, et diviser sa hauteur par trois le
    # quadruplerait à tort.
    # Deux corrections successives, la seconde venue du terrain. La hauteur de
    # la BD TOPO est mesurée au faîtage, toiture comprise : diviser par 3
    # surestimait de 75 % sur le seul cas vérifié — le Grand Hôtel de Sète,
    # 734 m² au sol et 20,5 m de haut, compte 4 niveaux réels et non 7.
    # On retranche donc environ 3 m de toiture avant de compter 4 m par niveau,
    # hauteur d'étage des bâtiments anciens du centre. Le repli ne s'applique
    # qu'aux emprises modestes : un hangar de 12 m reste un bâtiment à un seul
    # niveau. Calibrage à un seul point de mesure — l'ordre de grandeur vaut,
    # la valeur exacte non.
    immeuble = (hauteur >= 9) & (emprise <= 1500)
    niveaux = etages.where(etages >= 2)
    niveaux = niveaux.fillna(
        pd.Series(np.where(immeuble, ((hauteur - 3) / 4).round(), np.nan), index=etages.index)
    )
    niveaux = niveaux.fillna(etages).fillna(1).clip(lower=1)
    batiments = batiments.assign(plancher=(emprise * niveaux).round(), niveaux=niveaux)

    valides = bx.notna() & by.notna() & (emprise > 0)
    lon = pd.to_numeric(cibles["longitude"], errors="coerce")
    lat = pd.to_numeric(cibles["latitude"], errors="coerce")
    utilisables = lon.notna() & lat.notna()

    for nom in ["Bâtiment — usage", "Bâtiment — emprise au sol (m²)", "Bâtiment — niveaux",
                "Bâtiment — plancher, ordre de grandeur (m²)", "Bâtiment — distance (m)"]:
        cibles[nom] = ""

    if valides.any() and utilisables.any():
        arbre = cKDTree(np.c_[bx[valides], by[valides]])
        ex, ey = wgs84_vers_lambert93(lon[utilisables].to_numpy(), lat[utilisables].to_numpy())
        distances, indices = arbre.query(np.c_[ex, ey], k=1)
        lignes = utilisables[utilisables].index
        garde = distances <= seuil
        source = batiments[valides].iloc[indices[garde]]
        cibles.loc[lignes[garde], "Bâtiment — usage"] = source["usage_1"].to_numpy()
        cibles.loc[lignes[garde], "Bâtiment — emprise au sol (m²)"] = emprise[valides].to_numpy()[
            indices[garde]
        ]
        cibles.loc[lignes[garde], "Bâtiment — niveaux"] = source["niveaux"].to_numpy()
        cibles.loc[lignes[garde], "Bâtiment — plancher, ordre de grandeur (m²)"] = source[
            "plancher"
        ].to_numpy()
        cibles.loc[lignes[garde], "Bâtiment — distance (m)"] = distances[garde].round(1)

    plancher = pd.to_numeric(
        cibles["Bâtiment — plancher, ordre de grandeur (m²)"], errors="coerce"
    )
    surface_dpe = pd.to_numeric(cibles["DPE — surface SHON (m²)"], errors="coerce")
    # Contrôle sur les 7 610 établissements où DPE et estimation coexistent :
    # le ratio médian est de 3,36 et 1 390 « grands bâtiments » ont un DPE
    # inférieur à 1 000 m². L'écart n'est pas une erreur, c'est un changement
    # d'objet — le DPE mesure un LOCAL, l'estimation mesure le BÂTIMENT entier.
    # La colonne ne peut donc pas s'appeler présomption d'assujettissement :
    # elle dit que le bâtiment est grand, ce qui reste un signal de ciblage.
    occupants = cibles.groupby(
        cibles["Bâtiment — plancher, ordre de grandeur (m²)"].astype(str)
        + "|" + cibles["Bâtiment — distance (m)"].astype(str)
    )["siret"].transform("size").where(plancher.notna(), "")
    cibles["Bâtiment — établissements recensés"] = occupants
    cibles["Bâtiment — grand volume"] = np.select(
        [plancher.isna(), plancher >= SEUIL_EET],
        ["", "Oui — bâtiment de plus de 1 000 m² estimés"],
        default="Non",
    )
    cibles["Cumul tertiaire possible"] = np.where(
        (plancher >= SEUIL_EET) & (pd.to_numeric(occupants, errors="coerce") > 1),
        "À vérifier — grand bâtiment partagé, le seuil s'apprécie au cumul",
        np.where(surface_dpe.notna(), "— voir la présomption DPE, plus sûre", ""),
    )
    for nom in ["Bâtiment — usage", "Bâtiment — emprise au sol (m²)", "Bâtiment — niveaux",
                "Bâtiment — plancher, ordre de grandeur (m²)", "Bâtiment — distance (m)",
                "Bâtiment — établissements recensés", "Bâtiment — grand volume",
                "Cumul tertiaire possible"]:
        journal.append(
            {"Colonne": nom, "Origine": "BD TOPO IGN — bâtiments d'activité",
             "Rattachement": f"bâtiment le plus proche (≤ {seuil:.0f} m) ; surface estimée"}
        )
    touches = int((cibles["Bâtiment — usage"].astype(str).str.strip() != "").sum())
    larges = int((plancher >= SEUIL_EET).sum())
    print(f"    bâtiment rattaché : {touches} / {len(cibles)} — dont {larges} au-delà de 1 000 m²")
    return cibles


def feuille_appels(cibles: pd.DataFrame) -> pd.DataFrame:
    """Liste d'appels : les mieux notés, actifs, sur les segments prioritaires."""

    liste = cibles[
        (cibles["Activité"] == "Actif")
        & (cibles["priorite"].isin(["1", "2", "3"]))
        & (cibles["Score de non-pilotage"] >= 7)
    ].copy()
    colonnes = [
        "Score de non-pilotage", "Priorité d'appel", "nom_entreprise", "enseigne", "segment",
        "commune", "adresse", "tranche_effectif", "nombre_etablissements",
        "Détention depuis (années)", "Parc du propriétaire (locaux)",
        "Propriétaire du bâtiment", "DPE — surface SHON (m²)", "DPE — étiquette",
        "Présomption Éco Énergie Tertiaire", "Signaux retenus", "siret",
    ]
    return liste[[c for c in colonnes if c in liste.columns]].sort_values(
        ["Score de non-pilotage", "segment", "commune"], ascending=[False, True, True]
    )


NOM_COMMUNE = {
    "34301": "Sète", "34003": "Agde", "34108": "Frontignan", "34023": "Balaruc-les-Bains",
    "34024": "Balaruc-le-Vieux", "34039": "Bouzigues", "34113": "Gigean", "34143": "Loupian",
    "34150": "Marseillan", "34157": "Mèze", "34159": "Mireval", "34165": "Montbazin",
    "34213": "Poussan", "34333": "Vic-la-Gardiole", "34341": "Villeveyrac",
}
# Déclarations et surfaces déclarées relevées sur le jeu agrégé de l'ADEME.
OPERAT_SURFACE = {
    "34301": 348392, "34003": 206264, "34108": 129169, "34023": 56022, "34213": 23751,
    "34024": 24394, "34150": 30996, "34157": 16476, "34113": 14919, "34333": 9586,
    "34159": 8341, "34039": 0, "34143": 0, "34165": 0, "34341": 0,
}
# Usages de la BD TOPO qui relèvent du champ tertiaire du décret.
USAGES_TERTIAIRES = {"Commercial et services", "Sportif", "Religieux"}


def feuille_operat(cibles: pd.DataFrame, data_dir: Path) -> pd.DataFrame:
    """Couverture du décret tertiaire, commune par commune.

    L'ADEME ne publie rien de nominatif : impossible de nommer un non-déclarant.
    Mais en rapportant les surfaces déclarées au parc de bâtiments d'activité de
    plus de 1 000 m², on obtient un **taux de couverture** qui dit où le décret
    passe à la trappe.

    À lire en relatif, jamais en absolu&nbsp;: Balaruc-les-Bains dépasse 100 %,
    preuve que l'estimation sous-estime autant qu'elle surestime. C'est l'écart
    entre communes à parc comparable qui porte l'information.
    """

    chemin = data_dir / "batiments_activite.csv"
    if not chemin.is_file():
        return pd.DataFrame()
    batiments = lire(chemin)
    x = pd.to_numeric(batiments["x_l93"], errors="coerce")
    y = pd.to_numeric(batiments["y_l93"], errors="coerce")
    emprise = pd.to_numeric(batiments["emprise_m2"], errors="coerce")
    etages = pd.to_numeric(batiments["nombre_d_etages"], errors="coerce")
    hauteur = pd.to_numeric(batiments["hauteur"], errors="coerce")
    # La BD TOPO déclare parfois « 1 étage » sur un immeuble de 20 m — 953
    # bâtiments sont dans ce cas, dont le Grand Hôtel de Sète (734 m² au sol,
    # 20,5 m de haut, 1 étage annoncé). On retient la hauteur quand elle
    # contredit franchement les étages, mais **seulement sur une emprise
    # modeste** : un hangar ou une grande surface de 12 m de haut reste un
    # bâtiment d'un seul niveau, et diviser sa hauteur par trois le
    # quadruplerait à tort.
    # Deux corrections successives, la seconde venue du terrain. La hauteur de
    # la BD TOPO est mesurée au faîtage, toiture comprise : diviser par 3
    # surestimait de 75 % sur le seul cas vérifié — le Grand Hôtel de Sète,
    # 734 m² au sol et 20,5 m de haut, compte 4 niveaux réels et non 7.
    # On retranche donc environ 3 m de toiture avant de compter 4 m par niveau,
    # hauteur d'étage des bâtiments anciens du centre. Le repli ne s'applique
    # qu'aux emprises modestes : un hangar de 12 m reste un bâtiment à un seul
    # niveau. Calibrage à un seul point de mesure — l'ordre de grandeur vaut,
    # la valeur exacte non.
    immeuble = (hauteur >= 9) & (emprise <= 1500)
    niveaux = etages.where(etages >= 2)
    niveaux = niveaux.fillna(
        pd.Series(np.where(immeuble, ((hauteur - 3) / 4).round(), np.nan), index=etages.index)
    )
    niveaux = niveaux.fillna(etages).fillna(1).clip(lower=1)
    batiments = batiments.assign(plancher=emprise * niveaux, x=x, y=y)

    centres = centres_parcelles(data_dir)
    utilisables = batiments["x"].notna() & batiments["y"].notna()
    arbre = cKDTree(centres[["x", "y"]].to_numpy())
    _, indices = arbre.query(np.c_[batiments.loc[utilisables, "x"],
                                   batiments.loc[utilisables, "y"]], k=1)
    batiments.loc[utilisables, "insee"] = pd.Series(
        centres["id_par"].to_numpy()[indices], index=batiments.index[utilisables]
    ).str[:5]

    grands = batiments[
        batiments["usage_1"].isin(USAGES_TERTIAIRES)
        & (batiments["plancher"] >= SEUIL_EET)
        & batiments["insee"].notna()
    ]
    parc = grands.groupby("insee").agg(batiments=("plancher", "size"),
                                       surface=("plancher", "sum"))

    actifs = cibles[cibles["Activité"] == "Actif"].groupby("code_commune").size()
    appels = cibles[
        (cibles["Activité"] == "Actif") & (cibles["Score de non-pilotage"] >= 7)
    ].groupby("code_commune").size()

    lignes = []
    for insee, nom in NOM_COMMUNE.items():
        surface_estimee = int(parc["surface"].get(insee, 0))
        declaree = OPERAT_SURFACE.get(insee, 0)
        lignes.append({
            "Commune": nom,
            "Code INSEE": insee,
            "Bâtiments d'activité > 1 000 m² (estimés)": int(parc["batiments"].get(insee, 0)),
            "Surface tertiaire estimée (m²)": surface_estimee,
            "Surface déclarée à OPERAT (m²)": declaree,
            "Taux de couverture (%)": (
                round(100 * declaree / surface_estimee) if surface_estimee else ""
            ),
            "Surface non déclarée (m²)": max(surface_estimee - declaree, 0),
            "Établissements actifs": int(actifs.get(insee, 0)),
            "Cibles notées 7 et plus": int(appels.get(insee, 0)),
        })
    tableau = pd.DataFrame(lignes)
    return tableau.sort_values("Surface non déclarée (m²)", ascending=False)


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


def ecrire_classeur(
    cibles: pd.DataFrame, dictionnaire: pd.DataFrame, partenaires: pd.DataFrame,
    appels: pd.DataFrame, operat: pd.DataFrame, chemin: Path
) -> None:
    """Liste d'appels, cibles, partenaires et dictionnaire dans un seul classeur."""

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

    feuille("Liste d'appels", appels, largeur=22)
    feuille("Décret tertiaire", operat, largeur=20)
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

    print("[4/6] DPE tertiaire")
    cibles = rattacher_dpe(cibles, data_dir, centres, journal, args.seuil)

    print("[5/6] bâtiment et surface estimée")
    cibles = rattacher_batiment(cibles, data_dir, journal)

    print("[6/6] score de non-pilotage")
    cibles = scorer(cibles, data_dir, journal)

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
    appels = feuille_appels(cibles)
    operat = feuille_operat(cibles, data_dir)
    ecrire_classeur(cibles, dictionnaire, partenaires, appels, operat, cible)

    print(f"\nClasseur : {cible.resolve()}")
    print(f"  « Liste d'appels »    : {len(appels)} cibles notées 7 et plus")
    print(f"  « Décret tertiaire »  : couverture OPERAT des {len(operat)} communes")
    print(f"  « Cibles tertiaires » : {len(cibles)} lignes × {len(cibles.columns)} colonnes")
    print(f"  « Partenaires RGE »   : {len(partenaires)} entreprises qualifiées")
    print("  « Dictionnaire »      : origine et remplissage de chaque colonne")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
