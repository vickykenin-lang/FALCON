#!/usr/bin/env python3
"""Send a bounded Falcon task result to Telegram without exposing credentials or overstating verification."""
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


def _truth_state(result: dict) -> tuple[str, str]:
    """Separate runtime execution from verification of the Founder's requested outcome."""
    execution = str(result.get("status", "UNKNOWN")).upper()
    explicit = result.get("reporting_verified") is True
    if execution != "SUCCEEDED":
        return execution, "NOT_VERIFIED"
    return execution, "VERIFIED" if explicit else "NOT_VERIFIED"


def _format_mission(result: dict) -> str:
    execution_status, completeness = _truth_state(result)
    mission_id = str(result.get("mission_id", "unknown"))
    attempts = int(result.get("attempts", 0) or 0)
    lines = [
        f"FALCON mission {mission_id}",
        f"Execution status: {execution_status}",
        f"Requested outcome verified: {completeness}",
        f"Attempts: {attempts}",
    ]
    if execution_status == "SUCCEEDED" and completeness != "VERIFIED":
        lines.append("Integrity: execution completed, but Falcon has not proved that every requested deliverable is complete. Do not treat this as full task success.")
    reason = _clip(result.get("reason"), 500)
    if reason:
        lines.append(f"Reason: {reason}")
    summary = _clip(result.get("plan_summary"), 900)
    if summary:
        lines.append(f"Plan summary: {summary}")
    actions = result.get("actions") or []
    if isinstance(actions, list) and actions:
        lines.append("Executed actions: " + ", ".join(_clip(item, 80) for item in actions[:6]))
    evidence = result.get("evidence")
    if isinstance(evidence, dict) and evidence:
        parts = [f"{_clip(k, 50)}={_clip(v, 120)}" for k, v in list(evidence.items())[:6]]
        lines.append("Bounded evidence: " + "; ".join(parts))
    verification = result.get("verification")
    if isinstance(verification, dict):
        lines.append("Execution verification: " + "; ".join(
            f"{_clip(k, 40)}={_clip(v, 100)}" for k, v in verification.items() if v is not None
        ))
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
        text = "FALCON Cloudflare gateway: HEALTHY (gateway health only; downstream capabilities are not implied)."
    elif kind == "help":
        text = "FALCON DIRECT connected via Cloudflare. Send a mission in plain language. /health verifies gateway health only."
    else:
        text = _format_mission(_load(args.result))

    TelegramClient(token).send_message(chat_id, text)
    print(json.dumps({"telegram_reply_sent": True, "kind": kind}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
