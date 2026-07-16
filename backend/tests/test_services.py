from datetime import date

from app.models import DailyBar
from app import services


def bar(day: date) -> DailyBar:
    return DailyBar(
        symbol="000001", trade_date=day, open=10, high=11, low=9,
        close=10, volume=1000, amount=10000,
    )


def test_cache_accepts_boundary_holidays_without_network(monkeypatch):
    cached = [bar(date(2020, 1, 2)), bar(date(2026, 7, 15))]
    monkeypatch.setattr(services.repository, "get", lambda *_: cached)

    result, source, warnings = services.get_daily_bars_with_source(
        "000001", date(2020, 1, 1), date(2026, 7, 15)
    )

    assert result == cached
    assert source == "cache"
    assert warnings


def test_falls_back_to_akshare_and_saves_result(monkeypatch):
    fetched = [bar(date(2024, 1, 2)), bar(date(2024, 1, 3))]
    calls: list[str] = []

    monkeypatch.setattr(services.repository, "get", lambda *_: [])
    monkeypatch.setattr(services.repository, "upsert", lambda bars: calls.append(f"saved:{len(bars)}"))
    monkeypatch.setattr(
        services.provider, "get_daily_bars", lambda *_: (_ for _ in ()).throw(OSError("socket failed"))
    )
    monkeypatch.setattr(services.fallback_daily_provider, "get_daily_bars", lambda *_: fetched)

    result, source, warnings = services.get_daily_bars_with_source(
        "000001", date(2024, 1, 2), date(2024, 1, 3)
    )

    assert result == fetched
    assert source == "akshare"
    assert calls == ["saved:2"]
    assert "自动切换" in warnings[0]
