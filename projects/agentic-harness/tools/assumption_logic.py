# lathe-generated module — do not edit by hand


def _dedup_assumptions(results):
    """Collapse near-duplicate assumptions (the analyst often emits the same choice several times under
    different materiality/category labels — the Advocate flagged 'speed listed 3-4x'). Keep the highest-
    materiality wording of each cluster. Token-overlap based; conservative so distinct choices survive."""
    import re as _re
    _rank = {"high": 2, "med": 1, "low": 0}
    _stop = {"the", "a", "an", "at", "of", "to", "in", "on", "per", "no", "not", "does", "do", "is", "are",
             "it", "its", "and", "or", "with", "without", "about", "around", "up", "then", "than", "as", "by",
             "for", "be", "so", "that", "this", "each", "any", "will", "would", "should", "rather", "instead",
             "moves", "move", "game", "player", "user", "default", "e.g", "eg", "etc"}

    def _toks(s):
        return {t for t in _re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split()
                if t and t not in _stop and len(t) > 1}
    kept = []
    for a in results:
        at = _toks(a.get("text", ""))
        if not at:
            kept.append(a); continue
        dup = -1
        for i, k in enumerate(kept):
            kt = _toks(k.get("text", ""))
            if not kt:
                continue
            inter = len(at & kt)
            jac = inter / (len(at | kt) or 1)
            contain = inter / (min(len(at), len(kt)) or 1)
            # merge when clearly the same choice reworded; category agreement lets a looser overlap count so
            # HIGH+MED near-duplicates of one choice collapse, while unrelated choices (near-zero overlap) never do.
            same_cat = (a.get("category") or "") == (k.get("category") or "") and inter >= 3
            if jac >= 0.55 or contain >= 0.8 or (same_cat and jac >= 0.4):
                dup = i; break
        if dup >= 0:
            if _rank.get(a.get("materiality"), 0) > _rank.get(kept[dup].get("materiality"), 0):
                kept[dup] = a                          # keep the higher-materiality copy, not a second row
        else:
            kept.append(a)
    return kept


def parse_assumptions(text):
    try:
        import re
        if not isinstance(text, str):
            return []
        results = []
        pattern = re.compile(r'^\[([^\]]*)\]\s*(.*)$')
        for line in text.splitlines():
            line = line.strip()
            m = pattern.match(line)
            if not m:
                continue
            pieces = [p.strip() for p in m.group(1).split('|')]
            if not pieces or pieces[0].lower() != 'assumption':
                continue
            rest = pieces[1:]
            raw_mat = rest[0] if len(rest) >= 1 else ''
            raw_cat = rest[1] if len(rest) >= 2 else ''
            mat_l = raw_mat.lower()
            if mat_l.startswith('h') or mat_l.startswith('crit'):
                materiality = 'high'
            elif mat_l.startswith('l'):
                materiality = 'low'
            elif mat_l.startswith('m'):
                materiality = 'med'
            else:
                materiality = 'high'
            category = raw_cat.lower() if raw_cat else 'general'
            body = m.group(2).strip()
            if not body:
                continue
            results.append({'materiality': materiality, 'category': category, 'text': body})
        return _dedup_assumptions(results)
    except Exception:
        return []

def blocking_assumptions(assumptions, policy):
    try:
        if not isinstance(assumptions, list):
            return []
        p = policy.strip().lower() if isinstance(policy, str) else ""
        if p in ('off', 'none', 'advisory', '0', 'false'):
            return []
        if 'all' in p or 'low' in p:
            allowed = {'high', 'med', 'low'}
        elif 'med' in p:
            allowed = {'high', 'med'}
        else:
            allowed = {'high'}
        out = []
        for item in assumptions:
            if not isinstance(item, dict):
                continue
            m = item.get('materiality')
            if m not in ('high', 'med', 'low'):
                m = 'high'
            if m in allowed:
                out.append(item)
        return out
    except Exception:
        return []

def unconfirmed_blockers(assumptions, confirmed, policy):
    import re

    def norm(s):
        try:
            return re.sub(r"\s+", " ", str(s).lower().strip())
        except Exception:
            return ""

    try:
        if not isinstance(assumptions, list):
            return []

        p = str(policy).lower().strip() if policy is not None else ""
        if p in ("off", "none", "advisory", "0", "false"):
            return []
        if "all" in p or "low" in p:
            levels = {"high", "med", "low"}
        elif "med" in p:
            levels = {"high", "med"}
        else:
            levels = {"high"}

        confirmed_norm = set()
        if confirmed:
            try:
                for c in confirmed:
                    confirmed_norm.add(norm(c))
            except Exception:
                pass

        out = []
        for a in assumptions:
            try:
                if isinstance(a, dict):
                    text = a.get("text", "")
                    mat = a.get("materiality")
                else:
                    text = a
                    mat = None
                m = str(mat).lower().strip() if mat is not None else ""
                if m not in ("high", "med", "low"):
                    m = "high"
                if m not in levels:
                    continue
                if norm(text) in confirmed_norm:
                    continue
                out.append(a)
            except Exception:
                continue
        return out
    except Exception:
        return []

def spec_digest(functions) -> str:
    import hashlib
    try:
        if not isinstance(functions, list):
            functions = []
        canonical = []
        for item in functions:
            if isinstance(item, dict):
                canonical.append((
                    item.get('name', ''),
                    item.get('prompt', ''),
                    tuple(item.get('tests') or []),
                ))
            else:
                canonical.append(('', '', ()))
        return hashlib.sha256(repr(canonical).encode('utf-8')).hexdigest()
    except Exception:
        return hashlib.sha256(b'').hexdigest()

