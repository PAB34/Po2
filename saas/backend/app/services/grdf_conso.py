"""
CONSO — collecte des consommations gaz GRDF ADICT.

- `fetch_consos_publiees` / `fetch_consos_informatives` : appel API + parsing
  tolérant (la réponse v1.9 peut être un objet unique ou une liste de périodes).
- `backfill` : historique complet (jusqu'à 5 ans publiées) sur tous les PCE
  collectables, à lancer une fois.
- `sync_recent` : fenêtre glissante (J-N → J) pour la synchro quotidienne.

L'`energie` (kWh) est la valeur principale. Seules les publiées `Définitive`
sont stockées comme telles ; les informatives sont marquées comme provisoires.
Upsert idempotent sur ``(pce_id, date_debut, type_conso)``.
"""
from __future__ import annotations

import logging
import threading
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.gas import GasConsumption, GasPce
from app.services.grdf_auth import GrdfQuotaExceeded
from app.services.grdf_client import GrdfApiError, get_ndjson

LOG = logging.getLogger(__name__)

# État de synchro en mémoire (mono-process, thread-safe) — alimente /status.
_LOCK = threading.Lock()
_STATE: dict[str, Any] = {
    "status": "idle",  # idle | running | success | error
    "started_at": None,
    "finished_at": None,
    "pce_total": 0,
    "pce_done": 0,
    "rows_upserted": 0,
    "mode": None,  # backfill | recent
    "error": None,
    "log": [],
}
_MAX_LOG = 50


def _log(msg: str) -> None:
    LOG.info(msg)
    with _LOCK:
        _STATE["log"].append(f"{datetime.utcnow().strftime('%H:%M:%S')} {msg}")
        _STATE["log"] = _STATE["log"][-_MAX_LOG:]


def get_sync_status() -> dict:
    with _LOCK:
        return dict(_STATE)


def is_sync_running() -> bool:
    with _LOCK:
        return _STATE["status"] == "running"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _to_int(value: Any) -> int | None:
    try:
        return int(round(float(value))) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    txt = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(txt[:19], fmt).date()
        except ValueError:
            continue
    return None


def _iter_entries(payload: Any) -> Iterable[dict]:
    """Normalise la réponse en une liste d'entrées ayant une clé ``consommation``.

    La v1.9 peut renvoyer : un objet unique, une liste d'objets, ou un objet
    enveloppe contenant une liste. Tolérant aux trois.
    """
    if payload is None:
        return []
    if isinstance(payload, list):
        return [e for e in payload if isinstance(e, dict)]
    if isinstance(payload, dict):
        if "consommation" in payload or "releve_debut" in payload:
            return [payload]
        for val in payload.values():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return [e for e in val if isinstance(e, dict)]
    return []


def _parse_entry(entry: dict, default_type: str) -> dict | None:
    conso = entry.get("consommation")
    if not conso:
        # Période sans donnée publiée (statut_restitution 1000008) → ignorée.
        return None
    periode = entry.get("periode") or {}
    coeff = conso.get("coeff_calcul") or {}
    date_debut = (
        _as_date(conso.get("date_debut_consommation"))
        or _as_date(periode.get("date_debut"))
    )
    date_fin = (
        _as_date(conso.get("date_fin_consommation"))
        or _as_date(periode.get("date_fin"))
    )
    if not date_debut or not date_fin:
        return None
    return {
        "date_debut": date_debut,
        "date_fin": date_fin,
        "energie_kwh": _to_int(conso.get("energie")),
        "volume_brut_m3": _to_int(conso.get("volume_brut")),
        "volume_converti_m3": _to_int(conso.get("volume_converti")),
        "coeff_conversion": (
            float(coeff["coeff_conversion"]) if coeff.get("coeff_conversion") is not None else None
        ),
        "statut_conso": conso.get("statut_conso"),
        "type_conso": conso.get("type_conso") or default_type,
        "type_qualif": conso.get("type_qualif_conso"),
        "journee_gaziere": _as_date(conso.get("journee_gaziere")),
    }


# ---------------------------------------------------------------------------
# Appels API
# ---------------------------------------------------------------------------

def fetch_consos_publiees(id_pce: str, date_debut: date, date_fin: date) -> list[dict]:
    entries = get_ndjson(
        f"/pce/{id_pce}/donnees_consos_publiees",
        params={"date_debut": date_debut.isoformat(), "date_fin": date_fin.isoformat()},
    )
    rows = [_parse_entry(e, "Publiée") for e in entries]
    return [r for r in rows if r]


def fetch_consos_informatives(id_pce: str, date_debut: date, date_fin: date) -> list[dict]:
    entries = get_ndjson(
        f"/pce/{id_pce}/donnees_consos_informatives",
        params={"date_debut": date_debut.isoformat(), "date_fin": date_fin.isoformat()},
    )
    rows = [_parse_entry(e, "Informative Journalier") for e in entries]
    return [r for r in rows if r]


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

def _upsert_rows(db: Session, pce_id: int, rows: list[dict]) -> int:
    # Dédup intra-réponse : le flux GRDF peut livrer plusieurs entrées partageant
    # la même date_debut (ex. « Absence de Données » d'un jour + période mesurée du
    # mois) ; la contrainte unique (pce_id, date_debut, type_conso) n'en garde qu'une.
    # On conserve la période la plus longue (date_fin la plus tardive = la vraie mesure).
    deduped: dict[tuple, dict] = {}
    for r in rows:
        key = (r["date_debut"], r["type_conso"])
        prev = deduped.get(key)
        if prev is None or (r["date_fin"] or date.min) >= (prev["date_fin"] or date.min):
            deduped[key] = r
    rows = list(deduped.values())
    n = 0
    for r in rows:
        existing = (
            db.query(GasConsumption)
            .filter(
                GasConsumption.pce_id == pce_id,
                GasConsumption.date_debut == r["date_debut"],
                GasConsumption.type_conso == r["type_conso"],
            )
            .one_or_none()
        )
        if existing is None:
            db.add(GasConsumption(pce_id=pce_id, **r))
            n += 1
        else:
            for k, v in r.items():
                if getattr(existing, k) != v:
                    setattr(existing, k, v)
            existing.synced_at = datetime.utcnow()
            n += 1
    return n


def _collectable_pces(db: Session, *, informatives: bool = False) -> list[GasPce]:
    """PCE dont le droit est actif et le périmètre demandé accordé."""
    perim = GasPce.perim_informatives if informatives else GasPce.perim_publiees
    return (
        db.query(GasPce)
        .filter(GasPce.etat_droit_acces == "Active", perim.is_(True))
        .all()
    )


def _has_recent_publiees(db: Session, pce_id: int, min_days: int, type_conso: str) -> bool:
    """Vrai si le dernier relevé stocké pour ce PCE date de moins de `min_days`.

    Implémente la préconisation GRDF « publiées : 1 appel/mois/PCE » : on évite de
    rappeler l'API tant qu'un relevé récent couvre déjà la période.
    """
    last = (
        db.query(GasConsumption.date_fin)
        .filter(GasConsumption.pce_id == pce_id, GasConsumption.type_conso == type_conso)
        .order_by(GasConsumption.date_fin.desc())
        .first()
    )
    if last is None or last[0] is None:
        return False
    return (date.today() - last[0]).days < min_days


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _run(
    mode: str,
    date_debut: date,
    date_fin: date,
    *,
    informatives: bool = False,
    guard_min_days: int | None = None,
) -> dict:
    with _LOCK:
        if _STATE["status"] == "running":
            return {"message": "déjà en cours"}
        _STATE.update(
            status="running", started_at=datetime.utcnow().isoformat(), finished_at=None,
            mode=mode, pce_done=0, rows_upserted=0, error=None, log=[],
        )
    fetch = fetch_consos_informatives if informatives else fetch_consos_publiees
    type_conso = "Informative Journalier" if informatives else "Publiée"
    db = SessionLocal()
    total_rows = 0
    skipped = 0
    try:
        pces = _collectable_pces(db, informatives=informatives)
        with _LOCK:
            _STATE["pce_total"] = len(pces)
        _log(f"{mode} : {len(pces)} PCE ({date_debut} → {date_fin})")
        for pce in pces:
            # Garde anti-redondance (préconisation 1/mois/PCE pour les publiées)
            if guard_min_days and _has_recent_publiees(db, pce.id, guard_min_days, type_conso):
                skipped += 1
                with _LOCK:
                    _STATE["pce_done"] += 1
                continue
            try:
                rows = fetch(pce.id_pce, date_debut, date_fin)
                added = _upsert_rows(db, pce.id, rows)
                pce.last_synced_at = datetime.utcnow()
                db.commit()
                total_rows += added
            except GrdfQuotaExceeded as exc:
                # Quota journalier atteint → arrêt propre, reprise à la prochaine fenêtre.
                db.rollback()
                _log(f"{mode} interrompu : {exc}")
                with _LOCK:
                    _STATE["error"] = str(exc)
                break
            except GrdfApiError as exc:
                db.rollback()
                _log(f"PCE {pce.id_pce} : erreur {exc}")
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                _log(f"PCE {pce.id_pce} : exception {exc}")
            with _LOCK:
                _STATE["pce_done"] += 1
                _STATE["rows_upserted"] = total_rows
        with _LOCK:
            _STATE.update(status="success", finished_at=datetime.utcnow().isoformat())
        _log(f"{mode} terminé : {total_rows} lignes upsert, {skipped} PCE déjà à jour")
    except Exception as exc:  # noqa: BLE001
        with _LOCK:
            _STATE.update(status="error", finished_at=datetime.utcnow().isoformat(), error=str(exc))
        _log(f"{mode} échec global : {exc}")
    finally:
        db.close()
    return {"mode": mode, "rows_upserted": total_rows, "skipped": skipped}


def run_backfill(history_days: int | None = None) -> dict:
    """Backfill complet des publiées (par défaut `grdf_history_days` = 5 ans). Sans garde."""
    days = history_days or settings.grdf_history_days
    fin = date.today()
    debut = fin - timedelta(days=days)
    return _run("backfill", debut, fin)


def run_recent_sync() -> dict:
    """Synchro planifiée des publiées (préconisation GRDF : ~1/mois/PCE).

    Fenêtre de rattrapage large (couvre le délai de publication J+1 DPM + corrections)
    + garde par PCE pour ne pas dépasser ~1 appel/mois/PCE même si le job tourne tous
    les jours.
    """
    fin = date.today()
    debut = fin - timedelta(days=settings.grdf_publiees_lookback_days)
    return _run("recent", debut, fin, guard_min_days=settings.grdf_publiees_min_interval_days)


def run_informatives_sync(history_days: int | None = None) -> dict:
    """Synchro des consommations informatives (JJ/MM, préconisation 1/jour/PCE).

    Profondeur plafonnée à `grdf_informatives_history_days` (3 ans). Sans garde
    (cadence quotidienne assumée pour le suivi fin).
    """
    days = history_days or settings.grdf_informatives_history_days
    fin = date.today()
    debut = fin - timedelta(days=min(days, settings.grdf_informatives_history_days))
    return _run("informatives", debut, fin, informatives=True)
