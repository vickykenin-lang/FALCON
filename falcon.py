#!/usr/bin/env python3
"""Local FALCON CLI entry point."""
import argparse
import json
from bootstrap import build_runtime
from scheduler.bridge import SchedulerBridge
from scheduler.engine import Scheduler
from service import FalconService,install_signal_handlers


def self_test(runtime) -> int:
    heartbeat=runtime.heartbeat(); data=heartbeat.to_dict()
    healthy=data.get("payload",{}).get("status")=="HEALTHY"
    print(json.dumps({"falcon":"V1","self_test":"PASS" if healthy else "FAIL","heartbeat":data},indent=2))
    return 0 if healthy else 1


def build_service(state_dir:str=".falcon",tick_seconds:float=1.0,heartbeat_seconds:float=30.0):
    runtime=build_runtime(state_dir=state_dir)
    bridge=SchedulerBridge(runtime.bus.publish,runtime.accept)
    scheduler=Scheduler(f"{state_dir}/schedules.json",on_due=bridge.on_due)
    return FalconService(runtime,scheduler,tick_seconds=tick_seconds,heartbeat_seconds=heartbeat_seconds)


def main() -> int:
    p=argparse.ArgumentParser(prog="falcon")
    p.add_argument("--self-test",action="store_true",help="run Falcon V1 smoke verification")
    p.add_argument("--state-dir",default=".falcon",help="persistent Falcon state directory")
    p.add_argument("--tick-seconds",type=float,default=1.0,help="service scheduler tick interval")
    p.add_argument("--heartbeat-seconds",type=float,default=30.0,help="service heartbeat interval")
    p.add_argument("command",nargs="?",choices=["health","mission","serve"])
    p.add_argument("text",nargs="*")
    a=p.parse_args(); r=build_runtime(state_dir=a.state_dir)
    if a.self_test: return self_test(r)
    if not a.command: p.error("command is required unless --self-test is used")
    if a.command=="health": print(json.dumps(r.heartbeat().to_dict(),indent=2)); return 0
    if a.command=="serve":
        service=build_service(a.state_dir,a.tick_seconds,a.heartbeat_seconds)
        install_signal_handlers(service)
        service.run(); return 0
    if not a.text: p.error("mission requires an objective")
    m=r.accept(" ".join(a.text)); print(json.dumps(m.__dict__,indent=2)); return 0


if __name__=="__main__": raise SystemExit(main())
