#!/usr/bin/env python3
"""Local FALCON CLI entry point."""
import argparse
import json
from bootstrap import build_runtime


def self_test(runtime) -> int:
    heartbeat=runtime.heartbeat(); data=heartbeat.to_dict()
    healthy=data.get("payload",{}).get("status")=="HEALTHY"
    print(json.dumps({"falcon":"V1","self_test":"PASS" if healthy else "FAIL","heartbeat":data},indent=2))
    return 0 if healthy else 1


def main() -> int:
    p=argparse.ArgumentParser(prog="falcon")
    p.add_argument("--self-test",action="store_true",help="run Falcon V1 smoke verification")
    p.add_argument("command",nargs="?",choices=["health","mission"])
    p.add_argument("text",nargs="*")
    a=p.parse_args(); r=build_runtime()
    if a.self_test: return self_test(r)
    if not a.command: p.error("command is required unless --self-test is used")
    if a.command=="health": print(json.dumps(r.heartbeat().to_dict(),indent=2)); return 0
    if not a.text: p.error("mission requires an objective")
    m=r.accept(" ".join(a.text)); print(json.dumps(m.__dict__,indent=2)); return 0


if __name__=="__main__": raise SystemExit(main())
