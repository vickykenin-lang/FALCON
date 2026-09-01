"""Persistent, dependency-free Falcon scheduling engine.

Scheduler owns WHEN a task is due. It emits due records; it never reasons about
or executes the task itself. Current V1 expressions support ISO-8601 timestamps
for ONCE and interval expressions such as `every:300` for RECURRING tasks.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4


@dataclass
class Schedule:
    objective: str
    mode: str
    schedule_expression: str
    schedule_id: str = ""
    timezone: str = "UTC"
    enabled: bool = True
    missed_run_policy: str = "RUN_ONCE"
    max_concurrent_runs: int = 1
    next_run_at: str | None = None
    last_run_at: str | None = None

    def __post_init__(self):
        self.schedule_id = self.schedule_id or str(uuid4())
        if self.mode not in {"ONCE", "RECURRING"}:
            raise ValueError("invalid_schedule_mode")
        if self.missed_run_policy not in {"SKIP", "RUN_ONCE", "CATCH_UP"}:
            raise ValueError("invalid_missed_run_policy")
        if self.max_concurrent_runs < 1:
            raise ValueError("invalid_max_concurrent_runs")


class Scheduler:
    def __init__(self, state_file: str = ".falcon/schedules.json", on_due: Callable[[Schedule], None] | None = None):
        self.state_file = Path(state_file)
        self.on_due = on_due
        self.schedules: dict[str, Schedule] = {}
        self.load()

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_time(value: str) -> datetime:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    @staticmethod
    def _iso(dt: datetime) -> str:
        return dt.astimezone(timezone.utc).isoformat()

    def _calculate_first_run(self, item: Schedule, now: datetime) -> str:
        if item.mode == "ONCE":
            return self._iso(self._parse_time(item.schedule_expression))
        seconds = self._interval_seconds(item.schedule_expression)
        return self._iso(now + timedelta(seconds=seconds))

    @staticmethod
    def _interval_seconds(expression: str) -> int:
        if not expression.startswith("every:"):
            raise ValueError("recurring_expression_must_be_every_seconds")
        seconds = int(expression.split(":", 1)[1])
        if seconds < 1:
            raise ValueError("interval_must_be_positive")
        return seconds

    def add(self, item: Schedule, now: datetime | None = None) -> Schedule:
        now = now or self._utcnow()
        item.next_run_at = item.next_run_at or self._calculate_first_run(item, now)
        self.schedules[item.schedule_id] = item
        self.save()
        return item

    def remove(self, schedule_id: str) -> None:
        self.schedules.pop(schedule_id, None)
        self.save()

    def pause(self, schedule_id: str) -> None:
        self.schedules[schedule_id].enabled = False
        self.save()

    def resume(self, schedule_id: str, now: datetime | None = None) -> None:
        item = self.schedules[schedule_id]
        item.enabled = True
        if item.next_run_at is None:
            item.next_run_at = self._calculate_first_run(item, now or self._utcnow())
        self.save()

    def due(self, now: datetime | None = None) -> list[Schedule]:
        now = now or self._utcnow()
        due_items: list[Schedule] = []
        for item in self.schedules.values():
            if not item.enabled or not item.next_run_at:
                continue
            if self._parse_time(item.next_run_at) <= now:
                due_items.append(item)
        return due_items

    def tick(self, now: datetime | None = None) -> list[Schedule]:
        now = now or self._utcnow()
        triggered: list[Schedule] = []
        for item in self.due(now):
            scheduled_for = self._parse_time(item.next_run_at)
            if item.missed_run_policy == "SKIP" and scheduled_for < now and item.mode == "ONCE":
                item.enabled = False
                item.next_run_at = None
                continue
            triggered.append(item)
            item.last_run_at = self._iso(now)
            if self.on_due:
                self.on_due(item)
            if item.mode == "ONCE":
                item.enabled = False
                item.next_run_at = None
            else:
                seconds = self._interval_seconds(item.schedule_expression)
                next_run = scheduled_for + timedelta(seconds=seconds)
                if item.missed_run_policy in {"RUN_ONCE", "SKIP"}:
                    while next_run <= now:
                        next_run += timedelta(seconds=seconds)
                item.next_run_at = self._iso(next_run)
        self.save()
        return triggered

    def save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(item) for item in self.schedules.values()]
        self.state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self) -> None:
        if not self.state_file.exists():
            return
        raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.schedules = {item["schedule_id"]: Schedule(**item) for item in raw}
