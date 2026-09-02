"""Provider-independent Falcon intelligence and planning engine."""
from contracts.models import Event, Mission
from brain.plan_contract import normalize_plan


class Brain:
    def __init__(self, provider=None): self.provider = provider
    def replace_provider(self, provider) -> None: self.provider = provider
    def available(self) -> bool: return self.provider is not None
    def status(self) -> dict:
        if self.provider is None:
            return {"configured": False, "providers": [], "fallback_available": False}
        provider_status = getattr(self.provider, "status", None)
        if callable(provider_status):
            return {"configured": True, **provider_status()}
        return {"configured": True, "providers": [type(self.provider).__name__], "fallback_available": False}
    def understand(self, mission: Mission) -> Event:
        return Event("DECISION", "brain", {"mission_id": mission.mission_id, "objective": mission.objective, "decision": "inspect_context"}, target="execution", correlation_id=mission.mission_id)
    def plan(self, mission: Mission, context: dict | None = None) -> Event:
        if self.provider is None:
            return Event("FAILURE", "brain", {"ok": False, "error": "intelligence_provider_not_configured"}, target="autonomic", correlation_id=mission.mission_id)
        try:
            plan = normalize_plan(self.provider.decide(mission.objective, context or mission.context or {}))
        except Exception as exc:
            return Event("FAILURE", "brain", {"ok": False, "error": "intelligence_provider_failed", "provider_error": type(exc).__name__, "detail": str(exc)[:500]}, target="autonomic", correlation_id=mission.mission_id)
        return Event("DECISION", "brain", {"mission_id": mission.mission_id, "plan": plan}, target="autonomic", correlation_id=mission.mission_id)
    @staticmethod
    def _validate_plan(plan: dict) -> dict:
        return normalize_plan(plan)
    def action_events(self, mission: Mission, plan_event: Event) -> list[Event]:
        plan = plan_event.payload.get("plan", {})
        return [Event("ACTION", "brain", action, target="execution", correlation_id=mission.mission_id) for action in plan.get("actions", [])]
    def evaluate(self, result: Event) -> Event:
        ok = bool(result.payload.get("ok"))
        return Event("DECISION", "brain", {"outcome": "continue" if ok else "diagnose", "based_on": result.event_id}, correlation_id=result.correlation_id)
