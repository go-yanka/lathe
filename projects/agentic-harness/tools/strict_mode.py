# lathe-generated module — do not edit by hand


def strict_defaults(env_value, existing):
    try:
        if not isinstance(env_value, str):
            return []
        if env_value.strip().lower() not in ('1', 'true', 'yes', 'on'):
            return []
        defaults = [
            ['LATHE_TEST_ACK', '1'],
            ['LATHE_REGRESSION_PROOF', '1'],
            ['LATHE_LINT_SPEC', 'block'],
            ['LATHE_MUTATION_SCORE', '0.5'],
            ['LATHE_GATE_GLUE', '1'],
        ]
        result = []
        for key, value in defaults:
            try:
                current = existing.get(key) if isinstance(existing, dict) else None
            except Exception:
                current = None
            if isinstance(current, str) and current.strip():
                continue
            result.append([key, value])
        return result
    except Exception:
        return []

def strict_plan_gaps(env_value, has_functions, criteria, has_artifacts):
    if not isinstance(env_value, str):
        return []
    if env_value.strip().lower() not in ('1', 'true', 'yes', 'on'):
        return []
    problems = []
    if has_functions and (criteria is None or criteria == []):
        problems.append('strict mode requires declared CRITERIA (requirement->test traceability) for every FUNCTIONS plan')
    if has_artifacts and not has_functions:
        problems.append('strict mode cannot gate an ARTIFACTS-only plan (artifact/glue coverage is not yet enforceable) - build it outside STRICT or add gated FUNCTIONS')
    return problems

