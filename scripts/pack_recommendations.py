#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
pack_recommendations.py

把 a-stock-analysis skill 的 --json 输出 + Codex 的人工标注，打包成本 skill 期望的输入 JSON。

用法：
    uv run pack_recommendations.py \
        --analysis path/to/a_stock_analysis_output.json \
        --annotations path/to/codex_annotations.json \
        --output recommendations.json

或者直接走 stdin：
    uv run analyze.py 600789 002446 --json --minute \
      | uv run pack_recommendations.py --annotations annotations.json

annotations.json 的结构（Codex 写）：
{
  "600789": {
    "recommendation": "buy",            // 必填
    "confidence": 0.78,                 // 0~1
    "sector": "医药",
    "reasons": [
      "早盘主力抢筹明显，30 分钟成交量占比 41.6%",
      "分时图稳步上行，无明显出货迹象"
    ],
    "risk_factors": [
      "尾盘放量 10.3%，需警惕次日获利回吐"
    ]
  },
  "002446": { ... }
}

未在 annotations 里出现的股票，GUI 会用中性标签（watch）渲染，仍展示行情但不写推荐理由。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


A_SHARE_SECTORS_HINT = {
    "医药": ["医药", "生物", "制药", "鲁抗", "白云山", "恒瑞"],
}


def _infer_sector(name: str, code: str) -> str:
    """极简的行业推断兜底；Codex 应在 annotations 里显式覆盖。"""
    for sector, kws in A_SHARE_SECTORS_HINT.items():
        for kw in kws:
            if kw in name:
                return sector
    if code.startswith("300"):
        return "创业板"
    if code.startswith("688"):
        return "科创板"
    return ""


def _normalize_one(stock: dict[str, Any], annotation: dict[str, Any] | None) -> dict[str, Any]:
    """把 a-stock-analysis 单只股票的输出 + 标注，合并成一个 stock dict。"""
    rt = stock.get("realtime", {}) or {}
    minute = stock.get("minute_analysis", {}) or {}
    ann = annotation or {}

    price = rt.get("price")
    pre_close = rt.get("pre_close")
    change_pct = rt.get("change_pct")
    if change_pct is None and price and pre_close:
        change_pct = round((price - pre_close) / pre_close * 100, 2)

    volume_lots = rt.get("volume")
    amount_cny = rt.get("amount")
    change_amt = rt.get("change_amt")
    if change_amt is None and price and pre_close:
        change_amt = round(price - pre_close, 2)

    distribution = (minute.get("distribution") or {}) if minute else {}
    vd = {
        "open_30min": (distribution.get("open_30min") or {}).get("percent"),
        "mid_am": (distribution.get("mid_am") or {}).get("percent"),
        "mid_pm": (distribution.get("mid_pm") or {}).get("percent"),
        "close_30min": (distribution.get("close_30min") or {}).get("percent"),
    }
    # 过滤掉 None，保留可用的
    vd = {k: v for k, v in vd.items() if v is not None}

    top_volumes = minute.get("top_volumes") or []

    code = stock.get("code") or rt.get("code")
    name = stock.get("name") or rt.get("name") or code

    merged: dict[str, Any] = {
        "code": code,
        "name": name,
        "price": price,
        "open": rt.get("open"),
        "pre_close": pre_close,
        "high": rt.get("high"),
        "low": rt.get("low"),
        "volume_lots": volume_lots,
        "amount_cny": amount_cny,
        "change_pct": change_pct,
        "change_amt": change_amt,
        "recommendation": ann.get("recommendation", "watch"),
        "confidence": ann.get("confidence", 0.5),
        "sector": ann.get("sector") or _infer_sector(name or "", code or ""),
        "reasons": ann.get("reasons") or ann.get("reason") or [
            (minute.get("signals") or ["暂无主动标注"])[0]
            if minute.get("signals")
            else "暂无主动标注，Codex 未给出理由"
        ],
        "risk_factors": ann.get("risk_factors") or [],
    }

    if vd:
        merged["volume_distribution"] = vd
    if top_volumes:
        merged["top_volumes"] = top_volumes
    signals = minute.get("signals") or []
    if signals:
        merged["signals"] = signals

    return merged


def _infer_market_status() -> str:
    """根据 Asia/Shanghai 当前时间粗略判断市场状态。仅用于顶部状态灯。"""
    now = _dt.datetime.now()
    if now.weekday() >= 5:
        return "closed"
    t = now.time()
    if _dt.time(9, 15) <= t <= _dt.time(11, 35):
        return "open"
    if _dt.time(13, 0) <= t <= _dt.time(15, 5):
        return "open"
    if _dt.time(9, 0) <= t < _dt.time(9, 15):
        return "pre_market"
    return "closed"


def pack(analysis_payload: list[dict[str, Any]], annotations: dict[str, Any], title: str | None = None) -> dict[str, Any]:
    stocks: list[dict[str, Any]] = []
    for raw in analysis_payload:
        if "error" in raw:
            continue
        code = raw.get("code") or (raw.get("realtime") or {}).get("code")
        ann = annotations.get(code) or annotations.get(str(code)) if code else None
        stocks.append(_normalize_one(raw, ann))

    return {
        "meta": {
            "title": title or "Codex 量化推荐控制台",
            "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "analyst": "Codex",
            "market_status": _infer_market_status(),
        },
        "stocks": stocks,
    }


def _load_json_from_arg(arg: str | None, stdin_label: str) -> Any:
    if arg is None or arg == "-":
        data = sys.stdin.read()
    else:
        data = Path(arg).read_text(encoding="utf-8-sig")
    return json.loads(data)


def main() -> int:
    parser = argparse.ArgumentParser(description="把 a-stock-analysis 输出 + 标注打包成 GUI 输入 JSON")
    parser.add_argument("--analysis", "-a", help="a-stock-analysis --json 的输出文件，- 表示 stdin")
    parser.add_argument("--annotations", "-n", required=True, help="Codex 标注 JSON 文件")
    parser.add_argument("--output", "-o", default="-", help="输出文件，- 表示 stdout")
    parser.add_argument("--title", "-t", default=None, help="覆盖默认页面标题")
    args = parser.parse_args()

    if not args.analysis:
        # 默认从 stdin 读
        args.analysis = "-"

    analysis_payload = _load_json_from_arg(args.analysis, "analysis")
    if not isinstance(analysis_payload, list):
        print("错误: a-stock-analysis --json 输出应当是数组", file=sys.stderr)
        return 2

    annotations_doc = _load_json_from_arg(args.annotations, "annotations")
    if not isinstance(annotations_doc, dict):
        print("错误: annotations 应当是 {股票代码: {...}} 形式", file=sys.stderr)
        return 2

    packed = pack(analysis_payload, annotations_doc, title=args.title)
    out = json.dumps(packed, ensure_ascii=False, indent=2)
    if args.output == "-":
        sys.stdout.write(out)
    else:
        Path(args.output).write_text(out, encoding="utf-8-sig")
        print(f"已写入: {args.output} ({len(packed['stocks'])} 只股票)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
