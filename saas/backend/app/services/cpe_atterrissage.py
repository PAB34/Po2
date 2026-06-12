"""Atterrissage trimestriel CPE — projection de fin d'année à partir du réalisé à date.

Le bilan d'intéressement (`get_bilan_annuel`) calcule un **cumul** depuis le 1er janvier :
en cours d'année il est partiel et ne projette pas la fin d'exercice. Ce module répond au
besoin des **réunions trimestrielles DALKIA** : « vu le réalisé T1(+T2…), où atterrit-on au
31/12 ? ».

Méthode (v1, **pro-rata DJU** — à caler sur la méthode DALKIA quand leur tableau arrivera) :
la consommation de chauffage est proportionnelle aux DJU. À la fin du trimestre T (donc
``mois_ecoules = 3·T`` mois) :

- ``DJU_projeté_annuel = DJU_réel(mois écoulés) + DJU_normal(mois restants)`` où le profil
  **normal mensuel** vient de la moyenne historique du CSV DJU (Open-Meteo, hors année en cours) ;
- ``NC_projeté = NC_réalisé × (DJU_projeté_annuel / DJU_réel_écoulé)`` (extrapolation climatique,
  pas un simple pro-rata temporel — l'hiver pèse plus que l'été) ;
- ``N'B_projeté = NB × (DJU_projeté_annuel / 1426)`` ;
- intéressement / pénalité projetés via la formule contractuelle (`calcul_interessement`).

⚠️ Modèle pur-DJU : ignore une éventuelle part de consommation non thermosensible. Suffisant
pour un ordre de grandeur d'atterrissage ; à affiner à réception du tableau DALKIA.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.cpe import (
    DJU_REFERENCE,
    calcul_interessement,
    calcul_nc,
    get_all_prix_gaz,
    get_releves,
    get_sites,
    resolve_nb_for_year_detailed,
)
from app.services.dju_profiles import DALKIA_CONTRACT_PROFILE, aggregate_dju_monthly, is_dalkia_heating_month


def _real_dju_by_month(annee: int) -> dict[int, float]:
    """DJU chauffage réel DALKIA par mois, depuis le profil Montpellier dédié."""
    monthly = aggregate_dju_monthly(DALKIA_CONTRACT_PROFILE)
    out: dict[int, float] = {}
    for row in monthly:
        ym = row.get("month", "")
        if len(ym) < 7:
            continue
        try:
            y, m = int(ym[:4]), int(ym[5:7])
        except ValueError:
            continue
        if y == annee and is_dalkia_heating_month(m):
            out[m] = row.get("dju_chauffe", 0.0) or 0.0
    return out


def _normal_dju_profile(annee: int) -> dict[int, float]:
    """Profil DJU mensuel « normal » : moyenne historique par mois calendaire (hors `annee`).

    Sert à estimer les DJU des mois restants (météo future inconnue). Calculé sur toutes les
    années disponibles dans le CSV, l'année en cours exclue.
    """
    monthly = aggregate_dju_monthly(DALKIA_CONTRACT_PROFILE)
    sums: dict[int, float] = {}
    counts: dict[int, int] = {}
    for row in monthly:
        ym = row.get("month", "")
        if len(ym) < 7:
            continue
        try:
            y, m = int(ym[:4]), int(ym[5:7])
        except ValueError:
            continue
        if y == annee or not is_dalkia_heating_month(m):
            continue
        sums[m] = sums.get(m, 0.0) + (row.get("dju_chauffe", 0.0) or 0.0)
        counts[m] = counts.get(m, 0) + 1
    return {m: sums[m] / counts[m] for m in sums if counts[m] > 0}


def build_atterrissage(
    db: Session, annee: int, trimestre: int, city_id: int | None = None
) -> dict[str, Any]:
    """Projette l'intéressement/pénalité de fin d'année à partir du réalisé jusqu'à fin T.

    ``trimestre`` ∈ {1,2,3,4} : on prend les relevés des ``3·trimestre`` premiers mois.
    """
    if trimestre not in (1, 2, 3, 4):
        raise ValueError("Le trimestre doit etre 1, 2, 3 ou 4.")
    mois_ecoules = 3 * trimestre

    real_dju = _real_dju_by_month(annee)
    normal_dju = _normal_dju_profile(annee)

    dju_reel_ecoule = round(sum(real_dju.get(m, 0.0) for m in range(1, mois_ecoules + 1)), 1)

    # DJU des mois restants : profil normal ; fallback degrade (reference/12) si pas d'historique.
    fallback_month = DJU_REFERENCE / 12.0
    method = "profil_normal"
    dju_normal_restant = 0.0
    for m in range(mois_ecoules + 1, 13):
        if m in normal_dju:
            dju_normal_restant += normal_dju[m]
        else:
            dju_normal_restant += fallback_month
            method = "fallback_reference"
    dju_normal_restant = round(dju_normal_restant, 1)
    dju_projete_annuel = round(dju_reel_ecoule + dju_normal_restant, 1)

    has_dju = dju_reel_ecoule > 0
    prix_par_tarif = {p.tarif: p.pu_eur_mwh_pci for p in get_all_prix_gaz(db, annee)}

    items: list[dict[str, Any]] = []
    total_interessement = 0.0
    total_penalite = 0.0
    nb_projetes = 0

    for site in get_sites(db, city_id=city_id, actifs_seulement=True):
        pu_site = prix_par_tarif.get(site.tarif) if site.tarif else None
        if pu_site is None and site.tarif is not None:
            pu_site = prix_par_tarif.get(None)

        releves = [r for r in get_releves(db, site.id, annee) if r.mois <= mois_ecoules]
        mois_realises = len([r for r in releves if r.qt_mwh_pci is not None])
        qt_realise = sum(r.qt_mwh_pci for r in releves if r.qt_mwh_pci is not None) or None
        m_ecs = sum(r.volume_ecs_m3 for r in releves if r.volume_ecs_m3 is not None)
        if m_ecs == 0 and site.ecs_ref_m3_an > 0:
            # Pro-rata de l'ECS de reference sur la part d'annee ecoulee.
            m_ecs = site.ecs_ref_m3_an * mois_ecoules / 12.0

        nb_exercice, nb_source = resolve_nb_for_year_detailed(db, site, annee)
        nc_realise = calcul_nc(qt_realise, m_ecs, site.q_ecs_mwh_pci_per_m3) if qt_realise else None

        nc_projete: float | None = None
        n_prime_b_projete: float | None = None
        fin: dict[str, Any] = {}
        statut = "sans_donnee"
        if nc_realise is not None and has_dju and pu_site is not None:
            facteur = dju_projete_annuel / dju_reel_ecoule if dju_reel_ecoule else 1.0
            nc_projete = round(nc_realise * facteur, 2)
            n_prime_b_projete = round(nb_exercice * (dju_projete_annuel / DJU_REFERENCE), 2)
            fin = calcul_interessement(n_prime_b_projete, nc_projete, pu_site)
            statut = "projete"
            nb_projetes += 1
            if fin.get("type_resultat") == "interessement":
                total_interessement += fin.get("montant_ht") or 0.0
            elif fin.get("type_resultat") == "penalite":
                total_penalite += fin.get("montant_ht") or 0.0
        elif nc_realise is None:
            statut = "sans_donnee"
        elif pu_site is None or not has_dju:
            statut = "incomplet"

        items.append({
            "code_site": site.code_site,
            "nom_site": site.nom_site,
            "site_id": site.id,
            "tarif": site.tarif,
            "nb_exercice": round(nb_exercice, 2),
            "nb_source": nb_source,
            "mois_realises": mois_realises,
            "nc_realise": round(nc_realise, 2) if nc_realise is not None else None,
            "nc_projete": nc_projete,
            "n_prime_b_projete": n_prime_b_projete,
            "ecart_projete": round(fin["ecart"], 2) if fin.get("ecart") is not None else None,
            "type_resultat": fin.get("type_resultat"),
            "montant_ht_projete": fin.get("montant_ht"),
            "statut": statut,
        })

    total_interessement = round(total_interessement, 2)
    total_penalite = round(total_penalite, 2)
    return {
        "annee": annee,
        "trimestre": trimestre,
        "mois_ecoules": mois_ecoules,
        "dju_reel_ecoule": dju_reel_ecoule,
        "dju_normal_restant": dju_normal_restant,
        "dju_projete_annuel": dju_projete_annuel,
        "dju_reference": DJU_REFERENCE,
        "dju_method": method,
        "has_data": has_dju and nb_projetes > 0,
        "nb_sites_projetes": nb_projetes,
        "total_interessement_projete": total_interessement,
        "total_penalite_projete": total_penalite,
        "net_projete": round(total_interessement - total_penalite, 2),
        "items": items,
    }
