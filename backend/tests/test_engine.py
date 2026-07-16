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


def test_ma_cross_returns_benchmark_curve_and_closed_trade_metrics():
    closes = [10, 10, 10, 10, 10, 12, 14, 12, 10, 8, 8, 8]
    result = run_ma_cross(
        make_bars(closes),
        symbol="000001",
        initial_cash=10000,
        fast_period=2,
        slow_period=3,
        fees=FeeConfig(commission_rate=0, min_commission_cny=0, stamp_duty_rate=0.001, transfer_rate=0, slippage_rate=0),
    )

    assert len(result.equity_curve) == len(closes)
    assert all("benchmark_equity" in point for point in result.equity_curve)
    assert result.equity_curve[-1]["equity"] == result.final_equity
    assert result.equity_curve[-1]["benchmark_equity"] == result.benchmark_final_equity
    assert result.excess_return == result.total_return - result.benchmark_return
    assert result.closed_trade_count == 1
    assert result.win_rate == 0
    assert result.profit_loss_ratio is None
    assert result.average_holding_days is not None


def test_ma_cross_executes_close_signal_at_next_open_and_liquidates_final_position():
    # 第 4 根 K 线收盘形成上穿，实际买入必须发生在第 5 根 K 线的开盘。
    bars = [
        DailyBar(symbol="000001", trade_date=date(2024, 1, 1) + timedelta(days=index), open=open_price, high=max(open_price, close), low=min(open_price, close), close=close, volume=1000, amount=10000)
        for index, (open_price, close) in enumerate([(10, 10), (10, 10), (10, 10), (10, 12), (15, 15)])
    ]
    result = run_ma_cross(
        bars,
        symbol="000001",
        initial_cash=10000,
        fast_period=2,
        slow_period=3,
        fees=FeeConfig(commission_rate=0, min_commission_cny=0, stamp_duty_rate=0, transfer_rate=0, slippage_rate=0),
    )

    assert [(trade.side, trade.trade_date, trade.price) for trade in result.trades] == [
        ("buy", date(2024, 1, 5), 15),
        ("sell", date(2024, 1, 5), 15),
    ]
    assert result.equity_curve[-1]["quantity"] == 0
    assert result.equity_curve[-1]["cash"] == result.final_equity
