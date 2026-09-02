import unittest

from service import FalconService


class FakeRuntime:
    def __init__(self,fail=False):
        self.calls=0; self.fail=fail
    def heartbeat(self):
        self.calls+=1
        if self.fail: raise RuntimeError("heartbeat_failed")


class FakeScheduler:
    def __init__(self,fail=False):
        self.calls=0; self.fail=fail
    def tick(self):
        self.calls+=1
        if self.fail: raise RuntimeError("scheduler_failed")
        return ["due"]


class ServiceTests(unittest.TestCase):
    def test_cycle_ticks_scheduler(self):
        scheduler=FakeScheduler()
        service=FalconService(FakeRuntime(),scheduler=scheduler)
        self.assertEqual(service.cycle(),["due"])
        self.assertEqual(scheduler.calls,1)

    def test_stop_interrupts_default_wait(self):
        service=FalconService(FakeRuntime())
        service.stop()
        self.assertTrue(service.stop_event_wait(10))

    def test_run_isolates_heartbeat_and_scheduler_errors(self):
        runtime=FakeRuntime(fail=True); scheduler=FakeScheduler(fail=True); errors=[]
        waits=[]
        def waiter(seconds):
            waits.append(seconds)
            service.stop()
            return True
        service=FalconService(runtime,scheduler=scheduler,waiter=waiter,on_error=lambda stage,exc: errors.append((stage,type(exc).__name__)))
        service.run()
        self.assertEqual(runtime.calls,1)
        self.assertEqual(scheduler.calls,1)
        self.assertEqual(errors,[("heartbeat","RuntimeError"),("scheduler","RuntimeError")])
        self.assertEqual(waits,[1.0])

    def test_falsey_clock_is_preserved(self):
        class FalseyClock:
            def __bool__(self): return False
            def __call__(self): return 0.0
        clock=FalseyClock()
        service=FalconService(FakeRuntime(),clock=clock)
        self.assertIs(service.clock,clock)


if __name__ == "__main__":
    unittest.main()
