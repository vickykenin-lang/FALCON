"""GitHub execution adapter boundary.

Credentials are injected through environment/runtime configuration; never stored here.
The transport client is injected so Falcon core remains provider-independent.
"""
class GitHubAdapter:
    name = "github"
    def __init__(self, client=None): self.client=client
    def available(self): return self.client is not None
    def execute(self, action, **kwargs):
        if not self.client: raise RuntimeError("github_client_not_configured")
        fn=getattr(self.client, action, None)
        if not callable(fn): raise ValueError(f"unsupported_github_action:{action}")
        return fn(**kwargs)
