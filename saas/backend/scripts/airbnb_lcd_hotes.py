#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portrait des hôtes — la maille utile pour la prospection.

Change d'unité d'analyse : ni le logement (inatteignable — Airbnb floute les
coordonnées et n'expose pas le numéro d'enregistrement), ni la parcelle, mais
**l'hôte**. Un hôte est identifiable, dénombrable, et son parc est descriptible
en entier. C'est la maille sur laquelle un argumentaire tient.

Produit par hôte : taille du parc, communes, capacité, positionnement
commercial, et surtout la **composition en équipements de son parc** — ce qu'il
a déjà, et ce qui lui manque.

Le classement pro/particulier n'est pas déclaratif (Airbnb ne le dit pas) : il
est déduit de la taille du parc et du nom affiché, et le critère retenu est
écrit dans la colonne `segment_motif` pour rester contestable.

Usage :
    python airbnb_lcd_hotes.py --sortie sig_agglo_data/airbnb
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import airbnb_lcd_equipements as equip

# Indices d'une structure professionnelle dans le nom affiché.
RE_PRO = re.compile(
    r"conciergerie|concierg|gestion|immobili|agence|location|rental|"
    r"property|estate|sarl|sas\b|eurl|sci\b|holiday|vacances|resid|"
    r"logis|keys?\b|cles\b|host\b|booking|tourism",
    re.I,
)

# Équipements mis en avant dans l'argumentaire d'intendance technique :
# ce sont ceux qui génèrent de l'entretien, donc du besoin de service.
EQUIP_ARGUMENTAIRE = [
    "clim", "piscine", "jacuzzi", "sauna", "chauffage", "parking",
    "borne_recharge", "lave_linge", "seche_linge", "lave_vaisselle",
    "jardin", "terrasse_balcon", "barbecue", "ascenseur", "vue_mer",
    "arrivee_autonome",
]


def charger(sortie: Path) -> list[dict]:
    chemin = sortie / "passage2" / "annonces_details.jsonl"
    if not chemin.exists():
        raise SystemExit(f"{chemin} introuvable. Lancer airbnb_lcd_details.py.")
    with chemin.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _segmenter(nom: str, nb: int) -> tuple[str, str]:
    """
    Rend (segment, motif). Le motif dit pourquoi, pour que le classement
    puisse être discuté plutôt que subi.
    """
    if RE_PRO.search(nom or ""):
        return "professionnel", f"nom évocateur d'une structure ({nom})"
    if nb >= 5:
        return "professionnel", f"{nb} annonces"
    if nb >= 2:
        return "multi-proprietaire", f"{nb} annonces"
    return "particulier", "1 annonce, nom sans indice de structure"


def _part(annonces: list[dict], cat: str) -> float | None:
    """Part des biens du parc portant l'équipement (sur ceux qui se prononcent)."""
    col = f"eq_{cat}"
    connus = [a for a in annonces if a.get(col) is not None]
    if not connus:
        return None
    return round(sum(1 for a in connus if a[col] is True) / len(connus), 3)


def _mediane(vals: list) -> float | None:
    v = sorted(x for x in vals if x is not None)
    if not v:
        return None
    m = len(v) // 2
    return float(v[m]) if len(v) % 2 else round((v[m - 1] + v[m]) / 2, 1)


def portraits(lignes: list[dict]) -> list[dict]:
    par_hote: dict[str, list[dict]] = defaultdict(list)
    for l in lignes:
        if l.get("host_id"):
            par_hote[l["host_id"]].append(l)

    out = []
    for hid, ann in par_hote.items():
        nom = ann[0].get("host_nom") or ""
        nb = len(ann)
        segment, motif = _segmenter(nom, nb)

        communes = sorted({a.get("commune_contour") or
                           a.get("commune_recherche") or "" for a in ann})
        types = Counter(a.get("type_logement") or "?" for a in ann)
        notes = [a["note"] for a in ann if a.get("note")]

        p = {
            "host_id": hid,
            "host_nom": nom,
            "segment": segment,
            "segment_motif": motif,
            "nb_annonces": nb,
            "communes": " | ".join(c for c in communes if c),
            "nb_communes": len([c for c in communes if c]),
            "capacite_totale": sum(a.get("capacite") or 0 for a in ann),
            "capacite_mediane": _mediane([a.get("capacite") for a in ann]),
            "type_dominant": types.most_common(1)[0][0] if types else "",
            "nb_avis_cumules": sum(a.get("nb_avis") or 0 for a in ann),
            "note_moyenne": round(sum(notes) / len(notes), 2) if notes else None,
            "nb_superhost": sum(1 for a in ann if a.get("superhost")),
            "taux_indispo_median": _mediane(
                [a.get("calendrier_taux_indisponibilite") for a in ann]),
        }

        # Composition du parc en équipements : la matière de l'argumentaire.
        for cat in EQUIP_ARGUMENTAIRE:
            p[f"part_{cat}"] = _part(ann, cat)
            p[f"nb_{cat}"] = sum(1 for a in ann if a.get(f"eq_{cat}") is True)

        # Ce qui manque au parc : un parc climatisé sans borne de recharge,
        # un parc avec piscines mais sans arrivée autonome, etc.
        p["biens_avec_piscine_ou_jacuzzi"] = sum(
            1 for a in ann
            if a.get("eq_piscine") is True or a.get("eq_jacuzzi") is True)
        p["biens_sans_clim"] = sum(1 for a in ann if a.get("eq_clim") is False)
        p["room_ids"] = " | ".join(a["room_id"] for a in ann)
        out.append(p)

    out.sort(key=lambda x: -x["nb_annonces"])
    return out


def _cle_groupe(nom: str) -> str:
    """
    Clé de regroupement d'un enseigne éclatée sur plusieurs comptes.

    Mesuré : « Poplidays », « Agence Poplidays » et « Agence Poplidays 5 » sont
    trois comptes distincts du même acteur ; comptés séparément, il passe du
    1er au 3e rang. On normalise (accents, casse, marques de mise en forme
    invisibles qu'Airbnb insère parfois), on retire les mots de structure et
    les numéros de compte.
    """
    n = unicodedata.normalize("NFKD", nom or "")
    n = "".join(c for c in n if unicodedata.category(c) not in ("Mn", "Cf"))
    n = n.lower().strip()
    n = re.sub(r"\b(agence|conciergerie|sarl|sas|eurl|sci|groupe|"
               r"immobilier|location|locations)\b", " ", n)
    n = re.sub(r"\d+", " ", n)          # « Poplidays 5 » -> « poplidays »
    n = re.sub(r"[^a-z ]", " ", n)
    return " ".join(n.split())


def grouper_enseignes(hotes: list[dict]) -> list[dict]:
    """
    Consolide les comptes multiples d'un même acteur.

    Prudence volontaire : on ne regroupe **que** les hôtes classés
    professionnels. Fusionner sur un prénom réunirait deux « Sébastien » sans
    rapport, ce qui inventerait un acteur qui n'existe pas.
    """
    groupes: dict[str, list[dict]] = defaultdict(list)
    for h in hotes:
        if h["segment"] != "professionnel":
            continue
        cle = _cle_groupe(h["host_nom"])
        if cle:
            groupes[cle].append(h)

    out = []
    for cle, membres in groupes.items():
        if len(membres) < 2:
            continue
        communes = sorted({c for m in membres
                           for c in m["communes"].split(" | ") if c})
        out.append({
            "enseigne": cle,
            "nb_comptes": len(membres),
            "noms_affiches": " | ".join(m["host_nom"] for m in membres),
            "nb_annonces_total": sum(m["nb_annonces"] for m in membres),
            "capacite_totale": sum(m["capacite_totale"] for m in membres),
            "communes": " | ".join(communes),
            "nb_avis_cumules": sum(m["nb_avis_cumules"] for m in membres),
            "host_ids": " | ".join(m["host_id"] for m in membres),
        })
    out.sort(key=lambda x: -x["nb_annonces_total"])
    return out


def ecrire_csv(chemin: Path, lignes: list[dict]) -> None:
    if not lignes:
        chemin.write_text("", encoding="utf-8")
        return
    cols: list[str] = []
    for l in lignes:
        for k in l:
            if k not in cols:
                cols.append(k)
    with chemin.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)


def fiches_argumentaire(hotes: list[dict], n: int) -> str:
    """Fiches lisibles pour les n plus gros parcs : la matière d'un entretien."""
    L = ["# Fiches hôtes — matière d'argumentaire\n"]
    L.append("Une fiche par gestionnaire, classée par taille de parc. "
             "Les pourcentages portent sur les biens qui se prononcent sur "
             "l'équipement ; un parc peut ne rien déclarer.\n")
    for h in hotes[:n]:
        L.append(f"\n## {h['host_nom'] or '(sans nom)'} — "
                 f"{h['nb_annonces']} biens")
        L.append(f"*{h['segment']} · {h['segment_motif']}*\n")
        L.append(f"- **Parc** : {h['nb_annonces']} biens sur "
                 f"{h['communes']}, {h['capacite_totale']} couchages "
                 f"(médiane {h['capacite_mediane']} par bien)")
        L.append(f"- **Positionnement** : note moyenne "
                 f"{h['note_moyenne']}, {h['nb_avis_cumules']} avis cumulés, "
                 f"{h['nb_superhost']} bien(s) Superhost")
        equipe = [(c, h[f"part_{c}"], h[f"nb_{c}"]) for c in EQUIP_ARGUMENTAIRE
                  if h.get(f"part_{c}")]
        equipe.sort(key=lambda x: -x[1])
        if equipe:
            det = ", ".join(f"{c} {p:.0%} ({n})" for c, p, n in equipe[:8])
            L.append(f"- **Équipements du parc** : {det}")
        if h["biens_avec_piscine_ou_jacuzzi"]:
            L.append(f"- **{h['biens_avec_piscine_ou_jacuzzi']} bien(s) avec "
                     f"piscine ou jacuzzi** → entretien spécialisé récurrent")
        if h["biens_sans_clim"]:
            L.append(f"- {h['biens_sans_clim']} bien(s) déclarés **sans "
                     f"climatisation** → angle d'équipement")
    return "\n".join(L) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sortie", default="sig_agglo_data/airbnb")
    p.add_argument("--fiches", type=int, default=30,
                   help="Nombre de fiches détaillées à rédiger.")
    args = p.parse_args()

    sortie = Path(args.sortie)
    dossier = sortie / "export"
    dossier.mkdir(parents=True, exist_ok=True)

    lignes = charger(sortie)
    hotes = portraits(lignes)

    ecrire_csv(dossier / "hotes_portraits.csv", hotes)

    enseignes = grouper_enseignes(hotes)
    ecrire_csv(dossier / "enseignes_multi_comptes.csv", enseignes)
    (dossier / "fiches-hotes.md").write_text(
        fiches_argumentaire(hotes, args.fiches), encoding="utf-8")

    seg = Counter(h["segment"] for h in hotes)
    total_annonces = sum(h["nb_annonces"] for h in hotes)
    print(f"{len(hotes)} hôtes, {total_annonces} annonces rattachées\n")
    print("  segment              hôtes   annonces   part du parc")
    for s in ("professionnel", "multi-proprietaire", "particulier"):
        hs = [h for h in hotes if h["segment"] == s]
        na = sum(h["nb_annonces"] for h in hs)
        print(f"  {s:<20} {len(hs):5d} {na:10d} "
              f"{na / total_annonces:13.1%}")

    print(f"\n  top 10 des parcs :")
    for h in hotes[:10]:
        print(f"    {h['nb_annonces']:3d} biens — {h['host_nom']:<22} "
              f"[{h['segment']}] {h['communes']}")

    if enseignes:
        print(f"\n  {len(enseignes)} enseignes eclatees sur plusieurs comptes :")
        for e in enseignes[:6]:
            print(f"    {e['nb_annonces_total']:3d} biens sur "
                  f"{e['nb_comptes']} comptes — {e['noms_affiches'][:60]}")

    print(f"\n  -> {dossier / 'hotes_portraits.csv'}")
    print(f"  -> {dossier / 'enseignes_multi_comptes.csv'}")
    print(f"  -> {dossier / 'fiches-hotes.md'}")


if __name__ == "__main__":
    main()
