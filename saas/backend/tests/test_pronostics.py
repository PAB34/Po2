from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.pronostics import PronosticsMatch, PronosticsPasswordReset
from app.schemas.pronostics import PronosticsPredictionWrite
from app.services.football_data import FootballDataClient, build_pronostics_model_feed
from app.services.pronostics import (
    _normalize_team,
    _score_prediction,
    authenticate_player,
    calculate_ranking,
    change_player_password,
    create_player,
    ensure_matches,
    fifa_rank,
    save_predictions,
    request_password_reset,
    reset_password,
    sync_scores,
    update_player,
)


class FakeFootballDataClient(FootballDataClient):
    def __init__(self):
        super().__init__(token="test-token", base_url="https://example.test")
        self.paths: list[tuple[str, dict | None]] = []

    def get(self, path: str, *, params: dict | None = None) -> dict:
        self.paths.append((path, params))
        if path == "competitions/WC/teams":
            return {
                "teams": [
                    {
                        "id": 1,
                        "name": "Mexico",
                        "shortName": "Mexico",
                        "tla": "MEX",
                        "area": {"name": "Mexico", "code": "MEX"},
                        "crest": "https://crests.example/mex.png",
                    }
                ]
            }
        if path == "teams/1":
            return {
                "id": 1,
                "name": "Mexico",
                "shortName": "Mexico",
                "tla": "MEX",
                "area": {"name": "Mexico", "code": "MEX"},
                "crest": "https://crests.example/mex.png",
                "coach": {
                    "id": 10,
                    "name": "Coach Mexico",
                    "nationality": "Mexico",
                    "contract": {"start": "2024-01", "until": "2026-12"},
                },
                "squad": [
                    {
                        "id": 100,
                        "name": "Player One",
                        "position": "Attacker",
                        "dateOfBirth": "1999-01-01",
                        "nationality": "Mexico",
                        "shirtNumber": 9,
                        "currentTeam": {"id": 500, "name": "Club One", "contract": {"until": "2027-06"}},
                    }
                ],
                "staff": [{"id": 11, "name": "Assistant"}],
            }
        if path == "teams/1/matches":
            return {
                "resultSet": {"wins": 1, "draws": 0, "losses": 1},
                "matches": [
                    {
                        "homeTeam": {"name": "Mexico"},
                        "awayTeam": {"name": "Canada"},
                        "score": {"fullTime": {"home": 2, "away": 0}},
                    },
                    {
                        "homeTeam": {"name": "United States"},
                        "awayTeam": {"name": "Mexico"},
                        "score": {"fullTime": {"home": 1, "away": 0}},
                    },
                ],
            }
        if path == "persons/100/matches":
            return {
                "aggregations": {
                    "matchesOnPitch": 3,
                    "startingXI": 2,
                    "minutesPlayed": 210,
                    "goals": 1,
                    "assists": 2,
                    "subbedIn": 1,
                    "subbedOut": 1,
                    "yellowCards": 0,
                    "redCards": 0,
                }
            }
        if path == "competitions/WC/scorers":
            return {
                "scorers": [
                    {
                        "player": {"id": 100, "name": "Player One"},
                        "team": {"id": 1, "name": "Mexico"},
                        "goals": 2,
                        "assists": 1,
                        "penalties": 0,
                    }
                ]
            }
        raise AssertionError(f"Unexpected path {path}")


def test_score_prediction_barème():
    assert _score_prediction(2, 1, 2, 1) == (10, True, True)
    assert _score_prediction(3, 2, 2, 1) == (7, False, True)
    assert _score_prediction(2, 0, 2, 1) == (6, False, True)
    assert _score_prediction(0, 1, 2, 1) == (1, False, False)


def test_team_aliases_cover_api_english_names():
    assert _normalize_team("South Korea") == _normalize_team("Corée du Sud")
    assert _normalize_team("United States") == _normalize_team("Etats-Unis")
    assert _normalize_team("Ivory Coast") == _normalize_team("Côte d'Ivoire")


def test_fifa_ranking_is_exposed_for_known_teams():
    assert fifa_rank("France") == 1
    assert fifa_rank("Coree du Sud") == 25
    assert fifa_rank("Equipe inconnue") is None


def test_profile_update_rejects_an_existing_pseudo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        first = create_player(db, email="premier@example.com", password="motdepasse123", pseudo="Premier", service="CTM")
        create_player(db, email="second@example.com", password="motdepasse123", pseudo="Second", service="Voirie")
        updated = update_player(db, first, pseudo="Premier bis", service="Batiments")
        assert (updated.pseudo, updated.service) == ("Premier bis", "Batiments")

        try:
            update_player(db, updated, pseudo="Second", service="Batiments")
        except ValueError as exc:
            assert str(exc) == "PSEUDO_ALREADY_EXISTS"
        else:
            raise AssertionError("Le pseudo existant aurait du etre refuse.")


def test_password_reset_token_is_single_use(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    captured = {}
    monkeypatch.setattr("app.services.pronostics.settings.smtp_host", "smtp.example.com")
    monkeypatch.setattr("app.services.pronostics.settings.smtp_from_email", "pronostics@example.com")
    monkeypatch.setattr(
        "app.services.pronostics._send_password_reset_email",
        lambda email, pseudo, token: captured.update(email=email, pseudo=pseudo, token=token),
    )
    with Session(engine) as db:
        player = create_player(db, email="joueur@example.com", password="ancienmotdepasse", pseudo="Joueur", service="CTM")
        request_password_reset(db, player.email)
        assert captured["email"] == player.email
        assert captured["token"]
        assert db.query(PronosticsPasswordReset).count() == 1
        assert reset_password(db, captured["token"], "nouveaumotdepasse")
        assert not reset_password(db, captured["token"], "encoreunnouveau")

    with Session(engine) as db:
        assert authenticate_player(db, email="joueur@example.com", password="nouveaumotdepasse")
        assert not authenticate_player(db, email="joueur@example.com", password="ancienmotdepasse")


def test_change_player_password_requires_current_password():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        player = create_player(db, email="joueur@example.com", password="ancienmotdepasse", pseudo="Joueur", service="CTM")

        try:
            change_player_password(
                db,
                player,
                current_password="mauvaismotdepasse",
                new_password="nouveaumotdepasse",
            )
        except ValueError as exc:
            assert str(exc) == "INVALID_PASSWORD"
        else:
            raise AssertionError("Le mot de passe actuel invalide aurait du etre refuse.")

        change_player_password(
            db,
            player,
            current_password="ancienmotdepasse",
            new_password="nouveaumotdepasse",
        )

        assert authenticate_player(db, email="joueur@example.com", password="nouveaumotdepasse")
        assert not authenticate_player(db, email="joueur@example.com", password="ancienmotdepasse")


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


def test_ensure_matches_updates_existing_schedule_without_scores():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            PronosticsMatch(
                id="M001",
                group_name="A",
                team1="Mexique",
                team2="Afrique du Sud",
                match_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
                stadium="Ancien stade",
                real_score1=2,
                real_score2=1,
                locked=True,
            )
        )
        db.commit()

        ensure_matches(db)
        match = db.get(PronosticsMatch, "M001")

    assert match is not None
    assert match.match_at.isoformat() == "2026-06-11T19:00:00"
    assert match.stadium == "Estadio Azteca, Mexico City"
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


def test_model_feed_reports_unconfigured_without_token(monkeypatch):
    monkeypatch.setattr("app.services.football_data.settings.football_data_token", "")

    feed = build_pronostics_model_feed()

    assert feed["configured"] is False
    assert feed["summary"]["teams"] == 0
    assert "injury_status" in feed["unavailable_fields"]


def test_model_feed_collects_team_coach_squad_and_recent_form():
    client = FakeFootballDataClient()

    feed = build_pronostics_model_feed(client=client)

    assert feed["configured"] is True
    assert feed["summary"]["teams"] == 1
    assert feed["summary"]["players"] == 1
    assert feed["teams"][0]["local_team_key"] == "mexique"
    assert feed["teams"][0]["coach"]["name"] == "Coach Mexico"
    assert feed["teams"][0]["recent_form"]["goals_for"] == 2
    assert feed["teams"][0]["recent_form"]["goals_against"] == 1
    assert feed["teams"][0]["recent_form"]["clean_sheets"] == 1
    assert feed["players"][0]["current_team_name"] == "Club One"
    assert feed["competition_scorers"][0]["player_name"] == "Player One"
    assert not any(path == "persons/100/matches" for path, _ in client.paths)


def test_model_feed_can_enrich_player_recent_stats():
    client = FakeFootballDataClient()

    feed = build_pronostics_model_feed(client=client, include_player_matches=True)

    assert feed["summary"]["players_with_recent_match_stats"] == 1
    assert feed["coverage"]["player_recent_matches"]["status"] == "retrieved"
    assert feed["players"][0]["recent_stats"]["minutes_played"] == 210
    assert feed["players"][0]["recent_stats"]["goals"] == 1
    assert any(path == "persons/100/matches" for path, _ in client.paths)
