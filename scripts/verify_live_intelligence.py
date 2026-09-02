"""Live intelligence acceptance for Falcon production providers.

This script intentionally emits only bounded status evidence. It never prints
API keys or raw provider responses.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from bootstrap import build_runtime, run_mission
from brain.engine import Brain
from brain.providers.deepseek import DeepSeekProvider
from brain.providers.failover import FailoverProvider
from brain.providers.gemini import GeminiProvider
from execution.adapters.noop import NoopAdapter
from execution.registry import Executor
from governance.policy import Governance


OBJECTIVE = (
    "Use only the available noop.inspect capability exactly once to verify the "
    "Falcon live intelligence integration. Do not request any unavailable tool, "
    "credential, repository, or external action."
)


class ForcedFailureProvider:
    def decide(self, objective: str, context: dict) -> dict:
        raise RuntimeError("forced_primary_failure_for_acceptance")


def _executor() -> Executor:
    executor = Executor()
    executor.register(NoopAdapter())
    return executor


def _safe_brain_failure(runtime) -> dict | None:
    if runtime.memory is None:
        return None
    for event in reversed(runtime.memory.recent(100)):
        if event.get("event_type") == "FAILURE" and event.get("source") == "brain":
            payload = event.get("payload") or {}
            return {
                "error": str(payload.get("error", ""))[:120],
                "provider_error": str(payload.get("provider_error", ""))[:120],
                "detail": str(payload.get("detail", ""))[:300],
            }
    return None


def _run_provider(name: str, provider) -> dict:
    with tempfile.TemporaryDirectory() as state_dir:
        runtime = build_runtime(
            state_dir,
            brain=Brain(provider),
            executor=_executor(),
            governance=Governance({"noop.inspect"}),
        )
        mission = run_mission(
            runtime,
            OBJECTIVE,
            acceptance_criteria={"execution_result_ok": True},
            context={"acceptance_test": "live_intelligence", "provider": name},
        )
        result = {
            "provider": name,
            "mission_status": mission.status,
            "attempts": mission.attempts,
            "succeeded": mission.status == "SUCCEEDED",
        }
        if not result["succeeded"]:
            result["brain_failure"] = _safe_brain_failure(runtime)
            print(json.dumps({"live_provider_failure": result}, sort_keys=True))
            raise RuntimeError(f"live_provider_acceptance_failed:{name}:{mission.status}")
        return result


def main() -> int:
    deepseek_key = os.getenv("FALCON_DEEPSEEK_API_KEY", "").strip()
    gemini_key = os.getenv("FALCON_GEMINI_API_KEY", "").strip()
    if not deepseek_key:
        raise RuntimeError("FALCON_DEEPSEEK_API_KEY_required")
    if not gemini_key:
        raise RuntimeError("FALCON_GEMINI_API_KEY_required")

    timeout = float(os.getenv("FALCON_INTELLIGENCE_TIMEOUT", "60"))
    deepseek_timeout = float(os.getenv("FALCON_DEEPSEEK_TIMEOUT", str(timeout)))
    gemini_timeout = float(os.getenv("FALCON_GEMINI_TIMEOUT", str(timeout)))
    gemini_attempts = int(os.getenv("FALCON_GEMINI_MAX_ATTEMPTS", "2"))
    gemini_retry_delay = float(os.getenv("FALCON_GEMINI_RETRY_DELAY", "1"))
    deepseek_model = os.getenv("FALCON_DEEPSEEK_MODEL", "deepseek-v4-pro").strip()
    gemini_model = os.getenv("FALCON_GEMINI_MODEL", "gemini-3.7-flash").strip()

    deepseek = DeepSeekProvider(deepseek_key, model=deepseek_model, timeout=deepseek_timeout)
    gemini = GeminiProvider(
        gemini_key,
        model=gemini_model,
        timeout=gemini_timeout,
        max_attempts=gemini_attempts,
        retry_delay=gemini_retry_delay,
    )

    evidence = {
        "contract_version": "1.0",
        "deepseek": _run_provider("deepseek", deepseek),
        "gemini": _run_provider("gemini", gemini),
    }

    failover = FailoverProvider([
        ("forced_primary_failure", ForcedFailureProvider()),
        ("gemini", GeminiProvider(
            gemini_key,
            model=gemini_model,
            timeout=gemini_timeout,
            max_attempts=gemini_attempts,
            retry_delay=gemini_retry_delay,
        )),
    ])
    fallback_result = _run_provider("controlled_failover", failover)
    fallback_result["selected_provider"] = failover.last_provider
    fallback_result["primary_failure_recorded"] = bool(failover.last_failures)
    if failover.last_provider != "gemini":
        raise RuntimeError("live_failover_did_not_select_gemini")
    evidence["controlled_failover"] = fallback_result
    evidence["all_live_checks_passed"] = True

    Path("live-intelligence-result.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
