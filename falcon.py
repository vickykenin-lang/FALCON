#!/usr/bin/env python3
"""Local FALCON CLI entry point."""
import argparse, json
from autonomic.runtime import Runtime

def main():
    p=argparse.ArgumentParser(prog="falcon")
    p.add_argument("command", choices=["health","mission"])
    p.add_argument("text", nargs="*")
    a=p.parse_args(); r=Runtime()
    if a.command=="health": print(json.dumps(r.heartbeat().to_dict(), indent=2))
    else:
        if not a.text: p.error("mission requires an objective")
        m=r.accept(" ".join(a.text)); print(json.dumps(m.__dict__, indent=2))
if __name__=="__main__": main()
