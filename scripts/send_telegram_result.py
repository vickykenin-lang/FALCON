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
        result = _load(args.result)
        status = str(result.get("status", "UNKNOWN"))
        mission_id = str(result.get("mission_id", "unknown"))
        attempts = int(result.get("attempts", 0) or 0)
        text = f"FALCON mission {mission_id}\nStatus: {status}\nAttempts: {attempts}"

    TelegramClient(token).send_message(chat_id, text)
    print(json.dumps({"telegram_reply_sent": True, "kind": kind}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
