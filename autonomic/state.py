"""Replaceable durable mission-state boundary for Falcon Autonomic.

The Runtime owns mission semantics; backends only persist opaque mission and
operation records. HTTP/D1 or local implementations can be swapped without
changing the Brain, Executor, or mission contracts.
"""
from abc import ABC, abstractmethod
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class MissionStateBackend(ABC):
    @abstractmethod
    def put_mission(self, mission_id: str, payload: dict) -> None: ...
    @abstractmethod
    def get_mission(self, mission_id: str) -> dict | None: ...
    @abstractmethod
    def claim_source(self, source: str, source_id: str, mission_id: str) -> str: ...
    @abstractmethod
    def claim_operation(self, operation_key: str, metadata: dict) -> dict: ...
    @abstractmethod
    def complete_operation(self, operation_key: str, result: dict) -> None: ...


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


class JsonMissionStateBackend(MissionStateBackend):
    """Local durable backend used by containers and tests."""
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def put_mission(self, mission_id: str, payload: dict) -> None:
        _atomic_json(self.root / "missions" / f"{mission_id}.json", payload)

    def get_mission(self, mission_id: str) -> dict | None:
        path = self.root / "missions" / f"{mission_id}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def claim_source(self, source: str, source_id: str, mission_id: str) -> str:
        key = self._digest(f"{source}:{source_id}")
        path = self.root / "sources" / f"{key}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(mission_id)
            return mission_id
        except FileExistsError:
            return path.read_text(encoding="utf-8").strip()

    def claim_operation(self, operation_key: str, metadata: dict) -> dict:
        key = self._digest(operation_key)
        path = self.root / "operations" / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"operation_key": operation_key, "status": "running", "metadata": metadata}
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(record, handle, ensure_ascii=False, indent=2)
            return {"claimed": True, "status": "running", "result": None}
        except FileExistsError:
            current = json.loads(path.read_text(encoding="utf-8"))
            return {"claimed": False, "status": current.get("status", "running"), "result": current.get("result")}

    def complete_operation(self, operation_key: str, result: dict) -> None:
        key = self._digest(operation_key)
        path = self.root / "operations" / f"{key}.json"
        current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"operation_key": operation_key}
        current.update({"status": "completed", "result": result})
        _atomic_json(path, current)


class HttpMissionStateBackend(MissionStateBackend):
    """Remote state adapter for Falcon's authenticated Cloudflare state API."""
    def __init__(self, endpoint: str, token: str, timeout: float = 20.0, opener=None):
        self.endpoint = str(endpoint).rstrip("/")
        self.token = str(token).strip()
        self.timeout = float(timeout)
        self.opener = opener or urlopen
        if not self.endpoint: raise ValueError("state_endpoint_required")
        if not self.token: raise ValueError("state_token_required")
        if self.timeout <= 0: raise ValueError("state_timeout_must_be_positive")

    def _request(self, method: str, path: str, payload: dict | None = None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.token}"}
        if body is not None: headers["Content-Type"] = "application/json"
        request = Request(f"{self.endpoint}{path}", data=body, headers=headers, method=method)
        try:
            raw = self.opener(request, timeout=self.timeout).read()
        except HTTPError as exc:
            if exc.code == 404 and method == "GET": return None
            detail = ""
            try:
                error_raw = exc.read()
                if error_raw:
                    parsed = json.loads(error_raw)
                    if isinstance(parsed, dict) and parsed.get("error") == "state_forbidden":
                        bounded = {
                            "configured_length": parsed.get("configured_length"),
                            "supplied_length": parsed.get("supplied_length"),
                            "configured_matches_expected": parsed.get("configured_matches_expected"),
                            "supplied_matches_expected": parsed.get("supplied_matches_expected"),
                            "bearer_prefix": parsed.get("bearer_prefix"),
                        }
                        detail = f":diag={json.dumps(bounded, separators=(',', ':'))}"
            except Exception:
                detail = ""
            raise RuntimeError(f"state_http_error:{exc.code}{detail}") from exc
        except URLError as exc:
            raise RuntimeError("state_backend_unreachable") from exc
        if not raw: return {}
        try: return json.loads(raw)
        except (TypeError, ValueError) as exc: raise RuntimeError("state_backend_invalid_json") from exc

    def put_mission(self, mission_id: str, payload: dict) -> None:
        self._request("PUT", f"/state/missions/{quote(mission_id, safe='')}", payload)

    def get_mission(self, mission_id: str) -> dict | None:
        data = self._request("GET", f"/state/missions/{quote(mission_id, safe='')}")
        return data.get("mission") if isinstance(data, dict) else None

    def claim_source(self, source: str, source_id: str, mission_id: str) -> str:
        data = self._request("POST", "/state/sources/claim", {"source": source, "source_id": source_id, "mission_id": mission_id})
        resolved = str((data or {}).get("mission_id", "")).strip()
        if not resolved: raise RuntimeError("state_source_claim_invalid")
        return resolved

    def claim_operation(self, operation_key: str, metadata: dict) -> dict:
        data = self._request("POST", "/state/operations/claim", {"operation_key": operation_key, "metadata": metadata})
        if not isinstance(data, dict): raise RuntimeError("state_operation_claim_invalid")
        return data

    def complete_operation(self, operation_key: str, result: dict) -> None:
        self._request("POST", "/state/operations/complete", {"operation_key": operation_key, "result": result})
