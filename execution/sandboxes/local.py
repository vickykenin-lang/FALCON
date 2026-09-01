"""Constrained local sandbox backend for explicitly allow-listed commands."""
import subprocess
from execution.sandbox import SandboxBackend, SandboxRequest, SandboxResult

class LocalSandboxBackend(SandboxBackend):
    name="local"
    def __init__(self, allowed_commands:set[str]|None=None): self.allowed_commands=set(allowed_commands or [])
    def run(self,request:SandboxRequest)->SandboxResult:
        if request.network: return SandboxResult(False,error="network_not_supported",request_id=request.request_id)
        if request.command not in self.allowed_commands: return SandboxResult(False,error="command_not_allowed",request_id=request.request_id)
        argv=[request.command]+[str(x) for x in request.args.get("argv",[])]
        try:
            completed=subprocess.run(argv,capture_output=True,text=True,timeout=request.timeout_seconds,check=False)
            return SandboxResult(completed.returncode==0,output={"stdout":completed.stdout,"stderr":completed.stderr,"returncode":completed.returncode},error=None if completed.returncode==0 else "nonzero_exit",request_id=request.request_id)
        except subprocess.TimeoutExpired:
            return SandboxResult(False,error="timeout",request_id=request.request_id)
        except Exception as exc:
            return SandboxResult(False,error=f"{type(exc).__name__}:{exc}",request_id=request.request_id)
