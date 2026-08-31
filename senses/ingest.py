"""Senses subsystem: normalize external observations."""
from datetime import datetime, timezone
from uuid import uuid4


def observe(source: str, payload: dict, target: str = "brain") -> dict:
    return {
        "event_id": str(uuid4()),
        "event_type": "OBSERVATION",
        "source": source,
        "target": target,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": None,
        "payload": payload,
        "contract_version": "1.0",
    }
