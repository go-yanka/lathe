# W01_flow_report — pure functions for the transparent workflow run-report + fail-loud verdict.
# Built THROUGH the harness (plans -> engine -> gated -> pinned). Consumed by lathe.py cmd_flow (spine glue).
# No duplication: these only CLASSIFY/RENDER; step execution reuses the real `lathe <cmd>` commands.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "flow_report"
HEADER = ""
GLUE = ""
_ONLY = 'Output ONLY the Python function code - no prose, no markdown, no tests. Import any module you need INSIDE the function. Define constants INSIDE the function.'
FUNCTIONS = [
    {
        "name": "classify_step",
        "prompt": ("Implement classify_step(kind, rc, output) -> str. kind is one of 'auto', 'gate', 'you'. "
                   "If kind == 'you' return 'todo' (human-judgment step, not auto-run). Otherwise treat output as "
                   "'' when None; if rc is a nonzero integer return 'blocked'; else if the LOWERCASED output contains "
                   "any of these failure signals: 'not exist', 'could be read', 'traceback', 'fail ::', 'error:' "
                   "-> return 'blocked'; otherwise return 'pass'. Never raise." + "\n" + _ONLY),
        "tests": [
            "assert classify_step('you', 0, '') == 'todo'",
            "assert classify_step('gate', 0, 'stale_gate PASS :: clean') == 'pass'",
            "assert classify_step('auto', 1, 'boom') == 'blocked'",
            "assert classify_step('auto', 0, 'review: these targets do not exist: x') == 'blocked'",
            "assert classify_step('gate', 0, 'capability_registry FAIL :: task_board missing') == 'blocked'",
            "assert classify_step('auto', 0, None) == 'pass'",
            "assert classify_step('auto', 0, 'Traceback (most recent call last):') == 'blocked'",
            "assert classify_step('you', 1, 'ignored') == 'todo'",
        ],
    },
    {
        "name": "workflow_verdict",
        "prompt": ("Implement workflow_verdict(statuses) -> str. statuses is a list of strings each 'pass', 'blocked', "
                   "or 'todo'. Return 'BLOCKED' if any element equals 'blocked', otherwise return 'PASS'. None or an "
                   "empty list -> 'PASS'. Never raise." + "\n" + _ONLY),
        "tests": [
            "assert workflow_verdict(['pass', 'todo', 'pass']) == 'PASS'",
            "assert workflow_verdict(['pass', 'blocked']) == 'BLOCKED'",
            "assert workflow_verdict([]) == 'PASS'",
            "assert workflow_verdict(None) == 'PASS'",
            "assert workflow_verdict(['todo']) == 'PASS'",
            "assert workflow_verdict(['blocked']) == 'BLOCKED'",
        ],
    },
    {
        "name": "render_report",
        "prompt": ("Implement render_report(name, rows) -> str. name is the workflow name. rows is a list of "
                   "(label, status) tuples where status is 'pass', 'blocked', or 'todo'. Return a multi-line string: "
                   "line 1 is 'workflow report: ' + name; then one line per row formatted as '  [' + status.upper() + "
                   "'] ' + label; then a final line 'verdict: ' + ('BLOCKED' if any row status == 'blocked' else 'PASS'). "
                   "None rows -> treat as empty list. Never raise." + "\n" + _ONLY),
        "tests": [
            "assert 'verdict: PASS' in render_report('doc-review', [('review', 'pass'), ('gate', 'pass')])",
            "assert 'verdict: BLOCKED' in render_report('bug-fix', [('build', 'pass'), ('review', 'blocked')])",
            "assert '[BLOCKED] review' in render_report('bug-fix', [('review', 'blocked')])",
            "assert 'workflow report: doc-review' in render_report('doc-review', [])",
            "assert 'verdict: PASS' in render_report('x', None)",
            "assert '[TODO] fix the spec' in render_report('bug-fix', [('fix the spec', 'todo')])",
        ],
    },
]
