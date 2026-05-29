"""Unified CLI output formatting."""

import json
import sys
from typing import Any, Literal, Optional

OutputFormat = Literal["json", "text"]


def api_result(
    status: str,
    data: Any = None,
    msg: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {"status": status, "data": data, "msg": msg}
    result.update(extra)
    return result


def emit_result(
    data: dict[str, Any],
    fmt: OutputFormat,
    output_path: Optional[str] = None,
) -> None:
    if fmt == "json":
        text = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        text = _format_text(data)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
            if not text.endswith("\n"):
                f.write("\n")
    else:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")


def _format_text(data: dict[str, Any]) -> str:
    lines = [f"status: {data.get('status')}"]
    if data.get("msg"):
        lines.append(f"msg: {data.get('msg')}")
    payload = data.get("data")
    if payload is not None:
        lines.append("data:")
        if isinstance(payload, (dict, list)):
            lines.append(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            lines.append(f"  {payload}")
    for key, value in data.items():
        if key in ("status", "data", "msg"):
            continue
        if value is not None:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)
