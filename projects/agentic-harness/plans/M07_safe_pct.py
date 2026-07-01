# M07_safe_pct - matcher helper (gated pure function). Auto-refilled by refill_plans.py so a prior agent never idles.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "safe_pct"
HEADER = ""
GLUE = ""
_ONLY = 'Output ONLY the Python function code - no prose, no markdown, no tests. Import any module you need INSIDE the function. Define constants INSIDE the function.'
FUNCTIONS = [
    {
        "name": "safe_pct",
        "prompt": 'Implement safe_pct(part, whole) -> float. Return part/whole*100 rounded 2dp. whole==0 -> 0.0. Clamp result to [0,100]. Never raise.' + "\n" + _ONLY,
        "tests": ['assert safe_pct(1,4)==25.0', 'assert safe_pct(5,0)==0.0', 'assert safe_pct(10,5)==100.0', 'assert safe_pct(0,5)==0.0'],
    },
]
