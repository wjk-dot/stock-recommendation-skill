from __future__ import annotations

from datetime import date
from typing import Protocol

from app.models import DailyBar, MarketFlow


class MarketDataProvider(Protocol):
    def get_daily_bars(self, symbol: str, start: date, end: date) -> list[DailyBar]: ...

    def get_market_flow(self) -> MarketFlow: ...
