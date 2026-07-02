# H_mutation_score — enforcement mechanism #3 (the one that earns the word "comprehensiveness"): test
# strength is MEASURED, not assumed. After a candidate passes its tests, deterministic AST mutants of the
# ACCEPTED code are generated (operator swaps, constant nudges); the suite must KILL >= threshold of them
# (LATHE_MUTATION_SCORE=<0..1>). A green suite that can't tell x*x from x+x proves nothing. LLM-free.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "mutation_score"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "mutate_code",
     "prompt": ("Write mutate_code(code, limit) -> list of mutated Python source strings. Deterministic AST "
                "mutation: parse `code` with ast (import ast, copy inside). Walk the tree in ast.walk order; for "
                "each mutable node, produce ONE variant where ONLY that node is changed (use copy.deepcopy of the "
                "whole tree each time, mutate the corresponding node found by identical walk position, then "
                "ast.unparse). Mutations: (a) ast.BinOp: Add -> Sub, Sub -> Add, Mult -> Add, Div -> Mult; "
                "(b) ast.Compare with exactly one op: Lt -> LtE, LtE -> Lt, Gt -> GtE, GtE -> Gt, Eq -> NotEq, "
                "NotEq -> Eq; (c) ast.Constant whose value is an int and not a bool: value -> value + 1. Collect "
                "variants in walk order, return at most `limit` (limit <= 0 -> []). Skip variants whose unparse "
                "fails. code None/non-str/unparseable -> []. Never raise." + "\n" + _ONLY),
     "tests": [
        "v = mutate_code('def f(x):\\n    return x * x', 10); assert any('x + x' in m for m in v)",
        "v = mutate_code('def f(x):\\n    if x < 0:\\n        return 0\\n    return x', 20); assert any('x <= 0' in m for m in v)",
        "v = mutate_code('def f():\\n    return 1', 10); assert any('return 2' in m for m in v)",
        "v = mutate_code('def f(x):\\n    return x == 3', 20); assert any('x != 3' in m for m in v)",
        "assert mutate_code('not python ((', 10) == []",
        "assert mutate_code(None, 10) == []",
        "assert mutate_code('def f(x):\\n    return x * x', 0) == []",
        "v = mutate_code('def f(x):\\n    return x + x - x * x', 2); assert len(v) == 2",
        "v = mutate_code('def f(x):\\n    return True', 10); assert all('return 2' not in m for m in v)",
     ]},
    {"name": "mutation_gate",
     "prompt": ("Write mutation_gate(env_value, killed, total) -> list [blocked(bool), reason(str)]. If env_value "
                "is None, not a str, or blank after strip -> [False, 'mutation score not required']. Try "
                "float(env_value.strip()); on failure or if the value is not within 0.0..1.0 inclusive -> "
                "[False, 'unrecognized LATHE_MUTATION_SCORE value - gate skipped']. If total is not a positive "
                "int -> [False, 'no mutants generated - nothing to judge']. Let score = killed / total. If score "
                "+ 1e-9 >= threshold -> [False, 'mutation score ok: killed K/T']. Else -> [True, 'REFUSED: tests "
                "kill only K/T mutants (score S.SS < threshold X.XX) - the suite cannot distinguish the accepted "
                "code from its mutants; strengthen the tests'] with K, T, score to 2 decimals and threshold to 2 "
                "decimals substituted. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert mutation_gate(None, 0, 5) == [False, 'mutation score not required']",
        "assert mutation_gate('', 0, 5) == [False, 'mutation score not required']",
        "assert mutation_gate('abc', 0, 5)[0] is False",
        "assert mutation_gate('1.5', 0, 5)[0] is False",
        "assert mutation_gate('0.5', 0, 0)[0] is False",
        "assert mutation_gate('0.5', 3, 5) == [False, 'mutation score ok: killed 3/5']",
        "assert mutation_gate('0.5', 2, 5)[0] is True",
        "r = mutation_gate('0.9', 1, 2); assert r[0] is True and '1/2' in r[1] and '0.50' in r[1] and '0.90' in r[1]",
        "assert mutation_gate('1.0', 5, 5)[0] is False",
     ]},
]
