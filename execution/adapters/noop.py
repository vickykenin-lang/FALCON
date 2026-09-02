"""Safe local adapter for Falcon acceptance tests and offline autonomous runs."""
from execution.adapters.base import ExecutionAdapter,ExecutionContext

class NoopAdapter(ExecutionAdapter):
    name="noop"
    def available(self)->bool:return True
    def operations(self)->tuple[str,...]:return ("inspect",)
    def required_capability(self,action:str)->str|None:
        return "noop.inspect" if action=="inspect" else None
    def execute(self,action:str,*,execution_context:ExecutionContext|None=None,**kwargs):
        if action!="inspect": raise ValueError(f"unsupported_noop_operation:{action}")
        return {"execution_result_ok":True,"inspected":True,"objective":kwargs.get("objective"),"operation_id":execution_context.operation_id if execution_context else None}
