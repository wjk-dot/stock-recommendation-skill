from fastapi import APIRouter, Query

from app.services import get_market_flow

router = APIRouter()


@router.get("/market-flow")
def market_flow(refresh: bool = Query(False)):
    return get_market_flow(force_refresh=refresh).model_dump(mode="json")
