"""Canonical Falcon plan contract shared by Brain and intelligence providers."""

PLAN_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "adapter": {"type": "string"},
                    "operation": {"type": "string"},
                    "capability": {"type": "string"},
                    "args": {"type": "object", "additionalProperties": True},
                    "risk": {"type": "string"},
                },
                "required": ["adapter", "operation", "capability", "args", "risk"],
            },
        },
        "success_criteria": {"type": "array", "items": {"type": "string"}},
        "needs_more_context": {"type": "boolean"},
    },
    "required": ["summary", "actions", "success_criteria", "needs_more_context"],
}


def planning_instructions() -> str:
    return (
        "Return one valid JSON Falcon plan with summary, actions, success_criteria, and needs_more_context. "
        "Each action must contain adapter, operation, capability, args object, and risk. "
        "Use only operations listed in context.execution_capabilities when present and obey each operation's arguments contract. "
        "Never invent credentials, permissions, tools, adapters, repository names, runtime-generated IDs, SHAs, or evidence. "
        "If a later action would require an argument produced only by an earlier runtime action, prefer an available atomic operation whose contract resolves that dependency internally. "
        "If no such safe operation exists and the required value is unavailable, request more context instead of guessing it. "
        "If required operational context is unavailable, set needs_more_context=true and actions=[]. "
        "Prefer the smallest safe action sequence that can produce verifiable evidence. "
        "On retries, adapt using previous_evidence and verification rather than repeating blindly."
    )


def normalize_plan(plan: dict) -> dict:
    if not isinstance(plan, dict):
        raise ValueError("plan_must_be_object")
    summary = plan.get("summary")
    actions = plan.get("actions")
    criteria = plan.get("success_criteria")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("plan_summary_required")
    if not isinstance(actions, list):
        raise ValueError("plan_actions_required")
    if not isinstance(criteria, list):
        raise ValueError("success_criteria_required")
    normalized = []
    for action in actions:
        if not isinstance(action, dict) or not action.get("adapter") or not action.get("operation"):
            raise ValueError("invalid_plan_action")
        capability = action.get("capability")
        args = action.get("args", {})
        if not isinstance(capability, str) or not capability.strip():
            raise ValueError("action_capability_required")
        if not isinstance(args, dict):
            raise ValueError("action_args_must_be_object")
        normalized.append({
            "adapter": str(action["adapter"]),
            "operation": str(action["operation"]),
            "capability": capability.strip(),
            "args": args,
            "risk": str(action.get("risk", "low")),
        })
    return {
        "summary": summary.strip(),
        "actions": normalized,
        "success_criteria": criteria,
        "needs_more_context": bool(plan.get("needs_more_context", False)),
        "contract_version": "1.0",
    }
