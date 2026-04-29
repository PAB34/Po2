"""
DJU Sète — récupération Open-Meteo + calcul DJU chauffage (COSTIC) et froid (Météo-France).

Usage :
    python scripts/dju_sete.py

Variables d'environnement (toutes optionnelles) :
    CITY_NAME            Nom de la ville (défaut : Sète)
    COUNTRY_CODE         Code pays ISO 2 lettres (défaut : FR)
    BASE_HEATING         Seuil chauffage en °C (défaut : 18.0)
    BASE_COOLING         Seuil froid en °C (défaut : 22.0)
    HISTORY_START_DATE   Date de début du backfill initial YYYY-MM-DD (défaut : 2015-01-01)
    DJU_OUTPUT_PATH      Chemin du CSV de sortie (défaut : DJU/dju_sete.csv)
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
LOG = logging.getLogger(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def get_location(name: str, country_code: str = "FR") -> tuple[float, float, str]:
    params = {"name": name, "count": 1, "language": "fr", "format": "json", "countryCode": country_code}
    r = requests.get(GEOCODING_URL, params=params, timeout=30)
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise ValueError(f"Aucune localisation trouvée pour {name} ({country_code}).")
    loc = results[0]
    LOG.info("Localisation : %s (lat=%.4f, lon=%.4f, tz=%s).", loc.get("name"), loc["latitude"], loc["longitude"], loc.get("timezone"))
    return loc["latitude"], loc["longitude"], loc.get("timezone", "Europe/Paris")


def get_archive_daily(lat: float, lon: float, tz: str, start_date: str, end_date: str) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_min,temperature_2m_max",
        "timezone": tz,
    }
    r = requests.get(ARCHIVE_URL, params=params, timeout=60)
    r.raise_for_status()
    daily = r.json().get("daily")
    if not daily:
        raise ValueError("Réponse Open-Meteo invalide : bloc 'daily' absent.")
    df = pd.DataFrame({"date": daily["time"], "tmin_c": daily["temperature_2m_min"], "tmax_c": daily["temperature_2m_max"]})
    LOG.info("Open-Meteo : %d jours récupérés (%s → %s).", len(df), start_date, end_date)
    return df


def dju_heating_costic(tmin: float, tmax: float, base: float = 18.0) -> float | None:
    """DJU chauffage méthode COSTIC 3 cas (base 18 °C par défaut)."""
    if pd.isna(tmin) or pd.isna(tmax):
        return None
    if base >= tmax:
        return round(base - (tmin + tmax) / 2, 2)
    if base <= tmin:
        return 0.0
    a = tmax - tmin
    if a == 0:
        return 0.0
    b = (base - tmin) / a
    return round(a * b * (0.08 + 0.42 * b), 2)


def dju_cooling_mean(tmin: float, tmax: float, base: float = 22.0) -> float | None:
    """DJU froid méthode Météo-France : Tm = (Tmin+Tmax)/2, DJ = max(Tm-base, 0)."""
    if pd.isna(tmin) or pd.isna(tmax):
        return None
    return round(max((tmin + tmax) / 2 - base, 0), 2)


def _heating_season(d: pd.Timestamp) -> str:
    """Saison chauffe : Sep N → Aout N+1, label 'N/N+1'."""
    return f"{d.year}/{d.year + 1}" if d.month >= 9 else f"{d.year - 1}/{d.year}"


def _cooling_season(d: pd.Timestamp) -> str:
    """Saison froid : Mai → Sep, label 'N'. Hors saison : chaine vide."""
    return str(d.year) if 5 <= d.month <= 9 else ""


def compute_dju(df: pd.DataFrame, base_heating: float, base_cooling: float) -> pd.DataFrame:
    df = df.copy()
    df["tmoy_c"] = ((df["tmin_c"] + df["tmax_c"]) / 2).round(2)
    df[f"dju_chauffage_base_{int(base_heating)}"] = df.apply(
        lambda r: dju_heating_costic(r["tmin_c"], r["tmax_c"], base_heating), axis=1
    )
    df[f"dju_froid_base_{int(base_cooling)}"] = df.apply(
        lambda r: dju_cooling_mean(r["tmin_c"], r["tmax_c"], base_cooling), axis=1
    )
    return df


def merge_and_recompute(df_new: pd.DataFrame, output_file: Path, base_heating: float, base_cooling: float) -> pd.DataFrame:
    h_col = f"dju_chauffage_base_{int(base_heating)}"
    c_col = f"dju_froid_base_{int(base_cooling)}"

    raw_cols = ["date", "tmin_c", "tmax_c", "tmoy_c", h_col, c_col]

    if output_file.exists() and output_file.stat().st_size > 0:
        df_old = pd.read_csv(output_file)
        # Ne garder que les colonnes brutes pour eviter doublons de cumuls
        keep = [c for c in raw_cols if c in df_old.columns]
        df_old = df_old[keep]
        df_new2 = df_new[[c for c in raw_cols if c in df_new.columns]]
        df = pd.concat([df_old, df_new2], ignore_index=True)
        df = df.drop_duplicates(subset=["date"], keep="last")
    else:
        df = df_new[[c for c in raw_cols if c in df_new.columns]]

    df = df.sort_values("date").reset_index(drop=True)
    dates = pd.to_datetime(df["date"])

    # Saisons
    df["saison_chauffe"] = dates.apply(_heating_season)   # ex. '2024/2025'
    df["saison_froid"]   = dates.apply(_cooling_season)   # ex. '2025' ou ''

    # Cumuls annuels (depuis le 1er jan de chaque annee civile)
    df["annee"] = dates.dt.year.astype(str)
    df[f"cum_annuel_{h_col}"]  = df.groupby("annee")[h_col].cumsum().round(2)
    df[f"cum_annuel_{c_col}"]  = df.groupby("annee")[c_col].cumsum().round(2)

    # Cumuls saisonniers
    df[f"cum_saison_{h_col}"] = df.groupby("saison_chauffe")[h_col].cumsum().round(2)
    # Froid : cumul uniquement en saison (Mai-Sep), 0 hors saison
    df[f"cum_saison_{c_col}"] = (
        df[df["saison_froid"] != ""].groupby("saison_froid")[c_col].cumsum().round(2)
    )
    df[f"cum_saison_{c_col}"] = df[f"cum_saison_{c_col}"].fillna(0)

    df = df.drop(columns=["annee"])
    return df


def main() -> int:
    city = os.getenv("CITY_NAME", "Sète")
    country = os.getenv("COUNTRY_CODE", "FR")
    base_heating = float(os.getenv("BASE_HEATING", "18.0"))
    base_cooling = float(os.getenv("BASE_COOLING", "22.0"))
    history_start = os.getenv("HISTORY_START_DATE", "2015-01-01")
    output_path = Path(os.getenv("DJU_OUTPUT_PATH", "DJU/dju_sete.csv"))

    try:
        lat, lon, tz = get_location(city, country)

        today = date.today()
        end_date = today - timedelta(days=1)

        if output_path.exists() and output_path.stat().st_size > 0:
            df_existing = pd.read_csv(output_path)
            last_date = pd.to_datetime(df_existing["date"]).dt.date.max()
            start_date = last_date + timedelta(days=1)
        else:
            start_date = date.fromisoformat(history_start)
            LOG.info("Aucun fichier existant — backfill depuis %s.", history_start)

        if start_date > end_date:
            LOG.info("DJU déjà à jour (dernier : %s).", start_date - timedelta(days=1))
            return 0

        LOG.info("Collecte %s → %s pour %s.", start_date, end_date, city)
        df_new = get_archive_daily(lat, lon, tz, start_date.isoformat(), end_date.isoformat())
        df_new = compute_dju(df_new, base_heating, base_cooling)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_final = merge_and_recompute(df_new, output_path, base_heating, base_cooling)
        df_final.to_csv(output_path, index=False, encoding="utf-8")

        LOG.info("CSV mis à jour : %s (%d lignes totales).", output_path, len(df_final))
        LOG.info("\n%s", df_final.tail(5).to_string(index=False))
        return 0

    except Exception as exc:
        LOG.error("Erreur fatale : %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
