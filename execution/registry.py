"""Execution registry: capabilities are replaceable adapters."""
from typing import Any
from contracts.models import Event
from execution.adapters.base import ExecutionAdapter


class Executor:
    def __init__(self):
        self.adapters: dict[str, ExecutionAdapter] = {}

    def register(self, adapter: ExecutionAdapter) -> None:
        if not adapter.name:
            raise ValueError("adapter_name_required")
        self.adapters[adapter.name] = adapter

    def unregister(self, name: str) -> None:
        self.adapters.pop(name, None)

    def replace(self, adapter: ExecutionAdapter) -> None:
        """Hot-swap one adapter while preserving the Executor contract."""
        self.register(adapter)

    def available(self) -> dict[str, bool]:
        return {name: adapter.available() for name, adapter in self.adapters.items()}

    def execute(self, action: Event) -> Event:
        name = action.payload.get("adapter")
        adapter = self.adapters.get(name)
        if adapter is None:
            return Event("FAILURE", "execution", {"ok": False, "error": f"adapter_not_found:{name}"}, correlation_id=action.correlation_id)
        if not adapter.available():
            return Event("FAILURE", "execution", {"ok": False, "error": f"adapter_unavailable:{name}"}, correlation_id=action.correlation_id)
        try:
            args: dict[str, Any] = action.payload.get("args", {})
            operation = action.payload.get("operation") or action.payload.get("action")
            if not operation:
                raise ValueError("operation_required")
            data = adapter.execute(operation, **args)
            return Event("RESULT", "execution", {"ok": True, "adapter": name, "data": data}, correlation_id=action.correlation_id)
        except Exception as exc:
            return Event("FAILURE", "execution", {"ok": False, "adapter": name, "error": type(exc).__name__, "message": str(exc)}, correlation_id=action.correlation_id)

    def cancel(self, adapter_name: str, operation_id: str) -> bool:
        adapter = self.adapters.get(adapter_name)
        return bool(adapter and adapter.cancel(operation_id))
