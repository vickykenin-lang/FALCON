"""Governed public-web read adapter.

Read-only HTTP capability kept outside Falcon Brain.  Only explicit http/https
URLs are accepted; writes and credential injection are intentionally absent.
"""
from __future__ import annotations
import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from execution.adapters.base import ExecutionAdapter, ExecutionRequest, ExecutionResult

class WebReadAdapter(ExecutionAdapter):
    name = "web"
    required_capabilities = {"get": "web.read"}

    def __init__(self, timeout_seconds: int = 10, max_bytes: int = 262144):
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if request.operation != "get":
            return ExecutionResult(False, error="operation_not_supported")
        url = str(request.params.get("url", ""))
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return ExecutionResult(False, error="invalid_public_url")
        try:
            req = Request(url, method="GET", headers={"User-Agent":"Falcon/1.0 governed-web-read"})
            with urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read(self.max_bytes + 1)
                if len(body) > self.max_bytes:
                    return ExecutionResult(False, error="response_too_large")
                text = body.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
                return ExecutionResult(True, output={"url":response.geturl(),"status":response.status,"content_type":response.headers.get_content_type(),"body":text})
        except Exception as exc:
            return ExecutionResult(False, error=f"{type(exc).__name__}:{exc}")
