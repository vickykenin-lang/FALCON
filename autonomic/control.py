"""Mission pause/resume/cancel state with replaceable in-flight cancellation hook."""
from dataclasses import dataclass
@dataclass
class ControlState:
    paused:bool=False; cancelled:bool=False; reason:str|None=None; active_adapter:str|None=None; active_operation_id:str|None=None
class MissionControl:
    def __init__(self,cancel_operation=None): self._states:dict[str,ControlState]={}; self._cancel_operation=cancel_operation
    def state(self,mission_id:str)->ControlState: return self._states.setdefault(mission_id,ControlState())
    def pause(self,mission_id:str,reason:str|None=None):
        s=self.state(mission_id); s.paused=True; s.reason=reason; return s
    def resume(self,mission_id:str):
        s=self.state(mission_id); s.paused=False; s.reason=None; return s
    def begin_operation(self,mission_id:str,adapter:str,operation_id:str)->None:
        s=self.state(mission_id); s.active_adapter=adapter; s.active_operation_id=operation_id
    def end_operation(self,mission_id:str,operation_id:str|None=None)->None:
        s=self.state(mission_id)
        if operation_id is None or s.active_operation_id==operation_id: s.active_adapter=None; s.active_operation_id=None
    def cancel(self,mission_id:str,reason:str|None=None):
        s=self.state(mission_id); s.cancelled=True; s.paused=False; s.reason=reason
        if self._cancel_operation and s.active_adapter and s.active_operation_id: self._cancel_operation(s.active_adapter,s.active_operation_id)
        return s
    def can_run(self,mission_id:str)->bool:
        s=self.state(mission_id); return not s.paused and not s.cancelled
