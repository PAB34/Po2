"""Reconstitution du budget P1 gaz DALKIA par site = conso attendue (DJU) × prix OS3.

Le P1 gaz (fourniture d'énergie du CPE) est **quasi tout variable** : l'acompte P1 est un provisionnel
de trésorerie régularisé sur la conso réelle × prix. Dans l'atterrissage par poste
(``accounting_contract_budget``), P1 était laissé sans révision (budget = base) car un coefficient
``Σprix_révisé/Σprix_base`` sur des lignes de conso n'a pas de sens. Ce moteur reconstitue le budget P1 à
la bonne granularité :

    budget_P1_site = conso attendue (relevés N-1 corrigés du climat, DJU DALKIA) × Pu OS3 (année, tarif)

``qt_mwh_pci`` (relevés) et ``pu_eur_mwh_pci`` (OS3) sont tous deux en PCI → produit direct, sans conversion
PCS. Calcul à la volée, aucune migration. On branche ``get_releves`` / ``get_prix_gaz`` / le profil DJU
Montpellier — rien recodé côté prix.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services import cpe
from app.services.cpe_dalkia_db import resolve_p1_gaz_tarif
from app.services.dju_profiles import (
    DALKIA_CONTRACT_PROFILE,
    aggregate_dju_monthly,
    is_dalkia_heating_month,
)


def _dju_by_year_month() -> dict[tuple[int, int], float]:
    """{(année, mois): DJU chauffage} depuis le profil DALKIA Montpellier (mois de chauffe)."""
    out: dict[tuple[int, int], float] = {}
    for row in aggregate_dju_monthly(DALKIA_CONTRACT_PROFILE):
        ym = str(row.get("month", ""))
        if len(ym) < 7:
            continue
        try:
            y, m = int(ym[:4]), int(ym[5:7])
        except ValueError:
            continue
        if is_dalkia_heating_month(m):
            out[(y, m)] = float(row.get("dju_chauffe") or 0.0)
    return out


def _normal_annual_dju(dju: dict[tuple[int, int], float], exclude_year: int) -> float:
    """DJU annuel « normal » = moyenne des DJU annuels historiques (années ≠ exclude_year)."""
    per_year: dict[int, float] = {}
    for (y, _m), value in dju.items():
        if y == exclude_year:
            continue
        per_year[y] = per_year.get(y, 0.0) + value
    if not per_year:
        return 0.0
    return sum(per_year.values()) / len(per_year)


def compute_p1_gaz_budget(
    db: Session,
    city_id: int | None = None,
    *,
    year: int,
) -> dict[str, Any]:
    """Budget P1 gaz reconstitué par site (conso attendue DJU × prix OS3) et total.

    Retour : ``{year, total, climate_ratio, dju_available, by_site: [...], incomplete_sites}``.
    """
    dju = _dju_by_year_month()
    normal_annual = _normal_annual_dju(dju, exclude_year=year)
    dju_n1 = sum(v for (y, _m), v in dju.items() if y == year - 1)
    climate_ratio = (normal_annual / dju_n1) if (normal_annual > 0 and dju_n1 > 0) else 1.0

    by_site: list[dict[str, Any]] = []
    total = 0.0
    incomplete = 0
    for site in cpe.get_sites(db, city_id=city_id, actifs_seulement=True):
        tarif = site.tarif or resolve_p1_gaz_tarif(db, code_site=site.code_site, city_id=city_id)
        prix = cpe.get_prix_gaz(db, year, tarif)
        pu = prix.pu_eur_mwh_pci if prix else None

        releves = cpe.get_releves(db, site.id, year - 1)
        conso_n1 = sum(r.qt_mwh_pci for r in releves if r.qt_mwh_pci is not None)
        if conso_n1 > 0:
            conso_attendue = conso_n1 * climate_ratio
            conso_source = "releves_n1_dju"
        else:
            conso_attendue = cpe.resolve_nb_for_year(db, site, year) or 0.0
            conso_source = "nb_contractuel"

        if pu is None or conso_attendue <= 0:
            budget = 0.0
            status = "incomplet"
            incomplete += 1
        else:
            budget = conso_attendue * pu
            status = "reconstitue"
        total += budget

        by_site.append({
            "site_id": site.id,
            "code_site": site.code_site,
            "nom_site": site.nom_site,
            "tarif": tarif,
            "pu_os3_eur_mwh": round(pu, 4) if pu is not None else None,
            "conso_attendue_mwh": round(conso_attendue, 2),
            "conso_source": conso_source,
            "budget": round(budget, 2),
            "status": status,
        })

    by_site.sort(key=lambda s: s["budget"], reverse=True)
    return {
        "year": year,
        "total": round(total, 2),
        "climate_ratio": round(climate_ratio, 4),
        "dju_available": bool(dju),
        "incomplete_sites": incomplete,
        "by_site": by_site,
    }
