"""
Actualité gratuite par équipe via Google News RSS (français, sans clé API).

Remonte les titres d'articles récents par club et repère automatiquement les
sujets clés : blessures, forfaits, suspensions, retours (dont Coupe du monde),
méforme, changements d'entraîneur. Ne PARSE pas une liste structurée de blessés
(impossible de façon fiable en gratuit) : il fournit l'actualité brute lisible,
sourcée et datée, pour comprendre le contexte d'une équipe.
"""
import re
import html
import urllib.request
import urllib.parse
from datetime import datetime, timezone

from .config import NEWS_QUERIES, NEWS_MAX_ITEMS, NEWS_MAX_AGE_DAYS

_UA = {"User-Agent": "Mozilla/5.0 (compatible; Ligue1V4/1.0)"}

# Mots-clés → étiquette mise en avant.
TAGS = {
    "BLESSURE": ["bless", "forfait", "indisponib", "touché", "élongation", "claquage",
                 "ligament", "ischio", "rechute", "infirmerie", "béquille", "entorse"],
    "SUSPENSION": ["suspend", "suspension", "carton rouge", "expuls"],
    "RETOUR": ["de retour", "fait son retour", "retour de blessure", "revient",
               "rétabli", "reprise de l'entraînement", "de nouveau disponible"],
    "COUPE DU MONDE": ["coupe du monde", "mondial 2026", "sélectionné en", "avec sa sélection"],
    "MÉFORME": ["méforme", "en difficulté", "crise", "mauvaise passe", "inquiétude",
                "fébril", "doute"],
    "ENTRAÎNEUR": ["entraîneur", "coach", "limogé", "démission", "nouvel entraîneur"],
    "TRANSFERT": ["transfert", "mercato", "signe", "recrue", "départ", "prêt"],
}


def _fetch(url, timeout=20):
    req = urllib.request.Request(url, headers=_UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")


def _parse_items(xml):
    items = re.findall(r"<item>(.*?)</item>", xml, flags=re.S)
    out = []
    for it in items:
        t = re.search(r"<title>(.*?)</title>", it, flags=re.S)
        link = re.search(r"<link>(.*?)</link>", it, flags=re.S)
        date = re.search(r"<pubDate>(.*?)</pubDate>", it, flags=re.S)
        if not t:
            continue
        title = html.unescape(re.sub(r"<.*?>", "", t.group(1))).strip()
        source, headline = "", title
        if " - " in title:
            headline, source = title.rsplit(" - ", 1)
        dt = None
        if date:
            try:
                dt = datetime.strptime(date.group(1).strip(), "%a, %d %b %Y %H:%M:%S %Z")
                dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                dt = None
        out.append({"title": headline.strip(), "source": source.strip(),
                    "date": dt, "link": link.group(1).strip() if link else ""})
    return out


def _tag(title):
    low = title.lower()
    found = [tag for tag, kws in TAGS.items() if any(k in low for k in kws)]
    return found


def get_team_news(team: str, max_items: int = None, max_age_days: int = None):
    max_items = max_items or NEWS_MAX_ITEMS
    max_age_days = max_age_days or NEWS_MAX_AGE_DAYS
    query = NEWS_QUERIES.get(team, f'"{team}" Ligue 1')
    q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl=fr&gl=FR&ceid=FR:fr"
    try:
        xml = _fetch(url)
    except Exception as e:
        return {"team": team, "error": str(e)[:120], "items": []}
    items = _parse_items(xml)
    now = datetime.now(timezone.utc)
    kept = []
    for it in items:
        if it["date"] is not None and (now - it["date"]).days > max_age_days:
            continue
        it["tags"] = _tag(it["title"])
        kept.append(it)
    # priorité aux articles porteurs de mots-clés (blessure, retour…), puis récents.
    kept.sort(key=lambda x: (len(x["tags"]) > 0, x["date"] or now), reverse=True)
    return {"team": team, "error": None, "items": kept[:max_items]}


def get_league_news(max_items: int = 15, max_age_days: int = None):
    """Dernières actus générales de Ligue 1 (1 requête, pour l'onglet Actualité)."""
    max_age_days = max_age_days or NEWS_MAX_AGE_DAYS
    q = urllib.parse.quote('"Ligue 1" football')
    url = f"https://news.google.com/rss/search?q={q}&hl=fr&gl=FR&ceid=FR:fr"
    try:
        xml = _fetch(url)
    except Exception as e:
        return {"error": str(e)[:120], "items": []}
    now = datetime.now(timezone.utc)
    kept = []
    seen = set()
    for it in _parse_items(xml):
        key = it["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        if it["date"] is not None and (now - it["date"]).days > max_age_days:
            continue
        it["tags"] = _tag(it["title"])
        kept.append(it)
    kept.sort(key=lambda x: x["date"] or now, reverse=True)
    return {"error": None, "items": kept[:max_items]}


def get_journee_news(matches, max_items_per_team: int = None):
    teams = []
    for _, r in matches.iterrows():
        for t in (r["HomeTeam"], r["AwayTeam"]):
            if t not in teams:
                teams.append(t)
    return {t: get_team_news(t, max_items=max_items_per_team) for t in teams}
