import json
import tempfile
import unittest
from pathlib import Path
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

if __name__=="__main__":unittest.main()
