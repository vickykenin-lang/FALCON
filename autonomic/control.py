"""Mission cancellation/pause/resume state independent of execution providers."""
from dataclasses import dataclass

@dataclass
class ControlState:
    paused: bool=False
    cancelled: bool=False
    reason: str|None=None

class MissionControl:
    def __init__(self): self._states:dict[str,ControlState]={}
    def state(self,mission_id:str)->ControlState: return self._states.setdefault(mission_id,ControlState())
    def pause(self,mission_id:str,reason:str|None=None):
        s=self.state(mission_id); s.paused=True; s.reason=reason; return s
    def resume(self,mission_id:str):
        s=self.state(mission_id); s.paused=False; s.reason=None; return s
    def cancel(self,mission_id:str,reason:str|None=None):
        s=self.state(mission_id); s.cancelled=True; s.paused=False; s.reason=reason; return s
    def can_run(self,mission_id:str)->bool:
        s=self.state(mission_id); return not s.paused and not s.cancelled
