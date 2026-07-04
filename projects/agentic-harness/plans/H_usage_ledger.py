# H_usage_ledger — persona redesign STAGE 1 (owner-greenlit, issue #9). The subsystem couldn't answer "which
# personas never fire?" or "each persona's hit-rate" — no usage tracking. This is the durable ledger spine:
# every invocation is recorded (persona, run, considered/fired, findings raised/confirmed, model) so later
# stages (explore/exploit, work-based grades) have real data. These PURE pieces shape + aggregate records;
# the append I/O to agents/usage.jsonl is thin CLI glue. Backwards-compatible: absent ledger -> today's behavior.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "usage_ledger"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "usage_record",
     "kinds": ["edge"],
     "prompt": ("Write usage_record(persona, run_id, considered, fired, raised, confirmed, model) -> dict, a "
                "normalized one-invocation usage record. Coerce: persona -> str(persona) if not None else ''; "
                "run_id -> str(run_id) if not None else ''; considered -> bool(considered); fired -> "
                "bool(fired); raised -> int(raised) if it is an int/float and >= 0 else 0; confirmed -> int("
                "confirmed) if it is an int/float and >= 0 else 0 — but confirmed is capped at raised (a "
                "persona can't confirm more findings than it raised: confirmed = min(confirmed, raised)); "
                "model -> str(model) if not None else ''. Return {'persona':..., 'run':..., 'considered':..., "
                "'fired':..., 'raised':..., 'confirmed':..., 'model':...}. Never raise; bools are not ints here "
                "(treat a bool passed as raised/confirmed as 0)." + "\n" + _ONLY),
     "tests": [
        "assert usage_record('sec', 'r1', True, True, 3, 2, 'fable') == {'persona':'sec','run':'r1','considered':True,'fired':True,'raised':3,'confirmed':2,'model':'fable'}",
        "assert usage_record('x', 'r', True, False, 0, 0, 'm')['fired'] is False",
        "assert usage_record('x', 'r', 1, 1, 5, 9, 'm')['confirmed'] == 5",
        "assert usage_record(None, None, True, True, -2, 1, None) == {'persona':'','run':'','considered':True,'fired':True,'raised':0,'confirmed':0,'model':''}",
        "assert usage_record('x','r',True,True, True, 1, 'm')['raised'] == 0",
        "assert usage_record('x','r',False,False,2,1,'m')['considered'] is False",
     ]},
    {"name": "parse_usage",
     "kinds": ["edge"],
     "prompt": ("Write parse_usage(text) -> list of dict records parsed from JSONL (one JSON object per line). "
                "Import json inside. text not a str -> []. Split on newlines; for each line strip it; skip empty "
                "lines; try json.loads(line) and keep the result only if it is a dict; skip any line that fails "
                "to parse or isn't a dict. Preserve order. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert parse_usage('{\"persona\": \"a\", \"fired\": true}\\n{\"persona\": \"b\", \"fired\": false}') == [{'persona':'a','fired':True},{'persona':'b','fired':False}]",
        "assert parse_usage('{\"a\":1}\\n\\nnot json\\n[1,2]\\n{\"b\":2}') == [{'a':1},{'b':2}]",
        "assert parse_usage('') == [] and parse_usage(None) == []",
        "assert parse_usage('   ') == []",
     ]},
    {"name": "never_fired",
     "kinds": ["edge"],
     "prompt": ("Write never_fired(records, all_names) -> sorted list of names in `all_names` that NEVER appear "
                "with fired == True in `records`. records is a list of dicts (each may have 'persona' and "
                "'fired'); build the set of personas that fired at least once (a record counts as fired iff "
                "record.get('fired') is truthy). all_names is an iterable of persona-name strings. Return "
                "sorted([n for n in all_names if isinstance(n, str) and n not in fired_set]). records/all_names "
                "not iterable -> treat as empty. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert never_fired([{'persona':'a','fired':True},{'persona':'b','fired':False}], ['a','b','c']) == ['b','c']",
        "assert never_fired([], ['x','y']) == ['x','y']",
        "assert never_fired([{'persona':'a','fired':True}], []) == []",
        "assert never_fired(None, ['a']) == ['a']",
        "assert never_fired([{'persona':'a','fired':True}], ['a']) == []",
        "assert never_fired([{'persona':'z','fired':True}], ['a','z','m']) == ['a','m']",
     ]},
    {"name": "persona_stats",
     "kinds": ["edge"],
     "prompt": ("Write persona_stats(records, persona) -> dict {'considered':int, 'fired':int, 'raised':int, "
                "'confirmed':int, 'hit_rate':float}. Aggregate all records whose 'persona' == persona: count "
                "considered (record.get('considered') truthy), fired (record.get('fired') truthy), sum raised "
                "(int of record.get('raised',0) when it's a number, else 0), sum confirmed (same). hit_rate = "
                "confirmed / raised if raised > 0 else 0.0 (a float). records not a list -> all zeros. Never "
                "raise." + "\n" + _ONLY),
     "tests": [
        "R = [{'persona':'a','considered':True,'fired':True,'raised':4,'confirmed':2},{'persona':'a','considered':True,'fired':False,'raised':0,'confirmed':0},{'persona':'b','considered':True,'fired':True,'raised':1,'confirmed':1}]",
        "assert persona_stats(R, 'a') == {'considered':2,'fired':1,'raised':4,'confirmed':2,'hit_rate':0.5}",
        "assert persona_stats(R, 'b')['hit_rate'] == 1.0",
        "assert persona_stats(R, 'zzz') == {'considered':0,'fired':0,'raised':0,'confirmed':0,'hit_rate':0.0}",
        "assert persona_stats('nope', 'a')['raised'] == 0",
        "assert persona_stats([{'persona':'a','considered':True,'fired':True,'raised':0,'confirmed':0}], 'a')['hit_rate'] == 0.0",
     ]},
]

CRITERIA = [
    {"id": "U1", "text": "Normalize a single persona invocation into a durable usage record (confirmed<=raised)",
     "tests": ["usage_record"]},
    {"id": "U2", "text": "Parse a JSONL usage ledger tolerantly (skip malformed lines)", "tests": ["parse_usage"]},
    {"id": "U3", "text": "Answer which personas never fired (the never-used tail)", "tests": ["never_fired"]},
    {"id": "U4", "text": "Aggregate a persona's considered/fired counts and confirmed-finding hit-rate",
     "tests": ["persona_stats"]},
]
