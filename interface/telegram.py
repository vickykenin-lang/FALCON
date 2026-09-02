"""Founder-direct Telegram gateway for Falcon.

Uses Telegram Bot API long polling with stdlib only. Credentials stay outside
this repository. The gateway accepts messages only from the configured Founder
Telegram user id and routes plain text directly into Falcon's mission loop.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass
class TelegramConfig:
    bot_token: str
    allowed_user_id: int
    poll_timeout: int = 25

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        token = os.getenv("FALCON_TELEGRAM_BOT_TOKEN", "").strip()
        allowed = os.getenv("FALCON_TELEGRAM_ALLOWED_USER_ID", "").strip()
        if not token:
            raise RuntimeError("FALCON_TELEGRAM_BOT_TOKEN_required")
        if not allowed:
            raise RuntimeError("FALCON_TELEGRAM_ALLOWED_USER_ID_required")
        try:
            user_id = int(allowed)
        except ValueError as exc:
            raise RuntimeError("FALCON_TELEGRAM_ALLOWED_USER_ID_must_be_integer") from exc
        return cls(bot_token=token, allowed_user_id=user_id)


class TelegramClient:
    def __init__(self, token: str, opener=urlopen):
        self._base = f"https://api.telegram.org/bot{token}"
        self._opener = opener

    def _call(self, method: str, payload: dict | None = None) -> dict:
        data = urlencode(payload or {}).encode("utf-8")
        req = Request(f"{self._base}/{method}", data=data, method="POST")
        with self._opener(req, timeout=35) as response:
            body = json.loads(response.read().decode("utf-8"))
        if not body.get("ok"):
            raise RuntimeError(f"telegram_api_error:{method}")
        return body.get("result")

    def get_me(self) -> dict:
        return self._call("getMe")

    def get_updates(self, offset: int | None = None, timeout: int = 25) -> list[dict]:
        payload = {"timeout": timeout, "allowed_updates": json.dumps(["message"])}
        if offset is not None:
            payload["offset"] = offset
        return self._call("getUpdates", payload) or []

    def send_message(self, chat_id: int, text: str) -> dict:
        return self._call("sendMessage", {"chat_id": chat_id, "text": text[:4096]})


class TelegramGateway:
    def __init__(self, runtime, config: TelegramConfig, client: TelegramClient | None = None):
        self.runtime = runtime
        self.config = config
        self.client = client or TelegramClient(config.bot_token)
        self.offset = None

    def verify_bot(self) -> dict:
        return self.client.get_me()

    def _reply(self, chat_id: int, text: str) -> None:
        self.client.send_message(chat_id, text)

    def _mission_summary(self, mission) -> str:
        mission_id = getattr(mission, "mission_id", "unknown")
        status = getattr(mission, "status", getattr(mission, "state", "UNKNOWN"))
        attempts = getattr(mission, "attempts", 0)
        return f"FALCON mission {mission_id}\nStatus: {status}\nAttempts: {attempts}"

    def process_update(self, update: dict) -> str:
        message = update.get("message") or {}
        sender = message.get("from") or {}
        chat = message.get("chat") or {}
        user_id = sender.get("id")
        chat_id = chat.get("id")
        text = str(message.get("text") or "").strip()
        if not chat_id or not text:
            return "ignored"
        if user_id != self.config.allowed_user_id:
            self._reply(chat_id, "FALCON access denied.")
            return "denied"
        if text in {"/start", "/help"}:
            self._reply(chat_id, "FALCON DIRECT connected. Send a mission in plain language. /health checks runtime health.")
            return "help"
        if text == "/health":
            heartbeat = self.runtime.heartbeat().to_dict()
            status = heartbeat.get("payload", {}).get("status", "UNKNOWN")
            self._reply(chat_id, f"FALCON health: {status}")
            return "health"
        mission = self.runtime.accept(text, context={"channel": "telegram", "founder_user_id": user_id})
        driver = getattr(self.runtime, "driver", None)
        if driver is not None:
            mission = driver.run(mission, context={"channel": "telegram", "founder_user_id": user_id})
        self._reply(chat_id, self._mission_summary(mission))
        return "mission"

    def run_forever(self, sleep_on_error: float = 2.0) -> None:
        me = self.verify_bot()
        username = me.get("username", "unknown")
        print(f"FALCON TELEGRAM connected @{username}")
        while True:
            try:
                updates = self.client.get_updates(self.offset, self.config.poll_timeout)
                for update in updates:
                    update_id = update.get("update_id")
                    if isinstance(update_id, int):
                        self.offset = update_id + 1
                    self.process_update(update)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"FALCON TELEGRAM error: {type(exc).__name__}")
                time.sleep(sleep_on_error)


def run_telegram(runtime, config: TelegramConfig | None = None) -> None:
    TelegramGateway(runtime, config or TelegramConfig.from_env()).run_forever()
