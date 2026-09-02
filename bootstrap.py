"""Falcon composition root: concrete organ wiring lives only here."""
import os
from autonomic.control import MissionControl
from autonomic.driver import BrainDriver
from autonomic.runtime import Runtime
from brain.engine import Brain
from brain.providers.deepseek import DeepSeekProvider
from brain.providers.deterministic import DeterministicProvider
from brain.providers.failover import FailoverProvider
from brain.providers.gemini import GeminiProvider
from brain.providers.json_http import JsonHttpProvider
from brain.providers.openai_responses import OpenAIResponsesProvider
from clients.github_http import GitHubHttpClient
from execution.adapters.github import GitHubAdapter
from execution.adapters.noop import NoopAdapter
from execution.registry import Executor
from governance.policy import Governance
from learning.evaluator import Evaluator
from memory.store import MemoryStore
from nervous_system.bus import EventBus


def _truthy(value) -> bool: return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

def _env_value(env, primary: str, fallback: str | None = None) -> str:
    value = str(env.get(primary, "")).strip()
    if not value and fallback: value = str(env.get(fallback, "")).strip()
    return value


def build_brain_from_env(environ=None) -> Brain:
    env = os.environ if environ is None else environ
    mode = str(env.get("FALCON_INTELLIGENCE_MODE", "")).strip().lower()
    endpoint = str(env.get("FALCON_INTELLIGENCE_ENDPOINT", "")).strip()
    deepseek_key = _env_value(env, "FALCON_DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY")
    gemini_key = _env_value(env, "FALCON_GEMINI_API_KEY", "GEMINI_API_KEY")
    openai_key = _env_value(env, "FALCON_OPENAI_API_KEY", "OPENAI_API_KEY")
    if not mode and (deepseek_key or gemini_key): mode = "auto"
    if not mode and openai_key: mode = "openai"
    if not mode and endpoint: mode = "json_http"
    if not mode: return Brain()
    if mode == "deterministic": return Brain(DeterministicProvider())
    timeout = float(env.get("FALCON_INTELLIGENCE_TIMEOUT", "60"))
    deepseek_timeout = float(env.get("FALCON_DEEPSEEK_TIMEOUT", timeout))
    gemini_timeout = float(env.get("FALCON_GEMINI_TIMEOUT", timeout))

    def deepseek():
        if not deepseek_key: raise ValueError("falcon_deepseek_api_key_required")
        return DeepSeekProvider(
            deepseek_key,
            model=str(env.get("FALCON_DEEPSEEK_MODEL", "deepseek-v4-pro")).strip(),
            timeout=deepseek_timeout,
            max_tokens=int(env.get("FALCON_DEEPSEEK_MAX_TOKENS", "8192")),
        )

    def gemini():
        if not gemini_key: raise ValueError("falcon_gemini_api_key_required")
        return GeminiProvider(
            gemini_key,
            model=str(env.get("FALCON_GEMINI_MODEL", "gemini-3.7-flash")).strip(),
            timeout=gemini_timeout,
            max_attempts=int(env.get("FALCON_GEMINI_MAX_ATTEMPTS", "2")),
            retry_delay=float(env.get("FALCON_GEMINI_RETRY_DELAY", "1")),
            max_output_tokens=int(env.get("FALCON_GEMINI_MAX_OUTPUT_TOKENS", "4096")),
        )

    if mode in {"auto", "deepseek_gemini", "multi"}:
        providers = []
        if deepseek_key: providers.append(("deepseek", deepseek()))
        if gemini_key: providers.append(("gemini", gemini()))
        if not providers: raise ValueError("falcon_live_intelligence_key_required")
        return Brain(providers[0][1] if len(providers) == 1 else FailoverProvider(providers))
    if mode == "deepseek": return Brain(deepseek())
    if mode == "gemini": return Brain(gemini())
    if mode == "openai":
        if not openai_key: raise ValueError("falcon_openai_api_key_required")
        model = str(env.get("FALCON_OPENAI_MODEL", "gpt-5.6-sol")).strip()
        return Brain(OpenAIResponsesProvider(openai_key, model=model, timeout=timeout))
    if mode != "json_http": raise ValueError(f"unsupported_intelligence_mode:{mode}")
    if not endpoint: raise ValueError("falcon_intelligence_endpoint_required")
    headers = {}; token = str(env.get("FALCON_INTELLIGENCE_TOKEN", "")).strip()
    if token: headers["Authorization"] = f"Bearer {token}"
    return Brain(JsonHttpProvider(endpoint, headers=headers, timeout=timeout))


def build_executor_from_env(environ=None) -> Executor:
    env = os.environ if environ is None else environ; executor = Executor(); executor.register(NoopAdapter())
    token = str(env.get("FALCON_GITHUB_TOKEN", "")).strip() or None; timeout = float(env.get("FALCON_GITHUB_TIMEOUT", "30"))
    executor.register(GitHubAdapter(GitHubHttpClient(token=token, timeout=timeout)))
    return executor


def build_governance_from_env(environ=None) -> Governance:
    env = os.environ if environ is None else environ; allowed = {"noop.inspect", "github.read"}
    if _truthy(env.get("FALCON_GITHUB_WRITE_ENABLED")): allowed.add("github.write")
    extra = str(env.get("FALCON_ALLOWED_CAPABILITIES", "")).strip()
    if extra: allowed.update(x.strip() for x in extra.split(",") if x.strip())
    return Governance(allowed)


def build_runtime(state_dir: str = ".falcon", brain=None, memory=None, bus=None, control=None, executor=None, governance=None, evaluator=None) -> Runtime:
    if bus is None: bus = EventBus()
    if brain is None: brain = build_brain_from_env()
    if memory is None: memory = MemoryStore(f"{state_dir}/memory.jsonl")
    if executor is None: executor = build_executor_from_env()
    if governance is None: governance = build_governance_from_env()
    if evaluator is None: evaluator = Evaluator()
    if control is None: control = MissionControl(cancel_operation=executor.cancel)
    runtime = Runtime(bus=bus, brain=brain, memory=memory, state_dir=state_dir)
    runtime.control = control; runtime.executor = executor; runtime.governance = governance; runtime.evaluator = evaluator
    runtime.driver = BrainDriver(brain, executor, governance, runtime, memory=memory, control=control, evaluator=evaluator)
    return runtime


def run_mission(runtime: Runtime, objective: str, acceptance_criteria: dict | None = None, context: dict | None = None, source: str = "founder", source_id: str | None = None):
    mission = runtime.accept(objective, source=source, source_id=source_id, acceptance_criteria=acceptance_criteria, context=context)
    return runtime.driver.run(mission, context=context)
