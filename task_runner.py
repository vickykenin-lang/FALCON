#!/usr/bin/env python3
"""Run one Founder task request through Falcon and emit bounded evidence."""
import argparse
import json
from pathlib import Path
from bootstrap import build_runtime,run_mission
from brain.engine import Brain
from brain.providers.deterministic import DeterministicProvider

TERMINAL={"SUCCEEDED","FAILED","BLOCKED","CANCELLED"}

def _load(path:str)->dict:
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data,dict):raise ValueError("task_request_must_be_object")
    return data

def _summary(runtime,mission)->dict:
    events=runtime.memory.recent(250) if runtime.memory else []
    verification=None; reason=None; plan_summary=None; actions=[]; evidence={}
    for event in events:
        payload=event.get("payload",{}) if isinstance(event,dict) else {}
        if event.get("event_type")=="DECISION" and event.get("source")=="brain" and isinstance(payload.get("plan"),dict):
            plan=payload["plan"]; plan_summary=plan.get("summary")
            actions=[f"{item.get('adapter')}.{item.get('operation')}" for item in plan.get("actions",[]) if isinstance(item,dict)]
        if event.get("event_type")=="ALERT" and not reason: reason=payload.get("reason")
        if event.get("event_type")=="FAILURE" and not reason: reason=payload.get("detail") or payload.get("error")
        if event.get("event_type")=="RESULT" and event.get("source")=="autonomic_driver":
            verification={k:payload.get(k) for k in ("ok","execution_ok","evaluation_score","lesson")}
            observed=payload.get("observed")
            if isinstance(observed,dict): evidence={k:v for k,v in observed.items() if k not in {"content","content_text"}}
    return {"mission_id":mission.mission_id,"objective":mission.objective,"status":mission.status,"attempts":mission.attempts,"reason":reason,"plan_summary":plan_summary,"actions":actions,"evidence":evidence,"verification":verification,"event_types":[event.get("event_type") for event in events],"event_count":len(events)}

def _profile_brain(profile:str,task:dict):
    if not profile:return None
    context=task.get("context") or {}
    if profile=="deterministic_acceptance":return Brain(DeterministicProvider())
    if profile=="github_read_acceptance":
        repository=str(context.get("repository","")).strip()
        if not repository:raise ValueError("github_read_acceptance_repository_required")
        return Brain(DeterministicProvider("github","get_repository","github.read",{"repository":repository}))
    if profile=="github_workflow_runs_acceptance":
        repository=str(context.get("repository","")).strip(); per_page=int(context.get("per_page",20))
        if not repository:raise ValueError("github_workflow_runs_acceptance_repository_required")
        return Brain(DeterministicProvider("github","get_workflow_runs","github.read",{"repository":repository,"per_page":per_page}))
    if profile=="github_write_acceptance":
        repository=str(context.get("repository","")).strip(); path=str(context.get("path","")).strip()
        content=str(context.get("content","")).strip(); message=str(context.get("message","Falcon KRA1 governed write acceptance")).strip()
        if not repository:raise ValueError("github_write_acceptance_repository_required")
        if not path.startswith("artifacts/kra1/") or path.endswith("/"):raise ValueError("github_write_acceptance_path_not_sandboxed")
        if not content:raise ValueError("github_write_acceptance_content_required")
        return Brain(DeterministicProvider("github","create_file","github.write",{"repository":repository,"path":path,"content":content,"message":message,"branch":"main"}))
    if profile=="github_workflow_dispatch_acceptance":
        repository=str(context.get("repository","")).strip(); workflow=str(context.get("workflow","")).strip(); ref=str(context.get("ref","main")).strip() or "main"
        if not repository:raise ValueError("github_workflow_dispatch_acceptance_repository_required")
        if not workflow:raise ValueError("github_workflow_dispatch_acceptance_workflow_required")
        return Brain(DeterministicProvider("github","dispatch_workflow","github.write",{"repository":repository,"workflow":workflow,"ref":ref,"inputs":context.get("inputs") or {}}))
    raise ValueError(f"unsupported_task_profile:{profile}")

def main()->int:
    parser=argparse.ArgumentParser(prog="falcon-task"); parser.add_argument("request"); parser.add_argument("--state-dir",default=".falcon/task-runtime"); parser.add_argument("--output",default="falcon-task-result.json"); args=parser.parse_args()
    task=_load(args.request)
    if not bool(task.get("enabled",True)):
        result={"status":"SKIPPED","reason":"task_disabled"}; Path(args.output).write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result)); return 0
    objective=str(task.get("objective","")).strip()
    if not objective:raise ValueError("task_objective_required")
    profile=str(task.get("profile","")).strip().lower(); brain=_profile_brain(profile,task)
    runtime=build_runtime(state_dir=args.state_dir,brain=brain)
    mission=run_mission(runtime,objective,acceptance_criteria=task.get("acceptance_criteria") or {},context=task.get("context") or {},source="founder",source_id=task.get("task_id"))
    result=_summary(runtime,mission); result["profile"]=profile or "production"; Path(args.output).write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result))
    return 0 if mission.status=="SUCCEEDED" else 2

if __name__=="__main__":raise SystemExit(main())
