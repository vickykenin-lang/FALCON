"""Local JSONL implementation of the Memory backend contract."""
import json
from pathlib import Path
from memory.base import MemoryBackend
class JsonlMemoryBackend(MemoryBackend):
    def __init__(self,path:str=".falcon/memory.jsonl"):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
    def append(self,item:dict)->None:
        with self.path.open("a",encoding="utf-8") as f:f.write(json.dumps(item,ensure_ascii=False)+"\n")
    def recent(self,limit:int)->list[dict]:
        if limit<=0:return []
        if not self.path.exists():return []
        lines=self.path.read_text(encoding="utf-8").splitlines(); return [json.loads(x) for x in lines[-limit:]]
