# lathe-generated module — do not edit by hand


def regime_signature(env) -> dict:
    try:
        if not isinstance(env, dict):
            try:
                env = dict(env)
            except Exception:
                env = {}
    except Exception:
        env = {}
    names = ('LATHE_TEST_ACK', 'LATHE_REGRESSION_PROOF', 'LATHE_GATE_GLUE',
             'LATHE_TEST_KIND', 'LATHE_ASSUMPTION_GATE', 'LATHE_ADV_SYNTH')
    modes = {}
    for name in names:
        try:
            modes[name] = str(env.get(name, '')).strip().lower() in ('1', 'true', 'yes', 'on')
        except Exception:
            modes[name] = False
    try:
        lint = str(env.get('LATHE_LINT_SPEC', '')).strip().lower()
    except Exception:
        lint = ''
    try:
        mutation = float(env.get('LATHE_MUTATION_SCORE') or 0)
    except Exception:
        mutation = 0.0
    return {'modes': modes, 'lint': lint, 'mutation': mutation}

def regime_covers(pinned, current):
    def normalize(sig):
        if not isinstance(sig, dict):
            sig = {}
        modes = sig.get('modes')
        if not isinstance(modes, dict):
            modes = {}
        clean_modes = {}
        for name, val in modes.items():
            clean_modes[name] = val is True
        lint = sig.get('lint')
        if not isinstance(lint, str):
            lint = ''
        mut = sig.get('mutation')
        try:
            mut = float(mut)
        except (TypeError, ValueError):
            mut = 0.0
        if mut != mut:
            mut = 0.0
        return clean_modes, lint, mut

    try:
        p_modes, p_lint, p_mut = normalize(pinned)
        c_modes, c_lint, c_mut = normalize(current)
        for name, required in c_modes.items():
            if required and not p_modes.get(name, False):
                return False
        if p_mut < c_mut:
            return False
        if c_lint == 'block' and p_lint != 'block':
            return False
        return True
    except Exception:
        return False

