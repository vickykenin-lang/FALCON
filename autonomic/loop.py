"""Bounded autonomous mission loop.

Coordinates organs through their public methods. Concrete execution adapters are
injected; this loop does not know vendor/provider implementations.
"""
from contracts.models import Event, Mission


class AutonomousLoop:
    def __init__(self, runtime, executor, governance, evaluator=None, max_attempts: int = 3):
        self.runtime = runtime
        self.executor = executor
        self.governance = governance
        self.evaluator = evaluator
        self.max_attempts = max_attempts

    def run(self, mission: Mission, action: Event) -> Mission:
        """Run one mission to a terminal/bounded state from an explicit action."""
        while mission.status not in {"SUCCEEDED", "FAILED", "BLOCKED"}:
            if mission.status == "DISCOVERING":
                self.runtime.advance(mission)
                continue
            if mission.status == "PLANNING":
                self.runtime.advance(mission)
                continue
            if mission.status == "EXECUTING":
                allowed, reason = self.governance.authorize(action)
                if not allowed:
                    mission.transition("BLOCKED")
                    self.runtime.bus.publish(Event("ALERT", "governance", {"mission_id": mission.mission_id, "reason": reason}, target="interface", correlation_id=mission.mission_id))
                    self.runtime.checkpoint(mission)
                    break
                result = self.executor.execute(action)
                self.runtime.bus.publish(result)
                self.runtime.advance(mission)
                self.runtime.advance(mission, result)
                if mission.status == "SUCCEEDED":
                    break
                continue
            if mission.status == "ADAPTING":
                if mission.attempts >= self.max_attempts:
                    mission.transition("FAILED")
                    self.runtime.bus.publish(Event("ALERT", "autonomic", {"mission_id": mission.mission_id, "reason": "retry_budget_exhausted"}, target="interface", correlation_id=mission.mission_id))
                    self.runtime.checkpoint(mission)
                    break
                self.runtime.advance(mission)
                continue
            if mission.status == "VERIFYING":
                # VERIFYING is normally handled immediately after execution.
                mission.transition("ADAPTING")
                self.runtime.checkpoint(mission)
        return mission
