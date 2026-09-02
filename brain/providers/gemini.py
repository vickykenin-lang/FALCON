"""Gemini intelligence provider using the current Interactions API.

Gemini-specific transport stays behind Falcon's provider-neutral intelligence
contract. Structured output is enforced before Brain validation.
"""
from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from brain.plan_contract import PLAN_JSON_SCHEMA, planning_instructions
from brain.providers.base import IntelligenceProvider


class GeminiProvider(IntelligenceProvider):
    endpoint = "https://generativelanguage.googleapis.com/v1beta/interactions"
    RETRYABLE_HTTP = {429, 500, 502, 503, 504}

    def __init__(self, api_key: str, model: str = "gemini-3.7-flash", timeout: float = 60.0, opener=None, endpoint: str | None = None, max_attempts: int = 2, retry_delay: float = 1.0, sleeper=None, max_output_tokens: int = 4096):
        key = str(api_key or "").strip()
        model = str(model or "").strip()
        if not key: raise ValueError("gemini_api_key_required")
        if not model: raise ValueError("gemini_model_required")
        if timeout <= 0: raise ValueError("timeout_must_be_positive")
        if int(max_attempts) < 1: raise ValueError("max_attempts_must_be_positive")
        if float(retry_delay) < 0: raise ValueError("retry_delay_must_be_non_negative")
        if int(max_output_tokens) <= 0: raise ValueError("max_output_tokens_must_be_positive")
        self.api_key = key
        self.model = model
        self.timeout = float(timeout)
        self.max_attempts = int(max_attempts)
        self.retry_delay = float(retry_delay)
        self.max_output_tokens = int(max_output_tokens)
        self.opener = opener or urlopen
        self.sleeper = sleeper or time.sleep
        self.endpoint = (endpoint or self.endpoint).rstrip("/")

    def _request(self, payload: dict) -> bytes:
        last_error = None
        for attempt in range(self.max_attempts):
            req = Request(self.endpoint, data=json.dumps(payload).encode("utf-8"), headers={
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "FALCON/1.0",
            }, method="POST")
            try:
                return self.opener(req, timeout=self.timeout).read()
            except HTTPError as exc:
                last_error = exc
                if exc.code not in self.RETRYABLE_HTTP or attempt + 1 >= self.max_attempts:
                    raise RuntimeError(f"gemini_http_error:{exc.code}") from exc
            except TimeoutError as exc:
                last_error = exc
                if attempt + 1 >= self.max_attempts:
                    raise RuntimeError("gemini_provider_timeout") from exc
            except URLError as exc:
                last_error = exc
                if attempt + 1 >= self.max_attempts:
                    raise RuntimeError("gemini_provider_unreachable") from exc
            if self.retry_delay:
                self.sleeper(self.retry_delay)
        raise RuntimeError("gemini_provider_unreachable") from last_error

    @staticmethod
    def _extract_output_text(data: dict) -> str:
        direct = data.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct
        parts = []
        for step in data.get("steps") or []:
            if not isinstance(step, dict) or step.get("type") != "model_output":
                continue
            for item in step.get("content") or []:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str) and text:
                        parts.append(text)
        text = "".join(parts).strip()
        if not text:
            raise RuntimeError("gemini_response_missing_output_text")
        return text

    def decide(self, objective: str, context: dict) -> dict:
        payload = {
            "model": self.model,
            "system_instruction": planning_instructions(),
            "input": json.dumps({"objective": objective, "context": context, "falcon_contract_version": "1.0"}, ensure_ascii=False),
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": PLAN_JSON_SCHEMA,
            },
            "generation_config": {"max_output_tokens": self.max_output_tokens},
            "stream": False,
            "store": False,
        }
        raw = self._request(payload)
        try:
            data = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("gemini_invalid_json") from exc
        if not isinstance(data, dict):
            raise RuntimeError("gemini_response_must_be_object")
        status = str(data.get("status") or "completed").lower()
        if status == "failed":
            raise RuntimeError("gemini_response_failed")
        if status in {"cancelled", "incomplete", "requires_action"}:
            raise RuntimeError(f"gemini_response_not_completed:{status}")
        try:
            plan = json.loads(self._extract_output_text(data))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("gemini_invalid_plan_response") from exc
        if not isinstance(plan, dict):
            raise RuntimeError("gemini_plan_must_be_object")
        return plan
