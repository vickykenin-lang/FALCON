"""Memory facade: retrieval semantics are independent of persistence backend."""
import json
from contracts.models import Event
from memory.jsonl import JsonlMemoryBackend
class MemoryStore:
    def __init__(self,path:str=".falcon/memory.jsonl",backend=None):
        self.backend=backend if backend is not None else JsonlMemoryBackend(path)
    def remember(self,event:Event)->None:self.backend.append(event.to_dict())
    def recent(self,limit:int=20)->list[dict]:return self.backend.recent(limit)
    def recall(self,objective:str,limit:int=12)->list[dict]:
        terms={x.lower() for x in objective.split() if len(x)>2}; scored=[]
        for index,item in enumerate(self.recent(200)):
            text=json.dumps(item,ensure_ascii=False).lower(); score=sum(1 for term in terms if term in text)
            if score:scored.append((score,index,item))
        scored.sort(key=lambda x:(x[0],x[1]),reverse=True); return [item for _,_,item in scored[:limit]]
    def context_for(self,objective:str,limit:int=12)->dict:
        memories=self.recall(objective,limit); return {"relevant_memory":memories,"memory_count":len(memories)}
