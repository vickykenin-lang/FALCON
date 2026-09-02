import json
import os
import unittest
from unittest.mock import patch

from bootstrap import build_brain_from_env
from brain.engine import Brain
from brain.providers.deterministic import DeterministicProvider
from brain.providers.json_http import JsonHttpProvider
from contracts.models import Mission

class Response:
    def __init__(self,data): self.data=data
    def read(self): return self.data

class IntelligenceProviderTests(unittest.TestCase):
    def test_deterministic_provider_passes_strict_brain_validation(self):
        brain=Brain(DeterministicProvider("safe","inspect","safe.inspect"))
        mission=Mission("inspect project")
        event=brain.plan(mission)
        action=event.payload["plan"]["actions"][0]
        self.assertEqual(action["capability"],"safe.inspect")
    def test_json_http_provider_is_contract_neutral(self):
        captured={}
        plan={"summary":"Inspect","actions":[{"adapter":"safe","operation":"inspect","capability":"safe.inspect","args":{}}],"success_criteria":["ok"]}
        def opener(request,timeout):
            captured["body"]=json.loads(request.data); captured["timeout"]=timeout
            return Response(json.dumps(plan).encode())
        provider=JsonHttpProvider("https://intelligence.example/decide",timeout=7,opener=opener)
        self.assertEqual(provider.decide("mission",{"x":1}),plan)
        self.assertEqual(captured["body"]["objective"],"mission"); self.assertEqual(captured["timeout"],7)
    def test_json_http_provider_rejects_bad_response(self):
        provider=JsonHttpProvider("https://intelligence.example/decide",opener=lambda *_args,**_kwargs:Response(b"not-json"))
        with self.assertRaisesRegex(RuntimeError,"intelligence_invalid_json"): provider.decide("x",{})
    def test_composition_fails_closed_without_intelligence_config(self):
        brain=build_brain_from_env({})
        self.assertFalse(brain.available())
    def test_composition_supports_explicit_deterministic_mode(self):
        brain=build_brain_from_env({"FALCON_INTELLIGENCE_MODE":"deterministic"})
        self.assertTrue(brain.available()); self.assertIsInstance(brain.provider,DeterministicProvider)
    def test_composition_builds_json_http_provider_without_storing_credentials(self):
        env={"FALCON_INTELLIGENCE_MODE":"json_http","FALCON_INTELLIGENCE_ENDPOINT":"https://intelligence.example/decide","FALCON_INTELLIGENCE_TOKEN":"secret-value","FALCON_INTELLIGENCE_TIMEOUT":"9"}
        brain=build_brain_from_env(env)
        self.assertIsInstance(brain.provider,JsonHttpProvider); self.assertEqual(brain.provider.endpoint,env["FALCON_INTELLIGENCE_ENDPOINT"]); self.assertEqual(brain.provider.timeout,9.0); self.assertEqual(brain.provider.headers["Authorization"],"Bearer secret-value")
    def test_composition_rejects_unknown_mode(self):
        with self.assertRaisesRegex(ValueError,"unsupported_intelligence_mode"):build_brain_from_env({"FALCON_INTELLIGENCE_MODE":"mystery"})

if __name__=="__main__": unittest.main()
