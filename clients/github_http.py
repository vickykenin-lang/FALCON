"""Dependency-free GitHub REST transport used by the replaceable GitHub adapter."""
import base64
import json
from urllib.error import HTTPError,URLError
from urllib.parse import quote,urlencode
from urllib.request import Request,urlopen

class GitHubHttpClient:
    def __init__(self,token:str|None=None,base_url:str="https://api.github.com",timeout:float=30.0,opener=None):
        if timeout<=0:raise ValueError("timeout_must_be_positive")
        self.token=(token or "").strip() or None; self.base_url=base_url.rstrip("/"); self.timeout=timeout; self.opener=opener or urlopen
    @staticmethod
    def _repo(repository:str)->str:
        parts=str(repository).strip().split("/")
        if len(parts)!=2 or not all(parts):raise ValueError("repository_must_be_owner_name")
        return f"{quote(parts[0],safe='')}/{quote(parts[1],safe='')}"
    def _request(self,method:str,path:str,payload:dict|None=None):
        body=None if payload is None else json.dumps(payload).encode("utf-8")
        headers={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"FALCON/1.0"}
        if body is not None:headers["Content-Type"]="application/json"
        if self.token:headers["Authorization"]=f"Bearer {self.token}"
        request=Request(f"{self.base_url}{path}",data=body,headers=headers,method=method)
        try:raw=self.opener(request,timeout=self.timeout).read()
        except HTTPError as exc:raise RuntimeError(f"github_http_error:{exc.code}") from exc
        except URLError as exc:raise RuntimeError("github_unreachable") from exc
        if not raw:return {}
        try:return json.loads(raw)
        except (TypeError,ValueError) as exc:raise RuntimeError("github_invalid_json") from exc
    def get_repository(self,repository:str):
        return self._request("GET",f"/repos/{self._repo(repository)}")
    def get_file(self,repository:str,path:str,ref:str|None=None,max_bytes:int=524288):
        clean=quote(str(path).lstrip("/"),safe="/")
        query=f"?{urlencode({'ref':ref})}" if ref else ""
        data=self._request("GET",f"/repos/{self._repo(repository)}/contents/{clean}{query}")
        if isinstance(data,dict) and data.get("encoding")=="base64" and isinstance(data.get("content"),str):
            decoded=base64.b64decode(data["content"],validate=False)
            if len(decoded)>max_bytes:raise ValueError("github_file_too_large")
            data=dict(data); data["content_text"]=decoded.decode("utf-8",errors="replace"); data.pop("content",None)
        return data
    def list_tree(self,repository:str,ref:str="main",recursive:bool=True):
        suffix=f"?recursive={1 if recursive else 0}"
        return self._request("GET",f"/repos/{self._repo(repository)}/git/trees/{quote(ref,safe='')}{suffix}")
    def get_workflow_runs(self,repository:str,per_page:int=10):
        if not 1<=int(per_page)<=100:raise ValueError("per_page_out_of_range")
        return self._request("GET",f"/repos/{self._repo(repository)}/actions/runs?{urlencode({'per_page':int(per_page)})}")
    def _require_write(self):
        if not self.token:raise PermissionError("github_token_required_for_write")
    def create_file(self,repository:str,path:str,content:str,message:str,branch:str|None=None):
        self._require_write(); payload={"message":message,"content":base64.b64encode(content.encode()).decode()}
        if branch:payload["branch"]=branch
        clean=quote(str(path).lstrip("/"),safe="/")
        return self._request("PUT",f"/repos/{self._repo(repository)}/contents/{clean}",payload)
    def update_file(self,repository:str,path:str,content:str,message:str,sha:str,branch:str|None=None):
        self._require_write(); payload={"message":message,"content":base64.b64encode(content.encode()).decode(),"sha":sha}
        if branch:payload["branch"]=branch
        clean=quote(str(path).lstrip("/"),safe="/")
        return self._request("PUT",f"/repos/{self._repo(repository)}/contents/{clean}",payload)
    def dispatch_workflow(self,repository:str,workflow:str,ref:str="main",inputs:dict|None=None):
        self._require_write()
        workflow_id=quote(str(workflow).strip(),safe="")
        if not workflow_id:raise ValueError("workflow_required")
        payload={"ref":str(ref or "main").strip() or "main"}
        if inputs is not None:
            if not isinstance(inputs,dict):raise TypeError("workflow_inputs_must_be_object")
            payload["inputs"]=inputs
        return self._request("POST",f"/repos/{self._repo(repository)}/actions/workflows/{workflow_id}/dispatches",payload)
