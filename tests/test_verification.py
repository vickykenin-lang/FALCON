import tempfile,unittest
from autonomic.driver import BrainDriver
from bootstrap import build_runtime
from brain.engine import Brain
from execution.registry import Executor
from execution.adapters.base import ExecutionAdapter
from governance.policy import Governance
from learning.evaluator import Evaluator
CAP="test.verify"
class ResultAdapter(ExecutionAdapter):
    name="verify"
    def __init__(self,result): self.result=result
    def available(self): return True
    def execute(self,operation,**kwargs): return dict(self.result)
class Provider:
    def decide(self,objective,context): return {"summary":"verify outcome","actions":[{"adapter":"verify","operation":"run","capability":CAP,"args":{},"risk":"low"}],"success_criteria":["acceptance_criteria"]}
class VerificationTests(unittest.TestCase):
    def run_mission(self,result,criteria,max_replans=0):
        with tempfile.TemporaryDirectory() as d:
            brain=Brain(Provider()); runtime=build_runtime(d,brain=brain); mission=runtime.accept("verify real outcome",acceptance_criteria=criteria); executor=Executor(); executor.register(ResultAdapter(result))
            return BrainDriver(brain,executor,Governance({CAP}),runtime,max_replans=max_replans,evaluator=Evaluator()).run(mission)
    def test_execution_ok_does_not_imply_objective_success(self): self.assertEqual(self.run_mission({"verified":False},{"verified":True}).status,"FAILED")
    def test_matching_acceptance_criteria_allows_success(self): self.assertEqual(self.run_mission({"verified":True},{"verified":True}).status,"SUCCEEDED")
    def test_multiple_criteria_must_all_match(self): self.assertEqual(self.run_mission({"verified":True,"count":1},{"verified":True,"count":2}).status,"FAILED")
if __name__=="__main__": unittest.main()
