"""Scheduler output bridge using injected contract-level callables only."""
from contracts.models import Event
from scheduler.engine import Schedule
class SchedulerBridge:
    def __init__(self,publish,start_mission):
        if not callable(publish) or not callable(start_mission): raise TypeError("scheduler_bridge_callables_required")
        self.publish=publish; self.start_mission=start_mission; self.started_missions:dict[str,str]={}
    def on_due(self,schedule:Schedule):
        trigger=Event("REQUEST","scheduler",{"schedule_id":schedule.schedule_id,"objective":schedule.objective,"trigger":"SCHEDULE_DUE"},target="autonomic",correlation_id=schedule.schedule_id)
        self.publish(trigger)
        mission=self.start_mission(schedule.objective,source="scheduler",source_id=schedule.schedule_id)
        self.started_missions[schedule.schedule_id]=mission.mission_id
        return mission
