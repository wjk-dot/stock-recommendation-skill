from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

from app.models import DailyBar


class BarRepository:
    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        with duckdb.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_bars (
                    symbol VARCHAR,
                    trade_date DATE,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume DOUBLE,
                    amount DOUBLE,
                    adjust_factor DOUBLE,
                    PRIMARY KEY (symbol, trade_date)
                )
                """
            )

    def upsert(self, bars: list[DailyBar]) -> None:
        if not bars:
            return
        with duckdb.connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO daily_bars VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (b.symbol, b.trade_date, b.open, b.high, b.low, b.close, b.volume, b.amount, b.adjust_factor)
                    for b in bars
                ],
            )

    def get(self, symbol: str, start: date, end: date) -> list[DailyBar]:
        with duckdb.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT symbol, trade_date, open, high, low, close, volume, amount, adjust_factor
                FROM daily_bars
                WHERE symbol = ? AND trade_date BETWEEN ? AND ?
                ORDER BY trade_date
                """,
                [symbol, start, end],
            ).fetchall()
        return [DailyBar(**dict(zip(("symbol", "trade_date", "open", "high", "low", "close", "volume", "amount", "adjust_factor"), row))) for row in rows]
