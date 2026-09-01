import tempfile,unittest
from autonomic.control import MissionControl
from bootstrap import build_runtime
from contracts.models import Mission
class FakeExecutor:
    def __init__(self):self.cancelled=[]
    def cancel(self,adapter,operation_id):self.cancelled.append((adapter,operation_id)); return True
class MissionControlTests(unittest.TestCase):
    def test_pause_resume_and_cancel_state(self):
        c=MissionControl(); c.pause("m1","hold"); self.assertFalse(c.can_run("m1")); c.resume("m1"); self.assertTrue(c.can_run("m1")); c.cancel("m1","stop"); self.assertFalse(c.can_run("m1"))
    def test_composition_root_wires_shared_control(self):
        with tempfile.TemporaryDirectory() as d:
            control=MissionControl(); runtime=build_runtime(d,control=control); self.assertIs(runtime.control,control)
    def test_cancelled_is_terminal_mission_state(self):
        mission=Mission("stop safely"); mission.transition("DISCOVERING"); mission.transition("CANCELLED"); self.assertEqual(mission.status,"CANCELLED")
    def test_cancel_propagates_to_active_operation(self):
        calls=[]; c=MissionControl(cancel_operation=lambda adapter,op:calls.append((adapter,op))); c.begin_operation("m1","sandbox","op-42"); c.cancel("m1"); self.assertEqual(calls,[("sandbox","op-42")])
    def test_completed_operation_is_not_cancelled(self):
        calls=[]; c=MissionControl(cancel_operation=lambda adapter,op:calls.append((adapter,op))); c.begin_operation("m1","github","op-1"); c.end_operation("m1","op-1"); c.cancel("m1"); self.assertEqual(calls,[])
    def test_composition_connects_control_to_executor_cancel(self):
        with tempfile.TemporaryDirectory() as d:
            executor=FakeExecutor(); runtime=build_runtime(d,executor=executor); runtime.control.begin_operation("m9","sandbox","op-99"); runtime.control.cancel("m9","founder_stop"); self.assertEqual(executor.cancelled,[("sandbox","op-99")])
if __name__=="__main__":unittest.main()
