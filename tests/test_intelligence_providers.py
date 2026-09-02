import json
import unittest

from bootstrap import build_brain_from_env
from brain.engine import Brain
from brain.providers.deterministic import DeterministicProvider
from brain.providers.json_http import JsonHttpProvider
from brain.providers.openai_responses import OpenAIResponsesProvider
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

    def test_openai_provider_requests_structured_falcon_plan(self):
        captured={}
        plan={"summary":"Inspect","actions":[{"adapter":"github","operation":"get_repository","capability":"github.read","args":{"repository":"owner/repo"},"risk":"low"}],"success_criteria":["repository_read"],"needs_more_context":False}
        body={"output":[{"type":"message","content":[{"type":"output_text","text":json.dumps(plan)}]}]}
        def opener(request,timeout):
            captured["request"]=request; captured["body"]=json.loads(request.data); captured["timeout"]=timeout
            return Response(json.dumps(body).encode())
        provider=OpenAIResponsesProvider("secret-key",model="model-x",timeout=11,opener=opener)
        self.assertEqual(provider.decide("inspect",{"execution_capabilities":[]}),plan)
        self.assertEqual(captured["body"]["model"],"model-x")
        self.assertEqual(captured["body"]["text"]["format"]["type"],"json_schema")
        self.assertTrue(captured["body"]["text"]["format"]["strict"])
        self.assertEqual(captured["timeout"],11)
        self.assertEqual(captured["request"].headers["Authorization"],"Bearer secret-key")

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

    def test_composition_builds_openai_provider_from_external_secret(self):
        env={"FALCON_INTELLIGENCE_MODE":"openai","FALCON_OPENAI_API_KEY":"secret-value","FALCON_OPENAI_MODEL":"model-x","FALCON_INTELLIGENCE_TIMEOUT":"13"}
        brain=build_brain_from_env(env)
        self.assertIsInstance(brain.provider,OpenAIResponsesProvider)
        self.assertEqual(brain.provider.model,"model-x"); self.assertEqual(brain.provider.timeout,13.0)

    def test_openai_mode_requires_key(self):
        with self.assertRaisesRegex(ValueError,"falcon_openai_api_key_required"):
            build_brain_from_env({"FALCON_INTELLIGENCE_MODE":"openai"})

    def test_composition_rejects_unknown_mode(self):
        with self.assertRaisesRegex(ValueError,"unsupported_intelligence_mode"):build_brain_from_env({"FALCON_INTELLIGENCE_MODE":"mystery"})

if __name__=="__main__": unittest.main()
