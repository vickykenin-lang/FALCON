"""FALCON V1 contract models. Standard-library only."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

ALLOWED_TYPES = {"OBSERVATION","REQUEST","DECISION","ACTION","RESULT","FAILURE","ALERT","HEARTBEAT","MEMORY","LEARNING"}
MISSION_STATES = {"QUEUED","DISCOVERING","PLANNING","EXECUTING","VERIFYING","ADAPTING","SUCCEEDED","FAILED","BLOCKED","CANCELLED"}

@dataclass(frozen=True)
class Event:
    event_type: str
    source: str
    payload: dict[str, Any]
    target: Optional[str] = None
    correlation_id: Optional[str] = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    contract_version: str = "1.0"

    def __post_init__(self):
        if self.event_type not in ALLOWED_TYPES: raise ValueError(f"Unsupported event_type: {self.event_type}")
        if not self.source: raise ValueError("source is required")
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass
class Mission:
    objective: str
    mission_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "QUEUED"
    attempts: int = 0
    checkpoint: dict[str, Any] = field(default_factory=dict)
    acceptance_criteria: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    def transition(self,state:str)->None:
        if state not in MISSION_STATES: raise ValueError(f"Unsupported mission state: {state}")
        self.status=state
