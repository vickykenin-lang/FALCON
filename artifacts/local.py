"""Local filesystem implementation of the artifact backend contract."""
from pathlib import Path
from artifacts.base import ArtifactBackend

class LocalArtifactBackend(ArtifactBackend):
    def __init__(self,root:str=".falcon/artifacts"):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
    def _path(self,digest:str)->Path: return self.root/digest[:2]/digest
    def put(self,digest:str,data:bytes)->None:
        path=self._path(digest); path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists(): path.write_bytes(data)
    def get(self,digest:str)->bytes: return self._path(digest).read_bytes()
