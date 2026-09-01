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
from brain.engine import Brain
from brain.driver import BrainDriver
from bootstrap import build_runtime

class FakeAdapter(ExecutionAdapter):
    name="fake"
    def __init__(self, fail_count=0): self.fail_count=fail_count; self.calls=0
    def available(self): return True
    def execute(self, action, **kwargs):
        self.calls+=1
        if self.calls<=self.fail_count: raise RuntimeError("planned_failure")
        return {"action":action,"verified":True}

class SequenceProvider:
    def __init__(self): self.calls=0; self.contexts=[]
    def decide(self, objective, context):
        self.calls+=1; self.contexts.append(dict(context))
        return {"summary":"progress mission","actions":[{"adapter":"fake","operation":"do_work","args":{},"risk":"low"}],"success_criteria":["execution_result_ok"]}

class FalconV1Tests(unittest.TestCase):
    def runtime(self,d,brain=None,memory=None,bus=None): return build_runtime(d,brain=brain,memory=memory,bus=bus)
    def test_event_bus(self):
        bus=EventBus(); seen=[]; bus.subscribe("HEARTBEAT",seen.append); e=Event("HEARTBEAT","test",{"status":"HEALTHY"}); bus.publish(e); self.assertEqual(seen[0].event_id,e.event_id)
    def test_memory(self):
        with tempfile.TemporaryDirectory() as d:
            m=MemoryStore(os.path.join(d,"m.jsonl")); m.remember(Event("MEMORY","test",{"x":1})); self.assertEqual(m.recent(1)[0]["payload"]["x"],1)
    def test_runtime_mission_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.runtime(d); m=r.accept("test objective"); self.assertEqual(m.status,"DISCOVERING"); r.advance(m); r.advance(m); r.advance(m); r.advance(m,Event("RESULT","execution",{"ok":False},correlation_id=m.mission_id)); self.assertEqual(m.status,"ADAPTING"); r.advance(m); self.assertEqual(r.resume(m.mission_id).status,"PLANNING")
    def test_autonomous_loop_success(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.runtime(d); m=r.accept("execute automatically"); ex=Executor(); adapter=FakeAdapter(); ex.register(adapter); action=Event("ACTION","brain",{"adapter":"fake","operation":"do_work","args":{},"risk":"low"},correlation_id=m.mission_id); self.assertEqual(AutonomousLoop(r,ex,Governance()).run(m,action).status,"SUCCEEDED")
    def test_autonomous_loop_adapts_and_retries(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.runtime(d); m=r.accept("recover automatically"); ex=Executor(); adapter=FakeAdapter(1); ex.register(adapter); action=Event("ACTION","brain",{"adapter":"fake","operation":"do_work","args":{},"risk":"low"},correlation_id=m.mission_id); result=AutonomousLoop(r,ex,Governance(),max_attempts=3).run(m,action); self.assertEqual(result.status,"SUCCEEDED"); self.assertEqual(adapter.calls,2)
    def test_brain_driver_replans_with_memory_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            provider=SequenceProvider(); brain=Brain(provider); memory=MemoryStore(os.path.join(d,"memory.jsonl")); memory.remember(Event("RESULT","old",{"ok":False,"objective":"recover service","lesson":"retry alternative"})); r=self.runtime(d,brain,memory); m=r.accept("recover service"); ex=Executor(); adapter=FakeAdapter(1); ex.register(adapter); result=BrainDriver(brain,ex,Governance(),r,memory,max_replans=2).run(m); self.assertEqual(result.status,"SUCCEEDED"); self.assertEqual(provider.calls,2); self.assertTrue(provider.contexts[0].get("relevant_memory")); self.assertIn("previous_evidence",provider.contexts[1])
    def test_recurring_scheduler_persists_and_recovers(self):
        with tempfile.TemporaryDirectory() as d:
            path=os.path.join(d,"s.json"); start=datetime(2026,9,1,tzinfo=timezone.utc); s=Scheduler(path); item=s.add(Schedule("check","RECURRING","every:60"),now=start); self.assertEqual(len(s.tick(start+timedelta(seconds=60))),1); self.assertIn(item.schedule_id,Scheduler(path).schedules)
    def test_due_schedule_starts_autonomic_mission(self):
        with tempfile.TemporaryDirectory() as d:
            start=datetime(2026,9,1,tzinfo=timezone.utc); runtime=self.runtime(os.path.join(d,"runtime")); bridge=SchedulerBridge(runtime); scheduler=Scheduler(os.path.join(d,"s.json"),on_due=bridge.on_due); item=scheduler.add(Schedule("scheduled objective","RECURRING","every:60"),now=start); scheduler.tick(start+timedelta(seconds=60)); self.assertEqual(runtime.resume(bridge.started_missions[item.schedule_id]).objective,"scheduled objective")
if __name__=="__main__": unittest.main()
