from __future__ import annotations

from datetime import date

from app.models import BacktestResult, DailyBar, FeeConfig, Trade


LOT_SIZE = 100


def _money(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def _fees(gross: float, side: str, config: FeeConfig) -> float:
    commission = max(gross * config.commission_rate, config.min_commission_cny)
    transfer = gross * config.transfer_rate
    stamp = gross * config.stamp_duty_rate if side == "sell" else 0
    return _money(commission + transfer + stamp)


def _buy_all(cash: float, price: float, config: FeeConfig) -> tuple[int, float, float, float]:
    """Return quantity, gross, fees and remaining cash for an all-in A-share buy."""
    affordable = int(cash // price // LOT_SIZE) * LOT_SIZE
    while affordable >= LOT_SIZE:
        gross = price * affordable
        fee = _fees(gross, "buy", config)
        total_cost = _money(gross + fee)
        if total_cost <= cash:
            return affordable, _money(gross), fee, _money(cash - total_cost)
        affordable -= LOT_SIZE
    return 0, 0.0, 0.0, _money(cash)


def _sell_all(cash: float, quantity: int, price: float, config: FeeConfig) -> tuple[float, float, float]:
    """Return updated cash, gross and fees for a full position sell."""
    gross = _money(price * quantity)
    fee = _fees(gross, "sell", config)
    return _money(cash + gross - fee), gross, fee


def _drawdown(values: list[float]) -> float:
    peak = values[0]
    result = 0.0
    for value in values:
        peak = max(peak, value)
        result = min(result, value / peak - 1 if peak else 0.0)
    return result


def _pair_metrics(closed_positions: list[dict[str, float]]) -> tuple[float | None, float | None, float | None]:
    if not closed_positions:
        return None, None, None
    pnl_values = [position["pnl"] for position in closed_positions]
    wins = [value for value in pnl_values if value > 0]
    losses = [value for value in pnl_values if value < 0]
    win_rate = len(wins) / len(pnl_values)
    profit_loss_ratio = (sum(wins) / len(wins)) / abs(sum(losses) / len(losses)) if wins and losses else None
    average_holding_days = sum(position["holding_days"] for position in closed_positions) / len(closed_positions)
    return win_rate, profit_loss_ratio, average_holding_days


def run_ma_cross(
    bars: list[DailyBar],
    *,
    symbol: str,
    initial_cash: float,
    fast_period: int = 5,
    slow_period: int = 20,
    fees: FeeConfig | None = None,
) -> BacktestResult:
    """MA cross: close generates a signal; the next trading day's open executes it.

    The benchmark uses the same capital, lot-size, fees and slippage: buy on the
    first available open and sell at the final available close. It is therefore a
    fair Buy & Hold comparison rather than a raw close-to-close percentage.
    """
    if fast_period < 1 or slow_period <= fast_period:
        raise ValueError("slow_period 必须大于 fast_period，且周期必须为正整数")
    if len(bars) < slow_period + 1:
        raise ValueError(f"行情数据至少需要 {slow_period + 1} 个交易日")

    fees = fees or FeeConfig()
    bars = sorted(bars, key=lambda item: item.trade_date)
    closes = [bar.close for bar in bars]
    cash = _money(initial_cash)
    quantity = 0
    entry_cost = 0.0
    entry_date: date | None = None
    pending_action: str | None = None
    trades: list[Trade] = []
    closed_positions: list[dict[str, float]] = []
    equity_curve: list[dict[str, object]] = []
    warnings: list[str] = []

    benchmark_cash = _money(initial_cash)
    benchmark_quantity = 0

    def execute_buy(bar: DailyBar) -> None:
        nonlocal cash, quantity, entry_cost, entry_date
        price = _money(bar.open * (1 + fees.slippage_rate))
        bought, gross, fee, remaining_cash = _buy_all(cash, price, fees)
        if bought < LOT_SIZE:
            warnings.append(f"{bar.trade_date.isoformat()} 买入信号未成交：资金不足以覆盖 1 手及费用")
            return
        cost = _money(cash - remaining_cash)
        cash = remaining_cash
        quantity = bought
        entry_cost = cost
        entry_date = bar.trade_date
        trades.append(Trade(trade_date=bar.trade_date, side="buy", price=price, quantity=bought, gross=gross, fees=fee))

    def execute_sell(bar: DailyBar, *, at_close: bool = False) -> None:
        nonlocal cash, quantity, entry_cost, entry_date
        if quantity < LOT_SIZE:
            return
        raw_price = bar.close if at_close else bar.open
        price = _money(raw_price * (1 - fees.slippage_rate))
        sold_quantity = quantity
        cash, gross, fee = _sell_all(cash, sold_quantity, price, fees)
        proceeds = _money(gross - fee)
        trades.append(Trade(trade_date=bar.trade_date, side="sell", price=price, quantity=sold_quantity, gross=gross, fees=fee))
        if entry_date is not None:
            closed_positions.append(
                {
                    "pnl": _money(proceeds - entry_cost),
                    "holding_days": float(max((bar.trade_date - entry_date).days, 0)),
                }
            )
        quantity = 0
        entry_cost = 0.0
        entry_date = None

    for index, bar in enumerate(bars):
        if index == 0:
            benchmark_price = _money(bar.open * (1 + fees.slippage_rate))
            benchmark_quantity, _, _, benchmark_cash = _buy_all(benchmark_cash, benchmark_price, fees)
            if benchmark_quantity < LOT_SIZE:
                warnings.append("Buy & Hold 基准未建仓：初始资金不足以覆盖 1 手及费用")

        # A signal from the previous close is executed only at today's open.
        if pending_action == "buy" and quantity == 0:
            execute_buy(bar)
        elif pending_action == "sell" and quantity > 0:
            execute_sell(bar)
        pending_action = None

        is_last_bar = index == len(bars) - 1
        if is_last_bar:
            # Close outstanding positions at the final close so final equity is realizable.
            if quantity > 0:
                execute_sell(bar, at_close=True)
            if benchmark_quantity >= LOT_SIZE:
                benchmark_price = _money(bar.close * (1 - fees.slippage_rate))
                benchmark_cash, _, _ = _sell_all(benchmark_cash, benchmark_quantity, benchmark_price, fees)
                benchmark_quantity = 0

        strategy_equity = _money(cash + quantity * bar.close)
        benchmark_equity = _money(benchmark_cash + benchmark_quantity * bar.close)
        equity_curve.append(
            {
                "trade_date": bar.trade_date.isoformat(),
                "equity": strategy_equity,
                "benchmark_equity": benchmark_equity,
                "cash": _money(cash),
                "quantity": quantity,
            }
        )

        # Today's close forms a signal for tomorrow's open. The final bar has no next open.
        if index >= slow_period and not is_last_bar:
            fast_now = sum(closes[index - fast_period + 1 : index + 1]) / fast_period
            slow_now = sum(closes[index - slow_period + 1 : index + 1]) / slow_period
            fast_prev = sum(closes[index - fast_period : index]) / fast_period
            slow_prev = sum(closes[index - slow_period : index]) / slow_period
            if quantity == 0 and fast_prev <= slow_prev and fast_now > slow_now:
                pending_action = "buy"
            elif quantity > 0 and fast_prev >= slow_prev and fast_now < slow_now:
                pending_action = "sell"

    values = [float(point["equity"]) for point in equity_curve]
    final_equity = values[-1]
    benchmark_final_equity = float(equity_curve[-1]["benchmark_equity"])
    total_return = final_equity / initial_cash - 1
    benchmark_return = benchmark_final_equity / initial_cash - 1
    days = max((bars[-1].trade_date - bars[0].trade_date).days, 1)
    annual_return = (final_equity / initial_cash) ** (365 / days) - 1 if final_equity > 0 else None
    win_rate, profit_loss_ratio, average_holding_days = _pair_metrics(closed_positions)
    if not trades:
        warnings.append("该时间区间没有产生可执行交易信号")

    return BacktestResult(
        symbol=symbol,
        start_date=bars[0].trade_date,
        end_date=bars[-1].trade_date,
        strategy="ma_cross",
        total_return=total_return,
        annual_return=annual_return,
        max_drawdown=_drawdown(values),
        trade_count=len(trades),
        final_equity=final_equity,
        benchmark_return=benchmark_return,
        benchmark_final_equity=benchmark_final_equity,
        excess_return=total_return - benchmark_return,
        win_rate=win_rate,
        profit_loss_ratio=profit_loss_ratio,
        average_holding_days=average_holding_days,
        closed_trade_count=len(closed_positions),
        equity_curve=equity_curve,
        trades=trades,
        warnings=warnings,
    )
