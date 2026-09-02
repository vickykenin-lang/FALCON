"""Stable execution adapter interface.

Adapters may be replaced without changing Executor or other Falcon organs.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ExecutionContext:
    """Stable execution identity propagated from mission coordination to adapters."""
    operation_id: str
    correlation_id: str | None = None

class ExecutionAdapter(ABC):
    name: str
    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError
    def required_capability(self,action:str)->str|None:
        """Return the exact capability required for an adapter operation, when constrained."""
        return None
    @abstractmethod
    def execute(self, action: str, *, execution_context: ExecutionContext | None = None, **kwargs: Any) -> Any:
        """Execute one adapter-owned action with an optional cancellable operation identity."""
        raise NotImplementedError
    def cancel(self, operation_id: str) -> bool:
        """Cancel the running operation identified by the same execution context ID."""
        return False
