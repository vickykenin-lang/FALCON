import tempfile,unittest
from contracts.models import Event
from memory.base import MemoryBackend
from memory.store import MemoryStore

class FakeMemoryBackend(MemoryBackend):
    def __init__(self): self.items=[]
    def append(self,item): self.items.append(item)
    def recent(self,limit): return self.items[-limit:] if limit>0 else []

class MemoryReplaceabilityTests(unittest.TestCase):
    def test_memory_store_accepts_replaceable_backend(self):
        backend=FakeMemoryBackend(); store=MemoryStore(backend=backend)
        store.remember(Event("RESULT","test",{"objective":"repair scheduler","ok":True}))
        self.assertEqual(len(backend.items),1)
        self.assertTrue(store.recall("repair scheduler"))

    def test_context_semantics_survive_backend_swap(self):
        backend=FakeMemoryBackend(); store=MemoryStore(backend=backend)
        store.remember(Event("RESULT","test",{"objective":"recover service","lesson":"retry alternative"}))
        context=store.context_for("recover service")
        self.assertEqual(context["memory_count"],1)
        self.assertEqual(context["relevant_memory"][0]["payload"]["lesson"],"retry alternative")

    def test_jsonl_default_backend_regression(self):
        with tempfile.TemporaryDirectory() as d:
            store=MemoryStore(f"{d}/memory.jsonl")
            store.remember(Event("MEMORY","test",{"value":7}))
            self.assertEqual(store.recent(1)[0]["payload"]["value"],7)

if __name__=="__main__": unittest.main()
