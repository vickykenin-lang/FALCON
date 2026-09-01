"""Constrained local subprocess backend for explicitly allow-listed commands.

This is not container/OS security isolation. It provides bounded local process
execution plus request-scoped cancellation behind the replaceable Sandbox API.
"""
import subprocess,threading
from execution.sandbox import SandboxBackend,SandboxRequest,SandboxResult
class LocalSandboxBackend(SandboxBackend):
    name="local"
    def __init__(self,allowed_commands:set[str]|None=None):
        self.allowed_commands=set(allowed_commands or []); self._processes:dict[str,subprocess.Popen]={}; self._lock=threading.Lock()
    def run(self,request:SandboxRequest)->SandboxResult:
        if request.network:return SandboxResult(False,error="network_not_supported",request_id=request.request_id)
        if request.command not in self.allowed_commands:return SandboxResult(False,error="command_not_allowed",request_id=request.request_id)
        argv=[request.command]+[str(x) for x in request.args.get("argv",[])]
        try:
            process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            with self._lock:self._processes[request.request_id]=process
            try:
                stdout,stderr=process.communicate(timeout=request.timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill(); stdout,stderr=process.communicate(); return SandboxResult(False,output={"stdout":stdout,"stderr":stderr,"returncode":process.returncode},error="timeout",request_id=request.request_id)
            cancelled=process.returncode is not None and process.returncode<0
            return SandboxResult(process.returncode==0,output={"stdout":stdout,"stderr":stderr,"returncode":process.returncode},error=None if process.returncode==0 else ("cancelled" if cancelled else "nonzero_exit"),request_id=request.request_id)
        except Exception as exc:return SandboxResult(False,error=f"{type(exc).__name__}:{exc}",request_id=request.request_id)
        finally:
            with self._lock:self._processes.pop(request.request_id,None)
    def cancel(self,request_id:str)->bool:
        with self._lock:process=self._processes.get(request_id)
        if process is None or process.poll() is not None:return False
        process.kill(); return True
