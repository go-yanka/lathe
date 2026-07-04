# H_regime — operating contract Phase 2b / H1 (reviewer's pin-trust finding): a pin created under a WEAKER
# past gate regime must NOT replay as PASS under a stricter one. The engine already RE-RUNS a pin's tests on
# replay (engine_v2.py ~:762), but "0 gate calls" was the hole — a pin minted before mutation-score existed,
# or under LINT_SPEC=warn, would be trusted wholesale. This module is the pinned DECISION core: represent the
# active gate regime as a comparable signature, and decide whether a pin's recorded regime COVERS (is at
# least as strict as) the current one. If not, the caller re-gates the pinned bytes instead of trusting them.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "regime"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "regime_signature",
     "kinds": ["edge"],
     "prompt": ("Write regime_signature(env) -> dict, the active gate regime distilled from an environment "
                "mapping. env is a dict-like (non-dict -> treat as {}). Read these keys (missing -> default): "
                "modes = for each of 'LATHE_TEST_ACK','LATHE_REGRESSION_PROOF','LATHE_GATE_GLUE',"
                "'LATHE_TEST_KIND','LATHE_ASSUMPTION_GATE','LATHE_ADV_SYNTH' -> True iff the value's stripped "
                "lowercased form is in ('1','true','yes','on') else False; 'LATHE_LINT_SPEC' -> its stripped "
                "lowercased str (default ''); and num = float(env.get('LATHE_MUTATION_SCORE') or 0) but 0.0 "
                "if unparseable. Return {'modes': {name:bool,...}, 'lint': <str>, 'mutation': <float>}. Never "
                "raise." + "\n" + _ONLY),
     "tests": [
        "s = regime_signature({'LATHE_TEST_ACK':'1','LATHE_MUTATION_SCORE':'0.5','LATHE_LINT_SPEC':'block'})",
        "assert s['modes']['LATHE_TEST_ACK'] is True and s['mutation']==0.5 and s['lint']=='block'",
        "assert regime_signature({})['modes']['LATHE_ADV_SYNTH'] is False and regime_signature({})['mutation']==0.0",
        "assert regime_signature({'LATHE_MUTATION_SCORE':'bad'})['mutation']==0.0",
        "assert regime_signature(None) == regime_signature({})",
        "assert regime_signature({'LATHE_TEST_KIND':'YES'})['modes']['LATHE_TEST_KIND'] is True",
        "assert regime_signature({'LATHE_LINT_SPEC':'  WARN '})['lint']=='warn'",
     ]},
    {"name": "regime_covers",
     "kinds": ["edge", "property"],
     "prompt": ("Write regime_covers(pinned, current) -> bool: does the PINNED regime signature prove the pin "
                "was verified at least as strictly as the CURRENT regime demands? Both are dicts shaped like "
                "regime_signature output; a non-dict -> treat as {'modes':{}, 'lint':'', 'mutation':0.0}. "
                "Rules — ALL must hold for True: (1) for every mode name that is True in current['modes'], "
                "pinned['modes'] must also have it True (a gate now required must have been on when pinned); "
                "modes True in pinned but not current are fine. (2) mutation: float(pinned.mutation) >= "
                "float(current.mutation) (the pin met at least today's floor). (3) lint: if current['lint'] "
                "== 'block' then pinned['lint'] must == 'block' (can't trust a warn-era pin under block). "
                "Any missing/garbled field is treated as its weakest value (mode absent -> False, mutation "
                "bad -> 0.0), so a malformed pinned regime does NOT cover a real current one. Never raise." + "\n" + _ONLY),
     "tests": [
        "R = lambda m,l,mut: {'modes':m,'lint':l,'mutation':mut}",
        "assert regime_covers(R({'LATHE_TEST_ACK':True},'block',0.5), R({'LATHE_TEST_ACK':True},'block',0.5)) is True",
        "assert regime_covers(R({'LATHE_TEST_ACK':True},'',0.0), R({},'',0.0)) is True  # extra PINNED modes are fine (current requires none)",
        "assert regime_covers(R({'LATHE_TEST_ACK':True},'',0.5), R({'LATHE_TEST_ACK':True,'LATHE_ADV_SYNTH':True},'',0.5)) is False  # adv now required, wasn't on at pin",
        "assert regime_covers(R({},'',0.1), R({},'',0.5)) is False  # pinned mutation below current floor",
        "assert regime_covers(R({},'',0.9), R({},'',0.5)) is True   # pinned stricter mutation covers",
        "assert regime_covers(R({},'warn',0.0), R({},'block',0.0)) is False  # warn-era pin can't cover block",
        "assert regime_covers(R({},'block',0.0), R({},'warn',0.0)) is True",
        "assert regime_covers('bad', R({'LATHE_TEST_ACK':True},'',0.0)) is False  # malformed pinned covers nothing required",
        "assert regime_covers('bad', 'bad') is True  # nothing required -> vacuously covered",
        "assert regime_covers(None, R({'LATHE_TEST_ACK':True},'block',0.5)) is False  # null pinned covers nothing real",
        "assert all(regime_covers(r, r) is True for r in [R({'LATHE_TEST_ACK':True},'block',0.5), R({},'',0.0), R({'LATHE_ADV_SYNTH':True},'warn',0.9)])  # property: every regime covers itself (reflexive)",
     ]},
]

CRITERIA = [
    {"id": "H1a", "text": "Distill the active gate regime into a comparable signature (#12 H1)",
     "tests": ["regime_signature"]},
    {"id": "H1b", "text": "A pin is honored only if its regime is at least as strict as the current one, else re-gate (#12 H1)",
     "tests": ["regime_covers"]},
]
