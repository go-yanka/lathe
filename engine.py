"""
Lathe — a reproducible, spec-driven build engine for LLM code generation.

Usage:  python engine.py <plan.py> <ollama-model> [N]

A *plan* is a Python file that declares (any subset of):
    MODULE_NAME : str                      # output module name
    OUT_DIR     : str                      # where to write it (default: plan's dir)
    HEADER      : str                      # imports prepended to the module
    FUNCTIONS   : [ {name, prompt, tests} ]# each generated + test-gated independently
    GLUE        : str                      # hand-authored wiring appended verbatim
    INTEGRATION : str                      # a script that imports the module and asserts (exit 0 = pass)
    ARTIFACTS   : [ {path, prompt, tests, functional} ]  # generated files (e.g. HTML), gated

Core ideas (see WHITEPAPER.md):
  - spec+tests are the source of truth; code is a build output, never hand-edited
  - a cheap LOCAL model generates; only gate-passing output is accepted
  - accepted output is PINNED by hash(spec+tests+model) -> reproducible rebuilds
  - on failure there is NO escalation; the analyst fixes the spec (failures are saved as assets)

Requires: an Ollama server on localhost:11434. No cloud calls.
"""
import sys, os, re, json, hashlib, subprocess, importlib.util, urllib.request, tempfile

PLAN_PATH = sys.argv[1]
MODEL     = sys.argv[2] if len(sys.argv) > 2 else "gemma4:12b"   # any ~12B local model; a 12B beats a 7B
N         = int(sys.argv[3]) if len(sys.argv) > 3 else 3
OLLAMA    = "http://localhost:11434/api/chat"

# ---- load the plan -----------------------------------------------------------
_spec = importlib.util.spec_from_file_location("plan", PLAN_PATH)
plan  = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(plan)
OUT_DIR     = getattr(plan, "OUT_DIR", os.path.dirname(os.path.abspath(PLAN_PATH)))
MODULE_NAME = getattr(plan, "MODULE_NAME", "module")
HEADER      = getattr(plan, "HEADER", "")
FUNCTIONS   = getattr(plan, "FUNCTIONS", [])
GLUE        = getattr(plan, "GLUE", "")
INTEGRATION = getattr(plan, "INTEGRATION", "")
ARTIFACTS   = getattr(plan, "ARTIFACTS", [])
os.makedirs(OUT_DIR, exist_ok=True)
PIN_FILE  = os.path.join(OUT_DIR, ".pins.json")
FAIL_DIR  = os.path.join(OUT_DIR, "_fails")
pins = json.load(open(PIN_FILE)) if os.path.exists(PIN_FILE) else {}

def key(*parts):
    return hashlib.sha256("\x00".join(map(str, parts)).encode()).hexdigest()

def call_model(prompt):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                       "stream": False, "options": {"temperature": 0.2}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["message"]["content"]

def strip_fence(t):
    m = re.search(r"```(?:\w+)?\s*(.*?)```", t or "", re.S)
    return (m.group(1) if m else (t or "")).strip()

def extract_func(text, name):
    """Pull a `def name(...)` block out of model output by indentation."""
    lines = strip_fence(text).splitlines()
    start = next((i for i, l in enumerate(lines) if re.match(rf"\s*def\s+{re.escape(name)}\b", l)), None)
    if start is None:
        return None
    base = len(lines[start]) - len(lines[start].lstrip())
    block = [lines[start]]
    for l in lines[start + 1:]:
        if l.strip() == "" or (len(l) - len(l.lstrip())) > base:
            block.append(l)
        else:
            break
    return "\n".join(block).rstrip()

def validate(code, name, tests, base_ns):
    ns = dict(base_ns)
    try:
        exec(code, ns)
    except Exception:
        return False
    if not callable(ns.get(name)):
        return False
    for t in tests:
        try:
            exec(t, ns)
        except Exception:
            return False
    return True

def save_fail(tag, content, reason):
    """Failures are assets: keep the candidate + why it failed, to sharpen the spec."""
    os.makedirs(FAIL_DIR, exist_ok=True)
    open(os.path.join(FAIL_DIR, tag + ".txt"), "w", encoding="utf-8").write(content)
    open(os.path.join(FAIL_DIR, tag + ".reason.txt"), "w", encoding="utf-8").write(reason)

# ---- build each function: pin-reuse or generate-gate-pin ---------------------
base_ns = {"re": re, "json": json}
solved, report = {}, []
for f in FUNCTIONS:
    name, prompt, tests = f["name"], f["prompt"], f.get("tests", [])
    k = key("FUNC", name, prompt, repr(tests), MODEL)
    if k in pins and validate(pins[k], name, tests, base_ns):
        solved[name], how = pins[k], "pinned"
    else:
        full = f"{prompt}\nReturn ONLY the Python function `{name}`, no prose, no markdown."
        how = None
        for i in range(N):
            cand = extract_func(call_model(full), name) or ""
            if validate(cand, name, tests, base_ns):
                solved[name] = pins[k] = cand; how = "generated"; break
            save_fail(f"{name}.attempt{i+1}", cand, f"failed {len(tests)} test(s) for {name}")
        if how is None:
            report.append((name, False, "FAIL"))
            print(f"  [FAIL] {name} -- no candidate passed in {N} tries. "
                  f"Analyst: sharpen the spec/tests (see {FAIL_DIR}). No escalation.")
            continue
    base_ns[name] = None  # name now exists for downstream tests
    report.append((name, True, how))
    print(f"  [{how:9}] {name}")

# ---- assemble + write the module (only if every function passed) -------------
all_ok = all(r[1] for r in report) if FUNCTIONS else True
if FUNCTIONS and all_ok:
    parts = [HEADER] + [solved[f["name"]] for f in FUNCTIONS] + [GLUE]
    open(os.path.join(OUT_DIR, MODULE_NAME + ".py"), "w", encoding="utf-8").write("\n\n".join(parts))

# ---- artifacts (e.g. HTML): structural gate + behavioral (browser) gate ------
def structural(content, tests):
    ns = {"content": content, "re": re, "json": json}
    for t in tests:
        try: exec(t, ns)
        except Exception: return False
    return True

def behavioral(content, func_script):
    """Run a functional test (e.g. Playwright) against the artifact; exit 0 = pass."""
    if not func_script:
        return True
    af = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
    af.write(content); af.close()
    tf = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8")
    tf.write(func_script); tf.close()
    try:
        env = dict(os.environ); env["ARTIFACT_FILE"] = af.name
        r = subprocess.run([sys.executable, tf.name], capture_output=True, text=True, timeout=180, env=env)
        return r.returncode == 0
    finally:
        for p in (af.name, tf.name): os.unlink(p)

for a in ARTIFACTS:
    apath = a["path"] if os.path.isabs(a["path"]) else os.path.join(OUT_DIR, a["path"])
    k = key("ART", apath, a["prompt"], repr(a.get("tests", [])), MODEL, a.get("functional", ""))
    if k in pins and structural(pins[k], a.get("tests", [])):
        content = pins[k]; how = "pinned"
    else:
        content, how = None, None
        for i in range(N):
            c = strip_fence(call_model(a["prompt"]))
            if structural(c, a.get("tests", [])) and behavioral(c, a.get("functional", "")):
                content = pins[k] = c; how = "generated"; break
            save_fail(f"{os.path.basename(apath)}.attempt{i+1}", c, "failed structural/behavioral gate")
        if content is None:
            print(f"  [FAIL] artifact {apath} -- analyst sharpens spec. No escalation."); continue
    os.makedirs(os.path.dirname(apath), exist_ok=True)
    open(apath, "w", encoding="utf-8").write(content)
    print(f"  [{how:9}] artifact {os.path.basename(apath)}")

# ---- pin + integration -------------------------------------------------------
json.dump(pins, open(PIN_FILE, "w"))  # pins are the reproducibility guarantee — commit this file
integration = "n/a"
if INTEGRATION and all_ok:
    tf = os.path.join(OUT_DIR, "_itest.py"); open(tf, "w", encoding="utf-8").write(INTEGRATION)
    r = subprocess.run([sys.executable, "_itest.py"], cwd=OUT_DIR, capture_output=True, text=True, timeout=180)
    integration = "PASS :: " + r.stdout.strip() if r.returncode == 0 else "FAIL\n" + (r.stdout + r.stderr)[:600]
    os.remove(tf)

print(f"\nbuild: {'OK - reproducible (pinned)' if all_ok else 'INCOMPLETE - fix the spec'} | "
      f"integration: {integration}")
