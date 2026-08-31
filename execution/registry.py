"""Execution registry: capabilities are replaceable adapters."""
from typing import Callable, Any
from contracts.models import Event

class Executor:
    def __init__(self): self.adapters: dict[str, Callable[[dict], Any]] = {}
    def register(self, name: str, fn: Callable[[dict], Any]) -> None: self.adapters[name] = fn
    def execute(self, action: Event) -> Event:
        name = action.payload.get("adapter")
        if name not in self.adapters:
            return Event("FAILURE", "execution", {"ok": False, "error": f"adapter_not_found:{name}"}, correlation_id=action.correlation_id)
        try:
            data = self.adapters[name](action.payload.get("args", {}))
            return Event("RESULT", "execution", {"ok": True, "data": data}, correlation_id=action.correlation_id)
        except Exception as exc:
            return Event("FAILURE", "execution", {"ok": False, "error": type(exc).__name__, "message": str(exc)}, correlation_id=action.correlation_id)
