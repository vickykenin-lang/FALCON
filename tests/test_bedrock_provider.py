import json
import unittest
from brain.providers.bedrock import BedrockProvider


class FakeBedrock:
    def __init__(self): self.calls=[]
    def converse(self, **kwargs):
        self.calls.append(kwargs)
        plan={"summary":"bedrock ok","actions":[],"success_criteria":["real provider contract preserved"]}
        return {"output":{"message":{"content":[{"text":json.dumps(plan)}]}}}


class BedrockProviderTests(unittest.TestCase):
    def test_requires_model(self):
        with self.assertRaisesRegex(ValueError,"bedrock_model_required"):
            BedrockProvider("")

    def test_converse_returns_structured_plan(self):
        client=FakeBedrock()
        provider=BedrockProvider("test.model",region="ap-south-1",client=client)
        result=provider.decide("own project",{"repo":"AURA3"})
        self.assertEqual(result["summary"],"bedrock ok")
        call=client.calls[0]
        self.assertEqual(call["modelId"],"test.model")
        self.assertEqual(call["inferenceConfig"]["temperature"],0)
        self.assertIn("own project",call["messages"][0]["content"][0]["text"])

    def test_invalid_model_output_fails_closed(self):
        class Bad:
            def converse(self,**kwargs): return {"output":{"message":{"content":[{"text":"not-json"}]}}}
        with self.assertRaisesRegex(RuntimeError,"bedrock_invalid_plan_response"):
            BedrockProvider("test.model",client=Bad()).decide("x",{})

if __name__ == "__main__": unittest.main()
