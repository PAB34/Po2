import csv
import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings


def _energie_path(*parts: str) -> Path:
    configured = Path(settings.energie_dir)
    if configured.exists():
        return configured.joinpath(*parts)
    repo_output = Path(__file__).resolve().parents[3] / "energie" / "output"
    return repo_output.joinpath(*parts)


def _load_diagnostic(filename: str) -> dict[str, str]:
    """Charge un fichier de diagnostic (mapping PRM → outcome). Tolérant aux absences."""
    path = _energie_path(filename)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    outcomes = data.get("outcomes", {})
    if isinstance(outcomes, dict):
        return {str(k): str(v) for k, v in outcomes.items()}
    return {}


def _load_lc_outcomes() -> dict[str, str]:
    """Le rapport CDC stocke les outcomes dans `prms_by_outcome` (liste par outcome)."""
    path = _energie_path("enedis_lc_report.json")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    by_outcome = data.get("prms_by_outcome", {})
    if not isinstance(by_outcome, dict):
        return {}
    result: dict[str, str] = {}
    for outcome, prm_list in by_outcome.items():
        if not isinstance(prm_list, list):
            continue
        for prm_id in prm_list:
            result[str(prm_id)] = str(outcome)
    return result


def _meter_profile(service_level: str | None, connection_state: str | None) -> str:
    """Classe le profil compteur d'après les métadonnées contractuelles ENEDIS.

    Valeurs : non_powered | non_communicant | communicant_closed | communicant_open | unknown
    """
    state_lower = (connection_state or "").lower()
    if state_lower and ("non aliment" in state_lower or "coup" in state_lower):
        return "non_powered"
    sl = (service_level or "").lower()
    if not sl:
        return "unknown"
    if "non communicant" in sl:
        return "non_communicant"
    if "communicant" in sl:
        if "non ouvert" in sl or "non-ouvert" in sl:
            return "communicant_closed"
        return "communicant_open"
    return "unknown"


def _scan_csv_dates(rel_path: str, date_col: str) -> dict[str, Any]:
    """Scanne un CSV en streaming pour trouver première/dernière date et nombre de lignes."""
    path = _energie_path(rel_path)
    if not path.exists() or path.stat().st_size == 0:
        return {"first_date": None, "last_date": None, "row_count": 0}
    min_d = max_d = None
    count = 0
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return {"first_date": None, "last_date": None, "row_count": 0}
        try:
            col_idx = header.index(date_col)
        except ValueError:
            return {"first_date": None, "last_date": None, "row_count": 0}
        for row in reader:
            if len(row) > col_idx:
                d = row[col_idx][:10]
                if len(d) == 10:
                    count += 1
                    if min_d is None or d < min_d:
                        min_d = d
                    if max_d is None or d > max_d:
                        max_d = d
    return {"first_date": min_d, "last_date": max_d, "row_count": count}


def _source_coverage(rel_path: str, date_col: str) -> dict[str, Any]:
    path = _energie_path(rel_path)
    if not path.exists() or path.stat().st_size == 0:
        return {
            "first_date": None,
            "last_date": None,
            "row_count": 0,
            "bad_date_rows": 0,
            "prms": {},
        }

    first_date = last_date = None
    row_count = 0
    bad_date_rows = 0
    prms: dict[str, dict[str, Any]] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return {
                "first_date": None,
                "last_date": None,
                "row_count": 0,
                "bad_date_rows": 0,
                "prms": {},
            }
        try:
            prm_idx = header.index("usage_point_id")
            date_idx = header.index(date_col)
        except ValueError:
            return {
                "first_date": None,
                "last_date": None,
                "row_count": 0,
                "bad_date_rows": 0,
                "prms": {},
            }

        for row in reader:
            if len(row) <= max(prm_idx, date_idx):
                continue
            prm_id = row[prm_idx].strip()
            raw_date = row[date_idx][:10]
            if not prm_id:
                continue
            try:
                parsed_date = date.fromisoformat(raw_date)
            except ValueError:
                bad_date_rows += 1
                continue

            row_count += 1
            if first_date is None or raw_date < first_date:
                first_date = raw_date
            if last_date is None or raw_date > last_date:
                last_date = raw_date

            entry = prms.setdefault(
                prm_id,
                {
                    "row_count": 0,
                    "dates": set(),
                    "first_date": raw_date,
                    "last_date": raw_date,
                },
            )
            entry["row_count"] += 1
            entry["dates"].add(parsed_date)
            if raw_date < entry["first_date"]:
                entry["first_date"] = raw_date
            if raw_date > entry["last_date"]:
                entry["last_date"] = raw_date

    normalized_prms = {}
    for prm_id, entry in prms.items():
        span_days = (date.fromisoformat(entry["last_date"]) - date.fromisoformat(entry["first_date"])).days + 1
        covered_days = len(entry["dates"])
        normalized_prms[prm_id] = {
            "row_count": entry["row_count"],
            "covered_days": covered_days,
            "first_date": entry["first_date"],
            "last_date": entry["last_date"],
            "span_days": span_days,
            "coverage_ratio_in_span": round(covered_days / span_days, 3) if span_days else 0,
        }

    return {
        "first_date": first_date,
        "last_date": last_date,
        "row_count": row_count,
        "bad_date_rows": bad_date_rows,
        "prms": normalized_prms,
    }


@lru_cache(maxsize=1)
def get_data_ranges() -> dict[str, Any]:
    """Retourne les plages de dates disponibles pour chaque source de données."""
    # Contrats : simple comptage
    contracts_count = 0
    cp = _energie_path("enedis_contracts.csv")
    if cp.exists():
        with open(cp, encoding="utf-8-sig") as f:
            contracts_count = max(0, sum(1 for _ in f) - 1)

    return {
        "consumption": _scan_csv_dates("enedis_data.csv", "date"),
        "max_power": _scan_csv_dates("enedis_max_power.csv", "date"),
        "load_curve": _scan_csv_dates("enedis_load_curve.csv", "datetime"),
        "dju": _scan_csv_dates("DJU/dju_sete.csv", "date"),
        "contracts": {"count": contracts_count},
    }


@lru_cache(maxsize=1)
def get_data_audit() -> dict[str, Any]:
    contracts = _contracts()
    summaries = _summaries()
    connections = _connections()
    contract_prms = set(contracts)
    source_configs = {
        "consumption": {
            "label": "Consommation journaliere",
            "filename": "enedis_data.csv",
            "date_col": "date",
            "min_days": 30,
        },
        "load_curve": {
            "label": "Courbe de charge",
            "filename": "enedis_load_curve.csv",
            "date_col": "datetime",
            "min_days": 30,
        },
        "max_power": {
            "label": "Puissance max journaliere",
            "filename": "enedis_max_power.csv",
            "date_col": "date",
            "min_days": 30,
        },
    }
    coverages = {
        key: _source_coverage(config["filename"], config["date_col"])
        for key, config in source_configs.items()
    }
    source_prms = {key: set(value["prms"]) for key, value in coverages.items()}

    # Diagnostics ENEDIS par PRM/source (résultat de la dernière sync)
    diagnostics = {
        "consumption": _load_diagnostic("enedis_data_diagnostic.json"),
        "max_power": _load_diagnostic("enedis_mp_diagnostic.json"),
        "load_curve": _load_lc_outcomes(),
    }

    combo_counts: dict[str, int] = {}
    missing_by_segment: dict[str, dict[str, int]] = {key: {} for key in source_configs}
    profile_counts: dict[str, int] = {
        "non_powered": 0,
        "non_communicant": 0,
        "communicant_closed": 0,
        "communicant_open": 0,
        "unknown": 0,
    }
    rows: list[dict[str, Any]] = []
    correctable = {
        "backfill_consumption": 0,
        "backfill_load_curve": 0,
        "backfill_max_power": 0,
        "non_communicant_structural": 0,
        "cdc_activation_needed": 0,
        "api_rights_issue": 0,
        "non_powered_normal": 0,
    }

    for prm_id in sorted(contract_prms):
        contract = contracts[prm_id]
        summary = summaries.get(prm_id) or {}
        connection = connections.get(prm_id) or {}
        segment = contract.get("0_segment") or summary.get("segments_0_segment") or "Inconnu"
        service_level = summary.get("services_level")
        connection_state = connection.get("connection_state")
        meter_profile = _meter_profile(service_level, connection_state)
        profile_counts[meter_profile] = profile_counts.get(meter_profile, 0) + 1

        present_sources = [key for key in source_configs if prm_id in source_prms[key]]
        missing_sources = [key for key in source_configs if prm_id not in source_prms[key]]
        weak_sources: list[str] = []
        coverage_days: dict[str, int] = {}
        first_dates: dict[str, str | None] = {}
        last_dates: dict[str, str | None] = {}
        enedis_outcomes: dict[str, str | None] = {}

        for key, config in source_configs.items():
            prm_stats = coverages[key]["prms"].get(prm_id)
            coverage_days[key] = prm_stats["covered_days"] if prm_stats else 0
            first_dates[key] = prm_stats["first_date"] if prm_stats else None
            last_dates[key] = prm_stats["last_date"] if prm_stats else None
            if prm_stats and prm_stats["covered_days"] < config["min_days"]:
                weak_sources.append(key)
            if not prm_stats:
                missing_by_segment[key][segment] = missing_by_segment[key].get(segment, 0) + 1
            enedis_outcomes[key] = diagnostics[key].get(prm_id)

        combo_key = "+".join(present_sources) if present_sources else "none"
        combo_counts[combo_key] = combo_counts.get(combo_key, 0) + 1

        # Déterminer la sévérité et le diagnostic selon le profil compteur
        actions: list[str] = []
        if meter_profile == "non_powered":
            severity = "info"
            probable_reason = "PRM non alimente — absence de donnees normale."
            actions.append("Verifier l'etat contractuel/alimentation")
            correctable["non_powered_normal"] += 1
        elif meter_profile == "non_communicant":
            # Seule la conso journalière est attendue ; CDC et P max ne sont pas disponibles structurellement
            if "consumption" in missing_sources:
                severity = "warning"
                probable_reason = "Compteur non communicant : seule la conso journaliere est recuperable, et elle manque."
                actions.append("Verifier remontee compteur ENEDIS / relancer le backfill conso")
                correctable["backfill_consumption"] += 1
            else:
                severity = "ok"
                probable_reason = "Compteur non communicant : conso disponible, CDC/P max non disponibles structurellement."
            correctable["non_communicant_structural"] += 1
        elif meter_profile == "communicant_closed":
            # CDC bloquée par démarche admin, mais conso et P max attendues
            if "consumption" in missing_sources or "max_power" in missing_sources:
                severity = "warning"
                probable_reason = "Communicant non ouvert aux services : CDC bloquee par defaut, mais conso/P max devraient remonter."
                if "consumption" in missing_sources:
                    actions.append("Relancer le backfill conso journaliere")
                    correctable["backfill_consumption"] += 1
                if "max_power" in missing_sources:
                    actions.append("Relancer le backfill puissance max")
                    correctable["backfill_max_power"] += 1
            else:
                severity = "warning"
                probable_reason = "Communicant non ouvert aux services : CDC necessite une activation aupres d'ENEDIS."
            actions.append("Demander activation CDC aupres d'ENEDIS")
            correctable["cdc_activation_needed"] += 1
        elif meter_profile == "communicant_open":
            # Tous les flux sont attendus
            if not present_sources:
                severity = "critical"
                probable_reason = "Communicant ouvert aux services mais aucun flux remonte — anomalie a investiguer."
            elif missing_sources or weak_sources:
                severity = "warning"
                probable_reason = "Communicant ouvert : certains flux manquent ou sont incomplets."
            else:
                severity = "ok"
                probable_reason = "Donnees completes sur les trois flux."

            for source_key in missing_sources:
                outcome = enedis_outcomes.get(source_key)
                if outcome in ("access_not_subscribed", "forbidden", "not_found"):
                    actions.append(f"Verifier service/droits API ENEDIS ({source_key})")
                    correctable["api_rights_issue"] += 1
                elif outcome == "invalid_request":
                    actions.append(f"Verifier eligibilite/profil ENEDIS ou periode demandee ({source_key})")
                    correctable["api_rights_issue"] += 1
                elif outcome in ("error_technical", "quota_exceeded"):
                    actions.append(f"Relancer le backfill {source_key} (erreur technique au dernier essai)")
                    if source_key == "consumption":
                        correctable["backfill_consumption"] += 1
                    elif source_key == "load_curve":
                        correctable["backfill_load_curve"] += 1
                    elif source_key == "max_power":
                        correctable["backfill_max_power"] += 1
                elif outcome == "cdc_inactive":
                    actions.append("Demander activation CDC aupres d'ENEDIS")
                    correctable["cdc_activation_needed"] += 1
                elif outcome == "ok_empty":
                    actions.append(f"ENEDIS retourne vide pour {source_key} — verifier collecte / etat compteur")
                else:
                    if source_key == "consumption":
                        actions.append("Lancer le backfill conso journaliere")
                        correctable["backfill_consumption"] += 1
                    elif source_key == "load_curve":
                        actions.append("Lancer le backfill courbe de charge")
                        correctable["backfill_load_curve"] += 1
                    elif source_key == "max_power":
                        actions.append("Lancer le backfill puissance max")
                        correctable["backfill_max_power"] += 1
        else:
            # Profil inconnu : on garde l'ancienne logique défensive
            if not present_sources:
                severity = "warning"
                probable_reason = "Niveau de service compteur inconnu — flux absents."
                actions.append("Verifier le niveau de service ENEDIS pour ce PRM")
            elif missing_sources or weak_sources:
                severity = "warning"
                probable_reason = "Flux partiels et profil compteur inconnu."
            else:
                severity = "ok"
                probable_reason = "Donnees disponibles sur les trois flux."

        rows.append(
            {
                "usage_point_id": prm_id,
                "name": contract.get("0_organization_commercial_name") or contract.get("0_organization_name") or prm_id,
                "segment": segment,
                "contractor": contract.get("0_contractor"),
                "tariff": contract.get("0_distribution_tariff"),
                "subscribed_power_kva": _safe_float(contract.get("0_subscribed_power_value")),
                "service_level": service_level,
                "connection_state": connection_state,
                "meter_profile": meter_profile,
                "present_sources": present_sources,
                "missing_sources": missing_sources,
                "weak_sources": weak_sources,
                "coverage_days": coverage_days,
                "first_dates": first_dates,
                "last_dates": last_dates,
                "enedis_outcomes": enedis_outcomes,
                "probable_reason": probable_reason,
                "correctable_actions": sorted(set(actions)),
                "severity": severity,
            }
        )

    severity_rank = {"critical": 0, "warning": 1, "info": 2, "ok": 3}
    rows.sort(key=lambda item: (severity_rank.get(item["severity"], 9), -len(item["missing_sources"]), item["usage_point_id"]))

    sources = {}
    for key, config in source_configs.items():
        coverage = coverages[key]
        weak_count = sum(
            1
            for prm_id in contract_prms & source_prms[key]
            if coverage["prms"][prm_id]["covered_days"] < config["min_days"]
        )
        sources[key] = {
            "label": config["label"],
            "filename": config["filename"],
            "first_date": coverage["first_date"],
            "last_date": coverage["last_date"],
            "row_count": coverage["row_count"],
            "prm_count": len(source_prms[key] & contract_prms),
            "missing_prm_count": len(contract_prms - source_prms[key]),
            "weak_prm_count": weak_count,
            "outside_contract_prm_count": len(source_prms[key] - contract_prms),
            "bad_date_rows": coverage["bad_date_rows"],
        }

    return {
        "contracts_count": len(contract_prms),
        "sources": sources,
        "combo_counts": combo_counts,
        "missing_by_segment": missing_by_segment,
        "profile_counts": profile_counts,
        "summary": {
            "all_sources": combo_counts.get("consumption+load_curve+max_power", 0),
            "no_source": combo_counts.get("none", 0),
            "partial_sources": len(contract_prms) - combo_counts.get("consumption+load_curve+max_power", 0) - combo_counts.get("none", 0),
            "info": sum(1 for row in rows if row["severity"] == "info"),
            "with_warnings": sum(1 for row in rows if row["severity"] == "warning"),
            "critical": sum(1 for row in rows if row["severity"] == "critical"),
        },
        "correctable": correctable,
        "rows": rows,
    }


def _csv_rows(filename: str) -> list[dict[str, str]]:
    path = _energie_path(filename)
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _csv_rows_path(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def _contracts() -> dict[str, dict[str, str]]:
    return {r["usage_point_id"]: r for r in _csv_rows("enedis_contracts.csv")}


@lru_cache(maxsize=1)
def _addresses() -> dict[str, dict[str, str]]:
    return {r["usage_point_id"]: r for r in _csv_rows("enedis_addresses.csv")}


@lru_cache(maxsize=1)
def _connections() -> dict[str, dict[str, str]]:
    return {r["usage_point_id"]: r for r in _csv_rows("enedis_connections.csv")}


@lru_cache(maxsize=1)
def _summaries() -> dict[str, dict[str, str]]:
    return {r["usage_point_id"]: r for r in _csv_rows("enedis_contract_summary.csv")}


@lru_cache(maxsize=1)
def _max_power_index() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for r in _csv_rows("enedis_max_power.csv"):
        uid = r.get("usage_point_id", "")
        raw = r.get("value_va")
        if not uid or not raw:
            continue
        try:
            fval = float(raw)
        except ValueError:
            continue
        index.setdefault(uid, []).append({"date": r["date"], "value_va": fval})
    for uid in index:
        index[uid].sort(key=lambda x: x["date"])
    return index


@lru_cache(maxsize=1)
def _daily_consumption_index() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for r in _csv_rows("enedis_data.csv"):
        uid = r.get("usage_point_id", "")
        raw = r.get("value_wh")
        if not uid or not raw:
            continue
        try:
            fval = float(raw)
        except ValueError:
            continue
        index.setdefault(uid, []).append({"date": r["date"], "value_wh": fval})
    for uid in index:
        index[uid].sort(key=lambda x: x["date"])
    return index


@lru_cache(maxsize=1)
def _load_curve_index() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for r in _csv_rows("enedis_load_curve.csv"):
        uid = r.get("usage_point_id", "")
        raw = r.get("value_w")
        if not uid or not raw:
            continue
        try:
            fval = float(raw)
        except ValueError:
            continue
        index.setdefault(uid, []).append({"datetime": r["datetime"], "value_w": fval})
    for uid in index:
        index[uid].sort(key=lambda x: x["datetime"])
    return index


@lru_cache(maxsize=1)
def _dju_rows() -> list[dict[str, str]]:
    dju_path = _energie_path("DJU", "dju_sete.csv")
    return _csv_rows_path(dju_path)


def _safe_float(val: str | None) -> float | None:
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _addr_display(addr: dict[str, str] | None) -> str:
    if not addr:
        return ""
    parts = [
        addr.get("address_number_street_name", ""),
        addr.get("address_postal_code_city", ""),
    ]
    return ", ".join(p for p in parts if p)


def _compute_calibration(peak_kva: float, subscribed_kva: float) -> tuple[str, float]:
    """Returns (status_key, ratio_percent)."""
    if subscribed_kva <= 0:
        return "inconnu", 0.0
    ratio = peak_kva / subscribed_kva * 100
    if ratio > 95:
        status = "sous_dimensionne"
    elif ratio > 80:
        status = "proche_seuil"
    elif ratio >= 40:
        status = "bien_calibre"
    else:
        status = "sur_souscrit"
    return status, round(ratio, 1)


def _peak_kva_3y(prm_id: str) -> float | None:
    points = _max_power_index().get(prm_id)
    if not points:
        return None
    return round(max(p["value_va"] for p in points) / 1000, 2)


def _power_band(kva: float | None) -> tuple[str, str]:
    if kva is None or kva <= 0:
        return "unknown", "Puissance inconnue"
    if kva <= 3:
        return "0_3", "0-3 kVA"
    if kva <= 6:
        return "3_6", "3-6 kVA"
    if kva <= 12:
        return "6_12", "6-12 kVA"
    if kva <= 36:
        return "12_36", "12-36 kVA"
    if kva <= 250:
        return "36_250", "36-250 kVA"
    return "250_plus", ">250 kVA"


def _rolling_annual_kwh(prm_id: str) -> tuple[float | None, str | None, str | None, int]:
    points = _daily_consumption_index().get(prm_id, [])
    if not points:
        return None, None, None, 0
    end = date.fromisoformat(points[-1]["date"])
    start = end - timedelta(days=364)
    start_str = start.isoformat()
    selected = [point for point in points if point["date"] >= start_str]
    if not selected:
        return None, None, None, 0
    kwh = round(sum(point["value_wh"] for point in selected) / 1000, 1)
    return kwh, selected[0]["date"], selected[-1]["date"], len({point["date"] for point in selected})


_DATA_SOURCE_LABELS = {
    "consumption": "Consommation journaliere",
    "max_power": "Puissance maximale journaliere",
    "load_curve": "Courbe de charge",
}


def _source_has_data(prm_id: str, source: str) -> bool:
    if source == "consumption":
        return bool(_daily_consumption_index().get(prm_id))
    if source == "max_power":
        return bool(_max_power_index().get(prm_id))
    if source == "load_curve":
        return bool(_load_curve_index().get(prm_id))
    return False


def _diagnostic_outcomes() -> dict[str, dict[str, str]]:
    return {
        "consumption": _load_diagnostic("enedis_data_diagnostic.json"),
        "max_power": _load_diagnostic("enedis_mp_diagnostic.json"),
        "load_curve": _load_lc_outcomes(),
    }


def _data_diagnostic(
    prm_id: str,
    source: str,
    meter_profile: str,
    outcome: str | None,
) -> dict[str, Any]:
    has_data = _source_has_data(prm_id, source)
    label = _DATA_SOURCE_LABELS[source]
    if has_data:
        return {
            "source": source,
            "label": label,
            "has_data": True,
            "outcome": outcome or "ok_data",
            "severity": "ok",
            "message": f"{label} disponible pour ce PRM.",
            "action": None,
        }

    if meter_profile == "non_powered":
        return {
            "source": source,
            "label": label,
            "has_data": False,
            "outcome": outcome,
            "severity": "info",
            "message": "PRM non alimente : l'absence de mesures est normale tant que le point n'est pas remis en service.",
            "action": "Verifier l'etat d'alimentation si ce PRM devrait etre actif.",
        }

    if meter_profile == "non_communicant" and source in {"max_power", "load_curve"}:
        return {
            "source": source,
            "label": label,
            "has_data": False,
            "outcome": outcome,
            "severity": "info",
            "message": "Compteur non communicant : ce flux n'est pas attendu structurellement.",
            "action": "Utiliser la consommation journaliere lorsqu'elle est disponible.",
        }

    if meter_profile == "communicant_closed" and source == "load_curve":
        return {
            "source": source,
            "label": label,
            "has_data": False,
            "outcome": outcome,
            "severity": "warning",
            "message": "Compteur communicant non ouvert aux services : la courbe de charge peut etre bloquee par l'activation ENEDIS.",
            "action": "Demander l'activation de l'acces courbe de charge aupres d'ENEDIS.",
        }

    if outcome == "access_not_subscribed":
        return {
            "source": source,
            "label": label,
            "has_data": False,
            "outcome": outcome,
            "severity": "warning",
            "message": "ENEDIS indique qu'aucun service d'acces a la donnee n'est souscrit pour la periode demandee.",
            "action": "Verifier le perimetre de droits/services ENEDIS pour ce PRM et cette periode.",
        }
    if outcome == "invalid_request":
        return {
            "source": source,
            "label": label,
            "has_data": False,
            "outcome": outcome,
            "severity": "warning",
            "message": "ENEDIS repond que la demande est non valide pour ce PRM.",
            "action": "Verifier l'eligibilite du PRM, son profil compteur et les dates autorisees par ENEDIS.",
        }
    if outcome in {"forbidden", "not_found"}:
        return {
            "source": source,
            "label": label,
            "has_data": False,
            "outcome": outcome,
            "severity": "warning",
            "message": "ENEDIS ne donne pas acces a ce flux pour ce PRM.",
            "action": "Verifier les droits API ou la presence du PRM dans le perimetre ENEDIS.",
        }
    if outcome in {"cdc_inactive", "not_eligible"}:
        return {
            "source": source,
            "label": label,
            "has_data": False,
            "outcome": outcome,
            "severity": "warning",
            "message": "ENEDIS indique que ce flux n'est pas actif ou pas eligible pour ce PRM.",
            "action": "Verifier l'activation du service et l'eligibilite compteur.",
        }
    if outcome in {"quota_exceeded", "error", "error_technical"}:
        return {
            "source": source,
            "label": label,
            "has_data": False,
            "outcome": outcome,
            "severity": "error",
            "message": "La derniere collecte n'a pas abouti pour ce flux.",
            "action": "Relancer un backfill cible apres verification des quotas ENEDIS.",
        }

    return {
        "source": source,
        "label": label,
        "has_data": False,
        "outcome": outcome,
        "severity": "warning",
        "message": "Aucune donnee disponible pour ce flux dans les exports ENEDIS collectes.",
        "action": "Lancer ou relancer un backfill cible si ce flux est attendu pour ce PRM.",
    }


def get_energie_overview() -> dict[str, Any]:
    contracts = _contracts()
    addresses = _addresses()
    connections = _connections()
    summaries = _summaries()

    prms = []
    total_kva = 0.0
    calibration_counts: dict[str, int] = {
        "sous_dimensionne": 0,
        "proche_seuil": 0,
        "bien_calibre": 0,
        "sur_souscrit": 0,
        "inconnu": 0,
    }
    supplier_kva: dict[str, float] = {}
    supplier_count: dict[str, int] = {}
    band_stats: dict[str, dict[str, Any]] = {}
    top_consumers: list[dict[str, Any]] = []
    service_level_stats: dict[str, dict[str, Any]] = {}
    segment_stats: dict[str, dict[str, Any]] = {}
    tariff_stats: dict[str, dict[str, Any]] = {}
    connection_state_stats: dict[str, dict[str, Any]] = {}
    total_annual_kwh = 0.0
    total_annual_prms = 0
    annual_start: str | None = None
    annual_end: str | None = None

    def add_distribution(stats: dict[str, dict[str, Any]], label: str | None, kva_value: float | None) -> None:
        key = (label or "Inconnu").strip() or "Inconnu"
        item = stats.setdefault(key, {"label": key, "prm_count": 0, "total_kva": 0.0})
        item["prm_count"] += 1
        item["total_kva"] += kva_value or 0.0

    def distribution(stats: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {"label": item["label"], "prm_count": item["prm_count"], "total_kva": round(item["total_kva"], 1)}
            for item in sorted(stats.values(), key=lambda value: (-value["prm_count"], value["label"]))
        ]

    for uid, contract in contracts.items():
        kva = _safe_float(contract.get("0_subscribed_power_value"))
        addr = addresses.get(uid)
        conn = connections.get(uid)
        summary = summaries.get(uid)
        if kva:
            total_kva += kva

        supplier = contract.get("0_contractor") or "Inconnu"
        supplier_kva[supplier] = supplier_kva.get(supplier, 0.0) + (kva or 0.0)
        supplier_count[supplier] = supplier_count.get(supplier, 0) + 1
        add_distribution(service_level_stats, summary.get("services_level") if summary else None, kva)
        add_distribution(segment_stats, contract.get("0_segment"), kva)
        add_distribution(tariff_stats, contract.get("0_distribution_tariff"), kva)
        add_distribution(connection_state_stats, conn.get("connection_state") if conn else None, kva)

        peak = _peak_kva_3y(uid)
        calibration_status: str | None = None
        calibration_ratio: float | None = None
        if peak is not None and kva and kva > 0:
            calibration_status, calibration_ratio = _compute_calibration(peak, kva)
            calibration_counts[calibration_status] = calibration_counts.get(calibration_status, 0) + 1
        else:
            calibration_counts["inconnu"] += 1

        annual_kwh, prm_annual_start, prm_annual_end, annual_days = _rolling_annual_kwh(uid)
        if annual_kwh is not None:
            total_annual_kwh += annual_kwh
            total_annual_prms += 1
            if prm_annual_start and (annual_start is None or prm_annual_start < annual_start):
                annual_start = prm_annual_start
            if prm_annual_end and (annual_end is None or prm_annual_end > annual_end):
                annual_end = prm_annual_end
            top_consumers.append(
                {
                    "usage_point_id": uid,
                    "name": contract.get("0_organization_commercial_name") or contract.get("0_organization_name") or uid,
                    "contractor": supplier,
                    "subscribed_power_kva": kva,
                    "annual_consumption_kwh": annual_kwh,
                }
            )

        band_key, band_label = _power_band(kva)
        band = band_stats.setdefault(
            band_key,
            {
                "band": band_key,
                "label": band_label,
                "prm_count": 0,
                "total_kva": 0.0,
                "annual_consumption_kwh": 0.0,
            },
        )
        band["prm_count"] += 1
        band["total_kva"] += kva or 0.0
        if annual_kwh is not None:
            band["annual_consumption_kwh"] += annual_kwh

        prms.append(
            {
                "usage_point_id": uid,
                "name": contract.get("0_organization_commercial_name") or contract.get("0_organization_name") or uid,
                "address": _addr_display(addr),
                "contractor": supplier,
                "subscribed_power_kva": kva,
                "tariff": contract.get("0_distribution_tariff"),
                "segment": contract.get("0_segment"),
                "connection_state": conn.get("connection_state") if conn else None,
                "services_level": summary.get("services_level") if summary else None,
                "peak_kva_3y": peak,
                "calibration_status": calibration_status,
                "calibration_ratio": calibration_ratio,
            }
        )

    prms.sort(key=lambda x: (x["name"] or "").lower())
    top_consumers.sort(key=lambda item: item["annual_consumption_kwh"], reverse=True)

    supplier_distribution = [
        {
            "supplier": s,
            "total_kva": round(supplier_kva[s], 1),
            "prm_count": supplier_count[s],
        }
        for s in sorted(supplier_kva, key=lambda k: -supplier_kva[k])
    ]
    band_order = ["0_3", "3_6", "6_12", "12_36", "36_250", "250_plus", "unknown"]
    power_bands = []
    for key in band_order:
        if key not in band_stats:
            continue
        item = band_stats[key]
        power_bands.append(
            {
                "band": item["band"],
                "label": item["label"],
                "prm_count": item["prm_count"],
                "total_kva": round(item["total_kva"], 1),
                "annual_consumption_kwh": round(item["annual_consumption_kwh"], 1) if item["annual_consumption_kwh"] else None,
            }
        )

    calibration_distribution = [
        {"status": "sous_dimensionne", "label": "Sous-dimensionnes", "prm_count": calibration_counts["sous_dimensionne"]},
        {"status": "proche_seuil", "label": "Proches du seuil", "prm_count": calibration_counts["proche_seuil"]},
        {"status": "bien_calibre", "label": "Bien calibres", "prm_count": calibration_counts["bien_calibre"]},
        {"status": "sur_souscrit", "label": "Sur-souscrits", "prm_count": calibration_counts["sur_souscrit"]},
        {"status": "inconnu", "label": "Inconnus", "prm_count": calibration_counts["inconnu"]},
    ]

    return {
        "kpis": {
            "total_prms": len(prms),
            "total_subscribed_kva": round(total_kva, 1),
            "sous_dimensionnes": calibration_counts["sous_dimensionne"],
            "proche_seuil": calibration_counts["proche_seuil"],
            "sur_souscrits": calibration_counts["sur_souscrit"],
            "calibration_inconnue": calibration_counts["inconnu"],
            "annual_consumption_kwh": round(total_annual_kwh, 1) if total_annual_prms else None,
            "annual_consumption_prms": total_annual_prms,
            "annual_consumption_start": annual_start,
            "annual_consumption_end": annual_end,
        },
        "supplier_distribution": supplier_distribution,
        "power_bands": power_bands,
        "calibration_distribution": calibration_distribution,
        "top_consumers": top_consumers,
        "service_level_distribution": distribution(service_level_stats),
        "segment_distribution": distribution(segment_stats),
        "tariff_distribution": distribution(tariff_stats),
        "connection_state_distribution": distribution(connection_state_stats),
        "dju_seasonal": get_portfolio_dju_seasonal(),
        "prms": prms,
    }


def get_prm_detail(prm_id: str) -> dict[str, Any] | None:
    contracts = _contracts()
    if prm_id not in contracts:
        return None
    contract = contracts[prm_id]
    addr = _addresses().get(prm_id) or {}
    conn = _connections().get(prm_id) or {}
    summary = _summaries().get(prm_id) or {}

    subscribed_kva = _safe_float(contract.get("0_subscribed_power_value"))
    peak = _peak_kva_3y(prm_id)
    meter_profile = _meter_profile(summary.get("services_level"), conn.get("connection_state"))
    outcomes = _diagnostic_outcomes()
    data_diagnostics = {
        source: _data_diagnostic(prm_id, source, meter_profile, outcomes[source].get(prm_id))
        for source in ("consumption", "max_power", "load_curve")
    }
    calibration_status = None
    calibration_ratio = None
    calibration_recommendation = None
    if peak is not None and subscribed_kva and subscribed_kva > 0:
        calibration_status, calibration_ratio = _compute_calibration(peak, subscribed_kva)
        recommendations = {
            "sous_dimensionne": "Risque de dépassement — augmenter la puissance souscrite.",
            "proche_seuil": "Proche du seuil — surveiller et anticiper une révision à la hausse.",
            "bien_calibre": "Contrat bien dimensionné.",
            "sur_souscrit": "Sur-souscrit — négocier une puissance inférieure pour réduire les coûts.",
        }
        calibration_recommendation = recommendations.get(calibration_status)

    return {
        "usage_point_id": prm_id,
        "contract": {
            "usage_point_id": prm_id,
            "contract_start": contract.get("0_contract_start"),
            "contract_type": contract.get("0_contract_type"),
            "contractor": contract.get("0_contractor"),
            "tariff": contract.get("0_distribution_tariff"),
            "subscribed_power_kva": subscribed_kva,
            "segment": contract.get("0_segment"),
            "organization_name": contract.get("0_organization_name"),
            "name": contract.get("0_organization_commercial_name") or contract.get("0_organization_name"),
        },
        "address": {
            "address_number_street_name": addr.get("address_number_street_name"),
            "address_postal_code_city": addr.get("address_postal_code_city"),
            "address_staircase_floor_apartment": addr.get("address_staircase_floor_apartment"),
            "address_building": addr.get("address_building"),
            "address_insee_code": addr.get("address_insee_code"),
        },
        "connection": {
            "serial_number": conn.get("serial_number"),
            "connection_state": conn.get("connection_state"),
            "voltage_level": conn.get("voltage_level"),
            "subscribed_kva": _safe_float(conn.get("generation_connection_power_value")),
        },
        "summary": {
            "segment": summary.get("segments_0_segment"),
            "activation_date": summary.get("consumption_last_activation_date"),
            "last_power_change_date": summary.get("last_subscribed_power_change_date"),
            "services_level": summary.get("services_level"),
        },
        "calibration": {
            "subscribed_kva": subscribed_kva,
            "peak_kva_3y": peak,
            "ratio_percent": calibration_ratio,
            "status": calibration_status,
            "recommendation": calibration_recommendation,
        },
        "data_diagnostics": data_diagnostics,
    }


def get_prm_annual_profile(prm_id: str) -> dict[str, Any]:
    """Monthly max kVA per year (N, N-1, N-2) from max_power data."""
    points = _max_power_index().get(prm_id, [])
    subscribed_kva = None
    contract = _contracts().get(prm_id)
    if contract:
        subscribed_kva = _safe_float(contract.get("0_subscribed_power_value"))

    by_year_month: dict[str, dict[str, float]] = {}
    for p in points:
        year = p["date"][:4]
        month = p["date"][5:7]
        kva = round(p["value_va"] / 1000, 2)
        by_year_month.setdefault(year, {})
        if month not in by_year_month[year] or kva > by_year_month[year][month]:
            by_year_month[year][month] = kva

    profiles = []
    for year in sorted(by_year_month.keys(), reverse=True)[:3]:
        months = [
            {"month": m, "max_kva": by_year_month[year][m]}
            for m in sorted(by_year_month[year].keys())
        ]
        profiles.append({"year": year, "months": months})

    return {
        "usage_point_id": prm_id,
        "subscribed_kva": subscribed_kva,
        "profiles": profiles,
    }


def get_prm_daily_consumption(prm_id: str, days: int | None = 90) -> dict[str, Any]:
    points = list(_daily_consumption_index().get(prm_id, []))
    if days and points:
        try:
            end_date = date.fromisoformat(points[-1]["date"])
            start_str = (end_date - timedelta(days=days - 1)).isoformat()
            points = [p for p in points if p["date"] >= start_str]
        except ValueError:
            pass
    return {
        "usage_point_id": prm_id,
        "points": [
            {"date": p["date"], "value_kwh": round(p["value_wh"] / 1000, 3)}
            for p in points
        ],
    }


def get_prm_max_power(prm_id: str) -> dict[str, Any]:
    contract = _contracts().get(prm_id)
    subscribed_kva = None
    if contract:
        subscribed_kva = _safe_float(contract.get("0_subscribed_power_value"))
    return {
        "usage_point_id": prm_id,
        "subscribed_kva": subscribed_kva,
        "points": _max_power_index().get(prm_id, []),
    }


def get_prm_load_curve(prm_id: str, days: int | None = None) -> dict[str, Any]:
    points = list(_load_curve_index().get(prm_id, []))
    if days and points:
        try:
            end_date = date.fromisoformat(points[-1]["datetime"][:10])
            start_str = (end_date - timedelta(days=days - 1)).isoformat()
            points = [p for p in points if p["datetime"][:10] >= start_str]
        except ValueError:
            pass
    return {
        "usage_point_id": prm_id,
        "points": points,
    }


def get_dju_monthly() -> list[dict[str, Any]]:
    """Monthly aggregated DJU (heating + cooling) from dju_sete.csv."""
    rows = _dju_rows()
    by_month: dict[str, dict[str, float]] = {}
    for r in rows:
        d = r.get("date", "")
        if len(d) < 7:
            continue
        ym = d[:7]  # YYYY-MM
        h = _safe_float(r.get("dju_chauffage_base_18")) or 0.0
        c = _safe_float(r.get("dju_froid_base_22")) or 0.0
        if ym not in by_month:
            by_month[ym] = {"dju_chauffe": 0.0, "dju_froid": 0.0}
        by_month[ym]["dju_chauffe"] += h
        by_month[ym]["dju_froid"] += c

    return [
        {
            "month": ym,
            "dju_chauffe": round(by_month[ym]["dju_chauffe"], 1),
            "dju_froid": round(by_month[ym]["dju_froid"], 1),
        }
        for ym in sorted(by_month.keys())
    ]


@lru_cache(maxsize=1)
def _dju_monthly_index() -> dict[str, dict[str, float]]:
    """Returns {YYYY-MM: {dju_chauffe, dju_froid}}."""
    rows = _dju_rows()
    by_month: dict[str, dict[str, float]] = {}
    for r in rows:
        d = r.get("date", "")
        if len(d) < 7:
            continue
        ym = d[:7]
        h = _safe_float(r.get("dju_chauffage_base_18")) or 0.0
        c = _safe_float(r.get("dju_froid_base_22")) or 0.0
        if ym not in by_month:
            by_month[ym] = {"dju_chauffe": 0.0, "dju_froid": 0.0}
        by_month[ym]["dju_chauffe"] += h
        by_month[ym]["dju_froid"] += c
    return by_month


@lru_cache(maxsize=1)
def _consumption_by_month() -> dict[str, dict[str, float]]:
    """Returns {prm_id: {YYYY-MM: kWh}}."""
    result: dict[str, dict[str, float]] = {}
    for prm_id, points in _daily_consumption_index().items():
        by_month: dict[str, float] = {}
        for p in points:
            ym = p["date"][:7]
            by_month[ym] = by_month.get(ym, 0.0) + p["value_wh"] / 1000.0
        result[prm_id] = {ym: round(v, 2) for ym, v in by_month.items()}
    return result


_DJU_HEATING_MIN = 10.0
_DJU_COOLING_MIN = 5.0
_DJU_SEASONAL_HEATING_MIN = 20.0
_DJU_SEASONAL_COOLING_MIN = 20.0
_DJU_PERF_TOLERANCE = 0.10   # ±10 % = "dans la cible"
_DJU_PERF_MIN_MONTHS = 3


def _build_dju_side(
    dju_idx: dict[str, dict[str, float]],
    conso_idx: dict[str, float],
    current_ym: str,
    dju_key: str,
    dju_min: float,
) -> dict[str, Any]:
    """Compute baseline + last-month indicator for one DJU side (heating or cooling)."""
    timeseries: list[dict[str, Any]] = []
    for ym in sorted(dju_idx.keys()):
        if ym >= current_ym:
            continue
        dju_val = dju_idx[ym].get(dju_key, 0.0)
        if dju_val < dju_min:
            continue
        kwh = conso_idx.get(ym)
        if kwh is None or kwh <= 0:
            continue
        timeseries.append({
            "month": ym,
            "kwh": round(kwh, 1),
            "dju": round(dju_val, 1),
            "ratio_kwh_per_dju": round(kwh / dju_val, 4),
        })

    has_data = len(timeseries) > 0
    is_reliable = len(timeseries) >= _DJU_PERF_MIN_MONTHS

    baseline: float | None = None
    if is_reliable:
        baseline = round(sum(p["ratio_kwh_per_dju"] for p in timeseries) / len(timeseries), 4)

    last = timeseries[-1] if timeseries else None
    ecart: float | None = None
    status: str | None = None

    if last and baseline:
        e = (last["ratio_kwh_per_dju"] - baseline) / baseline
        ecart = round(e * 100, 1)
        if abs(e) <= _DJU_PERF_TOLERANCE:
            status = "dans_cible"
        elif e > _DJU_PERF_TOLERANCE:
            status = "depassement"
        else:
            status = "economie"

    return {
        "baseline_ratio_kwh_per_dju": baseline,
        "months_in_baseline": len(timeseries),
        "last_month": last,
        "last_month_ecart_percent": ecart,
        "last_month_status": status,
        "timeseries": timeseries,
        "has_data": has_data,
        "is_reliable": is_reliable,
    }


def get_prm_dju_performance(prm_id: str) -> dict[str, Any]:
    """
    kWh/DJU performance indicator split into heating (DJU_chauffage) and cooling (DJU_froid).
    Only past completed months are included; the current month is excluded.
    """
    dju_idx = _dju_monthly_index()
    conso_idx = _consumption_by_month().get(prm_id, {})
    current_ym = date.today().strftime("%Y-%m")

    return {
        "usage_point_id": prm_id,
        "heating": _build_dju_side(dju_idx, conso_idx, current_ym, "dju_chauffe", _DJU_HEATING_MIN),
        "cooling": _build_dju_side(dju_idx, conso_idx, current_ym, "dju_froid", _DJU_COOLING_MIN),
    }


# ---------------------------------------------------------------------------
# DJU saisonnier — graphique Hiver (Oct→Avr) et Été (Mai→Sep), multi-années
# ---------------------------------------------------------------------------

_WINTER_MONTHS = ["10", "11", "12", "01", "02", "03", "04"]
_WINTER_LABELS = ["Oct", "Nov", "Déc", "Jan", "Fév", "Mar", "Avr"]
_SUMMER_MONTHS = ["05", "06", "07", "08", "09"]
_SUMMER_LABELS = ["Mai", "Jun", "Jul", "Aoû", "Sep"]


def _linear_trend(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Régression linéaire y = slope*x + intercept."""
    n = len(xs)
    if n < 2:
        return 0.0, ys[0] if ys else 0.0
    sx, sy = sum(xs), sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sx2 = sum(x * x for x in xs)
    denom = n * sx2 - sx * sx
    if denom == 0:
        return 0.0, sy / n
    slope = (n * sxy - sx * sy) / denom
    return slope, (sy - slope * sx) / n


def _winter_label(year: int, month: int) -> str:
    if month >= 10:
        return f"{year}-{str(year + 1)[2:]}"
    return f"{year - 1}-{str(year)[2:]}"


def _summer_label(year: int) -> str:
    return str(year)


def _build_dju_seasonal_from_consumption(usage_point_id: str, conso_idx: dict[str, float]) -> dict[str, Any]:
    """
    Performance kWh/DJU par saison (Hiver Oct→Avr, Été Mai→Sep), multi-années.
    Cible par mois = moyenne historique avec correction de tendance linéaire.
    """
    dju_idx = _dju_monthly_index()
    current_ym = date.today().strftime("%Y-%m")
    today = date.today()

    current_winter_label = _winter_label(today.year, today.month)
    current_summer_label = _summer_label(today.year)

    winter_by_season: dict[str, dict[str, dict[str, float]]] = {}
    summer_by_season: dict[str, dict[str, dict[str, float]]] = {}

    for ym in sorted(dju_idx.keys()):
        if ym >= current_ym:
            continue
        y, m = int(ym[:4]), int(ym[5:7])
        mn = f"{m:02d}"
        kwh = conso_idx.get(ym)
        if kwh is None or kwh <= 0:
            continue
        dju_vals = dju_idx[ym]

        if mn in _WINTER_MONTHS:
            dju = dju_vals.get("dju_chauffe", 0.0)
            if dju >= _DJU_SEASONAL_HEATING_MIN:
                lbl = _winter_label(y, m)
                winter_by_season.setdefault(lbl, {})[mn] = {"dju": round(dju, 1), "kwh": round(kwh, 1)}

        if mn in _SUMMER_MONTHS:
            dju = dju_vals.get("dju_froid", 0.0)
            if dju >= _DJU_SEASONAL_COOLING_MIN:
                lbl = _summer_label(y)
                summer_by_season.setdefault(lbl, {})[mn] = {"dju": round(dju, 1), "kwh": round(kwh, 1)}

    def _build_season(
        by_season: dict[str, dict[str, dict[str, float]]],
        months_order: list[str],
        months_labels: list[str],
        current_label: str,
    ) -> dict[str, Any]:
        ratio_history: dict[str, list[tuple[float, float]]] = {mn: [] for mn in months_order}
        years_data: list[dict[str, Any]] = []

        for lbl in sorted(by_season.keys()):
            season_months = []
            for mn in months_order:
                d = by_season[lbl].get(mn)
                if d is None:
                    continue
                dju, kwh = d["dju"], d["kwh"]
                ratio = round(kwh / dju, 4)
                ratio_history[mn].append((float(lbl[:4]), ratio))
                season_months.append({"month_num": mn, "dju": dju, "kwh": kwh, "ratio": ratio})
            if season_months:
                years_data.append({"label": lbl, "months": season_months})

        # Cible par mois : moyenne historique avec tendance linéaire projetée sur la saison courante
        current_x = float(current_label[:4])
        cible_by_month: dict[str, float | None] = {}
        for mn in months_order:
            pts = ratio_history[mn]
            if not pts:
                cible_by_month[mn] = None
            elif len(pts) == 1:
                cible_by_month[mn] = round(pts[0][1], 4)
            else:
                slope, intercept = _linear_trend([p[0] for p in pts], [p[1] for p in pts])
                cible_by_month[mn] = round(max(slope * current_x + intercept, 0.0), 4)

        # Écart saison courante vs cible (pondéré par DJU)
        current_ecart: float | None = None
        current_data = by_season.get(current_label, {})
        if current_data:
            sum_kwh_actual = sum_kwh_cible = 0.0
            for mn, d in current_data.items():
                cible = cible_by_month.get(mn)
                if cible is not None and cible > 0:
                    sum_kwh_actual += d["kwh"]
                    sum_kwh_cible += cible * d["dju"]
            if sum_kwh_cible > 0:
                current_ecart = round((sum_kwh_actual / sum_kwh_cible - 1) * 100, 1)

        return {
            "months_order": months_order,
            "months_labels": months_labels,
            "years": years_data,
            "cible_by_month": cible_by_month,
            "current_label": current_label,
            "current_ecart_percent": current_ecart,
            "current_months_count": len(current_data),
            "expected_months_count": len(months_order),
            "current_is_complete": len(current_data) == len(months_order),
            "has_data": len(years_data) > 0,
        }

    return {
        "usage_point_id": usage_point_id,
        "winter": _build_season(winter_by_season, _WINTER_MONTHS, _WINTER_LABELS, current_winter_label),
        "summer": _build_season(summer_by_season, _SUMMER_MONTHS, _SUMMER_LABELS, current_summer_label),
    }


def _portfolio_consumption_by_month() -> dict[str, float]:
    """Returns monthly kWh summed across all PRM with daily consumption."""
    result: dict[str, float] = {}
    for conso_idx in _consumption_by_month().values():
        for ym, kwh in conso_idx.items():
            result[ym] = result.get(ym, 0.0) + kwh
    return {ym: round(kwh, 2) for ym, kwh in result.items()}


def get_portfolio_dju_seasonal() -> dict[str, Any]:
    """
    Performance kWh/DJU du patrimoine complet.
    Les kWh sont additionnes avant calcul du ratio afin de ponderer naturellement par la consommation.
    """
    return _build_dju_seasonal_from_consumption("portfolio", _portfolio_consumption_by_month())


def get_prm_dju_seasonal(prm_id: str) -> dict[str, Any]:
    return _build_dju_seasonal_from_consumption(prm_id, _consumption_by_month().get(prm_id, {}))
