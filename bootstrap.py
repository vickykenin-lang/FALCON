"""Falcon composition root.

Only this boundary knows concrete organ implementations. Replacing an organ
should normally require changing wiring here, not consumers in other organs.
"""
from autonomic.control import MissionControl
from autonomic.runtime import Runtime
from brain.engine import Brain
from memory.store import MemoryStore
from nervous_system.bus import EventBus

def build_runtime(state_dir:str=".falcon",brain=None,memory=None,bus=None,control=None)->Runtime:
    if bus is None: bus=EventBus()
    if brain is None: brain=Brain()
    if memory is None: memory=MemoryStore(f"{state_dir}/memory.jsonl")
    runtime=Runtime(bus=bus,brain=brain,memory=memory,state_dir=state_dir)
    runtime.control=control if control is not None else MissionControl()
    return runtime
