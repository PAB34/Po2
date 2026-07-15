"""Année par défaut de l'atterrissage élec = dernière année significative (sujet #1)."""

import datetime

from app.services.engie_elec_budget_revise import _years_overview


def _lines(year, months):
    return [
        {"period_start": datetime.date(year, m, 1), "period_end": datetime.date(year, m, 28)}
        for m in months
    ]


def test_recommends_last_full_year_when_current_is_partial():
    by_prm = {"prm1": {"lines": _lines(2025, range(1, 13)) + _lines(2026, [1, 2])}}
    available, recommended = _years_overview(by_prm, current_year=2026)
    assert available == [2025, 2026]
    assert recommended == 2025  # 2026 n'a que 2 mois → non significatif


def test_recommends_current_year_once_it_is_mature():
    by_prm = {"prm1": {"lines": _lines(2025, range(1, 13)) + _lines(2026, range(1, 8))}}
    _, recommended = _years_overview(by_prm, current_year=2026)
    assert recommended == 2026  # 7 mois couverts → significatif


def test_no_data_falls_back_to_current_year():
    available, recommended = _years_overview({}, current_year=2026)
    assert available == []
    assert recommended == 2026
