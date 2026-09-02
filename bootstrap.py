"""Falcon composition root: concrete organ wiring lives only here."""
import os
from autonomic.control import MissionControl
from autonomic.driver import BrainDriver
from autonomic.runtime import Runtime
from brain.engine import Brain
from brain.providers.deterministic import DeterministicProvider
from brain.providers.json_http import JsonHttpProvider
from execution.adapters.noop import NoopAdapter
from execution.registry import Executor
from governance.policy import Governance
from learning.evaluator import Evaluator
from memory.store import MemoryStore
from nervous_system.bus import EventBus

def build_brain_from_env(environ=None)->Brain:
    env=os.environ if environ is None else environ
    mode=str(env.get("FALCON_INTELLIGENCE_MODE","")).strip().lower()
    endpoint=str(env.get("FALCON_INTELLIGENCE_ENDPOINT","")).strip()
    if not mode and endpoint:mode="json_http"
    if not mode:return Brain()
    if mode=="deterministic":return Brain(DeterministicProvider())
    if mode!="json_http":raise ValueError(f"unsupported_intelligence_mode:{mode}")
    if not endpoint:raise ValueError("falcon_intelligence_endpoint_required")
    timeout=float(env.get("FALCON_INTELLIGENCE_TIMEOUT","30"))
    headers={}
    token=str(env.get("FALCON_INTELLIGENCE_TOKEN","")).strip()
    if token:headers["Authorization"]=f"Bearer {token}"
    return Brain(JsonHttpProvider(endpoint,headers=headers,timeout=timeout))

def build_runtime(state_dir:str=".falcon",brain=None,memory=None,bus=None,control=None,executor=None,governance=None,evaluator=None)->Runtime:
    if bus is None:bus=EventBus()
    if brain is None:brain=build_brain_from_env()
    if memory is None:memory=MemoryStore(f"{state_dir}/memory.jsonl")
    if executor is None:
        executor=Executor(); executor.register(NoopAdapter())
    if governance is None:governance=Governance({"noop.inspect"})
    if evaluator is None:evaluator=Evaluator()
    if control is None:control=MissionControl(cancel_operation=executor.cancel)
    runtime=Runtime(bus=bus,brain=brain,memory=memory,state_dir=state_dir)
    runtime.control=control; runtime.executor=executor; runtime.governance=governance; runtime.evaluator=evaluator
    runtime.driver=BrainDriver(brain,executor,governance,runtime,memory=memory,control=control,evaluator=evaluator)
    return runtime

def run_mission(runtime:Runtime,objective:str,acceptance_criteria:dict|None=None,context:dict|None=None,source:str="founder",source_id:str|None=None):
    mission=runtime.accept(objective,source=source,source_id=source_id,acceptance_criteria=acceptance_criteria,context=context)
    return runtime.driver.run(mission,context=context)
