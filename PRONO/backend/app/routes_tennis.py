"""Routes Tennis protegees par l'auth JWT PRONO."""
import time

from fastapi import APIRouter, Depends

from app import tennis, tennis_atp_elo, tennis_journal, tennis_odds_movement, tennis_outsider_radar, tennis_scorecard
from app.auth import get_current_user


router = APIRouter(prefix="/api/tennis", tags=["tennis"])

_CACHE = {"data": None, "ts": 0.0}
_BRACKET_CACHE = {"data": None, "ts": 0.0}
CACHE_TTL = 1800
BRACKET_CACHE_TTL = 3600


def _payload(force: bool = False) -> dict:
    if force or _CACHE["data"] is None or (time.time() - _CACHE["ts"]) > CACHE_TTL:
        try:
            elo_refresh = tennis_atp_elo.refresh_coach_if_needed(tennis._coach(), force=force)
        except Exception as exc:
            # L'actualisation externe ne doit jamais rendre la page tennis indisponible.
            elo_refresh = {"status": "error", "source": "donnees ATP embarquees", "error": type(exc).__name__}
        payload = tennis.build_tennis()
        payload["atp_elo_refresh"] = elo_refresh
        _CACHE["data"] = payload
        _CACHE["ts"] = time.time()
    return _CACHE["data"]


def _brackets_payload(force: bool = False) -> dict:
    if force or _BRACKET_CACHE["data"] is None or (time.time() - _BRACKET_CACHE["ts"]) > BRACKET_CACHE_TTL:
        _BRACKET_CACHE["data"] = tennis.build_tennis_brackets()
        _BRACKET_CACHE["ts"] = time.time()
    return _BRACKET_CACHE["data"]


@router.get("/matches")
def tennis_matches(refresh: int = 0, user=Depends(get_current_user)):
    return _payload(force=bool(refresh))


@router.get("/decision-calibration")
def tennis_decision_calibration(min_sample: int = 50, user=Depends(get_current_user)):
    return tennis.build_decision_calibration(min_sample=max(1, int(min_sample)))


@router.get("/brackets")
def tennis_brackets(refresh: int = 0, user=Depends(get_current_user)):
    return _brackets_payload(force=bool(refresh))


@router.get("/outsiders/recent")
def tennis_recent_outsiders(days: int = 7, user=Depends(get_current_user)):
    return tennis_outsider_radar.recent_outsiders(days=days)


@router.get("/outsiders/radar")
def tennis_outsider_radar_view(days: int = 7, refresh: int = 0, user=Depends(get_current_user)):
    return tennis_outsider_radar.build_radar(_payload(force=bool(refresh)), days=days)


@router.get("/outsiders/odds-movement")
def tennis_odds_movement_view(days: int = 14, user=Depends(get_current_user)):
    """Evolution de la cote outsider (open -> close) et agregat CLV sur la fenetre."""
    return tennis_odds_movement.recent_movements(days=days)


@router.get("/outsiders/scorecard")
def tennis_scorecard_view(user=Depends(get_current_user)):
    """Bilan hebdomadaire : calibration des marches secondaires + mouvement de cote."""
    return tennis_scorecard.weekly_scorecard()


# ---------------------------------------------------------------------------
# Registre des marches secondaires. Alimente et regle AUTOMATIQUEMENT par
# tennis.build_tennis() a chaque construction de la page : ces routes ne font que
# lire. Aucune route d'ecriture n'est exposee, et c'est delibere -- la saisie
# manuelle a ete abandonnee le 23/07/2026, avec la seconde base qui allait avec.
#
# Ce qui est mesure ici est une CALIBRATION (taux realise contre probabilite
# annoncee), pas un rendement : la cote reellement obtenue chez un bookmaker
# n'est archivee nulle part. Voir l'en-tete de app/tennis_journal.py.
# ---------------------------------------------------------------------------
@router.get("/journal/pending")
def journal_pending(user=Depends(get_current_user)):
    return {"pending": tennis_journal.pending()}


@router.get("/journal/markets")
def journal_markets(min_sample: int = 20, user=Depends(get_current_user)):
    return {"markets": tennis_journal.calibration_by_market(min_sample=max(1, int(min_sample)))}


@router.get("/journal/calibration")
def journal_calibration(min_sample: int = 50, user=Depends(get_current_user)):
    return tennis_journal.calibration(min_sample=max(1, int(min_sample)))


@router.get("")
def tennis_matches_root(refresh: int = 0, user=Depends(get_current_user)):
    return _payload(force=bool(refresh))


@router.get("/")
def tennis_matches_slash(refresh: int = 0, user=Depends(get_current_user)):
    return _payload(force=bool(refresh))
