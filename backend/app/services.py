from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.config import DATA_DIR, DB_PATH
from app.data.akshare_daily_provider import AkShareDailyProvider
from app.data.akshare_provider import AkShareProvider
from app.data.baostock_provider import BaostockProvider
from app.data.repository import BarRepository
from app.models import DailyBar, MarketFlow


repository = BarRepository(DB_PATH)
provider = BaostockProvider()
fallback_daily_provider = AkShareDailyProvider()
market_flow_provider = AkShareProvider()
market_flow_cache_path = DATA_DIR / "market-flow-cache.json"
market_flow_cache_ttl = timedelta(minutes=5)
_market_flow_cache: MarketFlow | None = None


class DailyBarUnavailable(RuntimeError):
    def __init__(self, symbol: str, attempts: list[str]):
        self.symbol = symbol
        self.attempts = attempts
        super().__init__("；".join(attempts) or "没有可用的数据源")


def get_daily_bars(symbol: str, start: date, end: date) -> list[DailyBar]:
    bars, _, _ = get_daily_bars_with_source(symbol, start, end)
    return bars


def get_daily_bars_with_source(symbol: str, start: date, end: date) -> tuple[list[DailyBar], str, list[str]]:
    """返回日线、数据来源和告警；缓存优先，外部源失败不会掩盖已有缓存。"""
    cached = repository.get(symbol, start, end)
    if _cache_covers_request(cached, start, end):
        return cached, "cache", ["使用本地行情缓存；数据按请求股票和日期范围保存。"]

    attempts: list[str] = []
    for source_name, source in (("baostock", provider), ("akshare", fallback_daily_provider)):
        try:
            fetched = source.get_daily_bars(symbol, start, end)
            if not fetched:
                attempts.append(f"{source_name}: 未返回该日期范围内的日线")
                continue
            repository.upsert(fetched)
            merged = repository.get(symbol, start, end)
            result = merged or fetched
            warnings = []
            if source_name != "baostock":
                warnings.append("Baostock 不可用，已自动切换至 AkShare。")
            if _cache_covers_request(result, start, end):
                return result, source_name, warnings
            # 交易所休市日会让首尾日期不完全一致；只要有日线就不能把有效数据丢掉。
            return result, source_name, [*warnings, "请求区间包含休市日，已返回可取得的交易日数据。"]
        except Exception as exc:
            attempts.append(f"{source_name}: {_short_error(exc)}")

    if cached:
        return cached, "cache-stale", [
            "实时数据源暂不可用，已回退到本地缓存；请核对缓存覆盖日期。",
            *attempts,
        ]
    raise DailyBarUnavailable(symbol, attempts)


def _cache_covers_request(bars: list[DailyBar], start: date, end: date) -> bool:
    """允许首尾最多相差 7 天，避免周末/节假日被误判为缓存不完整。"""
    if not bars:
        return False
    return bars[0].trade_date <= start + timedelta(days=7) and bars[-1].trade_date >= end - timedelta(days=7)


def _short_error(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    return text[:180] or exc.__class__.__name__


def get_market_flow(force_refresh: bool = False) -> MarketFlow:
    global _market_flow_cache

    cached = _market_flow_cache or _read_market_flow_cache()
    if cached and not force_refresh and _is_fresh(cached):
        _market_flow_cache = cached
        return cached
    try:
        result = market_flow_provider.get_market_flow()
        _market_flow_cache = result
        _write_market_flow_cache(result)
        return result
    except Exception as exc:
        if cached:
            stale = cached.model_copy(deep=True)
            stale.warnings.append(
                f"实时刷新失败，当前展示 {cached.as_of.isoformat()} 的最近成功快照: {exc}"
            )
            return stale
        return MarketFlow(
            as_of=datetime.now(timezone.utc),
            source="unavailable",
            scope="沪深 A 股",
            warnings=[f"全市场资金流向暂不可用: {exc}"],
        )


def _is_fresh(flow: MarketFlow) -> bool:
    as_of = flow.as_of
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - as_of <= market_flow_cache_ttl


def _read_market_flow_cache() -> MarketFlow | None:
    try:
        return MarketFlow.model_validate_json(market_flow_cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_market_flow_cache(flow: MarketFlow) -> None:
    temp_path = market_flow_cache_path.with_suffix(".tmp")
    try:
        temp_path.write_text(flow.model_dump_json(), encoding="utf-8")
        temp_path.replace(market_flow_cache_path)
    except OSError:
        temp_path.unlink(missing_ok=True)
