from datetime import date, timedelta

from app.backtest.engine import run_ma_cross
from app.models import DailyBar, FeeConfig


def make_bars(closes: list[float]) -> list[DailyBar]:
    return [
        DailyBar(symbol="000001", trade_date=date(2024, 1, 1) + timedelta(days=i), open=price, high=price, low=price, close=price, volume=1000, amount=10000)
        for i, price in enumerate(closes)
    ]


def test_ma_cross_respects_lot_size_and_costs():
    closes = [10, 10, 10, 10, 10, 12, 14, 12, 10, 8, 8, 8]
    result = run_ma_cross(
        make_bars(closes), symbol="000001", initial_cash=10000,
        fast_period=2, slow_period=3,
        fees=FeeConfig(commission_rate=0, min_commission_cny=0, stamp_duty_rate=0.001, transfer_rate=0, slippage_rate=0),
    )
    assert result.trade_count >= 2
    assert all(trade.quantity % 100 == 0 for trade in result.trades)
    assert result.final_equity < 10000
    assert result.max_drawdown <= 0
