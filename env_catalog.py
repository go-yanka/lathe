"""env_catalog.py — the SINGLE SOURCE OF TRUTH for Lathe's environment variables (PR#1 CLI-review #1).

Every env var the harness reads is listed here with its group, role, and default. `lathe env` prints this;
`qa/env_drift_gate.py` extracts the vars the code actually reads (env_logic.extract_env_vars) and FAILS the
build if any is missing here — so a new undocumented var can't drift in. Hand-maintained data (not generated).
"""

# (name, group, role, default)  — default "—" = no literal default / context-dependent.
REGISTRY = [
    # --- endpoints & routing ---
    ("HARNESS_CLAUDE_URL", "endpoints", "analyst endpoint (OpenAI-compatible); the 'thinker'", "http://127.0.0.1:8787/v1/chat/completions"),
    ("HARNESS_ANALYST_MODEL", "endpoints", "model name sent to the analyst endpoint", "—"),
    ("HARNESS_MODEL", "endpoints", "default implementer model (fallback)", "gemma4:12b"),
    ("LOCAL_OPENAI_URL", "endpoints", "endpoint for openai:* implementer models", "llama-server :8089"),
    ("OLLAMA_URL", "endpoints", "endpoint for bare-name (ollama) implementer models", "http://localhost:11434"),
    ("LATHE_MODEL", "endpoints", "CLI default implementer model", "openai:local"),
    ("LATHE_TRIES", "endpoints", "best-of-N implementer attempts (Rule-of-Three)", "3"),
    # --- analyst / implementer tuning ---
    ("CLAUDE_TIMEOUT", "tuning", "analyst call timeout (s)", "120"),
    ("CLAUDE_RETRIES", "tuning", "analyst call retries", "2"),
    ("LOCAL_OPENAI_MAXTOK", "tuning", "implementer max_tokens cap", "16384"),
    ("LOCAL_GEN_TIMEOUT", "tuning", "implementer generation timeout (s)", "900 (openai) / 300 (ollama)"),
    ("LATHE_MAX_RESP", "tuning", "max response bytes accepted from an endpoint", "—"),
    ("LATHE_RUN_TIMEOUT", "tuning", "per-run wall-clock bound (s)", "—"),
    # --- operating contract spine (#12) ---
    ("LATHE_THINK", "spine", "thinking dial casual|medium|high -> tries/personas/assumption depth", "medium"),
    ("LATHE_SPINE", "spine", "operator bypass: off = raw dispatch (still manifested + recorded)", "on"),
    # --- adversarial test synthesis gate (#11) ---
    ("LATHE_ADV_SYNTH", "gates", "arm the adversarial-synthesis gate (analyst synthesizes bypass probes pre-pin)", "off"),
    ("LATHE_ADV_POLICY", "gates", "which functions face synthesis: off | gates (default) | all", "gates"),
    ("LATHE_ADV_MIN", "gates", "minimum admissible adversarial cases required (fail-closed below this)", "3"),
    ("LATHE_ADV_MODEL", "gates", "model the analyst-adversary synthesizes probes with (a capable model)", "claude"),
    # --- enforcement gates (STRICT umbrella arms all of these) ---
    ("LATHE_STRICT", "gates", "umbrella: arm all enforcement gates + require CRITERIA", "off"),
    ("LATHE_TEST_ACK", "gates", "require a human-acked test set (lathe ack)", "off"),
    ("LATHE_REGRESSION_PROOF", "gates", "a change must ship a test that fails on the old code", "off"),
    ("LATHE_LINT_SPEC", "gates", "block/warn on stub-satisfiable tests (spec-lint)", "off"),
    ("LATHE_MUTATION_SCORE", "gates", "min fraction of mutants the suite must kill (0..1)", "off"),
    ("LATHE_MUTATION_LIMIT", "gates", "cap on mutants generated per function", "—"),
    ("LATHE_GATE_GLUE", "gates", "hand-written GLUE must have an INTEGRATION test", "off"),
    ("LATHE_GLUE_MAX", "gates", "max GLUE lines allowed without integration coverage", "—"),
    ("LATHE_TEST_KIND", "gates", "require declared test KINDS (property/edge/…) per function", "off"),
    ("LATHE_ASSUMPTION_GATE", "gates", "refuse build while a blocking assumption is unresolved", "off"),
    ("LATHE_ASSUMPTION_POLICY", "gates", "assumption scrutiny: all|high+med|high|off", "high"),
    # --- regression / gate control ---
    ("FUNC_GATE_TIMEOUT", "gate-control", "per-function gate timeout (s)", "360"),
    ("ITEST_TIMEOUT", "gate-control", "integration-test timeout (s)", "360"),
    ("REGRESSION_TIMEOUT", "gate-control", "regression gate timeout (s)", "300"),
    ("SKIP_REGRESSION", "gate-control", "skip the standing regression gate (1 = skip)", "off"),
    ("RUN_GATES_PATH", "gate-control", "override path to qa/run_gates.py", "—"),
    ("LATHE_PRODUCT_GATES", "gate-control", "path to a project's own qa/gates/ tree", "—"),
    # --- sandbox (untrusted execution) ---
    ("LATHE_SANDBOX", "sandbox", "execution mode: subprocess | docker | docker-ssh | 0", "subprocess (autonomy)"),
    ("LATHE_SANDBOX_TIMEOUT", "sandbox", "sandbox execution timeout (s)", "—"),
    ("LATHE_DOCKER_IMAGE", "sandbox", "image for LATHE_SANDBOX=docker", "—"),
    ("LATHE_DOCKER_SSH", "sandbox", "remote host for LATHE_SANDBOX=docker-ssh", "—"),
    # --- autonomy / project ---
    ("LATHE_AUTO_COMMIT", "autonomy", "let auto/do/run git-commit green builds (opt-in)", "off"),
    ("LATHE_PROJECT", "autonomy", "active project subtree under projects/", "agentic-harness"),
    ("LATHE_REMOTE", "autonomy", "git remote for checkin --push", "origin"),
    # --- cassette (deterministic record/replay of LLM calls) ---
    ("LATHE_CASSETTE", "cassette", "cassette file for record/replay", "—"),
    ("LATHE_CASSETTE_UPSTREAM", "cassette", "real endpoint to record from", "—"),
    ("LATHE_CASSETTE_PORT", "cassette", "port the cassette proxy listens on", "8791"),
    ("LATHE_CASSETTE_STRICT", "cassette", "fail on a cassette miss instead of passthrough", "off"),
    ("LATHE_CASSETTE_TIMEOUT", "cassette", "cassette upstream timeout (s)", "—"),
    ("LATHE_GATE_RECORD", "cassette", "record mode for gate/cassette capture", "off"),
    # --- paths / dirs / logging ---
    ("LATHE_CONFIG", "paths", "path to lathe.config.json (else ./ or ~/.lathe/)", "—"),
    ("LATHE_ISSUES_DIR", "paths", "directory for lathe issues", "—"),
    ("LATHE_LEDGER_DIR", "paths", "directory for the failure/metrics ledger", "—"),
    ("LATHE_METRICS_PATH", "paths", "path to metrics/runs.jsonl", "metrics/runs.jsonl"),
    ("LATHE_LOG", "paths", "structured run-log toggle/path", "—"),
    ("LATHE_LOG_DIR", "paths", "directory for runs/<id>.jsonl logs", "runs/"),
    ("LATHE_LOG_KEEP", "paths", "how many run logs to retain", "—"),
    # --- persona market ---
    ("LATHE_RATE_PACE", "persona", "seconds between agent-rating probes (throttle)", "2"),
    # --- trust / safety (advanced; loosen guards deliberately) ---
    ("LATHE_TRUST_PLAN", "trust", "allow OUT_DIR outside the tree (dangerous)", "off"),
    ("LATHE_TRUST_REMOTE_ANALYST", "trust", "open the non-local analyst SSRF guard", "off"),
    # --- REST API (lathe serve / lathe_api.py) ---
    ("LATHE_API_TOKEN", "api", "bearer token the REST API requires (no token = server refuses to start)", "—"),
    ("LATHE_API_PORT", "api", "port the REST API binds", "8799"),
]

# Internal/forced vars — read by the code but NOT user-facing; excluded from `lathe env` and the drift gate.
IGNORE = {
    "LATHE_VALIDATE_PLAN", "LATHE_VALIDATOR_PY",   # forced on by main(); not user-settable in practice
    "LATHE_SANDBOX_PAYLOAD", "LATHE_SANDBOX_PY",   # internal sandbox IPC (parent<->child)
}


def registry_names():
    """The set of documented (user-facing) env var names."""
    return {name for (name, _g, _r, _d) in REGISTRY}


def grouped():
    """(group -> [(name, role, default), ...]) in REGISTRY order."""
    out = {}
    for name, group, role, default in REGISTRY:
        out.setdefault(group, []).append((name, role, default))
    return out
