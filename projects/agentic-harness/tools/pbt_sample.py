# lathe-generated module — do not edit by hand


def adversarial_strings():
    return ['', ' ', chr(9), 'a=1; b=2; import os', 'x = 1  # comment', '# just a comment',
            '   ' + chr(10) + '  ', 'def f():', 'a' + chr(10) + 'b', 'assert True  # not a real test',
            'a' + chr(0) + 'b', 'return None']

def sample_inputs(seed, n):
    import random
    try:
        seed = int(seed)
    except Exception:
        seed = 0
    try:
        n = int(n)
    except Exception:
        n = 1
    if n < 1:
        n = 1
    try:
        advs = adversarial_strings()
    except Exception:
        try:
            from pbt_sample import adversarial_strings as _a
            advs = _a()
        except Exception:
            advs = []
    out = [(-2,), (-1,), (0,), (1,), (2,), (10,), (-10,), ('',), ('a',), (None,), (True,), (False,), ([],)]
    for s in advs:
        out.append((s,))
    rng = random.Random(seed)
    for _ in range(n):
        pick = rng.randint(0, 2)
        if pick == 0:
            out.append((rng.randint(-1000, 1000),))
        elif pick == 1:
            out.append((''.join(chr(rng.randint(97, 122)) for _ in range(rng.randint(0, 6))),))
        else:
            out.append((rng.uniform(-1000.0, 1000.0),))
    return out

