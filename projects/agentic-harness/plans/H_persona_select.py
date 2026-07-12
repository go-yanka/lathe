# H_persona_select — persona redesign STAGE 2 (issue #9): explore/exploit selection that makes ALL personas
# reachable. Root cause of "99/143 unreachable": pure word-overlap selection never surfaces personas whose
# capability vocabulary doesn't token-match the goal. Fix (FR-3/FR-4): UCB1 over per-persona invocation count +
# mean verified grade; a persona with ZERO ledger entries scores +inf so it is always eligible to explore ->
# every persona is eventually reachable. Deterministic (no RNG) so selection stays reproducible.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "persona_select"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "ucb1",
     "kinds": ["edge"],
     "prompt": ("Write ucb1(mean, count, total, c) -> float, the UCB1 selection score. Import math inside. An "
                "UNSEEN persona (count is not a positive int, or <= 0) returns float('inf') — it must always be "
                "eligible to explore. Otherwise: coerce mean->float (bad->0.0), count->int n>0, total->int t "
                "(t<1 becomes 1), c->float (bad->1.4); return mean + c * math.sqrt(math.log(t) / n). A bool "
                "passed as count is NOT a valid count (treat as unseen -> inf). Never raise; on unexpected "
                "error return float('inf') (fail toward exploration)." + "\n" + _ONLY),
     "tests": [
        "assert ucb1(0.5, 0, 100, 1.4) == float('inf')",
        "assert ucb1(0.9, -3, 10, 1.4) == float('inf')",
        "assert ucb1(0.8, 10, 100, 0.0) == 0.8",
        "assert ucb1(0.0, 1, 1, 1.4) == 0.0",
        "assert ucb1(0.5, True, 10, 1.4) == float('inf')",
        "r = ucb1(0.5, 4, 100, 1.4); assert 1.5 < r < 3.0",
        "assert ucb1(0.5, 'x', 10, 1.4) == float('inf')",
     ]},
]

CRITERIA = [
    {"id": "S1", "text": "UCB1 score balances exploit (grade) vs explore; an unseen persona scores +inf (FR-3/FR-4)",
     "tests": ["ucb1"]},
]
