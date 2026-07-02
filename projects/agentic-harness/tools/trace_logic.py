# lathe-generated module — do not edit by hand


def resolve_refs(refs, fn_tests):
    try:
        if not refs or not fn_tests:
            return []
        out = []
        seen = set()

        def add(fn, test):
            key = (fn, test)
            if key not in seen:
                seen.add(key)
                out.append([fn, test])

        for ref in refs:
            try:
                if not isinstance(ref, str):
                    continue
                if ref in fn_tests:
                    tests = fn_tests[ref]
                    if tests:
                        for t in tests:
                            add(ref, t)
                    continue
                if ':' not in ref:
                    continue
                fn, idx_s = ref.rsplit(':', 1)
                if fn not in fn_tests:
                    continue
                if not idx_s.isdigit():
                    continue
                idx = int(idx_s)
                tests = fn_tests[fn]
                if tests is None or idx >= len(tests):
                    continue
                add(fn, tests[idx])
            except Exception:
                continue
        return out
    except Exception:
        return []

def trace_rows(criteria, fn_tests, fn_pins):
    rows = []
    try:
        if not criteria:
            return []
        fn_tests = fn_tests if isinstance(fn_tests, dict) else {}
        fn_pins = fn_pins if isinstance(fn_pins, dict) else {}
        for crit in criteria:
            try:
                if not isinstance(crit, dict):
                    continue
                cid = crit.get('id')
                text = crit.get('text')
                refs = crit.get('tests') or []
                if not isinstance(refs, (list, tuple)):
                    refs = []
                pairs = []
                seen = set()
                for ref in refs:
                    try:
                        if not isinstance(ref, str) or not ref.strip():
                            continue
                        ref = ref.strip()
                        if ':' in ref:
                            fn, _, idx_s = ref.rpartition(':')
                            fn = fn.strip()
                            tests = fn_tests.get(fn)
                            if not isinstance(tests, (list, tuple)):
                                continue
                            try:
                                idx = int(idx_s.strip())
                            except Exception:
                                continue
                            if idx < 0 or idx >= len(tests):
                                continue
                            candidates = [(fn, tests[idx])]
                        else:
                            tests = fn_tests.get(ref)
                            if not isinstance(tests, (list, tuple)):
                                continue
                            candidates = [(ref, t) for t in tests]
                        for fn, test in candidates:
                            key = (fn, test)
                            if key in seen:
                                continue
                            seen.add(key)
                            pairs.append((fn, test))
                    except Exception:
                        continue
                if not pairs:
                    rows.append({
                        'criterion': cid, 'text': text,
                        'fn': '(unresolved)', 'test': '-',
                        'pin': '-', 'model': '-',
                    })
                    continue
                for fn, test in pairs:
                    pin, model = 'UNPINNED', '-'
                    try:
                        if fn in fn_pins:
                            entry = fn_pins[fn]
                            pin, model = entry[0], entry[1]
                    except Exception:
                        pin, model = 'UNPINNED', '-'
                    rows.append({
                        'criterion': cid, 'text': text,
                        'fn': fn, 'test': test,
                        'pin': pin, 'model': model,
                    })
            except Exception:
                continue
    except Exception:
        return rows
    return rows

