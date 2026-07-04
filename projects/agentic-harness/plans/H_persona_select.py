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
    {"name": "select_personas",
     "kinds": ["edge", "property"],
     "prompt": ("Write select_personas(names, counts, grades, k, c) -> list of the top-k persona names by UCB1, "
                "SELF-CONTAINED (inline the UCB1 formula; do not call other module functions). Import math "
                "inside. names: list of candidate name strings (skip non-str). counts: dict name->invocation "
                "count. grades: dict name->mean verified grade. Compute total = sum of the positive int values "
                "in counts. For each name compute its score: if counts.get(name) is not a positive int -> "
                "float('inf') (unseen, always explorable); else float(grades.get(name,0.0)) + float(c if a valid "
                "number else 1.4) * math.sqrt(math.log(max(total,1)) / count). Rank DESCENDING by score; break "
                "ties by name ascending (deterministic). Return the first k names (k coerced to int; k<=0 or "
                "bad -> []). names not a list -> []. counts/grades not dicts -> treat as {}. Never raise. Because "
                "every unseen persona scores inf, repeatedly selecting and incrementing counts eventually "
                "reaches EVERY name — that is the reachability guarantee." + "\n" + _ONLY),
     "tests": [
        "N = ['a','b','c','d']",
        "assert select_personas(N, {}, {}, 2, 1.4) == ['a','b']  # all unseen -> deterministic name order",
        "assert select_personas(N, {'a':5,'b':5,'c':5,'d':5}, {'a':0.9,'b':0.1,'c':0.5,'d':0.5}, 1, 1.4) == ['a']  # highest grade wins when counts equal",
        "assert select_personas(N, {'a':5,'b':5}, {'a':0.9,'b':0.9}, 4, 1.4)[:2] == ['c','d']  # unseen c,d rank above seen a,b",
        "assert select_personas(N, {}, {}, 0, 1.4) == []",
        "assert select_personas('nope', {}, {}, 2, 1.4) == []",
        "assert select_personas(N, {}, {}, 99, 1.4) == ['a','b','c','d']",
        "assert all(x in set(N) for x in select_personas(N, {'a':2,'b':2,'c':2,'d':2}, {}, 4, 1.4))  # property: every pick is a valid candidate",
        # reachability property: with k=1, every unseen persona surfaces within 4 rounds (each scores +inf)
        "cc={n:0 for n in N}",
        "r1=select_personas(N, cc, {}, 1, 1.4)[0]; cc[r1]=cc[r1]+1",
        "r2=select_personas(N, cc, {}, 1, 1.4)[0]; cc[r2]=cc[r2]+1",
        "r3=select_personas(N, cc, {}, 1, 1.4)[0]; cc[r3]=cc[r3]+1",
        "r4=select_personas(N, cc, {}, 1, 1.4)[0]; cc[r4]=cc[r4]+1",
        "assert {r1, r2, r3, r4} == set(N)  # ALL personas reachable within N rounds",
     ]},
]

CRITERIA = [
    {"id": "S1", "text": "UCB1 score balances exploit (grade) vs explore; an unseen persona scores +inf (FR-3/FR-4)",
     "tests": ["ucb1"]},
    {"id": "S2", "text": "Selection surfaces unseen personas first, so every persona is eventually reachable (BR-2)",
     "tests": ["select_personas"]},
]
