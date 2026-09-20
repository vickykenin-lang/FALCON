"""Amazon Bedrock intelligence provider for Falcon.

Uses Bedrock Runtime Converse over boto3. AWS credentials are resolved by the
standard AWS credential chain; credentials are never embedded in source.
"""
from __future__ import annotations

import json
from brain.plan_contract import planning_instructions
from brain.providers.base import IntelligenceProvider


class BedrockProvider(IntelligenceProvider):
    def __init__(self, model: str, region: str = "ap-south-1", timeout: float = 60.0, max_tokens: int = 4096, client=None):
        model = str(model or "").strip()
        region = str(region or "").strip()
        if not model:
            raise ValueError("bedrock_model_required")
        if not region:
            raise ValueError("bedrock_region_required")
        if timeout <= 0:
            raise ValueError("timeout_must_be_positive")
        if int(max_tokens) <= 0:
            raise ValueError("max_tokens_must_be_positive")
        self.model = model
        self.region = region
        self.timeout = float(timeout)
        self.max_tokens = int(max_tokens)
        self._client = client

    def _runtime(self):
        if self._client is not None:
            return self._client
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise RuntimeError("bedrock_boto3_required") from exc
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=self.region,
            config=Config(connect_timeout=self.timeout, read_timeout=self.timeout, retries={"max_attempts": 2}),
        )
        return self._client

    @staticmethod
    def _text(response: dict) -> str:
        try:
            blocks = response["output"]["message"]["content"]
            text = "".join(str(block.get("text", "")) for block in blocks if isinstance(block, dict)).strip()
        except (KeyError, TypeError) as exc:
            raise RuntimeError("bedrock_response_missing_output_text") from exc
        if not text:
            raise RuntimeError("bedrock_response_missing_output_text")
        return text

    def decide(self, objective: str, context: dict) -> dict:
        request_text = json.dumps({
            "objective": objective,
            "context": context,
            "falcon_contract_version": "1.0",
            "required_output": "Return only one JSON object with summary, actions, and success_criteria.",
        }, ensure_ascii=False)
        try:
            response = self._runtime().converse(
                modelId=self.model,
                system=[{"text": planning_instructions()}],
                messages=[{"role": "user", "content": [{"text": request_text}]}],
                inferenceConfig={"maxTokens": self.max_tokens, "temperature": 0},
            )
        except Exception as exc:
            raise RuntimeError(f"bedrock_runtime_error:{type(exc).__name__}") from exc
        try:
            plan = json.loads(self._text(response))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("bedrock_invalid_plan_response") from exc
        if not isinstance(plan, dict):
            raise RuntimeError("bedrock_plan_must_be_object")
        return plan
