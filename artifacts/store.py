"""Content-addressed local artifact store behind Falcon's V1 artifact contract.

Large outputs stay outside events/memory; other organs exchange only immutable
artifact references. A cloud/object-store backend can replace this implementation.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

@dataclass(frozen=True)
class ArtifactRef:
    artifact_id:str
    owner_module:str
    uri:str
    media_type:str
    sha256:str
    size_bytes:int
    contract_version:str="1.0"
    def to_dict(self): return asdict(self)

class ArtifactStore:
    def __init__(self,root:str=".falcon/artifacts"):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
    def put_bytes(self,data:bytes,owner_module:str,media_type:str="application/octet-stream")->ArtifactRef:
        digest=sha256(data).hexdigest(); path=self.root/digest[:2]/digest; path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists(): path.write_bytes(data)
        return ArtifactRef(str(uuid4()),owner_module,f"artifact://sha256/{digest}",media_type,digest,len(data))
    def put_text(self,text:str,owner_module:str,media_type:str="text/plain; charset=utf-8")->ArtifactRef:
        return self.put_bytes(text.encode("utf-8"),owner_module,media_type)
    def get_bytes(self,ref:ArtifactRef)->bytes:
        if ref.contract_version!="1.0": raise ValueError("unsupported_artifact_contract")
        prefix="artifact://sha256/"
        if not ref.uri.startswith(prefix): raise ValueError("unsupported_artifact_uri")
        digest=ref.uri[len(prefix):]; data=(self.root/digest[:2]/digest).read_bytes()
        if sha256(data).hexdigest()!=ref.sha256: raise ValueError("artifact_integrity_failure")
        return data
    def get_text(self,ref:ArtifactRef)->str: return self.get_bytes(ref).decode("utf-8")
