"""FALCON autonomous mission lifecycle.

This organ depends only on injected collaborators and shared contracts. Concrete
organ implementations are wired at the composition root.
"""
import json
from pathlib import Path
from contracts.models import Event, Mission
class Runtime:
    def __init__(self,bus,brain,memory=None,state_dir:str=".falcon"):
        self.bus=bus; self.brain=brain; self.memory=memory
        if self.memory is not None:self.bus.subscribe("*",self.memory.remember)
        self.alive=True; self.state_dir=Path(state_dir)
    def heartbeat(self)->Event:
        e=Event("HEARTBEAT","autonomic",{"status":"HEALTHY"},target="interface"); self.bus.publish(e); return e
    def accept(self,objective:str,source:str="founder",source_id:str|None=None,acceptance_criteria:dict|None=None,context:dict|None=None)->Mission:
        mission=Mission(objective=objective,acceptance_criteria=dict(acceptance_criteria or {}),context=dict(context or {})); mission.transition("DISCOVERING")
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
        p=self.state_dir/"checkpoints"; p.mkdir(parents=True,exist_ok=True); (p/f"{mission.mission_id}.json").write_text(json.dumps(mission.__dict__,indent=2),encoding="utf-8")
    def resume(self,mission_id:str)->Mission:
        data=json.loads((self.state_dir/"checkpoints"/f"{mission_id}.json").read_text(encoding="utf-8")); return Mission(**data)
