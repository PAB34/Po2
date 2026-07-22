"""
Tests de fiabilité de l'état de synchronisation ENEDIS.

Régression couverte : l'état persistant enregistrait la date *demandée*
(`today - 1`) et non la date *réellement reçue*. ENEDIS publiant avec un décalage
variable, chaque run laissait un trou d'un jour, jamais redemandé puisque la sync
incrémentale repart de `last_sync + 1`.

Pour exécuter :
    cd saas/backend && pytest tests/test_enedis_sync_state.py -v
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.services import enedis_sync


@pytest.fixture()
def energie_dir(tmp_path, monkeypatch):
    """Isole settings.energie_dir et vide le memo de couverture."""
    monkeypatch.setattr(enedis_sync.settings, "energie_dir", str(tmp_path))
    enedis_sync._COVERAGE_MEMO["signature"] = None
    enedis_sync._COVERAGE_MEMO["value"] = None
    return tmp_path


def _write_csv(path, days: list[str]) -> None:
    lines = ["usage_point_id,date,value_wh,unit,quality,flow_direction,_ingested_at_utc"]
    for day in days:
        lines.append(f"11111111111111,{day},1000,Wh,BRUT,consumption,2026-07-22T00:00:00Z")
    (path / "enedis_data.csv").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# Couverture réelle du CSV
# ---------------------------------------------------------------------------


def test_coverage_reports_real_max_date(energie_dir) -> None:
    _write_csv(energie_dir, ["2026-07-13", "2026-07-14", "2026-07-15"])
    cov = enedis_sync._csv_coverage()
    assert cov["data_min_date"] == "2026-07-13"
    assert cov["data_max_date"] == "2026-07-15"
    assert cov["missing_days"] == 0


def test_coverage_detects_interior_gap(energie_dir) -> None:
    """Le trou du 2026-06-10 constaté en prod doit être remonté."""
    _write_csv(energie_dir, ["2026-06-09", "2026-06-11", "2026-06-12"])
    cov = enedis_sync._csv_coverage()
    assert cov["missing_days"] == 1
    assert cov["missing_days_sample"] == ["2026-06-10"]


def test_coverage_empty_when_no_csv(energie_dir) -> None:
    cov = enedis_sync._csv_coverage()
    assert cov["data_max_date"] is None
    assert cov["missing_days"] == 0


def test_status_exposes_gap_between_state_and_data(energie_dir) -> None:
    """Reproduit la prod du 2026-07-22 : état à J+1 sur la donnée réelle."""
    _write_csv(energie_dir, ["2026-07-14", "2026-07-15"])
    enedis_sync._save_persistent_state("2026-07-16")

    status = enedis_sync.get_sync_status()
    assert status["last_sync_date"] == "2026-07-16"
    assert status["data_max_date"] == "2026-07-15"
    # L'écart est désormais visible au lieu d'être masqué.
    assert status["data_max_date"] < status["last_sync_date"]


# ---------------------------------------------------------------------------
# L'état n'avance pas au-delà de la donnée reçue
# ---------------------------------------------------------------------------


def _run_sync_with(
    monkeypatch, energie_dir, returned_days: list[str], history_days: int | None = 5
) -> None:
    """Exécute la sync en simulant ENEDIS renvoyant exactement `returned_days`."""
    (energie_dir / "enedis_contracts.csv").write_text(
        "usage_point_id\n11111111111111\n", encoding="utf-8-sig"
    )
    monkeypatch.setattr(enedis_sync, "_get_token", lambda: "fake-token")

    def fake_fetch(token, prm, start_date, end_date, ingested_at):
        rows = [
            {
                "usage_point_id": prm,
                "date": day,
                "value_wh": 1000.0,
                "unit": "Wh",
                "quality": "BRUT",
                "flow_direction": "consumption",
                "_ingested_at_utc": ingested_at,
            }
            for day in returned_days
            if start_date <= day <= end_date
        ]
        return rows, ("ok_data" if rows else "ok_empty")

    monkeypatch.setattr(enedis_sync, "_fetch_one_prm", fake_fetch)
    enedis_sync._SYNC_STATE["status"] = "idle"
    enedis_sync.run_daily_consumption_sync(history_days=history_days)
    enedis_sync._COVERAGE_MEMO["signature"] = None


def test_state_stops_at_last_received_day(monkeypatch, energie_dir) -> None:
    """ENEDIS s'arrête à J-2 : l'état ne doit pas enregistrer J-1."""
    today = date.today()
    requested_end = today - timedelta(days=1)
    received_end = today - timedelta(days=2)
    _run_sync_with(monkeypatch, energie_dir, [received_end.isoformat()])

    saved = enedis_sync._load_persistent_state()["last_sync_date"]
    assert saved == received_end.isoformat()
    assert saved != requested_end.isoformat(), "l'état ne doit pas dépasser la donnée reçue"


def test_state_does_not_advance_when_nothing_received(monkeypatch, energie_dir) -> None:
    """Une fenêtre entièrement vide ne doit pas faire avancer l'état."""
    enedis_sync._save_persistent_state("2026-01-01")
    _run_sync_with(monkeypatch, energie_dir, [])

    assert enedis_sync._load_persistent_state()["last_sync_date"] == "2026-01-01"


def test_empty_day_is_requested_again_on_next_run(monkeypatch, energie_dir) -> None:
    """Auto-réparation : le jour resté vide est redemandé, puis comblé."""
    today = date.today()
    day_j2 = (today - timedelta(days=2)).isoformat()
    day_j1 = (today - timedelta(days=1)).isoformat()

    # Run 1 : ENEDIS n'a pas encore publié J-1.
    _run_sync_with(monkeypatch, energie_dir, [day_j2])
    assert enedis_sync._load_persistent_state()["last_sync_date"] == day_j2

    # Run 2 : J-1 est publié — il est bien récupéré, sans trou.
    _run_sync_with(monkeypatch, energie_dir, [day_j2, day_j1])
    assert enedis_sync._load_persistent_state()["last_sync_date"] == day_j1

    cov = enedis_sync._csv_coverage()
    assert cov["data_max_date"] == day_j1
    assert cov["missing_days"] == 0


def test_inherited_ahead_state_is_repaired(monkeypatch, energie_dir) -> None:
    """État hérité en avance sur la donnée (cas prod 2026-07-22) : le jour sauté
    est bien re-collecté au lieu d'être perdu définitivement."""
    today = date.today()
    day_j3 = (today - timedelta(days=3)).isoformat()
    day_j2 = (today - timedelta(days=2)).isoformat()

    _write_csv(energie_dir, [day_j3])
    # État corrompu par l'ancien code : une journée d'avance sur le CSV.
    enedis_sync._save_persistent_state(day_j2)
    enedis_sync._COVERAGE_MEMO["signature"] = None

    # Sync incrémentale (history_days=None) : sans réparation, elle repartirait
    # après day_j2 et day_j2 ne serait jamais collecté.
    _run_sync_with(monkeypatch, energie_dir, [day_j3, day_j2], history_days=None)

    cov = enedis_sync._csv_coverage()
    assert cov["data_max_date"] == day_j2
    assert cov["missing_days"] == 0
