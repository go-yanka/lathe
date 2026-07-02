# Ledger demo app — plan 2/3: aggregation over parsed entries (builds on plan 1's entry dicts).
OUT_DIR = "examples/ledger"
MODULE_NAME = "ledger_stats"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "total",
     "prompt": ("Write total(entries) that sums the 'amount' field over a list of entry dicts "
                "(each like {'date':..,'category':..,'amount':float}). None or empty -> 0.0. Round to 2 decimals. "
                "Never raise." + "\n" + _ONLY),
     "tests": ["assert total([{'amount':1.5},{'amount':2.25}])==3.75", "assert total([])==0.0",
               "assert total(None)==0.0", "assert total([{'amount':-1.0},{'amount':1.0}])==0.0"]},
    {"name": "by_category",
     "prompt": ("Write by_category(entries) that returns a dict mapping each entry's 'category' to the summed "
                "'amount' for that category, rounded to 2 decimals. None or empty -> {}. Never raise." + "\n" + _ONLY),
     "tests": ["assert by_category([{'category':'a','amount':1.0},{'category':'a','amount':2.0},{'category':'b','amount':5.0}])=={'a':3.0,'b':5.0}",
               "assert by_category([])=={}", "assert by_category(None)=={}"]},
    {"name": "top_category",
     "prompt": ("Write top_category(entries) that returns the category name with the highest summed amount "
                "(use the same summing as by_category). None or empty -> None. Never raise." + "\n" + _ONLY),
     "tests": ["assert top_category([{'category':'a','amount':1.0},{'category':'b','amount':9.0}])=='b'",
               "assert top_category([])==None", "assert top_category(None)==None",
               "assert top_category([{'category':'x','amount':2.0},{'category':'x','amount':3.0},{'category':'y','amount':4.0}])=='x'"]},
]
