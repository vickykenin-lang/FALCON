"""Gemini intelligence provider using structured JSON output with bounded retry."""
from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from brain.plan_contract import PLAN_JSON_SCHEMA, planning_instructions
from brain.providers.base import IntelligenceProvider


class GeminiProvider(IntelligenceProvider):
    base_endpoint = "https://generativelanguage.googleapis.com/v1beta/models"
    RETRYABLE_HTTP = {429, 500, 502, 503, 504}
    THINKING_LEVELS = {"low", "medium", "high"}

    def __init__(self, api_key: str, model: str = "gemini-3.7-flash", timeout: float = 60.0, opener=None, base_endpoint: str | None = None, max_attempts: int = 2, retry_delay: float = 1.0, sleeper=None, thinking_level: str = "low", max_output_tokens: int = 4096):
        key = str(api_key or "").strip()
        model = str(model or "").strip()
        thinking_level = str(thinking_level or "").strip().lower()
        if not key: raise ValueError("gemini_api_key_required")
        if not model: raise ValueError("gemini_model_required")
        if timeout <= 0: raise ValueError("timeout_must_be_positive")
        if int(max_attempts) < 1: raise ValueError("max_attempts_must_be_positive")
        if float(retry_delay) < 0: raise ValueError("retry_delay_must_be_non_negative")
        if thinking_level not in self.THINKING_LEVELS: raise ValueError("invalid_gemini_thinking_level")
        if int(max_output_tokens) <= 0: raise ValueError("max_output_tokens_must_be_positive")
        self.api_key = key
        self.model = model
        self.timeout = float(timeout)
        self.max_attempts = int(max_attempts)
        self.retry_delay = float(retry_delay)
        self.thinking_level = thinking_level
        self.max_output_tokens = int(max_output_tokens)
        self.opener = opener or urlopen
        self.sleeper = sleeper or time.sleep
        self.base_endpoint = (base_endpoint or self.base_endpoint).rstrip("/")

    @property
    def endpoint(self) -> str:
        return f"{self.base_endpoint}/{quote(self.model, safe='')}:generateContent"

    def _request(self, payload: dict) -> bytes:
        last_error = None
        for attempt in range(self.max_attempts):
            req = Request(self.endpoint, data=json.dumps(payload).encode("utf-8"), headers={
                "x-goog-api-key": self.api_key, "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "FALCON/1.0"
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

    def decide(self, objective: str, context: dict) -> dict:
        prompt = json.dumps({"objective": objective, "context": context, "falcon_contract_version": "1.0"}, ensure_ascii=False)
        payload = {
            "systemInstruction": {"parts": [{"text": planning_instructions()}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": PLAN_JSON_SCHEMA,
                "thinkingConfig": {"thinkingLevel": self.thinking_level},
                "maxOutputTokens": self.max_output_tokens,
            },
        }
        raw = self._request(payload)
        try:
            data = json.loads(raw)
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
            plan = json.loads(text)
        except (TypeError, ValueError, KeyError, IndexError) as exc:
            raise RuntimeError("gemini_invalid_plan_response") from exc
        if not isinstance(plan, dict):
            raise RuntimeError("gemini_plan_must_be_object")
        return plan
