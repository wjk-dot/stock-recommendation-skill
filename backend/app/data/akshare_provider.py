from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Callable

from app.models import MarketFlow


class AkShareProvider:
    """通过 AkShare 适配多个独立上游的市场资金流数据。"""

    def get_market_flow(self) -> MarketFlow:
        try:
            import akshare as ak
        except ImportError as exc:
            raise RuntimeError("未安装 AkShare，无法获取市场资金流向") from exc

        errors: list[str] = []
        loaders: list[tuple[str, Callable[[], MarketFlow]]] = [
            ("同花顺行业资金流", lambda: self._get_ths_industry_flow(ak)),
            ("东方财富板块资金流", lambda: self._get_eastmoney_sector_flow(ak)),
        ]
        for label, loader in loaders:
            try:
                return loader()
            except Exception as exc:
                errors.append(f"{label}: {self._short_error(exc)}")
        raise RuntimeError("；".join(errors))

    def _get_ths_industry_flow(self, ak: Any) -> MarketFlow:
        frame = ak.stock_fund_flow_industry(symbol="即时")
        if frame is None or frame.empty:
            raise RuntimeError("未返回行业资金流数据")

        sectors: list[dict[str, object]] = []
        for row in frame.to_dict("records"):
            name = row.get("行业")
            # AkShare 对该同花顺接口返回的流入、流出和净额单位均为亿元。
            flow = self._number(row.get("净额"), default_multiplier=100_000_000)
            change = self._number(row.get("行业-涨跌幅"))
            if not name or flow is None:
                continue
            sectors.append(
                {
                    "name": str(name),
                    "net_inflow_cny": flow,
                    "change_pct": change or 0,
                }
            )
        selected = self._select_balanced_sectors(sectors)
        if not selected:
            raise RuntimeError("返回字段无法校验")
        return MarketFlow(
            as_of=datetime.now(timezone.utc),
            source="akshare/10jqka",
            scope="同花顺行业资金流（即时）",
            net_inflow_cny=sum(float(item["net_inflow_cny"]) for item in sectors),
            sectors=selected,
            warnings=["金额按同花顺页面口径由亿元换算为人民币元。"],
        )

    def _get_eastmoney_sector_flow(self, ak: Any) -> MarketFlow:
        frame = ak.stock_sector_fund_flow_rank(
            indicator="今日", sector_type="行业资金流"
        )
        if frame is None or frame.empty:
            raise RuntimeError("未返回板块资金流数据")

        sectors: list[dict[str, object]] = []
        for row in frame.to_dict("records"):
            name = row.get("名称") or row.get("板块") or row.get("name")
            flow = self._number(
                row.get("今日主力净流入-净额", row.get("主力净流入"))
            )
            change = self._number(row.get("今日涨跌幅", row.get("涨跌幅")))
            if not name or flow is None:
                continue
            sectors.append(
                {
                    "name": str(name),
                    "net_inflow_cny": flow,
                    "change_pct": change or 0,
                }
            )
        selected = self._select_balanced_sectors(sectors)
        if not selected:
            raise RuntimeError("返回字段无法校验")
        return MarketFlow(
            as_of=datetime.now(timezone.utc),
            source="akshare/eastmoney",
            scope="东方财富行业主力资金流（今日）",
            sectors=selected,
        )

    @staticmethod
    def _select_balanced_sectors(
        sectors: list[dict[str, object]], limit_each_side: int = 5
    ) -> list[dict[str, object]]:
        inflows = sorted(
            (item for item in sectors if float(item["net_inflow_cny"]) >= 0),
            key=lambda item: float(item["net_inflow_cny"]),
            reverse=True,
        )[:limit_each_side]
        outflows = sorted(
            (item for item in sectors if float(item["net_inflow_cny"]) < 0),
            key=lambda item: float(item["net_inflow_cny"]),
        )[:limit_each_side]
        selected = inflows + outflows
        for rank, item in enumerate(selected, start=1):
            item["rank"] = rank
        return selected

    @staticmethod
    def _number(value: object, default_multiplier: float = 1) -> float | None:
        if value is None:
            return None
        multiplier = default_multiplier
        text = str(value).strip().replace(",", "").replace("%", "")
        unit_multipliers = {"亿元": 100_000_000, "亿": 100_000_000, "万元": 10_000, "万": 10_000, "元": 1}
        for unit, unit_multiplier in unit_multipliers.items():
            if text.endswith(unit):
                text = text[: -len(unit)].strip()
                multiplier = unit_multiplier
                break
        try:
            number = float(text) * multiplier
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @staticmethod
    def _short_error(exc: Exception) -> str:
        text = " ".join(str(exc).split())
        return text[:180] or exc.__class__.__name__
