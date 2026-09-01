"""Founder-direct capability governance gate."""
from contracts.models import Event

class Governance:
    def __init__(self,allowed_capabilities:set[str]|None=None,require_capability:bool=True):
        self.allowed_capabilities=set(allowed_capabilities or [])
        self.require_capability=require_capability
    def allow(self,*capabilities:str): self.allowed_capabilities.update(capabilities)
    def revoke(self,*capabilities:str):
        for capability in capabilities: self.allowed_capabilities.discard(capability)
    def authorize(self,event:Event)->tuple[bool,str]:
        if event.event_type!="ACTION": return True,"non_action"
        risk=event.payload.get("risk","low")
        if risk=="restricted": return False,"restricted_action"
        if risk=="credential_required" and not event.payload.get("credential_available"): return False,"credential_required"
        capability=event.payload.get("capability")
        if self.require_capability and (not isinstance(capability,str) or not capability.strip()): return False,"capability_required"
        if capability and capability not in self.allowed_capabilities: return False,f"capability_not_allowed:{capability}"
        return True,"authorized"
