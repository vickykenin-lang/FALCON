"""FALCON live interface server - standard library only.

The Interface receives a runtime from the composition root; it never imports
another organ's implementation.
"""
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

runtime=None
DASHBOARD=Path(__file__).with_name("dashboard.html")

class Handler(BaseHTTPRequestHandler):
    def _send(self,code,data):
        body=json.dumps(data,default=lambda o:o.__dict__).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers(); self.wfile.write(body)
    def _html(self):
        body=DASHBOARD.read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path in {"/","/dashboard"}:return self._html()
        if runtime is None:return self._send(503,{"error":"runtime_not_configured"})
        if self.path=="/health":self._send(200,{"falcon":"LIVE","heartbeat":runtime.heartbeat().__dict__})
        elif self.path=="/activity":self._send(200,{"events":runtime.memory.recent(100) if runtime.memory else []})
        else:self._send(404,{"error":"not_found"})
    def do_POST(self):
        if runtime is None:return self._send(503,{"error":"runtime_not_configured"})
        if self.path!="/missions":return self._send(404,{"error":"not_found"})
        try:n=int(self.headers.get("Content-Length","0")); data=json.loads(self.rfile.read(n) or b"{}")
        except (ValueError,json.JSONDecodeError):return self._send(400,{"error":"invalid_json"})
        objective=str(data.get("objective","")).strip()
        if not objective:return self._send(400,{"error":"objective_required"})
        mission=runtime.accept(objective,acceptance_criteria=data.get("acceptance_criteria"),context=data.get("context"))
        if getattr(runtime,"driver",None) is not None:mission=runtime.driver.run(mission,context=data.get("context"))
        self._send(200 if mission.status in {"SUCCEEDED","FAILED","BLOCKED","CANCELLED"} else 202,{"mission":mission.__dict__})
    def log_message(self,*_):pass

def make_server(app_runtime,host="0.0.0.0",port=8080):
    global runtime; runtime=app_runtime; return ThreadingHTTPServer((host,port),Handler)
def serve(app_runtime,host="0.0.0.0",port=8080):
    server=make_server(app_runtime,host,port); print(f"FALCON LIVE http://{host}:{port}")
    try:server.serve_forever()
    finally:server.server_close()
