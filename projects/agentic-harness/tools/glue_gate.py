# lathe-generated module — do not edit by hand


def count_glue_lines(glue) -> int:
    if not isinstance(glue, str):
        return 0
    try:
        count = 0
        for line in glue.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                count += 1
        return count
    except Exception:
        return 0

def glue_gap(env_value, glue_lines, has_integration, threshold):
    try:
        if not isinstance(env_value, str):
            return [False, 'glue gate not required']
        if env_value.strip().lower() not in ('1', 'true', 'yes', 'on'):
            return [False, 'glue gate not required']
        if isinstance(glue_lines, bool) or not isinstance(glue_lines, int):
            return [False, 'glue is trivial - not gated']
        try:
            if glue_lines <= threshold:
                return [False, 'glue is trivial - not gated']
        except Exception:
            return [False, 'glue is trivial - not gated']
        if has_integration:
            return [False, 'glue exercised by INTEGRATION']
        return [True, 'REFUSED: %d lines of hand-written GLUE with no INTEGRATION test - the wiring is ungated; add an INTEGRATION block that imports the module and asserts its behavior' % glue_lines]
    except Exception:
        return [False, 'glue gate not required']

