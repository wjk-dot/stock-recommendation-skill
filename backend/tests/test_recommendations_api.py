from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import recommendations
from app.data.recommendation_repository import RecommendationRepository
from app.main import app


def recommendation_payload() -> dict:
    return {
        "meta": {
            "title": "测试推荐",
            "generated_at": "2026-07-15T15:00:00",
            "market_status": "closed",
        },
        "user_profile": {
            "capital_cny": 10000,
            "fees": {
                "commission_rate": 0.0003,
                "min_commission_cny": 5,
                "stamp_duty_rate": 0.0005,
                "transfer_rate": 0.00001,
            },
            "markets": ["sh_main", "sz_main"],
            "horizon": "short",
            "risk_level": "balanced",
            "confirmed": True,
        },
        "stocks": [
            {
                "code": "000001",
                "name": "平安银行",
                "price": 10.5,
                "change_pct": 1.2,
                "recommendation": "buy",
                "confidence": 0.75,
                "sector": "银行",
                "reasons": ["测试理由"],
                "risk_factors": ["测试风险"],
            }
        ],
        "market_overview": {},
    }


def test_recommendation_session_create_and_read_latest(tmp_path, monkeypatch):
    monkeypatch.setattr(recommendations, "repository", RecommendationRepository(tmp_path))
    client = TestClient(app)

    created = client.post("/api/recommendations", json=recommendation_payload())

    assert created.status_code == 200
    body = created.json()
    assert body["session_id"].startswith("rec_")
    assert body["created_at"]
    assert body["stocks"][0]["name"] == "平安银行"

    latest = client.get("/api/recommendations/latest")
    assert latest.status_code == 200
    assert latest.json()["session_id"] == body["session_id"]
    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / f"{body['session_id']}.json").exists()


def test_recommendation_session_returns_structured_missing_error(tmp_path, monkeypatch):
    monkeypatch.setattr(recommendations, "repository", RecommendationRepository(tmp_path))

    response = TestClient(app).get("/api/recommendations/latest")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "recommendation_session_missing"


def test_recommendation_session_rejects_invalid_stock_code(tmp_path, monkeypatch):
    monkeypatch.setattr(recommendations, "repository", RecommendationRepository(tmp_path))
    payload = recommendation_payload()
    payload["stocks"][0]["code"] = "not-a-share"

    response = TestClient(app).post("/api/recommendations", json=payload)

    assert response.status_code == 422
    assert "6 位数字 code" in response.json()["detail"][0]["msg"]
