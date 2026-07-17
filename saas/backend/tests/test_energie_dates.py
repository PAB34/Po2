from app.services import energie


def test_energy_csv_dates_accept_iso_and_french_formats(monkeypatch):
    rows = [
        {"usage_point_id": "PRM1", "date": "2026-02-16", "value_wh": "1000"},
        {"usage_point_id": "PRM1", "date": "17/02/2026", "value_wh": "2000"},
        {"usage_point_id": "PRM1", "date": "18-02-2026", "value_wh": "3000"},
        {"usage_point_id": "PRM1", "date": "bad-date", "value_wh": "4000"},
    ]

    monkeypatch.setattr(energie, "_csv_rows", lambda filename: rows if filename == "enedis_data.csv" else [])
    energie._daily_consumption_index.cache_clear()
    energie._consumption_by_month.cache_clear()

    try:
        index = energie._daily_consumption_index()
        assert [point["date"] for point in index["PRM1"]] == ["2026-02-16", "2026-02-17", "2026-02-18"]
        assert energie._consumption_by_month()["PRM1"] == {"2026-02": 6.0}
    finally:
        energie._daily_consumption_index.cache_clear()
        energie._consumption_by_month.cache_clear()


def test_dju_monthly_accepts_iso_and_french_dates(monkeypatch):
    rows = [
        {"date": "2026-02-16", "dju_chauffage_base_18": "1", "dju_froid_base_22": "0"},
        {"date": "17/02/2026", "dju_chauffage_base_18": "2", "dju_froid_base_22": "0.5"},
        {"date": "bad-date", "dju_chauffage_base_18": "100", "dju_froid_base_22": "100"},
    ]

    monkeypatch.setattr(energie, "_dju_rows", lambda: rows)
    energie._dju_monthly_index.cache_clear()

    try:
        assert energie._dju_monthly_index() == {"2026-02": {"dju_chauffe": 3.0, "dju_froid": 0.5}}
        assert energie.get_dju_monthly() == [{"month": "2026-02", "dju_chauffe": 3.0, "dju_froid": 0.5}]
    finally:
        energie._dju_monthly_index.cache_clear()
