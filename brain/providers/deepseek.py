"""DeepSeek intelligence provider using the official Responses API.

DeepSeek-specific transport stays behind Falcon's provider-neutral intelligence
contract. Structured JSON Schema output is required before Brain validation.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from brain.plan_contract import PLAN_JSON_SCHEMA, planning_instructions
from brain.providers.base import IntelligenceProvider


class DeepSeekProvider(IntelligenceProvider):
    endpoint = "https://api.deepseek.com/responses"

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

    @staticmethod
    def _extract_output_text(data: dict) -> str:
        direct = data.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct
        for item in data.get("output") or []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for part in item.get("content") or []:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        return text
        raise RuntimeError("deepseek_response_missing_output_text")

    def decide(self, objective: str, context: dict) -> dict:
        payload = {
            "model": self.model,
            "instructions": planning_instructions(),
            "input": json.dumps({"objective": objective, "context": context, "falcon_contract_version": "1.0"}, ensure_ascii=False),
            "reasoning": {"effort": "none"},
            "max_output_tokens": self.max_tokens,
            "stream": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "falcon_plan",
                    "schema": PLAN_JSON_SCHEMA,
                }
            },
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
        except (TypeError, ValueError) as exc:
            raise RuntimeError("deepseek_invalid_json") from exc
        if not isinstance(data, dict):
            raise RuntimeError("deepseek_response_must_be_object")
        if data.get("status") == "failed":
            raise RuntimeError("deepseek_response_failed")
        try:
            plan = json.loads(self._extract_output_text(data))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("deepseek_invalid_plan_response") from exc
        if not isinstance(plan, dict):
            raise RuntimeError("deepseek_plan_must_be_object")
        return plan
