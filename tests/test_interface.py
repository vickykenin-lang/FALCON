import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from interface.server import make_server

class Heartbeat:
    def __init__(self): self.event_type="HEARTBEAT"; self.payload={"status":"HEALTHY"}
class Mission:
    def __init__(self,objective): self.mission_id="m1"; self.objective=objective; self.state="QUEUED"
class Memory:
    def recent(self,n): return [{"event_type":"HEARTBEAT","source":"autonomic","payload":{"status":"HEALTHY"}}]
class Runtime:
    def __init__(self): self.memory=Memory(); self.accepted=[]
    def heartbeat(self): return Heartbeat()
    def accept(self,objective,**_): self.accepted.append(objective); return Mission(objective)

class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.runtime=Runtime(); self.server=make_server(self.runtime,"127.0.0.1",0); self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start(); self.base=f"http://127.0.0.1:{self.server.server_port}"
    def tearDown(self): self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=1)
    def get(self,path,headers=None): return urlopen(Request(self.base+path,headers=headers or {}),timeout=2)
    def test_dashboard_health_and_session(self):
        self.assertIn(b"FALCON",self.get("/").read())
        data=json.loads(self.get("/health").read()); self.assertEqual(data["falcon"],"LIVE")
        session=json.loads(self.get("/session").read()); self.assertFalse(session["founder_auth_required"])
    def test_activity(self):
        data=json.loads(self.get("/activity").read()); self.assertEqual(data["events"][0]["event_type"],"HEARTBEAT")
    def test_create_mission(self):
        req=Request(self.base+"/missions",data=json.dumps({"objective":"inspect project"}).encode(),headers={"Content-Type":"application/json"},method="POST")
        with urlopen(req,timeout=2) as response: self.assertEqual(response.status,202)
        self.assertEqual(self.runtime.accepted,["inspect project"])
    def test_rejects_invalid_json(self):
        req=Request(self.base+"/missions",data=b"{",headers={"Content-Type":"application/json"},method="POST")
        with self.assertRaises(HTTPError) as error: urlopen(req,timeout=2)
        self.assertEqual(error.exception.code,400)
    def test_founder_token_protects_activity_and_missions(self):
        protected=make_server(self.runtime,"127.0.0.1",0,founder_token="founder-secret")
        thread=threading.Thread(target=protected.serve_forever,daemon=True); thread.start(); base=f"http://127.0.0.1:{protected.server_port}"
        try:
            with self.assertRaises(HTTPError) as error:urlopen(base+"/activity",timeout=2)
            self.assertEqual(error.exception.code,401)
            session=json.loads(urlopen(base+"/session",timeout=2).read()); self.assertTrue(session["founder_auth_required"])
            headers={"Authorization":"Bearer founder-secret"}
            data=json.loads(urlopen(Request(base+"/activity",headers=headers),timeout=2).read()); self.assertEqual(data["events"][0]["event_type"],"HEARTBEAT")
            req=Request(base+"/missions",data=json.dumps({"objective":"protected mission"}).encode(),headers={"Content-Type":"application/json",**headers},method="POST")
            with urlopen(req,timeout=2) as response:self.assertEqual(response.status,202)
            self.assertIn("protected mission",self.runtime.accepted)
        finally:
            protected.shutdown(); protected.server_close(); thread.join(timeout=1)

if __name__=="__main__": unittest.main()
