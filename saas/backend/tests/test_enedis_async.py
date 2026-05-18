from __future__ import annotations

import csv
from datetime import date

import pytest

from app.models.enedis_async import TYPE_DONNEE_CDC, TYPE_DONNEE_ENERGIE
from app.services import enedis_async


def test_validate_request_rejects_cdc_over_7_days() -> None:
    with pytest.raises(ValueError, match="7 jours par appel"):
        enedis_async._validate_request(
            TYPE_DONNEE_CDC,
            date(2026, 1, 1),
            date(2026, 1, 9),
            ["24300144543450"],
        )


def test_validate_request_accepts_cdc_7_day_window() -> None:
    enedis_async._validate_request(
        TYPE_DONNEE_CDC,
        date(2026, 1, 1),
        date(2026, 1, 8),
        ["24300144543450"],
    )


def test_iter_date_windows_splits_backfill_by_7_days() -> None:
    windows = list(
        enedis_async._iter_date_windows(
            date(2026, 1, 1),
            date(2026, 1, 20),
            7,
        )
    )

    assert windows == [
        (date(2026, 1, 1), date(2026, 1, 8)),
        (date(2026, 1, 8), date(2026, 1, 15)),
        (date(2026, 1, 15), date(2026, 1, 20)),
    ]


def test_load_prms_for_type_filters_communicant_open_services(tmp_path, monkeypatch) -> None:
    contracts_path = tmp_path / "enedis_contracts.csv"
    summary_path = tmp_path / "enedis_contract_summary.csv"

    with contracts_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["usage_point_id"])
        writer.writeheader()
        writer.writerows(
            [
                {"usage_point_id": "24300144543450"},
                {"usage_point_id": "24300723476755"},
                {"usage_point_id": "24302170625476"},
                {"usage_point_id": "24304196703989"},
            ]
        )

    with summary_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["usage_point_id", "services_level"])
        writer.writeheader()
        writer.writerows(
            [
                {
                    "usage_point_id": "24300144543450",
                    "services_level": "Communicant (ouvert aux services)",
                },
                {
                    "usage_point_id": "24300723476755",
                    "services_level": "Communicant (non ouvert aux services)",
                },
                {"usage_point_id": "24302170625476", "services_level": "Non communicant"},
                {"usage_point_id": "24304196703989", "services_level": ""},
            ]
        )

    monkeypatch.setattr(enedis_async.settings, "energie_dir", str(tmp_path))

    assert enedis_async._load_prms_for_type(TYPE_DONNEE_CDC) == ["24300144543450"]
    assert enedis_async._load_prms_for_type(TYPE_DONNEE_ENERGIE) == ["24300144543450"]
