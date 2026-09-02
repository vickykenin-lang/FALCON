#!/usr/bin/env python3
"""Run one Founder task request through Falcon and emit bounded evidence."""
import argparse
import json
from pathlib import Path
from bootstrap import build_runtime,run_mission

TERMINAL={"SUCCEEDED","FAILED","BLOCKED","CANCELLED"}

def _load(path:str)->dict:
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data,dict):raise ValueError("task_request_must_be_object")
    return data

def _summary(runtime,mission)->dict:
    events=runtime.memory.recent(250) if runtime.memory else []
    verification=None
    for event in reversed(events):
        if event.get("event_type")=="RESULT" and event.get("source")=="autonomic_driver":
            payload=event.get("payload",{}); verification={k:payload.get(k) for k in ("ok","execution_ok","evaluation_score","lesson")}; break
    return {"mission_id":mission.mission_id,"objective":mission.objective,"status":mission.status,"attempts":mission.attempts,"verification":verification,"event_types":[event.get("event_type") for event in events],"event_count":len(events)}

def main()->int:
    parser=argparse.ArgumentParser(prog="falcon-task"); parser.add_argument("request"); parser.add_argument("--state-dir",default=".falcon/task-runtime"); parser.add_argument("--output",default="falcon-task-result.json"); args=parser.parse_args()
    task=_load(args.request)
    if not bool(task.get("enabled",True)):
        result={"status":"SKIPPED","reason":"task_disabled"}; Path(args.output).write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result)); return 0
    objective=str(task.get("objective","")).strip()
    if not objective:raise ValueError("task_objective_required")
    runtime=build_runtime(state_dir=args.state_dir)
    mission=run_mission(runtime,objective,acceptance_criteria=task.get("acceptance_criteria") or {},context=task.get("context") or {},source="founder",source_id=task.get("task_id"))
    result=_summary(runtime,mission); Path(args.output).write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result))
    return 0 if mission.status=="SUCCEEDED" else 2

if __name__=="__main__":raise SystemExit(main())
