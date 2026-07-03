# H_assumption_logic — the ASSUMPTION GATE spine. An LLM fills unstated requirements with silent guesses
# ("intent drift"); worse, when told "ask if unsure" it rates its own guesses as "common enough" and proceeds.
# So we DON'T trust self-report: an adversarial auditor persona re-reads the spec against the goal and emits a
# ranked ledger of decisions the goal never specified. These PURE pieces parse that ledger, rank by blast
# radius, and compute the UNCONFIRMED high-materiality blockers the gate refuses to build past.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "assumption_logic"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "parse_assumptions",
     "kinds": ["edge"],
     "prompt": ("Write parse_assumptions(text) -> list of dicts, each {'materiality': str, 'category': str, "
                "'text': str}. The auditor emits one assumption per line in the form "
                "'[ASSUMPTION | <materiality> | <category>] <the assumption text>' — the '|' separators and the "
                "<category> are the payload. Parse deterministically with the re module (import inside): "
                "(1) text not a str -> return []. "
                "(2) For each line: strip it; match a leading bracket group '[...]' whose FIRST '|'-separated "
                "token is the word 'assumption' (case-INSENSITIVE); if it doesn't match, skip the line. "
                "(3) Inside the bracket, split the payload on '|' and strip each piece; drop the leading "
                "'assumption' token. Of what remains: the 1st piece (if any) is the raw materiality, the 2nd (if "
                "any) is the category. "
                "(4) Normalize materiality (lowercase): if it starts with 'h' or 'crit' -> 'high'; if it starts "
                "with 'l' -> 'low'; if it starts with 'm' -> 'med'; OTHERWISE (empty, absent, or unrecognized) "
                "-> 'high'. This is FAIL-CLOSED: an assumption the auditor left unranked or garbled must SURFACE "
                "(block under default 'high' scrutiny), never hide as 'med'. "
                "(5) category = the 2nd piece lowercased if present and non-empty, else 'general'. "
                "(6) text = everything AFTER the closing ']', stripped. If that text is empty, skip the line. "
                "(7) Preserve order. Never raise; on error return []." + "\n" + _ONLY),
     "tests": [
        "assert parse_assumptions('[ASSUMPTION | high | behavior] First row is treated as a header.') == [{'materiality': 'high', 'category': 'behavior', 'text': 'First row is treated as a header.'}]",
        "r = parse_assumptions('prose line\\n[ASSUMPTION | low | scope] Only CSV is supported.\\nmore prose'); assert r == [{'materiality': 'low', 'category': 'scope', 'text': 'Only CSV is supported.'}]",
        "assert parse_assumptions('[assumption|HIGH|Data] Encoding is UTF-8.')[0]['materiality'] == 'high' and parse_assumptions('[assumption|HIGH|Data] Encoding is UTF-8.')[0]['category'] == 'data'",
        "assert parse_assumptions('[ASSUMPTION | critical | security] Auth is not required.')[0]['materiality'] == 'high'",
        "assert parse_assumptions('[ASSUMPTION | high] No category here.') == [{'materiality': 'high', 'category': 'general', 'text': 'No category here.'}]",
        "assert parse_assumptions('[ASSUMPTION | med | x] explicit med stays med.')[0]['materiality'] == 'med'",
        "assert parse_assumptions('[ASSUMPTION] bare tag defaults to high (fail-closed).')[0]['materiality'] == 'high'",
        "assert parse_assumptions('[ASSUMPTION | ??? | x] garbled materiality fails closed.')[0]['materiality'] == 'high'",
        "assert parse_assumptions(None) == [] and parse_assumptions('') == [] and parse_assumptions('no tags at all here') == []",
        "assert parse_assumptions('[ASSUMPTION | high | data]   ') == []",
     ]},
    {"name": "blocking_assumptions",
     "kinds": ["edge"],
     "prompt": ("Write blocking_assumptions(assumptions, policy) -> list. Given a list of assumption dicts (each "
                "with a 'materiality' key of 'high'/'med'/'low') and a user-governed scrutiny `policy` string, "
                "return the subset whose materiality meets the blocking threshold, preserving order. Resolve "
                "policy (lowercased, stripped): "
                "if it is one of 'off','none','advisory','0','false' -> NOTHING blocks, return []; "
                "elif it contains 'all' or 'low' -> threshold is every level (high, med, low); "
                "elif it contains 'med' (e.g. 'high+med' or 'med') -> threshold is high and med; "
                "else (default, including 'high' or None or unrecognized) -> threshold is high only. "
                "Items that are not dicts are skipped. For a dict, resolve its materiality: 'high'/'med'/'low' "
                "as-is; ANY other value (missing, empty, 'medium', 'critical', garbage) is treated as 'high' "
                "(FAIL-CLOSED — labeling drift must never silently disarm the gate). Then include the item iff "
                "its (resolved) materiality meets the threshold. assumptions not a list -> []. Never raise." + "\n" + _ONLY),
     "tests": [
        "A = [{'materiality': 'high', 'text': 'a'}, {'materiality': 'med', 'text': 'b'}, {'materiality': 'low', 'text': 'c'}]",
        "assert [x['text'] for x in blocking_assumptions(A, 'high')] == ['a']",
        "assert [x['text'] for x in blocking_assumptions(A, 'high+med')] == ['a', 'b']",
        "assert [x['text'] for x in blocking_assumptions(A, None)] == ['a']",
        "assert [x['text'] for x in blocking_assumptions(A, 'all')] == ['a', 'b', 'c']",
        "assert blocking_assumptions(A, 'off') == [] and blocking_assumptions(A, 'advisory') == []",
        "assert blocking_assumptions('nope', 'high') == [] and blocking_assumptions([], 'high') == []",
        "assert [x['text'] for x in blocking_assumptions([{'text': 'no materiality'}, {'materiality': 'high', 'text': 'a'}], 'high')] == ['no materiality', 'a']",
        "assert [x['text'] for x in blocking_assumptions([{'materiality': 'medium', 'text': 'x'}], 'high')] == ['x']",
        "assert [x['text'] for x in blocking_assumptions([{'materiality': 'critical', 'text': 'y'}], 'high')] == ['y']",
        "assert [x['text'] for x in blocking_assumptions(A, 'med')] == ['a', 'b']",
     ]},
    {"name": "unconfirmed_blockers",
     "kinds": ["edge"],
     "prompt": ("Write unconfirmed_blockers(assumptions, confirmed, policy) -> list. Compute the assumptions the "
                "gate must refuse to build past: the blocking-materiality assumptions (per the user-governed "
                "scrutiny `policy`, SAME resolution as blocking_assumptions: 'off'/'none'/'advisory'/'0'/'false' "
                "-> nothing blocks; 'all'/'low' in policy -> all levels; 'med' in policy -> high+med; else -> "
                "high only; AND materiality resolution is FAIL-CLOSED — any non-canonical materiality "
                "(missing/'medium'/'critical'/garbage) counts as 'high') whose text has NOT been confirmed by "
                "the user. `confirmed` is a list/set of confirmed "
                "assumption texts. Match by NORMALIZED text: lowercase + strip + collapse internal whitespace "
                "runs to one space (use the re module). Return the still-unconfirmed blockers in order. If a "
                "blocker's normalized text is in the normalized confirmed set, exclude it. assumptions not a list "
                "-> []; confirmed falsy/None -> treat as empty (so all blockers are returned). Never raise." + "\n" + _ONLY),
     "tests": [
        "A = [{'materiality': 'high', 'text': 'Encoding is UTF-8'}, {'materiality': 'high', 'text': 'First row is a header'}, {'materiality': 'low', 'text': 'x'}]",
        "assert [b['text'] for b in unconfirmed_blockers(A, [], 'high')] == ['Encoding is UTF-8', 'First row is a header']",
        "assert [b['text'] for b in unconfirmed_blockers(A, ['encoding  is   utf-8'], 'high')] == ['First row is a header']",
        "assert unconfirmed_blockers(A, ['Encoding is UTF-8', 'First row is a header'], 'high') == []",
        "assert unconfirmed_blockers(A, [], 'off') == [] and unconfirmed_blockers(A, [], 'advisory') == []",
        "assert [b['text'] for b in unconfirmed_blockers(A, [], 'all')] == ['Encoding is UTF-8', 'First row is a header', 'x']",
        "assert unconfirmed_blockers('nope', [], 'high') == []",
        "assert [b['text'] for b in unconfirmed_blockers([{'materiality':'med','text':'m'}], [], 'high+med')] == ['m']",
        "assert [b['text'] for b in unconfirmed_blockers([{'materiality':'medium','text':'d'}], [], 'high')] == ['d']",
        "assert [b['text'] for b in unconfirmed_blockers([{'text':'no-mat'}], [], 'high')] == ['no-mat']",
     ]},
    {"name": "spec_digest",
     "kinds": ["edge"],
     "prompt": ("Write spec_digest(functions) -> str, a stable hex digest binding an assumption ledger to the "
                "spec it was audited against, so a spec change invalidates stale confirmations. Use hashlib "
                "(import inside). Build a canonical representation: if functions is a list, for each item that "
                "is a dict collect the tuple (item.get('name',''), item.get('prompt',''), tuple(item.get("
                "'tests') or [])); items that are not dicts contribute ('', '', ()). If functions is not a "
                "list, use an empty list. repr() that list of tuples, encode utf-8, and return "
                "hashlib.sha256(...).hexdigest(). Deterministic for equal input; never raise (on error return "
                "hashlib.sha256(b'').hexdigest())." + "\n" + _ONLY),
     "tests": [
        "import hashlib",
        "d = spec_digest([{'name': 'f', 'prompt': 'p', 'tests': ['t']}]); assert isinstance(d, str) and len(d) == 64",
        "assert spec_digest([{'name': 'f', 'prompt': 'p', 'tests': ['t']}]) == spec_digest([{'name': 'f', 'prompt': 'p', 'tests': ['t']}])",
        "assert spec_digest([{'name': 'f', 'prompt': 'p', 'tests': ['t']}]) != spec_digest([{'name': 'f', 'prompt': 'CHANGED', 'tests': ['t']}])",
        "assert spec_digest([{'name': 'f', 'prompt': 'p', 'tests': ['t']}]) != spec_digest([{'name': 'f', 'prompt': 'p', 'tests': ['t', 'u']}])",
        "assert spec_digest('nope') == hashlib.sha256(repr([]).encode('utf-8')).hexdigest()",
        "assert spec_digest([]) == hashlib.sha256(repr([]).encode('utf-8')).hexdigest()",
        "assert isinstance(spec_digest([1, 'x', None]), str) and len(spec_digest([1, 'x', None])) == 64",
     ]},
]

# Requirement -> test traceability (consumed by `lathe trace`, enforced under LATHE_STRICT).
CRITERIA = [
    {"id": "A1", "text": "Parse the auditor's ranked assumption ledger into structured records",
     "tests": ["parse_assumptions"]},
    {"id": "A2", "text": "Select which assumptions are severe enough to block, per the configured policy",
     "tests": ["blocking_assumptions"]},
    {"id": "A3", "text": "Compute the unconfirmed high-materiality blockers the gate refuses to build past",
     "tests": ["unconfirmed_blockers"]},
    {"id": "A4", "text": "Bind a ledger to its spec so a spec change invalidates stale confirmations",
     "tests": ["spec_digest"]},
]
