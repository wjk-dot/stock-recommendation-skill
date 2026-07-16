from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import backtest, health, market_flow, recommendations, stocks

app = FastAPI(title="Stock Recommendation Quant Backend", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8765",
        "http://localhost:8765",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        # `render_gui.py` also supports directly opening dashboard.html.  A
        # local file has the opaque browser origin "null", so allow only this
        # development case for the loopback-only Docker backend.
        "null",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(health.router, prefix="/api")
app.include_router(stocks.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(market_flow.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
