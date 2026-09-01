import tempfile, os, unittest
from datetime import datetime, timedelta, timezone
from contracts.models import Event
from nervous_system.bus import EventBus
from memory.store import MemoryStore
from autonomic.runtime import Runtime
from scheduler.engine import Schedule, Scheduler

class FalconV1Tests(unittest.TestCase):
    def test_event_bus(self):
        bus=EventBus(); seen=[]; bus.subscribe("HEARTBEAT", seen.append)
        e=Event("HEARTBEAT","test",{"status":"HEALTHY"}); bus.publish(e)
        self.assertEqual(seen[0].event_id,e.event_id)

    def test_memory(self):
        with tempfile.TemporaryDirectory() as d:
            m=MemoryStore(os.path.join(d,"m.jsonl")); m.remember(Event("MEMORY","test",{"x":1}))
            self.assertEqual(m.recent(1)[0]["payload"]["x"],1)

    def test_runtime_mission_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(state_dir=d); m=r.accept("test objective")
            self.assertEqual(m.status,"DISCOVERING")
            r.advance(m); self.assertEqual(m.status,"PLANNING")
            r.advance(m); self.assertEqual(m.status,"EXECUTING")
            r.advance(m); self.assertEqual(m.status,"VERIFYING")
            r.advance(m, Event("RESULT","execution",{"ok":False}, correlation_id=m.mission_id))
            self.assertEqual(m.status,"ADAPTING")
            r.advance(m); self.assertEqual(m.status,"PLANNING"); self.assertEqual(m.attempts,1)
            restored=r.resume(m.mission_id)
            self.assertEqual(restored.status,"PLANNING")
            self.assertEqual(restored.objective,"test objective")

    def test_runtime_success(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(state_dir=d); m=r.accept("success objective")
            r.advance(m); r.advance(m); r.advance(m)
            r.advance(m, Event("RESULT","execution",{"ok":True}, correlation_id=m.mission_id))
            self.assertEqual(m.status,"SUCCEEDED")

    def test_recurring_scheduler_persists_and_recovers(self):
        with tempfile.TemporaryDirectory() as d:
            path=os.path.join(d,"schedules.json")
            start=datetime(2026,9,1,0,0,tzinfo=timezone.utc)
            seen=[]
            s=Scheduler(path, on_due=lambda item: seen.append(item.objective))
            item=s.add(Schedule("check system","RECURRING","every:60"), now=start)
            self.assertEqual(s.tick(start+timedelta(seconds=59)), [])
            self.assertEqual(len(s.tick(start+timedelta(seconds=60))),1)
            self.assertEqual(seen,["check system"])
            restored=Scheduler(path)
            self.assertIn(item.schedule_id, restored.schedules)
            self.assertTrue(restored.schedules[item.schedule_id].enabled)
            self.assertEqual(len(restored.tick(start+timedelta(seconds=120))),1)

    def test_one_time_schedule_disables_after_run(self):
        with tempfile.TemporaryDirectory() as d:
            start=datetime(2026,9,1,0,0,tzinfo=timezone.utc)
            s=Scheduler(os.path.join(d,"s.json"))
            item=s.add(Schedule("one shot","ONCE",(start+timedelta(seconds=10)).isoformat()), now=start)
            self.assertEqual(len(s.tick(start+timedelta(seconds=10))),1)
            self.assertFalse(item.enabled)
            self.assertIsNone(item.next_run_at)

    def test_scheduler_pause_resume(self):
        with tempfile.TemporaryDirectory() as d:
            start=datetime(2026,9,1,0,0,tzinfo=timezone.utc)
            s=Scheduler(os.path.join(d,"s.json"))
            item=s.add(Schedule("repeat","RECURRING","every:30"), now=start)
            s.pause(item.schedule_id)
            self.assertEqual(s.tick(start+timedelta(seconds=30)),[])
            s.resume(item.schedule_id, now=start+timedelta(seconds=30))
            self.assertTrue(s.schedules[item.schedule_id].enabled)

if __name__=="__main__": unittest.main()
