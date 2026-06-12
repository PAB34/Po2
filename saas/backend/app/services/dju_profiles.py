from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings


@dataclass(frozen=True)
class DjuProfile:
    code: str
    label: str
    city: str
    country: str
    csv_filename: str
    heating_base_c: float
    cooling_base_c: float | None
    station_label: str
    source_label: str
    reference_dju: float | None = None
    reference_period: str | None = None
    heating_period: str | None = None
    contractual: bool = False
    compliant_source: bool = False
    notes: str | None = None


DALKIA_CONTRACT_PROFILE = DjuProfile(
    code="dalkia_contractuel",
    label="DALKIA contractuel",
    city="Montpellier",
    country="FR",
    csv_filename="dju_dalkia_montpellier.csv",
    heating_base_c=18.0,
    cooling_base_c=None,
    station_label="Montpellier",
    source_label="METEOCLIM COSTIC",
    reference_dju=1426.0,
    reference_period="1981-2010",
    heating_period="1er octobre -> 31 mai, puis dates effectives de chauffe",
    contractual=True,
    compliant_source=False,
    notes=(
        "Le contrat impose Montpellier / METEOCLIM COSTIC. Le moteur actuel reconstitue les DJU "
        "depuis Open-Meteo et doit etre qualifie tant que la station/source contractuelle n'est pas branchee."
    ),
)


EXPLOITATION_SETE_PROFILE = DjuProfile(
    code="exploitation_sete",
    label="Exploitation patrimoine Sete",
    city="Sète",
    country="FR",
    csv_filename="dju_sete.csv",
    heating_base_c=18.0,
    cooling_base_c=22.0,
    station_label="Sete",
    source_label="Open-Meteo archive",
    reference_dju=None,
    reference_period=None,
    heating_period="Reglage exploitation courant",
    contractual=False,
    compliant_source=True,
)


def dju_profile_payload(profile: DjuProfile) -> dict:
    return {
        "profile_code": profile.code,
        "profile_label": profile.label,
        "heating_base_c": profile.heating_base_c,
        "cooling_base_c": profile.cooling_base_c,
        "station_label": profile.station_label,
        "source_label": profile.source_label,
        "reference_dju": profile.reference_dju,
        "reference_period": profile.reference_period,
        "heating_period": profile.heating_period,
        "contractual": profile.contractual,
        "compliant_source": profile.compliant_source,
        "notes": profile.notes,
    }


def dju_csv_path(profile: DjuProfile) -> Path:
    return Path(settings.energie_dir) / "DJU" / profile.csv_filename


def read_dju_rows(profile: DjuProfile) -> list[dict[str, str]]:
    path = dju_csv_path(profile)
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def dju_heating_column(profile: DjuProfile) -> str:
    return f"dju_chauffage_base_{int(profile.heating_base_c)}"


def dju_cooling_column(profile: DjuProfile) -> str | None:
    if profile.cooling_base_c is None:
        return None
    return f"dju_froid_base_{int(profile.cooling_base_c)}"


def safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def aggregate_dju_monthly(profile: DjuProfile) -> list[dict[str, Any]]:
    h_col = dju_heating_column(profile)
    c_col = dju_cooling_column(profile)
    by_month: dict[str, dict[str, float]] = {}
    for row in read_dju_rows(profile):
        raw_date = row.get("date", "")
        if len(raw_date) < 7:
            continue
        month = raw_date[:7]
        entry = by_month.setdefault(month, {"dju_chauffe": 0.0, "dju_froid": 0.0})
        entry["dju_chauffe"] += safe_float(row.get(h_col)) or 0.0
        if c_col:
            entry["dju_froid"] += safe_float(row.get(c_col)) or 0.0
    return [
        {
            "month": month,
            "dju_chauffe": round(values["dju_chauffe"], 1),
            "dju_froid": round(values["dju_froid"], 1),
        }
        for month, values in sorted(by_month.items())
    ]


def is_dalkia_heating_month(month: int) -> bool:
    return month in {1, 2, 3, 4, 5, 10, 11, 12}
