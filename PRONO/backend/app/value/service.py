"""Snapshot collection service for PRONO value research."""
from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import os
from typing import Mapping

import pandas as pd

from app.ligue1.config import DATA_DIR
from app.ligue1.data import load_history, load_upcoming

from .betting_completeness import BettingCompletenessAssessment, assess_betting_completeness
from .clv_report import SnapshotClvReport, build_snapshot_clv_report
from .collectors import snapshots_from_football_data_rows, snapshots_from_the_odds_api_events
from .manual_odds_csv import snapshots_from_manual_csv
from .odds_api import OddsApiRequest, fetch_odds_events
from .odds_coverage import OddsCoverageReport, build_odds_coverage_report
from .scenario_backtest import ScenarioBacktestResult, run_scenario_backtest
from .scenario_predictions import (
    ScenarioPredictionPersistResult,
    ScenarioPredictionStore,
    predictions_from_ligue1_journee,
)
from .ticket_families import TicketFamilyReport, build_ticket_family_candidates
from .ticket_backtest import BoostedTicketBacktestResult, build_market_favorite_selections, run_boosted_ticket_backtest
from .snapshots import OddsSnapshotStore

SNAPSHOT_DB = os.path.join(DATA_DIR, "odds_snapshots.db")
SCENARIO_PREDICTION_DB = os.path.join(DATA_DIR, "scenario_predictions.db")


@dataclass(frozen=True)
class CollectionResult:
    source: str
    captured_at: str
    generated_count: int
    inserted_count: int
    db_path: str


@dataclass(frozen=True)
class SnapshotStoreStats:
    db_path: str
    total_count: int
    by_source: Mapping[str, int]


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_store() -> OddsSnapshotStore:
    os.makedirs(DATA_DIR, exist_ok=True)
    return OddsSnapshotStore(SNAPSHOT_DB)


def default_scenario_prediction_store() -> ScenarioPredictionStore:
    os.makedirs(DATA_DIR, exist_ok=True)
    return ScenarioPredictionStore(SCENARIO_PREDICTION_DB)


def collect_football_data_snapshots(
    rows: pd.DataFrame | None = None,
    captured_at: str | None = None,
    store: OddsSnapshotStore | None = None,
) -> CollectionResult:
    """Collect current Football-Data odds into the snapshot store.

    Passing `rows` is mainly for tests. In production the service calls
    `load_upcoming()`, which reads the already-used Football-Data fixtures feed.
    """
    capture_time = captured_at or utc_now_iso()
    target_store = store or default_store()
    frame = load_upcoming() if rows is None else rows
    snapshots = snapshots_from_football_data_rows(frame, captured_at=capture_time)
    inserted = target_store.insert_many(snapshots)
    return CollectionResult(
        source="football-data-fixtures",
        captured_at=capture_time,
        generated_count=len(snapshots),
        inserted_count=inserted,
        db_path=target_store.db_path,
    )



def collect_manual_csv_snapshots(
    csv_text: str,
    captured_at: str | None = None,
    default_bookmaker: str = "manual",
    default_sport: str = "football",
    default_competition: str = "ligue1",
    store: OddsSnapshotStore | None = None,
) -> CollectionResult:
    capture_time = captured_at or utc_now_iso()
    target_store = store or default_store()
    snapshots = snapshots_from_manual_csv(
        csv_text,
        captured_at=capture_time,
        default_bookmaker=default_bookmaker,
        default_sport=default_sport,
        default_competition=default_competition,
    )
    inserted = target_store.insert_many(snapshots)
    return CollectionResult(
        source="manual-csv",
        captured_at=capture_time,
        generated_count=len(snapshots),
        inserted_count=inserted,
        db_path=target_store.db_path,
    )
def snapshot_store_stats(store: OddsSnapshotStore | None = None) -> SnapshotStoreStats:
    target_store = store or default_store()
    return SnapshotStoreStats(
        db_path=target_store.db_path,
        total_count=target_store.count(),
        by_source=target_store.count_by_source(),
    )

def snapshot_clv_report(
    decision_at: str,
    event_id: str | None = None,
    market: str | None = None,
    store: OddsSnapshotStore | None = None,
) -> SnapshotClvReport:
    target_store = store or default_store()
    snapshots = target_store.list_snapshots(event_id=event_id, market=market)
    return build_snapshot_clv_report(snapshots, decision_at=decision_at)

def collect_the_odds_api_snapshots(
    sport_key: str,
    sport: str,
    competition: str,
    regions: str = "eu",
    markets: str = "h2h",
    bookmakers: str | None = None,
    captured_at: str | None = None,
    store: OddsSnapshotStore | None = None,
    events: list[dict] | None = None,
) -> CollectionResult:
    """Collect current odds from The Odds API into the snapshot store.

    `events` can be injected by tests. In production, `PRONO_ODDS_API_KEY` must
    be configured and the request consumes free-plan credits.
    """
    capture_time = captured_at or utc_now_iso()
    target_store = store or default_store()
    payload = events if events is not None else fetch_odds_events(OddsApiRequest(
        sport_key=sport_key,
        regions=regions,
        markets=markets,
        bookmakers=bookmakers,
    ))
    snapshots = snapshots_from_the_odds_api_events(
        payload,
        captured_at=capture_time,
        sport=sport,
        competition=competition,
        allowed_markets=set(m.strip() for m in markets.split(",") if m.strip()),
    )
    inserted = target_store.insert_many(snapshots)
    return CollectionResult(
        source="the-odds-api",
        captured_at=capture_time,
        generated_count=len(snapshots),
        inserted_count=inserted,
        db_path=target_store.db_path,
    )

def run_ligue1_boosted_ticket_backtest(
    selections_per_ticket: int = 5,
    stake: float = 50.0,
    max_tickets: int | None = 10,
    min_odd: float | None = None,
    max_odd: float | None = None,
) -> BoostedTicketBacktestResult:
    hist = load_history()
    selections = build_market_favorite_selections(
        hist,
        odds_columns={"H": "PSH", "D": "PSD", "A": "PSA"},
        source="Pinnacle",
        min_odd=min_odd,
        max_odd=max_odd,
    )
    return run_boosted_ticket_backtest(
        selections,
        selections_per_ticket=selections_per_ticket,
        stake=stake,
        max_tickets=max_tickets,
    )

def persist_ligue1_journee_scenario_predictions(
    payload: Mapping[str, object],
    predicted_at: str | None = None,
    store: ScenarioPredictionStore | None = None,
) -> ScenarioPredictionPersistResult:
    prediction_time = predicted_at or utc_now_iso()
    target_store = store or default_scenario_prediction_store()
    predictions = predictions_from_ligue1_journee(payload, predicted_at=prediction_time)
    inserted = target_store.insert_many(predictions)
    return ScenarioPredictionPersistResult(
        source="ligue1-journee",
        predicted_at=prediction_time,
        generated_count=len(predictions),
        inserted_count=inserted,
        db_path=target_store.db_path,
        predictions=tuple(predictions),
    )

def run_ligue1_scenario_backtest(
    store: ScenarioPredictionStore | None = None,
    history: pd.DataFrame | None = None,
) -> ScenarioBacktestResult:
    target_store = store or default_scenario_prediction_store()
    predictions = target_store.list_predictions()
    hist = load_history() if history is None else history
    return run_scenario_backtest(predictions, hist, source="ligue1-scenario-predictions")

def betting_completeness_report(
    event_id: str | None = None,
    decision_at: str | None = None,
    required_markets: tuple[str, ...] = ("1x2",),
    store: OddsSnapshotStore | None = None,
) -> BettingCompletenessAssessment:
    target_store = store or default_store()
    snapshots = target_store.list_snapshots(event_id=event_id)
    if required_markets:
        wanted = {market.strip().lower().replace(" ", "_").replace("over_1.5", "over_1_5") for market in required_markets}
        snapshots = [snapshot for snapshot in snapshots if snapshot.market.strip().lower().replace(" ", "_").replace("over_1.5", "over_1_5") in wanted]
    return assess_betting_completeness(
        snapshots,
        required_markets=required_markets,
        decision_at=decision_at,
    )

def build_ligue1_ticket_family_report(
    min_sporting_completeness: int = 70,
    require_betting_ready: bool = False,
    prediction_store: ScenarioPredictionStore | None = None,
    odds_store: OddsSnapshotStore | None = None,
    decision_at: str | None = None,
) -> TicketFamilyReport:
    target_prediction_store = prediction_store or default_scenario_prediction_store()
    predictions = target_prediction_store.list_predictions()
    betting_by_event = {}
    if odds_store is not None or require_betting_ready:
        target_odds_store = odds_store or default_store()
        for prediction in predictions:
            betting_by_event[prediction.event_id] = betting_completeness_report(
                event_id=prediction.event_id,
                decision_at=decision_at or prediction.predicted_at,
                required_markets=("1x2",),
                store=target_odds_store,
            )
    return build_ticket_family_candidates(
        predictions,
        betting_completeness_by_event=betting_by_event,
        min_sporting_completeness=min_sporting_completeness,
        require_betting_ready=require_betting_ready,
        source="ligue1-ticket-families",
    )

def odds_coverage_report(
    event_id: str | None = None,
    sport: str | None = None,
    competition: str | None = None,
    required_markets: tuple[str, ...] = ("1x2",),
    decision_at: str | None = None,
    store: OddsSnapshotStore | None = None,
) -> OddsCoverageReport:
    target_store = store or default_store()
    snapshots = target_store.list_snapshots(event_id=event_id)
    if sport is not None:
        snapshots = [snapshot for snapshot in snapshots if snapshot.sport == sport]
    if competition is not None:
        snapshots = [snapshot for snapshot in snapshots if snapshot.competition == competition]
    return build_odds_coverage_report(
        snapshots,
        required_markets=required_markets,
        decision_at=decision_at,
        source="odds-coverage",
    )
