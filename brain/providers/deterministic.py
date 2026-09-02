"""Deterministic provider used for offline operation, tests and safe fallback.

It is intentionally simple. Real LLM/provider adapters can replace it without
changing Brain, mission runtime, scheduler or execution.
"""
from brain.providers.base import IntelligenceProvider


class DeterministicProvider(IntelligenceProvider):
    def __init__(self,adapter:str="noop",operation:str="inspect",capability:str="noop.inspect"):
        if not capability or not capability.strip(): raise ValueError("capability_required")
        self.adapter=adapter; self.operation=operation; self.capability=capability.strip()

    def decide(self,objective:str,context:dict)->dict:
        return {
            "summary":f"Inspect and progress objective: {objective}",
            "actions":[{
                "adapter":self.adapter,
                "operation":self.operation,
                "capability":self.capability,
                "args":{"objective":objective,"context":context},
                "risk":"low",
            }],
            "success_criteria":["execution_result_ok"],
            "needs_more_context":False,
        }
