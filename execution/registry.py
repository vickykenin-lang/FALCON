"""Execution registry: capabilities are replaceable adapters."""
from typing import Any
from contracts.models import Event
from execution.adapters.base import ExecutionAdapter,ExecutionContext
class Executor:
    def __init__(self): self.adapters:dict[str,ExecutionAdapter]={}
    def register(self,adapter:ExecutionAdapter)->None:
        if not adapter.name:raise ValueError("adapter_name_required")
        self.adapters[adapter.name]=adapter
    def unregister(self,name:str)->None:self.adapters.pop(name,None)
    def replace(self,adapter:ExecutionAdapter)->None:self.register(adapter)
    def available(self)->dict[str,bool]:return {name:adapter.available() for name,adapter in self.adapters.items()}
    def capability_catalog(self)->list[dict]:
        catalog=[]
        for name,adapter in sorted(self.adapters.items()):
            for operation in adapter.operations():
                catalog.append({"adapter":name,"operation":operation,"capability":adapter.required_capability(operation),"available":bool(adapter.available()),"arguments":adapter.operation_schema(operation)})
        return catalog
    def execute(self,action:Event,operation_id:str|None=None)->Event:
        name=action.payload.get("adapter"); adapter=self.adapters.get(name)
        if adapter is None:return Event("FAILURE","execution",{"ok":False,"error":f"adapter_not_found:{name}"},correlation_id=action.correlation_id)
        if not adapter.available():return Event("FAILURE","execution",{"ok":False,"error":f"adapter_unavailable:{name}"},correlation_id=action.correlation_id)
        try:
            args:dict[str,Any]=action.payload.get("args",{}); operation=action.payload.get("operation") or action.payload.get("action")
            if not operation:raise ValueError("operation_required")
            declared=action.payload.get("capability"); required=adapter.required_capability(operation)
            if required and declared!=required:raise PermissionError(f"capability_mismatch:{required}")
            context=ExecutionContext(operation_id=operation_id,correlation_id=action.correlation_id) if operation_id else None
            data=adapter.execute(operation,execution_context=context,**args)
            return Event("RESULT","execution",{"ok":True,"adapter":name,"operation_id":operation_id,"data":data},correlation_id=action.correlation_id)
        except Exception as exc:return Event("FAILURE","execution",{"ok":False,"adapter":name,"operation_id":operation_id,"error":type(exc).__name__,"message":str(exc)},correlation_id=action.correlation_id)
    def cancel(self,adapter_name:str,operation_id:str)->bool:
        adapter=self.adapters.get(adapter_name); return bool(adapter and adapter.cancel(operation_id))
