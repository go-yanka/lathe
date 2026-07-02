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
     "prompt": ("Write equivalent_over_samples(code_a, code_b, name) -> bool. Deterministic differential probe: "
                "exec code_a and code_b each in its own fresh dict namespace ({'__builtins__': __builtins__}); "
                "fetch the callable `name` from each (missing/exec error in EITHER -> return False: not provably "
                "equivalent). Canonical pool P = [-2, -1, 0, 1, 2, 10, -10, '', 'a', 'ab', None, True, False, "
                "[], [0, 1]]. Probe arity 1: call f(x) for each x in P. Probe arity 2: call f(x, y) for (x, y) "
                "in zip(P, reversed(P)) plus [(0, 0), (1, 2), ('a', 'b'), (True, False)]. For each probe args: "
                "call BOTH functions; capture the result as ('ok', repr(value)) or ('err', type(e).__name__) — "
                "catch Exception only. If for ANY probe the two captures DIFFER -> return False immediately "
                "(distinguishable). If the functions raised TypeError on EVERY arity-1 probe AND every arity-2 "
                "probe (wrong arity for both patterns) -> return False (unprobeable; never claim equivalence "
                "blindly). Otherwise (>=1 successfully-compared probe, all captures identical) -> return True. "
                "Never raise; any unexpected error -> False." + "\n" + _ONLY),
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
     ]},
]
