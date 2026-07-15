from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import backtest, health, market_flow, stocks

app = FastAPI(title="Stock Recommendation Quant Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8765",
        "http://localhost:8765",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(health.router, prefix="/api")
app.include_router(stocks.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(market_flow.router, prefix="/api")
