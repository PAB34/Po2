"""Private value-research routes."""
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.auth import get_current_user
from app.ligue1 import service as ligue1_service
from app.value import service
from app.value.ligue1_scenarios import build_ligue1_journee_scenarios
from app.value.scenarios import scenario_from_mapping
from app.value.diagnostics import build_value_diagnostics

router = APIRouter(prefix="/api/value", tags=["value"])


@router.get("/health")
def health(user=Depends(get_current_user)):
    stats = service.snapshot_store_stats()
    return {
        "ok": True,
        "store": {
            "db_path": stats.db_path,
            "total_count": stats.total_count,
            "by_source": dict(stats.by_source),
        },
    }



@router.get("/diagnostics")
def value_diagnostics(refresh: int = 0, user=Depends(get_current_user)):
    return build_value_diagnostics(refresh=bool(refresh))

@router.post("/collect/football-data")
def collect_football_data(user=Depends(get_current_user)):
    result = service.collect_football_data_snapshots()
    return {
        "source": result.source,
        "captured_at": result.captured_at,
        "generated_count": result.generated_count,
        "inserted_count": result.inserted_count,
        "db_path": result.db_path,
    }

@router.post("/collect/manual-csv")
def collect_manual_csv(
    csv_text: str = Body(..., media_type="text/csv"),
    default_bookmaker: str = Query(default="manual"),
    default_sport: str = Query(default="football"),
    default_competition: str = Query(default="ligue1"),
    captured_at: str | None = Query(default=None),
    user=Depends(get_current_user),
):
    result = service.collect_manual_csv_snapshots(
        csv_text,
        captured_at=captured_at,
        default_bookmaker=default_bookmaker,
        default_sport=default_sport,
        default_competition=default_competition,
    )
    return {
        "source": result.source,
        "captured_at": result.captured_at,
        "generated_count": result.generated_count,
        "inserted_count": result.inserted_count,
        "db_path": result.db_path,
    }
@router.post("/scenarios/football")
def football_scenario(payload: dict[str, Any] = Body(...), user=Depends(get_current_user)):
    try:
        report = scenario_from_mapping(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "completeness_score": report.completeness_score,
        "confidence": report.confidence,
        "main_scenario": report.main_scenario,
        "alternative_scenarios": list(report.alternative_scenarios),
        "coherent_markets": list(report.coherent_markets),
        "avoid_markets": list(report.avoid_markets),
        "missing_data": list(report.missing_data),
        "blocking_missing_data": list(report.blocking_missing_data),
        "degrading_missing_data": list(report.degrading_missing_data),
        "factors": list(report.factors),
    }

@router.get("/scenarios/ligue1/journee")
def ligue1_journee_scenarios(refresh: int = 0, user=Depends(get_current_user)):
    try:
        payload = ligue1_service.build_journee(force=bool(refresh))
        return build_ligue1_journee_scenarios(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
@router.post("/scenarios/ligue1/journee/predictions")
def persist_ligue1_journee_scenario_predictions(refresh: int = 0, user=Depends(get_current_user)):
    try:
        payload = ligue1_service.build_journee(force=bool(refresh))
        result = service.persist_ligue1_journee_scenario_predictions(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "source": result.source,
        "predicted_at": result.predicted_at,
        "generated_count": result.generated_count,
        "inserted_count": result.inserted_count,
        "db_path": result.db_path,
        "predictions": [prediction.to_dict() for prediction in result.predictions],
    }

@router.get("/coverage/odds")
def odds_coverage(
    event_id: str | None = Query(default=None),
    sport: str | None = Query(default=None),
    competition: str | None = Query(default=None),
    required_markets: str = Query(default="1x2"),
    decision_at: str | None = Query(default=None),
    user=Depends(get_current_user),
):
    markets = tuple(market.strip() for market in required_markets.split(",") if market.strip())
    report = service.odds_coverage_report(
        event_id=event_id,
        sport=sport,
        competition=competition,
        required_markets=markets or ("1x2",),
        decision_at=decision_at,
    )
    return {
        "source": report.source,
        "event_count": report.event_count,
        "snapshot_count": report.snapshot_count,
        "required_markets": list(report.required_markets),
        "events": [
            {
                "event_id": event.event_id,
                "sport": event.sport,
                "competition": event.competition,
                "participant_1": event.participant_1,
                "participant_2": event.participant_2,
                "commence_time": event.commence_time,
                "snapshot_count": event.snapshot_count,
                "bookmaker_count": event.bookmaker_count,
                "markets": list(event.markets),
                "selections_by_market": {market: list(values) for market, values in event.selections_by_market.items()},
                "bookmakers_by_market": {market: list(values) for market, values in event.bookmakers_by_market.items()},
                "first_captured_at": event.first_captured_at,
                "last_captured_at": event.last_captured_at,
                "completeness": {
                    "score": event.completeness.score,
                    "status": event.completeness.status,
                    "snapshot_count": event.completeness.snapshot_count,
                    "decision_snapshot_count": event.completeness.decision_snapshot_count,
                    "closing_snapshot_count": event.completeness.closing_snapshot_count,
                    "bookmaker_count": event.completeness.bookmaker_count,
                    "available_markets": list(event.completeness.available_markets),
                    "required_markets": list(event.completeness.required_markets),
                    "missing_data": list(event.completeness.missing_data),
                    "blocking_missing_data": list(event.completeness.blocking_missing_data),
                    "degrading_missing_data": list(event.completeness.degrading_missing_data),
                },
            }
            for event in report.events
        ],
    }
@router.get("/completeness/betting")
def betting_completeness(
    event_id: str | None = Query(default=None),
    decision_at: str | None = Query(default=None),
    required_markets: str = Query(default="1x2"),
    user=Depends(get_current_user),
):
    markets = tuple(market.strip() for market in required_markets.split(",") if market.strip())
    result = service.betting_completeness_report(
        event_id=event_id,
        decision_at=decision_at,
        required_markets=markets or ("1x2",),
    )
    return {
        "score": result.score,
        "status": result.status,
        "snapshot_count": result.snapshot_count,
        "decision_snapshot_count": result.decision_snapshot_count,
        "closing_snapshot_count": result.closing_snapshot_count,
        "bookmaker_count": result.bookmaker_count,
        "available_markets": list(result.available_markets),
        "required_markets": list(result.required_markets),
        "missing_data": list(result.missing_data),
        "blocking_missing_data": list(result.blocking_missing_data),
        "degrading_missing_data": list(result.degrading_missing_data),
        "warning": "Betting completeness describes odds/snapshot readiness only; it must not be used as a sports scenario feature.",
    }
@router.get("/clv")
def clv_report(
    decision_at: str = Query(...),
    event_id: str | None = Query(default=None),
    market: str | None = Query(default=None),
    user=Depends(get_current_user),
):
    report = service.snapshot_clv_report(decision_at=decision_at, event_id=event_id, market=market)
    return {
        "decision_at": report.decision_at,
        "count": len(report.rows),
        "skipped_groups": report.skipped_groups,
        "rows": [row.__dict__ for row in report.rows],
    }

@router.post("/collect/odds-api")
def collect_odds_api(
    sport_key: str = Query(...),
    sport: str = Query(...),
    competition: str = Query(...),
    regions: str = Query(default="eu"),
    markets: str = Query(default="h2h"),
    bookmakers: str | None = Query(default=None),
    user=Depends(get_current_user),
):
    result = service.collect_the_odds_api_snapshots(
        sport_key=sport_key,
        sport=sport,
        competition=competition,
        regions=regions,
        markets=markets,
        bookmakers=bookmakers,
    )
    return {
        "source": result.source,
        "captured_at": result.captured_at,
        "generated_count": result.generated_count,
        "inserted_count": result.inserted_count,
        "db_path": result.db_path,
    }
@router.get("/ticket-families/ligue1")
def ligue1_ticket_families(
    min_sporting_completeness: int = Query(default=70, ge=0, le=100),
    require_betting_ready: bool = Query(default=False),
    decision_at: str | None = Query(default=None),
    user=Depends(get_current_user),
):
    result = service.build_ligue1_ticket_family_report(
        min_sporting_completeness=min_sporting_completeness,
        require_betting_ready=require_betting_ready,
        decision_at=decision_at,
    )
    return {
        "source": result.source,
        "n_predictions": result.n_predictions,
        "n_candidates": result.n_candidates,
        "min_sporting_completeness": result.min_sporting_completeness,
        "warnings": list(result.warnings),
        "candidates": [
            {
                "family": candidate.family,
                "event_id": candidate.event_id,
                "kickoff": candidate.kickoff,
                "home": candidate.home,
                "away": candidate.away,
                "markets": list(candidate.markets),
                "rationale": candidate.rationale,
                "risk_level": candidate.risk_level,
                "readiness": candidate.readiness,
                "sporting_completeness_score": candidate.sporting_completeness_score,
                "betting_completeness_score": candidate.betting_completeness_score,
                "blocking_reasons": list(candidate.blocking_reasons),
                "degrading_reasons": list(candidate.degrading_reasons),
            }
            for candidate in result.candidates
        ],
    }
@router.get("/backtests/ligue1/scenarios")
def ligue1_scenario_backtest(user=Depends(get_current_user)):
    result = service.run_ligue1_scenario_backtest()
    return {
        "source": result.source,
        "n_predictions": result.n_predictions,
        "n_matched": result.n_matched,
        "unmatched_count": result.unmatched_count,
        "n_signals": result.n_signals,
        "open_accuracy": result.open_accuracy,
        "btts_accuracy": result.btts_accuracy,
        "ascendant_accuracy": result.ascendant_accuracy,
        "rows": [row.__dict__ for row in result.rows],
        "warning": "Scenario backtest measures sporting scenario descriptors only; it does not use odds, EV, CLV, bookmakers, boosts, or prices.",
    }

@router.get("/backtests/ligue1/boosted-tickets")
def ligue1_boosted_ticket_backtest(
    selections_per_ticket: int = Query(default=5, ge=1, le=10),
    stake: float = Query(default=50.0, gt=0),
    max_tickets: int | None = Query(default=10, ge=1),
    min_odd: float | None = Query(default=None, gt=1.0),
    max_odd: float | None = Query(default=None, gt=1.0),
    user=Depends(get_current_user),
):
    result = service.run_ligue1_boosted_ticket_backtest(
        selections_per_ticket=selections_per_ticket,
        stake=stake,
        max_tickets=max_tickets,
        min_odd=min_odd,
        max_odd=max_odd,
    )
    return {
        "source": result.source,
        "n_selections": result.n_selections,
        "n_tickets": result.n_tickets,
        "selections_per_ticket": result.selections_per_ticket,
        "stake": result.stake,
        "total_staked": result.total_staked,
        "total_profit": result.total_profit,
        "roi": result.roi,
        "hit_rate": result.hit_rate,
        "max_drawdown": result.max_drawdown,
        "avg_estimated_ev": result.avg_estimated_ev,
        "tickets": [
            {
                "ticket_id": ticket.ticket_id,
                "raw_odds": ticket.raw_odds,
                "boost_rate": ticket.boost_rate,
                "boosted_odds": ticket.boosted_odds,
                "probability": ticket.probability,
                "estimated_ev": ticket.estimated_ev,
                "won": ticket.won,
                "stake": ticket.stake,
                "profit": ticket.profit,
                "cumulative_profit": ticket.cumulative_profit,
                "drawdown": ticket.drawdown,
                "selections": [selection.__dict__ for selection in ticket.selections],
            }
            for ticket in result.tickets
        ],
        "warning": "Backtest uses market no-vig probabilities and historical Football-Data odds as proxy; this validates mechanics, not a proven betting edge.",
    }


