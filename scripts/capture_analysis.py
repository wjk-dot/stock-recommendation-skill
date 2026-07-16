#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Capture a-stock-analysis JSON without letting Windows rewrite stdout encoding."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from text_io import decode_text, ensure_text_is_not_garbled, write_utf8


def _repair_latin1_wrapped_gbk(value: object) -> object:
    """Repair Chinese text that an upstream Windows process decoded as Latin-1.

    The upstream analyzer normally emits UTF-8 JSON, but its Sina response can
    contain GBK bytes that are accidentally preserved as Latin-1 characters.
    Those characters are reversible (for example ``Æ½°²ÒøÐÐ`` -> ``平安银行``),
    unlike replacement-character corruption.  Repair them before the document
    reaches the GUI so stock names never render as mojibake.
    """
    if isinstance(value, str):
        try:
            repaired = value.encode("latin-1").decode("gb18030")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value
        # Only accept a round-trip-safe repair.  Normal ASCII and valid Unicode
        # strings therefore remain untouched.
        try:
            return repaired if repaired.encode("gb18030").decode("latin-1") == value else value
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value
    if isinstance(value, list):
        return [_repair_latin1_wrapped_gbk(item) for item in value]
    if isinstance(value, dict):
        return {key: _repair_latin1_wrapped_gbk(item) for key, item in value.items()}
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="以原始字节捕获 a-stock-analysis 的 JSON 输出")
    parser.add_argument("codes", nargs="+", help="股票代码，例如 000001 600000")
    parser.add_argument("--upstream", required=True, help="a-stock-analysis/scripts/analyze.py 路径")
    parser.add_argument("--minute", action="store_true", help="同时采集分时量能分析")
    parser.add_argument("--output", "-o", default="analysis.json", help="UTF-8 输出文件")
    args = parser.parse_args()

    command = [sys.executable, args.upstream, *args.codes, "--json"]
    if args.minute:
        command.append("--minute")

    completed = subprocess.run(command, capture_output=True)
    if completed.stderr:
        sys.stderr.buffer.write(completed.stderr)
    if completed.returncode != 0:
        print(f"上游 a-stock-analysis 执行失败，退出码：{completed.returncode}", file=sys.stderr)
        return completed.returncode or 1

    try:
        text = decode_text(completed.stdout, "a-stock-analysis 输出")
        payload = _repair_latin1_wrapped_gbk(json.loads(text))
        ensure_text_is_not_garbled(payload, "a-stock-analysis 输出")
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"错误：无法安全读取 a-stock-analysis 输出：{exc}", file=sys.stderr)
        return 2

    if not isinstance(payload, list):
        print("错误：a-stock-analysis 输出应当是数组", file=sys.stderr)
        return 2

    output = json.dumps(payload, ensure_ascii=False, indent=2)
    write_utf8(args.output, output)
    print(f"已写入 UTF-8 行情数据：{Path(args.output).resolve()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
