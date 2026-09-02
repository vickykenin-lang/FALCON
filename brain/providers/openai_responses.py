"""OpenAI Responses API intelligence provider for Falcon.

This adapter is replaceable and keeps OpenAI-specific request/response handling
outside Falcon's provider-neutral Brain contract. It uses structured JSON output
so every model response must conform to Falcon's plan schema.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from brain.providers.base import IntelligenceProvider


_PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "adapter": {"type": "string"},
                    "operation": {"type": "string"},
                    "capability": {"type": "string"},
                    "args": {"type": "object"},
                    "risk": {"type": "string"},
                },
                "required": ["adapter", "operation", "capability", "args", "risk"],
            },
        },
        "success_criteria": {"type": "array", "items": {"type": "string"}},
        "needs_more_context": {"type": "boolean"},
    },
    "required": ["summary", "actions", "success_criteria", "needs_more_context"],
}


class OpenAIResponsesProvider(IntelligenceProvider):
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.6-sol",
        timeout: float = 60.0,
        opener=None,
        endpoint: str | None = None,
    ):
        key = str(api_key or "").strip()
        model = str(model or "").strip()
        if not key:
            raise ValueError("openai_api_key_required")
        if not model:
            raise ValueError("openai_model_required")
        if timeout <= 0:
            raise ValueError("timeout_must_be_positive")
        self.api_key = key
        self.model = model
        self.timeout = float(timeout)
        self.opener = opener or urlopen
        self.endpoint = (endpoint or self.endpoint).rstrip("/")

    @staticmethod
    def _instructions() -> str:
        return (
            "You are Falcon's planning intelligence. Return only a valid Falcon plan. "
            "Use only operations listed in context.execution_capabilities when present. "
            "Never invent credentials, permissions, tools, adapters, repository names, or evidence. "
            "If required operational context is unavailable, set needs_more_context=true and actions=[]. "
            "Prefer the smallest safe action sequence that can produce verifiable evidence. "
            "For retries, use previous_evidence and verification to adapt rather than repeat blindly."
        )

    @staticmethod
    def _extract_output_text(data: dict) -> str:
        direct = data.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct
        for item in data.get("output") or []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content") or []:
                if isinstance(content, dict) and content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str) and text.strip():
                        return text
        raise RuntimeError("openai_response_missing_output_text")

    def decide(self, objective: str, context: dict) -> dict:
        payload = {
            "model": self.model,
            "store": False,
            "instructions": self._instructions(),
            "input": json.dumps(
                {
                    "objective": objective,
                    "context": context,
                    "falcon_contract_version": "1.0",
                },
                ensure_ascii=False,
            ),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "falcon_plan",
                    "strict": True,
                    "schema": _PLAN_SCHEMA,
                }
            },
        }
        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "FALCON/1.0",
            },
            method="POST",
        )
        try:
            raw = self.opener(request, timeout=self.timeout).read()
        except HTTPError as exc:
            raise RuntimeError(f"openai_http_error:{exc.code}") from exc
        except URLError as exc:
            raise RuntimeError("openai_provider_unreachable") from exc
        try:
            data = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("openai_invalid_json") from exc
        if not isinstance(data, dict):
            raise RuntimeError("openai_response_must_be_object")
        text = self._extract_output_text(data)
        try:
            plan = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("openai_plan_invalid_json") from exc
        if not isinstance(plan, dict):
            raise RuntimeError("openai_plan_must_be_object")
        return plan
