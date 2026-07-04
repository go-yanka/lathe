# lathe-generated module — do not edit by hand


def needs_adversarial(kinds, plan_name, policy):
    if policy == 'off':
        return False
    if policy == 'all':
        return True
    if not isinstance(kinds, list):
        kinds = []
    if not isinstance(plan_name, str):
        plan_name = ''
    name = plan_name.lower()
    return 'gate' in kinds or any(k in name for k in ('gate', 'valid', 'strict', 'guard'))

def admit_cases(cases, example_tests, min_cases):
    if not isinstance(cases, list):
        cases = []
    if not isinstance(example_tests, list):
        example_tests = []
    try:
        n = int(min_cases)
        if isinstance(min_cases, bool) or n < 1:
            n = 1
    except Exception:
        n = 1
    def norm(s):
        return ''.join(s.split())
    seen = set(norm(t) for t in example_tests if isinstance(t, str))
    kept = []
    for c in cases:
        if not isinstance(c, str):
            continue
        if not c.strip():
            continue
        if not c.lstrip().startswith('assert'):
            continue
        if norm(c) in seen:
            continue
        kept.append(c)
        seen.add(norm(c))
    if len(kept) >= n:
        return (kept, '')
    return ([], 'REFUSED: %d admissible adversarial case(s), need %d' % (len(kept), n))

def adv_verdict(ran, failures, admitted):
    def _coerce(v):
        try:
            if isinstance(v, bool):
                return 0
            n = int(v)
            return n if n >= 0 else 0
        except Exception:
            return 0
    ran = _coerce(ran)
    failures = _coerce(failures)
    admitted = _coerce(admitted)
    if admitted <= 0:
        return (False, 'INOPERATIVE: no admissible adversarial cases were run')
    if ran < admitted:
        return (False, 'INOPERATIVE: %d of %d admitted case(s) did not run' % (admitted - ran, admitted))
    if failures > 0:
        return (False, 'FAIL: candidate broke on %d adversarial case(s)' % failures)
    return (True, 'PASS: survived %d adversarial case(s)' % ran)

