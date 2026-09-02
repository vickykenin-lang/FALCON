"""Authenticated remote implementation of Falcon's stable Memory backend."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from memory.base import MemoryBackend


class HttpMemoryBackend(MemoryBackend):
    def __init__(self, endpoint: str, token: str, timeout: float = 20.0, opener=None):
        self.endpoint = str(endpoint).rstrip("/")
        self.token = str(token).strip()
        self.timeout = float(timeout)
        self.opener = opener or urlopen
        if not self.endpoint: raise ValueError("memory_endpoint_required")
        if not self.token: raise ValueError("memory_token_required")
        if self.timeout <= 0: raise ValueError("memory_timeout_must_be_positive")

    def _request(self, method: str, path: str, payload: dict | None = None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.token}"}
        if body is not None: headers["Content-Type"] = "application/json"
        request = Request(f"{self.endpoint}{path}", data=body, headers=headers, method=method)
        try:
            raw = self.opener(request, timeout=self.timeout).read()
        except HTTPError as exc:
            raise RuntimeError(f"memory_http_error:{exc.code}") from exc
        except URLError as exc:
            raise RuntimeError("memory_backend_unreachable") from exc
        if not raw: return {}
        try: return json.loads(raw)
        except (TypeError, ValueError) as exc: raise RuntimeError("memory_backend_invalid_json") from exc

    def append(self, item: dict) -> None:
        self._request("POST", "/state/memory", {"event": item})

    def recent(self, limit: int) -> list[dict]:
        if limit <= 0: return []
        data = self._request("GET", f"/state/memory?{urlencode({'limit': min(int(limit), 250)})}")
        items = data.get("events", []) if isinstance(data, dict) else []
        if not isinstance(items, list): raise RuntimeError("memory_backend_events_invalid")
        return [item for item in items if isinstance(item, dict)]
