# lathe-generated module — do not edit by hand


def parse_metrics_line(line: str) -> dict:
    """
    Parse a space-separated string of key=value tokens into a dictionary.
    
    Args:
        line (str): Input string containing key=value pairs separated by spaces
        
    Returns:
        dict: Dictionary mapping keys to values from valid key=value tokens
    """
    result = {}
    
    if not line:
        return result
        
    tokens = line.split()
    
    for token in tokens:
        if '=' in token:
            key, value = token.split('=', 1)
            result[key] = value
            
    return result

def format_build_status(report: dict) -> str:
    total = report.get('total', 0)
    if total == 0:
        return 'SKIP'
    if report.get('pass', 0) == total:
        return 'PASS'
    return 'FAIL'

def render_transcript_steps(steps: list) -> str:
    return '\n'.join(str(s['step']) + '. ' + s['status'] for s in steps)

def score_spec_quality(spec: dict) -> float:
    functions = spec.get('functions', [])
    if not functions:
        return 1.0
    tests = spec.get('tests', {})
    covered = sum(1 for f in functions if tests.get(f, 0) >= 1)
    return covered / len(functions)

def find_regressed_functions(before: dict, after: dict) -> list:
    result = [k for k in before if k in after and after[k] < before[k]]
    return sorted(result)

