import ast
import re

# Plans are DATA, not a program. The engine exec's them (the module, HEADER/GLUE/INTEGRATION, and each
# test string), so the validator is built on CLOSED rules, not denylists that an adversary can walk around:
#   1) top level is data-only (assignments + imports + a docstring);
#   2) IMPORTS are an ALLOWLIST — only pure-compute stdlib (re/json/math/...); everything else (io, http,
#      gzip, zipfile, tokenize, os, subprocess, ...) is rejected. A denylist of "dangerous modules" is
#      unbounded; inverting it closes the import-escape CLASS instead of chasing instances;
#   3) every EXEC'd value (HEADER/GLUE/INTEGRATION and each FUNCTIONS/ARTIFACTS field) must be a PURE
#      LITERAL — no dict()/f-string/"imp"+"ort", so the string the engine runs IS the string we scanned;
#   4) ALL dunder access is blocked (`__class__`, `__subclasses__`, `__globals__`, ...) — every Python
#      sandbox escape needs a dunder, and getattr/setattr (the string-indirection around the static check)
#      are blocked builtins. Builtins are a fixed finite set, so a denylist there is itself closed.
_ALLOWED_TOP = (ast.Assign, ast.AnnAssign, ast.ImportFrom, ast.Import)

# (2) ONLY these modules may be imported by plan code. Pure-compute stdlib with no file/network/exec reach.
_SAFE_MOD = {
    're', 'json', 'math', 'cmath', 'decimal', 'fractions', 'random', 'statistics', 'string', 'textwrap',
    'datetime', 'calendar', 'collections', 'itertools', 'functools', 'operator', 'heapq', 'bisect',
    'array', 'enum', 'dataclasses', 'typing', 'copy', 'numbers', 'abc', 'contextlib', 'hashlib', 'hmac',
    'secrets', 'base64', 'binascii', 'struct', 'uuid', 'unicodedata', 'difflib', 'pprint', 'warnings',
    'keyword', 'token', 'time', '__future__',
    # NOTE: 'types' is deliberately NOT here — types.CodeType + types.FunctionType hand-craft a function
    # from raw bytecode, a sandbox escape that needs no dunder. Keep it out of the allowlist.
}
# (4) Dangerous BUILTINS — no import needed to reach these, so they are blocked by name. Builtins are a
# fixed finite set, so this denylist is closed. getattr/setattr/delattr are here because they are the
# string-indirection that would dodge the static dunder check (getattr(x, "__class__")).
_DANGER_NAME = {'eval', 'exec', 'compile', '__import__', '__builtins__', 'getattr', 'setattr', 'delattr',
                'globals', 'locals', 'vars', 'open', 'input', 'breakpoint', 'memoryview', 'exit', 'quit',
                # operator.attrgetter('__class__')/methodcaller/itemgetter fetch attrs from a STRING at runtime,
                # which the static dunder check can't see — block them (also as `from operator import attrgetter`).
                'attrgetter', 'methodcaller', 'itemgetter'}
# Attribute-form of the rare-dangerous operations (defense in depth; the import allowlist already blocks
# the modules these live on). Common method names are deliberately absent to avoid false-rejecting tests.
_DANGER_ATTR = {'system', 'popen', 'rmtree', 'urlopen', 'spawn', 'spawnl', 'spawnv', 'fork',
                'write_text', 'write_bytes', 'rmdir', 'unlink', 'attrgetter', 'methodcaller', 'itemgetter'}


def _has_danger(src, allow_imports):
    """Walk AST. Reject any dunder name/attribute (the escape vector), dangerous builtins/attrs, and any
    import outside the safe allowlist (or any import at all if allow_imports is False). Unparseable ->
    dangerous. Returns True if dangerous."""
    if not src:
        return False
    try:
        t = ast.parse(src)
    except SyntaxError:
        return True
    for node in ast.walk(t):
        if isinstance(node, ast.ImportFrom):
            if not allow_imports or getattr(node, 'level', 0):          # no relative imports in a plan
                return True
            if (node.module or '').split('.')[0] not in _SAFE_MOD:
                return True
            # also inspect the IMPORTED SYMBOL (not just the module): `from operator import attrgetter as _x`
            # comes from a safe module but re-binds a dangerous name to an alias that dodges the Name/Attr checks.
            if any(a.name in _DANGER_NAME for a in node.names):
                return True
        elif isinstance(node, ast.Import):
            if not allow_imports:
                return True
            if any(a.name.split('.')[0] not in _SAFE_MOD for a in node.names):
                return True
        elif isinstance(node, ast.Name) and (node.id in _DANGER_NAME or node.id.startswith('__')):
            return True
        elif isinstance(node, ast.Attribute) and (node.attr in _DANGER_ATTR or node.attr.startswith('__')):
            return True
    return False


def _expr_safe(src):
    """A test string is a plain assert: NO imports and NO dangerous/dunder access."""
    return not _has_danger(src, allow_imports=False)


def _code_danger(src):
    """HEADER/GLUE/INTEGRATION/functional are exec'd; only safe-allowlist imports are allowed, and no
    dangerous builtins, attrs, or dunders."""
    return _has_danger(src, allow_imports=True)


def _is_pure_literal(node):
    """(3) True only for pure data: Constant, or List/Tuple/Set/Dict of pure literals (and +/- on a
    number). Rejects Call (dict(...)), Name, BinOp ("imp"+"ort"), JoinedStr (f-string), comprehensions,
    Attribute — anything whose runtime value differs from its source text, so a scanned string can't
    later become a different exec'd string."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(_is_pure_literal(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return all(k is not None and _is_pure_literal(k) and _is_pure_literal(v)
                   for k, v in zip(node.keys, node.values))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub, ast.Invert)):
        return _is_pure_literal(node.operand)
    return False


def _collect_strs(list_node, key):
    """list_node is a pure-literal List of literal Dicts (guaranteed by the caller). Pull the string
    value(s) for `key` from each dict."""
    out = []
    if isinstance(list_node, ast.List):
        for el in list_node.elts:
            if isinstance(el, ast.Dict):
                for k, v in zip(el.keys, el.values):
                    if isinstance(k, ast.Constant) and k.value == key:
                        if key == 'tests' and isinstance(v, (ast.List, ast.Tuple, ast.Set)):
                            out += [t.value for t in v.elts if isinstance(t, ast.Constant) and isinstance(t.value, str)]
                        elif isinstance(v, ast.Constant) and isinstance(v.value, str):
                            out.append(v.value)
    return out


def is_valid_plan(text):
    if not isinstance(text, str) or text.strip() == '':
        return {'ok': False, 'reason': 'empty response'}
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return {'ok': False, 'reason': 'not valid Python: %s' % e}

    # Assignment TARGETS must be a single plain Name — never a Subscript/Attribute (`FUNCTIONS[0]["tests"]=...`,
    # which mutates an already-scanned literal) and never a Tuple/List unpack (`(a, ARTIFACTS) = ...`, which
    # binds the name to a value the per-key scans skip as None while the engine exec's the real runtime value).
    # Both are scan-then-swap RCEs. A data-only plan only ever needs `NAME = literal`.
    def _simple_target(t):
        return isinstance(t, ast.Name)

    for node in tree.body:                                    # 1) data-only top level
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if not isinstance(node, _ALLOWED_TOP):
            return {'ok': False, 'reason': 'plans must be data: disallowed top-level %s' % type(node).__name__}
        if isinstance(node, ast.Assign) and not all(_simple_target(t) for t in node.targets):
            return {'ok': False, 'reason': 'plans must be data: assignment target must be a single plain name (no tuple-unpack/subscript/attribute)'}
        if isinstance(node, ast.AnnAssign) and not _simple_target(node.target):
            return {'ok': False, 'reason': 'plans must be data: assignment target must be a single plain name'}

    if _has_danger(text, allow_imports=True):                 # 2) no dangerous code/import ANYWHERE in the plan AST
        return {'ok': False, 'reason': 'plan contains a dangerous expression or non-allowlisted import'}

    names = {}

    def _record(target, value):
        if isinstance(target, ast.Name):
            names[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            for el in target.elts:
                if isinstance(el, ast.Name):
                    names[el.id] = None       # OVERWRITE (not setdefault): a later tuple-unpack of a key first
                    #                           assigned a safe literal must invalidate it, else the validator scans
                    #                           the stale literal while the engine evaluates the tuple's real value.

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                _record(t, node.value)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            _record(node.target, node.value)

    if 'OUT_DIR' not in names or 'MODULE_NAME' not in names:
        return {'ok': False, 'reason': 'missing OUT_DIR or MODULE_NAME assignment'}
    _mn = names.get('MODULE_NAME')                            # MODULE_NAME becomes a filename -> plain identifier
    if not (isinstance(_mn, ast.Constant) and isinstance(_mn.value, str) and re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', _mn.value)):
        return {'ok': False, 'reason': 'MODULE_NAME must be a simple identifier string'}
    _od = names.get('OUT_DIR')                                # OUT_DIR must be a literal string (engine/lathe enforce containment)
    if not (isinstance(_od, ast.Constant) and isinstance(_od.value, str)):
        return {'ok': False, 'reason': 'OUT_DIR must be a literal string'}

    def _nonempty_dicts(node):                                # 3) FUNCTIONS/ARTIFACTS: non-empty list of literal dicts
        return (isinstance(node, ast.List) and bool(node.elts)
                and all(isinstance(el, ast.Dict) for el in node.elts))

    # The EXEC'd fields must be pure literals so the scanned string IS the exec'd string. prompt/name/path
    # are sent to the model / used as identifiers (containment-checked elsewhere), never exec'd, so they may
    # be computed (e.g. a shared "_ONLY" suffix concatenated onto a prompt).
    # functional_ref is NOT exec'd (a lookup key into the TRUSTED tools/func_gates.py registry) but is held
    # to the same literal rule so the scanned value IS the resolved value (no computed-key indirection).
    _EXEC_FIELDS = ('tests', 'functional', 'skeleton', 'glue', 'header', 'integration', 'functional_ref')

    def _str_const(n):
        return isinstance(n, ast.Constant) and isinstance(n.value, str)

    def _exec_fields_literal(node):
        if not isinstance(node, ast.List):
            return True
        for el in node.elts:
            if not isinstance(el, ast.Dict):                  # a dict(...) Call etc. would dodge the field scan
                return False
            for k, v in zip(el.keys, el.values):
                if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
                    return False                              # computed keys would hide an exec'd field
                if k.value not in _EXEC_FIELDS:
                    continue
                # exec'd fields must be STRING literals — not just any literal. `exec` accepts bytes, so a
                # Constant(bytes) test/field would run while _collect_strs (isinstance str) silently skips it.
                if k.value == 'tests':
                    if not (isinstance(v, (ast.List, ast.Tuple, ast.Set)) and all(_str_const(e) for e in v.elts)):
                        return False
                elif not _str_const(v):
                    return False
        return True

    f_ok = 'FUNCTIONS' in names and _nonempty_dicts(names['FUNCTIONS'])
    a_ok = 'ARTIFACTS' in names and _nonempty_dicts(names['ARTIFACTS'])
    if not (f_ok or a_ok):
        return {'ok': False, 'reason': 'need a non-empty FUNCTIONS or ARTIFACTS list of dict literals'}
    for key in ('FUNCTIONS', 'ARTIFACTS'):                    # exec'd fields must be literal so scan == exec
        if key in names and names[key] is not None and not _exec_fields_literal(names[key]):
            return {'ok': False, 'reason': '%s exec field (tests/functional/skeleton/glue) must be a literal' % key}

    def _every_dict_has_tests(list_node):                     # no tests == no gate: an untested unit would auto-"pass"
        if not isinstance(list_node, ast.List):
            return True
        for el in list_node.elts:
            if isinstance(el, ast.Dict):
                tnode = next((v for k, v in zip(el.keys, el.values)
                              if isinstance(k, ast.Constant) and k.value == 'tests'), None)
                if not (isinstance(tnode, (ast.List, ast.Tuple, ast.Set)) and len(tnode.elts) > 0):
                    return False
        return True
    if 'FUNCTIONS' in names and names['FUNCTIONS'] is not None and not _every_dict_has_tests(names['FUNCTIONS']):
        return {'ok': False, 'reason': 'every FUNCTION needs a non-empty tests list (an untested unit would auto-pass the gate)'}

    def _names_are_identifiers(list_node):                    # `name` is consumed as a function name AND a glob key
        if not isinstance(list_node, ast.List):               # (_recent_fail_feedback) -> path-traversal/exfil sink. Pin it.
            return True
        for el in list_node.elts:
            if isinstance(el, ast.Dict):
                nnode = next((v for k, v in zip(el.keys, el.values)
                              if isinstance(k, ast.Constant) and k.value == 'name'), None)
                if not (isinstance(nnode, ast.Constant) and isinstance(nnode.value, str)
                        and re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', nnode.value)):
                    return False
        return True
    # FUNCTION names become Python def names AND glob keys in _recent_fail_feedback (a traversal/exfil sink),
    # so pin them to identifiers. ARTIFACTS are keyed by their (containment-checked) `path`, not `name` — and
    # legitimately use a free-form/empty name — so they are exempt here.
    if 'FUNCTIONS' in names and names['FUNCTIONS'] is not None and not _names_are_identifiers(names['FUNCTIONS']):
        return {'ok': False, 'reason': "every FUNCTION 'name' must be a simple identifier (it becomes a def name / file key)"}

    # #60 polyglot: a FUNCTIONS dict may declare lang="js" — its tests are JavaScript, not Python, so they
    # are held to a JS deny-list (no require/import/process/eval/fs/...) instead of the Python AST scan.
    _JS_DENY = ('require', 'import', 'process.', 'child_process', 'fs.', 'eval(', 'Function(',
                'fetch(', 'XMLHttpRequest', 'globalThis', '__proto__', 'constructor[', '`')

    def _dict_lang(el):
        ln = next((v for k, v in zip(el.keys, el.values)
                   if isinstance(k, ast.Constant) and k.value == 'lang'), None)
        return ln.value if (isinstance(ln, ast.Constant) and isinstance(ln.value, str)) else 'py'

    def _dict_tests(el):
        tn = next((v for k, v in zip(el.keys, el.values)
                   if isinstance(k, ast.Constant) and k.value == 'tests'), None)
        if isinstance(tn, (ast.List, ast.Tuple, ast.Set)):
            return [e.value for e in tn.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        return []

    if isinstance(names.get('FUNCTIONS'), ast.List):
        for el in names['FUNCTIONS'].elts:
            if not isinstance(el, ast.Dict):
                continue
            _lg = _dict_lang(el)
            if _lg not in ('py', 'js', 'javascript'):
                return {'ok': False, 'reason': "FUNCTION lang must be 'py' or 'js'"}
            if _lg in ('js', 'javascript'):
                for ts in _dict_tests(el):
                    if any(d in ts for d in _JS_DENY):
                        return {'ok': False, 'reason': 'unsafe JS test expression (require/import/process/eval/...)'}
            else:
                for ts in _dict_tests(el):
                    if not _expr_safe(ts):
                        return {'ok': False, 'reason': 'unsafe test expression (dunder/import/danger)'}
    for lst in (names.get('ARTIFACTS'),):                         # 4) artifact tests stay python (`content` asserts)
        for ts in _collect_strs(lst, 'tests'):
            if not _expr_safe(ts):
                return {'ok': False, 'reason': 'unsafe test expression (dunder/import/danger)'}
    for lst in (names.get('FUNCTIONS'), names.get('ARTIFACTS')):  # shared exec'd-field checks (both lists)
        for fn in _collect_strs(lst, 'functional') + _collect_strs(lst, 'glue'):
            if _code_danger(fn):
                return {'ok': False, 'reason': 'unsafe functional/glue (runs as code)'}
    # skeleton is EXEC'd only when the artifact is a .py (python scan). For CONTENT artifacts (html/js/...)
    # it is spliced file text — python ast.parse would auto-reject ALL of them — so hold it to a deny-list
    # of active/exfil primitives instead. (Backticks allowed: JS template literals are legitimate here;
    # 'import ' with the trailing space does NOT match CSS '!important'.)
    _SKEL_DENY = ('require(', 'child_process', 'fs.', 'eval(', 'Function(', 'fetch(', 'XMLHttpRequest',
                  'WebSocket', 'globalThis', '__proto__', 'constructor[', 'import(', 'import ')
    for fn in _collect_strs(names.get('FUNCTIONS'), 'skeleton'):
        if _code_danger(fn):
            return {'ok': False, 'reason': 'unsafe function skeleton (runs as code)'}
    if isinstance(names.get('ARTIFACTS'), ast.List):
        for el in names['ARTIFACTS'].elts:
            if not isinstance(el, ast.Dict):
                continue
            _kv = {k.value: v for k, v in zip(el.keys, el.values) if isinstance(k, ast.Constant)}
            _sk = _kv.get('skeleton')
            if not (isinstance(_sk, ast.Constant) and isinstance(_sk.value, str)):
                continue
            _pv = _kv.get('path')
            _p = _pv.value if (isinstance(_pv, ast.Constant) and isinstance(_pv.value, str)) else ''
            if _p.endswith('.py'):
                if _code_danger(_sk.value):
                    return {'ok': False, 'reason': 'unsafe .py artifact skeleton (runs as code)'}
            elif any(d in _sk.value for d in _SKEL_DENY):
                return {'ok': False, 'reason': 'unsafe content skeleton (eval/require/fetch/import denied)'}
            # CONTRACT-CONSISTENCY (v2.27.1 post-mortem): a skeleton artifact whose PROMPT orders whole-file
            # output ("whole file", "<!DOCTYPE"-first reply) is self-contradictory — the splice expects the
            # REGION only. This exact contradiction cost 9 wasted builds and a wrong verdict on the model.
            # Refuse it at validation instead of discovering it in the browser.
            _pr = _kv.get('prompt')
            if isinstance(_pr, ast.Constant) and isinstance(_pr.value, str):
                _plow = _pr.value.lower()
                if ('whole file' in _plow or 'whole completed file' in _plow or 'entire file' in _plow
                        or 'reply must be <!doctype' in _plow or 'must be <!doctype' in _plow):
                    return {'ok': False, 'reason': 'CONTRADICTORY spec: artifact has a skeleton (region fill) '
                                                   'but its prompt orders whole-file output'}
        for fr in _collect_strs(lst, 'functional_ref'):           # a registry KEY, not code — pin to identifier form
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', fr):
                return {'ok': False, 'reason': "functional_ref must be a simple identifier (a tools/func_gates.py key)"}
    for key in ('HEADER', 'GLUE', 'INTEGRATION'):                 # 5) top-level exec'd code blocks: literal + safe
        if key not in names:                                      # truly absent -> fine
            continue
        node = names[key]                                         # present-but-None means tuple-unpacked (`HEADER, _ = danger, 0`)
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):  # -> not a literal -> REJECT (don't skip the scan)
            return {'ok': False, 'reason': '%s must be a literal string (no tuple-unpack/concatenation/f-strings)' % key}
        if _code_danger(node.value):
            return {'ok': False, 'reason': '%s contains a disallowed operation (dunder/import/danger)' % key}

    # 6) TRACEABILITY (enforcement mechanism #2): if a plan declares acceptance CRITERIA, EVERY criterion
    #    must map to >=1 named, existing test — refs are 'fn_name' (all of that function's tests) or
    #    'fn_name:<idx>' (one assert). An unmapped/dangling criterion is a requirement nothing verifies,
    #    so the plan is REFUSED (closed-rule, same AST-literal discipline as everything above).
    if 'CRITERIA' in names and names['CRITERIA'] is not None:
        cnode = names['CRITERIA']
        if not isinstance(cnode, ast.List) or not cnode.elts:
            return {'ok': False, 'reason': 'CRITERIA must be a non-empty literal list of dicts'}
        # collect fn name -> test count from the FUNCTIONS AST (literals only — guaranteed above)
        _fn_tests = {}
        fl = names.get('FUNCTIONS')
        if isinstance(fl, ast.List):
            for el in fl.elts:
                if isinstance(el, ast.Dict):
                    _nm = next((v.value for k, v in zip(el.keys, el.values)
                                if isinstance(k, ast.Constant) and k.value == 'name'
                                and isinstance(v, ast.Constant) and isinstance(v.value, str)), None)
                    _tn = next((v for k, v in zip(el.keys, el.values)
                                if isinstance(k, ast.Constant) and k.value == 'tests'), None)
                    if _nm is not None and isinstance(_tn, (ast.List, ast.Tuple)):
                        _fn_tests[_nm] = len(_tn.elts)
        _seen_ids = set()
        for el in cnode.elts:
            if not isinstance(el, ast.Dict) or not _is_pure_literal(el):
                return {'ok': False, 'reason': 'each CRITERIA entry must be a pure-literal dict'}
            kv = {k.value: v for k, v in zip(el.keys, el.values) if isinstance(k, ast.Constant)}
            cid, ctext, ctests = kv.get('id'), kv.get('text'), kv.get('tests')
            if not (isinstance(cid, ast.Constant) and isinstance(cid.value, str)
                    and re.match(r'^[A-Za-z][A-Za-z0-9_.-]*$', cid.value)):
                return {'ok': False, 'reason': "each criterion needs a simple string 'id' (e.g. 'AC-1')"}
            if cid.value in _seen_ids:
                return {'ok': False, 'reason': "duplicate criterion id '%s'" % cid.value}
            _seen_ids.add(cid.value)
            if not (isinstance(ctext, ast.Constant) and isinstance(ctext.value, str) and ctext.value.strip()):
                return {'ok': False, 'reason': "criterion '%s' needs a non-empty 'text'" % cid.value}
            if not (isinstance(ctests, ast.List) and ctests.elts):
                return {'ok': False, 'reason': "criterion '%s' is UNMAPPED — it needs a non-empty 'tests' list "
                                               "(a requirement nothing verifies)" % cid.value}
            for t in ctests.elts:
                if not (isinstance(t, ast.Constant) and isinstance(t.value, str)):
                    return {'ok': False, 'reason': "criterion '%s': test refs must be literal strings" % cid.value}
                ref = t.value
                fn, _, idx = ref.partition(':')
                if fn not in _fn_tests:
                    return {'ok': False, 'reason': "criterion '%s' maps to unknown function '%s' (dangling ref)"
                                                   % (cid.value, fn)}
                if idx:
                    if not idx.isdigit() or int(idx) >= _fn_tests[fn]:
                        return {'ok': False, 'reason': "criterion '%s': test ref '%s' is out of range (%s has %d tests)"
                                                       % (cid.value, ref, fn, _fn_tests[fn])}
    return {'ok': True, 'reason': 'valid plan'}
