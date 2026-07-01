"""bench.py — an HONEST benchmark: Lathe vs Aider vs raw-Claude on the SAME specs, scored by HELD-OUT tests.

Each tool gets the same natural-language spec and operates NATURALLY. None of them sees the held-out acceptance
tests used for scoring (so this measures real correctness, not teaching-to-the-test). This is an END-TO-END
"spec -> correct code" comparison, NOT a single-variable study — the tools differ by design (documented):
  - raw-claude : one-shot to the analyst endpoint (frontier, no tests, no iteration)
  - aider      : Aider driving the LOCAL model to edit a file (tool-assisted, no external gate)
  - lathe      : `lathe do` — frontier analyst writes tests, local model implements UNDER the test gate

Env: ANALYST_URL (default :8787), LOCAL_OPENAI_URL (default rig :8090), LOCAL_MODEL (default 'local').
Usage: python benchmark/bench.py            # runs all tasks, writes BENCHMARK.md
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYST_URL = os.environ.get("ANALYST_URL", "http://127.0.0.1:8787/v1/chat/completions")
LOCAL_URL = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8090/v1/chat/completions")
LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "local")

TASKS = [
    {"name": "parse_duration",
     "spec": "Write parse_duration(s) that parses a duration like '2h30m', '45s', '1h', '90m' into total SECONDS as an int. Supports h, m, s units. Empty or None returns 0.",
     "tests": ["assert parse_duration('2h30m')==9000", "assert parse_duration('45s')==45", "assert parse_duration('1h')==3600",
               "assert parse_duration('90m')==5400", "assert parse_duration('')==0", "assert parse_duration(None)==0"]},
    {"name": "slugify",
     "spec": "Write slugify(text) that lowercases text, replaces any run of non-alphanumeric characters with a single hyphen, and strips leading/trailing hyphens. Empty or None returns ''.",
     "tests": ["assert slugify('Hello World!')=='hello-world'", "assert slugify('  A  B  ')=='a-b'", "assert slugify('foo_bar.baz')=='foo-bar-baz'",
               "assert slugify('')==''", "assert slugify(None)==''", "assert slugify('Already-Slug')=='already-slug'"]},
    {"name": "dedupe_keep_order",
     "spec": "Write dedupe_keep_order(items) that returns a list with duplicates removed, preserving first-seen order. None returns [].",
     "tests": ["assert dedupe_keep_order([1,2,1,3,2])==[1,2,3]", "assert dedupe_keep_order([])==[]", "assert dedupe_keep_order(None)==[]",
               "assert dedupe_keep_order(['a','b','a'])==['a','b']", "assert dedupe_keep_order([3,3,3])==[3]"]},
    {"name": "roman_to_int",
     "spec": "Write roman_to_int(s) that converts an uppercase Roman numeral string to its integer value (supports subtractive forms like IV, IX, XL, XC, CD, CM). Empty or None returns 0.",
     "tests": ["assert roman_to_int('XIV')==14", "assert roman_to_int('MCMXciv'.upper())==1994", "assert roman_to_int('IV')==4",
               "assert roman_to_int('LVIII')==58", "assert roman_to_int('')==0", "assert roman_to_int(None)==0"]},
    {"name": "clamp",
     "spec": "Write clamp(x, lo, hi) that returns x constrained to the range [lo, hi] (returns lo if x<lo, hi if x>hi, else x). Works for ints and floats.",
     "tests": ["assert clamp(5,0,10)==5", "assert clamp(-3,0,10)==0", "assert clamp(99,0,10)==10", "assert clamp(2.5,0,1)==1",
               "assert clamp(0,0,10)==0", "assert clamp(10,0,10)==10"]},
]


def _post(url, model, prompt, timeout=180):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def _strip(code):
    m = re.search(r"```(?:python)?\s*(.*?)```", code, re.S)
    return (m.group(1) if m else code).strip()


def eval_fn(src, tests):
    """True if the function source passes ALL held-out tests (in a bounded subprocess)."""
    prog = src + "\n\n" + "\n".join(tests) + "\n"
    d = tempfile.mkdtemp(prefix="bench_")
    p = os.path.join(d, "t.py")
    try:
        open(p, "w", encoding="utf-8").write(prog)
        r = subprocess.run([sys.executable, p], capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False
    finally:
        try: os.remove(p); os.rmdir(d)
        except OSError: pass


def run_raw_claude(task):
    t0 = time.time()
    try:
        code = _post(ANALYST_URL, "sonnet", task["spec"] + " Output ONLY the Python function code, no prose, no markdown.")
        return _strip(code), round(time.time() - t0, 1)
    except Exception as e:
        return "# raw-claude error: %s" % e, round(time.time() - t0, 1)


def run_aider(task):
    t0 = time.time()
    d = tempfile.mkdtemp(prefix="aider_")
    f = os.path.join(d, task["name"] + ".py")
    open(f, "w", encoding="utf-8").write("# implement per the instruction\n")
    env = dict(os.environ)
    env["OPENAI_API_BASE"] = LOCAL_URL.replace("/chat/completions", "")
    env.setdefault("OPENAI_API_KEY", "sk-local-dummy")
    try:
        subprocess.run(["python", "-m", "aider", "--model", "openai/" + LOCAL_MODEL, "--yes-always",
                        "--no-git", "--no-auto-commits", "--no-check-update", "--no-show-model-warnings",
                        "--message", task["spec"] + " Implement it fully in this file.", f],
                       cwd=d, env=env, capture_output=True, text=True, timeout=300)
        src = open(f, encoding="utf-8").read()
        return src, round(time.time() - t0, 1)
    except Exception as e:
        return "# aider error: %s" % e, round(time.time() - t0, 1)
    finally:
        try:
            for x in os.listdir(d): os.remove(os.path.join(d, x))
            os.rmdir(d)
        except OSError: pass


_TOOLS = os.path.join(ROOT, "projects", "agentic-harness", "tools")


def run_lathe(task):
    """`lathe do` builds into tools/. We diff the dir to find the new module, read it, then REMOVE it so the
    benchmark leaves the tree clean (pins are snapshot+restored around the whole run in main())."""
    t0 = time.time()
    before = set(f for f in os.listdir(_TOOLS) if f.endswith(".py"))
    try:
        subprocess.run([sys.executable, os.path.join(ROOT, "lathe.py"), "do", task["spec"]],
                       cwd=ROOT, capture_output=True, text=True, timeout=300)
        new = [f for f in os.listdir(_TOOLS) if f.endswith(".py") and f not in before]
        src = ""
        for f in new:
            try:
                if not src:
                    src = open(os.path.join(_TOOLS, f), encoding="utf-8").read()
                os.remove(os.path.join(_TOOLS, f))          # clean up the benchmark build immediately
            except OSError:
                pass
        if not src:                                         # module already existed (pinned) -> find one defining the fn
            import glob
            for f in glob.glob(os.path.join(_TOOLS, "*.py")):
                s = open(f, encoding="utf-8").read()
                if ("def %s(" % task["name"]) in s:
                    src = s; break
        return (src or "# lathe: no module produced"), round(time.time() - t0, 1)
    except Exception as e:
        return "# lathe error: %s" % e, round(time.time() - t0, 1)


TOOLS = [("raw-claude", run_raw_claude), ("aider", run_aider), ("lathe", run_lathe)]


def main():
    pin_file = os.path.join(_TOOLS, ".pins.json")
    pin_bak = open(pin_file, "rb").read() if os.path.exists(pin_file) else None   # restore after (benchmark builds add throwaway pins)
    rows = []
    for task in TASKS:
        for tool, fn in TOOLS:
            src, elapsed = fn(task)
            ok = eval_fn(src, task["tests"])
            rows.append({"task": task["name"], "tool": tool, "pass": ok, "elapsed_s": elapsed})
            print("  %-12s %-16s %s  %ss" % (tool, task["name"], "PASS" if ok else "fail", elapsed))
    # summary
    summ = {}
    for r in rows:
        s = summ.setdefault(r["tool"], {"pass": 0, "n": 0, "t": 0.0})
        s["pass"] += 1 if r["pass"] else 0; s["n"] += 1; s["t"] += r["elapsed_s"]
    print("\n=== SUMMARY ===")
    for tool, s in summ.items():
        print("  %-12s %d/%d passed  avg %.1fs" % (tool, s["pass"], s["n"], s["t"] / s["n"]))
    if pin_bak is not None:                                  # leave the pin ledger exactly as we found it
        open(pin_file, "wb").write(pin_bak)
    open(os.path.join(ROOT, "benchmark", "results.json"), "w", encoding="utf-8").write(json.dumps({"rows": rows, "summary": summ}, indent=1))
    return summ


if __name__ == "__main__":
    main()
