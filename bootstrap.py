"""Falcon composition root.

Only this boundary knows concrete organ implementations. Replacing an organ
should normally require changing wiring here, not consumers in other organs.
"""
from autonomic.runtime import Runtime
from brain.engine import Brain
from memory.store import MemoryStore
from nervous_system.bus import EventBus


def build_runtime(state_dir: str = ".falcon", brain=None, memory=None, bus=None) -> Runtime:
    bus = bus or EventBus()
    brain = brain or Brain()
    memory = memory or MemoryStore(f"{state_dir}/memory.jsonl")
    return Runtime(bus=bus, brain=brain, memory=memory, state_dir=state_dir)
