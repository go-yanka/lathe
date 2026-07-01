# lathe-generated module — do not edit by hand
_QUALITY_SCORES = {0: 0.0, 1: 0.33, 2: 0.67, 3: 1.0}


def summarize_gate_counts(report: dict) -> dict:
    gates = report.get('gates', [])
    passed = 0
    failed = 0
    for gate in gates:
        if gate.get('passed', False):
            passed += 1
        else:
            failed += 1
    return {
        'passed': passed,
        'failed': failed,
        'total': passed + failed
    }

def format_build_status(report: dict) -> str:
    if report.get('passed') is True:
        return 'PASS'
    else:
        return 'FAIL'

def render_transcript_steps(steps: list) -> str:
    return '\n'.join(steps)

def score_spec_quality(spec: dict) -> float:
    required_keys = ['name', 'description', 'functions']
    count = sum(1 for key in required_keys if key in spec)
    return _QUALITY_SCORES[count]

def flag_oversized_plan(spec: dict, max_funcs: int = 50) -> bool:
    return len(spec.get('functions', [])) > max_funcs

