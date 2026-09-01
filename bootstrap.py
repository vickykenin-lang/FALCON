"""Falcon composition root: concrete organ wiring lives only here."""
from autonomic.control import MissionControl
from autonomic.runtime import Runtime
from brain.engine import Brain
from memory.store import MemoryStore
from nervous_system.bus import EventBus

def build_runtime(state_dir:str=".falcon",brain=None,memory=None,bus=None,control=None,executor=None)->Runtime:
    if bus is None: bus=EventBus()
    if brain is None: brain=Brain()
    if memory is None: memory=MemoryStore(f"{state_dir}/memory.jsonl")
    if control is None: control=MissionControl(cancel_operation=executor.cancel if executor is not None else None)
    runtime=Runtime(bus=bus,brain=brain,memory=memory,state_dir=state_dir)
    runtime.control=control; runtime.executor=executor
    return runtime
