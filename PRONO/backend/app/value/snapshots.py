"""Odds snapshot model and lightweight SQLite storage."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import sqlite3
from typing import Iterable


@dataclass(frozen=True)
class OddsSnapshot:
    sport: str
    competition: str
    event_id: str
    participant_1: str
    participant_2: str
    market: str
    selection: str
    bookmaker: str
    odd: float
    captured_at: str
    commence_time: str
    source: str
    last_update: str | None = None
    raw_payload_hash: str | None = None

    def normalized(self) -> "OddsSnapshot":
        odd = float(self.odd)
        if odd <= 1.0:
            raise ValueError("Snapshot odd must be greater than 1.0.")
        required = {
            "sport": self.sport,
            "competition": self.competition,
            "event_id": self.event_id,
            "participant_1": self.participant_1,
            "participant_2": self.participant_2,
            "market": self.market,
            "selection": self.selection,
            "bookmaker": self.bookmaker,
            "captured_at": self.captured_at,
            "commence_time": self.commence_time,
            "source": self.source,
        }
        missing = [name for name, value in required.items() if not str(value or "").strip()]
        if missing:
            raise ValueError(f"Missing snapshot field(s): {', '.join(missing)}")
        return OddsSnapshot(
            sport=self.sport.strip(),
            competition=self.competition.strip(),
            event_id=self.event_id.strip(),
            participant_1=self.participant_1.strip(),
            participant_2=self.participant_2.strip(),
            market=self.market.strip(),
            selection=self.selection.strip(),
            bookmaker=self.bookmaker.strip(),
            odd=odd,
            captured_at=self.captured_at.strip(),
            commence_time=self.commence_time.strip(),
            source=self.source.strip(),
            last_update=(self.last_update.strip() if self.last_update else None),
            raw_payload_hash=(self.raw_payload_hash.strip() if self.raw_payload_hash else None),
        )


def payload_hash(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class OddsSnapshotStore:
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
                "CREATE TABLE IF NOT EXISTS odds_snapshots ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "sport TEXT NOT NULL,"
                "competition TEXT NOT NULL,"
                "event_id TEXT NOT NULL,"
                "participant_1 TEXT NOT NULL,"
                "participant_2 TEXT NOT NULL,"
                "market TEXT NOT NULL,"
                "selection TEXT NOT NULL,"
                "bookmaker TEXT NOT NULL,"
                "odd REAL NOT NULL,"
                "captured_at TEXT NOT NULL,"
                "last_update TEXT,"
                "commence_time TEXT NOT NULL,"
                "source TEXT NOT NULL,"
                "raw_payload_hash TEXT,"
                "UNIQUE(source, event_id, market, selection, bookmaker, captured_at)"
                ")"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS ix_odds_snapshots_event ON odds_snapshots(event_id, market)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_odds_snapshots_time ON odds_snapshots(captured_at, commence_time)")

    def insert_many(self, snapshots: Iterable[OddsSnapshot]) -> int:
        rows = [s.normalized() for s in snapshots]
        if not rows:
            return 0
        inserted = 0
        with self._connect() as conn:
            for s in rows:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO odds_snapshots("
                    "sport, competition, event_id, participant_1, participant_2, market, selection, "
                    "bookmaker, odd, captured_at, last_update, commence_time, source, raw_payload_hash"
                    ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        s.sport,
                        s.competition,
                        s.event_id,
                        s.participant_1,
                        s.participant_2,
                        s.market,
                        s.selection,
                        s.bookmaker,
                        s.odd,
                        s.captured_at,
                        s.last_update,
                        s.commence_time,
                        s.source,
                        s.raw_payload_hash,
                    ),
                )
                inserted += cur.rowcount
        return inserted

    def list_event_snapshots(self, event_id: str, market: str | None = None) -> list[OddsSnapshot]:
        sql = "SELECT * FROM odds_snapshots WHERE event_id=?"
        params: list[object] = [event_id]
        if market is not None:
            sql += " AND market=?"
            params.append(market)
        sql += " ORDER BY captured_at, bookmaker, selection"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [OddsSnapshot(
            sport=row["sport"],
            competition=row["competition"],
            event_id=row["event_id"],
            participant_1=row["participant_1"],
            participant_2=row["participant_2"],
            market=row["market"],
            selection=row["selection"],
            bookmaker=row["bookmaker"],
            odd=row["odd"],
            captured_at=row["captured_at"],
            last_update=row["last_update"],
            commence_time=row["commence_time"],
            source=row["source"],
            raw_payload_hash=row["raw_payload_hash"],
        ) for row in rows]
    def count(self) -> int:
        conn = self._connect()
        try:
            row = conn.execute("SELECT COUNT(*) AS n FROM odds_snapshots").fetchone()
            return int(row["n"] if row else 0)
        finally:
            conn.close()

    def count_by_source(self) -> dict[str, int]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT source, COUNT(*) AS n FROM odds_snapshots GROUP BY source ORDER BY source"
            ).fetchall()
            return {str(row["source"]): int(row["n"]) for row in rows}
        finally:
            conn.close()
    def list_snapshots(self, event_id: str | None = None, market: str | None = None) -> list[OddsSnapshot]:
        sql = "SELECT * FROM odds_snapshots WHERE 1=1"
        params: list[object] = []
        if event_id is not None:
            sql += " AND event_id=?"
            params.append(event_id)
        if market is not None:
            sql += " AND market=?"
            params.append(market)
        sql += " ORDER BY event_id, market, selection, bookmaker, captured_at"
        conn = self._connect()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [OddsSnapshot(
            sport=row["sport"],
            competition=row["competition"],
            event_id=row["event_id"],
            participant_1=row["participant_1"],
            participant_2=row["participant_2"],
            market=row["market"],
            selection=row["selection"],
            bookmaker=row["bookmaker"],
            odd=row["odd"],
            captured_at=row["captured_at"],
            last_update=row["last_update"],
            commence_time=row["commence_time"],
            source=row["source"],
            raw_payload_hash=row["raw_payload_hash"],
        ) for row in rows]

