from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class DailyBar(BaseModel):
    symbol: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float = 0
    amount: float = 0
    adjust_factor: float | None = None


class FeeConfig(BaseModel):
    commission_rate: float = Field(0.0003, ge=0)
    min_commission_cny: float = Field(5, ge=0)
    stamp_duty_rate: float = Field(0.0005, ge=0)
    transfer_rate: float = Field(0.00001, ge=0)
    slippage_rate: float = Field(0.0002, ge=0)


class BacktestRequest(BaseModel):
    symbol: str = Field(min_length=1)
    start_date: date
    end_date: date
    strategy: Literal["ma_cross"] = "ma_cross"
    parameters: dict[str, Any] = Field(default_factory=lambda: {"fast_period": 5, "slow_period": 20})
    initial_cash: float = Field(gt=0)
    fees: FeeConfig = Field(default_factory=FeeConfig)


class Trade(BaseModel):
    trade_date: date
    side: Literal["buy", "sell"]
    price: float
    quantity: int
    gross: float
    fees: float


class BacktestResult(BaseModel):
    symbol: str
    start_date: date
    end_date: date
    strategy: str
    total_return: float
    annual_return: float | None
    max_drawdown: float
    trade_count: int
    final_equity: float
    equity_curve: list[dict[str, Any]]
    trades: list[Trade]
    data_source: str = "unknown"
    warnings: list[str] = Field(default_factory=list)


class MarketFlow(BaseModel):
    as_of: datetime
    source: str
    scope: str
    net_inflow_cny: float | None = None
    main_force_inflow_cny: float | None = None
    up_count: int | None = None
    down_count: int | None = None
    flat_count: int | None = None
    limit_up_count: int | None = None
    limit_down_count: int | None = None
    sectors: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
