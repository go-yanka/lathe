# lathe-generated module — do not edit by hand


def extract_env_vars(code):
    import re
    if not isinstance(code, str):
        return []
    try:
        pattern = (
            r"os\.environ\.get\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"
            r"|os\.getenv\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"
            r"|os\.environ\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"
        )
        names = set()
        for match in re.finditer(pattern, code):
            for group in match.groups():
                if group:
                    names.add(group)
        return sorted(names)
    except Exception:
        return []

def env_drift(code_vars, registered, ignore):
    try:
        def to_set(x):
            if x is None:
                return set()
            try:
                return {i for i in x if isinstance(i, str)}
            except TypeError:
                return set()

        code = to_set(code_vars)
        reg = to_set(registered)
        ign = to_set(ignore)

        return {
            'undocumented': sorted(code - reg - ign),
            'unused': sorted(reg - code - ign),
        }
    except Exception:
        return {'undocumented': [], 'unused': []}

