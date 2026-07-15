from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("STOCK_DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "market.duckdb"
RECOMMENDATION_DIR = DATA_DIR / "recommendations"

DATA_DIR.mkdir(parents=True, exist_ok=True)
RECOMMENDATION_DIR.mkdir(parents=True, exist_ok=True)
