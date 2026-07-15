from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.services import DailyBarUnavailable, get_daily_bars_with_source


router = APIRouter(prefix="/stocks")


@router.get("/{symbol}/daily")
def daily_bars(
    symbol: str,
    start: date = Query(...),
    end: date = Query(...),
    adjust: str = "前复权",
):
    if start > end:
        raise HTTPException(status_code=400, detail="开始日期必须早于或等于结束日期")
    try:
        bars, data_source, warnings = get_daily_bars_with_source(symbol, start, end)
    except DailyBarUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "market_data_unavailable",
                "message": "行情数据源暂不可用。",
                "attempted_sources": exc.attempts,
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"行情数据获取失败: {exc}") from exc
    if not bars:
        raise HTTPException(status_code=404, detail="指定区间没有行情数据")
    return {
        "symbol": symbol,
        "adjust": adjust,
        "data_source": data_source,
        "warnings": warnings,
        "bars": [bar.model_dump(mode="json") for bar in bars],
    }
