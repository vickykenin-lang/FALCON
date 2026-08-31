"""Founder-direct governance gate."""
from contracts.models import Event

class Governance:
    def authorize(self, event: Event) -> tuple[bool, str]:
        if event.event_type != "ACTION":
            return True, "non_action"
        risk = event.payload.get("risk", "low")
        if risk == "credential_required" and not event.payload.get("credential_available"):
            return False, "credential_required"
        return True, "authorized"
