import threading,time,unittest
from contracts.models import Event
from execution.adapters.base import ExecutionAdapter
from execution.registry import Executor
class BlockingAdapter(ExecutionAdapter):
    name="blocking"
    def __init__(self):
        self.started=threading.Event(); self.release=threading.Event(); self.execution_id=None; self.cancel_id=None
    def available(self): return True
    def execute(self,action,*,execution_context=None,**kwargs):
        self.execution_id=execution_context.operation_id if execution_context else None; self.started.set(); self.release.wait(2); return {"released":True}
    def cancel(self,operation_id):
        self.cancel_id=operation_id; self.release.set(); return operation_id==self.execution_id
class ExecutionCancellationTests(unittest.TestCase):
    def test_executor_uses_same_operation_id_for_execute_and_cancel(self):
        executor=Executor(); adapter=BlockingAdapter(); executor.register(adapter); operation_id="op-stable-42"; result=[]
        action=Event("ACTION","brain",{"adapter":"blocking","operation":"wait","capability":"test.cancel","args":{}},correlation_id="mission-1")
        thread=threading.Thread(target=lambda:result.append(executor.execute(action,operation_id=operation_id)))
        thread.start(); self.assertTrue(adapter.started.wait(1)); self.assertEqual(adapter.execution_id,operation_id); self.assertTrue(executor.cancel("blocking",operation_id)); thread.join(1)
        self.assertFalse(thread.is_alive()); self.assertEqual(adapter.cancel_id,operation_id); self.assertEqual(result[0].payload["operation_id"],operation_id)
if __name__=="__main__": unittest.main()
