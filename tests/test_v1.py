import tempfile, os, unittest
from datetime import datetime, timedelta, timezone
from contracts.models import Event
from nervous_system.bus import EventBus
from memory.store import MemoryStore
from autonomic.runtime import Runtime
from autonomic.loop import AutonomousLoop
from execution.registry import Executor
from execution.adapters.base import ExecutionAdapter
from governance.policy import Governance
from scheduler.engine import Schedule, Scheduler
from scheduler.bridge import SchedulerBridge

class FakeAdapter(ExecutionAdapter):
    name="fake"
    def __init__(self, fail_count=0): self.fail_count=fail_count; self.calls=0
    def available(self): return True
    def execute(self, action, **kwargs):
        self.calls += 1
        if self.calls <= self.fail_count: raise RuntimeError("planned_failure")
        return {"action":action,"verified":True}

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

    def test_autonomous_loop_success(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(state_dir=d); m=r.accept("execute automatically")
            ex=Executor(); adapter=FakeAdapter(); ex.register(adapter)
            action=Event("ACTION","brain",{"adapter":"fake","operation":"do_work","args":{},"risk":"low"},correlation_id=m.mission_id)
            result=AutonomousLoop(r,ex,Governance()).run(m,action)
            self.assertEqual(result.status,"SUCCEEDED"); self.assertEqual(adapter.calls,1)

    def test_autonomous_loop_adapts_and_retries(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(state_dir=d); m=r.accept("recover automatically")
            ex=Executor(); adapter=FakeAdapter(fail_count=1); ex.register(adapter)
            action=Event("ACTION","brain",{"adapter":"fake","operation":"do_work","args":{},"risk":"low"},correlation_id=m.mission_id)
            result=AutonomousLoop(r,ex,Governance(),max_attempts=3).run(m,action)
            self.assertEqual(result.status,"SUCCEEDED"); self.assertEqual(adapter.calls,2); self.assertEqual(result.attempts,1)

    def test_autonomous_loop_blocks_missing_credentials(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(state_dir=d); m=r.accept("credential task")
            ex=Executor(); ex.register(FakeAdapter())
            action=Event("ACTION","brain",{"adapter":"fake","operation":"do_work","risk":"credential_required"},correlation_id=m.mission_id)
            result=AutonomousLoop(r,ex,Governance()).run(m,action)
            self.assertEqual(result.status,"BLOCKED")

    def test_recurring_scheduler_persists_and_recovers(self):
        with tempfile.TemporaryDirectory() as d:
            path=os.path.join(d,"schedules.json"); start=datetime(2026,9,1,0,0,tzinfo=timezone.utc); seen=[]
            s=Scheduler(path,on_due=lambda item:seen.append(item.objective)); item=s.add(Schedule("check system","RECURRING","every:60"),now=start)
            self.assertEqual(s.tick(start+timedelta(seconds=59)),[]); self.assertEqual(len(s.tick(start+timedelta(seconds=60))),1)
            restored=Scheduler(path); self.assertIn(item.schedule_id,restored.schedules); self.assertEqual(len(restored.tick(start+timedelta(seconds=120))),1)

    def test_one_time_schedule_disables_after_run(self):
        with tempfile.TemporaryDirectory() as d:
            start=datetime(2026,9,1,0,0,tzinfo=timezone.utc); s=Scheduler(os.path.join(d,"s.json"))
            item=s.add(Schedule("one shot","ONCE",(start+timedelta(seconds=10)).isoformat()),now=start)
            self.assertEqual(len(s.tick(start+timedelta(seconds=10))),1); self.assertFalse(item.enabled); self.assertIsNone(item.next_run_at)

    def test_scheduler_pause_resume(self):
        with tempfile.TemporaryDirectory() as d:
            start=datetime(2026,9,1,0,0,tzinfo=timezone.utc); s=Scheduler(os.path.join(d,"s.json")); item=s.add(Schedule("repeat","RECURRING","every:30"),now=start)
            s.pause(item.schedule_id); self.assertEqual(s.tick(start+timedelta(seconds=30)),[]); s.resume(item.schedule_id,now=start+timedelta(seconds=30)); self.assertTrue(s.schedules[item.schedule_id].enabled)

    def test_due_schedule_starts_autonomic_mission(self):
        with tempfile.TemporaryDirectory() as d:
            start=datetime(2026,9,1,0,0,tzinfo=timezone.utc); runtime=Runtime(state_dir=os.path.join(d,"runtime")); bridge=SchedulerBridge(runtime)
            scheduler=Scheduler(os.path.join(d,"schedules.json"),on_due=bridge.on_due); item=scheduler.add(Schedule("scheduled objective","RECURRING","every:60"),now=start); scheduler.tick(start+timedelta(seconds=60))
            mission=runtime.resume(bridge.started_missions[item.schedule_id]); self.assertEqual(mission.objective,"scheduled objective"); self.assertEqual(mission.status,"DISCOVERING")

if __name__=="__main__": unittest.main()
