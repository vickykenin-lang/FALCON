"""Secret-safe live mission observability projection for Founder control."""
from __future__ import annotations
from dataclasses import asdict,is_dataclass

_SECRET_KEYS={"secret","token","password","api_key","apikey","authorization","credential","credentials"}

def _safe(value):
    if isinstance(value,dict):
        return {k:("[REDACTED]" if k.lower() in _SECRET_KEYS else _safe(v)) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [_safe(v) for v in value]
    if is_dataclass(value):return _safe(asdict(value))
    return value

class LiveMissionView:
    """Builds a read-only, secret-safe snapshot from mission/control/event evidence."""
    def snapshot(self,mission,*,control=None,events=(),plan=None,provider=None):
        state=control.state(mission.mission_id) if control is not None else None
        timeline=[]
        for event in events:
            payload=getattr(event,"payload",{}) or {}
            timeline.append({
                "type":getattr(event,"event_type",None),
                "source":getattr(event,"source",None),
                "payload":_safe(payload),
            })
        reason=None
        for item in reversed(timeline):
            if item["type"] in {"FAILURE","ALERT"}:
                reason=item["payload"].get("reason") or item["payload"].get("error"); break
        status=mission.status
        return {
            "mission_id":mission.mission_id,
            "objective":mission.objective,
            "status":status,
            "verified_success":status=="SUCCEEDED",
            "planned_or_attempted":status!="SUCCEEDED",
            "current_plan":_safe(plan),
            "current_provider":_safe(provider),
            "control":_safe(state) if state is not None else None,
            "actionable_reason":reason,
            "timeline":timeline,
        }
