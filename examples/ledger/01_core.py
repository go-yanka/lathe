# Ledger demo app — plan 1/3: parsing primitives. Later plans build on this module.
OUT_DIR = "examples/ledger"
MODULE_NAME = "ledger_core"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "parse_amount",
     "prompt": ("Write parse_amount(s) that parses a money string into a float. Handles a leading '$', thousands "
                "commas, optional leading '-', and surrounding whitespace. e.g. '$1,234.50'->1234.5, ' -3.00 '->-3.0, "
                "'12'->12.0. Empty or None -> 0.0. Never raise (on garbage return 0.0)." + "\n" + _ONLY),
     "tests": ["assert parse_amount('$1,234.50')==1234.5", "assert parse_amount(' -3.00 ')==-3.0",
               "assert parse_amount('12')==12.0", "assert parse_amount('')==0.0", "assert parse_amount(None)==0.0",
               "assert parse_amount('$0')==0.0", "assert parse_amount('nonsense')==0.0"]},
    {"name": "parse_entry",
     "prompt": ("Write parse_entry(line) that parses a CSV line 'date,category,amount' into a dict "
                "{'date':str,'category':str,'amount':float}. Strip whitespace on each field; parse amount with the "
                "same rules as a money string (leading '$', commas). A line with fewer than 3 comma-separated fields "
                "-> None. Empty or None -> None. Never raise." + "\n" + _ONLY),
     "tests": ["assert parse_entry('2024-01-05, groceries, $45.20')=={'date':'2024-01-05','category':'groceries','amount':45.2}",
               "assert parse_entry('x,y')==None", "assert parse_entry('')==None", "assert parse_entry(None)==None",
               "assert parse_entry('2024-02-01,rent,1000')=={'date':'2024-02-01','category':'rent','amount':1000.0}"]},
]
