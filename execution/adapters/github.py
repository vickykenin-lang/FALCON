"""GitHub execution adapter boundary.

Credentials are injected through environment/runtime configuration; never stored here.
The transport client is injected so Falcon core remains provider-independent.
"""
from execution.adapters.base import ExecutionAdapter


class GitHubAdapter(ExecutionAdapter):
    name = "github"

    def __init__(self, client=None):
        self.client = client

    def available(self) -> bool:
        return self.client is not None

    def execute(self, action: str, **kwargs):
        if not self.client:
            raise RuntimeError("github_client_not_configured")
        fn = getattr(self.client, action, None)
        if not callable(fn):
            raise ValueError(f"unsupported_github_action:{action}")
        return fn(**kwargs)
