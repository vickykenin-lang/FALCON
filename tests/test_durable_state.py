import tempfile
import unittest
from pathlib import Path

from autonomic.state import JsonMissionStateBackend
from bootstrap import build_runtime, build_persistence_from_env
from brain.engine import Brain
from brain.providers.deterministic import DeterministicProvider
from contracts.models import Event
from execution.adapters.noop import NoopAdapter
from execution.registry import Executor
from governance.policy import Governance
from memory.store import MemoryStore


class ExplodingNoopAdapter(NoopAdapter):
    def __init__(self): self.called=False
    def execute(self,action,*,execution_context=None,**kwargs):
        self.called=True
        raise AssertionError("duplicate_execution_reached_adapter")


class DurableStateTests(unittest.TestCase):
    def test_restart_restores_same_mission_memory_and_replays_completed_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_root=Path(tmp)/"state"; memory_path=Path(tmp)/"memory.jsonl"
            source_id="telegram-update-123"; objective="recover durable mission"
            brain1=Brain(DeterministicProvider(action_args={"objective":objective}))
            runtime1=build_runtime(
                state_dir=str(Path(tmp)/"runtime1"),brain=brain1,
                memory=MemoryStore(str(memory_path)),state_backend=JsonMissionStateBackend(state_root),
            )
            mission=runtime1.accept(objective,source="telegram",source_id=source_id,acceptance_criteria={"execution_result_ok":True},context={"project":"FALCON"})
            plan=brain1.plan(mission,{})
            runtime1.advance(mission); runtime1.advance(mission)
            self.assertEqual(mission.status,"EXECUTING")
            action=brain1.action_events(mission,plan)[0]
            result=runtime1.driver._execute(mission,action,0)
            self.assertTrue(result.payload["ok"])
            runtime1.bus.publish(result)
            runtime1.bus.publish(Event("LEARNING","learning",{"objective":objective,"lesson":"reuse completed operation after restart"},correlation_id=mission.mission_id))
            first_id=mission.mission_id

            exploding=ExplodingNoopAdapter(); executor2=Executor(); executor2.register(exploding)
            brain2=Brain(DeterministicProvider(action_args={"objective":objective}))
            runtime2=build_runtime(
                state_dir=str(Path(tmp)/"runtime2"),brain=brain2,executor=executor2,
                governance=Governance({"noop.inspect"}),memory=MemoryStore(str(memory_path)),state_backend=JsonMissionStateBackend(state_root),
            )
            restored=runtime2.accept(objective,source="telegram",source_id=source_id,acceptance_criteria={"execution_result_ok":True},context={"project":"FALCON"})
            self.assertEqual(restored.mission_id,first_id)
            self.assertEqual(restored.status,"EXECUTING")
            finished=runtime2.driver.run(restored)
            self.assertEqual(finished.status,"SUCCEEDED")
            self.assertFalse(exploding.called)
            memories=runtime2.memory.context_for(objective)["relevant_memory"]
            self.assertTrue(any(item.get("event_type")=="LEARNING" and item.get("payload",{}).get("lesson")=="reuse completed operation after restart" for item in memories))
            self.assertTrue(any(item.get("source")=="execution_replay" and item.get("payload",{}).get("replayed") for item in runtime2.memory.recent(50)))

    def test_same_source_id_does_not_create_second_mission(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=JsonMissionStateBackend(Path(tmp)/"state")
            brain=Brain(DeterministicProvider(action_args={"objective":"x"}))
            runtime=build_runtime(state_dir=tmp,brain=brain,state_backend=state,memory=MemoryStore(str(Path(tmp)/"memory.jsonl")))
            first=runtime.accept("x",source="telegram",source_id="same")
            second=runtime.accept("x",source="telegram",source_id="same")
            self.assertEqual(first.mission_id,second.mission_id)
            requests=[e for e in runtime.memory.recent(20) if e.get("event_type")=="REQUEST"]
            self.assertEqual(len(requests),1)

    def test_remote_persistence_is_fail_closed_without_token(self):
        with self.assertRaisesRegex(ValueError,"falcon_state_token_required"):
            build_persistence_from_env(".falcon",{"FALCON_STATE_ENDPOINT":"https://state.example"})

if __name__=="__main__":unittest.main()
