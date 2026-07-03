# lathe-generated module — do not edit by hand


def detect_kinds(tests):
    try:
        if not tests or not isinstance(tests, list):
            return set()

        def strip_comment(s):
            in_sq = False
            in_dq = False
            prev = ''
            for i, ch in enumerate(s):
                if ch == "'" and not in_dq and prev != '\\':
                    in_sq = not in_sq
                elif ch == '"' and not in_sq and prev != '\\':
                    in_dq = not in_dq
                elif ch == '#' and not in_sq and not in_dq:
                    return s[:i]
                prev = ch
            return s

        stripped = [strip_comment(t) for t in tests if isinstance(t, str)]
        lowered = [s.lower() for s in stripped]
        blob = '\n'.join(lowered)

        kinds = set()

        for s in lowered:
            if ('for ' in s and ('in range' in s or 'in [' in s
                                 or 'assert all(' in s or 'hypothesis' in s)) \
                    or 'sorted(' in s or 'reversed(' in s:
                kinds.add('property')
                break

        pairs = [('encode', 'decode'), ('dumps', 'loads'), ('parse', 'format'),
                 ('serialize', 'deserialize'), ('to_', 'from_')]
        if any(a in blob and b in blob for a, b in pairs):
            kinds.add('roundtrip')

        if any(m in blob for m in ['== 0', '== -', "'' ", '[]', '{}',
                                   'none', 'empty', ' -1']):
            kinds.add('edge')

        if any(m in blob for m in ['raises', 'pytest.raises', 'try:',
                                   'except', 'error', 'invalid']):
            kinds.add('error')

        if any('assert' in s for s in lowered):
            kinds.add('example')

        return kinds
    except Exception:
        return set()

def kind_gaps(env_value, required, present):
    try:
        if not isinstance(env_value, str):
            return []
        if env_value.strip().lower() not in ('1', 'true', 'yes', 'on'):
            return []
        if not required:
            return []
        try:
            present_set = {p.strip().lower() for p in (present or []) if isinstance(p, str)}
        except Exception:
            present_set = set()
        problems = []
        for kind in required:
            if not isinstance(kind, str):
                continue
            k = kind.strip()
            if not k:
                continue
            if k.lower() not in present_set:
                problems.append("missing required test kind: '%s'" % k)
        return problems
    except Exception:
        return []

