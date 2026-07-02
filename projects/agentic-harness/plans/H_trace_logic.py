# H_trace_logic — enforcement mechanism #2 (requirement→test traceability): the pure matrix builder behind
# `lathe trace`. The VALIDATOR refuses a plan whose declared criterion is unmapped/dangling (closed-rule,
# in plan_validator.py — hand-hardened security infra, edited directly per policy); this module builds the
# criterion→test→pin→model MATRIX from already-validated data (the compliance artifact, strategy §6.1).
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "trace_logic"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "resolve_refs",
     "prompt": ("Write resolve_refs(refs, fn_tests) -> list. refs is a list of test-ref strings: 'fn' (all of "
                "that function's tests) or 'fn:idx'. fn_tests is a dict {fn_name: [test strings]}. Resolve each "
                "ref IN ORDER to pairs [fn_name, test_string]: a bare 'fn' expands to every test of fn in order; "
                "'fn:idx' picks that one (idx is a decimal string). Skip (silently) refs whose fn is missing, "
                "idx is non-numeric, or idx out of range. Duplicate resolved pairs keep only the first. "
                "None/empty refs or fn_tests -> []. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert resolve_refs(['f'], {'f': ['a', 'b']}) == [['f', 'a'], ['f', 'b']]",
        "assert resolve_refs(['f:1'], {'f': ['a', 'b']}) == [['f', 'b']]",
        "assert resolve_refs(['f', 'f:0'], {'f': ['a']}) == [['f', 'a']]",
        "assert resolve_refs(['g'], {'f': ['a']}) == []",
        "assert resolve_refs(['f:9'], {'f': ['a']}) == []",
        "assert resolve_refs(['f:x'], {'f': ['a']}) == []",
        "assert resolve_refs([], {'f': ['a']}) == []",
        "assert resolve_refs(None, {'f': ['a']}) == []",
        "assert resolve_refs(['f'], None) == []",
     ]},
    {"name": "trace_rows",
     "prompt": ("Write trace_rows(criteria, fn_tests, fn_pins) -> list. The requirement->test->pin->model "
                "traceability matrix. criteria is a list of dicts {'id','text','tests'(list of ref strings)}; "
                "fn_tests is {fn_name: [test strings]}; fn_pins is {fn_name: [pin_key_prefix(str), model(str)]}. "
                "For each criterion IN ORDER, resolve its refs exactly like this rule: a bare 'fn' ref expands to "
                "every test of fn in order, 'fn:idx' picks one, invalid refs are skipped, duplicate [fn,test] "
                "pairs keep the first. Emit one row per resolved pair: a dict {'criterion': id, 'text': text, "
                "'fn': fn, 'test': test_string, 'pin': fn_pins[fn][0] if fn in fn_pins else 'UNPINNED', "
                "'model': fn_pins[fn][1] if fn in fn_pins else '-'}. A criterion whose refs resolve to NOTHING "
                "still emits one row with fn='(unresolved)', test='-', pin='-', model='-'. None/empty criteria "
                "-> []. Never raise." + "\n" + _ONLY),
     "tests": [
        "r = trace_rows([{'id':'AC-1','text':'t','tests':['f']}], {'f':['a','b']}, {'f':['abc123','m1']}); assert len(r)==2 and r[0]=={'criterion':'AC-1','text':'t','fn':'f','test':'a','pin':'abc123','model':'m1'}",
        "r = trace_rows([{'id':'AC-1','text':'t','tests':['f:1']}], {'f':['a','b']}, {}); assert r==[{'criterion':'AC-1','text':'t','fn':'f','test':'b','pin':'UNPINNED','model':'-'}]",
        "r = trace_rows([{'id':'AC-2','text':'x','tests':['ghost']}], {'f':['a']}, {}); assert r==[{'criterion':'AC-2','text':'x','fn':'(unresolved)','test':'-','pin':'-','model':'-'}]",
        "assert trace_rows([], {'f':['a']}, {}) == []",
        "assert trace_rows(None, {}, {}) == []",
        "r = trace_rows([{'id':'A','text':'t','tests':['f','f:0']}], {'f':['a']}, {'f':['p','m']}); assert len(r)==1",
     ]},
]
