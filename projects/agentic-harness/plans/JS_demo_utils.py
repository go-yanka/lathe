# #60 polyglot proof: JavaScript functions, model-written, node-gated, pinned. Mixed with one python fn
# to prove both lanes coexist in one plan.
OUT_DIR = "projects/agentic-harness/goals/js-demo"
MODULE_NAME = "demo_utils"
HEADER = ""
GLUE = ""
FUNCTIONS = [
    {
        "name": "clampJs",
        "lang": "js",
        "prompt": (
            "Write ONE JavaScript function declaration clampJs(x, lo, hi) that returns x clamped into the "
            "inclusive range [lo, hi]. If x is null or undefined treat it as 0. Use a classic `function "
            "clampJs(x, lo, hi) { ... }` declaration, no arrow, no exports, no comments. "
            "Output ONLY the JavaScript function code - no prose, no markdown."
        ),
        "tests": [
            "assert(clampJs(5, 0, 10) === 5)",
            "assert(clampJs(-3, 0, 10) === 0)",
            "assert(clampJs(99, 0, 10) === 10)",
            "assert(clampJs(null, 2, 10) === 2)",
            "assert(clampJs(undefined, -5, 5) === 0)",
        ],
    },
    {
        "name": "titleCaseJs",
        "lang": "js",
        "prompt": (
            "Write ONE JavaScript function declaration titleCaseJs(s) that upper-cases the first letter of "
            "every whitespace-separated word and lower-cases the rest of each word. If s is null, undefined "
            "or empty return ''. Use a classic function declaration, no arrow, no exports, no comments. "
            "Output ONLY the JavaScript function code - no prose, no markdown."
        ),
        "tests": [
            "assert(titleCaseJs('hello world') === 'Hello World')",
            "assert(titleCaseJs('HELLO') === 'Hello')",
            "assert(titleCaseJs('') === '')",
            "assert(titleCaseJs(null) === '')",
            "assert(titleCaseJs('a b c') === 'A B C')",
        ],
    },
    {
        "name": "clamp_py",
        "prompt": (
            "Write a pure Python function clamp_py(x, lo, hi) that returns x clamped into the inclusive "
            "range [lo, hi]; if x is None treat it as 0. Output ONLY the Python function code - no prose, "
            "no markdown."
        ),
        "tests": [
            "assert clamp_py(5, 0, 10) == 5",
            "assert clamp_py(-3, 0, 10) == 0",
            "assert clamp_py(99, 0, 10) == 10",
            "assert clamp_py(None, 2, 10) == 2",
        ],
    },
]
