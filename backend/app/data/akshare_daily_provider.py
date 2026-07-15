from __future__ import annotations

import math
from datetime import date

from app.models import DailyBar


class AkShareDailyProvider:
    """按需拉取单只 A 股日线，作为 Baostock 不可用时的备用数据源。"""

    def get_daily_bars(self, symbol: str, start: date, end: date) -> list[DailyBar]:
        try:
            import akshare as ak
        except ImportError as exc:
            raise RuntimeError("未安装 AkShare") from exc

        code = symbol.split(".")[-1].strip()
        if not code.isdigit() or len(code) != 6:
            raise ValueError("股票代码必须是 6 位数字，例如 000001")

        frame = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
        if frame is None or frame.empty:
            return []

        required = {"日期", "开盘", "最高", "最低", "收盘"}
        missing = required.difference(frame.columns)
        if missing:
            raise RuntimeError(f"AkShare 返回字段不完整: {', '.join(sorted(missing))}")

        bars: list[DailyBar] = []
        for row in frame.to_dict("records"):
            try:
                trade_date = self._to_date(row["日期"])
                open_price = self._to_number(row["开盘"])
                high = self._to_number(row["最高"])
                low = self._to_number(row["最低"])
                close = self._to_number(row["收盘"])
                volume = self._to_number(row.get("成交量", 0), allow_empty=True)
                amount = self._to_number(row.get("成交额", 0), allow_empty=True)
            except (TypeError, ValueError) as exc:
                raise RuntimeError(f"AkShare 行情字段无法解析: {exc}") from exc
            bars.append(
                DailyBar(
                    symbol=symbol,
                    trade_date=trade_date,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                    amount=amount,
                )
            )
        return bars

    @staticmethod
    def _to_date(value: object) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])

    @staticmethod
    def _to_number(value: object, *, allow_empty: bool = False) -> float:
        if value is None and allow_empty:
            return 0.0
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("数值不是有限数")
        return number
