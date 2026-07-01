# M02_dedupe_keep_order - matcher helper (gated pure function). Auto-refilled by refill_plans.py so a prior agent never idles.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "dedupe_keep_order"
HEADER = ""
GLUE = ""
_ONLY = 'Output ONLY the Python function code - no prose, no markdown, no tests. Import any module you need INSIDE the function. Define constants INSIDE the function.'
FUNCTIONS = [
    {
        "name": "dedupe_keep_order",
        "prompt": 'Implement dedupe_keep_order(items) -> list. Return items with duplicates removed, preserving first-seen order. Items are hashable. Empty/None -> []. Never raise.' + "\n" + _ONLY,
        "tests": ['assert dedupe_keep_order([3,1,3,2,1])==[3,1,2]', 'assert dedupe_keep_order([])==[]', "assert dedupe_keep_order(['a','a'])==['a']", 'assert dedupe_keep_order(None)==[]'],
    },
]
