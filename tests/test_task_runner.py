import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import task_runner
from contracts.models import Mission

class TaskRunnerTests(unittest.TestCase):
    def test_disabled_task_skips_without_intelligence_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            request=Path(tmp)/"request.json"; output=Path(tmp)/"result.json"; request.write_text(json.dumps({"enabled":False}),encoding="utf-8")
            with patch("sys.argv",["task_runner",str(request),"--output",str(output),"--state-dir",str(Path(tmp)/"state")]):self.assertEqual(task_runner.main(),0)
            self.assertEqual(json.loads(output.read_text())["status"],"SKIPPED")
    def test_enabled_task_runs_end_to_end_with_safe_acceptance_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            request=Path(tmp)/"request.json"; output=Path(tmp)/"result.json"; request.write_text(json.dumps({"enabled":True,"profile":"deterministic_acceptance","task_id":"t1","objective":"Inspect task channel","acceptance_criteria":{"execution_result_ok":True},"context":{}}),encoding="utf-8")
            with patch.dict("os.environ",{},clear=True), patch("sys.argv",["task_runner",str(request),"--output",str(output),"--state-dir",str(Path(tmp)/"state")]):self.assertEqual(task_runner.main(),0)
            result=json.loads(output.read_text()); self.assertEqual(result["status"],"SUCCEEDED"); self.assertEqual(result["profile"],"deterministic_acceptance"); self.assertTrue(result["verification"]["ok"]); self.assertIn("ACTION",result["event_types"])
    def test_github_read_acceptance_profile_builds_governed_real_read_action(self):
        brain=task_runner._profile_brain("github_read_acceptance",{"context":{"repository":"owner/repo"}})
        event=brain.plan(Mission("inspect repository")); action=event.payload["plan"]["actions"][0]
        self.assertEqual(action["adapter"],"github"); self.assertEqual(action["operation"],"get_repository"); self.assertEqual(action["capability"],"github.read"); self.assertEqual(action["args"],{"repository":"owner/repo"})
    def test_github_write_acceptance_profile_is_sandboxed_and_governed(self):
        task={"context":{"repository":"owner/repo","path":"artifacts/kra1/canary.txt","content":"safe canary","message":"KRA1 test"}}
        brain=task_runner._profile_brain("github_write_acceptance",task)
        event=brain.plan(Mission("write canary")); action=event.payload["plan"]["actions"][0]
        self.assertEqual(action["adapter"],"github"); self.assertEqual(action["operation"],"create_file"); self.assertEqual(action["capability"],"github.write")
        self.assertEqual(action["args"]["path"],"artifacts/kra1/canary.txt")
        with self.assertRaisesRegex(ValueError,"path_not_sandboxed"):
            task_runner._profile_brain("github_write_acceptance",{"context":{"repository":"owner/repo","path":"README.md","content":"unsafe"}})
    def test_summary_surfaces_block_reason_plan_and_bounded_evidence(self):
        events=[
            {"event_type":"DECISION","source":"brain","payload":{"plan":{"summary":"Inspect the repository safely","actions":[{"adapter":"github","operation":"get_repository"}]}}},
            {"event_type":"ALERT","source":"brain","payload":{"reason":"more_context_required"}},
            {"event_type":"RESULT","source":"autonomic_driver","payload":{"ok":False,"execution_ok":False,"evaluation_score":0.0,"lesson":"blocked","observed":{"full_name":"owner/repo","nested":{"secret":"ignored"},"private":False}}},
        ]
        runtime=SimpleNamespace(memory=SimpleNamespace(recent=lambda limit:events))
        mission=SimpleNamespace(mission_id="m1",objective="inspect",status="BLOCKED",attempts=0)
        result=task_runner._summary(runtime,mission)
        self.assertEqual(result["reason"],"more_context_required")
        self.assertEqual(result["plan_summary"],"Inspect the repository safely")
        self.assertEqual(result["actions"],["github.get_repository"])
        self.assertEqual(result["evidence"],{"full_name":"owner/repo","private":False})

if __name__=="__main__":unittest.main()
