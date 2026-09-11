"""Classeur unique du cadastre à la maille LOCAL — une ligne par logement.

`sig_agglo_classeur.py` s'arrête à la parcelle : en copropriété, il ne voit que
le syndicat. Ce script-ci part des 176 695 locaux du module MAJIC et rattache à
chacun son propriétaire, l'adresse du bien et l'adresse du propriétaire.

Ce que la source permet, et ce qu'elle interdit (mesuré le 2026-09-08, détail
dans `docs/refonte-v1/sig-agglo-proprietaires-decisions.md` §6) :

  - le **nom** du propriétaire est connu pour 98,2 % des locaux ;
  - son **adresse postale** ne l'est que pour ~45 %. La fiche d'une parcelle en
    copropriété ne donne l'adresse que du syndicat ; celle de chaque appartement
    vit derrière `cadastre/fichedescriptiveinvariant`, que le compte n'a pas le
    privilège d'appeler. La colonne « Adresse propriétaire — connue » dit
    lesquels, plutôt que de laisser croire à un fichier complet ;
  - **aucune surface de local n'existe** dans la source : la seule contenance
    est celle de la parcelle.

L'adresse du bien est cadastrale et exacte, mais **à la maille parcelle** : les
1 480 appartements d'une résidence portent la même. La BAN sert seulement à
confirmer la voie et à donner le code postal.

⚠️ Données personnelles (noms, adresses de personnes physiques). La sortie reste
dans `sig_agglo_data/`, protégé de git par son propre `.gitignore`.

Usage :
    python scripts/sig_agglo_classeur_local.py
    python scripts/sig_agglo_classeur_local.py --sortie locaux-agglo.xlsx
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sig_agglo_classeur import COMMUNES_AGGLO, ecrire, normaliser_voie  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

FICHIERS = {
    "locaux": "cadastre_locaux.csv",
    "fiches": "fiche_locaux.csv",
    "parcelles": "cadastre_description_parcelles.csv",
    "comptes": "cadastre_proprietaires_comptes.csv",
    "proprietaires": "fiche_proprietaires.csv",
    "ban": "397_referentiels_vmp_ban.csv",
    "uf": "474_agglo_s_cadastre_vmp_uf_proprietaire.csv",
}


def charger(data_dir: Path, cle: str) -> pd.DataFrame:
    chemin = data_dir / FICHIERS[cle]
    if not chemin.is_file():
        raise SystemExit(f"Fichier manquant : {chemin}\nLancer d'abord sig_agglo_cadastre.py.")
    return pd.read_csv(chemin, dtype=str, encoding="utf-8-sig", low_memory=False).fillna("")


def sans_accent(serie: pd.Series) -> pd.Series:
    """Aligne les graphies : la BAN écrit « Balaruc-le-Vieux », MAJIC « BALARUC LE VIEUX »."""

    return (
        serie.map(lambda v: unicodedata.normalize("NFKD", v).encode("ascii", "ignore").decode())
        .str.upper()
        .str.replace(r"[^A-Z0-9]+", " ", regex=True)
        .str.strip()
    )


def date_majic(serie: pd.Series) -> pd.Series:
    """`31032017` → `31/03/2017`. Les dates absentes sont des espaces, pas du vide."""

    net = serie.str.strip()
    valide = net.str.fullmatch(r"\d{8}")
    return net.where(~valide, net.str[:2] + "/" + net.str[2:4] + "/" + net.str[4:]).where(valide, "")


def adresse_bien(parcelles: pd.DataFrame) -> pd.Series:
    """`0038` + `B` + `RUE` + `DUNOIS` → `38 B RUE DUNOIS`."""

    numero = parcelles["DNVOIRI"].map(normaliser_voie)
    morceaux = [numero, parcelles["DINDIC"], parcelles["L_NATURE_VOIE"], parcelles["DVOILIB"]]
    assemble = pd.Series("", index=parcelles.index)
    for morceau in morceaux:
        assemble = (assemble + " " + morceau.str.strip()).str.strip()
    return assemble.str.replace(r"\s+", " ", regex=True)


def annuaire_comptes(proprietaires: pd.DataFrame) -> pd.DataFrame:
    """Adresse postale par compte, reconstituée depuis les fiches de parcelle.

    Un compte qui possède une parcelle en propre quelque part y a son adresse
    complète. On la réutilise pour tous ses locaux, y compris ceux que la fiche
    de copropriété ne détaille pas. Couverture mesurée : ~45 % des locaux.
    """

    adresses = proprietaires[
        (proprietaires["DLIGN4"].str.strip() != "") | (proprietaires["DLIGN6"].str.strip() != "")
    ].copy()
    adresses["ID_COM"] = adresses["id_par"].str[:5]
    adresses["DNUPRO"] = adresses["DNUPRO"].str.strip()
    return (
        adresses.drop_duplicates(subset=["ID_COM", "DNUPRO"])
        .set_index(["ID_COM", "DNUPRO"])[["DLIGN3", "DLIGN4", "DLIGN6", "DDENOM", "L_CCODRO"]]
    )


def annuaire_couche_uf(uf: pd.DataFrame) -> pd.DataFrame:
    """Second annuaire, tiré de la couche SIG 474 « Propriétaire parcelle ».

    Même nature que le précédent — des comptes propriétaires de parcelles — mais
    constitué autrement, et il apporte 1 398 comptes que les fiches n'avaient
    pas. Gain mesuré : +1,1 point de couverture. Modeste, mais gratuit.
    """

    adresses = uf[(uf["dlign4"].str.strip() != "") | (uf["dlign6"].str.strip() != "")].copy()
    adresses["DNUPRO"] = adresses["dnupro"].str.strip()
    return (
        adresses.drop_duplicates(subset=["id_com", "DNUPRO"])
        .set_index(["id_com", "DNUPRO"])[["dlign3", "dlign4", "dlign6", "ddenom"]]
        .rename(
            columns={
                "dlign3": "DLIGN3",
                "dlign4": "DLIGN4",
                "dlign6": "DLIGN6",
                "ddenom": "DDENOM",
            }
        )
    )


def codes_postaux_ban(ban: pd.DataFrame) -> pd.Series:
    """Code postal par (commune, voie)."""

    ban = ban.copy()
    ban["cle_com"] = sans_accent(ban["nom_commune"])
    ban["cle_voie"] = sans_accent(ban["nom_voie"])
    return (
        ban.drop_duplicates(subset=["cle_com", "cle_voie"])
        .set_index(["cle_com", "cle_voie"])["code_postal"]
    )


def hors_agglo(ligne6: pd.Series, communes: set[str]) -> pd.Series:
    """Le propriétaire habite-t-il hors des 14 communes de l'agglo ?

    Le code postal ne peut pas servir d'arbitre : le référentiel d'adresses du
    SIG couvre 27 communes, dont Agde, Pézenas ou Fabrègues qui ne sont pas dans
    l'agglo. Les classer « dedans » parce que leur code postal figure au
    référentiel faussait la colonne qui sert justement à repérer les
    propriétaires non résidents. On compare donc les noms de communes.
    """

    nom = sans_accent(ligne6.astype(str).str.replace(r"^\d{5}\s*", "", regex=True))
    return nom.map(
        lambda valeur: ""
        if not valeur.strip()
        else ("Non" if any(valeur.startswith(c) for c in communes) else "Oui")
    )


def construire(data_dir: Path) -> pd.DataFrame:
    print("[1/5] lecture des locaux et des fiches")
    locaux = charger(data_dir, "locaux").drop_duplicates(subset=["INVAR"])
    locaux = locaux[locaux["ID_COM"].isin(COMMUNES_AGGLO)]
    fiches = charger(data_dir, "fiches").drop_duplicates(subset=["INVAR"]).set_index("INVAR")
    print(f"      {len(locaux)} locaux, {len(fiches)} détaillés par une fiche")

    print("[2/5] adresse du bien et contenance, par parcelle")
    parcelles = charger(data_dir, "parcelles").drop_duplicates(subset=["ID_PAR"]).set_index("ID_PAR")
    parcelles["adresse"] = adresse_bien(parcelles)
    # MAJIC range le type de voie à part (`RUE` dans L_NATURE_VOIE, `DUNOIS` dans
    # DVOILIB) là où la BAN écrit « Rue Dunois » d'un seul tenant : sans les
    # recoller, aucun rapprochement ne sort.
    parcelles["cle_voie"] = sans_accent(
        (parcelles["L_NATURE_VOIE"].str.strip() + " " + parcelles["DVOILIB"].str.strip()).str.strip()
    )
    parcelles["cle_voie_courte"] = sans_accent(parcelles["DVOILIB"])

    print("[3/5] propriétaires : nom par compte, adresse quand elle existe")
    comptes = charger(data_dir, "comptes")
    comptes["DNUPRO"] = comptes["DNUPRO"].str.strip()
    comptes = comptes.drop_duplicates(subset=["ID_COM", "DNUPRO"]).set_index(["ID_COM", "DNUPRO"])
    annuaire = annuaire_comptes(charger(data_dir, "proprietaires"))
    renfort = annuaire_couche_uf(charger(data_dir, "uf"))
    manquants = renfort.index.difference(annuaire.index)
    annuaire = pd.concat([annuaire, renfort.loc[manquants].reindex(columns=annuaire.columns)])
    print(f"      {len(annuaire)} comptes adressés, dont {len(manquants)} venus de la couche 474")

    print("[4/5] assemblage")
    cle_compte = pd.MultiIndex.from_arrays(
        [locaux["ID_COM"], locaux["DNUPRO"].str.strip()]
    )
    nom_fiche = locaux["INVAR"].map(fiches["DDENOM"])
    nom_compte = pd.Series(comptes["DDENOM"].reindex(cle_compte).to_numpy(), index=locaux.index)
    postale = annuaire.reindex(cle_compte)

    nom_commune = comptes.reset_index().groupby("ID_COM")["COMMUNE"].first()
    communes_agglo = set(sans_accent(pd.Series(nom_commune.loc[list(COMMUNES_AGGLO)].unique())))
    ban = codes_postaux_ban(charger(data_dir, "ban"))
    commune_norm = sans_accent(locaux["ID_COM"].map(nom_commune).fillna(""))

    def cp_par_voie(colonne: str) -> pd.Series:
        cle = pd.MultiIndex.from_arrays(
            [commune_norm, locaux["ID_PAR"].map(parcelles[colonne]).fillna("")]
        )
        return pd.Series(ban.reindex(cle).to_numpy(), index=locaux.index)

    code_postal = cp_par_voie("cle_voie").fillna(cp_par_voie("cle_voie_courte")).fillna("")

    # Un compte peut posséder plusieurs locaux sur la parcelle ; la copropriété
    # se lit au nombre de comptes distincts, pas au nombre de locaux.
    comptes_par_parcelle = locaux.groupby("ID_PAR")["DNUPRO"].nunique()

    ligne6 = postale["DLIGN6"].fillna("").to_numpy()
    non_resident = hors_agglo(pd.Series(ligne6, index=locaux.index), communes_agglo)

    # `.map` laisse un NaN pour une parcelle absente, et `NaN != ""` est vrai :
    # sans ce fillna, tout local passerait pour adressé.
    adresse = locaux["ID_PAR"].map(parcelles["adresse"]).fillna("")

    classeur = pd.DataFrame(
        {
            "Commune": locaux["ID_COM"].map(nom_commune),
            "Code INSEE": locaux["ID_COM"],
            "Réf. cadastrale (id_par)": locaux["ID_PAR"],
            "Section": locaux["CCOSEC"],
            "Parcelle": locaux["DNUPLA"],
            "Invariant": locaux["INVAR"],
            "Adresse du bien": adresse,
            "Code postal": code_postal,
            "Source adresse du bien": pd.Series(
                "Exacte (cadastre)", index=locaux.index
            ).where(adresse.str.strip() != "", "Non trouvée"),
            "Type de local": locaux["INVAR"].map(fiches["L_DTELOC"]),
            "Nature": locaux["INVAR"].map(fiches["L_CCONLC"]),
            "Occupation": locaux["INVAR"].map(fiches["L_DNATLC"]),
            "Année de construction": locaux["INVAR"].map(fiches["JANNAT"]).fillna("").str.strip(),
            "Date de mutation": date_majic(locaux["INVAR"].map(fiches["JDATAT"]).fillna("")),
            "Propriétaire": nom_fiche.fillna("").where(
                nom_fiche.fillna("").str.strip() != "", nom_compte
            ),
            "N° de compte": locaux["DNUPRO"].str.strip(),
            "Droit": pd.Series(postale["L_CCODRO"].to_numpy(), index=locaux.index),
            "Prop. — complément": pd.Series(postale["DLIGN3"].to_numpy(), index=locaux.index),
            "Prop. — n° et voie": pd.Series(
                postale["DLIGN4"].fillna("").to_numpy(), index=locaux.index
            ).map(normaliser_voie),
            "Prop. — commune": pd.Series(ligne6, index=locaux.index),
            "Adresse propriétaire — connue": pd.Series(
                postale["DLIGN4"].notna().to_numpy(), index=locaux.index
            ).map({True: "Oui", False: "Non"}),
            "Propriétaire hors agglo": non_resident,
            "Copropriété": locaux["ID_PAR"]
            .map(comptes_par_parcelle)
            .map(lambda n: "Oui" if n and n > 1 else "Non"),
            "Comptes sur la parcelle": locaux["ID_PAR"].map(comptes_par_parcelle),
            "Contenance parcelle (m²)": pd.to_numeric(
                locaux["ID_PAR"].map(parcelles["DCNTPA"]), errors="coerce"
            ),
        }
    )
    return classeur.fillna("").sort_values(["Commune", "Adresse du bien", "Invariant"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Classeur du cadastre à la maille local.")
    parser.add_argument("--data-dir", default="sig_agglo_data", help="dossier des extractions")
    parser.add_argument("--sortie", default="locaux-agglo.xlsx", help="nom du classeur produit")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    classeur = construire(data_dir)
    code = ecrire(classeur, data_dir, args.sortie, "Locaux agglo")

    connue = int((classeur["Adresse propriétaire — connue"] == "Oui").sum())
    nomme = int((classeur["Propriétaire"].str.strip() != "").sum())
    total = len(classeur)
    print(f"  propriétaire nommé : {nomme} ({nomme / total:.1%})")
    print(f"  adresse postale du propriétaire : {connue} ({connue / total:.1%})")
    print("  le reste est en copropriété — adresse verrouillée par un privilège SIG")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
