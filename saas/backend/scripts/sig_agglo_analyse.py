"""Analyse des données foncières extraites du SIG de l'agglo.

Troisième temps, après `sig_agglo_recon.py` (ce qui existe) et
`sig_agglo_extract.py` (récupération) : ce script lit les CSV extraits et produit
un rapport lisible — qui possède quoi, où, en quelle quantité, et avec quelle
qualité de rattachement au cadastre.

Il ne touche pas au réseau : il travaille sur le dossier d'extraction, qui est
déjà protégé de git par son propre `.gitignore`. Le rapport est écrit **dans ce
même dossier**, parce qu'il dérive de données personnelles.

Par défaut, les classements nomment les **personnes morales** (communes, État,
bailleurs, SCI, sociétés) et agrègent les **personnes physiques** sans les nommer :
un rapport de synthèse n'a pas besoin de désigner des particuliers pour être
exploitable. `--noms-particuliers` lève cette réserve si le besoin le justifie ;
les CSV extraits contiennent de toute façon la donnée complète.

Usage :
    python scripts/sig_agglo_analyse.py [--data sig_agglo_data] [--noms-particuliers]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

FICHIERS = {
    "proprietaires": "474_agglo_s_cadastre_vmp_uf_proprietaire.csv",
    "parcelles": "943_agglo_s_cadastre_vmap_fond_cadastral_parcelle.csv",
    "public": "317_foncier_vmp_foncier_public.csv",
    "unites": "532_s_cadastre_v_vmap_unite_fonciere.csv",
}


def charger(data_dir: Path, cle: str) -> pd.DataFrame:
    chemin = data_dir / FICHIERS[cle]
    if not chemin.is_file():
        raise SystemExit(f"Fichier manquant : {chemin}\nLancer d'abord sig_agglo_extract.py.")
    return pd.read_csv(chemin, dtype=str, encoding="utf-8-sig", low_memory=False)


def nombre(valeur: object) -> str:
    """Formate un entier à la française (espace insécable fine comme séparateur)."""

    try:
        return f"{int(valeur):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(valeur)


def surface(m2: float) -> str:
    if m2 >= 1_000_000:
        return f"{m2 / 1_000_000:.1f} km²"
    return f"{nombre(round(m2))} m²"


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyse des données foncières extraites.")
    parser.add_argument("--data", default="sig_agglo_data", help="dossier d'extraction")
    parser.add_argument(
        "--noms-particuliers",
        action="store_true",
        help="nomme aussi les personnes physiques dans les classements",
    )
    args = parser.parse_args()

    data_dir = Path(args.data)
    proprios = charger(data_dir, "proprietaires")
    parcelles = charger(data_dir, "parcelles")
    public = charger(data_dir, "public")

    # --- Préparation ------------------------------------------------------- #
    # `id_uf` porte en réalité un identifiant de parcelle : c'est ce qui rend la
    # jointure au cadastre possible directement, sans passer par l'unité foncière.
    proprios = proprios.rename(columns={"id_uf": "id_par"})
    proprios["ddenom"] = proprios["ddenom"].fillna("").str.strip()
    parcelles["sup_m2_num"] = pd.to_numeric(parcelles["sup_m2"], errors="coerce")
    # Le fond cadastral sert plusieurs symbologies : un même `id_par` y revient
    # plusieurs fois. Sans dédoublonnage, la jointure gonfle les lignes et compte
    # deux fois la surface.
    parcelles = parcelles.drop_duplicates("id_par")
    communes = (
        parcelles[["id_com", "commune"]].dropna().drop_duplicates("id_com").set_index("id_com")["commune"]
    )

    # Personne morale = pas de civilité (les particuliers sont M ou MME).
    proprios["morale"] = ~proprios["dqualp"].fillna("").str.strip().isin(["M", "MME"])
    jointes = proprios.merge(
        parcelles[["id_par", "sup_m2_num", "commune", "section", "parcelle"]],
        on="id_par",
        how="left",
    )
    rattachees = jointes["sup_m2_num"].notna()

    out: list[str] = []
    add = out.append

    add("# Analyse du foncier de l'agglo — qui possède quoi")
    add("")
    add(f"> Généré par `scripts/sig_agglo_analyse.py` depuis `{data_dir}`.")
    add("> Source : SIG Sète Agglopôle Méditerranée (fichiers fonciers DGFiP/MAJIC).")
    add("> **Document dérivé de données personnelles — ne pas diffuser.**")
    add("")

    # --- 1. Volumétrie ------------------------------------------------------ #
    add("## 1. Le gisement")
    add("")
    add("| Objet | Volume |")
    add("| --- | ---: |")
    add(f"| Lignes propriétaire (parcelle × titulaire) | {nombre(len(proprios))} |")
    add(f"| Parcelles cadastrales | {nombre(len(parcelles))} |")
    add(f"| Propriétaires distincts (`dnuper`) | {nombre(proprios['dnuper'].nunique())} |")
    add(f"| Comptes communaux distincts (`dnupro`) | {nombre(proprios['dnupro'].nunique())} |")
    add(f"| Communes couvertes | {proprios['id_com'].nunique()} |")
    add(f"| Parcelles du foncier public | {nombre(len(public))} |")
    add("")

    # --- 2. Qualité de la jointure ------------------------------------------ #
    taux = 100 * rattachees.mean()
    add("## 2. Rattachement au cadastre")
    add("")
    add(
        f"**{nombre(int(rattachees.sum()))} lignes sur {nombre(len(jointes))} "
        f"({taux:.1f} %)** se rattachent directement à une parcelle du cadastre : "
        "`id_uf` porte un identifiant de parcelle."
    )
    add("")
    orphelines = len(jointes) - int(rattachees.sum())
    if orphelines:
        add(
            f"Les {nombre(orphelines)} lignes restantes désignent des unités foncières "
            "sans parcelle correspondante dans le fond cadastral (parcelles disparues, "
            "remembrements, décalage de millésime) — à traiter comme un reste à qualifier, "
            "pas comme une erreur."
        )
        add("")
    # Le fond cadastral déborde du territoire : il embarque les communes limitrophes.
    # Rapporter la couverture à ses 170 000 parcelles donnerait un taux faussement bas.
    communes_majic = set(proprios["id_com"].dropna())
    dans_agglo = parcelles[parcelles["id_com"].isin(communes_majic)]
    couvertes = dans_agglo["id_par"].isin(proprios["id_par"]).sum()
    add(
        f"Vu dans l'autre sens, et **en ramenant au bon périmètre** : le fond cadastral "
        f"couvre {parcelles['id_com'].nunique()} communes ({nombre(len(parcelles))} parcelles), "
        f"soit les {len(communes_majic)} de l'agglo **plus les limitrophes**. Dans les seules "
        f"communes de l'agglo, **{nombre(couvertes)} parcelles sur {nombre(len(dans_agglo))} "
        f"({100 * couvertes / len(dans_agglo):.1f} %)** ont un propriétaire directement rattaché."
    )
    add("")

    # --- 3. Qui possède ----------------------------------------------------- #
    morales = int(proprios["morale"].sum())
    physiques = len(proprios) - morales
    add("## 3. Personnes physiques et personnes morales")
    add("")
    add("| Type | Lignes | Part |")
    add("| --- | ---: | ---: |")
    add(f"| Personnes physiques (civilité M / MME) | {nombre(physiques)} | {100 * physiques / len(proprios):.0f} % |")
    add(f"| Personnes morales (sociétés, collectivités, SCI…) | {nombre(morales)} | {100 * morales / len(proprios):.0f} % |")
    add("")
    surf_morale = jointes.loc[jointes["morale"], "sup_m2_num"].sum()
    surf_physique = jointes.loc[~jointes["morale"], "sup_m2_num"].sum()
    total_surf = surf_morale + surf_physique
    if total_surf:
        part_lignes = 100 * morales / len(proprios)
        part_surface = 100 * surf_morale / total_surf
        add(
            f"En surface, les personnes morales détiennent **{surface(surf_morale)}** "
            f"({part_surface:.0f} %) contre {surface(surf_physique)} pour les particuliers : "
            f"{part_lignes:.0f} % des lignes mais {part_surface:.0f} % du terrain, soit "
            f"**{part_surface / part_lignes:.1f} fois plus de surface par ligne**. "
            "Moins nombreuses, elles possèdent plus grand."
        )
        add("")

    # --- 4. Par commune ----------------------------------------------------- #
    add("## 4. Répartition par commune")
    add("")
    par_commune = (
        jointes.groupby("id_com")
        .agg(
            lignes=("id_par", "size"),
            morales=("morale", "sum"),
            surface_m2=("sup_m2_num", "sum"),
        )
        .sort_values("lignes", ascending=False)
    )
    add("| Commune | Lignes propriétaire | dont morales | Surface rattachée |")
    add("| --- | ---: | ---: | ---: |")
    for id_com, ligne in par_commune.iterrows():
        nom = communes.get(id_com, id_com)
        add(
            f"| {nom} ({id_com}) | {nombre(ligne['lignes'])} | "
            f"{nombre(int(ligne['morales']))} | {surface(ligne['surface_m2'])} |"
        )
    add("")

    # --- 5. Concentration --------------------------------------------------- #
    add("## 5. Les plus gros propriétaires")
    add("")
    if args.noms_particuliers:
        base = jointes
        note = "Classement toutes personnes confondues."
    else:
        base = jointes[jointes["morale"]]
        note = (
            "Classement limité aux **personnes morales**. Les particuliers sont agrégés "
            "plus bas ; `--noms-particuliers` les fait apparaître nommément."
        )
    add(note)
    add("")
    top = (
        base.groupby("ddenom")
        .agg(parcelles=("id_par", "nunique"), surface_m2=("sup_m2_num", "sum"))
        .sort_values("surface_m2", ascending=False)
        .head(25)
    )
    add("| Propriétaire | Parcelles | Surface |")
    add("| --- | ---: | ---: |")
    for nom, ligne in top.iterrows():
        add(f"| {nom} | {nombre(ligne['parcelles'])} | {surface(ligne['surface_m2'])} |")
    add("")

    multi = jointes.groupby("dnuper")["id_par"].nunique()
    add(
        f"Concentration : {nombre(int((multi > 5).sum()))} propriétaires détiennent plus de "
        f"5 parcelles, {nombre(int((multi > 20).sum()))} en détiennent plus de 20, sur "
        f"{nombre(len(multi))} propriétaires distincts."
    )
    add("")

    # --- 6. Propriétaires hors territoire ----------------------------------- #
    cp = proprios["dlign6"].fillna("").str.strip().str.slice(0, 2)
    hors = cp[(cp != "") & (cp != "34")]
    add("## 6. Propriétaires domiciliés hors de l'Hérault")
    add("")
    add(
        f"**{nombre(len(hors))} lignes sur {nombre(int((cp != '').sum()))}** "
        f"({100 * len(hors) / max(int((cp != '').sum()), 1):.0f} %) ont une adresse "
        "hors du département — résidences secondaires, sociétés extérieures, héritiers."
    )
    add("")
    add("| Département de résidence | Lignes |")
    add("| --- | ---: |")
    for dep, valeur in hors.value_counts().head(10).items():
        add(f"| {dep} | {nombre(valeur)} |")
    add("")

    # --- 7. Le foncier public ----------------------------------------------- #
    add("## 7. Le foncier public")
    add("")
    public["surfcad_num"] = pd.to_numeric(public["surfcad_m2"], errors="coerce")
    add("| Type de propriétaire public | Parcelles | Surface |")
    add("| --- | ---: | ---: |")
    for type_, groupe in (
        public.groupby("type").agg(n=("id_par", "nunique"), s=("surfcad_num", "sum")).sort_values("s", ascending=False).iterrows()
    ):
        add(f"| {type_} | {nombre(groupe['n'])} | {surface(groupe['s'])} |")
    add("")
    add("Nature du droit détenu (`l_ccodro`) :")
    add("")
    add("| Droit | Lignes |")
    add("| --- | ---: |")
    for droit, valeur in public["l_ccodro"].value_counts().head(8).items():
        add(f"| {droit} | {nombre(valeur)} |")
    add("")

    # --- 8. Ce que possède la Ville de Sète --------------------------------- #
    ville = public[public["ddenom"].fillna("").str.contains("SETE|SÈTE", case=False, regex=True)]
    if not ville.empty:
        add("## 8. Ce qui porte le nom de Sète dans le foncier public")
        add("")
        add("| Propriétaire | Parcelles | Surface |")
        add("| --- | ---: | ---: |")
        detail = (
            ville.groupby("ddenom")
            .agg(n=("id_par", "nunique"), s=("surfcad_num", "sum"))
            .sort_values("s", ascending=False)
            .head(15)
        )
        for nom, ligne in detail.iterrows():
            add(f"| {nom} | {nombre(ligne['n'])} | {surface(ligne['s'])} |")
        add("")
        add(
            f"Total : **{nombre(ville['id_par'].nunique())} parcelles** pour "
            f"{surface(ville['surfcad_num'].sum())}. C'est le point de comparaison "
            "direct avec les bâtiments déjà connus de Po2."
        )
        add("")

    # --- 9. Limites ---------------------------------------------------------- #
    unites = charger(data_dir, "unites")
    unites["nb"] = pd.to_numeric(unites["nb_parcelles"], errors="coerce")
    groupees = int((unites["nb"] > 1).sum())
    add("## 9. Limites, et ce qui reste à gagner")
    add("")
    add(
        f"La couche propriétaire est à la maille **unité foncière**, pas parcelle : "
        f"{nombre(len(unites))} unités regroupent {nombre(int(unites['nb'].sum()))} parcelles, "
        f"dont {nombre(groupees)} unités en contiennent plusieurs (jusqu'à "
        f"{int(unites['nb'].max())}). Seule la parcelle « tête » d'unité porte l'identifiant "
        "exploitable — c'est ce qui explique l'écart entre les "
        f"{nombre(couvertes)} parcelles directement rattachées et les "
        f"{nombre(int(unites['nb'].sum()))} réellement couvertes par un propriétaire."
    )
    add("")
    add(
        "**Prochaine étape pour combler l'écart** : rattacher les parcelles secondaires "
        "d'une unité foncière à son propriétaire. Deux voies — le compte communal "
        "(`id_dnupro`, présent des deux côtés) ou l'intersection géométrique (extraction "
        "avec `--avec-geom`). La première est à tenter d'abord : elle ne coûte qu'une jointure."
    )
    add("")

    rapport = data_dir / "rapport-proprietaires.md"
    rapport.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Rapport écrit : {rapport.resolve()}")
    print(f"  {len(out)} lignes, {len(proprios)} lignes propriétaire analysées")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
