# M03_group_by_first - matcher helper (gated pure function). Auto-refilled by refill_plans.py so a prior agent never idles.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "group_by_first"
HEADER = ""
GLUE = ""
_ONLY = 'Output ONLY the Python function code - no prose, no markdown, no tests. Import any module you need INSIDE the function. Define constants INSIDE the function.'
FUNCTIONS = [
    {
        "name": "group_by_first",
        "prompt": 'Implement group_by_first(pairs) -> dict. pairs is an iterable of (key, value). Return dict mapping each key to a list of its values in order. Empty -> {}. Never raise.' + "\n" + _ONLY,
        "tests": ["assert group_by_first([('a',1),('b',2),('a',3)])=={'a':[1,3],'b':[2]}", 'assert group_by_first([])=={}', "assert group_by_first([('x',1)])=={'x':[1]}"],
    },
]
