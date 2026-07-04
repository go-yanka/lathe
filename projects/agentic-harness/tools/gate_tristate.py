# lathe-generated module — do not edit by hand


def classify_gate(raw, errored):
    try:
        if errored:
            return 'inoperative'
        if raw is None:
            return 'inoperative'
        if raw:
            return 'pass'
        return 'fail'
    except Exception:
        return 'inoperative'

def canary_trustworthy(pos_passed, neg_passed) -> bool:
    try:
        return (pos_passed is True) and (neg_passed is False)
    except Exception:
        return False

def gate_blocks(verdict, strict):
    try:
        v = verdict.strip().lower() if isinstance(verdict, str) else ''
    except Exception:
        v = ''
    if v == 'pass':
        return False
    if v == 'fail':
        return True
    return bool(strict)

