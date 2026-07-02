# lathe-generated module — do not edit by hand


def equivalent_over_samples(code_a, code_b, name):
    try:
        def capture(f, args):
            try:
                return ('ok', repr(f(*args)))
            except Exception as e:
                return ('err', type(e).__name__)

        funcs = []
        for code in (code_a, code_b):
            ns = {'__builtins__': __builtins__}
            try:
                exec(code, ns)
            except Exception:
                return False
            f = ns.get(name)
            if not callable(f):
                return False
            funcs.append(f)
        fa, fb = funcs

        P = [-2, -1, 0, 1, 2, 10, -10, '', 'a', 'ab', None, True, False, [], [0, 1]]
        probes = [(x,) for x in P]
        probes += list(zip(P, reversed(P)))
        probes += [(0, 0), (1, 2), ('a', 'b'), (True, False)]

        comparable = False
        for args in probes:
            ca = capture(fa, args)
            cb = capture(fb, args)
            if ca != cb:
                return False
            if ca != ('err', 'TypeError'):
                comparable = True
        return comparable
    except Exception:
        return False

