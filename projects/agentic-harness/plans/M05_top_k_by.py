# M05_top_k_by - matcher helper (gated pure function). Auto-refilled by refill_plans.py so a prior agent never idles.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "top_k_by"
HEADER = ""
GLUE = ""
_ONLY = 'Output ONLY the Python function code - no prose, no markdown, no tests. Import any module you need INSIDE the function. Define constants INSIDE the function.'
FUNCTIONS = [
    {
        "name": "top_k_by",
        "prompt": 'Implement top_k_by(score_map, k) -> list of (id, score) tuples, highest score first, ties broken by id ascending, at most k entries. k<=0 or empty -> []. Never raise.' + "\n" + _ONLY,
        "tests": ["assert top_k_by({'a':10,'b':30,'c':20},2)==[('b',30),('c',20)]", 'assert top_k_by({},3)==[]', "assert top_k_by({'a':5},0)==[]", "assert top_k_by({'a':5,'b':5},2)==[('a',5),('b',5)]"],
    },
]
