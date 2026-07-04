# H_gate_tristate — operating contract Phase 2b / U1 (reviewer's headline structural finding): gates must
# return a TRI-STATE {pass, fail, inoperative}, never a bare bool that fails OPEN on its own error. Today a
# gate whose probe throws (sandbox import fail, timeout, OOM) does `except: return False`-as-pass, so a gate
# that CANNOT RUN reports green. This module is the pinned DECISION core: (1) normalize a gate's outcome to a
# tri-state that maps an internal error to INOPERATIVE (not pass); (2) a CANARY check — a probe is only
# trustworthy if a known-good control passes AND a known-bad control is caught; (3) the blocking policy —
# STRICT-only rollout (owner decision): INOPERATIVE blocks only under STRICT; non-strict keeps today.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "gate_tristate"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "classify_gate",
     "kinds": ["edge"],
     "prompt": ("Write classify_gate(raw, errored) -> one of the strings 'pass', 'fail', 'inoperative'. This "
                "normalizes a gate probe's outcome. Rules IN ORDER: if errored is truthy -> 'inoperative' "
                "(the probe threw / could not run — NEVER silently a pass). Else if raw is None -> "
                "'inoperative' (indeterminate). Else if raw is truthy -> 'pass'. Else -> 'fail'. Note a "
                "bool raw is fine (True->pass, False->fail). Never raise." + "\n" + _ONLY),
     "tests": [
        "assert classify_gate(True, False) == 'pass'",
        "assert classify_gate(False, False) == 'fail'",
        "assert classify_gate(True, True) == 'inoperative'   # an error trumps a truthy result",
        "assert classify_gate(None, False) == 'inoperative'",
        "assert classify_gate(None, True) == 'inoperative'",
        "assert classify_gate(1, 0) == 'pass' and classify_gate(0, 0) == 'fail'",
        "assert classify_gate('ok', False) == 'pass' and classify_gate('', False) == 'fail'",
     ]},
    {"name": "canary_trustworthy",
     "kinds": ["edge"],
     "prompt": ("Write canary_trustworthy(pos_passed, neg_passed) -> bool. Before a gate judges the real "
                "subject it runs two controls: a POSITIVE control (a known-GOOD input that MUST pass the "
                "gate) and a NEGATIVE control (a known-BAD input the gate MUST catch, i.e. must NOT pass). "
                "The gate's probe is trustworthy ONLY if pos_passed is exactly True AND neg_passed is "
                "exactly False. Any other combination (positive control failed, or negative control slipped "
                "through, or either is a non-bool like None) -> False (the probe is miscalibrated -> caller "
                "treats the gate as inoperative). Never raise." + "\n" + _ONLY),
     "tests": [
        "assert canary_trustworthy(True, False) is True   # good passes, bad caught -> trustworthy",
        "assert canary_trustworthy(False, False) is False  # good control wrongly failed",
        "assert canary_trustworthy(True, True) is False    # bad control slipped through (fail-open probe)",
        "assert canary_trustworthy(False, True) is False",
        "assert canary_trustworthy(None, False) is False and canary_trustworthy(True, None) is False",
        "assert canary_trustworthy(1, 0) is False   # non-bool is not trusted (strict identity)",
     ]},
    {"name": "gate_blocks",
     "kinds": ["edge", "property"],
     "prompt": ("Write gate_blocks(verdict, strict) -> bool: does this tri-state gate verdict BLOCK the "
                "build? verdict is coerced to a lowercased stripped str (non-str -> ''). Rules: 'pass' -> "
                "False (never blocks). 'fail' -> True (always blocks). 'inoperative' -> blocks ONLY under "
                "strict: return True if strict is truthy else False (STRICT-only rollout). ANY other/"
                "unknown verdict string -> fail-closed: True if strict else False (an unrecognized verdict "
                "is not a free pass under strict). Never raise." + "\n" + _ONLY),
     "tests": [
        "assert gate_blocks('pass', True) is False and gate_blocks('pass', False) is False",
        "assert gate_blocks('fail', False) is True and gate_blocks('fail', True) is True",
        "assert gate_blocks('inoperative', True) is True   # STRICT: a gate that can't run REFUSES",
        "assert gate_blocks('inoperative', False) is False  # non-strict keeps today's behavior",
        "assert gate_blocks('  INOPERATIVE  ', True) is True  # normalized",
        "assert gate_blocks('garbage', True) is True and gate_blocks('garbage', False) is False  # unknown fail-closed under strict",
        "assert gate_blocks(None, True) is True and gate_blocks(None, False) is False",
        "assert all(gate_blocks('fail', s) is True for s in [True, False, 1, 0])",
     ]},
]

CRITERIA = [
    {"id": "U1a", "text": "A gate that errored/indeterminate classifies as INOPERATIVE, never a silent pass (#12 U1)",
     "tests": ["classify_gate"]},
    {"id": "U1b", "text": "A gate probe is trusted only when its positive+negative canary controls both behave (#12 U1 canary pair)",
     "tests": ["canary_trustworthy"]},
    {"id": "U1c", "text": "Blocking policy: FAIL always blocks; INOPERATIVE blocks under STRICT only; unknown fails closed (owner: STRICT-first)",
     "tests": ["gate_blocks"]},
]
