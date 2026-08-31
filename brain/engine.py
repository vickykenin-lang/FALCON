"""Brain orchestration policy. Model reasoning is injected later through an adapter."""
from contracts.models import Event, Mission

class Brain:
    def understand(self, mission: Mission) -> Event:
        return Event("DECISION", "brain", {"mission_id": mission.mission_id, "objective": mission.objective, "decision": "inspect_context"}, target="execution", correlation_id=mission.mission_id)

    def evaluate(self, result: Event) -> Event:
        ok = bool(result.payload.get("ok"))
        return Event("DECISION", "brain", {"outcome": "continue" if ok else "diagnose", "based_on": result.event_id}, correlation_id=result.correlation_id)
