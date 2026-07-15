#!/usr/bin/env python3
"""发布 Skill 生成的 recommendations.json 到本地量化工作台。

示例：
    python scripts/publish_recommendations.py recommendations.json
    python scripts/publish_recommendations.py recommendations.json --api http://127.0.0.1:8765
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from text_io import ensure_text_is_not_garbled, read_json_path, write_stdout_utf8


DEFAULT_API_BASE = "http://127.0.0.1:8765"
WORKBENCH_PATH = "/templates/workbench.html"


def normalize_api_base(api_base: str) -> str:
    return api_base.rstrip("/")


def validate_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ValueError("recommendations.json 顶层必须是对象")
    ensure_text_is_not_garbled(document, "recommendations.json")

    stocks = document.get("stocks")
    if not isinstance(stocks, list) or not stocks:
        raise ValueError("recommendations.json 必须包含至少一只股票 stocks")
    for index, stock in enumerate(stocks, start=1):
        if not isinstance(stock, dict):
            raise ValueError(f"stocks[{index}] 必须是对象")
        code = str(stock.get("code") or "").strip()
        if not (code.isdigit() and len(code) == 6):
            raise ValueError(f"stocks[{index}].code 必须是 6 位数字，例如 000001")
    return document


def publish(document: dict[str, Any], api_base: str, *, timeout: float = 15) -> dict[str, Any]:
    endpoint = f"{normalize_api_base(api_base)}/api/recommendations"
    body = json.dumps(document, ensure_ascii=False).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - 用户指定的本地 API 地址
            raw = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"发布失败：HTTP {exc.code}，{detail}") from exc
    except URLError as exc:
        raise RuntimeError(
            f"无法连接量化后端 {endpoint}。请先在项目根目录运行 "
            r".\scripts\start-docker.ps1，然后重试。"
        ) from exc

    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("量化后端返回的不是有效 UTF-8 JSON") from exc
    if not isinstance(result, dict) or not result.get("session_id"):
        raise RuntimeError("量化后端没有返回推荐会话 session_id")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="把 recommendations.json 发布到本地量化工作台")
    parser.add_argument("recommendations", help="pack_recommendations.py 生成的 recommendations.json")
    parser.add_argument("--api", default=DEFAULT_API_BASE, help=f"量化工作台地址，默认 {DEFAULT_API_BASE}")
    parser.add_argument("--timeout", type=float, default=15, help="HTTP 超时秒数，默认 15")
    parser.add_argument("--dry-run", action="store_true", help="只校验文件，不向后端发布")
    args = parser.parse_args()

    try:
        document = validate_document(read_json_path(args.recommendations, "recommendations.json"))
        if args.dry_run:
            write_stdout_utf8(f"校验通过：{len(document['stocks'])} 只股票，未发布（--dry-run）。\n")
            return 0
        result = publish(document, args.api, timeout=args.timeout)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    base = normalize_api_base(args.api)
    write_stdout_utf8(
        "发布成功。\n"
        f"会话 ID：{result['session_id']}\n"
        f"统一工作台：{base}{WORKBENCH_PATH}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
