"""FALCON autonomous mission lifecycle.

This organ depends only on injected collaborators and shared contracts. Concrete
organ implementations are wired at the composition root.
"""
from contracts.models import Event, Mission
from autonomic.state import JsonMissionStateBackend

TERMINAL_STATES={"SUCCEEDED","FAILED","BLOCKED","CANCELLED"}

class Runtime:
    def __init__(self,bus,brain,memory=None,state_dir:str=".falcon",state_backend=None):
        self.bus=bus; self.brain=brain; self.memory=memory
        if self.memory is not None:self.bus.subscribe("*",self.memory.remember)
        self.alive=True; self.state_dir=state_dir
        self.state_backend=state_backend if state_backend is not None else JsonMissionStateBackend(f"{state_dir}/state")
    def heartbeat(self)->Event:
        e=Event("HEARTBEAT","autonomic",{"status":"HEALTHY"},target="interface"); self.bus.publish(e); return e
    def accept(self,objective:str,source:str="founder",source_id:str|None=None,acceptance_criteria:dict|None=None,context:dict|None=None)->Mission:
        mission=Mission(objective=objective,acceptance_criteria=dict(acceptance_criteria or {}),context=dict(context or {})); mission.transition("DISCOVERING")
        if source_id:
            resolved=self.state_backend.claim_source(source,str(source_id),mission.mission_id)
            if resolved!=mission.mission_id:
                existing=self.state_backend.get_mission(resolved)
                if not existing:raise RuntimeError("claimed_mission_not_materialized")
                return Mission(**existing)
        payload={"objective":objective,"mission_id":mission.mission_id,"acceptance_criteria":mission.acceptance_criteria}
        if source_id:payload["source_id"]=source_id
        self.bus.publish(Event("REQUEST",source,payload,target="brain",correlation_id=mission.mission_id)); self.bus.publish(self.brain.understand(mission)); self.checkpoint(mission); return mission
    def advance(self,mission:Mission,result:Event|None=None)->Mission:
        transitions={"DISCOVERING":"PLANNING","PLANNING":"EXECUTING","EXECUTING":"VERIFYING"}
        if mission.status in transitions:mission.transition(transitions[mission.status])
        elif mission.status=="VERIFYING":mission.transition("SUCCEEDED" if bool(result and result.payload.get("ok")) else "ADAPTING")
        elif mission.status=="ADAPTING":mission.attempts+=1; mission.transition("PLANNING")
        self.bus.publish(Event("HEARTBEAT","autonomic",{"mission_id":mission.mission_id,"mission_status":mission.status},target="interface",correlation_id=mission.mission_id)); self.checkpoint(mission); return mission
    def checkpoint(self,mission:Mission)->None:
        self.state_backend.put_mission(mission.mission_id,dict(mission.__dict__))
    def resume(self,mission_id:str)->Mission:
        data=self.state_backend.get_mission(mission_id)
        if not data:raise FileNotFoundError(f"mission_checkpoint_not_found:{mission_id}")
        return Mission(**data)
    def claim_operation(self,operation_key:str,metadata:dict)->dict:
        return self.state_backend.claim_operation(operation_key,metadata)
    def complete_operation(self,operation_key:str,result:dict)->None:
        self.state_backend.complete_operation(operation_key,result)
