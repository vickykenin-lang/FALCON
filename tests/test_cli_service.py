import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch

import falcon
from scheduler.engine import Schedule

class CliServiceTests(unittest.TestCase):
    def test_build_service_wires_persistent_scheduler(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=falcon.build_service(tmp,tick_seconds=0.01,heartbeat_seconds=1)
            self.assertIsNotNone(service.runtime)
            self.assertIsNotNone(service.scheduler)
            self.assertEqual(service.scheduler.state_file,Path(tmp)/"schedules.json")
            self.assertIsNotNone(service.scheduler.on_due)

    def test_serve_installs_signals_and_runs_service(self):
        class FakeService:
            def __init__(self): self.ran=False
            def run(self): self.ran=True
        service=FakeService()
        with patch.object(falcon,"build_service",return_value=service), patch.object(falcon,"install_signal_handlers") as install, patch("sys.argv",["falcon","serve"]):
            self.assertEqual(falcon.main(),0)
        install.assert_called_once_with(service)
        self.assertTrue(service.ran)

    def test_due_schedule_executes_full_autonomous_mission(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ",{"FALCON_INTELLIGENCE_MODE":"deterministic"},clear=True):
            service=falcon.build_service(tmp,tick_seconds=0.01,heartbeat_seconds=1)
            now=datetime.now(timezone.utc)
            item=service.scheduler.add(Schedule("inspect scheduled project","ONCE",now.isoformat()),now=now)
            service.scheduler.tick(now)
            mission_id=service.scheduler_bridge.started_missions[item.schedule_id]
            mission=service.runtime.resume(mission_id)
            self.assertEqual(mission.status,"SUCCEEDED")

if __name__=="__main__": unittest.main()
