# lathe-generated module — do not edit by hand


def expand_words(s):
    import re
    if s is None or not isinstance(s, str) or not s.strip():
        return set()
    SYNONYM_CANON = {}
    for words, canon in [
        (['auth', 'authentication', 'authorization', 'authenticate', 'login', 'credential', 'credentials', 'oauth'], 'auth'),
        (['database', 'databases', 'db', 'sql', 'sqlite', 'postgres', 'mysql', 'query', 'queries'], 'database'),
        (['kubernetes', 'k8s'], 'kubernetes'),
        (['performance', 'perf', 'latency', 'speed', 'slow'], 'performance'),
        (['security', 'vulnerability', 'vulnerabilities', 'exploit', 'exploits', 'injection'], 'security'),
        (['test', 'tests', 'testing', 'qa', 'assert', 'asserts'], 'test'),
        (['frontend', 'ui', 'ux'], 'frontend'),
        (['api', 'endpoint', 'endpoints', 'rest'], 'api'),
        (['error', 'errors', 'exception', 'exceptions', 'failure', 'failures', 'bug', 'bugs'], 'error'),
        (['concurrency', 'async', 'asyncio', 'thread', 'threads', 'race'], 'concurrency'),
        (['deploy', 'deployment', 'deployments', 'release', 'releases'], 'deploy'),
        (['doc', 'docs', 'document', 'documents', 'documentation'], 'doc'),
    ]:
        for w in words:
            SYNONYM_CANON[w] = canon
    result = set()
    try:
        tokens = [t for t in re.split(r'[^a-z0-9]+', s.lower()) if t]
        for tok in tokens:
            if tok in SYNONYM_CANON:
                result.add(SYNONYM_CANON[tok])
                continue
            if len(tok) > 4 and tok.endswith('ies'):
                tok = tok[:-3] + 'y'
            elif len(tok) > 4 and tok.endswith('ing'):
                tok = tok[:-3]
            elif len(tok) > 3 and tok.endswith('ed'):
                tok = tok[:-2]
            elif len(tok) > 3 and tok.endswith('es'):
                tok = tok[:-2]
            elif len(tok) > 3 and tok.endswith('s'):
                tok = tok[:-1]
            result.add(tok)
    except Exception:
        pass
    return result

def score_match(need, capability):
    try:
        return len(expand_words(need) & expand_words(capability))
    except Exception:
        return 0

def license_ok(lic) -> bool:
    if not isinstance(lic, str):
        return False
    s = lic.strip().lower()
    return s.startswith(('mit', 'apache', 'bsd', 'isc', 'unlicense', 'cc0'))

def select_agents_for_goal(goal, entries, k):
    try:
        if not goal or not entries or k is None or k <= 0:
            return []
        goal_words = expand_words(goal)
        scored = []
        for idx, entry in enumerate(entries):
            try:
                name, capability = entry[0], entry[1]
                score = len(goal_words & expand_words(capability))
            except Exception:
                continue
            if score > 0:
                scored.append((-score, idx, name))
        scored.sort()
        return [name for _, _, name in scored[:k]]
    except Exception:
        return []

def pick_best(need, entries):
    try:
        need_words = expand_words(need)
        best_name = ''
        best_score = 0
        for entry in (entries or []):
            try:
                if entry is None:
                    continue
                name, capability = entry[0], entry[1]
                score = len(need_words & expand_words(capability))
                if score > best_score:
                    best_score = score
                    best_name = name if name is not None else ''
            except Exception:
                continue
        return best_name if best_score > 0 else ''
    except Exception:
        return ''

def spawn_candidates(names, entries):
    try:
        if not names or not entries:
            return []
        prefixes = ('mit', 'apache', 'bsd', 'isc', 'unlicense', 'cc0')
        lookup = {}
        for entry in entries:
            try:
                name, vendored, license_ = entry[0], entry[1], entry[2]
            except Exception:
                continue
            if name not in lookup:
                lookup[name] = (vendored, license_)
        result = []
        seen = set()
        for name in names:
            try:
                if name in seen or name not in lookup:
                    continue
                seen.add(name)
                vendored, license_ = lookup[name]
                if vendored:
                    continue
                if not isinstance(license_, str):
                    continue
                if license_.strip().lower().startswith(prefixes):
                    result.append(name)
            except Exception:
                continue
        return result
    except Exception:
        return []

