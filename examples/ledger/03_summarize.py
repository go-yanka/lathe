# Ledger demo app — plan 3/3: composition across modules + an INTEGRATION boundary test.
OUT_DIR = "examples/ledger"
MODULE_NAME = "ledger"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests."
FUNCTIONS = [
    {"name": "summarize",
     "prompt": ("Write summarize(lines) that takes a list of CSV strings 'date,category,amount'. INSIDE the function, "
                "do `from ledger_core import parse_entry` and `from ledger_stats import total, by_category, top_category`. "
                "Parse each line with parse_entry, drop any that parse to None, then return a dict "
                "{'total': total(entries), 'by_category': by_category(entries), 'top': top_category(entries)}. "
                "None or empty lines -> {'total':0.0,'by_category':{},'top':None}. Never raise." + "\n" + _ONLY),
     "tests": ["assert summarize(['2024-01-01,food,$10','2024-01-02,food,$5','2024-01-03,rent,$100'])=={'total':115.0,'by_category':{'food':15.0,'rent':100.0},'top':'rent'}",
               "assert summarize([])=={'total':0.0,'by_category':{},'top':None}",
               "assert summarize(None)=={'total':0.0,'by_category':{},'top':None}",
               "assert summarize(['garbage line'])=={'total':0.0,'by_category':{},'top':None}"]},
]
