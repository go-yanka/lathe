# M04_weighted_mean - matcher helper (gated pure function). Auto-refilled by refill_plans.py so a prior agent never idles.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "weighted_mean"
HEADER = ""
GLUE = ""
_ONLY = 'Output ONLY the Python function code - no prose, no markdown, no tests. Import any module you need INSIDE the function. Define constants INSIDE the function.'
FUNCTIONS = [
    {
        "name": "weighted_mean",
        "prompt": 'Implement weighted_mean(pairs) -> float. pairs is iterable of (value, weight). Return sum(v*w)/sum(w) rounded 4dp. If total weight is 0 or empty -> 0.0. Never raise.' + "\n" + _ONLY,
        "tests": ['assert weighted_mean([(10,1),(20,3)])==17.5', 'assert weighted_mean([])==0.0', 'assert weighted_mean([(5,0)])==0.0', 'assert weighted_mean([(4,1),(8,1)])==6.0'],
    },
]
