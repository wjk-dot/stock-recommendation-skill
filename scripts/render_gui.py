#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
#
# [tool.ruff]
# line-length = 100
#
# /// script
"""
render_gui.py

把 Codex 的推荐 JSON 渲染成自包含的交互式 HTML GUI。

用法：
    uv run render_gui.py recommendations.json --output dashboard.html
    uv run render_gui.py recommendations.json        # 默认输出 dashboard.html

输入 JSON 结构见 references/data-schema.md。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

from text_io import ensure_text_is_not_garbled, read_json_path, read_json_stdin, write_utf8


SKILL_ROOT = Path(__file__).resolve().parent.parent
# VANTA 是正式产品界面；dashboard.html 保留为第一代兼容模板。
TEMPLATE_PATH = SKILL_ROOT / "templates" / "orbit-3d-web.html"

DEFAULT_META = {
    "title": "Codex 量化推荐控制台",
    "subtitle": "",
    "generated_at": "",
    "analyst": "Codex",
    "market_status": "closed",
}

DEFAULT_PROFILE = {
    "capital_cny": 100000,
    "only_recommendations": False,
    "fees": {
        "commission_rate": 0.0003,
        "min_commission_cny": 5,
        "stamp_duty_rate": 0.0005,
        "transfer_rate": 0.00001,
    },
    "markets": ["sh_main", "sz_main"],
    "horizon": "swing",
    "risk_level": "balanced",
    "confirmed": False,
}


def _coerce_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(DEFAULT_PROFILE)
    out["fees"] = dict(DEFAULT_PROFILE["fees"])
    if profile:
        for key in ("capital_cny", "only_recommendations", "markets", "horizon", "risk_level", "confirmed"):
            if key in profile and profile[key] is not None:
                out[key] = profile[key]
        if isinstance(profile.get("fees"), dict):
            for key in out["fees"]:
                if profile["fees"].get(key) is not None:
                    out["fees"][key] = profile["fees"][key]
    return out


def _coerce_meta(meta: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(DEFAULT_META)
    if meta:
        for k, v in meta.items():
            if v is not None and v != "":
                out[k] = v
    if not out.get("generated_at"):
        out["generated_at"] = _dt.datetime.now().isoformat(timespec="seconds")
    return out


def _normalize_stock(s: dict[str, Any]) -> dict[str, Any]:
    """保证 stock 渲染所需字段都存在，缺失项用 None 兜底。"""
    out = {
        "code": s.get("code") or "",
        "name": s.get("name") or "",
        "price": s.get("price"),
        "open": s.get("open"),
        "pre_close": s.get("pre_close"),
        "high": s.get("high"),
        "low": s.get("low"),
        "volume_lots": s.get("volume_lots"),
        "amount_cny": s.get("amount_cny"),
        "change_pct": s.get("change_pct"),
        "change_amt": s.get("change_amt"),
        "recommendation": s.get("recommendation") or "watch",
        "confidence": s.get("confidence"),
        "sector": s.get("sector") or "",
        "reasons": s.get("reasons") or [],
        "risk_factors": s.get("risk_factors") or [],
    }
    vd = s.get("volume_distribution") or {}
    if vd:
        out["volume_distribution"] = vd
    tv = s.get("top_volumes") or []
    if tv:
        out["top_volumes"] = tv
    sig = s.get("signals") or []
    if sig:
        out["signals"] = sig
    return out


def render(input_json: dict[str, Any], template_html: str) -> str:
    ensure_text_is_not_garbled(input_json, "推荐 JSON")
    if "stocks" not in input_json or not isinstance(input_json["stocks"], list):
        raise ValueError("输入 JSON 缺少 stocks 数组")

    meta = _coerce_meta(input_json.get("meta"))
    user_profile = _coerce_profile(input_json.get("user_profile"))
    stocks = [_normalize_stock(s) for s in input_json["stocks"]]
    market_overview = input_json.get("market_overview") or {}

    payload = {
        "meta": meta,
        "user_profile": user_profile,
        "stocks": stocks,
        "market_overview": market_overview,
    }
    data_json = json.dumps(payload, ensure_ascii=False, indent=2)

    return template_html.replace("__DATA_JSON__", data_json)


def main() -> int:
    parser = argparse.ArgumentParser(description="把推荐 JSON 渲染成交互式 HTML GUI")
    parser.add_argument("input", help="输入 JSON 文件路径（- 表示 stdin）")
    parser.add_argument("--output", "-o", default="dashboard.html", help="输出 HTML 文件路径")
    parser.add_argument(
        "--template",
        default=str(TEMPLATE_PATH),
        help=f"HTML 模板路径，默认 {TEMPLATE_PATH}",
    )
    args = parser.parse_args()

    if args.input == "-":
        data = read_json_stdin("推荐 JSON")
    else:
        data = read_json_path(args.input, "推荐 JSON")

    template = Path(args.template).read_text(encoding="utf-8-sig")

    html = render(data, template)

    out_path = Path(args.output).resolve()
    write_utf8(out_path, html)
    print(f"GUI 已生成: {out_path}", file=sys.stderr)
    print(f"打开方式: 在资源管理器双击，或 file:///{out_path.as_posix().lstrip('/')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
