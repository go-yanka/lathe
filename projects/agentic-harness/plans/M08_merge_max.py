# M08_merge_max - matcher helper (gated pure function). Auto-refilled by refill_plans.py so a prior agent never idles.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "merge_max"
HEADER = ""
GLUE = ""
_ONLY = 'Output ONLY the Python function code - no prose, no markdown, no tests. Import any module you need INSIDE the function. Define constants INSIDE the function.'
FUNCTIONS = [
    {
        "name": "merge_max",
        "prompt": 'Implement merge_max(maps) -> dict. maps is a list of dicts id->score. Return a single dict mapping each id to the MAX score seen across all maps. Empty -> {}. Never raise.' + "\n" + _ONLY,
        "tests": ["assert merge_max([{'a':1},{'a':5,'b':2}])=={'a':5,'b':2}", 'assert merge_max([])=={}', "assert merge_max([{'x':3},{'x':1}])=={'x':3}"],
    },
]
