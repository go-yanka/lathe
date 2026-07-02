# lathe-generated module — do not edit by hand


def strict_defaults(env_value, existing):
    if not isinstance(env_value, str):
        return []
    if env_value.strip().lower() not in ('1', 'true', 'yes', 'on'):
        return []
    defaults = [
        ['LATHE_TEST_ACK', '1'],
        ['LATHE_REGRESSION_PROOF', '1'],
        ['LATHE_LINT_SPEC', 'block'],
        ['LATHE_MUTATION_SCORE', '0.5'],
    ]
    result = []
    for key, value in defaults:
        try:
            current = existing.get(key) if existing else None
        except Exception:
            current = None
        if isinstance(current, str) and current.strip():
            continue
        result.append([key, value])
    return result

def strict_plan_gaps(env_value, has_functions, criteria):
    if not isinstance(env_value, str):
        return []
    if env_value.strip().lower() not in ('1', 'true', 'yes', 'on'):
        return []
    if has_functions and (criteria is None or criteria == []):
        return ['strict mode requires declared CRITERIA (requirement->test traceability) for every FUNCTIONS plan']
    return []

