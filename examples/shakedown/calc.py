'''calc.py — a safe arithmetic evaluator (shunting-yard), authored as a Lathe plan.

Three pure functions compose into evaluate(); no eval(), no recursion.
This is the plan from the v2.62.6 live shakedown (docs/SHAKEDOWN_v2.62.6_TERMINAL_DRIVE.md).

RUN IT (from the repo root, with the two endpoints up — see examples/shakedown/README.md):
    LATHE_MUTATION_SCORE=0.5 LATHE_TRUST_PLAN=1 python3 lathe.py build examples/shakedown/calc.py

Why LATHE_TRUST_PLAN=1: the INTEGRATION test must `import` the module, but the plan validator
otherwise bans imports (issue #44). Trust mode is the current workaround.
'''

MODULE_NAME = "calc"
OUT_DIR = "examples/shakedown/build"          # relative to repo root; inside the tree so the OUT_DIR guard is happy

HEADER = (
    "class CalcError(Exception):\n"
    "    \"\"\"Raised on any malformed expression.\"\"\"\n"
    "    pass\n"
)

FUNCTIONS = [
    {
        "name": "tokenize",
        "prompt": (
            "Write tokenize(expr: str) -> list. Turn an arithmetic expression string into a list of "
            "(kind, value) tuples. A number becomes ('num', float(value)) and supports integers and "
            "decimals like '12' or '3.5'. The operators + - * / and the two-character ** each become "
            "('op', symbol); recognise '**' BEFORE a single '*'. Parentheses become ('op', '(') and "
            "('op', ')'). Skip all whitespace. Raise CalcError (already defined in scope) on any "
            "character that is not a digit, '.', whitespace, an operator, or a parenthesis. "
            "kind is the string 'num' or 'op'."
        ),
        "tests": [
            "assert tokenize('1 + 2') == [('num', 1.0), ('op', '+'), ('num', 2.0)]",
            "assert tokenize('3.5*4') == [('num', 3.5), ('op', '*'), ('num', 4.0)]",
            "assert tokenize('2**3') == [('num', 2.0), ('op', '**'), ('num', 3.0)]",
            "assert tokenize('(1)') == [('op', '('), ('num', 1.0), ('op', ')')]",
            "assert tokenize('') == []",
            "try:\n    tokenize('1 $ 2')\n    assert False\nexcept CalcError:\n    pass",
        ],
    },
    {
        "name": "to_rpn",
        "prompt": (
            "Write to_rpn(tokens: list) -> list. Convert a token list (each a ('num', float) or "
            "('op', symbol) tuple, as produced by tokenize) into Reverse Polish Notation using the "
            "shunting-yard algorithm. Operator precedence, lowest to highest: ('+','-') then ('*','/') "
            "then ('**'). '**' is RIGHT-associative; '+ - * /' are LEFT-associative. Handle '(' and ')' "
            "grouping. Output is a list of the same ('num'/'op') tuples in RPN order (numbers and "
            "operators, no parentheses). Raise CalcError (in scope) on mismatched parentheses."
        ),
        "tests": [
            "assert to_rpn([('num',1.0),('op','+'),('num',2.0)]) == [('num',1.0),('num',2.0),('op','+')]",
            "assert to_rpn([('num',2.0),('op','+'),('num',3.0),('op','*'),('num',4.0)]) == [('num',2.0),('num',3.0),('num',4.0),('op','*'),('op','+')]",
            "assert to_rpn([('op','('),('num',2.0),('op','+'),('num',3.0),('op',')'),('op','*'),('num',4.0)]) == [('num',2.0),('num',3.0),('op','+'),('num',4.0),('op','*')]",
            "assert to_rpn([('num',2.0),('op','**'),('num',3.0),('op','**'),('num',2.0)]) == [('num',2.0),('num',3.0),('num',2.0),('op','**'),('op','**')]",
            "try:\n    to_rpn([('op','('),('num',1.0)])\n    assert False\nexcept CalcError:\n    pass",
        ],
    },
    {
        "name": "eval_rpn",
        "prompt": (
            "Write eval_rpn(rpn: list) -> float. Evaluate a Reverse Polish Notation list of ('num', float) "
            "and ('op', symbol) tuples using a stack. Operators: '+', '-', '*', '/', '**' (Python power). "
            "Each operator pops two operands (left = the deeper one). Return the final float. Raise "
            "CalcError (in scope) on division by zero, or if the expression is malformed (too few operands, "
            "or leftover operands remain on the stack at the end)."
        ),
        "tests": [
            "assert eval_rpn([('num',1.0),('num',2.0),('op','+')]) == 3.0",
            "assert eval_rpn([('num',2.0),('num',3.0),('num',4.0),('op','*'),('op','+')]) == 14.0",
            "assert eval_rpn([('num',10.0),('num',2.0),('op','/'),('num',5.0),('op','/')]) == 1.0",
            "assert eval_rpn([('num',2.0),('num',3.0),('num',2.0),('op','**'),('op','**')]) == 512.0",
            "try:\n    eval_rpn([('num',1.0),('num',0.0),('op','/')])\n    assert False\nexcept CalcError:\n    pass",
            "try:\n    eval_rpn([('num',1.0),('num',2.0)])\n    assert False\nexcept CalcError:\n    pass",
        ],
    },
]

GLUE = (
    "def evaluate(expr):\n"
    "    \"\"\"Safely evaluate an arithmetic expression string (no eval()).\"\"\"\n"
    "    return eval_rpn(to_rpn(tokenize(expr)))\n"
)

INTEGRATION = (
    "from calc import *\n"                      # the itest runs standalone in OUT_DIR — it must import the module
    "assert evaluate('2 + 3 * 4') == 14.0\n"
    "assert evaluate('(2 + 3) * 4') == 20.0\n"
    "assert evaluate('2 ** 3 ** 2') == 512.0\n"
    "assert evaluate('10 / 2 / 5') == 1.0\n"
    "try:\n    evaluate('1 / 0')\n    assert False\nexcept CalcError:\n    pass\n"
    "try:\n    evaluate('1 + ')\n    assert False\nexcept CalcError:\n    pass\n"
)
