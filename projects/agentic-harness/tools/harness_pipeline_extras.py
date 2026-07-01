# lathe-generated module — do not edit by hand


def compute_attempt_efficiency(records):
    if not records:
        return 0.0
    total = len(records)
    first_attempt_success = sum(1 for r in records if r['attempt'] == 1 and r['passed'])
    return round(first_attempt_success / total, 4)

def detect_oscillating_function(results):
    if len(results) < 2:
        return False
    for i in range(1, len(results)):
        if results[i] == results[i - 1]:
            return False
    return True

def format_improvement_delta(before_pass, after_pass, total):
    delta = after_pass - before_pass
    abs_delta = abs(delta)
    
    if total > 0:
        pct = round(abs_delta / total * 100)
        pct_str = f'{pct}%'
    else:
        pct_str = 'n/a%'
    
    if delta > 0:
        return f'+{abs_delta} tests (+{pct_str})'
    elif delta < 0:
        return f'-{abs_delta} tests (-{pct_str})'
    else:
        return f'0 tests ({pct_str})'

def label_spec_priority(spec):
    fail_rate = spec.get('fail_rate', 0.0)
    complexity = spec.get('complexity', 0)
    if fail_rate >= 0.5 or complexity > 10:
        return 'high'
    if fail_rate >= 0.25:
        return 'medium'
    return 'low'

