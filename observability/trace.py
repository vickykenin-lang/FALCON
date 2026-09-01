"""Provider-neutral structured tracing. Never records private reasoning."""
import json
from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from observability.base import TraceExporter

ALLOWED_STATUS={"RUNNING","OK","ERROR","CANCELLED","BLOCKED"}
SENSITIVE_KEYS={"chain_of_thought","reasoning","private_reasoning","thoughts","password","secret","token","api_key"}

def _safe_attributes(attributes:dict|None)->dict:
    if attributes is None: return {}
    if not isinstance(attributes,dict): raise TypeError("trace_attributes_must_be_object")
    return {str(k):v for k,v in attributes.items() if str(k).lower() not in SENSITIVE_KEYS}
@dataclass(frozen=True)
class TraceContext:
    trace_id:str; span_id:str; component:str; parent_span_id:str|None=None; operation:str|None=None; contract_version:str="1.0"
    def to_contract(self): return asdict(self)
@dataclass
class SpanRecord:
    context:TraceContext; started_at:str; ended_at:str|None=None; status:str="RUNNING"; attributes:dict=field(default_factory=dict); error:str|None=None
    def to_dict(self): return {"context":self.context.to_contract(),"started_at":self.started_at,"ended_at":self.ended_at,"status":self.status,"attributes":self.attributes,"error":self.error}
class JsonlTraceExporter(TraceExporter):
    def __init__(self,path:str=".falcon/traces.jsonl"):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
    def export(self,span:SpanRecord)->None:
        with self.path.open("a",encoding="utf-8") as f: f.write(json.dumps(span.to_dict(),ensure_ascii=False,default=str)+"\n")
class Tracer:
    def __init__(self,exporters=None): self.exporters=list(exporters or [])
    def add_exporter(self,exporter:TraceExporter)->None: self.exporters.append(exporter)
    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()
    def start(self,component:str,operation:str|None=None,parent:TraceContext|None=None,trace_id:str|None=None,attributes:dict|None=None)->SpanRecord:
        if not isinstance(component,str) or not component.strip(): raise ValueError("trace_component_required")
        context=TraceContext(trace_id or (parent.trace_id if parent else str(uuid4())),str(uuid4()),component.strip(),parent.span_id if parent else None,operation)
        return SpanRecord(context,self._now(),attributes=_safe_attributes(attributes))
    def finish(self,span:SpanRecord,status:str="OK",error:str|None=None,attributes:dict|None=None)->SpanRecord:
        if status not in ALLOWED_STATUS or status=="RUNNING": raise ValueError("invalid_terminal_trace_status")
        if span.ended_at is not None: raise ValueError("span_already_finished")
        span.ended_at=self._now(); span.status=status; span.error=str(error) if error is not None else None; span.attributes.update(_safe_attributes(attributes))
        for exporter in self.exporters: exporter.export(span)
        return span
    def child(self,parent:SpanRecord,component:str,operation:str|None=None,attributes:dict|None=None)->SpanRecord:
        return self.start(component,operation,parent.context,attributes=attributes)
