"""Sandbox boundary for execution isolation.

This module defines policy and lifecycle only. Concrete sandbox technologies are
plugged in as replaceable backends, so changing E2B/container/local isolation
never requires changes to Falcon's Brain, Memory, Interface, or mission runtime.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class SandboxRequest:
    command: str
    args: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 60
    network: bool = False
    request_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class SandboxResult:
    ok: bool
    output: Any = None
    error: str | None = None
    request_id: str | None = None


class SandboxBackend(ABC):
    name: str

    @abstractmethod
    def run(self, request: SandboxRequest) -> SandboxResult:
        raise NotImplementedError

    def cancel(self, request_id: str) -> bool:
        return False


class Sandbox:
    def __init__(self, backend: SandboxBackend | None = None):
        self.backend = backend

    def replace_backend(self, backend: SandboxBackend) -> None:
        self.backend = backend

    def run(self, request: SandboxRequest) -> SandboxResult:
        if self.backend is None:
            return SandboxResult(False, error="sandbox_backend_not_configured", request_id=request.request_id)
        return self.backend.run(request)
