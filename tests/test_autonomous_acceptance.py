import tempfile
import unittest
from bootstrap import build_runtime,run_mission
from brain.engine import Brain
from brain.providers.deterministic import DeterministicProvider

class AutonomousAcceptanceTests(unittest.TestCase):
    def test_founder_task_runs_end_to_end_without_manual_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=build_runtime(tmp,brain=Brain(DeterministicProvider()))
            mission=run_mission(runtime,"Inspect this test project and verify execution",acceptance_criteria={"execution_result_ok":True})
            self.assertEqual(mission.status,"SUCCEEDED")
            self.assertEqual(mission.attempts,0)
            events=runtime.memory.recent(100)
            types=[e["event_type"] for e in events]
            self.assertIn("REQUEST",types); self.assertIn("DECISION",types); self.assertIn("ACTION",types); self.assertIn("RESULT",types)
            verification=[e for e in events if e["event_type"]=="RESULT" and e["source"]=="autonomic_driver"][-1]
            self.assertTrue(verification["payload"]["ok"])
            self.assertEqual(verification["payload"]["evaluation_score"],1.0)

if __name__=="__main__":unittest.main()
