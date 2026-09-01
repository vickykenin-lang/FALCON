"""Durable JSONL memory with bounded retrieval for intelligence context."""
import json
from pathlib import Path
from contracts.models import Event


class MemoryStore:
    def __init__(self, path: str = ".falcon/memory.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def remember(self, event: Event) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def recent(self, limit: int = 20) -> list[dict]:
        if not self.path.exists(): return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(x) for x in lines[-limit:]]

    def recall(self, objective: str, limit: int = 12) -> list[dict]:
        """Retrieve bounded relevant evidence without exposing storage internals."""
        if not self.path.exists(): return []
        terms={x.lower() for x in objective.split() if len(x)>2}
        scored=[]
        for index,item in enumerate(self.recent(200)):
            text=json.dumps(item,ensure_ascii=False).lower()
            score=sum(1 for term in terms if term in text)
            if score:
                scored.append((score,index,item))
        scored.sort(key=lambda x:(x[0],x[1]),reverse=True)
        return [item for _,_,item in scored[:limit]]

    def context_for(self, objective: str, limit: int = 12) -> dict:
        memories=self.recall(objective,limit)
        return {"relevant_memory":memories,"memory_count":len(memories)}
