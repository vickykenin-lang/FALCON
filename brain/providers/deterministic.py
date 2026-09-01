"""Deterministic provider used for offline operation, tests and safe fallback.

It is intentionally simple. Real LLM/provider adapters can replace it without
changing Brain, mission runtime, scheduler or execution.
"""
from brain.providers.base import IntelligenceProvider


class DeterministicProvider(IntelligenceProvider):
    def __init__(self, adapter: str = "noop", operation: str = "inspect"):
        self.adapter = adapter
        self.operation = operation

    def decide(self, objective: str, context: dict) -> dict:
        return {
            "summary": f"Inspect and progress objective: {objective}",
            "actions": [{
                "adapter": self.adapter,
                "operation": self.operation,
                "args": {"objective": objective, "context": context},
                "risk": "low",
            }],
            "success_criteria": ["execution_result_ok"],
            "needs_more_context": False,
        }
