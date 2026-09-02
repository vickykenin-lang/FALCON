import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import task_runner

class TaskRunnerTests(unittest.TestCase):
    def test_disabled_task_skips_without_intelligence_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            request=Path(tmp)/"request.json"; output=Path(tmp)/"result.json"; request.write_text(json.dumps({"enabled":False}),encoding="utf-8")
            with patch("sys.argv",["task_runner",str(request),"--output",str(output),"--state-dir",str(Path(tmp)/"state")]):self.assertEqual(task_runner.main(),0)
            self.assertEqual(json.loads(output.read_text())["status"],"SKIPPED")
    def test_enabled_task_runs_end_to_end_with_explicit_test_intelligence(self):
        with tempfile.TemporaryDirectory() as tmp:
            request=Path(tmp)/"request.json"; output=Path(tmp)/"result.json"; request.write_text(json.dumps({"enabled":True,"task_id":"t1","objective":"Inspect task channel","acceptance_criteria":{"execution_result_ok":True},"context":{}}),encoding="utf-8")
            with patch.dict("os.environ",{"FALCON_INTELLIGENCE_MODE":"deterministic"},clear=True), patch("sys.argv",["task_runner",str(request),"--output",str(output),"--state-dir",str(Path(tmp)/"state")]):self.assertEqual(task_runner.main(),0)
            result=json.loads(output.read_text()); self.assertEqual(result["status"],"SUCCEEDED"); self.assertTrue(result["verification"]["ok"]); self.assertIn("ACTION",result["event_types"])

if __name__=="__main__":unittest.main()
