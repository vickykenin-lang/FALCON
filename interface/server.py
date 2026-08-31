"""FALCON live interface server - standard library only."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from autonomic.runtime import Runtime

runtime = Runtime()

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, data):
        body=json.dumps(data, default=lambda o:o.__dict__).encode()
        self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path == '/health': self._send(200, {'falcon':'LIVE','heartbeat':runtime.heartbeat().__dict__})
        elif self.path == '/activity': self._send(200, {'events':[e.__dict__ for e in runtime.memory.recent(100)]})
        else: self._send(404, {'error':'not_found'})
    def do_POST(self):
        if self.path != '/missions': return self._send(404, {'error':'not_found'})
        n=int(self.headers.get('Content-Length','0')); data=json.loads(self.rfile.read(n) or b'{}')
        objective=str(data.get('objective','')).strip()
        if not objective: return self._send(400, {'error':'objective_required'})
        self._send(202, {'mission':runtime.accept(objective).__dict__})
    def log_message(self, *_): pass

def serve(host='0.0.0.0', port=8080):
    print(f'FALCON LIVE http://{host}:{port}')
    ThreadingHTTPServer((host,port), Handler).serve_forever()

if __name__ == '__main__': serve()
