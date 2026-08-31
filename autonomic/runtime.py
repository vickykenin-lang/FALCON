"""FALCON autonomous mission runtime with resumable lifecycle."""
import json
from pathlib import Path
from contracts.models import Event, Mission
from nervous_system.bus import EventBus
from brain.engine import Brain
from memory.store import MemoryStore


class Runtime:
    def __init__(self, state_dir: str = ".falcon"):
        self.bus, self.brain, self.memory = EventBus(), Brain(), MemoryStore()
        self.bus.subscribe("*", self.memory.remember)
        self.alive = True
        self.state_dir = Path(state_dir)

    def heartbeat(self) -> Event:
        e = Event("HEARTBEAT", "autonomic", {"status": "HEALTHY"}, target="interface")
        self.bus.publish(e)
        return e

    def accept(self, objective: str) -> Mission:
        mission = Mission(objective=objective)
        mission.transition("DISCOVERING")
        self.bus.publish(Event("REQUEST", "founder", {"objective": objective, "mission_id": mission.mission_id}, target="brain", correlation_id=mission.mission_id))
        self.bus.publish(self.brain.understand(mission))
        self.checkpoint(mission)
        return mission

    def advance(self, mission: Mission, result: Event | None = None) -> Mission:
        """Advance one observable lifecycle step; callers provide tool results explicitly."""
        transitions = {
            "DISCOVERING": "PLANNING",
            "PLANNING": "EXECUTING",
            "EXECUTING": "VERIFYING",
        }
        if mission.status in transitions:
            mission.transition(transitions[mission.status])
        elif mission.status == "VERIFYING":
            ok = bool(result and result.payload.get("ok"))
            mission.transition("SUCCEEDED" if ok else "ADAPTING")
        elif mission.status == "ADAPTING":
            mission.attempts += 1
            mission.transition("PLANNING")
        self.bus.publish(Event("HEARTBEAT", "autonomic", {"mission_id": mission.mission_id, "mission_status": mission.status}, target="interface", correlation_id=mission.mission_id))
        self.checkpoint(mission)
        return mission

    def checkpoint(self, mission: Mission) -> None:
        p = self.state_dir / "checkpoints"
        p.mkdir(parents=True, exist_ok=True)
        (p / f"{mission.mission_id}.json").write_text(json.dumps(mission.__dict__, indent=2), encoding="utf-8")

    def resume(self, mission_id: str) -> Mission:
        data = json.loads((self.state_dir / "checkpoints" / f"{mission_id}.json").read_text(encoding="utf-8"))
        return Mission(**data)
