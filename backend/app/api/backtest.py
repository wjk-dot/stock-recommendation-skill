from fastapi import APIRouter, HTTPException

from app.backtest.engine import run_ma_cross
from app.models import BacktestRequest
from app.services import DailyBarUnavailable, get_daily_bars_with_source


router = APIRouter(prefix="/backtests")


@router.post("")
def create_backtest(request: BacktestRequest):
    try:
        bars, data_source, source_warnings = get_daily_bars_with_source(
            request.symbol, request.start_date, request.end_date
        )
        if request.strategy != "ma_cross":
            raise ValueError(f"暂不支持策略: {request.strategy}")
        result = run_ma_cross(
            bars,
            symbol=request.symbol,
            initial_cash=request.initial_cash,
            fast_period=int(request.parameters.get("fast_period", 5)),
            slow_period=int(request.parameters.get("slow_period", 20)),
            fees=request.fees,
        )
        result.data_source = data_source
        result.warnings = [*source_warnings, *result.warnings]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DailyBarUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "market_data_unavailable",
                "message": "历史行情数据源暂不可用，未生成回测结果。",
                "attempted_sources": exc.attempts,
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"code": "backtest_failed", "message": f"回测执行失败: {exc}"}) from exc
    return result.model_dump(mode="json")
