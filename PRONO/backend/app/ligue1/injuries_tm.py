"""
Blessés / indisponibles de Ligue 1 — source gratuite Transfermarkt.

Récupère la table « joueurs blessés » de la Ligue 1 (vue détaillée) et la
structure par équipe : joueur, poste, blessure, date depuis, retour estimé.

⚠ C'est du scraping (zone grise vis-à-vis des CGU Transfermarkt, usage perso).
Le HTML peut changer → SURVEILLANCE INTÉGRÉE : toute anomalie (table absente,
0 ligne, chute brutale, champs vides, erreur HTTP) est journalisée comme ALERTE
dans le fichier de log et exposée à l'appelant via get_status().
On reste poli : une seule requête par rafraîchissement, mise en cache locale.
"""
import os
import json
import time
import logging
import urllib.request

from .config import (
    TM_INJURIES_URL, TM_CACHE_FILE, TM_CACHE_HOURS, TM_CLUB_MAP,
    TM_LOG_FILE, TM_MIN_EXPECTED_ROWS, TM_DROP_ALERT_RATIO,
)

_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

# ---- Logger : fichier + console ----
logger = logging.getLogger("injuries_tm")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(TM_LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

# Dernier état de santé du scraping, lisible par l'appelant (run.py).
LAST_STATUS = {"ok": True, "issues": [], "count": None, "source": None, "checked_at": None}


def get_status():
    return dict(LAST_STATUS)


def _set_status(ok, issues, count, source):
    LAST_STATUS.update(ok=ok, issues=list(issues), count=count, source=source,
                       checked_at=time.strftime("%Y-%m-%d %H:%M:%S"))


def _map_club(tm_name: str) -> str:
    low = (tm_name or "").lower()
    for kw, short in TM_CLUB_MAP.items():
        if kw.lower() in low:
            return short
    return tm_name


def _fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=_UA)
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")


def _parse(html: str):
    """Renvoie (records, issues). issues non vide = anomalie de structure."""
    from bs4 import BeautifulSoup
    issues = []
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="items")
    if table is None:
        issues.append("table.items introuvable — structure HTML probablement modifiée")
        return [], issues
    body = table.find("tbody")
    if body is None:
        issues.append("tbody introuvable dans table.items")
        return [], issues
    rows = [tr for tr in body.find_all("tr", recursive=False)
            if tr.get("class") and tr.get("class")[0] in ("odd", "even")]
    if len(rows) == 0:
        issues.append("0 ligne de joueur dans la table")
        return [], issues

    out = []
    bad = 0
    for tr in rows:
        tds = tr.find_all("td", recursive=False)
        a = tr.select_one('a[href*="/profil/spieler/"]')
        if a is None or len(tds) < 7:
            bad += 1
            continue
        name = (a.get("title") or a.get_text(strip=True)).strip()
        pos = tds[0].get_text(strip=True).replace(name, "").strip()
        club_img = tds[1].find("img")
        club_tm = club_img.get("title") if club_img else tds[1].get_text(strip=True)
        injury = tds[4].get_text(strip=True)
        if not name or not injury:
            bad += 1
            continue
        out.append({
            "player": name, "position": pos, "club_tm": club_tm,
            "team": _map_club(club_tm), "injury": injury,
            "since": tds[5].get_text(strip=True),
            "return": tds[6].get_text(strip=True) or "non précisé",
        })

    # Anomalies de contenu
    if len(out) == 0:
        issues.append(f"{len(rows)} lignes trouvées mais 0 exploitable — colonnes modifiées")
    elif bad > len(rows) * 0.5:
        issues.append(f"{bad}/{len(rows)} lignes non parsables — markup partiellement changé")
    unknown = sum(1 for r in out if r["team"] == r["club_tm"])
    if out and unknown > len(out) * 0.5:
        issues.append(f"{unknown}/{len(out)} clubs non reconnus — vérifier TM_CLUB_MAP")
    return out, issues


def _read_cache():
    if not os.path.exists(TM_CACHE_FILE):
        return None
    try:
        with open(TM_CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_injuries(force_refresh: bool = False):
    """Renvoie la liste structurée des blessés (avec cache + surveillance)."""
    cache = _read_cache()
    prev_count = cache.get("count") if isinstance(cache, dict) else None

    # Cache encore frais : on le sert sans requête.
    if (not force_refresh) and isinstance(cache, dict) and "data" in cache:
        age_h = (time.time() - os.path.getmtime(TM_CACHE_FILE)) / 3600.0
        if age_h < TM_CACHE_HOURS:
            _set_status(True, [], cache.get("count"), "cache")
            return cache["data"]

    # Rafraîchissement
    try:
        html = _fetch_html(TM_INJURIES_URL)
    except Exception as e:
        msg = f"ALERTE : échec HTTP Transfermarkt ({str(e)[:120]})"
        logger.error(msg)
        _set_status(False, [msg], prev_count, "http_error")
        return cache["data"] if isinstance(cache, dict) and "data" in cache else []

    records, issues = _parse(html)

    # Chute brutale vs dernier relevé sain = alerte (souvent signe de cassure).
    if prev_count and len(records) < max(TM_MIN_EXPECTED_ROWS,
                                         prev_count * TM_DROP_ALERT_RATIO):
        issues.append(f"chute suspecte : {len(records)} blessés vs {prev_count} au "
                      f"dernier relevé")
    elif prev_count is None and 0 < len(records) < TM_MIN_EXPECTED_ROWS:
        issues.append(f"seulement {len(records)} blessés trouvés "
                      f"(seuil attendu ≥ {TM_MIN_EXPECTED_ROWS})")

    if issues:
        for i in issues:
            logger.error("ALERTE cassure scraping : %s", i)
        _set_status(False, issues, len(records), "live(anomalie)")
        # On garde l'ancien cache valide plutôt que d'écraser avec des données douteuses.
        if isinstance(cache, dict) and "data" in cache and len(records) < (prev_count or 1):
            logger.info("Conservation du cache précédent (%s blessés).", prev_count)
            return cache["data"]
        return records

    # Tout est OK : on met à jour le cache + log info.
    logger.info("OK : %d blessés récupérés.", len(records))
    _set_status(True, [], len(records), "live")
    try:
        with open(TM_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"fetched_at": LAST_STATUS["checked_at"],
                       "count": len(records), "data": records}, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("Écriture cache impossible : %s", str(e)[:100])
    return records


def injuries_by_team(force_refresh: bool = False):
    data = get_injuries(force_refresh)
    by = {}
    for d in data:
        by.setdefault(d["team"], []).append(d)
    return by
