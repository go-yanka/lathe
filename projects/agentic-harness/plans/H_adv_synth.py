# H_adv_synth — issue #11 (owner-directed, coupled to #12 phase 4): adversarial test synthesis as a GATE.
# Every fail-open the external reviewer found was a harness-built module whose tests didn't cover the
# adversarial case — this makes the harness find that gap ITSELF before a module pins. The analyst (model)
# SYNTHESIZES bypass probes; these pinned pure functions make the GATE DECISIONS around that model output:
# (1) which plans/functions must face synthesis; (2) is the synthesized block even admissible (fail-closed:
# zero cases / duplicates of the example tests / non-assert lines are REFUSED — a lazy analyst cannot
# rubber-stamp); (3) the verdict from the probe run. Model text never decides — the rc/asserts decide.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "adv_synth"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "needs_adversarial",
     "kinds": ["edge"],
     "prompt": ("Write needs_adversarial(kinds, plan_name, policy) -> bool: must this function face "
                "adversarial test synthesis before pinning? policy is a str: 'off' -> always False; "
                "'all' -> always True; anything else (including None/non-str) is the default 'gates' "
                "policy -> True iff the function is gate-critical: kinds (a list; non-list -> []) contains "
                "'gate' OR the lowercased plan_name (str; non-str -> '') contains any of 'gate', 'valid', "
                "'strict', 'guard'. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert needs_adversarial(['edge'], 'H_glue_gate.py', 'gates') is True",
        "assert needs_adversarial(['gate'], 'H_anything.py', 'gates') is True",
        "assert needs_adversarial(['edge'], 'H_plan_validator.py', None) is True",
        "assert needs_adversarial(['edge'], 'H_usage_ledger.py', 'gates') is False",
        "assert needs_adversarial(['edge'], 'H_usage_ledger.py', 'all') is True",
        "assert needs_adversarial(['gate'], 'H_strict_mode.py', 'off') is False",
        "assert needs_adversarial(None, None, 'gates') is False",
     ]},
    {"name": "admit_cases",
     "kinds": ["edge"],
     "prompt": ("Write admit_cases(cases, example_tests, min_cases, fname) -> a tuple (kept, reason). Follow "
                "these steps EXACTLY, in order.\n"
                "STEP 1: if cases is not a list, set cases = []. If example_tests is not a list, set "
                "example_tests = []. Coerce fname = str(fname) if isinstance(fname, str) else ''.\n"
                "STEP 2: try n = int(min_cases); on ANY exception, or if isinstance(min_cases, bool), or if "
                "n < 1: n = 1.\n"
                "STEP 3: def norm(s): return ''.join(s.split()). Build seen = set(norm(t) for t in "
                "example_tests if isinstance(t, str)).\n"
                "STEP 4: kept = []. For each c in cases, in order: skip unless isinstance(c, str); skip "
                "unless c.strip() (non-empty); skip unless c.lstrip() starts with 'assert'; skip if norm(c) "
                "in seen (a copy of an example test, or a duplicate of an earlier kept case, is NOT a new "
                "probe); AND (the DISCRIMINATION check #20) if fname is non-empty, skip unless (fname + '(') "
                "is in c — a probe that never CALLS the function under test (e.g. 'assert True', 'assert "
                "1==1') cannot discriminate a broken impl and is REJECTED. Otherwise append c to kept AND "
                "add norm(c) to seen.\n"
                "STEP 5: if len(kept) >= n: return (kept, ''). Otherwise return ([], 'REFUSED: %d admissible "
                "adversarial case(s), need %d' % (len(kept), n)). Never raise." + "\n" + _ONLY),
     "tests": [
        "k, r = admit_cases(['assert f(1)==1', 'assert f(-1) is None'], ['assert f(0)==0'], 2, 'f')",
        "assert k == ['assert f(1)==1', 'assert f(-1) is None'] and r == ''",
        "k, r = admit_cases([], ['assert f(0)==0'], 1, 'f'); assert k == [] and 'REFUSED' in r  # zero cases = REFUSE",
        "k, r = admit_cases(['assert  f(0)==0'], ['assert f(0)==0'], 1, 'f'); assert k == [] and 'REFUSED' in r  # copy of an example test does not count",
        "assert admit_cases(['looks fine to me', 'assert f(2)==2'], [], 1, 'f') == (['assert f(2)==2'], '')  # prose dropped, real probe survives",
        "k, r = admit_cases(['assert True', 'assert 1==1', 'assert f(2)==2'], [], 1, 'f'); assert k == ['assert f(2)==2']  # #20: vacuous asserts that never call f are rejected",
        "k, r = admit_cases(['assert True  # not a real test'], [], 1, 'f'); assert k == [] and 'REFUSED' in r  # #20 kill-shot: the known-bad vacuous case is refused",
        "assert admit_cases(['assert f(3)==3', 'assert f(3) == 3'], [], 1, 'f') == (['assert f(3)==3'], '')  # dupes collapse to one",
        "assert admit_cases(['assert g(1)==1', 'assert f(1)==1'], [], 1, '') == (['assert g(1)==1', 'assert f(1)==1'], '')  # empty fname -> no discrimination filter (back-compat)",
        "k, r = admit_cases(None, None, 'x', None); assert k == [] and 'REFUSED' in r",
        "k, r = admit_cases(['assert g(9)==9'], ['assert f(0)==0'], -5, 'g'); assert k == ['assert g(9)==9'] and r == ''  # bad min -> 1",
     ]},
    {"name": "adv_verdict",
     "kinds": ["edge"],
     "prompt": ("Write adv_verdict(ran, failures, admitted) -> (ok, detail). The gate verdict AFTER running "
                "admitted adversarial cases against the candidate. Coerce ran/failures/admitted to int (bad/"
                "bool/negative -> 0). Rules, in order: admitted <= 0 -> (False, 'INOPERATIVE: no admissible "
                "adversarial cases were run'); ran < admitted -> (False, 'INOPERATIVE: %d of %d admitted "
                "case(s) did not run' % (admitted-ran, admitted)) — a probe that cannot run is NEVER a pass; "
                "failures > 0 -> (False, 'FAIL: candidate broke on %d adversarial case(s)' % failures); "
                "else -> (True, 'PASS: survived %d adversarial case(s)' % ran). Never raise." + "\n" + _ONLY),
     "tests": [
        "assert adv_verdict(6, 0, 6) == (True, 'PASS: survived 6 adversarial case(s)')",
        "ok, d = adv_verdict(6, 2, 6); assert ok is False and 'FAIL' in d and '2' in d",
        "ok, d = adv_verdict(0, 0, 0); assert ok is False and 'INOPERATIVE' in d  # nothing ran != pass",
        "ok, d = adv_verdict(4, 0, 6); assert ok is False and 'INOPERATIVE' in d and '2 of 6' in d  # unrun probes never pass",
        "ok, d = adv_verdict('x', None, True); assert ok is False and 'INOPERATIVE' in d  # garbage -> fail-closed",
     ]},
]

CRITERIA = [
    {"id": "A1", "text": "Gate-critical functions are selected for synthesis deterministically (policy off/gates/all) (#11 stage 1)",
     "tests": ["needs_adversarial"]},
    {"id": "A2", "text": "Synthesized cases are admitted fail-closed: zero/lazy/copied/prose output REFUSES (#11 stage 2, #7 zero-case symmetry)",
     "tests": ["admit_cases"]},
    {"id": "A3", "text": "Verdict is tri-state honest: unrun probes are INOPERATIVE, never a silent pass (#12 U1 direction)",
     "tests": ["adv_verdict"]},
]
