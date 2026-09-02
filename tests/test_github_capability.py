import base64
import json
import unittest
from bootstrap import build_executor_from_env,build_governance_from_env
from clients.github_http import GitHubHttpClient
from contracts.models import Event
from execution.adapters.github import GitHubAdapter
from execution.registry import Executor

class Response:
    def __init__(self,data):self.data=data
    def read(self):return self.data

class GitHubCapabilityTests(unittest.TestCase):
    def test_public_read_transport_decodes_file_content(self):
        payload={"encoding":"base64","content":base64.b64encode(b"hello Falcon").decode(),"sha":"abc"}
        seen={}
        def opener(request,timeout):seen["url"]=request.full_url; seen["timeout"]=timeout; return Response(json.dumps(payload).encode())
        client=GitHubHttpClient(timeout=7,opener=opener)
        data=client.get_file("owner/repo","README.md")
        self.assertEqual(data["content_text"],"hello Falcon"); self.assertIn("/repos/owner/repo/contents/README.md",seen["url"]); self.assertEqual(seen["timeout"],7)
    def test_write_requires_injected_token(self):
        client=GitHubHttpClient(opener=lambda *_args,**_kwargs:Response(b"{}"))
        with self.assertRaisesRegex(PermissionError,"github_token_required_for_write"):client.create_file("owner/repo","x.txt","x","msg")
    def test_workflow_dispatch_uses_authenticated_post(self):
        seen={}
        def opener(request,timeout):
            seen["url"]=request.full_url; seen["method"]=request.get_method(); seen["body"]=json.loads(request.data.decode()); seen["auth"]=request.headers.get("Authorization"); return Response(b"")
        client=GitHubHttpClient(token="secret",opener=opener)
        self.assertEqual(client.dispatch_workflow("owner/repo","ci.yml",ref="main",inputs={"x":"1"}),{})
        self.assertEqual(seen["method"],"POST"); self.assertIn("/actions/workflows/ci.yml/dispatches",seen["url"]); self.assertEqual(seen["body"],{"ref":"main","inputs":{"x":"1"}}); self.assertEqual(seen["auth"],"Bearer secret")
    def test_executor_blocks_capability_operation_mismatch(self):
        class Client:
            def __init__(self):self.called=False
            def update_file(self,**kwargs):self.called=True; return {"ok":True}
        client=Client(); executor=Executor(); executor.register(GitHubAdapter(client))
        action=Event("ACTION","brain",{"adapter":"github","operation":"update_file","capability":"github.read","args":{"repository":"owner/repo","path":"x","content":"x","message":"m","sha":"s"}})
        result=executor.execute(action)
        self.assertFalse(result.payload["ok"]); self.assertIn("capability_mismatch:github.write",result.payload["message"]); self.assertFalse(client.called)
    def test_write_path_scope_blocks_unrelated_files(self):
        class Client:
            def create_file(self,**kwargs):return {"ok":True}
        executor=Executor(); executor.register(GitHubAdapter(Client(),write_path_prefixes=["artifacts/kra1/"]))
        safe=Event("ACTION","brain",{"adapter":"github","operation":"create_file","capability":"github.write","args":{"repository":"owner/repo","path":"artifacts/kra1/x.txt","content":"x","message":"m"}})
        unsafe=Event("ACTION","brain",{"adapter":"github","operation":"create_file","capability":"github.write","args":{"repository":"owner/repo","path":"README.md","content":"x","message":"m"}})
        self.assertTrue(executor.execute(safe).payload["ok"])
        result=executor.execute(unsafe); self.assertFalse(result.payload["ok"]); self.assertIn("github_write_path_not_allowed",result.payload["message"])
    def test_capability_catalog_exposes_argument_contracts(self):
        executor=build_executor_from_env({"FALCON_GITHUB_WRITE_PATH_PREFIXES":"artifacts/kra1/"})
        items={(x["adapter"],x["operation"]):x for x in executor.capability_catalog()}
        self.assertIn("path",items[("github","update_file")]["arguments"]["required"])
        self.assertIn("sha",items[("github","update_file")]["arguments"]["required"])
        self.assertEqual(executor.adapters["github"].write_path_prefixes,("artifacts/kra1/",))
    def test_composition_allows_public_read_but_write_is_explicit(self):
        executor=build_executor_from_env({}); self.assertTrue(executor.available()["github"])
        self.assertIn("dispatch_workflow",executor.adapters["github"].operations())
        self.assertEqual(build_governance_from_env({}).authorize(Event("ACTION","brain",{"adapter":"github","operation":"get_repository","capability":"github.read","args":{}}))[0],True)
        self.assertEqual(build_governance_from_env({}).authorize(Event("ACTION","brain",{"adapter":"github","operation":"dispatch_workflow","capability":"github.write","args":{}}))[0],False)
        self.assertEqual(build_governance_from_env({"FALCON_GITHUB_WRITE_ENABLED":"true"}).authorize(Event("ACTION","brain",{"adapter":"github","operation":"dispatch_workflow","capability":"github.write","args":{}}))[0],True)

if __name__=="__main__":unittest.main()
