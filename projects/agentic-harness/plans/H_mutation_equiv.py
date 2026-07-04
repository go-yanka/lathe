# H_mutation_equiv — E2 fix (review §16.1, HIGH): equivalent mutants must not count against the score.
# A mutant no input can distinguish from the original (e.g. slack in a guard constant: n=5 -> n=6 with
# `if n > 0`) is UNKILLABLE — counting it makes the gate a false-positive generator on correct code and
# "strengthen the tests" impossible advice. Fix: a BOUNDED, DETERMINISTIC differential probe — evaluate
# original vs mutant over a fixed canonical input sample; no sampled difference -> equivalent -> excluded
# from the denominator (reported, not hidden). No RNG: the gate stays reproducible.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "mutation_equiv"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "equivalent_over_samples",
     "prompt": ("Write equivalent_over_samples(code_a, code_b, name) -> bool. A DETERMINISTIC differential probe "
                "deciding whether two functions are behaviorally indistinguishable over a fixed canonical "
                "sample (used to EXCLUDE equivalent mutants from a mutation score, so it must err toward "
                "returning False when equivalence is not PROVEN). exec code_a and code_b each in its own fresh "
                "namespace {'__builtins__': __builtins__}; fetch the callable `name` from each (missing/exec "
                "error in EITHER -> return False). Canonical pool P = [-2, -1, 0, 1, 2, 10, -10, '', 'a', 'ab', "
                "None, True, False, [], [0, 1]]. probes = [(x,) for x in P] + list(zip(P, reversed(P))) + "
                "[(0, 0), (1, 2), ('a', 'b'), (True, False)]. THEN broaden the probe set off the fixed sample "
                "(#12 #2/#3): try `from pbt_sample import sample_inputs` inside a try, and if it imports, do "
                "`probes = probes + sample_inputs(1337, 24)` (a FIXED seed so the gate stays deterministic) — "
                "this adds the adversarial structural-string classes (';'-packed, '#'-comment, whitespace, "
                "NUL). On ImportError keep just the fixed probes. For each probe call BOTH functions, capturing "
                "either ('ok', VALUE) on success or ('err', type(e).__name__) on Exception (catch Exception "
                "only; keep the ACTUAL value — do NOT repr it). Two captures are SAME iff: both are ('err', X) "
                "with equal X; OR both are ('ok', va) and ('ok', vb) with va == vb evaluated inside a try (if "
                "the '==' itself raises, fall back to repr(va) == repr(vb)). If ANY probe's captures are NOT "
                "same -> return False immediately (distinguishable). Track whether at least one probe produced a "
                "matching ('ok', ...) on BOTH sides — a real VALUE agreement, not merely an error agreement. "
                "After all probes, return True ONLY if there was >=1 such real value agreement; otherwise return "
                "False (never declare equivalence from error-agreement alone, nor from an all-error/unprobeable "
                "run). Never raise; any unexpected error -> False." + "\n" + _ONLY),
     "tests": [
        "a = 'def f(x):\\n    n = 5\\n    if n > 0:\\n        return x * 2\\n    return -x'",
        "b = 'def f(x):\\n    n = 6\\n    if n > 0:\\n        return x * 2\\n    return -x'",
        "assert equivalent_over_samples(a, b, 'f') is True",
        "c = 'def f(x):\\n    return x * x'",
        "d = 'def f(x):\\n    return x + x'",
        "assert equivalent_over_samples(c, d, 'f') is False",
        "assert equivalent_over_samples(c, 'def f(x):\\n    return x * x', 'f') is True",
        "assert equivalent_over_samples(c, 'not python ((', 'f') is False",
        "assert equivalent_over_samples(c, 'def g(x):\\n    return x * x', 'f') is False",
        "e2 = 'def f(a, b):\\n    return a and b'",
        "e3 = 'def f(a, b):\\n    return a or b'",
        "assert equivalent_over_samples(e2, e3, 'f') is False",
        "raiser = 'def f(x):\\n    raise ValueError(\\'boom\\')'",
        "assert equivalent_over_samples(raiser, raiser, 'f') is False",
        "da = 'def f(x):\\n    return {\\'a\\': 1, \\'b\\': 2}'",
        "db = 'def f(x):\\n    return {\\'b\\': 2, \\'a\\': 1}'",
        "assert equivalent_over_samples(da, db, 'f') is True",
        "g10a = 'def f(x):\\n    return 1 if x == 10 else 0'",
        "assert equivalent_over_samples(g10a, 'def f(x):\\n    return 0', 'f') is False",
        "gna = 'def f(x):\\n    return 1 if x == -10 else 0'",
        "assert equivalent_over_samples(gna, 'def f(x):\\n    return 0', 'f') is False",
        "h2a = 'def f(a, b):\\n    return a - b'",
        "h2b = 'def f(a, b):\\n    return b - a'",
        "assert equivalent_over_samples(h2a, h2b, 'f') is False",
        "assert equivalent_over_samples(h2a, 'def f(a, b):\\n    return a - b', 'f') is True",
        "assert equivalent_over_samples('def f(x):\\n    return x', 'def f(x):\\n    return x', 'f') is True",
     ]},
]

CRITERIA = [
    {"id": "M1", "text": "Two functions are equivalent ONLY when they agree on a real value over the probe "
                         "sample (never from error-agreement alone); value-equality, not repr, is the oracle",
     "tests": ["equivalent_over_samples"]},
]
