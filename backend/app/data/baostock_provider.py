from __future__ import annotations

from datetime import date

from app.models import DailyBar


class BaostockProvider:
    """按需拉取历史日线；生产环境应在此层增加限流、重试和本地同步任务。"""

    def get_daily_bars(self, symbol: str, start: date, end: date) -> list[DailyBar]:
        import baostock as bs

        code = symbol if "." in symbol else (f"sh.{symbol}" if symbol.startswith("6") else f"sz.{symbol}")
        login = bs.login()
        if login.error_code != "0":
            raise RuntimeError(f"Baostock 登录失败: {login.error_msg}")
        try:
            result = bs.query_history_k_data_plus(
                code,
                "date,open,high,low,close,volume,amount,adjustflag",
                start_date=start.isoformat(),
                end_date=end.isoformat(),
                frequency="d",
                adjustflag="2",
            )
            if result.error_code != "0":
                raise RuntimeError(f"Baostock 查询失败: {result.error_msg}")
            bars: list[DailyBar] = []
            while result.next():
                row = dict(zip(result.fields, result.get_row_data()))
                bars.append(
                    DailyBar(
                        symbol=symbol,
                        trade_date=date.fromisoformat(row["date"]),
                        open=float(row["open"]), high=float(row["high"]),
                        low=float(row["low"]), close=float(row["close"]),
                        volume=float(row["volume"] or 0), amount=float(row["amount"] or 0),
                        adjust_factor=float(row["adjustflag"] or 0),
                    )
                )
            return bars
        finally:
            bs.logout()
