"""Validated content-addressed artifact facade."""
from dataclasses import asdict,dataclass
from hashlib import sha256
import re
from uuid import uuid4
from artifacts.base import ArtifactBackend
from artifacts.local import LocalArtifactBackend

DIGEST_RE=re.compile(r"^[0-9a-f]{64}$")
@dataclass(frozen=True)
class ArtifactRef:
    artifact_id:str; owner_module:str; uri:str; media_type:str; sha256:str; size_bytes:int; contract_version:str="1.0"
    def to_dict(self): return asdict(self)
class ArtifactStore:
    def __init__(self,root:str=".falcon/artifacts",backend:ArtifactBackend|None=None):
        self.backend=backend if backend is not None else LocalArtifactBackend(root)
    @staticmethod
    def _validate_metadata(owner_module:str,media_type:str)->None:
        if not isinstance(owner_module,str) or not owner_module.strip(): raise ValueError("owner_module_required")
        if not isinstance(media_type,str) or not media_type.strip(): raise ValueError("media_type_required")
    def put_bytes(self,data:bytes,owner_module:str,media_type:str="application/octet-stream")->ArtifactRef:
        if not isinstance(data,bytes): raise TypeError("artifact_data_must_be_bytes")
        self._validate_metadata(owner_module,media_type); digest=sha256(data).hexdigest(); self.backend.put(digest,data)
        return ArtifactRef(str(uuid4()),owner_module.strip(),f"artifact://sha256/{digest}",media_type.strip(),digest,len(data))
    def put_text(self,text:str,owner_module:str,media_type:str="text/plain; charset=utf-8")->ArtifactRef:
        if not isinstance(text,str): raise TypeError("artifact_text_must_be_string")
        return self.put_bytes(text.encode("utf-8"),owner_module,media_type)
    def get_bytes(self,ref:ArtifactRef)->bytes:
        if not isinstance(ref,ArtifactRef): raise TypeError("artifact_ref_required")
        if ref.contract_version!="1.0": raise ValueError("unsupported_artifact_contract")
        prefix="artifact://sha256/"
        if not ref.uri.startswith(prefix): raise ValueError("unsupported_artifact_uri")
        digest=ref.uri[len(prefix):]
        if not DIGEST_RE.fullmatch(digest): raise ValueError("invalid_artifact_digest")
        if not DIGEST_RE.fullmatch(ref.sha256) or digest!=ref.sha256: raise ValueError("artifact_reference_mismatch")
        data=self.backend.get(digest)
        if len(data)!=ref.size_bytes or sha256(data).hexdigest()!=digest: raise ValueError("artifact_integrity_failure")
        return data
    def get_text(self,ref:ArtifactRef)->str: return self.get_bytes(ref).decode("utf-8")
