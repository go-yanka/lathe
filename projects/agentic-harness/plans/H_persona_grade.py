# H_persona_grade — persona redesign STAGE 3 (issue #9): work-based grading. A persona's grade must come from
# findings that SURVIVE independent verification (cold-start prior, no originating context) — track record, not
# articulation (the old `lathe agent rate` measured talk). FR-6: credit a finding only when the verifier passes
# it; BR-4: verified grade is the sole exploitation weight; cold-start prior so new personas aren't stuck at 0.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "persona_grade"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "finding_score",
     "kinds": ["edge"],
     "prompt": ("Write finding_score(result, min_conf) -> float or None. A finding is credited toward a grade "
                "ONLY when its independent verifier PASSED it with enough confidence (FR-6). `result` is a dict "
                "{'pass': bool, 'confidence': float in [0,1]}. Rules: result not a dict -> None. If result.get("
                "'pass') is falsy -> None (verifier rejected it — discard, do not grade). Coerce confidence to "
                "float (missing/bad -> 0.0) and CLAMP it to [0.0, 1.0] FIRST. Coerce min_conf to float (bad -> "
                "0.0). If the clamped confidence < min_conf -> None (too weak to count). Otherwise return the "
                "clamped confidence. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert finding_score({'pass': True, 'confidence': 0.8}, 0.5) == 0.8",
        "assert finding_score({'pass': False, 'confidence': 0.9}, 0.5) is None",
        "assert finding_score({'pass': True, 'confidence': 0.3}, 0.5) is None",
        "assert finding_score({'pass': True, 'confidence': 1.5}, 0.5) == 1.0",
        "assert finding_score({'pass': True}, 0.5) is None",
        "assert finding_score('nope', 0.5) is None",
        "assert finding_score({'pass': True, 'confidence': -0.2}, 0.0) == 0.0",
     ]},
    {"name": "grade_update",
     "kinds": ["edge", "property"],
     "prompt": ("Write grade_update(prior, prior_weight, scores) -> float in [0.0, 1.0], a smoothed grade with a "
                "cold-start prior. Coerce prior -> float (bad -> 0.5) then clamp to [0,1]; prior_weight -> float "
                "(bad or < 0 -> 1.0); scores -> keep only the real numbers in the iterable (drop bool and "
                "non-numbers; a bool is NOT a number here), each clamped to [0,1]. If there are no valid scores, "
                "return the (clamped) prior. Otherwise return clamp01( (prior*prior_weight + sum(scores)) / "
                "(prior_weight + len(scores)) ). This is a pseudo-count Bayesian mean: with prior_weight pseudo-"
                "observations at `prior`, a new persona starts near the prior and moves toward its measured mean "
                "as real verified findings accumulate. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert grade_update(0.5, 4, []) == 0.5",
        "assert grade_update(0.5, 0, [1.0, 1.0]) == 1.0",
        "assert grade_update(0.5, 4, [1.0]) == 0.6",
        "assert grade_update(0.5, 4, [0.0]) == 0.4",
        "assert grade_update(2.0, 1, []) == 1.0",
        "assert abs(grade_update(0.5, 4, [True, 0.8, 'x']) - 0.56) < 1e-9  # bool/'x' dropped -> [0.8]",
        "assert all(0.0 <= grade_update(0.5, 4, [s]) <= 1.0 for s in [0.0, 0.5, 1.0, 2.0, -1.0])",
        "assert grade_update('bad', 4, []) == 0.5",
     ]},
]

CRITERIA = [
    {"id": "G1", "text": "Credit a finding to a grade only when its independent verifier passed it (FR-6)",
     "tests": ["finding_score"]},
    {"id": "G2", "text": "Compute a smoothed grade with a cold-start prior so new personas aren't stuck at zero (BR-3/BR-4)",
     "tests": ["grade_update"]},
]
