import sqlite3

from app.services import load_curve_store


def _create_load_curve_index(directory):
    db_path = directory / "enedis_load_curve.sqlite"
    con = sqlite3.connect(db_path)
    try:
        con.execute("CREATE TABLE load_curve (prm_id TEXT NOT NULL, dt TEXT NOT NULL, value_w REAL NOT NULL)")
        con.executemany(
            "INSERT INTO load_curve VALUES (?, ?, ?)",
            [
                ("PRM1", "2026-02-16T00:00:00", 100.0),
                ("PRM1", "2026-02-16T00:30:00", 110.0),
                ("PRM1", "2026-02-17T00:00:00", 120.0),
                ("PRM2", "2026-03-01T00:00:00", 200.0),
            ],
        )
        con.commit()
    finally:
        con.close()
    return db_path


def test_load_curve_sqlite_summaries(monkeypatch, tmp_path):
    _create_load_curve_index(tmp_path)
    monkeypatch.setattr(load_curve_store.settings, "energie_dir", str(tmp_path))

    assert load_curve_store.data_range_summary() == {
        "first_date": "2026-02-16",
        "last_date": "2026-03-01",
        "row_count": 4,
        "stale": False,
    }

    coverage = load_curve_store.coverage_summary()
    assert coverage["first_date"] == "2026-02-16"
    assert coverage["last_date"] == "2026-03-01"
    assert coverage["row_count"] == 4
    assert coverage["bad_date_rows"] == 0
    assert coverage["prms"] == {
        "PRM1": {
            "row_count": 3,
            "covered_days": 2,
            "first_date": "2026-02-16",
            "last_date": "2026-02-17",
        },
        "PRM2": {
            "row_count": 1,
            "covered_days": 1,
            "first_date": "2026-03-01",
            "last_date": "2026-03-01",
        },
    }
