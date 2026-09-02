"""GitHub execution adapter boundary.

Credentials are injected through environment/runtime configuration; never stored here.
The transport client is injected so Falcon core remains provider-independent.
"""
from execution.adapters.base import ExecutionAdapter,ExecutionContext

class GitHubAdapter(ExecutionAdapter):
    name="github"
    READ_OPERATIONS={"get_repository","get_file","list_tree","get_workflow_runs"}
    WRITE_OPERATIONS={"create_file","update_file","dispatch_workflow"}
    SCHEMAS={
        "get_repository":{"required":["repository"],"optional":[]},
        "get_file":{"required":["repository","path"],"optional":["ref","max_bytes"]},
        "list_tree":{"required":["repository"],"optional":["ref","recursive"]},
        "get_workflow_runs":{"required":["repository"],"optional":["per_page"]},
        "create_file":{"required":["repository","path","content","message"],"optional":["branch"]},
        "update_file":{"required":["repository","path","content","message","sha"],"optional":["branch"]},
        "dispatch_workflow":{"required":["repository","workflow"],"optional":["ref","inputs"]},
    }
    def __init__(self,client=None,write_path_prefixes=None):
        self.client=client; self.write_path_prefixes=tuple(str(x).strip().lstrip("/") for x in (write_path_prefixes or []) if str(x).strip())
    def available(self)->bool:return self.client is not None
    def operations(self)->tuple[str,...]:return tuple(sorted(self.READ_OPERATIONS|self.WRITE_OPERATIONS))
    def operation_schema(self,action:str)->dict:return dict(self.SCHEMAS.get(action,{}))
    def required_capability(self,action:str)->str|None:
        if action in self.READ_OPERATIONS:return "github.read"
        if action in self.WRITE_OPERATIONS:return "github.write"
        return None
    def _enforce_write_scope(self,action:str,kwargs:dict)->None:
        if action not in {"create_file","update_file"} or not self.write_path_prefixes:return
        path=str(kwargs.get("path","")).lstrip("/")
        if not path or not any(path.startswith(prefix) for prefix in self.write_path_prefixes):raise PermissionError("github_write_path_not_allowed")
    def execute(self,action:str,*,execution_context:ExecutionContext|None=None,**kwargs):
        if not self.client:raise RuntimeError("github_client_not_configured")
        if action not in self.READ_OPERATIONS|self.WRITE_OPERATIONS:raise ValueError(f"unsupported_github_action:{action}")
        self._enforce_write_scope(action,kwargs)
        fn=getattr(self.client,action,None)
        if not callable(fn):raise ValueError(f"unsupported_github_action:{action}")
        return fn(**kwargs)
