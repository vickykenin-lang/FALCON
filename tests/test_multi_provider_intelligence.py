import json
import unittest

from bootstrap import build_brain_from_env
from brain.engine import Brain
from brain.providers.deepseek import DeepSeekProvider
from brain.providers.failover import FailoverProvider
from brain.providers.gemini import GeminiProvider
from contracts.models import Mission


VALID_PLAN = {
    "summary": "Inspect repository",
    "actions": [{"adapter": "github", "operation": "get_repository", "capability": "github.read", "args": {"repository": "owner/repo"}, "risk": "low"}],
    "success_criteria": ["repository_read"],
    "needs_more_context": False,
}


class Response:
    def __init__(self, data): self.data = data
    def read(self): return self.data


class Provider:
    def __init__(self, result=None, error=None): self.result = result; self.error = error; self.calls = 0
    def decide(self, objective, context):
        self.calls += 1
        if self.error: raise self.error
        return self.result


class MultiProviderIntelligenceTests(unittest.TestCase):
    def test_deepseek_uses_responses_json_schema_and_returns_plan(self):
        captured = {}
        body = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(VALID_PLAN)}]}]}
        def opener(request, timeout):
            captured["body"] = json.loads(request.data); captured["headers"] = dict(request.header_items()); captured["timeout"] = timeout; captured["url"] = request.full_url
            return Response(json.dumps(body).encode())
        provider = DeepSeekProvider("secret", model="deepseek-test", timeout=9, opener=opener)
        self.assertEqual(provider.decide("inspect", {"execution_capabilities": []}), VALID_PLAN)
        self.assertEqual(captured["body"]["model"], "deepseek-test")
        self.assertEqual(captured["body"]["reasoning"], {"effort": "none"})
        self.assertEqual(captured["body"]["text"]["format"]["type"], "json_schema")
        self.assertEqual(captured["body"]["text"]["format"]["name"], "falcon_plan")
        self.assertEqual(captured["body"]["text"]["format"]["schema"]["type"], "object")
        self.assertTrue(captured["url"].endswith("/responses"))
        self.assertEqual(captured["timeout"], 9)
        self.assertTrue(any(k.lower() == "authorization" and v == "Bearer secret" for k, v in captured["headers"].items()))

    def test_gemini_uses_structured_json_schema_and_returns_plan(self):
        captured = {}
        body = {"candidates": [{"content": {"parts": [{"text": json.dumps(VALID_PLAN)}]}}]}
        def opener(request, timeout):
            captured["body"] = json.loads(request.data); captured["headers"] = dict(request.header_items()); captured["url"] = request.full_url
            return Response(json.dumps(body).encode())
        provider = GeminiProvider("secret", model="gemini-test", opener=opener)
        self.assertEqual(provider.decide("inspect", {}), VALID_PLAN)
        self.assertIn("gemini-test:generateContent", captured["url"])
        config = captured["body"]["generationConfig"]
        self.assertEqual(config["responseMimeType"], "application/json")
        self.assertEqual(config["responseJsonSchema"]["type"], "object")
        self.assertTrue(any(k.lower() == "x-goog-api-key" and v == "secret" for k, v in captured["headers"].items()))

    def test_gemini_retries_transient_timeout_then_succeeds(self):
        calls = {"count": 0}; sleeps = []
        body = {"candidates": [{"content": {"parts": [{"text": json.dumps(VALID_PLAN)}]}}]}
        def opener(request, timeout):
            calls["count"] += 1
            if calls["count"] == 1: raise TimeoutError("planned_timeout")
            return Response(json.dumps(body).encode())
        provider = GeminiProvider("secret", opener=opener, max_attempts=2, retry_delay=0.25, sleeper=sleeps.append)
        self.assertEqual(provider.decide("inspect", {}), VALID_PLAN)
        self.assertEqual(calls["count"], 2)
        self.assertEqual(sleeps, [0.25])

    def test_failover_moves_from_primary_failure_to_gemini(self):
        primary = Provider(error=RuntimeError("primary_down")); fallback = Provider(result=VALID_PLAN)
        provider = FailoverProvider([("deepseek", primary), ("gemini", fallback)])
        plan = provider.decide("x", {})
        self.assertEqual(plan["summary"], VALID_PLAN["summary"])
        self.assertEqual(provider.last_provider, "gemini")
        self.assertEqual(primary.calls, 1); self.assertEqual(fallback.calls, 1)
        self.assertTrue(provider.status()["fallback_available"])

    def test_failover_rejects_invalid_primary_plan_before_fallback(self):
        primary = Provider(result={"summary": "broken"}); fallback = Provider(result=VALID_PLAN)
        provider = FailoverProvider([("deepseek", primary), ("gemini", fallback)])
        self.assertEqual(provider.decide("x", {})["summary"], VALID_PLAN["summary"])
        self.assertEqual(provider.last_provider, "gemini")

    def test_auto_composition_prefers_deepseek_and_configures_gemini_fallback(self):
        brain = build_brain_from_env({"FALCON_DEEPSEEK_API_KEY": "d", "FALCON_GEMINI_API_KEY": "g", "FALCON_GEMINI_MAX_ATTEMPTS": "3"})
        self.assertIsInstance(brain.provider, FailoverProvider)
        self.assertEqual([name for name, _ in brain.provider.providers], ["deepseek", "gemini"])
        gemini = brain.provider.providers[1][1]
        self.assertEqual(gemini.max_attempts, 3)

    def test_auto_composition_accepts_single_live_provider(self):
        deepseek_brain = build_brain_from_env({"FALCON_DEEPSEEK_API_KEY": "d"})
        gemini_brain = build_brain_from_env({"FALCON_GEMINI_API_KEY": "g"})
        self.assertIsInstance(deepseek_brain.provider, DeepSeekProvider)
        self.assertIsInstance(gemini_brain.provider, GeminiProvider)

    def test_brain_fails_closed_when_all_live_providers_fail(self):
        provider = FailoverProvider([("deepseek", Provider(error=RuntimeError("down"))), ("gemini", Provider(error=RuntimeError("down")))])
        event = Brain(provider).plan(Mission("test"))
        self.assertEqual(event.event_type, "FAILURE")
        self.assertEqual(event.payload["error"], "intelligence_provider_failed")
        self.assertNotIn("secret", json.dumps(event.payload).lower())


if __name__ == "__main__": unittest.main()
