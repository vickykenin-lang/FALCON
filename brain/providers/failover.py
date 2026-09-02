"""Ordered failover wrapper for replaceable Falcon intelligence providers."""
from brain.plan_contract import normalize_plan
from brain.providers.base import IntelligenceProvider


class FailoverProvider(IntelligenceProvider):
    def __init__(self, providers: list[tuple[str, IntelligenceProvider]]):
        self.providers = [(str(name), provider) for name, provider in providers if provider is not None]
        if not self.providers:
            raise ValueError("at_least_one_intelligence_provider_required")
        self.last_provider: str | None = None
        self.last_failures: list[str] = []

    def decide(self, objective: str, context: dict) -> dict:
        failures = []
        for name, provider in self.providers:
            try:
                plan = normalize_plan(provider.decide(objective, context))
                self.last_provider = name
                self.last_failures = failures
                return plan
            except Exception as exc:
                failures.append(f"{name}:{type(exc).__name__}")
        self.last_provider = None
        self.last_failures = failures
        raise RuntimeError("intelligence_all_providers_failed:" + ",".join(failures))

    def status(self) -> dict:
        return {
            "providers": [name for name, _ in self.providers],
            "last_provider": self.last_provider,
            "fallback_available": len(self.providers) > 1,
            "last_failures": list(self.last_failures),
        }
