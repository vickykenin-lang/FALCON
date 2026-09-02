"""Gemini intelligence provider using structured JSON output."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from brain.plan_contract import PLAN_JSON_SCHEMA, planning_instructions
from brain.providers.base import IntelligenceProvider


class GeminiProvider(IntelligenceProvider):
    base_endpoint = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: str = "gemini-3.7-flash", timeout: float = 60.0, opener=None, base_endpoint: str | None = None):
        key = str(api_key or "").strip()
        model = str(model or "").strip()
        if not key: raise ValueError("gemini_api_key_required")
        if not model: raise ValueError("gemini_model_required")
        if timeout <= 0: raise ValueError("timeout_must_be_positive")
        self.api_key = key
        self.model = model
        self.timeout = float(timeout)
        self.opener = opener or urlopen
        self.base_endpoint = (base_endpoint or self.base_endpoint).rstrip("/")

    @property
    def endpoint(self) -> str:
        return f"{self.base_endpoint}/{quote(self.model, safe='')}:generateContent"

    def decide(self, objective: str, context: dict) -> dict:
        prompt = json.dumps({"objective": objective, "context": context, "falcon_contract_version": "1.0"}, ensure_ascii=False)
        payload = {
            "systemInstruction": {"parts": [{"text": planning_instructions()}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": PLAN_JSON_SCHEMA,
            },
        }
        req = Request(self.endpoint, data=json.dumps(payload).encode("utf-8"), headers={
            "x-goog-api-key": self.api_key, "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "FALCON/1.0"
        }, method="POST")
        try:
            raw = self.opener(req, timeout=self.timeout).read()
        except HTTPError as exc:
            raise RuntimeError(f"gemini_http_error:{exc.code}") from exc
        except URLError as exc:
            raise RuntimeError("gemini_provider_unreachable") from exc
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
