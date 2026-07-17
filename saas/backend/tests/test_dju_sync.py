import csv
from datetime import date, timedelta

from app.services import dju_sync
from app.services.dju_profiles import DjuProfile


def test_dju_sync_ignores_invalid_existing_dates(monkeypatch, tmp_path):
    csv_path = tmp_path / "dju_test.csv"
    yesterday = date.today() - timedelta(days=1)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "dju_chauffage_base_18"])
        writer.writeheader()
        writer.writerow({"date": "lier", "dju_chauffage_base_18": "0"})
        writer.writerow({"date": yesterday.isoformat(), "dju_chauffage_base_18": "1"})

    profile = DjuProfile(
        code="test",
        label="Test DJU",
        city="Sete",
        country="FR",
        csv_filename="dju_test.csv",
        heating_base_c=18.0,
        cooling_base_c=None,
        station_label="Sete",
        source_label="Test",
    )
    monkeypatch.setattr(dju_sync, "_csv_path", lambda _: csv_path)

    last_sync_date, added = dju_sync._sync_profile(profile)

    assert last_sync_date == yesterday.isoformat()
    assert added == 0
