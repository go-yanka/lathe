# lathe-generated module — do not edit by hand

def _parse_test_count(text):
    words = text.lower().split()
    for i, word in enumerate(words):
        if word in ('test', 'tests') and i > 0:
            try:
                return int(words[i - 1])
            except ValueError:
                pass
    return 0


def compute_acceptance_verdict(report: dict) -> str:
    total = report['total']
    if total > 0 and report['pass'] == total:
        return 'ACCEPT'
    if report['fail'] > 0:
        return 'REJECT'
    return 'INDETERMINATE'

def extract_test_count_from_plan(plan_text: str) -> int:
    return _parse_test_count(plan_text)

def format_acceptance_report(verdict: str, report: dict) -> str:
    return f'verdict={verdict} pass={report["pass"]} fail={report["fail"]} total={report["total"]}'

def validate_function_spec(spec: dict) -> bool:
    # Condition 1: spec has a key 'functions'
    if 'functions' not in spec:
        return False
    
    functions = spec['functions']
    
    # Condition 2: spec['functions'] is a list
    if not isinstance(functions, list):
        return False
    
    # Condition 3: the list is non-empty
    if len(functions) == 0:
        return False
    
    # Condition 4: every item in the list is a non-empty string
    for item in functions:
        if not isinstance(item, str):
            return False
        if len(item) == 0:
            return False
    
    return True

