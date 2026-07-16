from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "publish_recommendations.py"


@pytest.fixture(scope="module")
def publisher_module():
    scripts_dir = str(SCRIPT_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("publish_recommendations", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_document() -> dict:
    return {
        "meta": {"title": "测试推荐"},
        "user_profile": {"capital_cny": 1000},
        "stocks": [{"code": "000001", "name": "平安银行", "price": 10.5}],
    }


def test_publisher_validates_document(publisher_module):
    document = publisher_module.validate_document(valid_document())
    assert document["stocks"][0]["name"] == "平安银行"


def test_publisher_rejects_invalid_stock_code(publisher_module):
    document = valid_document()
    document["stocks"][0]["code"] = "123"

    with pytest.raises(ValueError, match="6 位数字"):
        publisher_module.validate_document(document)


def test_publisher_uses_utf8_json_body(monkeypatch, publisher_module):
    captured: dict[str, object] = {}

    class FakeResponse:
        def read(self):
            return json.dumps({"session_id": "rec_test"}, ensure_ascii=False).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["data"] = request.data
        captured["content_type"] = request.headers["Content-type"]
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(publisher_module, "urlopen", fake_urlopen)
    result = publisher_module.publish(valid_document(), "http://127.0.0.1:8765/")

    assert result["session_id"] == "rec_test"
    assert captured["url"] == "http://127.0.0.1:8765/api/recommendations"
    assert "平安银行" in captured["data"].decode("utf-8")
    assert captured["content_type"] == "application/json; charset=utf-8"
