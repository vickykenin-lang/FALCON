"""Durable JSONL memory. Storage can later be swapped without changing callers."""
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
