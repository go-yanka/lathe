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
        "steps": [
            ("auto", "Decider picks the right reviewer personas for the change, then reviews", "review auto {files}"),
            ("you",  "Triage: separate real findings from false positives; write the fix for each real one", ""),
            ("you",  "Fix UPSTREAM: fold each real finding into the OWNING plan and rebuild — never hand-edit generated code", ""),
            ("auto", "Rebuild the owning plan(s)", "build {plan}"),
            ("gate", "Verify the tree: cleanliness / lint / docs-drift gates", ""),
            ("auto", "Test-quality check on touched plan(s)", "lint-spec {plan}"),
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
            ("auto", "Rebuild", "build {plan}"),
            ("gate", "Verify the tree is clean + no regression", ""),
            ("auto", "Review the fix — decider picks the appropriate personas for the code", "review auto {files}"),
            ("you",  "Resolve the issue in the shared queue + re-cut canonical (release immediately)", ""),
        ],
    },
    "enhancement": {
        "desc": "Accept + scope (vendoring boundary) -> build via the harness -> integrate -> review -> document -> release.",
        "steps": [
            ("you",  "Scope it: is this a general HARNESS capability or a PROJECT-specific check? (vendor-don't-fork)", ""),
            ("you",  "Design: break it into small PURE functions + strong tests (edge cases: empty/None/0/boundary)", ""),
            ("auto", "Build it THROUGH the harness (dogfood — do not hand-write what the harness can build)", "build {plan}"),
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
    "new-project": {
        "when": "You're onboarding a fresh project onto Lathe.",
        "entry": "You have a project repo and access to an implementer + analyst endpoint.",
        "deliverable": "A vendored, configured, verified Lathe install with a first gated build landed.",
        "done": "selftest passes, tree clean, first `do` build pinned, product data-quality gates added."},
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
