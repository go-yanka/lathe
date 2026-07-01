# M09_clamp_range - matcher helper (gated pure function). Auto-refilled by refill_plans.py so a prior agent never idles.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "clamp_range"
HEADER = ""
GLUE = ""
_ONLY = 'Output ONLY the Python function code - no prose, no markdown, no tests. Import any module you need INSIDE the function. Define constants INSIDE the function.'
FUNCTIONS = [
    {
        "name": "clamp_range",
        "prompt": 'Implement clamp_range(x, lo, hi) -> float. Return x clamped to [lo,hi]. If lo>hi, swap them. None x -> lo. Never raise.' + "\n" + _ONLY,
        "tests": ['assert clamp_range(5,0,10)==5', 'assert clamp_range(-1,0,10)==0', 'assert clamp_range(99,0,10)==10', 'assert clamp_range(5,10,0)==5'],
    },
]
