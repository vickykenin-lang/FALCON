"""GitHub execution adapter boundary.

Credentials are injected through environment/runtime configuration; never stored here.
The transport client is injected so Falcon core remains provider-independent.
"""
from execution.adapters.base import ExecutionAdapter,ExecutionContext

class GitHubAdapter(ExecutionAdapter):
    name="github"
    READ_OPERATIONS={"get_repository","get_file","list_tree","get_workflow_runs"}
    WRITE_OPERATIONS={"create_file","update_file","dispatch_workflow"}
    def __init__(self,client=None): self.client=client
    def available(self)->bool:return self.client is not None
    def operations(self)->tuple[str,...]:return tuple(sorted(self.READ_OPERATIONS|self.WRITE_OPERATIONS))
    def required_capability(self,action:str)->str|None:
        if action in self.READ_OPERATIONS:return "github.read"
        if action in self.WRITE_OPERATIONS:return "github.write"
        return None
    def execute(self,action:str,*,execution_context:ExecutionContext|None=None,**kwargs):
        if not self.client:raise RuntimeError("github_client_not_configured")
        if action not in self.READ_OPERATIONS|self.WRITE_OPERATIONS:raise ValueError(f"unsupported_github_action:{action}")
        fn=getattr(self.client,action,None)
        if not callable(fn):raise ValueError(f"unsupported_github_action:{action}")
        return fn(**kwargs)
