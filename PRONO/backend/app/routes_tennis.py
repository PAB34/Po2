"""Routes Tennis protegees par l'auth JWT PRONO."""
import time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app import tennis, tennis_journal
from app.auth import get_current_user


router = APIRouter(prefix="/api/tennis", tags=["tennis"])

_CACHE = {"data": None, "ts": 0.0}
_BRACKET_CACHE = {"data": None, "ts": 0.0}
CACHE_TTL = 1800
BRACKET_CACHE_TTL = 3600


def _payload(force: bool = False) -> dict:
    if force or _CACHE["data"] is None or (time.time() - _CACHE["ts"]) > CACHE_TTL:
        _CACHE["data"] = tennis.build_tennis()
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


# ---------------------------------------------------------------------------
# Journal des decisions : ce qui a ete joue, a quel prix, et le resultat.
# Sans ce journal, la calibration des decisions n'a aucune donnee a lire, et les
# marches secondaires (prend un set, handicap) restent non mesurables faute de
# cotes archivees.
# ---------------------------------------------------------------------------
class JournalEntry(BaseModel):
    match_id: str
    favorite: str
    market_probability: float
    opponent: str | None = None
    kickoff: str | None = None
    tour: str = "ATP"
    tournament: str | None = None
    surface: str | None = None
    favorite_odds: float | None = None
    outsider_odds: float | None = None
    elo_probability: float | None = None
    elo_gap: float | None = None
    decision: str | None = None
    decision_level: str | None = None
    concordance: str | None = None
    context_label: str | None = None
    quality: str | None = None
    # pari reellement pris ; laisser vide journalise un "aucun pari"
    market: str | None = None
    selection: str | None = None
    taken_odds: float | None = None
    stake: float | None = None


class JournalSettlement(BaseModel):
    winner: str
    score: str | None = None
    bet_won: bool | None = None


@router.post("/journal", status_code=status.HTTP_201_CREATED)
def journal_record(entry: JournalEntry, user=Depends(get_current_user)):
    tennis_journal.record_decision(**entry.model_dump())
    return {"match_id": entry.match_id, "recorded": True}


@router.post("/journal/{match_id}/settle")
def journal_settle(match_id: str, payload: JournalSettlement, user=Depends(get_current_user)):
    if not tennis_journal.settle(match_id, **payload.model_dump()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision inconnue au journal.")
    return {"match_id": match_id, "settled": True}


@router.get("/journal/pending")
def journal_pending(user=Depends(get_current_user)):
    return {"pending": tennis_journal.pending()}


@router.get("/journal/roi")
def journal_roi(min_sample: int = 1, user=Depends(get_current_user)):
    return {"markets": tennis_journal.roi_by_market(min_sample=max(1, int(min_sample)))}


@router.get("/journal/calibration")
def journal_calibration(min_sample: int = 50, user=Depends(get_current_user)):
    return tennis_journal.calibration(min_sample=max(1, int(min_sample)))


@router.get("")
def tennis_matches_root(refresh: int = 0, user=Depends(get_current_user)):
    return _payload(force=bool(refresh))


@router.get("/")
def tennis_matches_slash(refresh: int = 0, user=Depends(get_current_user)):
    return _payload(force=bool(refresh))
