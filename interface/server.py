"""FALCON live interface server - standard library only.

The Interface receives a runtime from the composition root; it never imports
another organ's implementation.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

runtime=None

class Handler(BaseHTTPRequestHandler):
    def _send(self,code,data):
        body=json.dumps(data,default=lambda o:o.__dict__).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if runtime is None: return self._send(503,{"error":"runtime_not_configured"})
        if self.path=="/health": self._send(200,{"falcon":"LIVE","heartbeat":runtime.heartbeat().__dict__})
        elif self.path=="/activity": self._send(200,{"events":runtime.memory.recent(100) if runtime.memory else []})
        else: self._send(404,{"error":"not_found"})
    def do_POST(self):
        if runtime is None: return self._send(503,{"error":"runtime_not_configured"})
        if self.path!="/missions": return self._send(404,{"error":"not_found"})
        n=int(self.headers.get("Content-Length","0")); data=json.loads(self.rfile.read(n) or b"{}"); objective=str(data.get("objective","")).strip()
        if not objective: return self._send(400,{"error":"objective_required"})
        self._send(202,{"mission":runtime.accept(objective).__dict__})
    def log_message(self,*_): pass

def serve(app_runtime,host="0.0.0.0",port=8080):
    global runtime; runtime=app_runtime; print(f"FALCON LIVE http://{host}:{port}"); ThreadingHTTPServer((host,port),Handler).serve_forever()
