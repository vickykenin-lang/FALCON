"""Persistent dependency-free Falcon scheduling engine."""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

@dataclass
class Schedule:
    objective:str; mode:str; schedule_expression:str
    schedule_id:str=""; timezone:str="UTC"; enabled:bool=True
    missed_run_policy:str="RUN_ONCE"; max_concurrent_runs:int=1
    next_run_at:str|None=None; last_run_at:str|None=None; contract_version:str="1.0"
    def __post_init__(self):
        self.schedule_id=self.schedule_id or str(uuid4())
        if self.contract_version!="1.0": raise ValueError("unsupported_schedule_contract")
        if self.mode not in {"ONCE","RECURRING"}: raise ValueError("invalid_schedule_mode")
        if self.missed_run_policy not in {"SKIP","RUN_ONCE","CATCH_UP"}: raise ValueError("invalid_missed_run_policy")
        if self.max_concurrent_runs<1: raise ValueError("invalid_max_concurrent_runs")
        if not isinstance(self.schedule_expression,str) or not self.schedule_expression: raise ValueError("schedule_expression_required")

class Scheduler:
    def __init__(self,state_file:str=".falcon/schedules.json",on_due:Callable[[Schedule],None]|None=None): self.state_file=Path(state_file); self.on_due=on_due; self.schedules={}; self.load()
    @staticmethod
    def _utcnow(): return datetime.now(timezone.utc)
    @staticmethod
    def _parse_time(value):
        dt=datetime.fromisoformat(value.replace("Z","+00:00")); return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    @staticmethod
    def _iso(dt): return dt.astimezone(timezone.utc).isoformat()
    @staticmethod
    def _interval_seconds(expression):
        if not expression.startswith("every:"): raise ValueError("recurring_expression_must_be_every_seconds")
        seconds=int(expression.split(":",1)[1])
        if seconds<1: raise ValueError("interval_must_be_positive")
        return seconds
    def _calculate_first_run(self,item,now): return self._iso(self._parse_time(item.schedule_expression)) if item.mode=="ONCE" else self._iso(now+timedelta(seconds=self._interval_seconds(item.schedule_expression)))
    def add(self,item,now=None): item.next_run_at=item.next_run_at or self._calculate_first_run(item,now or self._utcnow()); self.schedules[item.schedule_id]=item; self.save(); return item
    def remove(self,schedule_id): self.schedules.pop(schedule_id,None); self.save()
    def pause(self,schedule_id): self.schedules[schedule_id].enabled=False; self.save()
    def resume(self,schedule_id,now=None):
        item=self.schedules[schedule_id]; item.enabled=True
        if item.next_run_at is None: item.next_run_at=self._calculate_first_run(item,now or self._utcnow())
        self.save()
    def due(self,now=None):
        now=now or self._utcnow(); return [x for x in self.schedules.values() if x.enabled and x.next_run_at and self._parse_time(x.next_run_at)<=now]
    def tick(self,now=None):
        now=now or self._utcnow(); triggered=[]
        for item in self.due(now):
            scheduled=self._parse_time(item.next_run_at)
            if item.missed_run_policy=="SKIP" and scheduled<now and item.mode=="ONCE": item.enabled=False; item.next_run_at=None; continue
            runs=1
            if item.mode=="RECURRING" and item.missed_run_policy=="CATCH_UP":
                seconds=self._interval_seconds(item.schedule_expression); runs=1+int((now-scheduled).total_seconds()//seconds); runs=min(runs,item.max_concurrent_runs)
            for _ in range(runs):
                triggered.append(item); item.last_run_at=self._iso(now)
                if self.on_due: self.on_due(item)
            if item.mode=="ONCE": item.enabled=False; item.next_run_at=None
            else:
                seconds=self._interval_seconds(item.schedule_expression); next_run=scheduled+timedelta(seconds=seconds*runs)
                if item.missed_run_policy in {"RUN_ONCE","SKIP"}:
                    while next_run<=now: next_run+=timedelta(seconds=seconds)
                item.next_run_at=self._iso(next_run)
        self.save(); return triggered
    def save(self): self.state_file.parent.mkdir(parents=True,exist_ok=True); self.state_file.write_text(json.dumps([asdict(x) for x in self.schedules.values()],indent=2),encoding="utf-8")
    def load(self):
        if self.state_file.exists(): self.schedules={x["schedule_id"]:Schedule(**x) for x in json.loads(self.state_file.read_text(encoding="utf-8"))}
