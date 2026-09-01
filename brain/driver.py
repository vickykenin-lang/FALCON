"""Brain-driven autonomous mission coordinator.

Turns provider-neutral plans into governed actions, executes them, collects
observable evidence and asks Brain to re-plan after failures. Bounded retries
prevent runaway autonomy.
"""
from contracts.models import Event, Mission


class BrainDriver:
    def __init__(self, brain, executor, governance, runtime, max_replans: int = 3):
        self.brain = brain
        self.executor = executor
        self.governance = governance
        self.runtime = runtime
        self.max_replans = max_replans

    def run(self, mission: Mission, context: dict | None = None) -> Mission:
        working_context = dict(context or mission.context or {})
        replans = 0
        while replans <= self.max_replans:
            plan_event = self.brain.plan(mission, working_context)
            self.runtime.bus.publish(plan_event)
            if plan_event.event_type == "FAILURE":
                mission.transition("BLOCKED")
                self.runtime.checkpoint(mission)
                return mission

            plan = plan_event.payload["plan"]
            if plan.get("needs_more_context"):
                mission.transition("BLOCKED")
                self.runtime.bus.publish(Event("ALERT", "brain", {"mission_id": mission.mission_id, "reason": "more_context_required"}, target="interface", correlation_id=mission.mission_id))
                self.runtime.checkpoint(mission)
                return mission

            if mission.status == "DISCOVERING": self.runtime.advance(mission)
            if mission.status == "PLANNING": self.runtime.advance(mission)

            evidence=[]
            all_ok=True
            actions=self.brain.action_events(mission, plan_event)
            if not actions:
                all_ok=False
                evidence.append({"ok":False,"error":"empty_plan"})

            for action in actions:
                allowed, reason = self.governance.authorize(action)
                if not allowed:
                    mission.transition("BLOCKED")
                    self.runtime.bus.publish(Event("ALERT", "governance", {"mission_id":mission.mission_id,"reason":reason}, target="interface", correlation_id=mission.mission_id))
                    self.runtime.checkpoint(mission)
                    return mission
                result=self.executor.execute(action)
                self.runtime.bus.publish(result)
                evidence.append(result.payload)
                if not result.payload.get("ok"):
                    all_ok=False
                    break

            if mission.status == "EXECUTING": self.runtime.advance(mission)
            verification=Event("RESULT","brain_driver",{"ok":all_ok,"evidence":evidence,"success_criteria":plan.get("success_criteria",[])},target="autonomic",correlation_id=mission.mission_id)
            self.runtime.bus.publish(verification)
            if mission.status == "VERIFYING": self.runtime.advance(mission,verification)
            if mission.status == "SUCCEEDED": return mission

            replans += 1
            working_context["previous_plan"] = plan
            working_context["previous_evidence"] = evidence
            working_context["replan_attempt"] = replans
            if replans > self.max_replans:
                mission.transition("FAILED")
                self.runtime.checkpoint(mission)
                return mission
            if mission.status == "ADAPTING": self.runtime.advance(mission)

        return mission
