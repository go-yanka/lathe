"""failure_modes.py — the ADVERSARIAL RATCHET registry (MASTER_PLAN C3/C4/C5).

Owner's design: a build carries two specs — how to DO it, and how an LLM could GET IT WRONG. The second is
not re-imagined per task (it would share the builder's blind spots); the durable part is this CURATED,
GROWING list of failure CLASSES we have actually hit, each bound to the standing GATE that now catches it.
When a new repeatable failure is found, it is added here AND a gate is written — so the class can never
recur silently. `failure_registry_gate.py` enforces the invariant: every entry with a named gate must have
that gate wired into the standing suite (run_gates.py). An entry with gate=None is an OPEN hole, tracked
loudly — never a silent gap.

Each entry: id, klass (one-line failure class), manifests (how it shows up), gate (the run_gates check name
that catches it, or None = UNGUARDED/open).
"""

FAILURE_MODES = [
    # --- discovered + gated 2026-07-08 (the wiring program) ---
    {"id": "wire-not-tested-e2e", "gate": "workflow_wiring",
     "klass": "Capability built + unit-gated in isolation but never wired into the user-facing command",
     "manifests": "module green, `do`/command silently skips it; nobody notices for weeks"},
    {"id": "silent-step-drop", "gate": "workflow_wiring",
     "klass": "A workflow DECLARES a step the runner never executes AND never records",
     "manifests": "front-end/clarify/assume 'ran' but didn't; declared != executed"},
    {"id": "contradictory-contracts", "gate": "skeleton_lane",
     "klass": "Two code paths give a model contradictory instructions (whole-file vs region)",
     "manifests": "the model OBEYS one and is punished; looks like model incapacity (9B GoL)"},
    {"id": "prose-instead-of-code", "gate": "skeleton_lane",
     "klass": "Model narrates/describes instead of emitting the artifact (format dud)",
     "manifests": "reply is a bullet list, no <!doctype; structural asserts fail — salvage + output contract catch it"},
    {"id": "assumption-guess", "gate": "manifest_contract",
     "klass": "Goal left a choice unstated; the model silently GUESSES it (intent drift)",
     "manifests": "helicopter falls (physics never specified); intake now surfaces + the assumption gate blocks HIGH"},
    {"id": "gate-inoperative-blamed-spec", "gate": "gate_tristate",
     "klass": "A gate that CANNOT run (broken env) is scored as a spec FAILURE",
     "manifests": "browser missing -> 'your spec failed'; tri-state INOPERATIVE fixes it"},
    {"id": "pin-provenance-endpoint", "gate": None,
     "klass": "Pin records the model STRING, not the endpoint behind it",
     "manifests": "fable-behind-proxy pinned as 'openai:local'. OPEN — candidate: stamp endpoint in .pins.index.json"},
    {"id": "behavioral-correctness-unchecked", "gate": None,
     "klass": "Interactive output passes 'it loads/animates' but is functionally WRONG",
     "manifests": "dead game controls pass web_canvas_game. OPEN — MASTER_PLAN D1 (analyst-authored behavioral tests)"},
    {"id": "false-done-unwired-tasklist", "gate": None,
     "klass": "'DONE' recorded when the MODULE's gate is green, not when the user command works + a gate proves it",
     "manifests": "tasks #41/#42 marked done but unwired. OPEN — cultural; each wire needs its own proving gate"},
    # --- older, standing ---
    {"id": "duplicate-capability", "gate": "capability_registry",
     "klass": "N copies of the same capability, no single 'which is live'",
     "manifests": "divergent forks; the capability registry enforces one canonical live copy"},
    {"id": "stub-satisfiable-tests", "gate": None,
     "klass": "Tests a trivial/stub implementation passes (weak spec)",
     "manifests": "spec_lint catches under LATHE_LINT_SPEC; not in the default suite -> tracked"},
]


def entries():
    return list(FAILURE_MODES)


def guarded():
    return [f for f in FAILURE_MODES if f.get("gate")]


def open_holes():
    return [f for f in FAILURE_MODES if not f.get("gate")]
