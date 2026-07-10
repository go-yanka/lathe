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
    ("LATHE_RUN_ID", "spine", "explicit run id for the persona usage ledger + manifest (else per-run stamp)", "—"),
    ("LATHE_SPINE_TOKEN", "spine", "#12 U3: dispatcher-minted token proving the engine ran via `lathe build`, not around it", "—"),
    ("LATHE_CE_DIR", "spine", "override manifest output dir (docs/ce); gates isolate probes into a temp dir", "docs/ce"),
    ("LATHE_ENGINE_REQUIRE_TOKEN", "spine", "#12 U3: hard-refuse a direct engine call with no spine token (default warn-first)", "off"),
    # --- persona subsystem (#9) ---
    ("LATHE_PERSONA_UCB", "personas", "explore/exploit selection (usage ledger + verified grades); ON by default, set 0 to opt out", "on"),
    # --- adversarial test synthesis gate (#11) ---
    ("LATHE_ADV_SYNTH", "gates", "arm the adversarial-synthesis gate; default-ON under LATHE_STRICT, off elsewhere (set 0 to force off)", "strict"),
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
    ("LATHE_REPAIR", "autonomy", "failed `lathe build` auto-invokes analyst spec repair + one retry (set 0 to disable)", "on"),
    ("LATHE_INTAKE", "autonomy", "`lathe do` intake: surface + record the goal's assumptions before drafting (set 0/off to skip)", "on"),
    ("LATHE_VISION_JUDGE", "autonomy", "D3 advisory visual judge on HTML artifacts: SHOW the rendered page to a vision model, record if it looks like the goal (1/strict to enable; advisory, never fails the build)", "off"),
    ("LATHE_VISION_MODEL", "autonomy", "model name for the D3 visual judge (vision-capable)", "sonnet"),
    ("LATHE_VISION_TIMEOUT", "autonomy", "seconds for a D3 visual-judge call", "90"),
    ("LATHE_REDTEAM", "autonomy", "C1/C2 advisory red-team: analyst enumerates how any LLM could get the goal wrong, then refutes the artifact (1 to enable; advisory, never fails the build)", "off"),
    ("LATHE_REDTEAM_MODEL", "autonomy", "model name for the C1/C2 red-team analyst", "sonnet"),
    ("LATHE_REDTEAM_TIMEOUT", "autonomy", "seconds for a C1/C2 red-team call", "120"),
    ("LATHE_DECIDER_MODE", "autonomy", "E3 persona decider: lexical (word-overlap, free default) | semantic (analyst ranks by meaning) | auto (lexical, semantic fills gaps)", "lexical"),
    ("LATHE_DECIDER_MODEL", "autonomy", "model for the E3 semantic decider", "sonnet"),
    ("LATHE_DECIDER_TIMEOUT", "autonomy", "seconds for a semantic-decider call", "60"),
    ("LATHE_GRADE_FEEDBACK", "autonomy", "E4: feed `lathe review` outcomes back into persona ratings (EWMA-blended); 1 to enable", "off"),
    ("LATHE_PROJECT_LAYOUT", "autonomy", "F4: physically organize a multi-file project into code/docs/scripts/config subdirs (1 to move; default writes PROJECT.md map only)", "off"),
    ("LATHE_WORKSPACE_ROOT", "autonomy", "where per-goal build workspaces are created — OUTSIDE the repo so outputs never pollute the code tree or get checked into the hub (absolute on every OS)", "C:/lathe-workspaces (Windows) / ~/.lathe/workspaces (POSIX)"),
    ("LATHE_ADVOCATE", "autonomy", "THE ADVOCATE: the sponsor's standing representative holds the intent for the whole run and judges the delivery against it; a VETO holds certification (build stays HELD, not DONE). Set 0/off/no to overrule", "on"),
    ("LATHE_ADVOCATE_MODEL", "autonomy", "model the Advocate uses to judge intent-alignment at each checkpoint", "sonnet"),
    ("LATHE_ADVOCATE_TIMEOUT", "autonomy", "seconds for an Advocate checkpoint call", "90"),
    ("LATHE_SPEC_TEST_STRICT", "gates", "FAIL CLOSED: refuse a build when its behavioral acceptance test contradicts its own spec and the reconcile loop could not fix it (fix the TEST, not the build). Set 0/off to restore warn-and-build-anyway", "on"),
    ("LATHE_SPEC_REVIEW", "gates", "the closed loop: on a spec<->test contradiction, the analyst REFINES spec+test until consistent BEFORE the implementer (1=on default, deep=also LLM self-critique, 0=warn-only)", "on"),
    ("LATHE_SPEC_REVIEW_MODEL", "gates", "model for the spec-review refine loop", "sonnet"),
    ("LATHE_SPEC_REVIEW_TIMEOUT", "gates", "seconds for a spec-review analyst call", "120"),
    ("LATHE_TARGETED_REPAIR", "gates", "loop #2: on a whole-file artifact retry, feed the model its own failed code + the exact gate failure to fix precisely (default on; 0 = blind best-of-N)", "on"),
    ("LATHE_STREAM_ENGINE", "autonomy", "stream the engine's live play-by-play to the terminal during do/auto builds + write <workspace>/BUILD_TRACE.md (default on; 0 = quiet, trace still written)", "on"),
    ("LATHE_CHROMIUM", "gates", "path to a pre-provisioned Chromium executable for the web functional/behavioral/vision gates; set it when Playwright's default browser path is absent or a different build (unset = Playwright's own default)", "(Playwright default)"),
    ("LATHE_HEARTBEAT", "autonomy", "print an alive-signal every N seconds during a slow BLOCKING analyst call (drafting/repair) so a slow phase is never a silent black hole (default on; 0 = off)", "on"),
    ("LATHE_HEARTBEAT_SECS", "autonomy", "heartbeat interval in seconds for a slow analyst call", "15"),
    ("LATHE_PHASE", "autonomy", "label the current phase shown in the analyst heartbeat (e.g. drafting spec / repairing spec)", "analyst"),
    ("LATHE_GATE_FULL", "gate-control", "run the HEAVY browser/engine-spawning capability gates (skeleton/behavioral/vision) — set by `lathe gate`; the per-build regression skips them so a heavy gate can't false-block a green build", "off (per-build) / on (lathe gate)"),
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
    "ARTIFACT_FILE",                               # internal engine->functional-gate IPC (func_gates.py scripts)
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
