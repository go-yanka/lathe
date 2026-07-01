# M06_invert_map - matcher helper (gated pure function). Auto-refilled by refill_plans.py so a prior agent never idles.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "invert_map"
HEADER = ""
GLUE = ""
_ONLY = 'Output ONLY the Python function code - no prose, no markdown, no tests. Import any module you need INSIDE the function. Define constants INSIDE the function.'
FUNCTIONS = [
    {
        "name": "invert_map",
        "prompt": 'Implement invert_map(d) -> dict. Given dict key->value (values hashable), return value->list of keys that had it, keys in insertion order. Empty -> {}. Never raise.' + "\n" + _ONLY,
        "tests": ["assert invert_map({'a':1,'b':1,'c':2})=={1:['a','b'],2:['c']}", 'assert invert_map({})=={}', "assert invert_map({'x':9})=={9:['x']}"],
    },
]
