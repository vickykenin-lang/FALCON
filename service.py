"""Persistent Falcon service runner.

This is composition/runtime infrastructure, not an organ. It keeps Falcon alive,
ticks the independent scheduler, emits health heartbeats, and shuts down cleanly.
"""
from __future__ import annotations
import signal
import time
from threading import Event

class FalconService:
    def __init__(self,runtime,scheduler=None,tick_seconds:float=1.0,heartbeat_seconds:float=30.0,clock=None,sleeper=None):
        if tick_seconds<=0 or heartbeat_seconds<=0: raise ValueError("intervals_must_be_positive")
        self.runtime=runtime; self.scheduler=scheduler; self.tick_seconds=tick_seconds; self.heartbeat_seconds=heartbeat_seconds
        self.clock=clock or time.monotonic; self.sleeper=sleeper or time.sleep; self.stop_event=Event()
    def stop(self): self.stop_event.set()
    def cycle(self):
        triggered=[]
        if self.scheduler is not None: triggered=self.scheduler.tick()
        return triggered
    def run(self):
        last_heartbeat=float("-inf")
        while not self.stop_event.is_set():
            now=self.clock()
            if now-last_heartbeat>=self.heartbeat_seconds:
                self.runtime.heartbeat(); last_heartbeat=now
            self.cycle()
            if not self.stop_event.is_set(): self.sleeper(self.tick_seconds)

def install_signal_handlers(service:FalconService):
    def shutdown(_signum,_frame): service.stop()
    signal.signal(signal.SIGTERM,shutdown); signal.signal(signal.SIGINT,shutdown)
