"""FALCON autonomous mission runtime."""
import json, time
from pathlib import Path
from contracts.models import Event, Mission
from nervous_system.bus import EventBus
from brain.engine import Brain
from memory.store import MemoryStore

class Runtime:
    def __init__(self):
        self.bus, self.brain, self.memory = EventBus(), Brain(), MemoryStore()
        self.bus.subscribe("*", self.memory.remember)
        self.alive = True

    def heartbeat(self) -> Event:
        e = Event("HEARTBEAT", "autonomic", {"status": "HEALTHY"}, target="interface")
        self.bus.publish(e); return e

    def accept(self, objective: str) -> Mission:
        mission = Mission(objective=objective, status="ACTIVE")
        self.bus.publish(Event("REQUEST", "founder", {"objective": objective, "mission_id": mission.mission_id}, target="brain", correlation_id=mission.mission_id))
        self.bus.publish(self.brain.understand(mission))
        self.checkpoint(mission)
        return mission

    def checkpoint(self, mission: Mission) -> None:
        p = Path(".falcon/checkpoints"); p.mkdir(parents=True, exist_ok=True)
        (p / f"{mission.mission_id}.json").write_text(json.dumps(mission.__dict__, indent=2), encoding="utf-8")
