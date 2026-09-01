"""Provider-neutral tracing for Falcon.

Falcon owns its trace model and can fan traces out to replaceable exporters.
No vendor tracing SDK is allowed in this core module.
"""
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

@dataclass(frozen=True)
class TraceContext:
    trace_id:str
    span_id:str
    component:str
    parent_span_id:str|None=None
    operation:str|None=None
    contract_version:str="1.0"

@dataclass
class SpanRecord:
    context:TraceContext
    started_at:str
    ended_at:str|None=None
    status:str="RUNNING"
    attributes:dict=field(default_factory=dict)
    error:str|None=None
    def to_dict(self):
        data=asdict(self); data["context"]=asdict(self.context); return data

class JsonlTraceExporter:
    def __init__(self,path:str=".falcon/traces.jsonl"):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
    def export(self,span:SpanRecord):
        with self.path.open("a",encoding="utf-8") as f: f.write(json.dumps(span.to_dict(),ensure_ascii=False)+"\n")

class Tracer:
    def __init__(self,exporters=None): self.exporters=list(exporters or [])
    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()
    def start(self,component:str,operation:str|None=None,parent:TraceContext|None=None,trace_id:str|None=None,attributes:dict|None=None)->SpanRecord:
        context=TraceContext(trace_id or (parent.trace_id if parent else str(uuid4())),str(uuid4()),component,parent.span_id if parent else None,operation)
        return SpanRecord(context,self._now(),attributes=dict(attributes or {}))
    def finish(self,span:SpanRecord,status:str="OK",error:str|None=None,attributes:dict|None=None)->SpanRecord:
        span.ended_at=self._now(); span.status=status; span.error=error
        if attributes: span.attributes.update(attributes)
        for exporter in self.exporters: exporter.export(span)
        return span
    def child(self,parent:SpanRecord,component:str,operation:str|None=None,attributes:dict|None=None)->SpanRecord:
        return self.start(component,operation,parent.context,attributes=attributes)
