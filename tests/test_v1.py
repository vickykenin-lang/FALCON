import tempfile, os, unittest
from contracts.models import Event
from nervous_system.bus import EventBus
from memory.store import MemoryStore
from autonomic.runtime import Runtime

class FalconV1Tests(unittest.TestCase):
    def test_event_bus(self):
        bus=EventBus(); seen=[]; bus.subscribe("HEARTBEAT", seen.append)
        e=Event("HEARTBEAT","test",{"status":"HEALTHY"}); bus.publish(e)
        self.assertEqual(seen[0].event_id,e.event_id)
    def test_memory(self):
        with tempfile.TemporaryDirectory() as d:
            m=MemoryStore(os.path.join(d,"m.jsonl")); m.remember(Event("MEMORY","test",{"x":1}))
            self.assertEqual(m.recent(1)[0]["payload"]["x"],1)
    def test_runtime_mission(self):
        with tempfile.TemporaryDirectory() as d:
            old=os.getcwd(); os.chdir(d)
            try:
                r=Runtime(); m=r.accept("test objective")
                self.assertEqual(m.status,"ACTIVE"); self.assertGreaterEqual(len(r.bus.history),2)
            finally: os.chdir(old)
if __name__=="__main__": unittest.main()
