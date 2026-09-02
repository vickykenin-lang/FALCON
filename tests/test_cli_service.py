import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import falcon


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


if __name__=="__main__": unittest.main()
