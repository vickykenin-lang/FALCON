"""FALCON live Founder interface - standard library only.

The Interface receives a runtime from the composition root; it never imports
another organ's implementation. Founder authentication is optional locally and
can be enabled through FALCON_FOUNDER_TOKEN for deployed environments.
"""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

DASHBOARD=Path(__file__).with_name("dashboard.html")
TERMINAL_STATES={"SUCCEEDED","FAILED","BLOCKED","CANCELLED"}

class Handler(BaseHTTPRequestHandler):
    @property
    def app_runtime(self):
        return getattr(self.server,"app_runtime",None)

    def _cors(self):
        origin=getattr(self.server,"allowed_origin",None)
        if origin:self.send_header("Access-Control-Allow-Origin",origin)

    def _send(self,code,data):
        body=json.dumps(data,default=lambda o:o.__dict__).encode()
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _html(self):
        body=DASHBOARD.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        expected=getattr(self.server,"founder_token",None)
        if not expected:return True
        supplied=""
        auth=self.headers.get("Authorization","")
        if auth.startswith("Bearer "):supplied=auth[7:].strip()
        if not supplied:supplied=self.headers.get("X-Falcon-Founder-Token","").strip()
        return bool(supplied) and hmac.compare_digest(str(expected),supplied)

    def _require_founder(self):
        if self._authorized():return True
        self._send(401,{"error":"founder_auth_required"})
        return False

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Headers","Authorization, Content-Type, X-Falcon-Founder-Token")
        self.send_header("Access-Control-Allow-Methods","GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self.path in {"/","/dashboard"}:return self._html()
        if self.path=="/session":return self._send(200,{"falcon":"LIVE","founder_auth_required":bool(getattr(self.server,"founder_token",None))})
        runtime=self.app_runtime
        if runtime is None:return self._send(503,{"error":"runtime_not_configured"})
        if self.path=="/health":return self._send(200,{"falcon":"LIVE","heartbeat":runtime.heartbeat().__dict__})
        if self.path=="/activity":
            if not self._require_founder():return
            return self._send(200,{"events":runtime.memory.recent(100) if runtime.memory else []})
        return self._send(404,{"error":"not_found"})

    def do_POST(self):
        runtime=self.app_runtime
        if runtime is None:return self._send(503,{"error":"runtime_not_configured"})
        if self.path!="/missions":return self._send(404,{"error":"not_found"})
        if not self._require_founder():return
        try:
            n=int(self.headers.get("Content-Length","0"))
            data=json.loads(self.rfile.read(n) or b"{}")
        except (ValueError,json.JSONDecodeError):return self._send(400,{"error":"invalid_json"})
        objective=str(data.get("objective","")).strip()
        if not objective:return self._send(400,{"error":"objective_required"})
        mission=runtime.accept(objective,acceptance_criteria=data.get("acceptance_criteria"),context=data.get("context"))
        driver=getattr(runtime,"driver",None)
        if driver is not None:mission=driver.run(mission,context=data.get("context"))
        status=getattr(mission,"status",getattr(mission,"state",None))
        self._send(200 if driver is not None and status in TERMINAL_STATES else 202,{"mission":mission.__dict__})

    def log_message(self,*_):pass

def make_server(app_runtime,host="0.0.0.0",port=8080,founder_token=None,allowed_origin=None):
    server=ThreadingHTTPServer((host,port),Handler)
    server.app_runtime=app_runtime
    server.founder_token=founder_token if founder_token is not None else os.environ.get("FALCON_FOUNDER_TOKEN")
    server.allowed_origin=allowed_origin if allowed_origin is not None else os.environ.get("FALCON_ALLOWED_ORIGIN")
    return server

def serve(app_runtime,host="0.0.0.0",port=8080):
    server=make_server(app_runtime,host,port)
    print(f"FALCON LIVE http://{host}:{port}")
    try:server.serve_forever()
    finally:server.server_close()
