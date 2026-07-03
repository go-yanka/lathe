# lathe-generated module — do not edit by hand


def equivalent_over_samples(code_a, code_b, name):
    try:
        ns_a = {'__builtins__': __builtins__}
        ns_b = {'__builtins__': __builtins__}
        try:
            exec(code_a, ns_a)
            exec(code_b, ns_b)
        except Exception:
            return False
        fa = ns_a.get(name)
        fb = ns_b.get(name)
        if not callable(fa) or not callable(fb):
            return False

        P = [-2, -1, 0, 1, 2, 10, -10, '', 'a', 'ab', None, True, False, [], [0, 1]]
        probes = [(x,) for x in P] + list(zip(P, reversed(P))) + [(0, 0), (1, 2), ('a', 'b'), (True, False)]

        def capture(f, args):
            try:
                return ('ok', f(*args))
            except Exception as e:
                return ('err', type(e).__name__)

        value_agreement = False
        for args in probes:
            ca = capture(fa, args)
            cb = capture(fb, args)
            if ca[0] == 'err' and cb[0] == 'err':
                if ca[1] != cb[1]:
                    return False
            elif ca[0] == 'ok' and cb[0] == 'ok':
                va, vb = ca[1], cb[1]
                try:
                    same = bool(va == vb)
                except Exception:
                    try:
                        same = repr(va) == repr(vb)
                    except Exception:
                        return False
                if not same:
                    return False
                value_agreement = True
            else:
                return False

        return value_agreement
    except Exception:
        return False

