"""
Retrait du talon non thermosensible avant calcul du ratio kWh/DJU.

Régression couverte : le ratio rapportait toute la consommation aux DJU, talon compris.
En demi-saison, ce talon divisé par des DJU proches de zéro faisait diverger le ratio —
en prod, septembre 2023 sortait à 25 066 kWh/DJU contre 3 900-8 600 les autres mois,
ce qui écrasait toute l'échelle du graphique.

Pour exécuter :
    cd saas/backend && pytest tests/test_dju_seasonal_baseload.py -v
"""
from __future__ import annotations

from app.services.energie import _estimate_baseload


def _synthetic(base: float, a_hot: float, b_cold: float) -> tuple[dict, dict]:
    """3 ans de mois avec une saisonnalité chaud/froid marquée et un talon connu."""
    hot = {"01": 300.0, "02": 260.0, "03": 190.0, "04": 90.0, "05": 20.0, "06": 0.0,
           "07": 0.0, "08": 0.0, "09": 0.0, "10": 70.0, "11": 180.0, "12": 280.0}
    cold = {"01": 0.0, "02": 0.0, "03": 0.0, "04": 0.0, "05": 10.0, "06": 80.0,
            "07": 110.0, "08": 120.0, "09": 20.0, "10": 0.0, "11": 0.0, "12": 0.0}
    dju: dict[str, dict[str, float]] = {}
    conso: dict[str, float] = {}
    for year in (2023, 2024, 2025):
        for mn in hot:
            ym = f"{year}-{mn}"
            dju[ym] = {"dju_chauffe": hot[mn], "dju_froid": cold[mn]}
            conso[ym] = base + a_hot * hot[mn] + b_cold * cold[mn]
    return dju, conso


def test_baseload_is_recovered_from_a_known_signal() -> None:
    dju, conso = _synthetic(base=400_000.0, a_hot=1_200.0, b_cold=800.0)
    fit = _estimate_baseload(dju, conso)

    assert fit is not None
    base, a_hot, b_cold = fit
    assert abs(base - 400_000.0) < 1.0
    assert abs(a_hot - 1_200.0) < 0.01
    assert abs(b_cold - 800.0) < 0.01


def test_removing_the_baseload_stabilises_a_low_dju_month() -> None:
    """Le cas prod : un mois à faible DJU ne doit plus produire un ratio hors échelle."""
    base, a_hot, b_cold = 400_000.0, 1_200.0, 800.0
    dju, conso = _synthetic(base=base, a_hot=a_hot, b_cold=b_cold)
    fit = _estimate_baseload(dju, conso)
    assert fit is not None
    estimated = fit[0]

    # Août : 120 DJU froid. Septembre : 20 DJU froid, donc très sensible au talon.
    ratios_raw = {}
    ratios_net = {}
    for mn in ("08", "09"):
        ym = f"2025-{mn}"
        d = dju[ym]["dju_froid"]
        ratios_raw[mn] = conso[ym] / d
        ratios_net[mn] = max(conso[ym] - estimated, 0.0) / d

    # Avant : septembre explose face à août.
    assert ratios_raw["09"] / ratios_raw["08"] > 4
    # Après : les deux mois retrouvent le même ratio thermosensible (= b_cold).
    assert abs(ratios_net["08"] - b_cold) < 1.0
    assert abs(ratios_net["09"] - b_cold) < 1.0


def test_short_history_is_refused() -> None:
    dju = {f"2025-{m:02d}": {"dju_chauffe": 100.0, "dju_froid": 0.0} for m in range(1, 6)}
    conso = {k: 500_000.0 for k in dju}
    assert _estimate_baseload(dju, conso) is None


def test_degenerate_signal_is_refused() -> None:
    """DJU constants : le systeme est singulier, aucun talon n'est identifiable."""
    dju = {f"2025-{m:02d}": {"dju_chauffe": 100.0, "dju_froid": 0.0} for m in range(1, 13)}
    conso = {k: 500_000.0 for k in dju}
    assert _estimate_baseload(dju, conso) is None


def test_baseload_above_average_consumption_is_refused() -> None:
    """Un talon superieur a la conso moyenne n'a pas de sens physique."""
    hot = {f"{m:02d}": float(300 - 20 * m) for m in range(1, 13)}
    dju = {f"2025-{mn}": {"dju_chauffe": hot[mn], "dju_froid": 0.0} for mn in hot}
    # Pente negative forte : l'ordonnee a l'origine depasse la moyenne.
    conso = {f"2025-{mn}": max(1_000.0, 50_000.0 - 200.0 * hot[mn]) for mn in hot}
    fit = _estimate_baseload(dju, conso)
    if fit is not None:
        assert fit[0] < sum(conso.values()) / len(conso)
