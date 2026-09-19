"""Governed public-web read adapter kept outside Falcon Brain."""
from __future__ import annotations
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from execution.adapters.base import ExecutionAdapter,ExecutionContext

class WebReadAdapter(ExecutionAdapter):
    name="web"
    def __init__(self,timeout_seconds:int=10,max_bytes:int=262144):
        self.timeout_seconds=timeout_seconds; self.max_bytes=max_bytes
    def available(self)->bool:return True
    def operations(self)->tuple[str,...]:return ("get",)
    def required_capability(self,action:str)->str|None:
        return "web.read" if action=="get" else None
    def operation_schema(self,action:str)->dict:
        return {"url":{"type":"string","required":True}} if action=="get" else {}
    def execute(self,action:str,*,execution_context:ExecutionContext|None=None,**kwargs):
        if action!="get": raise ValueError(f"unsupported_web_operation:{action}")
        url=str(kwargs.get("url", "")); parsed=urlparse(url)
        if parsed.scheme not in {"http","https"} or not parsed.hostname: raise ValueError("invalid_public_url")
        req=Request(url,method="GET",headers={"User-Agent":"Falcon/1.0 governed-web-read"})
        with urlopen(req,timeout=self.timeout_seconds) as response:
            body=response.read(self.max_bytes+1)
            if len(body)>self.max_bytes: raise ValueError("response_too_large")
            text=body.decode(response.headers.get_content_charset() or "utf-8",errors="replace")
            return {"execution_result_ok":True,"url":response.geturl(),"status":response.status,"content_type":response.headers.get_content_type(),"body":text,"operation_id":execution_context.operation_id if execution_context else None}
