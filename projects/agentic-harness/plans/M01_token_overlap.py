# M01_token_overlap - matcher helper (gated pure function). Auto-refilled by refill_plans.py so a prior agent never idles.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "token_overlap"
HEADER = ""
GLUE = ""
_ONLY = 'Output ONLY the Python function code - no prose, no markdown, no tests. Import any module you need INSIDE the function. Define constants INSIDE the function.'
FUNCTIONS = [
    {
        "name": "token_overlap",
        "prompt": "Implement token_overlap(a, b) -> int. a and b are strings. Lowercase each, split on whitespace into word sets, return the count of shared distinct words. None -> treated as ''. Never raise." + "\n" + _ONLY,
        "tests": ["assert token_overlap('data science','science of data')==2", "assert token_overlap('','x')==0", "assert token_overlap('a a b','a b')==2", "assert token_overlap(None,'x')==0"],
    },
]
