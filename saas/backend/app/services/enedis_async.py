"""
Pipeline asynchrone ENEDIS pour CDC et conso journalière.

Flux complet d'un job :
    1. POST commanderPublicationPonctuelle (avec liste PRM + dates + canal contact)
       → ENEDIS répond {dossierId: int}
       → On crée 1 ligne EnedisAsyncJob (status=requested)

    2. ENEDIS dépose sous 24h un fichier chiffré sur le FTP du canal de contact
       → On poll le FTP toutes les 5 min (APScheduler)
       → Download dans /tmp/enedis_async/incoming/
       → On match le fichier à un job (par nom contenant dossierId, ou heuristique)
       → status=file_received

    3. Déchiffrement AES-256 du fichier
       → status=decrypted

    4. Parse JSON ENEDIS → upsert dans le CSV cible (enedis_data.csv ou enedis_load_curve.csv)
       → status=parsed → success

Documentation API : kit de portage ENEDIS section "API Mesures Asynchrone".
Swagger : saas/energie/SWAGGER ENEDIS/mesure_asynchrone v1 (3).json
"""
from __future__ import annotations

import csv
import json
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from ftplib import FTP, error_perm
from pathlib import Path
from typing import Any, Iterable

import requests
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enedis_async import (
    JOB_STATUS_DECRYPTED,
    JOB_STATUS_ERROR,
    JOB_STATUS_FILE_RECEIVED,
    JOB_STATUS_PARSED,
    JOB_STATUS_REQUESTED,
    JOB_STATUS_SUCCESS,
    TYPE_DONNEE_CDC,
    TYPE_DONNEE_ENERGIE,
    TYPE_DONNEES_SUPPORTED,
    EnedisAsyncJob,
)
from app.services.enedis_common import RateLimiter, TokenManager

LOG = logging.getLogger(__name__)

_PUBLICATION_RATE_LIMITER = RateLimiter(rps=2.0, max_concurrent=1, max_hourly=900)


# ---------------------------------------------------------------------------
# Limites métier
# ---------------------------------------------------------------------------

_MAX_HISTORY_DAYS_BY_TYPE: dict[str, int] = {
    TYPE_DONNEE_CDC: 730,  # CDC : profondeur historique 24 mois
    TYPE_DONNEE_ENERGIE: 1095,  # ENERGIE : profondeur historique 36 mois
}

_MAX_QUERY_WINDOW_DAYS_BY_TYPE: dict[str, int] = {
    TYPE_DONNEE_CDC: 7,  # Kit ENEDIS : plage de consultation CDC = 7 jours
    TYPE_DONNEE_ENERGIE: 1095,  # Kit ENEDIS : Energie = 36 mois
}

_BACKFILL_WINDOW_DAYS_BY_TYPE: dict[str, int] = {
    TYPE_DONNEE_CDC: 7,
    TYPE_DONNEE_ENERGIE: 365,
}

# ENEDIS documente 1000 PRM par demande, mais l'API rejette en pratique les
# très gros lots de mesures par un simple HTTP 500. Les backfills historiques
# utilisent donc un lot conservateur, sans changer la limite des appels unitaires.
_BACKFILL_PRM_BATCH_SIZE = 50


def _validate_request(
    type_donnee: str, date_start: date, date_end: date, prm_list: list[str]
) -> None:
    if type_donnee not in TYPE_DONNEES_SUPPORTED:
        raise ValueError(
            f"type_donnee doit être dans {TYPE_DONNEES_SUPPORTED}, reçu : {type_donnee!r}"
        )
    if date_start >= date_end:
        raise ValueError("date_start doit être strictement antérieure à date_end")
    delta_days = (date_end - date_start).days
    max_window_days = _MAX_QUERY_WINDOW_DAYS_BY_TYPE[type_donnee]
    if delta_days > max_window_days:
        raise ValueError(
            f"Plage demandée ({delta_days} jours) dépasse la limite ENEDIS "
            f"pour {type_donnee} ({max_window_days} jours par appel)."
        )
    if not prm_list:
        raise ValueError("prm_list ne peut pas être vide")


def _chunk_prms(prm_list: list[str], chunk_size: int) -> Iterable[list[str]]:
    for i in range(0, len(prm_list), chunk_size):
        yield prm_list[i : i + chunk_size]


def _iter_date_windows(
    date_start: date, date_end: date, max_window_days: int
) -> Iterable[tuple[date, date]]:
    """Découpe une période en fenêtres compatibles ENEDIS."""
    if max_window_days <= 0:
        raise ValueError("max_window_days doit être > 0")
    current = date_start
    while current < date_end:
        window_end = min(date_end, current + timedelta(days=max_window_days))
        yield current, window_end
        current = window_end


def _backfill_batch_size() -> int:
    return max(1, min(_BACKFILL_PRM_BATCH_SIZE, settings.enedis_async_max_prms_per_request))


def _build_full_backfill_plan(today: date | None = None) -> dict[str, dict[str, Any]]:
    pivot = today or (date.today() - timedelta(days=1))
    plan: dict[str, dict[str, Any]] = {}
    for type_donnee in (TYPE_DONNEE_ENERGIE, TYPE_DONNEE_CDC):
        prms = _load_prms_for_type(type_donnee)
        history_days = min(
            getattr(settings, f"enedis_async_{type_donnee.lower()}_max_days"),
            _MAX_HISTORY_DAYS_BY_TYPE[type_donnee],
        )
        date_start = pivot - timedelta(days=history_days)
        window_days = min(
            _BACKFILL_WINDOW_DAYS_BY_TYPE[type_donnee],
            _MAX_QUERY_WINDOW_DAYS_BY_TYPE[type_donnee],
        )
        windows = list(_iter_date_windows(date_start, pivot, window_days))
        if type_donnee == TYPE_DONNEE_CDC and windows:
            history_floor = date.today() - timedelta(days=history_days)
            first_start, first_end = windows[0]
            if first_start < history_floor:
                if history_floor < first_end:
                    windows[0] = (history_floor, first_end)
                    date_start = history_floor
                else:
                    windows = windows[1:]
                    date_start = windows[0][0] if windows else pivot
        batch_size = _backfill_batch_size()
        batch_count = (len(prms) + batch_size - 1) // batch_size if prms else 0
        plan[type_donnee] = {
            "prms": prms,
            "windows": windows,
            "date_start": date_start,
            "date_end": pivot,
            "prm_count": len(prms),
            "window_count": len(windows),
            "batch_size": batch_size,
            "batch_count_per_window": batch_count,
            "expected_dossier_count": batch_count * len(windows),
        }
    return plan


def plan_backfill_full_period() -> dict[str, Any]:
    """Retourne un plan sérialisable du backfill complet sans appeler ENEDIS."""
    plan = _build_full_backfill_plan()
    return {
        type_donnee: {
            "date_start": data["date_start"].isoformat(),
            "date_end": data["date_end"].isoformat(),
            "prm_count": data["prm_count"],
            "window_count": data["window_count"],
            "batch_size": data["batch_size"],
            "batch_count_per_window": data["batch_count_per_window"],
            "expected_dossier_count": data["expected_dossier_count"],
        }
        for type_donnee, data in plan.items()
    }


def _existing_backfill_chunk_counts(
    db: Session,
    type_donnee: str,
    date_start: date,
    date_end: date,
) -> dict[int, int]:
    rows = (
        db.query(EnedisAsyncJob.prm_count, func.count(EnedisAsyncJob.id))
        .filter(EnedisAsyncJob.type_donnee == type_donnee)
        .filter(EnedisAsyncJob.date_start == date_start)
        .filter(EnedisAsyncJob.date_end == date_end)
        .filter(EnedisAsyncJob.status != JOB_STATUS_ERROR)
        .group_by(EnedisAsyncJob.prm_count)
        .all()
    )
    return {int(prm_count): int(count) for prm_count, count in rows}


# ---------------------------------------------------------------------------
# 1. Demander une publication ponctuelle à ENEDIS
# ---------------------------------------------------------------------------


def _build_payload(
    type_donnee: str, date_start: date, date_end: date, prm_list: list[str], canal_id: str
) -> dict[str, Any]:
    """Construit le payload conforme au swagger CommanderPublicationPonctuelleDemande."""
    return {
        "donneesGenerales": {
            "canauxContact": {
                "proprietaireCanal": [{"canauxId": [{"canalContactId": canal_id}]}]
            },
            "dateDebut": date_start.isoformat(),
            "dateFin": date_end.isoformat(),
            "typeDonnee": type_donnee,
        },
        "listePoints": {
            "soutirage": True,
            "injection": False,
            "points": [{"pointId": prm} for prm in prm_list],
        },
    }


def request_publication(
    db: Session,
    type_donnee: str,
    date_start: date,
    date_end: date,
    prm_list: list[str],
    canal_id: str | None = None,
    token_mgr: TokenManager | None = None,
    requested_by_user_id: int | None = None,
) -> list[EnedisAsyncJob]:
    """
    POST commanderPublicationPonctuelle. Découpe automatiquement si > 1000 PRM.

    Insère une ligne EnedisAsyncJob par sous-requête (donc par dossier_id),
    avec status=requested. Retourne la liste des jobs créés.

    Levée d'exception si le payload est invalide ou si l'API renvoie un code != 2xx.
    """
    _validate_request(type_donnee, date_start, date_end, prm_list)

    canal_id = canal_id or settings.enedis_canal_contact_id
    if not canal_id:
        raise RuntimeError(
            "ENEDIS_CANAL_CONTACT_ID manquant. Renseigner dans le .env du backend."
        )

    if token_mgr is None:
        token_mgr = TokenManager()

    chunk_size = settings.enedis_async_max_prms_per_request
    jobs: list[EnedisAsyncJob] = []

    for chunk in _chunk_prms(prm_list, chunk_size):
        payload = _build_payload(type_donnee, date_start, date_end, chunk, canal_id)
        LOG.info(
            "POST commanderPublicationPonctuelle type=%s start=%s end=%s prms=%d",
            type_donnee, date_start, date_end, len(chunk),
        )
        _PUBLICATION_RATE_LIMITER.acquire()
        try:
            try:
                resp = requests.post(
                    settings.enedis_async_url,
                    headers={
                        "Authorization": f"Bearer {token_mgr.get()}",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=60,
                )
            except requests.RequestException as exc:
                raise RuntimeError(
                    "POST commanderPublicationPonctuelle impossible : "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
        finally:
            _PUBLICATION_RATE_LIMITER.release()
        if resp.status_code in (200, 201):
            data = resp.json()
            dossier_id = data.get("dossierId")
            if not dossier_id:
                raise RuntimeError(
                    f"Réponse ENEDIS sans dossierId : {resp.text[:300]}"
                )
            job = EnedisAsyncJob(
                dossier_id=int(dossier_id),
                type_donnee=type_donnee,
                date_start=date_start,
                date_end=date_end,
                prm_count=len(chunk),
                canal_contact_id=canal_id,
                status=JOB_STATUS_REQUESTED,
                requested_by_user_id=requested_by_user_id,
            )
            db.add(job)
            db.flush()
            jobs.append(job)
            LOG.info("ENEDIS dossier_id=%s créé pour %d PRM", dossier_id, len(chunk))
        else:
            raise RuntimeError(
                f"POST commanderPublicationPonctuelle HTTP {resp.status_code} : "
                f"{resp.text[:500]}"
            )

    db.commit()
    return jobs


# ---------------------------------------------------------------------------
# 2. FTP — listing + download
# ---------------------------------------------------------------------------


def _ftp_connect() -> FTP:
    """Connexion FTP vers le serveur configuré (mode passif par défaut)."""
    if not settings.ftp_host or not settings.ftp_user or not settings.ftp_password:
        raise RuntimeError(
            "FTP_HOST / FTP_USER / FTP_PASSWORD manquants dans le .env."
        )
    ftp = FTP()
    ftp.connect(settings.ftp_host, settings.ftp_port, timeout=30)
    ftp.login(settings.ftp_user, settings.ftp_password)
    ftp.set_pasv(settings.ftp_passive_mode)
    ftp.cwd(settings.ftp_remote_dir)
    return ftp


def list_remote_files() -> list[str]:
    """Retourne la liste des fichiers présents dans /upload/ sur le FTP."""
    ftp = _ftp_connect()
    try:
        names = ftp.nlst()
        # FTP peut renvoyer "." et ".."
        return [n for n in names if n not in (".", "..")]
    finally:
        ftp.quit()


def download_file(remote_name: str, local_dir: str | None = None) -> str:
    """
    Télécharge un fichier du FTP vers le dossier local. Retourne le chemin local.
    """
    local_dir = local_dir or settings.ftp_local_incoming_dir
    Path(local_dir).mkdir(parents=True, exist_ok=True)
    local_path = os.path.join(local_dir, remote_name)
    ftp = _ftp_connect()
    try:
        with open(local_path, "wb") as f:
            ftp.retrbinary(f"RETR {remote_name}", f.write)
    finally:
        ftp.quit()
    LOG.info("FTP download OK : %s → %s (%d bytes)", remote_name, local_path, os.path.getsize(local_path))
    return local_path


# ---------------------------------------------------------------------------
# 3. Déchiffrement AES-256
# ---------------------------------------------------------------------------


def _aes_key_bytes() -> bytes:
    """Convertit la clé hex (64 chars) du .env en 32 bytes AES-256."""
    hex_key = (settings.enedis_decryption_key or "").strip().lower()
    if len(hex_key) != 64:
        raise RuntimeError(
            f"ENEDIS_DECRYPTION_KEY doit être 64 caractères hex (256 bits), "
            f"reçu : {len(hex_key)} caractères."
        )
    try:
        return bytes.fromhex(hex_key)
    except ValueError as exc:
        raise RuntimeError(f"ENEDIS_DECRYPTION_KEY n'est pas du hex valide : {exc}")


def decrypt_file(encrypted_path: str, mode: str = "cbc_iv_prefix") -> bytes:
    """
    Déchiffre un fichier ENEDIS.

    Hypothèse par défaut (`mode="cbc_iv_prefix"`) : AES-256-CBC avec IV de 16 bytes
    en début de fichier, padding PKCS7.

    Modes alternatifs supportés :
    - `"gcm_iv_prefix"` : AES-256-GCM avec IV 12 bytes + tag 16 bytes à la fin
    - `"raw_cbc"` : AES-256-CBC sans IV embarqué (IV = 0x00 × 16, à éviter)

    Le mode exact sera confirmé après le premier fichier réel reçu. Le code est
    pluggable : modifier `mode` ou ajouter une variante ici.
    """
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    key = _aes_key_bytes()
    with open(encrypted_path, "rb") as f:
        blob = f.read()

    if mode == "cbc_iv_prefix":
        if len(blob) < 32:
            raise RuntimeError(f"Fichier trop court pour AES-CBC : {len(blob)} bytes")
        iv = blob[:16]
        ciphertext = blob[16:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()
        return plaintext

    if mode == "gcm_iv_prefix":
        if len(blob) < 12 + 16:
            raise RuntimeError(f"Fichier trop court pour AES-GCM : {len(blob)} bytes")
        iv = blob[:12]
        tag = blob[-16:]
        ciphertext = blob[12:-16]
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    if mode == "raw_cbc":
        iv = b"\x00" * 16
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(blob) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded) + unpadder.finalize()

    raise ValueError(f"Mode AES non supporté : {mode}")


def decrypt_to_json(encrypted_path: str, mode: str = "cbc_iv_prefix") -> dict[str, Any]:
    """Déchiffre puis parse le JSON. Lève RuntimeError si plaintext n'est pas JSON."""
    plaintext = decrypt_file(encrypted_path, mode=mode)
    try:
        return json.loads(plaintext.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        # Sauvegarde le plaintext brut pour inspection
        raw_path = encrypted_path + ".plaintext.bin"
        with open(raw_path, "wb") as f:
            f.write(plaintext)
        raise RuntimeError(
            f"Plaintext non JSON après déchiffrement (mode={mode}). "
            f"Tester un autre mode AES. Plaintext sauvegardé dans : {raw_path}"
        ) from exc


# ---------------------------------------------------------------------------
# 4. Parsers vers les CSV existants
# ---------------------------------------------------------------------------


def _upsert_daily_csv(rows: list[dict[str, Any]], csv_path: Path) -> int:
    """Upsert dans enedis_data.csv (clé usage_point_id+date). Cf. enedis_sync._upsert_csv."""
    if not rows:
        return 0
    key_cols = ("usage_point_id", "date")
    existing: dict[tuple, dict] = {}
    existing_cols: list[str] = []
    if csv_path.exists() and csv_path.stat().st_size > 0:
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            existing_cols = list(reader.fieldnames or [])
            for r in reader:
                key = tuple(r.get(k, "") for k in key_cols)
                existing[key] = dict(r)
    new_count = 0
    for row in rows:
        key = tuple(str(row.get(k, "")) for k in key_cols)
        if key not in existing:
            new_count += 1
        existing[key] = {k: str(v) if v is not None else "" for k, v in row.items()}
    all_cols = list(dict.fromkeys(existing_cols + [k for r in rows for k in r]))
    sorted_rows = sorted(
        existing.values(),
        key=lambda r: (r.get("usage_point_id", ""), r.get("date", "")),
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_cols, extrasaction="ignore")
        writer.writeheader()
        for r in sorted_rows:
            writer.writerow({k: r.get(k, "") for k in all_cols})
    return new_count


def _append_cdc_csv(rows: list[dict[str, Any]], csv_path: Path) -> int:
    """Append dans enedis_load_curve.csv. Cf. enedis_sync._append_lc_csv."""
    if not rows:
        return 0
    fieldnames = ["usage_point_id", "datetime", "value_w", "unit", "quality", "_ingested_at_utc"]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: "" if row.get(k) is None else str(row[k]) for k in fieldnames})
    return len(rows)


def _iter_prm_readings(payload: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    """
    Itère sur les lectures de PRM dans le JSON ENEDIS async.

    Le format exact n'est pas documenté précisément dans le swagger (le contenu
    du fichier déposé est défini ailleurs). On supporte ici plusieurs structures
    plausibles afin d'être robuste à l'inspection du premier fichier réel :
    - `{"listeMesures": [{"pointId": "...", "meter_reading": {...}}]}`
    - `{"points": [{"pointId": "...", "mesures": {...}}]}`
    - `{"meterReadings": [{...}]}`

    Adaptable après inspection du premier fichier — c'est ce module à ajuster.
    """
    candidates = [
        payload.get("listeMesures"),
        payload.get("points"),
        payload.get("meterReadings"),
        payload.get("listePoints", {}).get("points") if isinstance(payload.get("listePoints"), dict) else None,
    ]
    for items in candidates:
        if isinstance(items, list) and items:
            for item in items:
                prm = (
                    item.get("pointId")
                    or item.get("usage_point_id")
                    or item.get("prm")
                    or ""
                )
                if prm:
                    yield str(prm), item
            return


def parse_energie_to_csv(json_path: str | Path, ingested_at: str | None = None) -> int:
    """
    Parse un fichier JSON ENEDIS (typeDonnee=ENERGIE) et upsert dans enedis_data.csv.
    Retourne le nombre de lignes nouvelles insérées.
    """
    json_path = Path(json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    ingested_at = ingested_at or (datetime.utcnow().replace(microsecond=0).isoformat() + "Z")
    rows: list[dict[str, Any]] = []
    for prm, item in _iter_prm_readings(payload):
        mr = item.get("meter_reading") or item.get("meterReading") or item
        unit = (mr.get("reading_type") or mr.get("readingType") or {}).get("unit", "Wh")
        quality = mr.get("quality", "")
        flow_dir = (mr.get("reading_type") or mr.get("readingType") or {}).get("flow_direction", "")
        intervals = mr.get("interval_reading") or mr.get("intervalReading") or []
        for ir in intervals:
            raw_date = ir.get("date", "")
            val = ir.get("value")
            try:
                rows.append({
                    "usage_point_id": prm,
                    "date": raw_date[:10],
                    "value_wh": float(val) if val not in (None, "") else None,
                    "unit": unit,
                    "quality": quality,
                    "flow_direction": flow_dir,
                    "_ingested_at_utc": ingested_at,
                })
            except (ValueError, TypeError):
                continue
    csv_path = Path(settings.energie_dir) / "enedis_data.csv"
    return _upsert_daily_csv(rows, csv_path)


def parse_cdc_to_csv(json_path: str | Path, ingested_at: str | None = None) -> int:
    """
    Parse un fichier JSON ENEDIS (typeDonnee=CDC) et append dans enedis_load_curve.csv.
    Retourne le nombre de lignes insérées.
    """
    json_path = Path(json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    ingested_at = ingested_at or (datetime.utcnow().replace(microsecond=0).isoformat() + "Z")
    rows: list[dict[str, Any]] = []
    for prm, item in _iter_prm_readings(payload):
        mr = item.get("meter_reading") or item.get("meterReading") or item
        unit = (mr.get("reading_type") or mr.get("readingType") or {}).get("unit", "W")
        quality = mr.get("quality", "")
        intervals = mr.get("interval_reading") or mr.get("intervalReading") or []
        for ir in intervals:
            raw_dt = ir.get("date", "")
            val = ir.get("value")
            try:
                rows.append({
                    "usage_point_id": prm,
                    "datetime": raw_dt,
                    "value_w": float(val) if val not in (None, "") else None,
                    "unit": unit,
                    "quality": quality,
                    "_ingested_at_utc": ingested_at,
                })
            except (ValueError, TypeError):
                continue
    csv_path = Path(settings.energie_dir) / "enedis_load_curve.csv"
    return _append_cdc_csv(rows, csv_path)


# ---------------------------------------------------------------------------
# 5. Orchestration : poll FTP + traitement
# ---------------------------------------------------------------------------


_DOSSIER_ID_RE = re.compile(r"(\d{6,})")


def _extract_dossier_id_from_filename(filename: str) -> int | None:
    """
    Tente d'extraire le dossier_id du nom de fichier (ex: ENEDIS_123456789_CDC_xxx.enc).
    Heuristique : 1er nombre de 6+ chiffres. À ajuster sur fichier réel.
    """
    m = _DOSSIER_ID_RE.search(filename)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _match_job(db: Session, filename: str) -> EnedisAsyncJob | None:
    """Trouve le job correspondant à un fichier FTP."""
    dossier_id = _extract_dossier_id_from_filename(filename)
    if dossier_id is None:
        return None
    return (
        db.query(EnedisAsyncJob)
        .filter(EnedisAsyncJob.dossier_id == dossier_id)
        .filter(EnedisAsyncJob.status.in_([JOB_STATUS_REQUESTED, JOB_STATUS_FILE_RECEIVED]))
        .first()
    )


def process_one_file(db: Session, filename: str, decrypt_mode: str = "cbc_iv_prefix") -> EnedisAsyncJob | None:
    """
    Traite un fichier FTP entrant : download → match job → décrypte → parse → success.

    Idempotent : si un job existe déjà avec ce filename et status>=parsed, retourne sans rien faire.
    Retourne le job mis à jour, ou None si aucun match (fichier orphelin).
    """
    # Idempotence : si déjà traité, skip
    existing = (
        db.query(EnedisAsyncJob)
        .filter(EnedisAsyncJob.ftp_filename == filename)
        .filter(EnedisAsyncJob.status.in_([JOB_STATUS_PARSED, JOB_STATUS_SUCCESS]))
        .first()
    )
    if existing:
        LOG.info("Fichier %s déjà traité (job #%s) — skip", filename, existing.id)
        return existing

    job = _match_job(db, filename)
    if job is None:
        LOG.warning(
            "Fichier FTP orphelin (pas de job trouvé pour dossier_id extrait de %s)", filename
        )
        return None

    try:
        local_path = download_file(filename)
        LOG.info(
            "ENEDIS async FTP file matched: filename=%s dossier_id=%s job_id=%s type=%s period=%s..%s",
            filename,
            job.dossier_id,
            job.id,
            job.type_donnee,
            job.date_start,
            job.date_end,
        )
        job.ftp_filename = filename
        job.received_at = datetime.now(timezone.utc)
        job.status = JOB_STATUS_FILE_RECEIVED
        db.flush()

        payload = decrypt_to_json(local_path, mode=decrypt_mode)
        job.decrypted_at = datetime.now(timezone.utc)
        job.status = JOB_STATUS_DECRYPTED
        db.flush()

        # On peut écrire le JSON déchiffré dans un dossier dédié (pratique pour debug)
        plain_path = local_path + ".json"
        Path(plain_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        if job.type_donnee == TYPE_DONNEE_CDC:
            n_rows = parse_cdc_to_csv(plain_path)
        else:
            n_rows = parse_energie_to_csv(plain_path)

        job.parsed_at = datetime.now(timezone.utc)
        job.finished_at = datetime.now(timezone.utc)
        job.rows_added = n_rows
        job.status = JOB_STATUS_SUCCESS
        db.commit()
        _invalidate_energie_caches()
        LOG.info(
            "ENEDIS async job success: job_id=%s dossier_id=%s filename=%s rows_added=%d",
            job.id,
            job.dossier_id,
            filename,
            n_rows,
        )
        return job

    except Exception as exc:
        LOG.exception("ENEDIS async file processing failed: filename=%s job_id=%s", filename, job.id)
        job.status = JOB_STATUS_ERROR
        job.error_message = str(exc)[:2000]
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        return job


def _requested_publication_stats(db: Session) -> dict[str, Any]:
    stale_before = datetime.now(timezone.utc) - timedelta(hours=24)
    requested_q = db.query(EnedisAsyncJob).filter(EnedisAsyncJob.status == JOB_STATUS_REQUESTED)
    by_type_rows = (
        db.query(EnedisAsyncJob.type_donnee, func.count(EnedisAsyncJob.id))
        .filter(EnedisAsyncJob.status == JOB_STATUS_REQUESTED)
        .group_by(EnedisAsyncJob.type_donnee)
        .all()
    )
    return {
        "pending_requested": int(requested_q.count() or 0),
        "pending_requested_by_type": {type_donnee: int(count) for type_donnee, count in by_type_rows},
        "pending_older_than_24h": int(
            requested_q.filter(EnedisAsyncJob.requested_at < stale_before).count() or 0
        ),
        "oldest_requested_at": requested_q.with_entities(func.min(EnedisAsyncJob.requested_at)).scalar(),
        "latest_requested_at": requested_q.with_entities(func.max(EnedisAsyncJob.requested_at)).scalar(),
    }


def _log_empty_ftp_poll(db: Session) -> dict[str, Any]:
    stats = _requested_publication_stats(db)
    if stats["pending_requested"]:
        LOG.warning(
            "ENEDIS async FTP poll found no files: host=%s port=%s remote_dir=%s user=%s "
            "canal_contact_id=%s pending_requested=%s pending_by_type=%s oldest_requested_at=%s "
            "latest_requested_at=%s pending_older_than_24h=%s. Diagnostic: ENEDIS may not have "
            "published yet, or the ENEDIS contact channel may target another FTP server/path/user.",
            settings.ftp_host,
            settings.ftp_port,
            settings.ftp_remote_dir,
            settings.ftp_user,
            settings.enedis_canal_contact_id,
            stats["pending_requested"],
            stats["pending_requested_by_type"],
            stats["oldest_requested_at"],
            stats["latest_requested_at"],
            stats["pending_older_than_24h"],
        )
    else:
        LOG.info(
            "ENEDIS async FTP poll found no files and no pending publication jobs: host=%s remote_dir=%s user=%s",
            settings.ftp_host,
            settings.ftp_remote_dir,
            settings.ftp_user,
        )
    return stats


def poll_and_process(db: Session, decrypt_mode: str = "cbc_iv_prefix") -> dict[str, Any]:
    """
    Liste les fichiers FTP, télécharge et traite ceux pas encore ingérés.
    Retourne un compteur {found, processed, errors, skipped}.
    """
    try:
        remote_files = list_remote_files()
    except Exception as exc:
        stats = _requested_publication_stats(db)
        LOG.exception(
            "ENEDIS async FTP listing failed: host=%s port=%s remote_dir=%s user=%s passive=%s "
            "canal_contact_id=%s pending_requested=%s oldest_requested_at=%s error=%s",
            settings.ftp_host,
            settings.ftp_port,
            settings.ftp_remote_dir,
            settings.ftp_user,
            settings.ftp_passive_mode,
            settings.enedis_canal_contact_id,
            stats["pending_requested"],
            stats["oldest_requested_at"],
            exc,
        )
        return {"found": 0, "processed": 0, "errors": 1, "skipped": 0, **stats}

    if not remote_files:
        stats = _log_empty_ftp_poll(db)
    else:
        stats = _requested_publication_stats(db)
        LOG.info(
            "ENEDIS async FTP poll found files: host=%s remote_dir=%s found=%d sample=%s pending_requested=%s",
            settings.ftp_host,
            settings.ftp_remote_dir,
            len(remote_files),
            remote_files[:5],
            stats["pending_requested"],
        )

    counters: dict[str, Any] = {"found": len(remote_files), "processed": 0, "errors": 0, "skipped": 0, **stats}
    for name in remote_files:
        try:
            job = process_one_file(db, name, decrypt_mode=decrypt_mode)
            if job is None:
                counters["skipped"] += 1
            elif job.status == JOB_STATUS_ERROR:
                counters["errors"] += 1
            else:
                counters["processed"] += 1
        except Exception:
            LOG.exception("Erreur process %s", name)
            counters["errors"] += 1
    return counters


def _invalidate_energie_caches() -> None:
    """Vide les caches LRU du module energie après ingestion."""
    try:
        from app.services.energie import (  # noqa: PLC0415
            _daily_consumption_index,
            _consumption_by_month,
            _load_curve_index,
            get_data_audit,
            get_data_ranges,
        )
        _daily_consumption_index.cache_clear()
        _consumption_by_month.cache_clear()
        _load_curve_index.cache_clear()
        get_data_audit.cache_clear()
        get_data_ranges.cache_clear()
    except Exception:
        LOG.exception("Cache invalidation failed")


# ---------------------------------------------------------------------------
# Helpers haut niveau utilisables depuis un endpoint
# ---------------------------------------------------------------------------


def kickoff_backfill(
    db: Session,
    type_donnee: str,
    date_start: date,
    date_end: date,
    prm_list: list[str] | None = None,
    requested_by_user_id: int | None = None,
) -> list[EnedisAsyncJob]:
    """
    Wrapper haut niveau : prend la liste des PRM depuis enedis_contracts.csv si non fournie.
    """
    if prm_list is None:
        prm_list = _load_prms_for_type(type_donnee)
    return request_publication(
        db,
        type_donnee=type_donnee,
        date_start=date_start,
        date_end=date_end,
        prm_list=prm_list,
        requested_by_user_id=requested_by_user_id,
    )


def _load_prms_from_contracts() -> list[str]:
    """Charge la liste des PRM depuis enedis_contracts.csv (même source que la sync existante)."""
    csv_path = Path(settings.energie_dir) / "enedis_contracts.csv"
    if not csv_path.exists():
        raise RuntimeError(f"enedis_contracts.csv introuvable : {csv_path}")
    prms: list[str] = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            uid = (row.get("usage_point_id") or "").strip()
            if uid and uid.isdigit() and len(uid) == 14:
                prms.append(uid)
    return sorted(set(prms))


def _load_contract_summary_by_prm() -> dict[str, dict[str, str]]:
    """Charge enedis_contract_summary.csv si disponible."""
    csv_path = Path(settings.energie_dir) / "enedis_contract_summary.csv"
    if not csv_path.exists():
        return {}
    rows: dict[str, dict[str, str]] = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            uid = (row.get("usage_point_id") or "").strip()
            if uid and uid.isdigit() and len(uid) == 14:
                rows[uid] = row
    return rows


def _is_communicant_open(service_level: str | None) -> bool:
    normalized = (service_level or "").strip().lower()
    return (
        "communicant" in normalized
        and "ouvert aux services" in normalized
        and "non ouvert" not in normalized
    )


def _load_prms_for_type(type_donnee: str) -> list[str]:
    """
    Charge les PRM candidats selon le type de mesure.

    Le kit ENEDIS précise que les mesures nécessitent des services activés sur
    compteurs communicants. Quand le référentiel contract summary est présent,
    on filtre donc les lots async aux compteurs "Communicant (ouvert aux
    services)" pour éviter qu'un PRM non éligible fasse rejeter tout le batch.
    """
    prms = _load_prms_from_contracts()
    summaries = _load_contract_summary_by_prm()
    if not summaries or type_donnee not in {TYPE_DONNEE_CDC, TYPE_DONNEE_ENERGIE}:
        return prms

    filtered = [
        prm
        for prm in prms
        if _is_communicant_open((summaries.get(prm) or {}).get("services_level"))
    ]
    if not filtered:
        LOG.warning(
            "Aucun PRM communicant ouvert aux services trouvé pour %s, fallback sur %d PRM",
            type_donnee,
            len(prms),
        )
        return prms
    LOG.info(
        "PRM candidats %s filtrés par services ENEDIS : %d/%d",
        type_donnee,
        len(filtered),
        len(prms),
    )
    return sorted(set(filtered))


def _backfill_full_period_legacy(db: Session, requested_by_user_id: int | None = None) -> dict[str, Any]:
    """
    Lance les 2 backfills à profondeur maximale :
    - ENERGIE : 3 ans (1095 jours), découpés en fenêtres annuelles par prudence
    - CDC : 2 ans (730 jours), découpés en fenêtres de 7 jours
    Le pivot est aujourd'hui-1 (ENEDIS retourne J-1).

    Retourne les dossier_ids créés et les erreurs partielles éventuelles.
    """
    today = date.today() - timedelta(days=1)
    result: dict[str, Any] = {
        "ENERGIE": [],
        "CDC": [],
        "errors": [],
        "summary": {
            "ENERGIE": {"prm_count": 0, "window_count": 0},
            "CDC": {"prm_count": 0, "window_count": 0},
        },
    }

    energie_prms = _load_prms_for_type(TYPE_DONNEE_ENERGIE)
    result["summary"]["ENERGIE"]["prm_count"] = len(energie_prms)
    energie_start = today - timedelta(
        days=min(settings.enedis_async_energie_max_days, _MAX_HISTORY_DAYS_BY_TYPE[TYPE_DONNEE_ENERGIE])
    )
    energie_windows = list(
        _iter_date_windows(
            energie_start,
            today,
            min(
                _BACKFILL_WINDOW_DAYS_BY_TYPE[TYPE_DONNEE_ENERGIE],
                _MAX_QUERY_WINDOW_DAYS_BY_TYPE[TYPE_DONNEE_ENERGIE],
            ),
        )
    )
    result["summary"]["ENERGIE"]["window_count"] = len(energie_windows)
    for window_start, window_end in energie_windows:
        try:
            energie_jobs = request_publication(
                db, TYPE_DONNEE_ENERGIE, window_start, window_end, energie_prms,
                requested_by_user_id=requested_by_user_id,
            )
            result["ENERGIE"].extend(j.dossier_id for j in energie_jobs)
        except RuntimeError as exc:
            db.rollback()
            result["errors"].append({
                "type_donnee": TYPE_DONNEE_ENERGIE,
                "date_start": window_start.isoformat(),
                "date_end": window_end.isoformat(),
                "prm_count": len(energie_prms),
                "message": str(exc)[:500],
            })

    cdc_prms = _load_prms_for_type(TYPE_DONNEE_CDC)
    result["summary"]["CDC"]["prm_count"] = len(cdc_prms)
    cdc_start = today - timedelta(
        days=min(settings.enedis_async_cdc_max_days, _MAX_HISTORY_DAYS_BY_TYPE[TYPE_DONNEE_CDC])
    )
    cdc_windows = list(
        _iter_date_windows(
            cdc_start,
            today,
            min(
                _BACKFILL_WINDOW_DAYS_BY_TYPE[TYPE_DONNEE_CDC],
                _MAX_QUERY_WINDOW_DAYS_BY_TYPE[TYPE_DONNEE_CDC],
            ),
        )
    )
    result["summary"]["CDC"]["window_count"] = len(cdc_windows)
    for window_start, window_end in cdc_windows:
        try:
            cdc_jobs = request_publication(
                db, TYPE_DONNEE_CDC, window_start, window_end, cdc_prms,
                requested_by_user_id=requested_by_user_id,
            )
            result["CDC"].extend(j.dossier_id for j in cdc_jobs)
        except RuntimeError as exc:
            db.rollback()
            result["errors"].append({
                "type_donnee": TYPE_DONNEE_CDC,
                "date_start": window_start.isoformat(),
                "date_end": window_end.isoformat(),
                "prm_count": len(cdc_prms),
                "message": str(exc)[:500],
            })

    if not result["ENERGIE"] and not result["CDC"] and result["errors"]:
        first_error = result["errors"][0]["message"]
        raise RuntimeError(
            "Aucun dossier ENEDIS créé pour le backfill complet. "
            f"Premier rejet : {first_error}"
        )

    return result


def backfill_full_period(db: Session, requested_by_user_id: int | None = None) -> dict[str, Any]:
    """
    Lance le backfill complet par lots conservateurs.

    Les tests réels ENEDIS montrent qu'un lot de 385 PRM peut être rejeté en
    HTTP 500, alors que les mêmes PRM passent lorsqu'ils sont découpés par 50.
    """
    plan = _build_full_backfill_plan()
    result: dict[str, Any] = {
        "ENERGIE": [],
        "CDC": [],
        "errors": [],
        "summary": plan_backfill_full_period(),
    }

    for type_donnee in (TYPE_DONNEE_ENERGIE, TYPE_DONNEE_CDC):
        prms = plan[type_donnee]["prms"]
        windows = plan[type_donnee]["windows"]
        batch_size = plan[type_donnee]["batch_size"]
        batch_count = plan[type_donnee]["batch_count_per_window"]
        for window_start, window_end in windows:
            existing_by_size = _existing_backfill_chunk_counts(
                db,
                type_donnee,
                window_start,
                window_end,
            )
            skipped_by_size: dict[int, int] = {}
            for batch_index, prm_chunk in enumerate(_chunk_prms(prms, batch_size), start=1):
                chunk_size = len(prm_chunk)
                already_skipped = skipped_by_size.get(chunk_size, 0)
                existing_count = existing_by_size.get(chunk_size, 0)
                if already_skipped < existing_count:
                    skipped_by_size[chunk_size] = already_skipped + 1
                    result["summary"][type_donnee]["skipped_existing_dossier_count"] = (
                        result["summary"][type_donnee].get("skipped_existing_dossier_count", 0) + 1
                    )
                    continue
                try:
                    jobs = request_publication(
                        db,
                        type_donnee,
                        window_start,
                        window_end,
                        prm_chunk,
                        requested_by_user_id=requested_by_user_id,
                    )
                    result[type_donnee].extend(j.dossier_id for j in jobs)
                except RuntimeError as exc:
                    db.rollback()
                    result["errors"].append({
                        "type_donnee": type_donnee,
                        "date_start": window_start.isoformat(),
                        "date_end": window_end.isoformat(),
                        "prm_count": len(prm_chunk),
                        "batch_index": batch_index,
                        "batch_count": batch_count,
                        "first_prm": prm_chunk[0] if prm_chunk else None,
                        "last_prm": prm_chunk[-1] if prm_chunk else None,
                        "message": str(exc)[:500],
                    })

    if not result["ENERGIE"] and not result["CDC"] and result["errors"]:
        first = result["errors"][0]
        raise RuntimeError(
            "Aucun dossier ENEDIS créé pour le backfill complet. "
            f"Premier rejet : {first['type_donnee']} {first['date_start']} - "
            f"{first['date_end']} lot {first.get('batch_index')}/"
            f"{first.get('batch_count')} ({first['prm_count']} PRM) : "
            f"{first['message']}"
        )

    for type_donnee in (TYPE_DONNEE_ENERGIE, TYPE_DONNEE_CDC):
        result["summary"][type_donnee]["created_dossier_count"] = len(result[type_donnee])

    return result
