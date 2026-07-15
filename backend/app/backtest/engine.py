from __future__ import annotations

from datetime import date

from app.models import BacktestResult, DailyBar, FeeConfig, Trade


def _money(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def _fees(gross: float, side: str, config: FeeConfig) -> float:
    commission = max(gross * config.commission_rate, config.min_commission_cny)
    transfer = gross * config.transfer_rate
    stamp = gross * config.stamp_duty_rate if side == "sell" else 0
    return _money(commission + transfer + stamp)


def run_ma_cross(
    bars: list[DailyBar],
    *,
    symbol: str,
    initial_cash: float,
    fast_period: int = 5,
    slow_period: int = 20,
    fees: FeeConfig | None = None,
) -> BacktestResult:
    """收盘产生信号，下一交易日开盘成交；单股全仓、100 股整数手。"""
    if fast_period < 1 or slow_period <= fast_period:
        raise ValueError("slow_period 必须大于 fast_period，且周期必须为正整数")
    if len(bars) < slow_period + 1:
        raise ValueError(f"行情数据至少需要 {slow_period + 1} 个交易日")
    fees = fees or FeeConfig()
    bars = sorted(bars, key=lambda item: item.trade_date)
    closes = [bar.close for bar in bars]
    cash = float(initial_cash)
    quantity = 0
    buy_cost = 0.0
    trades: list[Trade] = []
    equity_curve: list[dict[str, object]] = []
    warnings: list[str] = []

    def execute_buy(bar: DailyBar) -> None:
        nonlocal cash, quantity, buy_cost
        price = bar.open * (1 + fees.slippage_rate)
        affordable = int(cash // price // 100) * 100
        if affordable < 100:
            return
        gross = price * affordable
        cost = _money(gross + _fees(gross, "buy", fees))
        while affordable >= 100 and cost > cash:
            affordable -= 100
            gross = price * affordable
            cost = _money(gross + _fees(gross, "buy", fees))
        if affordable < 100:
            return
        fee = _fees(gross, "buy", fees)
        cash = _money(cash - cost)
        quantity = affordable
        buy_cost = cost
        trades.append(Trade(trade_date=bar.trade_date, side="buy", price=_money(price), quantity=quantity, gross=_money(gross), fees=fee))

    def execute_sell(bar: DailyBar) -> None:
        nonlocal cash, quantity, buy_cost
        if quantity < 100:
            return
        price = bar.open * (1 - fees.slippage_rate)
        gross = price * quantity
        fee = _fees(gross, "sell", fees)
        cash = _money(cash + gross - fee)
        trades.append(Trade(trade_date=bar.trade_date, side="sell", price=_money(price), quantity=quantity, gross=_money(gross), fees=fee))
        quantity = 0
        buy_cost = 0

    for i, bar in enumerate(bars):
        if i >= slow_period and i + 1 < len(bars):
            fast_now = sum(closes[i - fast_period + 1 : i + 1]) / fast_period
            slow_now = sum(closes[i - slow_period + 1 : i + 1]) / slow_period
            fast_prev = sum(closes[i - fast_period : i]) / fast_period
            slow_prev = sum(closes[i - slow_period : i]) / slow_period
            next_bar = bars[i + 1]
            if quantity == 0 and fast_prev <= slow_prev and fast_now > slow_now:
                execute_buy(next_bar)
            elif quantity > 0 and fast_prev >= slow_prev and fast_now < slow_now:
                execute_sell(next_bar)
        market_value = quantity * bar.close
        equity_curve.append({"trade_date": bar.trade_date.isoformat(), "equity": _money(cash + market_value), "cash": _money(cash), "quantity": quantity})

    if quantity > 0:
        execute_sell(bars[-1])
        equity_curve[-1]["equity"] = _money(cash)
        equity_curve[-1]["cash"] = _money(cash)
        equity_curve[-1]["quantity"] = 0

    values = [float(point["equity"]) for point in equity_curve]
    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value / peak - 1 if peak else 0)
    final_equity = values[-1]
    total_return = final_equity / initial_cash - 1
    days = max((bars[-1].trade_date - bars[0].trade_date).days, 1)
    annual_return = (final_equity / initial_cash) ** (365 / days) - 1 if final_equity > 0 else None
    if not trades:
        warnings.append("该时间区间没有产生可执行交易信号")
    return BacktestResult(
        symbol=symbol, start_date=bars[0].trade_date, end_date=bars[-1].trade_date,
        strategy="ma_cross", total_return=total_return, annual_return=annual_return,
        max_drawdown=max_drawdown, trade_count=len(trades), final_equity=final_equity,
        equity_curve=equity_curve, trades=trades, warnings=warnings,
    )
