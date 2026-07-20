import app.services.energie as energie_mod
from app.services.energie import (
    _fluids_climate_series,
    _fluids_thermal,
    _linreg,
    get_fluids_climate,
)


def test_linreg_perfect_line():
    slope, intercept, r2 = _linreg([0, 1, 2, 3], [3, 5, 7, 9])
    assert round(slope, 6) == 2.0
    assert round(intercept, 6) == 3.0
    assert r2 is not None and round(r2, 6) == 1.0


def test_linreg_too_few_points():
    assert _linreg([1, 2], [1, 2]) is None


def _dju(years):
    idx = {}
    for year, months in years.items():
        for month, (heat, cool) in months.items():
            idx[f"{year}-{month:02d}"] = {"dju_chauffe": heat, "dju_froid": cool}
    return idx


def test_series_current_previous_average():
    idx = _dju({2024: {1: (100, 0)}, 2025: {1: (120, 0)}, 2026: {1: (90, 0)}})
    series = _fluids_climate_series(idx, "dju_chauffe", 2026, 2025, [2024, 2025])
    jan = next(p for p in series["monthly"] if p["month"] == 1)
    assert jan["current"] == 90
    assert jan["previous"] == 120
    assert jan["average"] == 110  # mean of 100 and 120
    assert series["current_total"] == 90
    assert series["previous_total"] == 120
    assert series["delta_previous_pct"] == round((90 - 120) / 120 * 100, 1)


def test_thermal_rolling_window_evolution():
    # 24 mois : fenêtre courante = 12 derniers (pente 3), fenêtre précédente = 12 avant (pente 2).
    idx = {}
    conso = {}
    for m in range(1, 13):
        dju = 100 + m
        idx[f"2025-{m:02d}"] = {"dju_chauffe": dju, "dju_froid": 0}
        conso[f"2025-{m:02d}"] = 2 * dju + 50  # slope 2
        idx[f"2026-{m:02d}"] = {"dju_chauffe": dju, "dju_froid": 0}
        conso[f"2026-{m:02d}"] = 3 * dju + 50  # slope 3
    thermal = _fluids_thermal(idx, conso)
    assert thermal["sensitivity_kwh_per_dju"] == 3.0
    assert thermal["sensitivity_previous"] == 2.0
    assert thermal["sensitivity_delta_pct"] == 50.0
    assert thermal["window_months"] == 12
    assert thermal["current_period"] == "01/2026 – 12/2026"
    assert thermal["previous_period"] == "01/2025 – 12/2025"
    assert thermal["reliable"] is True


def test_thermal_no_previous_window_when_short_history():
    # 12 mois seulement : fenêtre courante pleine, pas de fenêtre précédente → delta None
    # (on n'invente pas une évolution sans historique comparable).
    idx = {}
    conso = {}
    for m in range(1, 13):
        dju = 100 + m
        idx[f"2026-{m:02d}"] = {"dju_chauffe": dju, "dju_froid": 0}
        conso[f"2026-{m:02d}"] = 2 * dju + 50
    thermal = _fluids_thermal(idx, conso)
    assert thermal["sensitivity_kwh_per_dju"] == 2.0
    assert thermal["sensitivity_previous"] is None
    assert thermal["sensitivity_delta_pct"] is None
    assert thermal["reliable"] is True


def test_get_fluids_climate_empty_is_safe(monkeypatch):
    monkeypatch.setattr(energie_mod, "_dju_monthly_index", lambda: {})
    out = get_fluids_climate()
    assert out["current_year"] == 0
    assert out["thermal"]["reliable"] is False
    assert out["heating"]["monthly"] == []
