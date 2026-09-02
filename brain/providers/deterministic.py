"""Deterministic provider used for offline operation, tests and safe fallback.

It is intentionally simple. Real LLM/provider adapters can replace it without
changing Brain, mission runtime, scheduler or execution.
"""
from brain.providers.base import IntelligenceProvider

class DeterministicProvider(IntelligenceProvider):
    def __init__(self,adapter:str="noop",operation:str="inspect",capability:str="noop.inspect",action_args:dict|None=None):
        if not capability or not capability.strip():raise ValueError("capability_required")
        if action_args is not None and not isinstance(action_args,dict):raise TypeError("action_args_must_be_object")
        self.adapter=adapter; self.operation=operation; self.capability=capability.strip(); self.action_args=dict(action_args) if action_args is not None else None
    def decide(self,objective:str,context:dict)->dict:
        args={"objective":objective,"context":context} if self.action_args is None else dict(self.action_args)
        return {"summary":f"Inspect and progress objective: {objective}","actions":[{"adapter":self.adapter,"operation":self.operation,"capability":self.capability,"args":args,"risk":"low"}],"success_criteria":["execution_result_ok"],"needs_more_context":False}
