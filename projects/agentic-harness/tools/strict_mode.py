# lathe-generated module — do not edit by hand


def strict_clamp(env_value, existing):
    if not isinstance(env_value, str):
        return []
    if env_value.strip().lower() not in ('1', 'true', 'yes', 'on'):
        return []
    if not isinstance(existing, dict):
        existing = {}

    def get(key):
        v = existing.get(key)
        return v if isinstance(v, str) else None

    triples = []
    mode_keys = [
        ('LATHE_TEST_ACK', '1'),
        ('LATHE_REGRESSION_PROOF', '1'),
        ('LATHE_LINT_SPEC', 'block'),
        ('LATHE_GATE_GLUE', '1'),
        ('LATHE_TEST_KIND', '1'),
        ('LATHE_ASSUMPTION_GATE', '1'),
    ]
    for key, forced in mode_keys:
        configured = get(key)
        if configured != forced:
            triples.append([key, forced, configured])

    key = 'LATHE_MUTATION_SCORE'
    configured = get(key)
    needs_clamp = True
    if configured is not None:
        try:
            if float(configured) >= 0.5:
                needs_clamp = False
        except (ValueError, TypeError):
            pass
    if needs_clamp:
        triples.append([key, '0.5', configured])

    return triples

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
        ['LATHE_GATE_GLUE', '1'],
        ['LATHE_TEST_KIND', '1'],
        ['LATHE_ASSUMPTION_GATE', '1'],
    ]
    result = []
    for key, value in defaults:
        try:
            current = existing.get(key) if existing is not None else None
        except Exception:
            current = None
        if isinstance(current, str) and current != '':
            continue
        result.append([key, value])
    return result

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

