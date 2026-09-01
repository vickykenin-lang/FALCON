"""Stable execution adapter interface.

Adapters may be replaced without changing Executor or other Falcon organs.
"""
from abc import ABC, abstractmethod
from typing import Any


class ExecutionAdapter(ABC):
    name: str

    @abstractmethod
    def available(self) -> bool:
        """Return whether the adapter can currently execute work."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, action: str, **kwargs: Any) -> Any:
        """Execute one adapter-owned action."""
        raise NotImplementedError

    def cancel(self, operation_id: str) -> bool:
        """Optional cancellation capability."""
        return False
