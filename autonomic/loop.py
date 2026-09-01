"""Bounded autonomous mission loop with enforced mission control."""
from contracts.models import Event, Mission

class AutonomousLoop:
    def __init__(self,runtime,executor,governance,evaluator=None,max_attempts:int=3,control=None):
        self.runtime=runtime; self.executor=executor; self.governance=governance; self.evaluator=evaluator; self.max_attempts=max_attempts; self.control=control

    def _control_gate(self,mission:Mission)->bool:
        if self.control is None: return True
        state=self.control.state(mission.mission_id)
        if state.cancelled:
            mission.transition("CANCELLED")
            self.runtime.bus.publish(Event("ALERT","autonomic",{"mission_id":mission.mission_id,"reason":state.reason or "cancelled","control":"CANCEL"},target="interface",correlation_id=mission.mission_id))
            self.runtime.checkpoint(mission); return False
        if state.paused:
            self.runtime.bus.publish(Event("ALERT","autonomic",{"mission_id":mission.mission_id,"reason":state.reason or "paused","control":"PAUSE"},target="interface",correlation_id=mission.mission_id))
            self.runtime.checkpoint(mission); return False
        return True

    def run(self,mission:Mission,action:Event)->Mission:
        while mission.status not in {"SUCCEEDED","FAILED","BLOCKED","CANCELLED"}:
            if not self._control_gate(mission): break
            if mission.status in {"DISCOVERING","PLANNING"}:
                self.runtime.advance(mission); continue
            if mission.status=="EXECUTING":
                allowed,reason=self.governance.authorize(action)
                if not allowed:
                    mission.transition("BLOCKED")
                    self.runtime.bus.publish(Event("ALERT","governance",{"mission_id":mission.mission_id,"reason":reason},target="interface",correlation_id=mission.mission_id)); self.runtime.checkpoint(mission); break
                if not self._control_gate(mission): break
                result=self.executor.execute(action); self.runtime.bus.publish(result)
                self.runtime.advance(mission); self.runtime.advance(mission,result)
                if mission.status=="SUCCEEDED": break
                continue
            if mission.status=="ADAPTING":
                if mission.attempts>=self.max_attempts:
                    mission.transition("FAILED")
                    self.runtime.bus.publish(Event("ALERT","autonomic",{"mission_id":mission.mission_id,"reason":"retry_budget_exhausted"},target="interface",correlation_id=mission.mission_id)); self.runtime.checkpoint(mission); break
                self.runtime.advance(mission); continue
            if mission.status=="VERIFYING":
                mission.transition("ADAPTING"); self.runtime.checkpoint(mission)
        return mission
