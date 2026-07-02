# lathe-generated module — do not edit by hand


def tests_digest(functions) -> str:
    import hashlib
    try:
        if not functions:
            return hashlib.sha256(b"").hexdigest()
        parts = []
        for f in functions:
            try:
                name = f.get('name') or ''
                if not isinstance(name, str):
                    name = str(name)
                tests = f.get('tests') or []
                try:
                    tests = [t if isinstance(t, str) else str(t) for t in tests]
                except Exception:
                    tests = []
            except Exception:
                name, tests = '', []
            parts.append(name + chr(0) + chr(1).join(tests))
        canonical = chr(2).join(parts)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    except Exception:
        return hashlib.sha256(b"").hexdigest()

def ack_ok(env_value, acks, plan_name, digest):
    if not isinstance(env_value, str) or env_value.strip().lower() not in ('1', 'true', 'yes', 'on'):
        return [True, 'test-ack not required']
    if isinstance(acks, dict) and acks.get(plan_name) == digest:
        return [True, 'tests acknowledged']
    return [False, 'tests NOT acknowledged - run: lathe ack <plan>']

