#!/usr/bin/env python3
"""从已采集的 a-stock-analysis JSON 生成一份可验收的 UTF-8 推荐会话。

这是开发/验收工具，不参与正式荐股决策。正式调用仍应由 Codex 根据实时
a-stock-analysis 输出填写 annotations，再依次调用 pack_recommendations.py 和
render_gui.py。所有文本均由 Python 以 UTF-8 写入，禁止 PowerShell 重定向中文。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from text_io import read_json_path, write_utf8


PROFILE = {
    "capital_cny": 10000,
    "only_recommendations": False,
    "fees": {
        "commission_rate": 0.0005,
        "min_commission_cny": 5,
        "stamp_duty_rate": 0.0005,
        "transfer_rate": 0.00001,
    },
    "markets": ["sh_main", "sz_main"],
    "horizon": "short",
    "risk_level": "aggressive",
    "confirmed": True,
}


ANNOTATIONS = {
    "600050": {
        "recommendation": "buy",
        "confidence": 0.70,
        "sector": "通信服务",
        "reasons": [
            "收盘 4.28 元、当日上涨 0.23%；早盘成交量占比 33.1%，尾盘占比 25.5%，成交仍保持活跃。",
            "总成交额约 6.30 亿元；以 10,000 元账户按 2,300 股估算，买入总支出约 9,849.02 元，仍保留少量现金。",
        ],
        "risk_factors": [
            "当日涨幅较小，短线突破需要次日量价确认；不要把当日分时信号当作确定性结论。",
            "模拟交易不连接券商，实际成交价格、滑点和费用可能不同。",
        ],
    },
    "601138": {
        "recommendation": "watch",
        "confidence": 0.63,
        "sector": "消费电子制造",
        "reasons": [
            "收盘 63.02 元、当日下跌 0.94%；早盘量能集中，但盘中波动区间较大，先放入观察池。",
            "单手成本约 6,307.06 元（按本次费率），10,000 元账户只适合小仓位验证，不宜用满仓追逐波动。",
        ],
        "risk_factors": [
            "当日收跌且振幅较大，若次日不能收复关键价位，短线趋势可能继续走弱。",
            "高价股单手占用资金较多，仓位管理弹性较低。",
        ],
    },
    "002475": {
        "recommendation": "strong_buy",
        "confidence": 0.76,
        "sector": "消费电子",
        "reasons": [
            "收盘 61.58 元、当日上涨 1.84%，最高触及 64.34 元；开盘后 30 分钟成交量占比 39.8%，早盘量能明显。",
            "成交额约 82.86 亿元，流动性充足；但 10,000 元账户最多只能以 100 股为一手进行小仓位模拟。",
        ],
        "risk_factors": [
            "日内从 60.00 元到 64.34 元波动较大，追高后可能面临回撤。",
            "强信号只描述本次数据快照，不构成收益保证；请设置止损并控制仓位。",
        ],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 UTF-8 推荐会话验收数据")
    parser.add_argument("--analysis", default="analysis-20260716.json")
    parser.add_argument("--annotations", default="annotations-20260716-utf8.json")
    parser.add_argument("--profile", default="profile-20260716-utf8.json")
    args = parser.parse_args()

    analysis = read_json_path(args.analysis, "a-stock-analysis 输出")
    wanted = set(ANNOTATIONS)
    shortlisted = [item for item in analysis if item.get("code") in wanted]
    if set(item.get("code") for item in shortlisted) != wanted:
        raise ValueError("analysis 中缺少本次验收的推荐股票，需重新采集真实快照")

    write_utf8(args.annotations, json.dumps(ANNOTATIONS, ensure_ascii=False, indent=2))
    write_utf8(args.profile, json.dumps(PROFILE, ensure_ascii=False, indent=2))
    write_utf8("analysis-20260716-shortlist.json", json.dumps(shortlisted, ensure_ascii=False, indent=2))
    print("已写入 UTF-8 标注、画像与真实行情子集。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
