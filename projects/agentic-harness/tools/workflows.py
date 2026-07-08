"""workflows.py — named, transparent WORKFLOWS for the harness.

A workflow is an ORDERED, documented series of steps for a common activity (review a change, fix a bug, add an
enhancement, review docs, onboard a project). Having them named + explicit gives clarity, trust, and predictable
EXPECTATIONS: anyone can see exactly how the harness handles a given job before running it. Definitions are DATA
(like plans), so they're auditable and can't drift from a hidden implementation.

Each step is (kind, label, action):
  kind "auto"   — a runnable `lathe` subcommand (executed by `lathe flow <name> --run`, gated on success)
  kind "gate"   — a standing check (`lathe gate`) that must pass
  kind "you"    — a human/analyst judgment step (printed as a checkpoint; never auto-run)
  action        — the lathe args for auto/gate (may contain {files}/{plan} placeholders), or "" for `you`

Doctrine baked in: never hand-edit generated code (fix the spec + rebuild); fix -> release to canonical
immediately; harness-framework vs project-specific respects the vendoring boundary.
"""

WORKFLOWS = {
    "code-review": {
        "desc": "Run a ready change through the multi-lens gauntlet and land ONLY verified fixes.",
        # #12 P2: invocation-safe — the old AUTO `build {plan}` step mis-bound a bare review's FILE target
        # as a plan and hard-blocked every promoted `lathe review <files>`; rebuilding the owning plan is a
        # human-judgment step (you must first identify WHICH plan owns the finding), so it is a YOU row.
        "steps": [
            ("auto", "Decider picks the right reviewer personas for the change, then reviews", "review auto {files}"),
            ("gate", "Verify the tree: cleanliness / lint / docs-drift gates", ""),
            ("you",  "Triage: separate real findings from false positives; write the fix for each real one", ""),
            ("you",  "Fix UPSTREAM: fold each real finding into the OWNING plan and rebuild (lathe build <plan>) — never hand-edit generated code", ""),
            ("you",  "If this is a shipped fix: re-cut canonical (release immediately — projects wait on it)", ""),
        ],
    },
    "bug-fix": {
        "desc": "Reproduce -> diagnose from the run log -> fix the SPEC -> verify -> review -> release.",
        "steps": [
            ("auto", "Reproduce: rebuild the failing plan (captures a run log)", "build {plan}"),
            ("auto", "Diagnose: read the full run trace (every model call, verdicts) — spec bug or impl?", "logs --tail"),
            ("auto", "Are the tests even GOOD? (a trivial impl must not pass them)", "lint-spec {plan}"),
            ("you",  "Fix the SPEC/tests to pin the correct behavior (never hand-edit generated code), then rebuild", ""),
            ("auto", "ASSUMPTION AUDIT: confirm the fix isn't silently assuming the unstated (adversarial auditor; HIGH blocks)", "assume {plan}"),
            ("auto", "Rebuild under STRICT mode (the fix must ship a test that reproduces the bug - LATHE_STRICT=1)", "build {plan}"),
            ("gate", "Verify the tree is clean + no regression", ""),
            ("auto", "Review the fix — decider picks the appropriate personas for the code", "review auto {files}"),
            ("you",  "Resolve the issue in the shared queue + re-cut canonical (release immediately)", ""),
        ],
    },
    "enhancement": {
        "desc": "Accept + scope (vendoring boundary) -> build via the harness -> integrate -> review -> document -> release.",
        "steps": [
            ("you",  "Scope it: is this a general HARNESS capability or a PROJECT-specific check? (vendor-don't-fork)", ""),
            ("you",  "Design: small PURE functions + strong tests. Declare required test KINDS per function (e.g. 'kinds': ['property','edge']) — an enhancement invariant needs a PROPERTY test; under STRICT (LATHE_TEST_KIND=1) a unit missing a declared kind is refused", ""),
            ("auto", "ASSUMPTION AUDIT: surface + confirm the unstated choices before building (adversarial auditor; HIGH-materiality blocks)", "assume {plan}"),
            ("auto", "Build it THROUGH the harness under STRICT mode — criteria declared, tests acked, stub-proof, change-proof, assumption-gated (LATHE_STRICT=1)", "build {plan}"),
            ("auto", "Confirm the tests pin behavior", "lint-spec {plan}"),
            ("gate", "Integrate + verify the whole tree", ""),
            ("auto", "Review the new capability (all lenses)", "review all {files}"),
            ("you",  "Document it: add the command/capability WITH an example (the docs-drift gate enforces this)", ""),
            ("you",  "Re-cut canonical (release immediately)", ""),
        ],
    },
    "doc-review": {
        "desc": "Review docs/plans for coherence + accuracy and prove docs haven't drifted from the code.",
        "steps": [
            ("auto", "Doc-review lens over the docs/plans", "review maintainability {files}"),
            ("gate", "Docs-drift gate: every CLI command is documented WITH an example, or the build fails", ""),
            ("you",  "Fix any gaps/inaccuracies; keep every skill's example runnable", ""),
        ],
    },
    "sdlc": {
        "desc": "Full SDLC: requirements (UC->BR->FR->TS, RTM-gated) -> criteria-mapped plan -> STRICT build -> trace -> review -> release.",
        "steps": [
            ("auto", "CLARIFY FIRST: the requirements liaison interrogates the user (inputs/outputs/success/edge/non-goals) before any design", "clarify {goal}"),
            ("auto", "Author LAYERED, ID-traced requirements from the clarified brief; the RTM gate refuses orphans/dangling refs", "sdlc {goal}"),
            ("you",  "Review REQUIREMENTS.md; turn the suggested CRITERIA block into a plan (each TS -> criterion -> named tests)", ""),
            ("auto", "Acknowledge the test set (the tests define 'correct')", "ack {plan}"),
            ("auto", "ASSUMPTION AUDIT: an adversarial auditor surfaces the choices the goal never specified; each HIGH one must be DECIDED (the build refuses until then)", "assume {plan}"),
            ("you",  "RESOLVE each blocking assumption (`lathe assume {plan} --resolve`): accept it as the real intent, pick an offered alternative, or state what you actually want — recorded as a decision in <plan>.decisions.md. No blanket accept.", ""),
            ("auto", "Build under STRICT mode - criteria+ack+stub-proof+change-proof+mutation-score+assumption-gate all forced (LATHE_STRICT=1)", "build {plan}"),
            ("auto", "Emit the requirement->test->pin->model traceability matrix (the compliance artifact)", "trace {plan}"),
            ("auto", "Review - decider picks the appropriate personas", "review auto {files}"),
            ("gate", "Tree clean + no regression", ""),
            ("you",  "Release: checkin + re-cut canonical", ""),
        ],
    },
    "new-project": {
        "desc": "Vendor Lathe into a project, configure endpoints, verify, and land the first gated build.",
        "steps": [
            ("you",  "Vendor a pinned copy of canonical Lathe; keep YOUR product layer separate (see VENDORING.md)", ""),
            ("you",  "Configure endpoints: LOCAL_OPENAI_URL (implementer) + HARNESS_CLAUDE_URL (analyst)", ""),
            ("auto", "Verify the install on your machine", "selftest"),
            ("gate", "Confirm the tree is clean", ""),
            ("auto", "First build: draft a spec, build it on the local model under gates, pin it", "do \"a small pure helper you need\""),
            ("you",  "Add YOUR product data-quality gates (see DATA_QUALITY.md) — the harness ships the framework", ""),
        ],
    },
}


# Per-workflow CONTRACT — the up-front EXPECTATIONS shown by `lathe flow <name>` before you run:
# when to reach for it, what must be true to start (entry), what you get (deliverable), and definition-of-done.
CONTRACTS = {
    "code-review": {
        "when": "A change is ready and you want ONLY verified fixes landed.",
        "entry": "The changed files exist and build; you know which plan owns them.",
        "deliverable": "Real findings folded UPSTREAM into the owning plans + rebuilt + gated — nothing hand-edited.",
        "done": "Gates green, touched specs pass lint-spec, canonical re-cut if this was a shipped fix."},
    "bug-fix": {
        "when": "A build/behavior is wrong and you need it corrected at the source, not patched.",
        "entry": "You can name the failing plan and reproduce it.",
        "deliverable": "The SPEC/tests pin the correct behavior; a green rebuild; the fix reviewed.",
        "done": "Rebuild green, tree clean, adversarial+correctness review clear, issue resolved + released."},
    "enhancement": {
        "when": "You want a NEW capability, built the disciplined way (dogfooded through the harness).",
        "entry": "The idea is scoped as harness-framework vs project-specific (vendoring boundary).",
        "deliverable": "Small pure functions + strong tests, built by the harness, reviewed, documented.",
        "done": "Built+gated, tests pin behavior, all-lens review clear, documented with an example, released."},
    "doc-review": {
        "when": "You need docs/plans checked for accuracy and proven not-drifted from the code.",
        "entry": "The docs/plans to review exist.",
        "deliverable": "A coherence/accuracy review + a passing docs-drift gate.",
        "done": "Review clear, docs-drift gate green (every command documented with a runnable example)."},
    "sdlc": {
        "when": "You want the FULL process enforced end-to-end: requirements with IDs, traceability, and every proof gate.",
        "entry": "A goal statement; analyst + implementer endpoints configured.",
        "deliverable": "RTM-gated REQUIREMENTS.md + a criteria-mapped plan built under STRICT + the trace matrix.",
        "done": "RTM gate PASS, STRICT build green, trace shows every criterion covered, review clear, released.",
    },
    "new-project": {
        "when": "You're onboarding a fresh project onto Lathe.",
        "entry": "You have a project repo and access to an implementer + analyst endpoint.",
        "deliverable": "A vendored, configured, verified Lathe install with a first gated build landed.",
        "done": "selftest passes, tree clean, first `do` build pinned, product data-quality gates added."},
}


# --- Operating contract #12 Phase 2: PER-INVOCATION workflows (the reviewer's 19-id set) ---------------------
# Design: primitive-FIRST with {args} passthrough (stdout + exit code preserved — the manifest is a side-
# file), then only steps that ADD enforcement (no duplicate gate runs: the engine gates its own builds).
# Single-step entries make the promotion machinery uniform: primitive + spine + manifest, nothing else.
WORKFLOWS.update({
    "build-from-goal": {
        "desc": "Bare `lathe do`: goal -> clarified spec -> gated build, then the standing gates.",
        "steps": [
            ("auto", "Goal -> analyst spec+tests -> gated build (the do primitive)", "do {args}"),
            ("gate", "Standing gates on the mutated tree", ""),
            ("you",  "Read the run manifest (docs/ce/) — confirm assumptions + selection look right", ""),
        ],
    },
    "build-from-plan": {
        "desc": "Bare `lathe build`: gated engine build (engine runs the standing regression itself), then traceability.",
        "steps": [
            ("auto", "Engine build under the plan's declared gates", "build {args}"),
            ("auto", "Requirement->test traceability check on the plan", "trace {plan}"),
            ("you",  "Read the run manifest — verify gates + per-role usage recorded", ""),
        ],
    },
    "clarify-goal":        {"desc": "Bare `lathe clarify`: requirements-liaison interview -> committed brief.",
                            "steps": [("auto", "Liaison interview -> brief", "clarify {args}")]},
    "assumption-audit":    {"desc": "Bare `lathe assume`: adversarial assumption audit -> committed decisions.",
                            "steps": [("auto", "Adversarial auditor -> materiality-ranked ledger -> resolutions", "assume {args}")]},
    "verify-reproduce":    {"desc": "Bare `lathe verify`: re-verify pinned bytes reproduce from the pin store.",
                            "steps": [("auto", "Verify pins reproduce", "verify {args}")]},
    "gate-quality":        {"desc": "Bare `lathe gate`: the standing gate suite, exit-code honest.",
                            "steps": [("auto", "Run the standing gates", "gate")]},
    "trace-inspect":       {"desc": "Bare `lathe trace`: requirement->test traceability report.",
                            "steps": [("auto", "Trace CRITERIA -> tests", "trace {args}")]},
    "maintain-tree":       {"desc": "Bare `lathe clean`: janitor pass, then prove the tree is pristine.",
                            "steps": [("auto", "Janitor: remove stale/dup/corrupt files", "clean {args}"),
                                      ("gate", "Standing gates prove the tree is clean", "")]},
    "ship-release":        {"desc": "Bare `lathe checkin`: leak-safe check-in, then human tags/notes.",
                            "steps": [("auto", "Leak-scanned check-in", "checkin {args}"),
                                      ("you",  "Tag + release notes + notify consuming projects", "")]},
    "serve-api":           {"desc": "Bare `lathe serve`: the REST API v0 (runs until stopped).",
                            "steps": [("auto", "Serve the API", "serve {args}")]},
    "select-grade-experts": {"desc": "Bare `lathe agent`: decider matches personas to the need (license-gated fetch).",
                             "steps": [("auto", "Match/spawn the best persona(s)", "agent {args}")]},
    "report-triage":       {"desc": "Bare `lathe report`: consuming-project issue intake, then human triage.",
                            "steps": [("auto", "Collect/emit the report", "report {args}"),
                                      ("you",  "Triage: accept/fix/decline each item, on the record", "")]},
    "autonomous":          {"desc": "Bare `lathe auto`: the supervised autonomy loop (its own gates inside).",
                            "steps": [("auto", "Autonomy loop", "auto {args}")]},
    "sdlc-requirements":   {"desc": "Bare `lathe sdlc`: analyst writes UC->BR->FR->TS, RTM-gated.",
                            "steps": [("auto", "Requirements authoring (RTM-gated)", "sdlc {args}"),
                                      ("you",  "Review REQUIREMENTS.md — every TS maps to a UC before building", "")]},
    "onboard-project":     {"desc": "Alias of new-project: vendor Lathe into a repo and land the first gated build.",
                            "steps": [("you", "Follow the new-project guided workflow (lathe flow new-project)", "")]},
})

# --- Operating contract #12 Phase 1: command -> CONTRACT (data — auditable; the spine's PHASES are code) ---
# Keys: workflow (Phase-2 promotion target; run when it exists AND binds cleanly), gate (phase-4 standing gates
# after a green write), writes (mutates the tree — documentary), argmap (how bare argv binds the workflow's
# placeholder — documentary). Only `workflow` and `gate` are BEHAVIOR-BEARING (read by run_spine); the rest is
# auditable metadata. The former `front_end`/`select` flags were REMOVED in v2.40.0 (MASTER_PLAN B3): they were
# never read — intake/assumptions run in cmd_do (front-end) and persona selection in _intake_panel/_do_review
# (select), at the COMMAND layer, not the spine. contract_hygiene_gate enforces they cannot creep back.
# A command absent here (or {}) is TRIVIAL: the spine still
# runs (run_id + thinking + manifest) but phases 1/2/4 no-op — byte-identical behavior for read-only commands.
# NOTE Phase 1: build/do gate:0 because the ENGINE already runs the standing regression inside the build
# (gating twice doubles cost for zero coverage); their workflow promotion + phase-4 wiring lands in Phase 2.
CONTRACT_FOR = {
    # workflow-promoted (#12 P2). gate flags: 0 where the workflow carries its own gate step or the engine
    # gates internally — the contract never runs the same gate twice for zero coverage.
    "do":       {"workflow": "build-from-goal",     "gate": 0, "writes": 1, "argmap": "goal"},
    "build":    {"workflow": "build-from-plan",     "gate": 0, "writes": 1, "argmap": "plan"},
    "review":   {"workflow": "code-review",         "gate": 0, "writes": 0, "argmap": "files"},
    "sdlc":     {"workflow": "sdlc-requirements",   "gate": 1, "writes": 1, "argmap": "goal"},
    "clarify":  {"workflow": "clarify-goal",        "writes": 1, "argmap": "goal"},
    "assume":   {"workflow": "assumption-audit",    "gate": 1, "writes": 1, "argmap": "plan"},
    "verify":   {"workflow": "verify-reproduce",    "gate": 0, "writes": 0, "argmap": "plan"},
    "trace":    {"workflow": "trace-inspect",       "writes": 0, "argmap": "plan"},
    "clean":    {"workflow": "maintain-tree",       "writes": 1},
    "checkin":  {"workflow": "ship-release",        "writes": 1},
    "serve":    {"workflow": "serve-api",           "writes": 0},
    "agent":    {"workflow": "select-grade-experts", "writes": 0},
    "report":   {"workflow": "report-triage",       "writes": 0},
    "auto":     {"workflow": "autonomous",          "writes": 1},
    "gate":     {"writes": 0},                 # cmd_gate IS the gate run — phase-4 repeating it adds nothing
    # read-only -> TRIVIAL (spine runs; phases no-op):
    "status": {}, "logs": {}, "metrics": {}, "board": {}, "plans": {}, "whatis": {},
    "map": {}, "env": {}, "dups": {}, "flow": {}, "issues": {}, "waiting": {},
}


def get_contract(name):
    """The up-front contract (when/entry/deliverable/done) for a workflow, or {} if none."""
    return CONTRACTS.get(name, {})


def list_workflows():
    """(name, desc) for each workflow, sorted."""
    return sorted((n, w["desc"]) for n, w in WORKFLOWS.items())


def get_workflow(name):
    """A workflow dict, or None."""
    return WORKFLOWS.get(name)
