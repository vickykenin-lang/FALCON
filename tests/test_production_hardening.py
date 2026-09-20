import json
import threading
import unittest

from brain.engine import Brain
from brain.providers.failover import FailoverProvider
from contracts.models import Event, Mission
from execution.adapters.base import ExecutionAdapter
from execution.registry import Executor
import task_runner


VALID_PLAN = {
    "summary": "safe fallback plan",
    "actions": [{"adapter": "github", "operation": "get_repository", "capability": "github.read", "args": {"repository": "owner/repo"}, "risk": "low"}],
    "success_criteria": ["repository_read"],
    "needs_more_context": False,
}


class Provider:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0
    def decide(self, objective, context):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


class RecordingAdapter(ExecutionAdapter):
    name = "recording"
    def __init__(self):
        self.calls = 0
        self.operation_ids = []
    def available(self): return True
    def operations(self): return ["write"]
    def required_capability(self, operation): return "recording.write"
    def execute(self, operation, *, execution_context=None, **kwargs):
        self.calls += 1
        self.operation_ids.append(execution_context.operation_id if execution_context else None)
        return {"ok": True, "echo": kwargs.get("value")}


class ProductionHardeningTests(unittest.TestCase):
    def test_capability_mismatch_fails_closed_without_side_effect(self):
        adapter = RecordingAdapter(); executor = Executor(); executor.register(adapter)
        action = Event("ACTION", "brain", {"adapter": "recording", "operation": "write", "capability": "recording.read", "args": {"value": "x"}}, correlation_id="m1")
        result = executor.execute(action, operation_id="op1")
        self.assertEqual(result.event_type, "FAILURE")
        self.assertEqual(adapter.calls, 0)
        self.assertEqual(result.payload["error"], "PermissionError")

    def test_stable_operation_id_reaches_adapter_for_idempotency(self):
        adapter = RecordingAdapter(); executor = Executor(); executor.register(adapter)
        action = Event("ACTION", "brain", {"adapter": "recording", "operation": "write", "capability": "recording.write", "args": {"value": "x"}}, correlation_id="m1")
        first = executor.execute(action, operation_id="stable-op")
        second = executor.execute(action, operation_id="stable-op")
        self.assertTrue(first.payload["ok"] and second.payload["ok"])
        self.assertEqual(adapter.operation_ids, ["stable-op", "stable-op"])

    def test_provider_failure_is_isolated_and_fallback_used(self):
        primary = Provider(error=TimeoutError("primary unavailable")); fallback = Provider(result=VALID_PLAN)
        provider = FailoverProvider([("primary", primary), ("fallback", fallback)])
        event = Brain(provider).plan(Mission("inspect"))
        self.assertEqual(event.event_type, "DECISION")
        self.assertEqual(provider.last_provider, "fallback")
        self.assertEqual((primary.calls, fallback.calls), (1, 1))

    def test_all_provider_failure_fails_closed_without_secret_material(self):
        provider = FailoverProvider([("a", Provider(error=RuntimeError("token=supersecret"))), ("b", Provider(error=RuntimeError("api_key=supersecret")))])
        event = Brain(provider).plan(Mission("inspect"))
        serialized = json.dumps(event.payload).lower()
        self.assertEqual(event.event_type, "FAILURE")
        self.assertEqual(event.payload["error"], "intelligence_provider_failed")
        self.assertNotIn("supersecret", serialized)
        self.assertNotIn("token=", serialized)
        self.assertNotIn("api_key=", serialized)

    def test_bounded_evidence_drops_credentials_and_nested_untrusted_payload(self):
        observed = {"ok": True, "token": "secret", "api_key": "secret", "authorization": "Bearer secret", "content": {"path": "artifacts/kra1/x.txt", "secret": "secret"}, "commit": {"sha": "abc", "author": {"email": "private@example.com"}}}
        evidence = task_runner._bounded_evidence(observed)
        self.assertEqual(evidence, {"ok": True, "commit_sha": "abc", "path": "artifacts/kra1/x.txt"})
        self.assertNotIn("secret", json.dumps(evidence).lower())


if __name__ == "__main__":
    unittest.main()
