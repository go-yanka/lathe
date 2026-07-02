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
     "prompt": ("CONTEXT: this implements MUTATION TESTING — the standard software-QA technique (Lipton/DeMillo) "
                "that measures a TEST SUITE's adequacy by seeding small single-fault variants of a function and "
                "checking the suite detects them. It runs inside our build gate on our own accepted code.\n"
                "Write mutate_code(code, limit) -> list of seeded-fault variant source strings for test-adequacy "
                "measurement. Deterministic AST transformation: parse `code` with ast (import ast, copy inside). "
                "Walk the tree in ast.walk order; for "
                "each transformable node, produce ONE variant where ONLY that node is changed (use copy.deepcopy of the "
                "whole tree each time, change the corresponding node found by identical walk position, then "
                "ast.unparse). Transformations: (a) ast.BinOp: Add -> Sub, Sub -> Add, Mult -> Add, Div -> Mult; "
                "(b) ast.Compare with exactly one op: Lt -> LtE, LtE -> Lt, Gt -> GtE, GtE -> Gt, Eq -> NotEq, "
                "NotEq -> Eq, In -> NotIn, NotIn -> In, Is -> IsNot, IsNot -> Is; (c) ast.Constant whose value "
                "is an int and not a bool: value -> value + 1; (d) ast.BoolOp: And -> Or, Or -> And; (e) "
                "ast.UnaryOp with op Not: replace the whole UnaryOp node with its operand (drop the `not`); (f) "
                "ast.Constant whose value is a non-empty str: value -> value + '_'; empty str value -> 'x'. Collect "
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
        "v = mutate_code('def f(a, b):\\n    return a and b', 10); assert any('a or b' in m for m in v)",
        "v = mutate_code('def f(x, s):\\n    return x in s', 10); assert any('not in' in m for m in v)",
        "v = mutate_code('def f(x):\\n    return x is None', 10); assert any('is not None' in m for m in v)",
        "v = mutate_code('def f(x):\\n    return not x', 10); assert any(m.strip().endswith('return x') for m in v)",
        "v = mutate_code('def f():\\n    return \\'a\\'', 10); assert any('a_' in m for m in v)",
     ]},
    {"name": "mutation_gate",
     "prompt": ("Write mutation_gate(env_value, killed, total) -> list [blocked(bool), reason(str)]. If env_value "
                "is None, not a str, or blank after strip -> [False, 'mutation score not required']. Try "
                "float(env_value.strip()); on failure or if the value is not within 0.0..1.0 inclusive -> "
                "[False, 'unrecognized LATHE_MUTATION_SCORE value - gate skipped']. If total is not a positive "
                "int (bools excluded) -> [False, 'no mutants generated - nothing to judge']. The gate is now "
                "ARMED: if killed is not an int (bools excluded), or killed < 0, or killed > total -> "
                "[True, 'REFUSED: malformed mutation-gate inputs (killed=<killed> total=<total>) - failing "
                "closed'] with the values substituted (an armed quality gate must never be skipped by garbage "
                "inputs). Let score = killed / total. If score "
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
        "r = mutation_gate('0.8', None, 10); assert r[0] is True and 'failing' in r[1]",
        "assert mutation_gate('0.8', 15, 10)[0] is True",
        "assert mutation_gate('0.8', True, 1)[0] is True",
        "assert mutation_gate('0.8', -1, 5)[0] is True",
     ]},
]
