"""DeepSeek intelligence provider using the official Chat Completions JSON mode."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from brain.plan_contract import planning_instructions
from brain.providers.base import IntelligenceProvider


class DeepSeekProvider(IntelligenceProvider):
    endpoint = "https://api.deepseek.com/chat/completions"

    def __init__(self, api_key: str, model: str = "deepseek-v4-pro", timeout: float = 60.0, max_tokens: int = 8192, opener=None, endpoint: str | None = None):
        key = str(api_key or "").strip()
        model = str(model or "").strip()
        if not key: raise ValueError("deepseek_api_key_required")
        if not model: raise ValueError("deepseek_model_required")
        if timeout <= 0: raise ValueError("timeout_must_be_positive")
        if int(max_tokens) <= 0: raise ValueError("max_tokens_must_be_positive")
        self.api_key = key
        self.model = model
        self.timeout = float(timeout)
        self.max_tokens = int(max_tokens)
        self.opener = opener or urlopen
        self.endpoint = (endpoint or self.endpoint).rstrip("/")

    def decide(self, objective: str, context: dict) -> dict:
        user_payload = json.dumps({"objective": objective, "context": context, "falcon_contract_version": "1.0"}, ensure_ascii=False)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": planning_instructions() + " Output JSON only."},
                {"role": "user", "content": user_payload},
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        req = Request(self.endpoint, data=json.dumps(payload).encode("utf-8"), headers={
            "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "FALCON/1.0"
        }, method="POST")
        try:
            raw = self.opener(req, timeout=self.timeout).read()
        except HTTPError as exc:
            raise RuntimeError(f"deepseek_http_error:{exc.code}") from exc
        except URLError as exc:
            raise RuntimeError("deepseek_provider_unreachable") from exc
        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
            plan = json.loads(content)
        except (TypeError, ValueError, KeyError, IndexError) as exc:
            raise RuntimeError("deepseek_invalid_plan_response") from exc
        if not isinstance(plan, dict):
            raise RuntimeError("deepseek_plan_must_be_object")
        return plan
