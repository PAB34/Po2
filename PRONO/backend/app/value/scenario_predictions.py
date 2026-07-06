"""Scenario prediction persistence for odds-blind PRONO research."""
from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
from typing import Any, Iterable, Mapping

from .ligue1_scenarios import ligue1_match_to_scenario_payload, scenario_report_to_dict
from .scenarios import scenario_from_mapping
from .snapshots import payload_hash


@dataclass(frozen=True)
class ScenarioPrediction:
    sport: str
    competition: str
    event_id: str
    home: str
    away: str
    kickoff: str
    predicted_at: str
    source: str
    input_hash: str
    sporting_input_json: str
    scenario_json: str

    def normalized(self) -> "ScenarioPrediction":
        required = {
            "sport": self.sport,
            "competition": self.competition,
            "event_id": self.event_id,
            "home": self.home,
            "away": self.away,
            "kickoff": self.kickoff,
            "predicted_at": self.predicted_at,
            "source": self.source,
            "input_hash": self.input_hash,
            "sporting_input_json": self.sporting_input_json,
            "scenario_json": self.scenario_json,
        }
        missing = [name for name, value in required.items() if not str(value or "").strip()]
        if missing:
            raise ValueError(f"Missing scenario prediction field(s): {', '.join(missing)}")
        return ScenarioPrediction(
            sport=self.sport.strip(),
            competition=self.competition.strip(),
            event_id=self.event_id.strip(),
            home=self.home.strip(),
            away=self.away.strip(),
            kickoff=self.kickoff.strip(),
            predicted_at=self.predicted_at.strip(),
            source=self.source.strip(),
            input_hash=self.input_hash.strip(),
            sporting_input_json=self.sporting_input_json.strip(),
            scenario_json=self.scenario_json.strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sport": self.sport,
            "competition": self.competition,
            "event_id": self.event_id,
            "home": self.home,
            "away": self.away,
            "kickoff": self.kickoff,
            "predicted_at": self.predicted_at,
            "source": self.source,
            "input_hash": self.input_hash,
            "sporting_input": json.loads(self.sporting_input_json),
            "scenario": json.loads(self.scenario_json),
        }


@dataclass(frozen=True)
class ScenarioPredictionPersistResult:
    source: str
    predicted_at: str
    generated_count: int
    inserted_count: int
    db_path: str
    predictions: tuple[ScenarioPrediction, ...]


class ScenarioPredictionStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS scenario_predictions ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "sport TEXT NOT NULL,"
                "competition TEXT NOT NULL,"
                "event_id TEXT NOT NULL,"
                "home TEXT NOT NULL,"
                "away TEXT NOT NULL,"
                "kickoff TEXT NOT NULL,"
                "predicted_at TEXT NOT NULL,"
                "source TEXT NOT NULL,"
                "input_hash TEXT NOT NULL,"
                "sporting_input_json TEXT NOT NULL,"
                "scenario_json TEXT NOT NULL,"
                "UNIQUE(source, event_id, predicted_at, input_hash)"
                ")"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS ix_scenario_predictions_event ON scenario_predictions(event_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_scenario_predictions_time ON scenario_predictions(predicted_at, kickoff)")

    def insert_many(self, predictions: Iterable[ScenarioPrediction]) -> int:
        rows = [prediction.normalized() for prediction in predictions]
        if not rows:
            return 0
        inserted = 0
        with self._connect() as conn:
            for prediction in rows:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO scenario_predictions("
                    "sport, competition, event_id, home, away, kickoff, predicted_at, source, "
                    "input_hash, sporting_input_json, scenario_json"
                    ") VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        prediction.sport,
                        prediction.competition,
                        prediction.event_id,
                        prediction.home,
                        prediction.away,
                        prediction.kickoff,
                        prediction.predicted_at,
                        prediction.source,
                        prediction.input_hash,
                        prediction.sporting_input_json,
                        prediction.scenario_json,
                    ),
                )
                inserted += cur.rowcount
        return inserted

    def count(self) -> int:
        conn = self._connect()
        try:
            row = conn.execute("SELECT COUNT(*) AS n FROM scenario_predictions").fetchone()
            return int(row["n"] if row else 0)
        finally:
            conn.close()

    def list_predictions(self, event_id: str | None = None) -> list[ScenarioPrediction]:
        sql = "SELECT * FROM scenario_predictions WHERE 1=1"
        params: list[object] = []
        if event_id is not None:
            sql += " AND event_id=?"
            params.append(event_id)
        sql += " ORDER BY predicted_at, kickoff, home, away"
        conn = self._connect()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [_prediction_from_row(row) for row in rows]


def predictions_from_ligue1_journee(
    payload: Mapping[str, Any],
    predicted_at: str,
    source: str = "ligue1-journee",
) -> list[ScenarioPrediction]:
    matches = payload.get("matches") or []
    if not isinstance(matches, list | tuple):
        raise ValueError("journee.matches must be a list.")
    break_info = payload.get("break") if isinstance(payload.get("break"), Mapping) else {}
    predictions: list[ScenarioPrediction] = []
    for match in matches:
        if not isinstance(match, Mapping):
            raise ValueError("journee.matches items must be objects.")
        sporting_input = ligue1_match_to_scenario_payload(match, break_info=break_info)
        report = scenario_from_mapping(sporting_input)
        home = str(sporting_input["home"]["team"]).strip()
        away = str(sporting_input["away"]["team"]).strip()
        kickoff = _optional_text(match.get("kickoff")) or "unknown-kickoff"
        event_id = stable_ligue1_event_id(kickoff=kickoff, home=home, away=away)
        predictions.append(ScenarioPrediction(
            sport="football",
            competition="ligue1",
            event_id=event_id,
            home=home,
            away=away,
            kickoff=kickoff,
            predicted_at=predicted_at,
            source=source,
            input_hash=payload_hash(sporting_input),
            sporting_input_json=_canonical_json(sporting_input),
            scenario_json=_canonical_json(scenario_report_to_dict(report)),
        ))
    return predictions


def stable_ligue1_event_id(kickoff: str, home: str, away: str) -> str:
    digest = payload_hash({"competition": "ligue1", "kickoff": kickoff, "home": home, "away": away})[:16]
    return f"ligue1-{digest}"


def _prediction_from_row(row: sqlite3.Row) -> ScenarioPrediction:
    return ScenarioPrediction(
        sport=row["sport"],
        competition=row["competition"],
        event_id=row["event_id"],
        home=row["home"],
        away=row["away"],
        kickoff=row["kickoff"],
        predicted_at=row["predicted_at"],
        source=row["source"],
        input_hash=row["input_hash"],
        sporting_input_json=row["sporting_input_json"],
        scenario_json=row["scenario_json"],
    )


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None