"""Autonomic mission coordinator across replaceable Falcon organs."""
from uuid import uuid4
from contracts.models import Event,Mission
class BrainDriver:
    def __init__(self,brain,executor,governance,runtime,memory=None,max_replans:int=3,control=None,evaluator=None):
        if evaluator is None: raise ValueError("evaluator_required")
        self.brain=brain; self.executor=executor; self.governance=governance; self.runtime=runtime; self.memory=memory; self.max_replans=max_replans; self.control=control; self.evaluator=evaluator
    def _context(self,mission,supplied):
        context=dict(mission.context or {}); context.update(supplied or {})
        if self.memory is not None: context.update(self.memory.context_for(mission.objective))
        if hasattr(self.executor,"capability_catalog"):
            allowed=getattr(self.governance,"allowed_capabilities",set())
            catalog=[]
            for item in self.executor.capability_catalog():
                capability=item.get("capability")
                if item.get("available") and (not capability or capability in allowed):catalog.append(item)
            context["execution_capabilities"]=catalog
        return context
    def _control_gate(self,mission):
        if self.control is None:return True
        state=self.control.state(mission.mission_id)
        if state.cancelled:
            if mission.status!="CANCELLED": mission.transition("CANCELLED"); self.runtime.checkpoint(mission)
            return False
        if state.paused:self.runtime.checkpoint(mission); return False
        return True
    def _execute(self,mission,action):
        operation_id=str(uuid4()); adapter=action.payload.get("adapter")
        if self.control is not None:self.control.begin_operation(mission.mission_id,adapter,operation_id)
        try:return self.executor.execute(action,operation_id=operation_id)
        finally:
            if self.control is not None:self.control.end_operation(mission.mission_id,operation_id)
    def _verify(self,mission,evidence):
        observed={}
        for item in evidence:
            if isinstance(item,dict): observed.update(item.get("data",{}) if isinstance(item.get("data"),dict) else {}); observed.update({k:v for k,v in item.items() if k!="data"})
        evaluation=self.evaluator.evaluate(mission.acceptance_criteria,observed); execution_ok=bool(evidence) and all(bool(item.get("ok")) for item in evidence)
        return execution_ok and evaluation.success,evaluation,observed
    def run(self,mission:Mission,context:dict|None=None)->Mission:
        working_context=self._context(mission,context); replans=0
        while replans<=self.max_replans:
            if not self._control_gate(mission):return mission
            plan_event=self.brain.plan(mission,working_context); self.runtime.bus.publish(plan_event)
            if plan_event.event_type=="FAILURE":mission.transition("BLOCKED"); self.runtime.checkpoint(mission); return mission
            plan=plan_event.payload["plan"]
            if plan.get("needs_more_context"):
                mission.transition("BLOCKED"); self.runtime.bus.publish(Event("ALERT","brain",{"mission_id":mission.mission_id,"reason":"more_context_required"},target="interface",correlation_id=mission.mission_id)); self.runtime.checkpoint(mission); return mission
            if mission.status=="DISCOVERING":self.runtime.advance(mission)
            if mission.status=="PLANNING":self.runtime.advance(mission)
            evidence=[]; actions=self.brain.action_events(mission,plan_event)
            if not actions:evidence.append({"ok":False,"error":"empty_plan"})
            for action in actions:
                if not self._control_gate(mission):return mission
                self.runtime.bus.publish(action)
                allowed,reason=self.governance.authorize(action)
                if not allowed:mission.transition("BLOCKED"); self.runtime.bus.publish(Event("ALERT","governance",{"mission_id":mission.mission_id,"reason":reason},target="interface",correlation_id=mission.mission_id)); self.runtime.checkpoint(mission); return mission
                result=self._execute(mission,action); self.runtime.bus.publish(result); evidence.append(result.payload)
                if not self._control_gate(mission):return mission
                if not result.payload.get("ok"):break
            if mission.status=="EXECUTING":self.runtime.advance(mission)
            verified,evaluation,observed=self._verify(mission,evidence)
            verification=Event("RESULT","autonomic_driver",{"ok":verified,"execution_ok":all(bool(x.get("ok")) for x in evidence),"evaluation_score":evaluation.score,"lesson":evaluation.lesson,"observed":observed,"evidence":evidence,"acceptance_criteria":mission.acceptance_criteria},target="autonomic",correlation_id=mission.mission_id); self.runtime.bus.publish(verification)
            if mission.status=="VERIFYING":self.runtime.advance(mission,verification)
            if mission.status=="SUCCEEDED":return mission
            replans+=1; working_context.update({"previous_plan":plan,"previous_evidence":evidence,"verification":verification.payload,"replan_attempt":replans})
            if self.memory is not None:working_context.update(self.memory.context_for(mission.objective))
            if replans>self.max_replans:mission.transition("FAILED"); self.runtime.checkpoint(mission); return mission
            if mission.status=="ADAPTING":self.runtime.advance(mission)
        return mission
