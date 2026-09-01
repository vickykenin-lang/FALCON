"""Provider-independent Falcon intelligence and planning engine."""
from contracts.models import Event, Mission


class Brain:
    def __init__(self, provider=None):
        self.provider = provider

    def replace_provider(self, provider) -> None:
        """Hot-swap intelligence without changing Falcon's Brain contract."""
        self.provider = provider

    def available(self) -> bool:
        return self.provider is not None

    def understand(self, mission: Mission) -> Event:
        return Event("DECISION", "brain", {"mission_id": mission.mission_id, "objective": mission.objective, "decision": "inspect_context"}, target="execution", correlation_id=mission.mission_id)

    def plan(self, mission: Mission, context: dict | None = None) -> Event:
        """Ask the injected provider for a structured, provider-neutral V1 plan."""
        if self.provider is None:
            return Event("FAILURE", "brain", {"ok": False, "error": "intelligence_provider_not_configured"}, target="autonomic", correlation_id=mission.mission_id)
        raw = self.provider.decide(mission.objective, context or mission.context or {})
        plan = self._validate_plan(raw)
        return Event("DECISION", "brain", {"mission_id": mission.mission_id, "plan": plan}, target="autonomic", correlation_id=mission.mission_id)

    @staticmethod
    def _validate_plan(plan: dict) -> dict:
        if not isinstance(plan, dict):
            raise ValueError("plan_must_be_object")
        summary = plan.get("summary")
        actions = plan.get("actions")
        criteria = plan.get("success_criteria")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("plan_summary_required")
        if not isinstance(actions, list):
            raise ValueError("plan_actions_required")
        if not isinstance(criteria, list):
            raise ValueError("success_criteria_required")
        normalized=[]
        for action in actions:
            if not isinstance(action, dict) or not action.get("adapter") or not action.get("operation"):
                raise ValueError("invalid_plan_action")
            normalized.append({
                "adapter": action["adapter"],
                "operation": action["operation"],
                "args": action.get("args", {}),
                "risk": action.get("risk", "low"),
            })
        return {
            "summary": summary.strip(),
            "actions": normalized,
            "success_criteria": criteria,
            "needs_more_context": bool(plan.get("needs_more_context", False)),
            "contract_version": "1.0",
        }

    def action_events(self, mission: Mission, plan_event: Event) -> list[Event]:
        plan = plan_event.payload.get("plan", {})
        return [Event("ACTION", "brain", action, target="execution", correlation_id=mission.mission_id) for action in plan.get("actions", [])]

    def evaluate(self, result: Event) -> Event:
        ok = bool(result.payload.get("ok"))
        return Event("DECISION", "brain", {"outcome": "continue" if ok else "diagnose", "based_on": result.event_id}, correlation_id=result.correlation_id)
