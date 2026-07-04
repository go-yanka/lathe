# lathe-generated module — do not edit by hand


def resolve_thinking(flag, env_value, config_value):
    valid = ('casual', 'medium', 'high')
    for candidate in (flag, env_value, config_value):
        if isinstance(candidate, str):
            normalized = candidate.strip().lower()
            if normalized in valid:
                return normalized
    return 'medium'

def depth_env(level):
    table = {
        'casual': {'LATHE_TRIES': '1', 'LATHE_SELECT_N': '1', 'LATHE_ASSUMPTION_POLICY': 'off'},
        'medium': {'LATHE_TRIES': '3', 'LATHE_SELECT_N': '2', 'LATHE_ASSUMPTION_POLICY': 'high'},
        'high': {'LATHE_TRIES': '5', 'LATHE_SELECT_N': '4', 'LATHE_ASSUMPTION_POLICY': 'high+med'},
    }
    try:
        row = table.get(level, table['medium'])
    except Exception:
        row = table['medium']
    return dict(row)

def contract_of(cmd, contracts):
    if not isinstance(contracts, dict):
        return {}
    if not isinstance(cmd, str):
        return {}
    value = contracts.get(cmd)
    if isinstance(value, dict):
        return dict(value)
    return {}

