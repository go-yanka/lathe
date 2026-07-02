# lathe-generated module — do not edit by hand


def detect_kinds(tests):
    try:
        if not tests or not isinstance(tests, list):
            return set()
        import re
        strs = [t for t in tests if isinstance(t, str)]
        blob = "\n".join(strs).lower()
        kinds = set()
        for t in strs:
            tl = t.lower()
            if 'for ' in tl and ('in range' in tl or 'in [' in tl or 'assert all(' in tl or 'hypothesis' in tl):
                kinds.add('property')
            if '==' in tl:
                before = tl.split('==', 1)[0]
                if len(re.findall(r'[a-z_][a-z0-9_]*\(', before)) >= 2:
                    kinds.add('roundtrip')
            if 'assert' in tl:
                kinds.add('example')
        pairs = [('encode', 'decode'), ('dumps', 'loads'), ('parse', 'format'),
                 ('serialize', 'deserialize'), ('to_', 'from_')]
        if any(a in blob and b in blob for a, b in pairs):
            kinds.add('roundtrip')
        if any(m in blob for m in ['== 0', '== -', "'' ", '[]', '{}', 'none', 'empty', ' -1']):
            kinds.add('edge')
        if any(m in blob for m in ['raises', 'pytest.raises', 'try:', 'except', 'error', 'invalid']):
            kinds.add('error')
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
        present_norm = set()
        if present:
            try:
                for p in present:
                    if isinstance(p, str):
                        present_norm.add(p.strip().lower())
            except Exception:
                present_norm = set()
        problems = []
        for kind in required:
            if not isinstance(kind, str):
                continue
            k = kind.strip()
            if not k:
                continue
            if k.lower() not in present_norm:
                problems.append("missing required test kind: '%s'" % k)
        return problems
    except Exception:
        return []

