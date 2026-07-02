#!/usr/bin/env python3
"""Reusable deterministic engine: reads a PLAN (Claude's handover) and drives a small
model to implement each function under best-of-N + test-gating. No LLM in the driver.

PLAN module must define:
  HEADER       : str  (imports prepended to assembled file)
  FUNCTIONS    : list of dicts {name, prompt, context?(str), tests:[assert-str,...]}
  GLUE         : str  (architect-written wiring + main, appended after functions)
  INTEGRATION  : str  (a python script that `import game` and asserts; exit 0 = pass)

Usage: python engine_v2.py <plan.py> [model] [N]
"""
import importlib.util, sys, json, re, time, os, tempfile, subprocess, urllib.request, random, math, datetime, html, sqlite3, hashlib, concurrent.futures
import xml.etree.ElementTree as ET
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

PLAN_PATH = sys.argv[1]
MODEL = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("HARNESS_MODEL", "gemma4:12b")
N = int(sys.argv[3]) if len(sys.argv) > 3 else 12

# structured per-run logging so a reported bug is self-diagnosing (best-effort — a logging failure must NEVER
# break a build). Appended to sys.path so it never shadows stdlib.
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "projects", "agentic-harness", "tools"))
from spine_helpers import resolve_out_dir, integration_label  # harness-built fix-logic (B1/B5)
try:
    import run_logger
except Exception:
    class run_logger:                      # no-op fallback: the engine runs even if the logger module is absent
        @staticmethod
        def new_run_id(): return ""
        @staticmethod
        def log(*a, **k): pass
        @staticmethod
        def rotate(*a, **k): pass
_RUN_ID = run_logger.new_run_id()
run_logger.log(_RUN_ID, "start", plan=os.path.basename(PLAN_PATH), model=MODEL, n=N)

# Read the plan source ONCE. The validator checks these exact bytes and the engine exec's these exact
# bytes — never two separate reads (a TOCTOU window where the file is swapped between validate and exec).
_plan_src = open(PLAN_PATH, encoding="utf-8").read()

# SECURITY: validate the plan as DATA before importing/exec'ing it. Gated by LATHE_VALIDATE_PLAN (the CLI
# and the autonomy loop set it) so every untrusted path is covered even on a direct `engine_v2.py <plan>`.
# LATHE_TRUST_PLAN=1 bypasses (trusted callers, e.g. the product harness).
if os.environ.get("LATHE_VALIDATE_PLAN") == "1" and os.environ.get("LATHE_TRUST_PLAN") != "1":
    # Resolve the validator ONLY from trusted infra (env override, or next to the engine). NEVER from a
    # PLAN_PATH-relative path: PLAN_PATH is attacker-influenced, so a `../tools/plan_validator.py` fallback
    # would let a hostile plan ship its own "validator" that rubber-stamps itself.
    _vp = os.environ.get("LATHE_VALIDATOR_PY") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "projects", "agentic-harness", "tools", "plan_validator.py")
    if not os.path.exists(_vp):
        sys.exit("engine: LATHE_VALIDATE_PLAN set but plan_validator.py not found — refusing (set LATHE_VALIDATOR_PY)")
    try:                              # FAIL CLOSED: any error running the validator refuses the plan, never lets it through
        _vs = importlib.util.spec_from_file_location("plan_validator", _vp)
        _vm = importlib.util.module_from_spec(_vs); _vs.loader.exec_module(_vm)
        _vv = _vm.is_valid_plan(_plan_src)              # validate the SAME bytes we will exec
    except SystemExit:
        raise
    except Exception as _ve:
        sys.exit("engine: plan validator failed to run (%s) — refusing to load plan" % _ve)
    if not _vv["ok"]:
        sys.exit("engine: REFUSING to load plan (%s) — set LATHE_TRUST_PLAN=1 for a trusted plan" % _vv["reason"])

_spec = importlib.util.spec_from_file_location("plan", PLAN_PATH)
plan = importlib.util.module_from_spec(_spec)
exec(compile(_plan_src, PLAN_PATH, "exec"), plan.__dict__)   # exec the validated bytes, not a fresh disk read (no TOCTOU)
sys.modules.setdefault("plan", plan)

if os.environ.get("LATHE_VALIDATE_PLAN") == "1" and os.environ.get("LATHE_TRUST_PLAN") != "1":
    # OUT_DIR is analyst/model-chosen; the engine WRITES module.py/itest.py/.pins.json there and RUNS
    # itest.py with cwd=OUT_DIR. Containment can't be a string check on the source (it's data) — enforce it
    # here on the engine itself, not only in lathe.py, so a direct `engine_v2.py <plan>` is covered too.
    _eroot = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
    _od = resolve_out_dir(getattr(plan, "OUT_DIR", ""), PLAN_PATH)   # B1: default to the plan's own dir, not a placeholder
    _eod = os.path.realpath(os.path.join(_eroot, _od))
    if not (_eod == _eroot or _eod.startswith(_eroot + os.sep)):
        sys.exit("engine: REFUSING to build — OUT_DIR escapes the working tree (%r). Set LATHE_TRUST_PLAN=1 to override."
                 % _od)

# Optional plan attrs: the validator accepts ARTIFACTS-only plans (no FUNCTIONS/HEADER/GLUE), so normalize
# defaults once here instead of `plan.FUNCTIONS` AttributeError-ing deep in the build.
for _attr, _dflt in (("FUNCTIONS", []), ("ARTIFACTS", []), ("HEADER", ""), ("GLUE", ""), ("INTEGRATION", "")):
    if not hasattr(plan, _attr) or getattr(plan, _attr) is None:
        setattr(plan, _attr, _dflt)

# STRICT MODE (LATHE_STRICT=1 — the SDLC enforcement umbrella): ALL development, new AND enhancement, is
# forced through every proof mechanism — tests acknowledged (TEST_ACK), changed code must ship a test that
# fails on the old implementation (REGRESSION_PROOF), new code must ship tests a trivial stub can't satisfy
# (LINT_SPEC=block), and the plan MUST declare CRITERIA (requirement→test traceability). The policy itself
# is harness-built + pinned (tools/strict_mode.py); an explicitly-set env var still wins over the umbrella.
try:
    _sm = importlib.util.spec_from_file_location("strict_mode", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "projects", "agentic-harness", "tools", "strict_mode.py"))
    _smm = importlib.util.module_from_spec(_sm); _sm.loader.exec_module(_smm)
    _strict = os.environ.get("LATHE_STRICT")
    for _k, _v in _smm.strict_defaults(_strict, dict(os.environ)):
        os.environ[_k] = _v
        print("engine: STRICT mode -> %s=%s" % (_k, _v))
    _gaps = _smm.strict_plan_gaps(_strict, bool(plan.FUNCTIONS), getattr(plan, "CRITERIA", None),
                                  bool(plan.ARTIFACTS))          # E3: ARTIFACTS-only plans are not gateable
    if _gaps:
        sys.exit("engine: STRICT MODE — " + "; ".join(_gaps) + " (plan: %s)" % os.path.basename(PLAN_PATH))
except SystemExit:
    raise
except Exception:
    pass                                 # policy module absent -> legacy behavior (strict is opt-in anyway)

# TEST-ACK GATE (review V4 §3 risk 1): the analyst's tests define truth but were the one ungated artifact —
# a misread goal becomes tests that certify the wrong behavior. Opt-in (LATHE_TEST_ACK=1): refuse to build
# until a human has acknowledged THIS exact test set (`lathe ack <plan>`); any test rewrite (incl. by the
# repair loop) changes the digest and forces a re-read. Decision logic is harness-built (tools/test_ack.py).
if plan.FUNCTIONS:
    try:
        _ta = importlib.util.spec_from_file_location("test_ack", os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "projects", "agentic-harness", "tools", "test_ack.py"))
        _tam = importlib.util.module_from_spec(_ta); _ta.loader.exec_module(_tam)
        _ack_file = os.path.join(os.path.dirname(os.path.abspath(PLAN_PATH)), ".test_ack.json")
        try:
            _acks = json.loads(open(_ack_file, encoding="utf-8").read())
        except Exception:
            _acks = {}
        _ok, _why = _tam.ack_ok(os.environ.get("LATHE_TEST_ACK"), _acks,
                                os.path.basename(PLAN_PATH), _tam.tests_digest(plan.FUNCTIONS))
        if not _ok:
            sys.exit("engine: TEST-ACK GATE — %s (plan: %s). The tests define what 'correct' means; read them "
                     "before the build certifies them." % (_why, os.path.basename(PLAN_PATH)))
    except SystemExit:
        raise
    except Exception:
        pass                             # gate module absent -> legacy behavior (gate is opt-in anyway)

# A plan must NEVER write over a file the engine didn't generate, nor shadow an importable module.
# MODULE_NAME is just an identifier, so without this MODULE_NAME="engine_v2" overwrites the engine, and
# MODULE_NAME="json" writes tools/json.py which (tools/ is on sys.path) shadows stdlib json -> RCE on next import.
_LATHE_MARK = "# lathe-generated module — do not edit by hand"
# A DISTINCT marker for .py artifacts: it grants overwrite-protection (rebuild-safe) but NOT prelude trust.
# PRELUDE execs files in the host process, so it must accept ONLY _LATHE_MARK (gated modules), never an
# artifact whose arbitrary model-written content was never AST-scanned. (marker = provenance, not safety.)
_LATHE_ARTIFACT_MARK = "# lathe-artifact — generated output, NOT a trusted prelude module"
_CORE_INFRA = {"engine_v2.py", "lathe.py", "hreview.py", "run_gates.py", "stale_gate.py", "plan_validator.py",
               "sandbox.py", "autonomy_live.py", "autonomy_loop.py", "self_feed_runner.py", "request_spec.py",
               "board.py", "dag.py", "__init__.py", ".pins.json", "conftest.py",
               "planner_prompt.py"}    # authored prompt template, hand-maintained — its origin plan T4 is retired; never let a rebuild overwrite it
_CORE_INFRA_LC = {x.lower() for x in _CORE_INFRA}               # Windows FS is case-insensitive: compare casefolded
_STDLIB = {m.lower() for m in getattr(sys, "stdlib_module_names", frozenset())}


def _name_collision(basename):
    """Reason string if writing `basename` would overwrite harness infra or shadow a stdlib module (so
    `import X` later loads the planted file because OUT_DIR is on sys.path). None if safe."""
    low = basename.lower()
    if low in _CORE_INFRA_LC:
        return "would overwrite harness infra"
    stem, ext = os.path.splitext(low)
    if ext == ".py" and stem in _STDLIB:
        return "shadows a stdlib module"
    return None


_mn = getattr(plan, "MODULE_NAME", "")
# DEFENSE-IN-DEPTH: MODULE_NAME becomes a filename. plan_validator already requires a bare identifier, but a
# LATHE_TRUST_PLAN=1 path skips the validator — so enforce it here too, else MODULE_NAME="../engine_v2" would
# traverse out of OUT_DIR and clobber the engine (same for the _itest_<name> path).
if _mn and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", _mn):
    sys.exit("engine: REFUSING to build — MODULE_NAME %r is not a bare identifier (path-traversal guard)" % _mn)
_coll = _name_collision(_mn + ".py")
if _coll:
    sys.exit("engine: REFUSING to build — MODULE_NAME %r %s" % (_mn, _coll))


def _refuse_if_foreign(path):
    """Refuse to overwrite a file the engine didn't generate (no Lathe marker) — covers every local infra
    module (dispatcher/driver/board/...) generally, not just a hand-maintained blocklist. Prior Lathe
    outputs carry the marker, so rebuilds are still allowed."""
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as _ef:
                _line1 = _ef.readline().strip()
            if _line1 not in (_LATHE_MARK, _LATHE_ARTIFACT_MARK):   # marker must be LINE 1 (content can't forge it)
                sys.exit("engine: REFUSING to overwrite non-Lathe file %r (no line-1 provenance marker)" % path)
        except OSError:
            pass


def _atomic_write(path, content):
    """Write via tmp+os.replace so a crash/power-loss mid-write can never leave a TRUNCATED file. A truncated
    file still carries the line-1 marker, so _refuse_if_foreign would trust it and the next build/PRELUDE would
    load half a module. .pins.json already does this; deliverables must too. os.replace is atomic on one volume."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as _f:
        _f.write(content)
        _f.flush()
        os.fsync(_f.fileno())
    os.replace(tmp, path)

tok = {"p": 0, "e": 0, "claude_calls": 0}
_MAX_RESP = int(os.environ.get("LATHE_MAX_RESP", str(16 * 1024 * 1024)))   # cap model responses (OOM guard)
CLAUDE_URL = os.environ.get("HARNESS_CLAUDE_URL", "http://127.0.0.1:8787/v1/chat/completions")  # analyst = Claude CLI proxy ($0 sub); env-overridable
# Model LEVELS: the PLAN picks the model/level per function; the engine STICKS with it.
# There is NO fall-through to another model on failure — a failure means the analyst
# improves the spec so the assigned model can implement it. (Owner directive.)
LEVELS = {1: MODEL, 2: "claude"}   # 1 = local local (default); 2 = claude via proxy (assigned deliberately)

def call_model(prompt, temperature, model):
    """Timed+logged wrapper over the router: every model call is traced (model, sizes, latency, tokens) into the
    run log, so a slow/failed/degraded call is visible after the fact. Logging is best-effort."""
    _t0 = time.time()
    _p0, _e0 = tok["p"], tok["e"]
    try:
        resp = _call_model_impl(prompt, temperature, model)
    except Exception as _me:
        run_logger.log(_RUN_ID, "model_call", model=model, prompt_chars=len(prompt or ""),
                       error=str(_me), elapsed_s=round(time.time() - _t0, 2))
        raise
    run_logger.log(_RUN_ID, "model_call", model=model, prompt_chars=len(prompt or ""),
                   resp_chars=len(resp or ""), elapsed_s=round(time.time() - _t0, 2),
                   tok_prompt=tok["p"] - _p0, tok_eval=tok["e"] - _e0)
    return resp


def _call_model_impl(prompt, temperature, model):
    """Implementer router. model=='claude' -> proxy; 'openai:<name>' -> any OpenAI-compatible local
    server (env LOCAL_OPENAI_URL, default llama-server :8089); otherwise an ollama model name."""
    if model == "claude":
        body = json.dumps({"model": "sonnet", "messages": [{"role": "user", "content": prompt}],
                           "stream": False}).encode()
        req = urllib.request.Request(CLAUDE_URL, data=body, headers={"Content-Type": "application/json"})
        # Large UI artifacts can take longer than 600s through the cli proxy; allow override.
        with urllib.request.urlopen(req, timeout=int(os.environ.get("CLAUDE_TIMEOUT", "600"))) as r:
            d = json.loads(r.read(_MAX_RESP))
        tok["claude_calls"] += 1
        return d["choices"][0]["message"]["content"]
    if model.startswith("openai:"):
        # FAITHFUL: sampling is governed entirely by the llama-server launch flags (the recipe under
        # test). The engine sends NO temperature/top_p/top_k override. max_tokens is a runaway guard only.
        body = json.dumps({"model": model.split(":", 1)[1] or "local",
                           "messages": [{"role": "user", "content": prompt}],
                           "stream": False,
                           "max_tokens": int(os.environ.get("LOCAL_OPENAI_MAXTOK", "16384"))}).encode()
        req = urllib.request.Request(os.environ.get("LOCAL_OPENAI_URL",
                                     "http://127.0.0.1:8089/v1/chat/completions"),
                                     data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=int(os.environ.get("LOCAL_GEN_TIMEOUT", "900"))) as r:
            d = json.loads(r.read(_MAX_RESP))
        u = d.get("usage") or {}
        tok["p"] += u.get("prompt_tokens", 0); tok["e"] += u.get("completion_tokens", 0)
        return d["choices"][0]["message"]["content"]
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "stream": False, "options": {"temperature": temperature}}).encode()
    req = urllib.request.Request(os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=int(os.environ.get("LOCAL_GEN_TIMEOUT", "300"))) as r:
        d = json.loads(r.read(_MAX_RESP))
    tok["p"] += d.get("prompt_eval_count", 0); tok["e"] += d.get("eval_count", 0)
    return d["message"]["content"]

def extract_func(text, name):
    t = text
    m = re.search(r"```(?:python)?\s*(.*?)```", t, re.S)
    if m: t = m.group(1)
    lines = t.splitlines()
    start = next((i for i, l in enumerate(lines)
                  if re.match(rf"\s*def\s+{re.escape(name)}\s*\(", l)), None)
    if start is None: return None
    base = len(lines[start]) - len(lines[start].lstrip())
    block = [lines[start]]
    for l in lines[start + 1:]:
        if l.strip() == "":
            block.append(l); continue
        if (len(l) - len(l.lstrip())) > base:
            block.append(l)
        else:
            break
    return "\n".join(block).rstrip()

_SB = None
def _sandbox():
    """Load the sandbox module IF LATHE_SANDBOX is an isolation mode. If the mode is set, this auto-resolves
    sandbox.py and FAILS LOUD if it can't — never silently falls through to in-proc (that would be false
    security). Unset -> None (trusted in-proc fast path)."""
    global _SB
    if _SB is None:
        mode = os.environ.get("LATHE_SANDBOX", "").lower()
        if mode not in ("subprocess", "docker"):
            _SB = False
            return None
        spp = os.environ.get("LATHE_SANDBOX_PY", "")
        if not (spp and os.path.exists(spp)):                 # auto-resolve ONLY from trusted infra next to the engine.
            # NEVER fall back to OUT_DIR/sandbox.py: OUT_DIR is model-writable, so loading the sandbox from
            # there would let a hostile plan supply its own "sandbox" and neuter the isolation it's meant to provide.
            _c = os.path.join(os.path.dirname(os.path.abspath(__file__)), "projects", "agentic-harness", "tools", "sandbox.py")
            if os.path.exists(_c):
                spp = _c
        if not (spp and os.path.exists(spp)):
            sys.exit("LATHE_SANDBOX=%s requested but sandbox.py not found — set LATHE_SANDBOX_PY" % mode)
        try:
            import importlib.util as _u
            _sp = _u.spec_from_file_location("lathe_sandbox", spp)
            _SB = _u.module_from_spec(_sp); _sp.loader.exec_module(_SB)
        except Exception as _e:
            sys.exit("LATHE_SANDBOX load failed: %s" % _e)
    return _SB or None


# Frame-introspection / raw-fd / hard-exit primitives. A generated function body that uses any of these is
# almost certainly trying to frame-walk to the sandbox nonce and forge a PASS verdict — legit compute code
# never needs them, so the candidate is rejected before the sandbox runs it (defense beyond the nonce).
_FORGE_ATTR = {'_getframe', 'f_back', 'f_locals', 'f_globals', 'f_code', 'f_builtins', 'f_trace',
               'settrace', 'setprofile', '_exit', 'tb_frame', 'gi_frame', 'cr_frame', 'ag_frame'}
_FORGE_NAME = {'_getframe', 'settrace', 'setprofile'}


def _body_forge_risk(code):
    try:
        import ast as _ast
        t = _ast.parse(code or "")
    except SyntaxError:
        return False
    for n in _ast.walk(t):
        if isinstance(n, _ast.Attribute) and n.attr in _FORGE_ATTR:
            return True
        if isinstance(n, _ast.Name) and n.id in _FORGE_NAME:
            return True
    return False


def validate(code, name, tests, base_ns):
    if _body_forge_risk(code):   # never sandbox a body that frame-walks for the verdict nonce — fail it outright
        return False
    sb = _sandbox()
    if sb is not None:   # ISOLATED exec of HEADER+code+tests (untrusted-plan path); base_ns deps aren't passed
        ok, _ = sb.run_unit(getattr(plan, "HEADER", "") or "", code, list(tests),
                            timeout=int(os.environ.get("LATHE_SANDBOX_TIMEOUT", "30")))
        return ok
    ns = dict(base_ns)
    try:
        exec((getattr(plan, "HEADER", "") or "") + "\n" + code, ns)  # validate the REAL deployed file (HEADER+code), strict ns
    except BaseException:                                            # catch SystemExit/KeyboardInterrupt too
        return False
    if not callable(ns.get(name)):
        return False
    for t in tests:
        try:
            exec(t, ns)
        except BaseException:
            return False
    return True

def _quality_score(code):
    """Heuristic cleanliness score (lower = cleaner): penalize length, bare excepts, long lines."""
    lines = [l for l in code.splitlines() if l.strip()]
    score = len(lines)
    if re.search(r'except\s*:', code):
        score += 10
    score += 2 * sum(1 for l in code.splitlines() if len(l) > 100)
    return score

def _judge_best(candidates, name, prompt):
    """Hybrid quality judge: Claude picks the cleanest/most-efficient passing candidate;
    deterministic heuristic is the fallback. Runs only at generation (result is pinned)."""
    try:
        listing = "\n\n".join(f"### Candidate {i}:\n```python\n{c}\n```" for i, c in enumerate(candidates))
        jp = (f"Below are {len(candidates)} CORRECT implementations of `{name}` (all pass the same tests). "
              f"Choose the single CLEANEST and most EFFICIENT one. Reply with ONLY the 0-based integer index.\n\n"
              f"Spec:\n{prompt[:600]}\n\n{listing}")
        resp = call_model(jp, 0.0, "claude")
        m = re.search(r'\d+', resp or "")
        if m and 0 <= int(m.group(0)) < len(candidates):
            return candidates[int(m.group(0))]
        print(f"  [judge: unusable reply for {name!r} -> heuristic pick]")   # judge ran but gave no valid index
        tok["judge_failures"] = tok.get("judge_failures", 0) + 1
    except Exception as _je:                                  # proxy down / 5xx / timeout: a SILENT fallback hides degraded mode
        print(f"  [judge FAILED for {name!r} ({_je}) -> heuristic pick]")
        tok["judge_failures"] = tok.get("judge_failures", 0) + 1
    return min(candidates, key=_quality_score)

BASE_NS = {}  # STRICT gate (fix 2026-06-28): NO pre-loaded stdlib. Generated code (+ the plan HEADER) must import what it uses — exactly like the deployed file (HEADER+funcs, assembled below). Previously json/re/etc were mirrored here, so a function using json without importing it PASSED the gate yet was broken in isolation (caught: T2 health_parse). validate() now prepends plan.HEADER so plans that import via HEADER still pass.
solved_ns = dict(BASE_NS)
solved_src = {}
try:                                  # load HEADER so a function exec'd into solved_ns sees its imports when called by a sibling
    exec((getattr(plan, "HEADER", "") or ""), solved_ns)
except BaseException:
    pass
report = []
_pins_added_this_run = set()      # pin KEYS this build added — on regression-fail rollback we remove ONLY these
_artifacts_written = []           # artifact paths this build wrote — rolled back too if regression fails
t0 = time.time()
print(f"=== ENGINE: plan={os.path.basename(PLAN_PATH)} model={MODEL} N={N} ===")
# PRE-IMPLEMENTER TEST-QUALITY GATE: the engine checks tests PASS, not that they're GOOD. If a trivial stub
# impl passes all of a function's tests, the tests don't pin behavior -> the model can ship confidently-wrong
# code green. LATHE_LINT_SPEC=warn prints it; =block refuses to build until the spec is strengthened.
_lint_mode = os.environ.get("LATHE_LINT_SPEC", "").lower()
if _lint_mode in ("warn", "block"):
    try:
        from spec_lint import lint_plan as _lint_plan
        _lv = _lint_plan(PLAN_PATH)
        _weak = []
        for _v in _lv:
            if _v.get("blocking"):
                _weak.append(_v)
                print("  [spec-lint BLOCK] %s: a trivial impl (%s) passes ALL its tests" % (_v["function"], ", ".join(_v["mutation_survivors"])))
                run_logger.log(_RUN_ID, "spec_lint", function=_v["function"], blocking=True, survivors=_v["mutation_survivors"])
            elif _v.get("static_gaps"):
                print("  [spec-lint warn] %s: %s" % (_v["function"], "; ".join(_v["static_gaps"])))
        if _weak and _lint_mode == "block":
            sys.exit("engine: REFUSING to build — %d function(s) have inadequate tests (LATHE_LINT_SPEC=block); strengthen the spec." % len(_weak))
    except SystemExit:
        raise
    except Exception as _le:
        print("  [spec-lint skipped: %s]" % _le)
# PRELUDE: exec already-built modules into solved_ns so this pass can call their functions
# during validation (they're imported by the assembled module's HEADER at runtime).
_pre_out = resolve_out_dir(getattr(plan, "OUT_DIR", ""), PLAN_PATH)   # B1


def _within(path, root):
    """True iff `path` resolves INSIDE `root` (blocks ../ + absolute escapes; cross-drive safe). Plans are
    analyst/LLM-authored, so PRELUDE/ARTIFACTS/RETIRE paths must never reach outside OUT_DIR/the project."""
    try:
        rp, rr = os.path.realpath(path), os.path.realpath(root)
        return rp == rr or rp.startswith(rr + os.sep)
    except Exception:
        return False


if _pre_out not in sys.path:
    sys.path.insert(0, _pre_out)   # so prelude modules can import each other normally
# A declared PRELUDE module is a REQUIRED dependency. If it fails to load, downstream functions that use its
# symbols fail N*12 candidates each and get MISBLAMED as spec failures (the analyst then "fixes" correct specs).
# So any prelude failure/rejection/miss must FAIL THE BUILD LOUDLY, not be a silent continue.
_prelude_ok = True
for pf in getattr(plan, "PRELUDE", []):
    pp = pf if os.path.isabs(pf) else os.path.join(_pre_out, pf)
    if os.path.isabs(pf) or not _within(pp, _pre_out):        # never exec a file outside OUT_DIR
        print(f"  [prelude REJECTED - escapes OUT_DIR: {pf!r}]"); _prelude_ok = False
    elif os.path.exists(pp):
        try:
            _psrc = open(pp, encoding="utf-8").read()
            # Require the module marker as EXACTLY line 1 — not a substring anywhere in 4 KB. An artifact's
            # model-written body can contain the marker string in a docstring to forge provenance; the engine
            # writes the real marker as line 1, and an artifact's line 1 is _LATHE_ARTIFACT_MARK (not trusted).
            if _psrc.split("\n", 1)[0].strip() != _LATHE_MARK:
                print(f"  [prelude REJECTED - not a Lathe-generated module (line-1 marker): {os.path.basename(pp)}]")
                _prelude_ok = False; continue
            exec(_psrc, solved_ns)
            print(f"  [prelude loaded: {os.path.basename(pp)}]")
        except Exception as e:
            print(f"  [prelude FAILED {pf}: {e}]"); _prelude_ok = False
    else:
        print(f"  [prelude MISSING: {pp}]"); _prelude_ok = False
if not _prelude_ok:
    print("  [BUILD WILL FAIL: a required PRELUDE dependency did not load — downstream failures are NOT spec bugs]")
# PINNING (D27): reuse previously-approved implementations -> deterministic, fast rebuilds.
PIN_FILE = os.path.join(_pre_out, ".pins.json")
pins = {}
if os.path.exists(PIN_FILE):
    try:
        pins = json.loads(open(PIN_FILE, encoding="utf-8").read())
    except Exception:
        pins = {}

# TRANSITIVE PIN INVALIDATION (review V3 §3 — the make-without-depfiles hole): if function A was freshly
# regenerated this run, any later function whose PINNED code references A was verified against the OLD A —
# reusing it would be stale-but-green even if its own tests still pass. Deps are derived from the pinned
# code itself (no .pins.json format change). Decision logic is harness-built (tools/pin_deps.py).
_pin_stale_by_deps = None
try:
    _pd = importlib.util.spec_from_file_location("pin_deps", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "projects", "agentic-harness", "tools", "pin_deps.py"))
    _pdm = importlib.util.module_from_spec(_pd); _pd.loader.exec_module(_pdm)
    _pin_stale_by_deps = _pdm.pin_stale_by_deps
except Exception:
    _pin_stale_by_deps = None            # module absent -> legacy behavior (no transitive invalidation)
_fresh_fn_names = []                     # functions regenerated THIS run (the dirty seeds; closure via plan order)

# REGRESSION-PROOF GATE (enforcement mechanism #1): with LATHE_REGRESSION_PROOF=1 (the bug-fix mode), a
# CHANGED function whose new tests ALL pass on the OLD accepted implementation is REFUSED — the change
# ships no test that reproduces the bug, so a green rebuild would prove nothing. Decision + old-def
# extraction are harness-built (tools/regression_proof.py); the tests-vs-old-code run uses the engine's
# own validate() (same sandbox as the gate itself).
_rp_extract, _rp_gate = None, None
try:
    _rp = importlib.util.spec_from_file_location("regression_proof", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "projects", "agentic-harness", "tools", "regression_proof.py"))
    _rpm = importlib.util.module_from_spec(_rp); _rp.loader.exec_module(_rpm)
    _rp_extract, _rp_gate = _rpm.extract_def, _rpm.proof_gate
    _rp_renames = getattr(_rpm, "rename_candidates", None)   # E4: rename-bypass guard
except Exception:
    pass                                 # module absent -> legacy behavior (gate is opt-in anyway)
_OLD_MODULE_SRC = ""
try:
    _omp = os.path.join(_pre_out, plan.MODULE_NAME + ".py") if getattr(plan, "MODULE_NAME", "") else ""
    if _omp and os.path.exists(_omp):
        _OLD_MODULE_SRC = open(_omp, encoding="utf-8", errors="replace").read()
except Exception:
    _OLD_MODULE_SRC = ""

# MUTATION-SCORE GATE (enforcement mechanism #3 — test COMPREHENSIVENESS is measured, not assumed): with
# LATHE_MUTATION_SCORE=<0..1>, deterministic AST mutants of the ACCEPTED code must be KILLED by the suite
# at >= that rate before the code may pin. A suite that can't tell x*x from x+x proves nothing. LLM-free
# (harness-built tools/mutation_score.py); mutants run through the same validate() as the gate itself.
_mut_code, _mut_gate = None, None
try:
    _ms = importlib.util.spec_from_file_location("mutation_score", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "projects", "agentic-harness", "tools", "mutation_score.py"))
    _msm = importlib.util.module_from_spec(_ms); _ms.loader.exec_module(_msm)
    _mut_code, _mut_gate = _msm.mutate_code, _msm.mutation_gate
except Exception:
    pass                                 # module absent -> legacy behavior (gate is opt-in anyway)
_mut_equiv = None
try:                                     # E2: equivalent-mutant filter (deterministic differential probe)
    _me = importlib.util.spec_from_file_location("mutation_equiv", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "projects", "agentic-harness", "tools", "mutation_equiv.py"))
    _mem = importlib.util.module_from_spec(_me); _me.loader.exec_module(_mem)
    _mut_equiv = _mem.equivalent_over_samples
except Exception:
    _mut_equiv = None
_mutation_unmeasured = []                # E1: functions the mutation gate could not measure (no mutable nodes)

# FAILURE-AS-ASSET for FUNCTIONS (mirrors the artifact preservation below): a failed candidate and
# the EXACT failing test are banked to disk so the analyst can sharpen the spec from real feedback.
_FN_FAILDIR = os.path.join(_pre_out, "_fn_fails")
def _why_fail(code, name, tests, base_ns):
    sb = _sandbox()
    if sb is not None:        # diagnostics must use the SAME isolation as the gate — never re-exec untrusted code in-process
        _ok, _detail = sb.run_unit((getattr(plan, "HEADER", "") or ""), code, list(tests))
        return _detail if not _ok else "no single test failed in isolation (namespace/ordering effect)"
    ns = dict(base_ns)        # trusted in-proc fast path only (LATHE_SANDBOX unset)
    try:
        exec((getattr(plan, "HEADER", "") or "") + "\n" + code, ns)
    except Exception as e:
        return f"definition error: {type(e).__name__}: {e}"
    if not callable(ns.get(name)):
        return f"no callable `{name}` was defined"
    for t in tests:
        try:
            exec(t, ns)
        except Exception as e:
            return f"first failing test:\n  {t[:200]}\n  -> {type(e).__name__}: {e}"
    return "no single test failed in isolation (namespace/ordering effect)"
def _save_fn_fail(name, model, attempt, code, reason):
    try:
        os.makedirs(_FN_FAILDIR, exist_ok=True)
        _sn = re.sub(r"[^A-Za-z0-9_-]", "_", str(name))[:64]      # plan-controlled -> sanitize (no path traversal)
        _sm = re.sub(r"[^A-Za-z0-9_-]", "_", str(model))[:40]
        stem = f"{_sn}.{_sm}.attempt{attempt}"
        _p = os.path.join(_FN_FAILDIR, stem + ".py")
        if not _within(_p, _FN_FAILDIR):                          # belt + suspenders
            return
        open(_p, "w", encoding="utf-8").write(code or "(no code extracted)")
        open(os.path.join(_FN_FAILDIR, stem + ".reason.txt"), "w", encoding="utf-8").write(reason)
    except Exception:
        pass

for f in plan.FUNCTIONS:
    name, tests = f["name"], f["tests"]
    prompt = f["prompt"] + (("\n\n" + f["context"]) if f.get("context") else "")
    # The PLAN assigns the model (or level) per function; the engine STICKS with it (no fall-through).
    fmodel = f.get("model") or LEVELS.get(f.get("level", 1), MODEL)
    short = "claude" if fmodel == "claude" else "local"
    pkey = hashlib.sha256((name + "\x00" + prompt + "\x00" + repr(tests) + "\x00" + fmodel).encode()).hexdigest()
    winner, tries, source, picked = None, 0, None, 0
    # Opt-in quality selection (D28): collect K passing candidates, judge-pick the cleanest.
    # K defaults to 1 -> classic first-pass. The analyst marks complex functions with "select": 2/3.
    K = max(1, int(f.get("select", 1)))
    # 1) Reuse the pinned (approved) implementation if its spec is unchanged AND no dependency it references
    #    was regenerated this run (transitive invalidation — V3 §3) AND it still passes.
    _dep_stale = bool(_pin_stale_by_deps and pkey in pins and _pin_stale_by_deps(pins[pkey], _fresh_fn_names))
    if _dep_stale:
        print(f"  {name:16} pin INVALIDATED — references a dependency regenerated this run; rebuilding")
    if not _dep_stale and pkey in pins and validate(pins[pkey], name, tests, solved_ns):
        winner, source = pins[pkey], "pinned"
    else:
        # REGRESSION-PROOF (mechanism #1, opt-in): this unit CHANGED — do the new tests actually catch a
        # bug in the OLD accepted implementation? If every new test passes on the old code, refuse before
        # spending a single generation token: the change ships no reproducing test.
        if _rp_gate is not None:
            _old = _rp_extract(_OLD_MODULE_SRC, name) if _rp_extract else ""
            _blocked, _rp_why = _rp_gate(os.environ.get("LATHE_REGRESSION_PROOF"), _old,
                                         bool(_old) and validate(_old, name, tests, solved_ns))
            # E4: rename-bypass guard — a "new" function under an armed gate may be a RENAMED changed unit.
            # If any DISAPPEARED def from the old module passes every new test (def-line renamed for the
            # probe), the change proves nothing and is refused the same way.
            if (not _blocked and not _old and _rp_renames is not None
                    and str(os.environ.get("LATHE_REGRESSION_PROOF") or "").strip().lower() in ("1", "true", "yes", "on")):
                _cur = [c.get("name", "") for c in plan.FUNCTIONS]
                for _cn, _cs in (_rp_renames(_OLD_MODULE_SRC, _cur) or []):
                    _probe = re.sub(r"def\s+%s\s*\(" % re.escape(_cn), "def %s(" % name, _cs, count=1)
                    if validate(_probe, name, tests, solved_ns):
                        _blocked = True
                        _rp_why = ("REFUSED: possible rename of '%s' — every new test PASSES on the old "
                                   "implementation; ship a reproducing test (rename is not a proof)" % _cn)
                        break
            if _blocked:
                print(f"  {name:16} REGRESSION-PROOF GATE — {_rp_why}")
                solved_src[name] = None
                report.append((name, False, 0, None))
                continue
        candidates = []
        for k in range(N):
            tries += 1
            try:
                code = extract_func(call_model(prompt, min(0.2 + 0.1 * k, 1.0), fmodel), name)
            except Exception:
                continue
            if code and validate(code, name, tests, solved_ns):
                candidates.append(code)
                if len(candidates) >= K:   # K=1 -> stop at first pass (unchanged behavior)
                    break
            else:
                # bank the failed candidate + the exact failing test (failure-as-asset)
                _save_fn_fail(name, fmodel, k + 1, code, _why_fail(code or "", name, tests, solved_ns))
        if candidates:
            picked = len(candidates)
            winner = candidates[0] if picked == 1 else _judge_best(candidates, name, prompt)
            # MUTATION-SCORE GATE (mechanism #3): before this code may PIN, the suite must kill enough
            # deterministic mutants of it — otherwise the tests can't distinguish right from nearly-right.
            if winner is not None and _mut_gate is not None:
                _mut_env = os.environ.get("LATHE_MUTATION_SCORE")
                _muts = _mut_code(winner, int(os.environ.get("LATHE_MUTATION_LIMIT", "8"))) if _mut_code else []
                if not _muts and _mut_env and str(_mut_env).strip():
                    # E1: no mutable nodes — do NOT silently pass an armed gate; warn loudly + record the gap
                    print(f"  {name:16} MUTATION: unmeasurable (no mutable nodes) — not gated; recorded")
                    _mutation_unmeasured.append(name)
                _survivors = [_m for _m in _muts if validate(_m, name, tests, solved_ns)]
                _killed = len(_muts) - len(_survivors)
                # E2: exclude provably-equivalent survivors (no sampled input distinguishes them from the
                # accepted code) from the denominator — an unkillable mutant must not fail a perfect suite.
                _equiv = sum(1 for _m in _survivors if _mut_equiv and _mut_equiv(winner, _m, name))
                if _equiv:
                    print(f"  {name:16} mutation: {_equiv} equivalent mutant(s) excluded from the score")
                _mblocked, _mwhy = _mut_gate(_mut_env, _killed, len(_muts) - _equiv)
                if _mblocked:
                    print(f"  {name:16} MUTATION-SCORE GATE — {_mwhy}")
                    _save_fn_fail(name, fmodel, 0, winner, "mutation gate: " + _mwhy)
                    winner = None
            if winner is None:
                solved_src[name] = None
                report.append((name, False, tries, None))
                continue
            source = short
            pins[pkey] = winner          # pin the SELECTED (cleanest) implementation
            _pins_added_this_run.add(pkey)
            _fresh_fn_names.append(name)  # dirty seed: later pins that reference this name are invalidated
    # FAIL -> analyst improves the spec so THIS model passes (D6/D19); NO model fall-through.
    solved_src[name] = winner
    report.append((name, winner is not None, tries, source))
    tag = {"local": "PASS (local)", "claude": "PASS (claude)", "pinned": "REUSED (pinned)",
           None: "FAIL -> analyst must refine spec"}[source]
    sel = f"  [judged best of {picked}]" if picked > 1 else ""
    print(f"  {name:16} {tag:22} {tries} tries  ({len(tests)} tests){sel}")
    if winner is None and source is None:
        print(f"    [failed candidates + reasons saved -> _fn_fails/ -- analyst: sharpen the spec]")
    if winner:
        try:
            exec(winner, solved_ns)  # available to downstream functions
        except BaseException:        # a top-level SystemExit in accepted code must not kill the build
            pass

# ARTIFACTS: plan-defined files (UI/API/config) GENERATED by the implementer model from a spec + tests.
# The analyst writes only prompt + tests; the MODEL writes the file. Test-gated + pinned -> reproducible.
def _strip_fence(t):
    m = re.search(r"```[a-zA-Z0-9]*\s*(.*?)```", t or "", re.S)
    s = (m.group(1) if m else (t or "")).strip()
    # Tolerate a model/CLI preamble before the doctype (e.g. claude-cli narration) and trailing chatter.
    i = s.lower().find("<!doctype html")
    if i > 0:
        s = s[i:]
    j = s.lower().rfind("</html>")
    if j != -1:
        s = s[:j + len("</html>")]
    return s.strip()
def _func_test(content, func_script, suffix=".html"):
    """FUNCTIONAL gate: run the plan's functional test (e.g. Playwright) against the generated content.
    Writes content to a temp file (path in env ARTIFACT_FILE) and runs func_script as a subprocess;
    exit 0 = pass. Lets the harness reject UI that is structurally present but behaviourally broken.
    `suffix` is the temp-file extension — defaults to .html (UI), pass the artifact's real extension
    (e.g. .py) so a backend/DB module can be imported by its gate via $ARTIFACT_FILE. (#132)
    Returns (ok, detail, timed_out). P0-1: a gate TIMEOUT is reported DISTINCTLY (slow/flaky, NOT a wrong
    answer) so the caller can retry or skip-banking instead of treating it as a spec failure."""
    if not func_script:
        return True, "", False
    th = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode="w", encoding="utf-8")
    th.write(content); th.close()
    ts = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8")
    ts.write(func_script); ts.close()
    try:
        # SECRET-SCRUB: a plan-authored functional script must NOT receive the harness's API keys / tokens /
        # creds (it could exfil them). Drop any secret-hinted var, same as sandbox._scrubbed_env.
        _hint = ("secret", "token", "key", "password", "passwd", "api", "cred")
        env = {k: v for k, v in os.environ.items() if not any(h in k.lower() for h in _hint)}
        env["ARTIFACT_FILE"] = th.name
        r = subprocess.run([sys.executable, ts.name], capture_output=True, text=True, timeout=int(os.environ.get("FUNC_GATE_TIMEOUT","360")), env=env)
        detail = (r.stdout + r.stderr).strip()
        if r.returncode != 0:
            print(f"    [functional FAIL] {(detail or 'nonzero exit')[:300]}")
        return r.returncode == 0, detail, False
    except subprocess.TimeoutExpired:
        _to = os.environ.get("FUNC_GATE_TIMEOUT", "360")
        print(f"    [functional TIMEOUT] gate exceeded {_to}s — flaky/slow, NOT counted as a spec failure")
        return False, f"TIMEOUT after {_to}s", True
    except Exception as e:
        print(f"    [functional ERROR] {e}")
        return False, str(e), False
    finally:
        for f in (th.name, ts.name):
            try:
                os.unlink(f)
            except Exception:
                pass
artifact_results = []
for art in getattr(plan, "ARTIFACTS", []):
    apath = art["path"] if os.path.isabs(art["path"]) else os.path.normpath(os.path.join(_pre_out, art["path"]))
    # SECURITY: the artifact path is analyst/model-chosen. Never let it escape OUT_DIR (an absolute path
    # or a ../ traversal would overwrite arbitrary files, e.g. engine_v2.py/board.py). Reject + bank as fail.
    if os.path.isabs(art["path"]) or not _within(apath, _pre_out):   # commonpath raises across drives; _within is safe
        print(f"  [artifact REJECTED - path escapes OUT_DIR: {art['path']!r}]")
        artifact_results.append(False)
        continue
    aprompt = art["prompt"]; amodel = art.get("model", "claude"); atests = art.get("tests", [])
    afunc = art.get("functional", "")
    aext = os.path.splitext(apath)[1] or ".html"   # #132: temp-file ext for the func gate (.py modules importable via $ARTIFACT_FILE)
    afallback = art.get("fallback"); afb_after = int(art.get("fallback_after", 2))  # local-first: after afb_after failed gate tries on the primary, escalate to fallback (e.g. claude)
    ashort = "claude" if amodel == "claude" else "local"
    def _structural(c):
        ns = {"content": c, "re": re, "json": json}
        fails = []
        for t in atests:
            try:
                exec(t, ns)
            except Exception as e:
                fails.append(f"{t}  ->  {type(e).__name__}: {e}")
        return (not fails), fails
    askel = art.get("skeleton", "")   # H8: optional skeleton -> model fills ONE region, engine splices
    amark = art.get("fill_marker", "__FILL__")
    akey = hashlib.sha256(("ARTIFACT\x00" + apath + "\x00" + aprompt + "\x00" + repr(atests) + "\x00" + amodel + "\x00" + afunc + (("\x00SK\x00" + askel) if askel else "")).encode()).hexdigest()
    acontent, asrc = None, None
    _faildir = os.path.join(_pre_out, "_artifact_fails")
    if akey in pins and _structural(pins[akey])[0]:
        acontent, asrc = pins[akey], "pinned"   # pin reuse: structural only (functional already gated at gen)
    elif askel and amark not in askel:
        # P0-2 SKELETON-COMPLETE: the scaffold has NO fill region, so calling the model only to splice nothing
        # (and discard its output) is wasted cost + a correctness illusion. Skip generation entirely — gate the
        # DETERMINISTIC skeleton directly. Re-run the gate up to 3x to absorb Playwright timing flakes (the
        # content is fixed, so re-running the gate IS the correct retry; a real fail recurs, a flake clears).
        c = askel
        sok, sfails = _structural(c)
        fok, fdetail, ftimeout = (True, "", False)
        if sok and afunc:
            fok, fdetail, ftimeout = (False, "", False)
            for _gt in range(3):
                fok, fdetail, ftimeout = _func_test(c, afunc, aext)
                if fok or not ftimeout:
                    break
                print(f"    [skeleton-complete] gate flake/timeout — retry {_gt + 1}/3")
        if sok and fok:
            acontent, asrc, pins[akey] = c, "skel", c
            _pins_added_this_run.add(akey)
            print(f"    [skeleton-complete: no model call — gated the scaffold directly]")
        elif ftimeout:
            print(f"    [skeleton-complete TIMEOUT after retries — NOT a spec failure; left undeployed, retry later]")
        else:
            try:
                os.makedirs(_faildir, exist_ok=True)
                stem = f"{os.path.basename(apath)}.skeleton-complete"
                open(os.path.join(_faildir, stem + ".html"), "w", encoding="utf-8").write(c)
                open(os.path.join(_faildir, stem + ".reason.txt"), "w", encoding="utf-8").write(
                    f"# SKELETON-COMPLETE GATE FAIL\nartifact: {apath}\nSTRUCTURAL: {'PASS' if sok else 'FAIL (' + str(len(sfails)) + ')'}\n"
                    + "\n".join(f"  - {x}" for x in sfails) + f"\n\nFUNCTIONAL: {'PASS' if fok else 'FAIL'}\n{fdetail or '(n/a)'}")
                print(f"    [saved skeleton-complete fail -> _artifact_fails/{stem}.html]")
            except Exception:
                pass
    else:
        for k in range(N):
            use_model = amodel if (not afallback or k < afb_after) else afallback   # local-first -> escalate
            ushort = "claude" if use_model == "claude" else "local"
            try:
                raw = call_model(aprompt, min(0.2 + 0.1 * k, 1.0), use_model)
            except Exception as e:
                print(f"    [gen ERROR attempt {k+1} ({use_model})] {e}")
                continue
            c = _strip_fence(raw)
            if askel:   # H8 splice skeleton-fill: model returned ONLY the fill region; place it in the scaffold
                c = askel.replace(amark, c, 1)
            sok, sfails = _structural(c)
            fok, fdetail, ftimeout = _func_test(c, afunc, aext) if sok else (False, "(skipped: structural failed first)", False)
            if sok and fok:                       # generation must pass STRUCTURAL + FUNCTIONAL
                acontent, asrc, pins[akey] = c, ushort, c
                _pins_added_this_run.add(akey)
                break
            if ftimeout:                          # P0-1: a gate TIMEOUT is slow/flaky, not a wrong answer — retry, do NOT bank as a spec failure
                print(f"    [gen attempt {k + 1} functional TIMEOUT — not banked]")
                continue
            # PRESERVE the failed candidate + WHY — post-mortem fuel for tightening the spec with REAL output.
            try:
                os.makedirs(_faildir, exist_ok=True)
                stem = f"{os.path.basename(apath)}.{use_model.replace(':', '_')}.attempt{k + 1}"
                open(os.path.join(_faildir, stem + ".html"), "w", encoding="utf-8").write(c)
                rpt = ["# FAILED ARTIFACT CANDIDATE", f"artifact: {apath}",
                       f"model: {use_model}  attempt: {k + 1}/{N}  length: {len(c)} chars", "",
                       f"STRUCTURAL: {'PASS' if sok else 'FAIL (' + str(len(sfails)) + ')'}"]
                rpt += [f"  - {x}" for x in sfails]
                rpt += ["", f"FUNCTIONAL: {'PASS' if fok else 'FAIL'}", (fdetail or "(n/a)")]
                open(os.path.join(_faildir, stem + ".reason.txt"), "w", encoding="utf-8").write("\n".join(rpt))
                print(f"    [saved failed candidate -> _artifact_fails/{stem}.html | structural_fails={len(sfails)} functional={'pass' if fok else 'fail'}]")
            except Exception:
                pass
    if acontent is not None:
        _acoll = _name_collision(os.path.basename(apath))     # artifacts write arbitrary paths — same infra/stdlib guard as modules
        if _acoll:
            sys.exit("engine: REFUSING to write artifact %r — %s" % (os.path.basename(apath), _acoll))
        if apath.endswith(".py"):                             # a .py artifact is importable: protect hand-written files generally
            _refuse_if_foreign(apath)                         # (refuses overwriting a non-marked file; prior .py artifacts carry the marker)
            # FORCE line 1 to the artifact mark (check LINE 1, not a 4KB substring). The old substring test could
            # be satisfied by putting the mark in a docstring while keeping _LATHE_MARK as line 1 — which made a
            # hostile artifact PRELUDE-trusted (prelude requires line1 == _LATHE_MARK). Now an artifact's line 1
            # is always _LATHE_ARTIFACT_MARK, so it can never be trusted as a prelude module.
            if acontent.split("\n", 1)[0].strip() != _LATHE_ARTIFACT_MARK:
                acontent = _LATHE_ARTIFACT_MARK + "\n" + acontent
        os.makedirs(os.path.dirname(apath), exist_ok=True)
        _atomic_write(apath, acontent)
        _artifacts_written.append(apath)
        print(f"  [artifact {asrc:7}] {os.path.basename(apath)} ({len(acontent)} chars, {len(atests)} tests, functional={'yes' if afunc else 'no'})")
    else:
        print(f"  [artifact FAIL -> analyst refines spec/tests] {apath}  (candidates saved in {_faildir})")
    artifact_results.append(acontent is not None)
_pins_snapshot = None      # pre-build on-disk pins, so a later regression FAIL can revert a just-written bad pin
try:
    os.makedirs(_pre_out, exist_ok=True)
    # Brief O_EXCL mutex so two concurrent engines (dispatcher + a manual build, two `auto` shells) don't lose
    # each other's pin additions in a read-modify-write race. Best-effort: if we can't grab it in ~5s, proceed
    # anyway (the MERGE below still picks up the other writer's committed entries).
    _plock = PIN_FILE + ".lock"
    _have_lock = False
    for _ in range(50):
        try:
            _lfd = os.open(_plock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(_lfd); _have_lock = True; break
        except FileExistsError:
            time.sleep(0.1)
    if os.path.exists(PIN_FILE):
        with open(PIN_FILE, "rb") as _pf:
            _pins_snapshot = _pf.read()
    _disk = {}                                  # MERGE: re-read on-disk pins (a concurrent build may have added some)
    if _pins_snapshot:                          # and let THIS build's freshly-approved pins win on key conflicts
        try: _disk = json.loads(_pins_snapshot.decode("utf-8"))
        except Exception: _disk = {}
    _merged = dict(_disk); _merged.update(pins)
    open(PIN_FILE + ".tmp", "w", encoding="utf-8").write(json.dumps(_merged))   # atomic: a crash mid-write won't zero all pins
    os.replace(PIN_FILE + ".tmp", PIN_FILE)
    if _have_lock:
        try: os.remove(_plock)
        except OSError: pass
except Exception:
    pass

passed = sum(1 for r in report if r[1])
by_local = sum(1 for r in report if r[3] == "local")
by_claude = sum(1 for r in report if r[3] == "claude")
by_pinned = sum(1 for r in report if r[3] == "pinned")
failed = [r[0] for r in report if not r[1]]
integration = integration_label(bool(getattr(plan, "INTEGRATION", "")), passed == len(plan.FUNCTIONS))   # B5
out_dir = resolve_out_dir(getattr(plan, "OUT_DIR", ""), PLAN_PATH)   # B1
module = getattr(plan, "MODULE_NAME", "game")
module_ok = (passed == len(plan.FUNCTIONS) and (bool(plan.FUNCTIONS) or bool(getattr(plan, "GLUE", "").strip()))
             and _prelude_ok)   # a missing/failed required PRELUDE dep makes the build untrusted, never green
artifacts_total = len(getattr(plan, "ARTIFACTS", []))
artifacts_passed = sum(1 for x in artifact_results if x)
if module_ok:
    os.makedirs(out_dir, exist_ok=True)
    parts = [plan.HEADER] + [solved_src[f["name"]] for f in plan.FUNCTIONS] + [plan.GLUE]
    game_code = _LATHE_MARK + "\n" + "\n\n".join(parts)         # stamp provenance so rebuilds are allowed but foreign files aren't overwritten
    _modpath = os.path.join(out_dir, module + ".py")
    _refuse_if_foreign(_modpath)
    _atomic_write(_modpath, game_code)
# INTEGRATION runs whenever present and the plan's functions (if any) all passed — incl. artifact-only plans.
_intg = getattr(plan, "INTEGRATION", "")
if _intg and (not plan.FUNCTIONS or passed == len(plan.FUNCTIONS)):
    os.makedirs(out_dir, exist_ok=True)
    # Per-module name (MODULE_NAME is validated to a bare identifier): a hardcoded "itest.py" collides with a
    # project's own hand-written itest.py, and the (correct) refuse-to-overwrite guard then aborts an otherwise-green
    # build. The "_" prefix also keeps it out of the planner's module inventory.
    _itest_name = "_itest_%s.py" % (_mn or "plan")
    _itestpath = os.path.join(out_dir, _itest_name)
    _refuse_if_foreign(_itestpath)
    _atomic_write(_itestpath, _LATHE_MARK + "\n" + _intg)
    try:
        r = subprocess.run([sys.executable, _itest_name], cwd=out_dir,
                           capture_output=True, text=True, timeout=int(os.environ.get("ITEST_TIMEOUT","360")))
        integration = ("PASS  :: " + r.stdout.strip()) if r.returncode == 0 \
                      else ("FAIL\n" + (r.stdout + r.stderr)[:800])
    except subprocess.TimeoutExpired:   # P0-1: a slow itest is NOT a spec failure (the module is already written above) — report it distinctly instead of crashing the engine
        integration = "TIMEOUT (%ss) — module written before the itest ran; benign for GLUE plans (verify live)" % os.environ.get("ITEST_TIMEOUT", "360")

# --- ANALYST-DIRECTED RETIREMENT (owner 2026-06-25): the PLAN (the bigger/analyst model) declares files this
#     build SUPERSEDES via `RETIRE = [...]`; the engine (the build step) ARCHIVES them to _archive/<date>-<plan>/
#     so the working tree stays pristine and the stale_gate (run in the regression below) passes. Backup/cleanup
#     is part of the implementation harness, INSTRUCTED by the analyst — not a thing anyone has to remember.
retired = []
_RETIRE = getattr(plan, "RETIRE", [])
if module_ok and _RETIRE and not str(integration).startswith("FAIL"):
    import shutil
    _proj = os.path.dirname(os.path.dirname(os.path.abspath(PLAN_PATH)))   # the project holding THIS plan (<proj>/plans/<plan>.py) — not a hardcoded path
    _arch = os.path.join(_proj, "_archive", "%s-%s" % (datetime.datetime.now().strftime("%Y-%m-%d"),
                                                       os.path.splitext(os.path.basename(PLAN_PATH))[0]))
    _RETIRE_CORE = {"engine_v2.py", "lathe.py", "hreview.py", "run_gates.py", "stale_gate.py", ".pins.json",
                    "board.py", "autonomy_live.py", "autonomy_loop.py", "autonomy_controller.py", "planner_prompt.py",
                    "plan_validator.py", "request_spec.py", "sandbox.py", "dispatcher.py", "driver.py",
                    "checkpoint.py", "safe_write.py", "claude_proxy.py", "harness.db"}
    _RETIRE_OK_PREFIX = tuple(os.path.realpath(os.path.join(_proj, d)) + os.sep    # only generated-output dirs are retirable
                              for d in ("tools", "_artifacts", "_archive", "plans"))

    def _retire_blocked(src):
        # A retire candidate must be EITHER under a generated-output dir OR carry a Lathe marker. This protects
        # every hand-written file regardless of extension (CLAUDE.md, docs/SECURITY.md, *.yaml, *.json, ...) —
        # not just .py — from being archived away by a single green plan listing it in RETIRE.
        if os.path.realpath(src).startswith(_RETIRE_OK_PREFIX):
            return False
        try:
            with open(src, encoding="utf-8", errors="ignore") as _f:
                _h = _f.read(4096)
            return _LATHE_MARK not in _h and _LATHE_ARTIFACT_MARK not in _h
        except OSError:
            return True

    for _rel in _RETIRE:
        _src = _rel if os.path.isabs(_rel) else os.path.join(_proj, _rel)
        _parts = {p.lower() for p in _src.replace("\\", "/").split("/")}
        if (os.path.isabs(_rel) or not _within(_src, _proj)
                or _parts & {".git", ".github", "qa"}               # never retire a gate / vcs / infra dir
                or os.path.basename(_src) in _RETIRE_CORE           # never retire the harness spine
                or _retire_blocked(_src)                            # only generated/marked outputs, any extension
                or os.path.realpath(_src) == os.path.realpath(PLAN_PATH)):
            print(f"  [RETIRE REJECTED - protected/unsafe target: {_rel!r}]"); continue
        if os.path.exists(_src):
            os.makedirs(_arch, exist_ok=True)
            try:
                shutil.move(_src, os.path.join(_arch, os.path.basename(_src))); retired.append(_rel)
            except Exception as _e:
                print("RETIRE failed for %s: %s" % (_rel, _e))
    if retired:
        open(os.path.join(_arch, "REASON.md"), "w", encoding="utf-8").write(
            "# Archived by the engine — plan %s superseded these (%s). Restore by moving back.\n\n%s\n"
            % (os.path.basename(PLAN_PATH), datetime.datetime.now().strftime("%Y-%m-%d"),
               "\n".join("- " + _r for _r in retired)))
        print("RETIRED (archived) %d superseded file(s) -> %s" % (len(retired), _arch))

# --- STANDING REGRESSION (Phase-0, council-ratified): a build that REGRESSES a previously-green standing
#     gate is RED. Baseline-aware (run_gates protects only the green set; known-open defects allowed). This
#     is "gate facts" — was-green-now-red is a fact. Env: SKIP_REGRESSION=1, REGRESSION_TIMEOUT, RUN_GATES_PATH.
regression = "SKIPPED"
_proj_root = os.path.dirname(os.path.dirname(os.path.abspath(PLAN_PATH)))  # projects/<proj> — plan lives in .../plans/<plan>.py; generic, NOT tied to any one project
_RG = os.environ.get("RUN_GATES_PATH") or os.path.join(_proj_root, "qa", "run_gates.py")
if module_ok and os.environ.get("SKIP_REGRESSION") != "1" and os.path.exists(_RG):
    try:
        _rg = subprocess.run([sys.executable, _RG], cwd=os.path.dirname(_RG),
                             capture_output=True, text=True, timeout=int(os.environ.get("REGRESSION_TIMEOUT", "300")))
        _last = (_rg.stdout.strip().splitlines() or [""])[-1]
        regression = ("PASS :: " + _last) if _rg.returncode == 0 else ("REGRESSION :: " + _last)
        if _rg.returncode != 0:
            module_ok = False     # a regressed standing gate fails the build
            try:                  # ROLL BACK the just-written module so broken code can't linger / be imported (git keeps history)
                _mp = os.path.join(out_dir, module + ".py")
                if os.path.exists(_mp):
                    os.remove(_mp); print("  [rolled back %s.py - regression failed]" % module)
            except Exception:
                pass
            try:                  # ROLL BACK only THIS build's pins: re-read the CURRENT on-disk pins (a concurrent
                if _pins_added_this_run:   # build may have committed its own since our snapshot) and drop ONLY the
                    _cur = {}              # keys we added — never blindly restore the pre-build byte image, which
                    if os.path.exists(PIN_FILE):   # would wipe a parallel build's freshly-approved pins.
                        try: _cur = json.loads(open(PIN_FILE, encoding="utf-8").read())
                        except Exception: _cur = {}
                    for _k in _pins_added_this_run:
                        _cur.pop(_k, None)
                    with open(PIN_FILE + ".tmp", "w", encoding="utf-8") as _pf:
                        _pf.write(json.dumps(_cur))
                    os.replace(PIN_FILE + ".tmp", PIN_FILE)
                    print("  [reverted %d pin(s) added by this build - regression failed]" % len(_pins_added_this_run))
            except Exception:
                pass
            for _ap in _artifacts_written:   # ROLL BACK artifacts written this build — a regression-red artifact must
                try:                         # not linger on disk trusted / re-importable via sys.path.insert(0, OUT_DIR)
                    if os.path.exists(_ap):
                        os.remove(_ap); print("  [rolled back artifact %s - regression failed]" % os.path.basename(_ap))
                except OSError:
                    pass
            if retired:           # RETIRE ran BEFORE this regression — restore the archived files so a failed build leaves no orphans
                import shutil
                for _rel in list(retired):
                    try:
                        _rsrc = _rel if os.path.isabs(_rel) else os.path.join(_proj, _rel)
                        _rarch = os.path.join(_arch, os.path.basename(_rsrc))
                        if os.path.exists(_rarch):
                            os.makedirs(os.path.dirname(_rsrc), exist_ok=True)
                            shutil.move(_rarch, _rsrc)
                    except Exception as _re:
                        print("  [RETIRE rollback failed for %s: %s]" % (_rel, _re))
                print("  [restored %d retired file(s) - regression failed]" % len(retired))
    except subprocess.TimeoutExpired:
        regression = "TIMEOUT (%ss) — investigate" % os.environ.get("REGRESSION_TIMEOUT", "300")

elapsed = time.time() - t0
# build_ok = the ROBUST overall success signal (functions AND artifacts green, with at least one unit,
# regression not failed). engine_build parses this from METRICS_JSON instead of scraping a 0/0 line.
build_ok = ((passed == len(plan.FUNCTIONS)) and (artifacts_passed == artifacts_total)
            and (len(plan.FUNCTIONS) + artifacts_total > 0)
            and not str(integration).startswith("FAIL")              # an INTEGRATION failure is NOT a green build
            and not (regression or "").startswith(("REGRESSION", "TIMEOUT")))   # a timeout is not a green gate
print("\n===== RESULT =====")
print(f"functions implemented: {passed}/{len(plan.FUNCTIONS)}  (generated: local={by_local}, claude={by_claude}; pinned-reused={by_pinned})")
if artifacts_total:
    print(f"artifacts implemented: {artifacts_passed}/{artifacts_total}")
if failed:
    print(f"NEEDS SPEC REFINEMENT (analyst refines spec/tests; never implements): {failed}")
print(f"integration: {integration}")
print(f"regression: {regression}")
print(f"local tokens: prompt={tok['p']} eval={tok['e']} total={tok['p']+tok['e']}")
print(f"elapsed: {elapsed:.0f}s")
if module_ok:
    print(f"program written to: {os.path.join(out_dir, module + '.py')}")

# --- token accounting + human-readable run report (for the 2-system savings comparison) ---
os.makedirs(out_dir, exist_ok=True)
rep = ["# RUN REPORT", "",
       f"- programmer model: {MODEL}",
       f"- best-of-N: {N}",
       f"- functions implemented: {passed}/{len(plan.FUNCTIONS)} (local={by_local}, claude={by_claude}, pinned-reused={by_pinned})",
       f"- needs-spec-refinement: {failed if failed else 'none'}",
       f"- integration: {integration.splitlines()[0]}",
       f"- elapsed: {elapsed:.0f}s",
       "", "## Token accounting (System A = this harness)",
       f"- PROGRAMMER tier-1 (local, local/free): prompt={tok['p']}  eval={tok['e']}  total={tok['p']+tok['e']}",
       f"- PROGRAMMER tier-2 (claude fallback, $0 subscription): {tok['claude_calls']} calls -> {by_claude} functions local couldn't do",
       "- ANALYST (spec authoring + refinement): NOT INSTRUMENTED this run "
       "(analyst was human-Claude). To measure true savings, automate the analyst as an "
       "LLM call and sum its tokens here.",
       "- ENGINE (deterministic): 0 tokens",
       "", "## Per-function", "| function | result | tries |", "|---|---|---|"]
for nm, ok, tries, src in report:
    rep.append(f"| {nm} | {'PASS (local)' if ok else 'FAIL - refine spec'} | {tries} |")
open(os.path.join(out_dir, "RUN_REPORT.md"), "w", encoding="utf-8").write("\n".join(rep))
print(f"run report: {os.path.join(out_dir, 'RUN_REPORT.md')}")

# --- STABLE machine-readable metrics block (delivery measurement / model A-B; also kills the
#     fragile-stdout-parsing gap). Function-lane fully instrumented; artifact-lane = TODO. ---
_endpoint = ("claude" if MODEL == "claude"
             else (os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions")
                   if MODEL.startswith("openai:")
                   else "ollama:" + os.environ.get("OLLAMA_URL", "http://localhost:11434")))
_metrics = {
    "ts": datetime.datetime.now().isoformat(timespec="seconds"), "run_id": _RUN_ID,   # ties the metrics row to runs/<run_id>.jsonl
    "plan": os.path.basename(PLAN_PATH), "model": MODEL, "endpoint": _endpoint, "N": N,
    "functions_total": len(plan.FUNCTIONS), "functions_passed": passed,
    "by_local": by_local, "by_claude": by_claude, "by_pinned": by_pinned, "failed": failed,
    "first_pass": sum(1 for r in report if r[1] and r[2] == 1),
    "fresh_attempts": sum(r[2] for r in report if r[3] != "pinned"),
    "avg_tries": round(sum(r[2] for r in report) / len(report), 2) if report else 0,
    "tok_prompt": tok["p"], "tok_eval": tok["e"], "tok_total": tok["p"] + tok["e"],
    "claude_calls": tok["claude_calls"], "judge_failures": tok.get("judge_failures", 0),   # >0 => degraded judge (proxy down): build still valid but picks were heuristic
    "elapsed_s": round(elapsed, 1),
    "tok_per_s": round(tok["e"] / elapsed, 1) if (elapsed > 0 and tok["e"]) else 0,
    "integration": (integration.splitlines()[0] if integration else ""),
    "regression": (regression.splitlines()[0] if regression else ""), "module_ok": module_ok, "retired": len(retired),
    "mutation_unmeasured": _mutation_unmeasured,   # E1: gated build, but these fns had no mutable nodes — visible, not hidden
    "artifacts_total": artifacts_total, "artifacts_passed": artifacts_passed, "build_ok": build_ok,
    "per_function": [{"name": nm, "ok": ok, "tries": tries, "src": src} for nm, ok, tries, src in report],
}
print("===METRICS_JSON_BEGIN===")
print(json.dumps(_metrics))
run_logger.log(_RUN_ID, "result", build_ok=_metrics.get("build_ok"), passed=passed,
               functions_total=len(plan.FUNCTIONS), integration=_metrics.get("integration"),
               regression=_metrics.get("regression"), failed=failed, elapsed_s=_metrics.get("elapsed_s"),
               judge_failures=tok.get("judge_failures", 0))
run_logger.rotate()
print("===METRICS_JSON_END===")
try:
    # project-local by default (portable); a consumer points LATHE_METRICS_PATH at its own ledger. No hardcoded
    # cross-repo path — the harness must never write its metrics into a consumer project just because that dir exists.
    _ledger = os.environ.get("LATHE_METRICS_PATH") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "metrics", "runs.jsonl")
    os.makedirs(os.path.dirname(_ledger), exist_ok=True)
    with open(_ledger, "a", encoding="utf-8") as _lf:
        _lf.write(json.dumps(_metrics) + "\n")
    print(f"metrics -> {_ledger}")
except Exception as _me:
    print(f"[metrics ledger write skipped: {_me}]")
