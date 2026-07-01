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
            ("auto", "Multi-lens review of the changed files (vendored CE personas + Lathe doctrine)", "review all {files}"),
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
            ("auto", "Review the fix (adversarial + correctness)", "review adversarial correctness {files}"),
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


def list_workflows():
    """(name, desc) for each workflow, sorted."""
    return sorted((n, w["desc"]) for n, w in WORKFLOWS.items())


def get_workflow(name):
    """A workflow dict, or None."""
    return WORKFLOWS.get(name)
