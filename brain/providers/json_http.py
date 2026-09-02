"""Generic JSON-over-HTTP intelligence adapter.

Provider-specific endpoints remain outside Falcon's Brain. The remote service
must return Falcon's structured plan object, keeping model vendors replaceable.
"""
import json
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from brain.providers.base import IntelligenceProvider

class JsonHttpProvider(IntelligenceProvider):
    def __init__(self,endpoint:str,headers:dict|None=None,timeout:float=30.0,opener=None):
        if not isinstance(endpoint,str) or not endpoint.startswith(("http://","https://")): raise ValueError("valid_http_endpoint_required")
        if timeout<=0: raise ValueError("timeout_must_be_positive")
        self.endpoint=endpoint; self.headers=dict(headers or {}); self.timeout=timeout; self.opener=opener or urlopen
    def decide(self,objective:str,context:dict)->dict:
        payload=json.dumps({"objective":objective,"context":context,"contract_version":"1.0"}).encode("utf-8")
        headers={"Content-Type":"application/json","Accept":"application/json",**self.headers}
        request=Request(self.endpoint,data=payload,headers=headers,method="POST")
        try:
            response=self.opener(request,timeout=self.timeout); raw=response.read()
        except HTTPError as exc: raise RuntimeError(f"intelligence_http_error:{exc.code}") from exc
        except URLError as exc: raise RuntimeError("intelligence_provider_unreachable") from exc
        try: data=json.loads(raw)
        except (TypeError,ValueError) as exc: raise RuntimeError("intelligence_invalid_json") from exc
        if not isinstance(data,dict): raise RuntimeError("intelligence_response_must_be_object")
        return data
