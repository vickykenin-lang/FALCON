#!/usr/bin/env python3
"""Send a bounded Falcon task result to Telegram without exposing credentials."""
import argparse
import json
import os
from pathlib import Path
from interface.telegram import TelegramClient


def _load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {"status": "FAILED", "reason": "result_not_available"}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"status": "FAILED", "reason": "invalid_result"}
    except Exception:
        return {"status": "FAILED", "reason": "invalid_result"}


def _clip(value, limit: int = 700) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _format_mission(result: dict) -> str:
    status = str(result.get("status", "UNKNOWN"))
    mission_id = str(result.get("mission_id", "unknown"))
    attempts = int(result.get("attempts", 0) or 0)
    lines = [f"FALCON mission {mission_id}", f"Status: {status}", f"Attempts: {attempts}"]
    reason = _clip(result.get("reason"), 500)
    if reason:
        lines.append(f"Reason: {reason}")
    summary = _clip(result.get("plan_summary"), 900)
    if summary:
        lines.append(f"Summary: {summary}")
    actions = result.get("actions") or []
    if isinstance(actions, list) and actions:
        lines.append("Actions: " + ", ".join(_clip(item, 80) for item in actions[:6]))
    evidence = result.get("evidence")
    if isinstance(evidence, dict) and evidence:
        parts = [f"{_clip(k, 50)}={_clip(v, 120)}" for k, v in list(evidence.items())[:6]]
        lines.append("Evidence: " + "; ".join(parts))
    text = "\n".join(lines)
    return text if len(text) <= 3900 else text[:3897] + "..."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-id", required=True)
    parser.add_argument("--kind", default="mission")
    parser.add_argument("--result", default="falcon-cloudflare-result.json")
    args = parser.parse_args()

    token = os.getenv("FALCON_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("FALCON_TELEGRAM_BOT_TOKEN_required")
    chat_id = int(args.chat_id)
    kind = args.kind.strip().lower()

    if kind == "health":
        text = "FALCON Cloudflare gateway: HEALTHY"
    elif kind == "help":
        text = "FALCON DIRECT connected via Cloudflare. Send a mission in plain language. /health checks gateway health."
    else:
        text = _format_mission(_load(args.result))

    TelegramClient(token).send_message(chat_id, text)
    print(json.dumps({"telegram_reply_sent": True, "kind": kind}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
