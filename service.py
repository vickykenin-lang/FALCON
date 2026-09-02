"""Persistent Falcon service runner.

This is composition/runtime infrastructure, not an organ. It keeps Falcon alive,
ticks the independent scheduler, emits health heartbeats, and shuts down cleanly.
"""
from __future__ import annotations

import signal
import time
from threading import Event


class FalconService:
    def __init__(
        self,
        runtime,
        scheduler=None,
        tick_seconds: float = 1.0,
        heartbeat_seconds: float = 30.0,
        clock=None,
        waiter=None,
        on_error=None,
    ):
        if tick_seconds <= 0 or heartbeat_seconds <= 0:
            raise ValueError("intervals_must_be_positive")
        self.runtime = runtime
        self.scheduler = scheduler
        self.tick_seconds = tick_seconds
        self.heartbeat_seconds = heartbeat_seconds
        self.clock = time.monotonic if clock is None else clock
        self.waiter = self.stop_event_wait if waiter is None else waiter
        self.on_error = on_error
        self.stop_event = Event()

    def stop_event_wait(self,seconds: float) -> bool:
        """Wait interruptibly; returns True when shutdown was requested."""
        return self.stop_event.wait(seconds)

    def stop(self) -> None:
        self.stop_event.set()

    def cycle(self):
        if self.scheduler is None:
            return []
        return self.scheduler.tick()

    def _report_error(self,stage: str,exc: Exception) -> None:
        if self.on_error is not None:
            self.on_error(stage,exc)

    def run(self) -> None:
        last_heartbeat = float("-inf")
        while not self.stop_event.is_set():
            now = self.clock()
            if now - last_heartbeat >= self.heartbeat_seconds:
                try:
                    self.runtime.heartbeat()
                except Exception as exc:
                    self._report_error("heartbeat",exc)
                else:
                    last_heartbeat = now

            try:
                self.cycle()
            except Exception as exc:
                self._report_error("scheduler",exc)

            if self.stop_event.is_set():
                break
            if self.waiter(self.tick_seconds):
                break


def install_signal_handlers(service: FalconService) -> None:
    def shutdown(_signum,_frame):
        service.stop()

    signal.signal(signal.SIGTERM,shutdown)
    signal.signal(signal.SIGINT,shutdown)
