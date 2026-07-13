"""JSON text I/O helpers for Windows and mixed-encoding upstream output."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# These markers mean that the original Chinese characters were already lost
# during an earlier decode. They cannot be recovered reliably downstream.
GARBLED_MARKERS = ("\ufffd", "锟斤拷", "ï¿½", "Ã", "Â")


def decode_text(data: bytes, source: str = "输入") -> str:
    """Decode text emitted by Python, PowerShell, or a GBK market API."""
    encodings: list[str]
    if data.startswith(b"\xef\xbb\xbf"):
        encodings = ["utf-8-sig", "utf-8", "gb18030", "utf-16"]
    elif data.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings = ["utf-16", "utf-8-sig", "gb18030"]
    else:
        encodings = ["utf-8", "gb18030", "utf-16"]

    errors: list[str] = []
    for encoding in encodings:
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
            continue
        if "\x00" in text:
            errors.append(f"{encoding}: 含有 NUL 字符")
            continue
        return text

    detail = "; ".join(errors)
    raise ValueError(f"无法按 UTF-8/GB18030 读取{source}，请检查文件编码。{detail}")


def load_json_bytes(data: bytes, source: str = "输入") -> Any:
    """Decode raw bytes and parse JSON without a shell text conversion."""
    try:
        text = decode_text(data, source)
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source}不是有效 JSON：第 {exc.lineno} 行第 {exc.colno} 列附近解析失败") from exc


def read_json_path(path: str | Path, label: str | None = None) -> Any:
    path = Path(path)
    return load_json_bytes(path.read_bytes(), label or str(path))


def read_json_stdin(label: str = "标准输入") -> Any:
    return load_json_bytes(sys.stdin.buffer.read(), label)


def write_utf8(path: str | Path, text: str) -> None:
    Path(path).write_bytes(text.encode("utf-8"))


def write_stdout_utf8(text: str) -> None:
    sys.stdout.buffer.write(text.encode("utf-8"))


def _find_garbled(value: Any, path: str = "$", found: list[str] | None = None) -> list[str]:
    found = found if found is not None else []
    if isinstance(value, str):
        if any(marker in value for marker in GARBLED_MARKERS):
            found.append(path)
    elif isinstance(value, dict):
        for key, item in value.items():
            _find_garbled(item, f"{path}.{key}", found)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _find_garbled(item, f"{path}[{index}]", found)
    return found


def ensure_text_is_not_garbled(value: Any, label: str = "输入 JSON") -> None:
    """Stop before rendering when a previous decode permanently lost text."""
    paths = _find_garbled(value)
    if paths:
        shown = ", ".join(paths[:5])
        more = "等" if len(paths) > 5 else ""
        raise ValueError(
            f"{label}含有不可恢复的乱码（字段：{shown}{more}）。"
            "请从 a-stock-analysis 重新采集，并确保以 UTF-8 写入文件；"
            "不要使用会转换编码的 PowerShell 文本重定向。"
        )
