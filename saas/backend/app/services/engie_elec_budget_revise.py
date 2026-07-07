"""Budget RÉVISÉ ENGIE électricité — reconstitution FIXE / VARIABLE par PRM.

Généralisation du moteur gaz TotalEnergies (``gas_budget_revise``) au 1er marché
**élec** (cf. ``docs/refonte-v1/engie-elec-revise-decisions.md``). Décisions actées :

- **Maille = PRM** (clé facture / ENEDIS / TURPE), agrégée par bâtiment via
  ``BuildingMeterLink`` quand le lien existe, + total marché.
- **Conso attendue = N-1 ENEDIS + correction DJU thermosensible** : régression
  ``kWh_mois = base + pente × DJU_mois`` par PRM (``energie._consumption_by_month``
  + ``_dju_monthly_index`` + ``_linear_trend``). On corrige **seulement** la part
  chauffage/clim ; la base (éclairage/bureautique/ventilation/froid) n'est pas
  thermosensible → pas de surcorrection (≠ ratio DJU global du gaz).
- **Prix de référence = BPU (fourniture) + TURPE (réseau var + fixe)** avec
  **fallback prix dérivés du N-1** par PRM : le fourniture est révisé par un ratio
  BPU (``resolve_historical_bpu_price`` Y / N-1), le réseau par le ratio TURPE
  (``TURPE_EVOLUTION_EVENTS`` cumulés) — analogues au ratio PEG du gaz.
- **Réalisé** = lignes factures ENGIE année Y (décomposées fixe/variable).
  **Atterrissage** = réalisé à date + reste projeté (conso mensuelle attendue ×
  prix de référence), base = mois RÉELLEMENT couverts.

Périmètre = tous les PRM facturés ENGIE (la cible DALKIA sera un calque comparatif,
incrément suivant). Calcul à la volée, aucune persistance, aucune migration :
aucun prix ni contrôle recodé, on **branche** les moteurs existants.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.building_meter import BuildingMeterLink
from app.models.invoice import (
    EnergyInvoice,
    EnergyInvoiceLine,
    EnergyInvoicePeriod,
    EnergyInvoiceSite,
)
from app.services import energie, turpe
from app.services.invoice_bpu import (
    POSTE_TO_BPU_PERIOD,
    load_historical_bpu_prices,
    normalize_bpu_supplier,
)

# --------------------------------------------------------------------------- codes
# Classification des lignes ENGIE (``normalized_code`` = normalized_component du
# parser xlsx). On EXCLUT les codes « total » pour ne pas double-compter les
# composantes qu'ils agrègent (cf. invoice_parsers/engie_xlsx).
_SUPPLY = {"supply"}  # fourniture (variable, sert au prix de référence BPU)
_NETWORK_VAR = {"network_variable"}  # soutirage part variable (TURPE)
_NETWORK_FIXE = {"network_management", "network_counting", "network_withdrawal", "soutirage_fixed"}
_OTHER_VAR = {
    "capacity", "cee", "contribution", "green_energy", "renewable",
    "cspe", "ticfe", "tax_communale", "tax_departementale", "tax_communal", "tax_departemental",
}
_OTHER_FIXE = {"cta", "subscription"}
_PENALTY = {"network_overrun", "network_overrun_quadratic"}  # réel mais hors prix unitaire
# ``network_fixed_total`` = total de la part fixe réseau. Chez ENGIE il DOUBLE les composantes
# (gestion/comptage/soutirage fixe) → ignoré si elles existent ; chez EDF c'est la SEULE ligne de
# fixe réseau → conservée. Arbitrage fait par PRM dans ``_strip_redundant_fixed_total``.
_NETWORK_FIXE_TOTAL = "network_fixed_total"
_IGNORE_TOTALS = {
    "network_total_ht", "supply_total", "supply_total_ht",
    "delivery_variable_total", "delivery_variable_full", "tax_total", "delivery_fixed_part",
    "energy_kwh",
}

# Poids mensuels ≈ heures de nuit (éclairage public, profil ~Sète lat. 43,4°N) : sert à répartir
# la conso annuelle EDF sur l'année (plus l'hiver). Normalisé à la volée (somme = 1).
_PHOTOPERIOD_NIGHT_WEIGHTS = {
    1: 446.4, 2: 372.4, 3: 372.0, 4: 318.0, 5: 291.4, 6: 264.0,
    7: 282.1, 8: 316.2, 9: 348.0, 10: 403.0, 11: 426.0, 12: 455.7,
}


# Prix unitaire élec physiquement impossible (€/kWh) → signature d'un bug d'import :
# le parser ENGIE a, sur certaines factures, écrit le MONTANT dans la colonne « prix
# unitaire » du soutirage variable, puis recalculé montant = quantité × prix (→ ×quantité).
# Le vrai montant de la ligne ≈ la valeur mal placée (le prix stocké). On corrige + signale.
_MAX_PLAUSIBLE_PU_EUR_KWH = 1.0


def _num(value: float | int | None) -> float:
    return float(value) if value is not None else 0.0


def _photoperiod_monthly() -> dict[int, float]:
    """Poids photopériode normalisés (somme = 1) par mois calendaire."""
    total = sum(_PHOTOPERIOD_NIGHT_WEIGHTS.values())
    return {m: w / total for m, w in _PHOTOPERIOD_NIGHT_WEIGHTS.items()}


def _strip_redundant_fixed_total(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retire ``network_fixed_total`` s'il double les composantes fixes réseau (cas ENGIE).

    S'il n'y a pas de composantes (cas EDF), on le garde : c'est la seule part fixe réseau.
    """
    if any(l["code"] in _NETWORK_FIXE for l in lines):
        return [l for l in lines if l["code"] != _NETWORK_FIXE_TOTAL]
    return lines


def _line_amount(line: dict[str, Any]) -> tuple[float, bool]:
    """Montant HT d'une ligne + drapeau anomalie. Corrige le bug d'import soutirage variable."""
    if (
        line["code"] in _NETWORK_VAR
        and abs(_num(line.get("unit_price"))) > _MAX_PLAUSIBLE_PU_EUR_KWH
        and _num(line.get("quantity")) != 0
    ):
        # montant réel ≈ prix stocké (le montant a été mal placé dans la colonne prix).
        return _num(line.get("unit_price")), True
    return _num(line["amount"]), False


def _line_year(period_start: date | None, period_end: date | None) -> int | None:
    for d in (period_start, period_end):
        if d is not None:
            return d.year
    return None


def _line_month(period_start: date | None, period_end: date | None) -> int | None:
    for d in (period_start, period_end):
        if d is not None:
            return d.month
    return None


# --------------------------------------------------------------------------- DJU

def _dju_normal_by_month(exclude_year: int) -> dict[int, float]:
    """Profil DJU chauffage « normal » par mois calendaire = moyenne historique."""
    sums: dict[int, float] = {}
    counts: dict[int, int] = {}
    for ym, values in energie._dju_monthly_index().items():
        try:
            y, m = int(ym[:4]), int(ym[5:7])
        except (ValueError, IndexError):
            continue
        if y == exclude_year:
            continue
        sums[m] = sums.get(m, 0.0) + _num(values.get("dju_chauffe"))
        counts[m] = counts.get(m, 0) + 1
    return {m: sums[m] / counts[m] for m in sums if counts[m] > 0}


# --------------------------------------------------------------------------- conso attendue

def _expected_consumption(
    prm_id: str,
    year: int,
    dju_normal: dict[int, float],
    kwh_invoice_n1: float,
    conso_model: str,
    photoperiod: dict[int, float],
) -> dict[str, Any]:
    """Conso attendue par PRM, selon le modèle du marché.

    - ``thermo_dju`` (ENGIE) : N-1 ENEDIS corrigé du climat sur la part thermosensible seule
      (régression ``kWh = base + pente × DJU``, projection ``base + pente × DJU_normal[m]``).
    - ``photoperiod`` (EDF éclairage public) : N-1 reconduit à l'annuel, réparti sur les mois
      selon le profil d'heures de nuit (pas de thermosensibilité).
    Fallbacks : pas d'ENEDIS → kWh facturés N-1.
    """
    conso_by_month = energie._consumption_by_month().get(prm_id, {})
    enedis_n1 = sum(v for ym, v in conso_by_month.items() if ym[:4] == str(year - 1))

    def _distribute(annual: float, weights: dict[int, float], method: str, enedis: bool) -> dict[str, Any]:
        monthly = {m: annual * weights.get(m, 0.0) for m in range(1, 13)}
        return {
            "conso_attendue_kwh": annual,
            "monthly_expected": monthly,
            "thermo_share": 0.0,
            "conso_method": method,
            "enedis_available": enedis,
            "enedis_kwh_n1": round(enedis_n1, 1) if enedis else 0.0,
        }

    flat_weights = {m: 1.0 / 12.0 for m in range(1, 13)}

    if conso_model == "photoperiod":
        # Éclairage public : annuel reconduit, réparti selon les heures de nuit.
        if enedis_n1 > 0:
            return _distribute(enedis_n1, photoperiod, "photoperiod", enedis=True)
        return _distribute(kwh_invoice_n1, photoperiod, "photoperiod_n1", enedis=False)

    # --- modèle thermosensible DJU (ENGIE) ---
    dju_by_ym = energie._dju_monthly_index()

    def _flat(annual: float, method: str, enedis: bool) -> dict[str, Any]:
        return _distribute(annual, flat_weights, method, enedis)

    if not conso_by_month:
        return _flat(kwh_invoice_n1, "no_enedis", enedis=False)

    # Points (DJU chauffage, kWh) sur les mois complets hors année Y.
    xs: list[float] = []
    ys: list[float] = []
    for ym, kwh in conso_by_month.items():
        if ym[:4] == str(year):
            continue
        dju = dju_by_ym.get(ym)
        if dju is None:
            continue
        xs.append(_num(dju.get("dju_chauffe")))
        ys.append(kwh)

    base_annual = enedis_n1 if enedis_n1 > 0 else kwh_invoice_n1
    if len(xs) < 6 or len(set(round(x) for x in xs)) < 3:
        return _flat(base_annual, "enedis_flat", enedis=True)

    slope, intercept = energie._linear_trend(xs, ys)
    if slope <= 0 or intercept < 0:
        # Pas de thermosensibilité exploitable (ou base négative) → N-1 ENEDIS tenu.
        return _flat(base_annual, "enedis_flat", enedis=True)

    monthly = {m: intercept + slope * dju_normal.get(m, 0.0) for m in range(1, 13)}
    annual = sum(monthly.values())
    thermo = sum(slope * dju_normal.get(m, 0.0) for m in range(1, 13))
    return {
        "conso_attendue_kwh": annual,
        "monthly_expected": monthly,
        "thermo_share": round(thermo / annual, 4) if annual > 0 else 0.0,
        "conso_method": "thermo",
        "enedis_available": True,
        "enedis_kwh_n1": round(enedis_n1, 1),
    }


# --------------------------------------------------------------------------- prix de référence

def _turpe_ratio(year: int) -> tuple[float, bool]:
    """Ratio de révision TURPE = indice(mi-Y) / indice(mi-N-1) via les évolutions moyennes HTA-BT."""
    events = turpe.list_turpe_evolution_events()
    if not events:
        return 1.0, False

    def _index(on: date) -> float:
        idx = 1.0
        for ev in events:
            eff = ev.get("effective_date")
            if isinstance(eff, date) and eff <= on:
                idx *= 1.0 + float(ev.get("evolution_percent") or 0) / 100.0
        return idx

    prev = _index(date(year - 1, 7, 1))
    cur = _index(date(year, 7, 1))
    return (cur / prev, True) if prev > 0 else (1.0, False)


# --------------------------------------------------------------------------- typologie BPU
# Le BPU fourniture vient du marché groupé HÉRAULT ÉNERGIE, indexé par TYPOLOGIE d'abonnement
# (classe tarifaire ENEDIS), PAS par fournisseur (ENGIE/EDF/TE ne sont que l'attributaire du lot
# l'année considérée). On résout donc par typologie canonique, tous fournisseurs confondus, ce qui
# permet le ratio Y/N-1 même quand l'attributaire change entre l'ancien et le nouveau marché.
# Cf. docs/refonte-v1/atterrissage-bpu-elec-decisions.md §8-10.
_CANON_HTA = "HTA"          # C1/C2/C3 (haute tension)
_CANON_BT_SUP36 = "BT_SUP36"  # C4 (BT > 36 kVA)
_CANON_BT_INF36 = "BT_INF36"  # C5 bâtiment (BT ≤ 36 kVA)
_CANON_EP = "EP"            # éclairage public
_CANON_BUILDING_ANY = "BUILDING_ANY"  # nouveau marché 2026 : « Bâtiment » agrégé (collapse import)


def _canonical_typology(segment_code: str) -> str | None:
    """Typologie canonique d'un ``segment_code`` BPU stocké (ancien ou nouveau marché)."""
    code = (segment_code or "").upper()
    if code in ("C1", "C2", "C3"):
        return _CANON_HTA
    if code == "C4":
        return _CANON_BT_SUP36
    if code.startswith("C5_BAT"):
        return _CANON_BT_INF36
    if code == "C5_EP" or code.startswith("ECLAIRAGE_PUBLIC"):
        return _CANON_EP
    # Nouveau marché : granularité préservée (BATIMENT_HTA/BT/BT36) ou collapse (BATIMENT).
    if code == "BATIMENT_HTA":
        return _CANON_HTA
    if code == "BATIMENT_BT":
        return _CANON_BT_SUP36
    if code == "BATIMENT_BT36":
        return _CANON_BT_INF36
    if code == "BATIMENT":
        return _CANON_BUILDING_ANY
    return None


def _prm_canonical_typology(site_meta: dict[str, Any], is_public_lighting: bool) -> str | None:
    """Typologie canonique d'un PRM depuis sa classe ENEDIS (+ usage éclairage public)."""
    if is_public_lighting:
        return _CANON_EP
    segment = str(site_meta.get("segment") or "").upper().strip()
    if segment in ("C1", "C2", "C3"):
        return _CANON_HTA
    if segment == "C4":
        return _CANON_BT_SUP36
    if segment == "C5":
        return _CANON_BT_INF36
    return None


def build_bpu_fourniture_index(references: list[Any]) -> dict[str, dict[tuple, float]]:
    """Index des prix FOURNITURE par (typologie canonique, année, poste) + repli (typologie, année).

    Repli = moyenne des prix fourniture de la typologie/année, pour rester robuste aux libellés de
    poste divergents entre marchés (ex. éclairage public mono-poste, collapse 2026).
    """
    by_poste: dict[tuple, list[float]] = {}
    by_year: dict[tuple, list[float]] = {}
    for ref in references:
        if ref.component_type != "fourniture":
            continue
        canon = _canonical_typology(ref.segment_code)
        if canon is None:
            continue
        price = float(ref.price_eur_per_mwh)
        by_poste.setdefault((canon, ref.valid_year, (ref.period_code or "").upper()), []).append(price)
        by_year.setdefault((canon, ref.valid_year), []).append(price)
    return {
        "by_poste": {k: sum(v) / len(v) for k, v in by_poste.items()},
        "by_year": {k: sum(v) / len(v) for k, v in by_year.items()},
    }


def _lookup_fourniture(
    index: dict[str, dict[tuple, float]], canon: str, year: int, period_code: str
) -> float | None:
    """Prix fourniture pour une typologie/année/poste, avec replis (poste → typologie-année,
    puis typologie bâtiment agrégée BUILDING_ANY du nouveau marché collapse)."""
    candidates = [canon]
    if canon in (_CANON_HTA, _CANON_BT_SUP36, _CANON_BT_INF36):
        candidates.append(_CANON_BUILDING_ANY)  # 2026 « Bâtiment » collapse
    for c in candidates:
        price = index["by_poste"].get((c, year, period_code))
        if price is not None:
            return price
    for c in candidates:
        price = index["by_year"].get((c, year))
        if price is not None:
            return price
    return None


def _bpu_fourniture_unit_price(
    index: dict[str, dict[tuple, float]],
    site_meta: dict[str, Any],
    year: int,
    is_public_lighting: bool,
) -> float | None:
    """Prix unitaire fourniture BPU (€/kWh) de la typologie du PRM pour l'année, moyenne postes.

    Sert de référence quand le marché n'a pas d'historique N-1 (prix contractuel du marché en vigueur).
    """
    canon = _prm_canonical_typology(site_meta, is_public_lighting)
    if canon is None:
        return None
    candidates = [canon]
    if canon in (_CANON_HTA, _CANON_BT_SUP36, _CANON_BT_INF36):
        candidates.append(_CANON_BUILDING_ANY)
    for c in candidates:
        price = index["by_year"].get((c, year))
        if price is not None:
            return price / 1000.0  # €/MWh → €/kWh
    return None


def _bpu_fourniture_ratio(
    index: dict[str, dict[tuple, float]],
    site_meta: dict[str, Any],
    postes_kwh: dict[str, float],
    year: int,
    is_public_lighting: bool,
) -> tuple[float, bool]:
    """Ratio fourniture BPU = Σ(kWh × prix_Y) / Σ(kWh × prix_N-1) par poste, résolu par typologie.

    Best-effort : nécessite une typologie résolue et des prix pour Y ET N-1. Sinon (1,0, False)
    → le prix dérivé N-1 est tenu à plat.
    """
    canon = _prm_canonical_typology(site_meta, is_public_lighting)
    if canon is None:
        return 1.0, False
    # Éclairage public / PRM sans poste facturé (EDF) : un seul poste BASE (ratio scale-invariant).
    weighted = {k: v for k, v in postes_kwh.items() if v > 0} or {"base": 1.0}
    num = den = 0.0
    for poste, kwh in weighted.items():
        period_code = POSTE_TO_BPU_PERIOD.get(str(poste or "").lower())
        if period_code is None:
            continue
        price_y = _lookup_fourniture(index, canon, year, period_code)
        price_p = _lookup_fourniture(index, canon, year - 1, period_code)
        if price_y is None or price_p is None:
            continue
        num += kwh * price_y
        den += kwh * price_p
    if den > 0:
        return num / den, True
    return 1.0, False


# --------------------------------------------------------------------------- agrégats lignes

def _reference_from_lines(lines: list[dict[str, Any]]) -> dict[str, Any]:
    """Prix unitaires (€/kWh) + parts fixes dérivés d'un lot de lignes N-1, par PRM."""
    kwh = sum(_num(l["quantity"]) for l in lines if l["code"] in _SUPPLY)
    fourniture = reseau_var = autres_var = fixe_reseau = fixe_autre = 0.0
    anomalies = 0
    for l in lines:
        amount, flagged = _line_amount(l)
        anomalies += 1 if flagged else 0
        if l["code"] in _SUPPLY:
            fourniture += amount
        elif l["code"] in _NETWORK_VAR:
            reseau_var += amount
        elif l["code"] in _OTHER_VAR:
            autres_var += amount
        elif l["code"] in _NETWORK_FIXE or l["code"] == _NETWORK_FIXE_TOTAL:
            fixe_reseau += amount
        elif l["code"] in _OTHER_FIXE:
            fixe_autre += amount
    postes_kwh: dict[str, float] = {}
    for l in lines:
        if l["code"] in _SUPPLY and l.get("poste"):
            postes_kwh[l["poste"]] = postes_kwh.get(l["poste"], 0.0) + _num(l["quantity"])
    return {
        "kwh": kwh,
        # Montants bruts N-1 : le prix unitaire est calculé dans _build_point avec le meilleur
        # dénominateur kWh disponible (kWh facture, sinon kWh ENEDIS N-1 — cas EDF sans kWh en ligne).
        "fourniture": fourniture,
        "reseau_var": reseau_var,
        "autres_var": autres_var,
        "fixe_reseau": fixe_reseau,
        "fixe_autre": fixe_autre,
        "postes_kwh": postes_kwh,
        "anomalies": anomalies,
    }


def _realise_from_lines(lines: list[dict[str, Any]]) -> dict[str, Any]:
    """Réalisé année Y décomposé fixe / variable, par PRM."""
    variable = fixe = 0.0
    anomalies = 0
    for l in lines:
        amount, flagged = _line_amount(l)
        anomalies += 1 if flagged else 0
        if l["code"] in (_SUPPLY | _NETWORK_VAR | _OTHER_VAR | _PENALTY):
            variable += amount
        elif l["code"] in (_NETWORK_FIXE | _OTHER_FIXE) or l["code"] == _NETWORK_FIXE_TOTAL:
            fixe += amount
    kwh = sum(_num(l["quantity"]) for l in lines if l["code"] in _SUPPLY)
    covered = {m for l in lines if (m := _line_month(l["period_start"], l["period_end"])) is not None}
    return {
        "realise_variable": round(variable, 2),
        "realise_fixe": round(fixe, 2),
        "realise_total": round(variable + fixe, 2),
        "kwh_realise": kwh,
        "covered_months": covered,
        "anomalies": anomalies,
    }


# --------------------------------------------------------------------------- atterrissage

def _landing(
    realise: dict[str, Any],
    monthly_expected: dict[int, float],
    pu_variable: float,
    fixe_prevision: float,
    year: int,
    today: date,
    prevision_reference: float,
) -> tuple[float, str]:
    """Atterrissage = réalisé + reste projeté sur les mois NON couverts.

    Reste conso = Σ conso mensuelle attendue (modèle thermo) des mois non facturés →
    pas de surcorrection (la base non thermosensible n'est pas mise à l'échelle du climat).
    """
    covered = realise["covered_months"]
    if not covered:
        # Aucune facture Y → l'atterrissage se réduit au repère de prévision.
        return round(prevision_reference, 2), "prevision"
    if today.year > year:
        return round(realise["realise_total"], 2), "realise_complet"
    remaining = [m for m in range(1, 13) if m not in covered]
    if not remaining:
        return round(realise["realise_total"], 2), "realise_complet"

    conso_reste = sum(monthly_expected.get(m, 0.0) for m in remaining)
    fixe_par_mois = (realise["realise_fixe"] / len(covered)) if realise["realise_fixe"] > 0 else (fixe_prevision / 12.0)
    total = realise["realise_total"] + conso_reste * pu_variable + fixe_par_mois * len(remaining)
    return round(total, 2), "mensuel"


# --------------------------------------------------------------------------- point PRM

def _build_point(
    prm: str,
    site_meta: dict[str, Any],
    lines_n1: list[dict[str, Any]],
    lines_y: list[dict[str, Any]],
    year: int,
    today: date,
    dju_normal: dict[int, float],
    turpe_ratio: float,
    bpu_index: dict[str, dict[tuple, float]],
    link: dict[str, Any] | None,
    conso_model: str,
    photoperiod: dict[int, float],
) -> dict[str, Any]:
    lines_n1 = _strip_redundant_fixed_total(lines_n1)
    lines_y = _strip_redundant_fixed_total(lines_y)
    ref = _reference_from_lines(lines_n1)
    realise = _realise_from_lines(lines_y)
    is_public_lighting = conso_model == "photoperiod"

    # Marché sans historique N-1 (ex. ENGIE démarré l'année Y) : une référence bâtie sur N-1 serait nulle.
    # Bascule « année en vigueur » : on prend les prix unitaires des factures Y (déjà au prix du marché
    # courant), fourniture calée sur le BPU du marché quand dispo, appliqués à la conso attendue ENEDIS N-1.
    reference_source = "historique_n1"
    if ref["kwh"] <= 0 and any(_num(l["quantity"]) for l in lines_y if l["code"] in _SUPPLY):
        ref = _reference_from_lines(lines_y)
        reference_source = "annee_en_vigueur"

    conso = _expected_consumption(prm, year, dju_normal, ref["kwh"], conso_model, photoperiod)
    bpu_ratio, bpu_available = _bpu_fourniture_ratio(
        bpu_index, site_meta, ref["postes_kwh"], year, is_public_lighting
    )

    # Dénominateur du prix unitaire : kWh facturés si présents (ENGIE), sinon kWh ENEDIS N-1
    # (EDF : les lignes fourniture n'ont pas de quantité → on prend la conso ENEDIS de l'année N-1).
    pu_denom = ref["kwh"] if ref["kwh"] > 0 else conso["enedis_kwh_n1"]
    pu_fourniture = (ref["fourniture"] / pu_denom) if pu_denom > 0 else 0.0
    pu_reseau_var = (ref["reseau_var"] / pu_denom) if pu_denom > 0 else 0.0
    pu_autres_var = (ref["autres_var"] / pu_denom) if pu_denom > 0 else 0.0

    if reference_source == "annee_en_vigueur":
        # Prix Y déjà courants → pas de révision Y/N-1 ; fourniture calée sur le BPU du marché si dispo.
        bpu_ratio, eff_turpe = 1.0, 1.0
        bpu_pu = _bpu_fourniture_unit_price(bpu_index, site_meta, year, is_public_lighting)
        if bpu_pu is not None:
            pu_fourniture, bpu_available = bpu_pu, True
    else:
        eff_turpe = turpe_ratio

    pu_variable = pu_fourniture * bpu_ratio + pu_reseau_var * eff_turpe + pu_autres_var
    fixe_prevision = ref["fixe_reseau"] * eff_turpe + ref["fixe_autre"]
    variable_prevision = conso["conso_attendue_kwh"] * pu_variable
    prevision_reference = variable_prevision + fixe_prevision

    atterrissage, method = _landing(
        realise, conso["monthly_expected"], pu_variable, fixe_prevision,
        year, today, prevision_reference,
    )

    anomaly_count = ref["anomalies"] + realise["anomalies"]
    return {
        "prm": prm,
        "site_name": site_meta.get("site_name"),
        "segment": site_meta.get("segment"),
        "regroupement": site_meta.get("regroupement"),
        "building_id": link["building_id"] if link else None,
        "building_name": link["building_name"] if link else None,
        "has_anomaly": anomaly_count > 0,
        "anomaly_count": anomaly_count,
        "kwh_n1": round(ref["kwh"], 0),
        "enedis_kwh_n1": conso["enedis_kwh_n1"],
        "conso_attendue_kwh": round(conso["conso_attendue_kwh"], 0),
        "thermo_share": conso["thermo_share"],
        "conso_method": conso["conso_method"],
        "enedis_available": conso["enedis_available"],
        "bpu_ratio": round(bpu_ratio, 4),
        "bpu_available": bpu_available,
        "turpe_ratio": round(turpe_ratio, 4),
        "pu_variable_eur_kwh": round(pu_variable, 6),
        "fixe_prevision": round(fixe_prevision, 2),
        "variable_prevision": round(variable_prevision, 2),
        "prevision_reference": round(prevision_reference, 2),
        "realise": realise["realise_total"],
        "realise_fixe": realise["realise_fixe"],
        "realise_variable": realise["realise_variable"],
        "kwh_realise": round(realise["kwh_realise"], 0),
        "months_covered": len(realise["covered_months"]),
        "atterrissage": atterrissage,
        "ecart_atterrissage_vs_prevision": round(atterrissage - prevision_reference, 2),
        "landing_method": method,
        "reference_source": reference_source,
        "has_history": ref["kwh"] > 0 or conso["enedis_available"],
    }


# --------------------------------------------------------------------------- entrée

def _fetch_lines(db: Session, city_id: int | None, supplier: str) -> dict[str, dict[str, Any]]:
    """Lignes factures élec du fournisseur, indexées par PRM (+ métadonnées site)."""
    rows = db.execute(
        select(
            EnergyInvoiceSite.prm_id,
            EnergyInvoiceSite.site_name,
            EnergyInvoiceSite.segment,
            EnergyInvoiceSite.tariff_option_label,
            EnergyInvoiceSite.regroupement,
            EnergyInvoicePeriod.period_start,
            EnergyInvoicePeriod.period_end,
            EnergyInvoiceLine.normalized_code,
            EnergyInvoiceLine.poste,
            EnergyInvoiceLine.quantity,
            EnergyInvoiceLine.unit_price_ht,
            EnergyInvoiceLine.amount_ht,
            EnergyInvoice.supplier,
        )
        .select_from(EnergyInvoiceLine)
        .join(EnergyInvoicePeriod, EnergyInvoiceLine.invoice_period_id == EnergyInvoicePeriod.id)
        .join(EnergyInvoiceSite, EnergyInvoicePeriod.invoice_site_id == EnergyInvoiceSite.id)
        .join(EnergyInvoice, EnergyInvoiceSite.invoice_id == EnergyInvoice.id)
        .where(
            EnergyInvoice.city_id == city_id,
            EnergyInvoice.energy_type == "electricity",
            EnergyInvoiceSite.prm_id.isnot(None),
        )
    ).all()

    by_prm: dict[str, dict[str, Any]] = {}
    for r in rows:
        if normalize_bpu_supplier(r.supplier) != supplier:
            continue
        code = (r.normalized_code or "").strip()
        if not code or code in _IGNORE_TOTALS:
            continue
        prm = r.prm_id.strip()
        entry = by_prm.setdefault(
            prm,
            {
                "meta": {
                    "site_name": r.site_name,
                    "segment": r.segment,
                    "tariff_option_label": r.tariff_option_label,
                    "regroupement": r.regroupement,
                },
                "lines": [],
            },
        )
        entry["lines"].append(
            {
                "code": code,
                "poste": r.poste,
                "quantity": r.quantity,
                "unit_price": r.unit_price_ht,
                "amount": r.amount_ht,
                "period_start": r.period_start,
                "period_end": r.period_end,
            }
        )
    return by_prm


def _building_links(db: Session, city_id: int | None) -> dict[str, dict[str, Any]]:
    """Lien PRM → bâtiment (ELECTRICITE), pour l'agrégat par bâtiment."""
    rows = db.execute(
        select(BuildingMeterLink.meter_identifier, BuildingMeterLink.building_id, Building.nom_batiment)
        .join(Building, BuildingMeterLink.building_id == Building.id)
        .where(
            Building.city_id == city_id,
            BuildingMeterLink.fluid == "ELECTRICITE",
        )
    ).all()
    return {
        r.meter_identifier.strip(): {"building_id": r.building_id, "building_name": r.nom_batiment}
        for r in rows
        if r.meter_identifier
    }


def build_elec_budget_revise(
    db: Session,
    city_id: int | None = None,
    *,
    year: int,
    supplier: str,
    conso_model: str,
    today: date | None = None,
) -> dict[str, Any]:
    """Budget révisé élec par PRM (fixe/variable), réalisé et atterrissage — générique ENGIE/EDF.

    ``supplier`` filtre les factures (``ENGIE``/``EDF``) et les prix BPU. ``conso_model`` choisit la
    source de conso attendue : ``thermo_dju`` (ENGIE) ou ``photoperiod`` (EDF éclairage public).
    """
    resolved_today = today or date.today()

    by_prm = _fetch_lines(db, city_id, supplier)
    links = _building_links(db, city_id)
    # BPU = marché HÉRAULT ÉNERGIE par typologie, tous fournisseurs élec confondus (pas seulement
    # l'attributaire courant) → indispensable au ratio Y/N-1 quand l'attributaire change (ex. ENGIE 2026
    # vs EDF 2025). Cf. atterrissage-bpu-elec-decisions §8-10.
    bpu_references: list[Any] = []
    for elec_supplier in ("ENGIE", "EDF"):
        bpu_references.extend(load_historical_bpu_prices(db, elec_supplier))
    bpu_index = build_bpu_fourniture_index(bpu_references)
    turpe_ratio, turpe_available = _turpe_ratio(year)
    dju_normal = _dju_normal_by_month(exclude_year=year)
    photoperiod = _photoperiod_monthly()

    points: list[dict[str, Any]] = []
    for prm in sorted(by_prm):
        entry = by_prm[prm]
        lines_n1 = [l for l in entry["lines"] if _line_year(l["period_start"], l["period_end"]) == year - 1]
        lines_y = [l for l in entry["lines"] if _line_year(l["period_start"], l["period_end"]) == year]
        if not lines_n1 and not lines_y:
            continue
        points.append(
            _build_point(
                prm, entry["meta"], lines_n1, lines_y, year, resolved_today,
                dju_normal, turpe_ratio, bpu_index, links.get(prm),
                conso_model, photoperiod,
            )
        )
    points.sort(key=lambda p: p["atterrissage"], reverse=True)

    def _sum(field: str) -> float:
        return round(sum(p[field] for p in points), 2)

    totals = {
        "fixe_prevision": _sum("fixe_prevision"),
        "variable_prevision": _sum("variable_prevision"),
        "prevision_reference": _sum("prevision_reference"),
        "realise": _sum("realise"),
        "realise_fixe": _sum("realise_fixe"),
        "realise_variable": _sum("realise_variable"),
        "atterrissage": _sum("atterrissage"),
    }
    totals["ecart_atterrissage_vs_prevision"] = round(
        totals["atterrissage"] - totals["prevision_reference"], 2
    )

    def _aggregate(key_field: str, none_label: str) -> list[dict[str, Any]]:
        """Agrège les points par un champ (bâtiment ou regroupement)."""
        acc: dict[Any, dict[str, Any]] = {}
        for p in points:
            key = p[key_field]
            row = acc.setdefault(
                key,
                {
                    "key": key if isinstance(key, int) or key is None else str(key),
                    "label": (p.get("building_name") if key_field == "building_id" else key) or none_label,
                    "prm_count": 0,
                    "prevision_reference": 0.0,
                    "realise": 0.0,
                    "atterrissage": 0.0,
                },
            )
            row["prm_count"] += 1
            row["prevision_reference"] += p["prevision_reference"]
            row["realise"] += p["realise"]
            row["atterrissage"] += p["atterrissage"]
        return sorted(
            (
                {**r,
                 "prevision_reference": round(r["prevision_reference"], 2),
                 "realise": round(r["realise"], 2),
                 "atterrissage": round(r["atterrissage"], 2)}
                for r in acc.values()
            ),
            key=lambda r: r["atterrissage"], reverse=True,
        )

    anomaly_prm = sum(1 for p in points if p["has_anomaly"])
    bpu_applied_prm = sum(1 for p in points if p["bpu_available"])
    ref_en_vigueur_prm = sum(1 for p in points if p.get("reference_source") == "annee_en_vigueur")

    return {
        "year": year,
        "generated_on": resolved_today.isoformat(),
        "prm_count": len(points),
        "turpe_available": turpe_available,
        "reference_annee_en_vigueur_count": ref_en_vigueur_prm,
        "bpu_available": bpu_applied_prm > 0,
        "bpu_applied_prm_count": bpu_applied_prm,
        "enedis_available": any(p["enedis_available"] for p in points),
        "anomaly_prm_count": anomaly_prm,
        "totals": totals,
        "points": points,
        "buildings": _aggregate("building_id", "Non affecté"),
        "regroupements": _aggregate("regroupement", "Non regroupé"),
        "source_note": (
            f"Budget prévisionnel de référence {supplier} élec (marché fourniture, tous PRM). Conso attendue = "
            + (
                "historique ENEDIS N-1 corrigé du climat sur la seule part thermosensible (régression kWh/DJU "
                "chauffage par PRM ; base non thermosensible tenue) — pas de surcorrection DJU. "
                if conso_model == "thermo_dju"
                else "conso N-1 reconduite (éclairage public non thermosensible), répartie par mois selon le "
                "profil d'heures de nuit (photopériode ~Sète). "
            )
            + (
                f"Prix de référence = fourniture révisée par ratio BPU (Y/N-1, appliqué sur "
                f"{bpu_applied_prm}/{len(points)} PRM) + réseau révisé par ratio TURPE (évolutions moyennes "
                "cumulées) ; à défaut, prix dérivés du N-1 par PRM. "
                if bpu_applied_prm
                else "Prix de référence = prix réels du N-1 par PRM, réseau ajusté par ratio TURPE "
                "(acheminement). ⚠ La révision BPU (fourniture) n'est PAS appliquée : millésime BPU unique "
                "(ratio année/N-1 impossible) et/ou segment tarifaire non couvert — la fourniture est tenue "
                "au niveau du N-1 réel. "
            )
            + "Atterrissage = réalisé Y (décomposé fixe/variable) + reste projeté sur les mois NON couverts "
            "(conso mensuelle attendue × prix de référence)."
            + (
                f" ⚠ {anomaly_prm} PRM avec anomalie d'import (soutirage variable au prix aberrant, montant "
                "corrigé sur la valeur mal placée et signalé) — à réimporter après correction du parser."
                if anomaly_prm
                else ""
            )
        ),
    }


def build_engie_elec_budget_revise(
    db: Session, city_id: int | None = None, *, year: int, today: date | None = None
) -> dict[str, Any]:
    """Budget révisé ENGIE élec (conso attendue = N-1 ENEDIS + DJU thermosensible)."""
    return build_elec_budget_revise(
        db, city_id, year=year, supplier="ENGIE", conso_model="thermo_dju", today=today
    )


def build_edf_elec_budget_revise(
    db: Session, city_id: int | None = None, *, year: int, today: date | None = None
) -> dict[str, Any]:
    """Budget révisé EDF éclairage public (conso attendue = N-1 reconduit + profil photopériode)."""
    return build_elec_budget_revise(
        db, city_id, year=year, supplier="EDF", conso_model="photoperiod", today=today
    )
