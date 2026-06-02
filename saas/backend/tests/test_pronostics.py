from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.pronostics import PronosticsMatch
from app.schemas.pronostics import PronosticsPredictionWrite
from app.services.pronostics import (
    _normalize_team,
    _score_prediction,
    calculate_ranking,
    create_player,
    ensure_matches,
    save_predictions,
    sync_scores,
)


def test_score_prediction_barème():
    assert _score_prediction(2, 1, 2, 1) == (10, True, True)
    assert _score_prediction(3, 2, 2, 1) == (7, False, True)
    assert _score_prediction(2, 0, 2, 1) == (6, False, True)
    assert _score_prediction(0, 1, 2, 1) == (1, False, False)


def test_team_aliases_cover_api_english_names():
    assert _normalize_team("South Korea") == _normalize_team("Corée du Sud")
    assert _normalize_team("United States") == _normalize_team("Etats-Unis")
    assert _normalize_team("Ivory Coast") == _normalize_team("Côte d'Ivoire")


def test_sync_scores_updates_finished_match(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "matches": [
                    {
                        "status": "FINISHED",
                        "homeTeam": {"name": "Mexico"},
                        "awayTeam": {"name": "South Africa"},
                        "score": {"fullTime": {"home": 2, "away": 1}},
                    }
                ]
            }

    monkeypatch.setattr("app.services.pronostics.settings.football_data_token", "test-token")
    monkeypatch.setattr("app.services.pronostics.requests.get", lambda *args, **kwargs: FakeResponse())
    with Session(engine) as db:
        ensure_matches(db)
        result = sync_scores(db)
        match = db.get(PronosticsMatch, "M001")

    assert result == {"configured": True, "api_matches": 1, "finished": 1, "updated": 1, "unmatched": 0}
    assert match is not None
    assert (match.real_score1, match.real_score2, match.locked) == (2, 1, True)


def test_ranking_recalculates_points_from_real_scores():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        ensure_matches(db)
        player = create_player(db, email="joueur@example.com", password="motdepasse123", pseudo="Joueur", service="CTM")
        save_predictions(db, player, [PronosticsPredictionWrite(match_id="M001", score1=2, score2=1)])
        match = db.get(PronosticsMatch, "M001")
        assert match is not None
        match.real_score1 = 2
        match.real_score2 = 1
        match.locked = True
        db.commit()

        ranking = calculate_ranking(db)

    assert ranking[0].pseudo == "Joueur"
    assert ranking[0].points == 10
    assert ranking[0].exact_scores == 1
    assert ranking[0].good_results == 1
