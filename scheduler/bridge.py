"""Scheduler-to-Falcon bridge.

This is the replaceable coupling point between the independent Scheduler organ
and Falcon's Nervous System/Autonomic runtime. Scheduler knows nothing about
mission internals; it only calls this boundary when work becomes due.
"""
from contracts.models import Event
from scheduler.engine import Schedule


class SchedulerBridge:
    def __init__(self, runtime):
        self.runtime = runtime
        self.started_missions: dict[str, str] = {}

    def on_due(self, schedule: Schedule):
        trigger = Event(
            "REQUEST",
            "scheduler",
            {
                "schedule_id": schedule.schedule_id,
                "objective": schedule.objective,
                "trigger": "SCHEDULE_DUE",
            },
            target="autonomic",
            correlation_id=schedule.schedule_id,
        )
        self.runtime.bus.publish(trigger)
        mission = self.runtime.accept(schedule.objective, source="scheduler", source_id=schedule.schedule_id)
        self.started_missions[schedule.schedule_id] = mission.mission_id
        return mission
