#!/usr/bin/env python
"""lathe - the command-line interface to the Lathe harness.

Treat AI code generation like a build system, not a conversation. This CLI is the user/agent surface
over the harness: draft a spec, build it on the local model under gates, run quality gates, get a CE
review, and inspect the autonomous board - all reproducible and pinned.

Usage:
  lathe "<goal>"               draft a spec for the goal, build it, gate it, pin it (one shot)
  lathe do "<goal>"            same as above (explicit)
  lathe chat                   interactive REPL: each line is a goal/command (works with you)
  lathe build <plan>           run the engine on an existing plan file (generate -> gate -> pin)
  lathe auto ["<objective>"]   run the autonomous self-feed loop (planner -> build -> repair -> commit)
  lathe gate [target]          run gates: regression (default) | h3|h4|h5|h6|all (product gates)
  lathe review <lens> <files>  CE review over files via a persona lens (read-only)
  lathe status                 board summary + latest ledger line + pins + rig/proxy health
  lathe board [status]         list tasks (optionally filtered by status)
  lathe verify <plan>          rebuild a plan; confirm pins are reused (byte-stable)
  lathe decompose              seed the board with one task per plan (+ DEPENDS_ON deps)
  lathe run [rounds]           dispatcher: drive the whole board to gated-green (overnight)
  lathe checkpoint [list|snapshot [reason]|restore <sha>]   safe git rollback points
  lathe metrics [N]            summarize the last N engine runs (tokens, pass-rate)
  lathe plans                  list available plan files
  lathe dups [--min N]         advisory: functions sharing an AST shape (duplicate logic, renamed-var safe)
  lathe whatis [capability]    source-of-truth: which artifact is LIVE for a capability (lookup, not grep)
  lathe clean [--dry]          janitor: quarantine corrupt/half-written files; keep the tree pristine (no git)
  lathe wait <task> <signal>   park a task DORMANT awaiting an external signal (event-driven pause)
  lathe resume <task> [signal] deliver the signal -> task resumes from durable state (event-driven resume)
  lathe waiting                list dormant tasks (what's waiting on a signal)
  lathe report "<title>"       file a Lathe issue into the shared queue for the maintainer to fix
  lathe issues [resolved]      maintainer: list open (or resolved) issues in the shared queue
  lathe ack <plan> [--yes]     review + acknowledge a plan's TEST SET (with LATHE_TEST_ACK=1 the engine
                               refuses to build un-acked or rewritten tests — the tests define 'correct')
  lathe trace <plan> [model]   requirement->test->pin->model traceability matrix; the validator refuses a
                               plan whose declared CRITERIA aren't each mapped to a named test
  lathe selftest               exercise every capability and report PASS/FAIL
  lathe help                   this help

Env: LATHE_MODEL (default openai:local), LATHE_TRIES (default 3),
     LOCAL_OPENAI_URL / HARNESS_CLAUDE_URL (implementer / analyst endpoints).
"""
import os
import sys
import json
import glob
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
INNER = os.path.join(ROOT, "projects", "agentic-harness")
TOOLS = os.path.join(INNER, "tools")
PLANS = os.path.join(INNER, "plans")
QA = os.path.join(INNER, "qa")
ENGINE = os.path.join(ROOT, "engine_v2.py")
HREVIEW = os.path.join(INNER, "hreview.py")
OBJ_FILE = os.path.join(ROOT, "_self_feed_objective.txt")
# Product (consuming-project) paths are env-overridable so the open-source core ships no hardcoded private path:
# LATHE_LEDGER_DIR / LATHE_PRODUCT_GATES override; a consuming project's tree is used if present, else a ROOT default.
_LEDGER_DIR = os.environ.get("LATHE_LEDGER_DIR") or os.path.join(ROOT, "docs")
LEDGER = os.path.join(_LEDGER_DIR, "OVERNIGHT_LEDGER.md")
PRODUCT_GATES = os.environ.get("LATHE_PRODUCT_GATES") or os.path.join(ROOT, "qa", "gates")   # a project's product gates; env-overridable, no hardcoded consumer path

MODEL = os.environ.get("LATHE_MODEL", "openai:local")
TRIES = os.environ.get("LATHE_TRIES", "3")
PY = sys.executable


_RUN_TIMEOUT = int(os.environ.get("LATHE_RUN_TIMEOUT", "0")) or None   # operator ceiling for unattended runs; off by default


def _run(cmd, cwd=ROOT, timeout=None):
    """Run a subprocess inheriting this terminal's stdout/stderr so the user sees live output.
    timeout (seconds) bounds the call; on expiry the child is killed and 124 is returned (GNU-timeout
    convention) so a wedged rig/engine can't freeze the CLI forever — the documented '503 for minutes while
    loading a 20GB model' is exactly this. Default ceiling from LATHE_RUN_TIMEOUT (unset = unbounded, so
    interactive commands aren't surprised); pass an explicit timeout for unattended paths."""
    import subprocess
    timeout = timeout or _RUN_TIMEOUT
    try:
        return subprocess.run(cmd, cwd=cwd, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        sys.stderr.write("\nlathe: command exceeded %ss timeout — killed (raise LATHE_RUN_TIMEOUT or pass --timeout)\n" % timeout)
        return 124


def _load_autonomy():
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import importlib.util
    spec = importlib.util.spec_from_file_location("autonomy_live", os.path.join(TOOLS, "autonomy_live.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _probe(url, timeout=4):
    """Any HTTP response (even 404) means the server is up; only a connection failure is 'down'."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return "up (%s)" % r.status
    except Exception as e:
        code = getattr(e, "code", None)
        return ("up (%s)" % code) if code else "down"


def _resolve_plan(arg):
    """Accept a full path, a plans/NN name, or a bare stem; return a path the engine can load."""
    if os.path.isfile(arg):
        return arg
    _plans_root = os.path.realpath(PLANS)
    def _in_plans(p):                                    # bare-name/glob lookups must not traverse out of PLANS (../ escape)
        return os.path.realpath(p).startswith(_plans_root + os.sep)
    for cand in (os.path.join(PLANS, arg), os.path.join(PLANS, arg + ".py")):
        if os.path.isfile(cand) and _in_plans(cand):
            return cand
    hits = [h for h in glob.glob(os.path.join(PLANS, arg + "*.py")) if _in_plans(h)]
    if len(hits) > 1:
        print("ambiguous '%s' matches %d plans — be specific" % (arg, len(hits)))
        return ""                                        # callers' isfile guard -> "plan not found"
    return hits[0] if hits else arg


# ---- commands -------------------------------------------------------------------------

def cmd_build(args):
    if not args:
        print("usage: lathe build <plan>"); return 2
    plan = _resolve_plan(args[0])
    if not os.path.isfile(plan):
        print("plan not found: %s" % args[0]); return 2
    if not _validate_plan_file(plan):
        return 2
    model = args[1] if len(args) > 1 else MODEL          # honor `lathe build <plan> [model] [tries]`
    tries = args[2] if len(args) > 2 else TRIES
    print("> building %s on %s (best-of-%s)..." % (os.path.basename(plan), model, tries))
    return _run([PY, ENGINE, plan, model, tries])


def _goal_board():
    """An ISOLATED board for one-shot goals, so `lathe do`/`chat` draft+build the user's goal instead of
    draining the standing autonomy self-feed board (`lathe auto`'s pending tasks). Fresh per call."""
    import tempfile
    fd, path = tempfile.mkstemp(prefix="lathe_goal_", suffix=".db")
    os.close(fd)
    os.remove(path)                                          # mkstemp made an empty file; board.init creates the schema
    return path


def cmd_do(args):
    goal = " ".join(args).strip()
    if not goal:
        print("usage: lathe do \"<goal>\""); return 2
    live = _load_autonomy()
    print("> drafting + building toward: %s\n" % goal)
    _gdb = _goal_board()
    try:
        tr = live.run(goal, max_plans=1, max_steps=4, build_one=True, max_repairs=2, db_path=_gdb)
    finally:
        try: os.remove(_gdb)
        except OSError: pass
    greens = sum(1 for r in tr if r["step"] == "ran_ok")
    for i, r in enumerate(tr, 1):
        print("  %2d. %s %s" % (i, r["step"], r.get("reason", "")))
    print("\n%s - %d module(s) built gated-green." % ("DONE" if greens else "no green build this run", greens))
    return 0 if greens else 1


def cmd_chat(_args):
    live = _load_autonomy()
    print("lathe chat - type a goal (or 'build <plan>', 'status', 'quit'). Each goal is spec->build->gate->pin.\n")
    while True:
        try:
            line = input("lathe> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not line:
            continue
        if len(line) > 4096:
            print("(input too long)"); continue
        if line in ("quit", "exit", ":q"):
            break
        if line.startswith("build "):
            cmd_build(line.split()[1:]); continue
        if line == "status":
            cmd_status([]); continue
        _gdb = _goal_board()
        tr = None
        try:
            tr = live.run(line, max_plans=1, max_steps=4, build_one=True, max_repairs=2, db_path=_gdb)
        except Exception as e:                      # a transient failure (proxy 502, rig 503, board lock) must NOT kill the REPL
            print("  -> error: %s (session continues — try again)\n" % e)
        finally:
            try: os.remove(_gdb)
            except OSError: pass
        if tr is None:
            continue
        greens = sum(1 for r in tr if r["step"] == "ran_ok")
        print("  -> %s (%d built)\n" % ("green" if greens else "no green build", greens))
    return 0


def cmd_auto(args):
    objective = " ".join(args).strip()
    if not objective and os.path.isfile(OBJ_FILE):
        objective = open(OBJ_FILE, encoding="utf-8").read().strip()
    if not objective:
        print("usage: lathe auto \"<objective>\"  (or create _self_feed_objective.txt)"); return 2
    live = _load_autonomy()
    print("> autonomous loop toward objective (%d chars)...\n" % len(objective))
    tr = live.run(objective, max_plans=1, max_steps=4, max_repairs=2)
    for i, r in enumerate(tr, 1):
        print("  %2d. %s %s" % (i, r["step"], r.get("reason", "")))
    greens = sum(1 for r in tr if r["step"] == "ran_ok")
    repaired = sum(1 for r in tr if r["step"] == "spec_repaired")
    print("\nbuilt=%d repaired=%d steps=%d" % (greens, repaired, len(tr)))
    return 0


def cmd_gate(args):
    target = (args[0].lower() if args else "regression")
    if target in ("h3", "h4", "h5", "h6", "all"):
        runner = os.path.join(PRODUCT_GATES, "run_all.py" if target == "all" else "")
        names = {"h3": "visual_gate.py", "h4": "perf_gate.py", "h5": "security_gate.py", "h6": "a11y_gate.py"}
        runner = os.path.join(PRODUCT_GATES, "run_all.py") if target == "all" else os.path.join(PRODUCT_GATES, names[target])
        if not os.path.isfile(runner):
            print("product gate not found (%s); these live in the consuming project's tree (LATHE_PRODUCT_GATES)." % runner); return 2
        return _run([PY, runner], cwd=os.path.dirname(PRODUCT_GATES))
    # default: harness regression + stale gate
    rg = os.path.join(QA, "run_gates.py")
    print("> regression gate (%s)..." % rg)
    return _run([PY, rg], cwd=INNER)


_ALL_LENSES = ["security", "correctness", "adversarial", "data", "perf", "reliability", "api", "maintainability", "testing", "ui"]
_DEFAULT_LENSES = ["correctness", "adversarial"]   # the two highest-value lenses, run together by default


def cmd_review(args):
    """Multi-file, multi-lens CE review. `lathe review <files>` runs correctness + adversarial over ALL
    files together (cross-referencing). `lathe review <lens|all> <files>` selects lenses."""
    if not args:
        print("usage: lathe review [lens|all] <file> [file...]")
        print("  default lenses: %s ; or one of: %s ; or 'all'" % (", ".join(_DEFAULT_LENSES), ", ".join(_ALL_LENSES)))
        return 2
    if args[0] == "auto":                            # DECIDER fires: pick the appropriate persona(s) for the code's domain
        files = args[1:]
        _sample = ""
        for f in files[:6]:
            try:
                _sample += open(f, encoding="utf-8", errors="ignore").read()[:2000] + "\n"
            except Exception:
                pass
        try:
            sys.path.insert(0, TOOLS)
            from agent_router import select_agents_for_goal
            _caps = [["security", "auth network subprocess fetch http url request input validation permission secret token git shell path traversal"],
                     ["reliability", "error handling retry timeout exception async network io connection"],
                     ["performance", "loop query cache io scale complexity memory"],
                     ["data", "database sqlite schema migration sql json"],
                     ["api", "api contract request response serialization version endpoint"],
                     ["maintainability", "complexity coupling naming dead code duplication"],
                     ["testing", "test assertion coverage mock fixture"]]
            _picked = select_agents_for_goal(_sample, _caps, 2)
        except Exception:
            _picked = []
        lenses = list(dict.fromkeys(_DEFAULT_LENSES + [p for p in _picked if p in _ALL_LENSES]))   # correctness+adversarial floor + domain specialists
        print("decider selected lenses for this code: %s" % ", ".join(lenses))
        try:                                        # D7: a needed-but-absent expert is FETCHED (license-gated) and injected
            from persona_spawn import auto_spawn_for_goal
            for _name, _md, _body in auto_spawn_for_goal(_sample, 2):
                lenses.append("@" + _md)            # hreview loads the fetched persona BODY from this path
                print("decider auto-spawned expert persona: %s (license-gated fetch -> %s)" % (_name, os.path.relpath(_md, ROOT)))
        except Exception as _sp_e:
            print("(persona auto-spawn skipped: %s)" % _sp_e)   # best-effort — never blocks the review floor
    elif args[0] == "all":
        lenses, files = _ALL_LENSES, args[1:]
    elif args[0] in _ALL_LENSES:
        n = 0                                         # consume ALL leading lens tokens (multi-lens: `review adversarial correctness <file>`)
        while n < len(args) and args[n] in _ALL_LENSES:
            n += 1
        lenses, files = args[:n], args[n:]
    else:
        lenses, files = _DEFAULT_LENSES, args        # first arg is a file -> use the default lens set
    if not files:
        print("no files given"); return 2
    files = [os.path.abspath(f) for f in files]            # resolve vs the caller's cwd, not the reviewer's INNER cwd
    missing = [f for f in files if not os.path.exists(f)]   # fail loud instead of silently "reviewing" nothing
    if missing:
        print("review: these targets do not exist: %s" % ", ".join(missing)); return 2
    rc = 0
    for lens in lenses:
        print("\n========== lathe review: %s  (%d file%s) ==========" % (lens, len(files), "s" if len(files) != 1 else ""))
        rc |= _run([PY, HREVIEW, lens] + list(files), cwd=INNER)
    return rc


def _board():
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import importlib.util
    spec = importlib.util.spec_from_file_location("board", os.path.join(TOOLS, "board.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def cmd_status(_args):
    from collections import Counter
    try:
        b = _board()
        ts = b.list_tasks(b.DEFAULT_DB)
        counts = dict(Counter(t["status"] for t in ts))
    except Exception as e:
        counts = {"(board error)": str(e)}
    pins = 0
    pin_files = set(glob.glob(os.path.join(TOOLS, ".pins.json"))) | set(glob.glob(os.path.join(INNER, "**", ".pins.json"), recursive=True))
    for pf in pin_files:                                  # set() so tools/.pins.json isn't double-counted
        try:
            with open(pf) as _pf:
                pins += len(json.load(_pf))
        except Exception:
            pass
    last = ""
    _lfs = sorted(glob.glob(os.path.join(_LEDGER_DIR, "OVERNIGHT_LEDGER_*.md")))
    if _lfs:                                              # newest per-day ledger (date-sortable names)
        lines = [l for l in open(_lfs[-1], encoding="utf-8").read().splitlines() if l.strip()]
        last = lines[-1] if lines else ""
    print("Lathe status")
    print("  board:   %s" % counts)
    print("  pins:    %d approved impls" % pins)
    print("  ledger:  %s" % (last[:120] or "(none)"))
    # labels derived from the ACTUAL configured endpoints — hardcoded "rig 35B (:8090)" lied when a user pointed
    # LOCAL_OPENAI_URL at a different model/port.
    _impl = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions")
    _anl = os.environ.get("HARNESS_CLAUDE_URL", "http://127.0.0.1:8787/v1/chat/completions")
    _hostport = lambda u: u.split("//", 1)[-1].split("/", 1)[0]
    print("  implementer (%s): %s" % (_hostport(_impl), _probe(_impl.replace("/chat/completions", "") + "/models")))
    print("  analyst (%s): %s" % (_hostport(_anl), _probe(_anl.replace("/v1/chat/completions", "") + "/health")))
    return 0


def cmd_board(args):
    b = _board()
    ts = b.list_tasks(b.DEFAULT_DB)
    flt = args[0] if args else None
    for t in ts:
        if flt and t["status"] != flt:
            continue
        print("  [%-10s] %-22s %s" % (t["status"], t.get("name") or t.get("id"), (t.get("reason") or "")[:60]))
    return 0


def cmd_verify(args):
    if not args:
        print("usage: lathe verify <plan>   (rebuilds; pins => byte-stable)"); return 2
    plan = _resolve_plan(args[0])
    if not os.path.isfile(plan):
        print("plan not found: %s" % args[0]); return 2
    if not _validate_plan_file(plan):
        return 2
    print("> verifying reproducibility of %s (rebuild should reuse pins)..." % os.path.basename(plan))
    rc = _run([PY, ENGINE, plan, MODEL, TRIES])
    print("  (check the run report: pin reuse = reproducible; fresh gen = pin miss)")
    return rc


def _tool(name):
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _validate_plan_file(plan_path):
    """A plan is EXECUTED when built, so refuse to build one that isn't data-safe (closes 'lathe build
    any.py = RCE') and whose OUT_DIR escapes the working tree. Bypass with LATHE_TRUST_PLAN=1."""
    if os.environ.get("LATHE_TRUST_PLAN") == "1":
        return True
    try:
        with open(plan_path, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        print("cannot read plan: %s" % e); return False
    v = _tool("plan_validator").is_valid_plan(text)
    if not v["ok"]:
        print("REFUSING to build: plan is not data-safe (%s). Plans are executed — build only TRUSTED plans, "
              "or set LATHE_TRUST_PLAN=1." % v["reason"]); return False
    import ast                                            # OUT_DIR must stay inside the working tree
    try:
        for n in ast.parse(text).body:
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "OUT_DIR" for t in n.targets) \
                    and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
                od = n.value.value
                full = od if os.path.isabs(od) else os.path.join(os.path.dirname(os.path.abspath(plan_path)), od)
                root = os.path.realpath(ROOT)            # the harness root, not cwd (lathe may be run from anywhere)
                if not (os.path.realpath(full) == root or os.path.realpath(full).startswith(root + os.sep)):
                    print("REFUSING to build: OUT_DIR escapes the working tree (%s). Set LATHE_TRUST_PLAN=1 to override." % od)
                    return False
    except Exception:
        pass
    return True


def cmd_decompose(_args):
    """Seed the board with one task per plan file, wiring DEPENDS_ON dependencies."""
    b = _board()
    res = _tool("decompose").seed_from_plans(PLANS, b.DEFAULT_DB, repo=ROOT)   # plan_path relative to repo ROOT (matches autonomy/engine resolution)
    print("> seeded board from plans:", res)
    return 0


def cmd_checkpoint(args):
    """Git snapshot / list / restore for safe rollback (refs/harness/ckpt, doesn't touch HEAD)."""
    ck = _tool("checkpoint")
    if not ck.is_repo(INNER):
        print("not a git repo: %s" % INNER); return 2
    sub = args[0] if args else "list"
    if sub == "snapshot":
        print("checkpoint:", ck.snapshot(INNER, args[1] if len(args) > 1 else "manual")); return 0
    if sub == "restore" and len(args) > 1:
        if "--yes" not in args:                          # whole-tree restore discards uncommitted work
            print("refusing destructive whole-tree restore without --yes.")
            print("  re-run (a safety snapshot is taken first):  lathe checkpoint restore %s --yes" % args[1])
            return 2
        print("safety snapshot:", ck.snapshot(INNER, "pre-restore"))
        ok = ck.restore(INNER, args[1]); print("restored" if ok else "restore failed"); return 0 if ok else 1
    for c in ck.list_checkpoints(INNER, 20):
        print(" ", c)
    return 0


def cmd_run(args):
    """Dispatcher: drive the WHOLE board to gated-green (the overnight multi-task driver)."""
    b = _board()
    rounds = int(args[0]) if args and args[0].isdigit() else 50
    print("> driving board via dispatcher (repo=%s, max_rounds=%d)..." % (INNER, rounds))
    _tool("dispatcher").run_board(repo=INNER, db_path=b.DEFAULT_DB, max_rounds=rounds,
                                  on_event=lambda e: print("  ", e))
    return 0


def cmd_metrics(args):
    """Summarize engine runs from the metrics ledger. `lathe metrics` lists recent runs; `lathe metrics summary`
    aggregates the EVIDENCE: build success rate, cost split (local vs frontier), first-pass rate, churn."""
    mf = os.environ.get("LATHE_METRICS_PATH") or os.path.join(ROOT, "metrics", "runs.jsonl")  # where the engine writes (project-local)
    if not os.path.isfile(mf):
        print("no metrics yet (%s)" % mf); return 0
    rows = []
    with open(mf, encoding="utf-8") as _f:
        for l in _f.read().splitlines():
            if l.strip():
                try:
                    rows.append(json.loads(l))
                except Exception:
                    pass                                     # tolerate a malformed/partial line
    if args and args[0] == "summary":
        sys.path.insert(0, TOOLS)
        from metrics_summary import metrics_summary          # harness-built pure aggregator
        s = metrics_summary(rows)
        print("Lathe metrics — %d runs" % s["runs"])
        print("  build success:   %.0f%%  (%d/%d builds green)" % (s["build_success_rate"] * 100, s["builds_ok"], s["runs"]))
        print("  functions:       %d built, %d first-try (%.0f%% first-pass)" % (s["functions_passed"], s["first_pass"], s["first_pass_rate"] * 100))
        print("  cost split:      local=%d  frontier=%d  (frontier calls=%d, %d tokens total)" % (s["by_local"], s["by_claude"], s["claude_calls"], s["tok_total"]))
        print("  churn:           avg %.2f tries/function,  %d escalations" % (s["avg_tries"], s["escalations"]))
        return 0
    n = int(args[0]) if args and args[0].isdigit() else 10
    for r in rows[-n:]:
        print("  %s  %-26s %s/%s pass  tok=%s claude=%s  %ss" % (
            (r.get("ts", "") or "")[11:19], r.get("plan", ""), r.get("functions_passed", 0),
            r.get("functions_total", 0), r.get("tok_total", 0), r.get("claude_calls", 0), r.get("elapsed_s", 0)))
    return 0


def cmd_plans(_args):
    """List available plan files."""
    for p in sorted(glob.glob(os.path.join(PLANS, "*.py"))):
        print(" ", os.path.basename(p))
    return 0


def cmd_dups(args):
    """Advisory structural-duplication report: flags functions that share an AST shape (renamed-var safe)
    across modules — 'same feature implemented in two places'. Built on the harness-made structural_signature."""
    return _tool("dup_report").main(list(args))


def _await_prefix():
    return "AWAIT:"


def cmd_wait(args):
    """Park a task DORMANT awaiting an external signal (human approval, a slow dep, a time window) instead of
    burning cycles or stalling. `lathe wait <task_id> <signal>`. Durable on the board; survives restarts."""
    if len(args) < 2:
        print("usage: lathe wait <task_id> <signal>"); return 2
    tid, sig = args[0], args[1]
    b = _tool("board")
    if not b.get_task(tid, b.DEFAULT_DB):
        print("no task %r on the board" % tid); return 1
    b.set_status(tid, "blocked", _await_prefix() + sig, db_path=b.DEFAULT_DB)
    print("task %s parked DORMANT, awaiting signal '%s' (resume with: lathe resume %s %s)" % (tid, sig, tid, sig))
    return 0


def cmd_resume(args):
    """Deliver a signal to a dormant task -> it resumes from durable board state (the ADK state_delta idea):
    `lathe resume <task_id> [signal]`. Sets it back to pending so the next `lathe auto` cycle continues it."""
    if not args:
        print("usage: lathe resume <task_id> [signal]"); return 2
    tid = args[0]
    sig = args[1] if len(args) > 1 else ""
    b = _tool("board")
    t = b.get_task(tid, b.DEFAULT_DB)
    if not t:
        print("no task %r on the board" % tid); return 1
    reason = t.get("reason", "") or ""
    awaited = reason[len(_await_prefix()):] if reason.startswith(_await_prefix()) else ""
    if t.get("status") != "blocked" or not awaited:
        print("task %s is not dormant (status=%s, reason=%r) — nothing to resume" % (tid, t.get("status"), reason)); return 1
    if sig and sig != awaited:
        print("task %s awaits '%s', not '%s'" % (tid, awaited, sig)); return 1
    b.set_status(tid, "pending", "resumed:%s" % (sig or awaited), db_path=b.DEFAULT_DB)
    print("signal '%s' delivered — task %s RESUMED (pending); next `lathe auto` cycle continues it." % (sig or awaited, tid))
    return 0


def cmd_waiting(_args):
    """List tasks parked dormant awaiting a signal — observability for long-running, event-gated jobs."""
    b = _tool("board")
    pre = _await_prefix()
    rows = [t for t in b.list_tasks(b.DEFAULT_DB) if t.get("status") == "blocked" and (t.get("reason") or "").startswith(pre)]
    if not rows:
        print("no dormant tasks (nothing waiting on a signal)."); return 0
    print("dormant tasks awaiting a signal:")
    for t in rows:
        print("  %-16s awaiting '%s'" % (t.get("task_id") or t.get("id"), (t.get("reason") or "")[len(pre):]))
    return 0


def cmd_clean(args):
    """Bring the tree to PRISTINE state, GIT-INDEPENDENTLY: quarantine unparseable plans/modules to _archive/
    and cap the failure bank. Cleanliness is intrinsic, not borrowed from git. `--dry` previews only."""
    import ast
    import shutil
    import time
    dry = "--dry" in args
    arch = os.path.join(INNER, "_archive", time.strftime("%Y-%m-%d") + "-cleanup")
    moved = [0]

    def _quarantine(path, why):
        print("  %s %s (%s)" % ("WOULD move" if dry else "quarantined", os.path.relpath(path, INNER), why))
        if not dry:
            os.makedirs(arch, exist_ok=True)
            dest = os.path.join(arch, os.path.basename(path))
            if os.path.exists(dest):                          # collision: same basename in plans/ AND tools/, or a 2nd clean same day
                base, ext = os.path.splitext(os.path.basename(path))
                i = 1
                while os.path.exists(os.path.join(arch, "%s.%d%s" % (base, i, ext))):
                    i += 1
                dest = os.path.join(arch, "%s.%d%s" % (base, i, ext))
            shutil.move(path, dest)
        moved[0] += 1

    cand = glob.glob(os.path.join(PLANS, "*.py")) + \
        [m for m in glob.glob(os.path.join(TOOLS, "*.py")) if not os.path.basename(m).startswith("test_")]
    for p in cand:                                            # 1) unparseable plans/modules = definitively not pristine
        try:
            ast.parse(open(p, encoding="utf-8").read())
        except Exception as e:
            _quarantine(p, "unparseable: %s" % type(e).__name__)

    import re as _re                                          # 2) sweep exactly what stale_gate flags so clean can REMEDY it
    _STALE = _re.compile(r"(_backup|\.bak$|_bak\b|_old\b|_v1\b|_v2_old|_copy\b|copy\d|\.orig$|~$|\.tmp$)", _re.I)
    for d in (PLANS, TOOLS):
        for name in (os.listdir(d) if os.path.isdir(d) else []):   # os.listdir (not glob "*") -> also catches dotfiles like .pins.json.tmp
            p = os.path.join(d, name)
            if os.path.isfile(p) and _STALE.search(name):
                _quarantine(p, "stale/backup/temp (stale-gate target)")

    faildir = os.path.join(TOOLS, "_fn_fails")                # 2) cap the failure bank (repair uses only the newest per fn)
    if os.path.isdir(faildir):
        old = sorted(glob.glob(os.path.join(faildir, "*")), key=os.path.getmtime, reverse=True)[40:]
        if old and not dry:
            _fb = os.path.join(arch, "_fn_fails_old")
            os.makedirs(_fb, exist_ok=True)
            for f in old:
                try:
                    shutil.move(f, os.path.join(_fb, os.path.basename(f)))
                except Exception:
                    pass
        if old:
            print("  %s %d stale fail-bank entr%s" % ("WOULD archive" if dry else "archived", len(old), "y" if len(old) == 1 else "ies"))

    print("clean: %d unparseable file(s) %s%s." % (
        moved[0], "would be quarantined" if dry else "quarantined",
        "" if dry else " -> %s" % os.path.relpath(arch, ROOT)))
    return 0


def _issues_dir():
    # cross-platform default (a hardcoded C:\ path created a literal "C:\lathe-issues" dir in the cwd on
    # macOS/Linux); override with LATHE_ISSUES_DIR (e.g. a shared team queue).
    return os.environ.get("LATHE_ISSUES_DIR", os.path.join(os.path.expanduser("~"), ".lathe", "issues"))


def cmd_report(args):
    """File a Lathe issue into the SHARED QUEUE so the maintainer can triage + fix it. `lathe report "<title>"`
    writes a skeleton (auto version/project/date) into <issues>/open/ for you to complete."""
    title = " ".join(args).strip()
    if not title:
        print('usage: lathe report "<short title>"'); return 2
    import time
    import re as _re
    od = os.path.join(_issues_dir(), "open"); os.makedirs(od, exist_ok=True)
    ver = "unknown"
    vf = os.path.join(ROOT, "VERSION")
    if os.path.isfile(vf):
        ver = open(vf, encoding="utf-8").read().strip()
    proj = os.environ.get("LATHE_PROJECT") or os.path.basename(ROOT)
    slug = (_re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]) or "issue"
    p = os.path.join(od, "%s-%s-%s.md" % (time.strftime("%Y%m%d-%H%M%S"), proj, slug))
    open(p, "w", encoding="utf-8").write(
        "# [SEVERITY: blocker|major|minor] %s\n\n- project: %s\n- lathe_version: %s\n- date: %s\n\n"
        "## What I ran / context\n\n## What happened\n\n## What I expected\n\n## Minimal repro\n\n## Impact\n"
        % (title, proj, ver, time.strftime("%Y-%m-%d %H:%M")))
    print("issue filed -> %s\n  fill in: what happened / expected / repro / impact, then save." % p)
    return 0


def cmd_issues(args):
    """Maintainer triage of the shared issue queue. `lathe issues` (open) | `lathe issues resolved`."""
    sub = "resolved" if (args and args[0] == "resolved") else "open"
    d = os.path.join(_issues_dir(), sub)
    fs = sorted(glob.glob(os.path.join(d, "*.md"))) if os.path.isdir(d) else []
    if not fs:
        print("no %s issues (%s)" % (sub, d)); return 0
    print("%s issues (%d) in %s:" % (sub, len(fs), d))
    for f in fs:
        try:
            first = open(f, encoding="utf-8").readline().strip()
        except Exception:
            first = ""
        line = "  %-46s %s" % (os.path.basename(f), first[:60])
        print(line.encode("ascii", "replace").decode("ascii"))   # console-safe (issue titles may hold non-ASCII)
    return 0


def cmd_whatis(args):
    """Capability SOURCE OF TRUTH: `lathe whatis <capability>` answers which artifact is LIVE for it (lookup,
    not grep/trace) — the fix for 'N copies, which is real'. No arg -> list all live capabilities."""
    reg = _tool("registry")
    table = reg.load()
    if not args:
        for name, e in sorted(table.items()):
            if isinstance(e, dict) and e.get("status") == "live":
                print("  %-26s -> %s" % (name, e.get("canonical", "?")))
        return 0
    cap = args[0]
    e = reg.whatis(cap)
    if not isinstance(e, dict):
        known = ", ".join(sorted(k for k, v in table.items() if isinstance(v, dict)))
        print("no capability %r in the registry. known: %s" % (cap, known))
        return 1
    print("%s:" % cap)
    for k in ("status", "canonical", "entrypoint", "supersedes"):
        if k in e:
            print("  %-11s %s" % (k, e[k]))
    return 0


def cmd_selftest(_args):
    """Exercise every Lathe capability and report PASS/FAIL - the CLI confirmation surface."""
    import importlib.util
    results = []
    def rec(name, ok, note=""):
        if ok is None:                       # SKIP — not applicable to this install (e.g. no consumer product gates)
            print("  [SKIP] %-34s %s" % (name, note)); return
        results.append(bool(ok))
        print("  [%s] %-34s %s" % ("PASS" if ok else "FAIL", name, note))
    print("Lathe self-test\n")

    plan = _resolve_plan("M01_token_overlap")
    rc = _run([PY, ENGINE, plan, MODEL, TRIES]) if os.path.isfile(plan) else 1
    rec("build + content-hash pins", rc == 0, "(pinned rebuild)")
    rec("regression / stale gate", _run([PY, os.path.join(QA, "run_gates.py")], cwd=INNER) == 0)
    try:
        spec = importlib.util.spec_from_file_location("autonomy_live", os.path.join(TOOLS, "autonomy_live.py"))
        al = importlib.util.module_from_spec(spec); spec.loader.exec_module(al)
        rec("focus: select-K (judged)", '"select": 2' in al._strict_suffix("judged"))
        rec("focus: artifact / UI", "ARTIFACTS" in al._strict_suffix("artifact"))
        deps = al.make_real_deps({"plans": 0, "max_plans": 0, "seq": 0, "repairs": 0,
                                  "max_repairs": 2, "focus": "helper"}, al._board.DEFAULT_DB)
        rec("repair feedback loop", "repair_spec" in deps)
    except Exception as e:
        rec("autonomy engine", False, str(e)[:50])
    rec("CE review (hreview)", os.path.isfile(HREVIEW))
    _pg = os.path.isfile(os.path.join(PRODUCT_GATES, "run_all.py"))   # a CONSUMER's product gates (vendoring boundary) — skip if this
    rec("product gates (consumer)", True if _pg else None,             # is a clean harness with none; set LATHE_PRODUCT_GATES to test one
        "" if _pg else "(none present — set LATHE_PRODUCT_GATES to test a consumer's)")
    for t in ("decompose", "checkpoint", "dispatcher"):
        try:
            _tool(t); rec("orchestration: %s" % t, True)
        except Exception as e:
            rec("orchestration: %s" % t, False, str(e)[:40])
    base = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions").replace("/chat/completions", "")
    try:                                                  # B6: label reflects the CONFIGURED model, not a hardcoded "35B"
        sys.path.insert(0, TOOLS); from spine_helpers import model_label
        _ml = model_label(os.environ.get("HARNESS_MODEL", ""))
    except Exception:
        _ml = "local"
    rec("implementer reachable [%s] (do/auto/judged)" % _ml, "up" in str(_probe(base + "/models")))
    rec("analyst proxy reachable (plan/repair)", "up" in str(_probe("http://127.0.0.1:8787/health")))

    n = sum(1 for ok in results if ok)
    print("\n%d/%d capabilities confirmed via CLI." % (n, len(results)))
    return 0 if n == len(results) else 1


def cmd_logs(args):
    """Read structured per-run logs. `lathe logs` lists recent runs; `lathe logs <run_id>` prints one run's
    full trace; `--tail` shows the most recent; `--grep <s>` searches across runs. This is what you send with
    a bug report — the whole run is captured (with secrets redacted)."""
    sys.path.insert(0, TOOLS)
    try:
        import run_logger
    except Exception as e:
        print("logs: run_logger unavailable (%s)" % e); return 1
    runs = run_logger.list_runs()
    if "--grep" in args:
        pat = args[args.index("--grep") + 1] if args.index("--grep") + 1 < len(args) else ""
        hits = 0
        for rid in runs:
            for rec in run_logger.read_run(rid):
                line = json.dumps(rec)
                if pat.lower() in line.lower():
                    print("%s  %s" % (rid, line)); hits += 1
        print("(%d matching entries)" % hits); return 0
    rid = None
    if "--tail" in args:
        rid = runs[0] if runs else None
    else:
        pos = [a for a in args if not a.startswith("-")]
        if pos:
            rid = pos[0]
    if rid:                                             # one run -> full trace
        recs = run_logger.read_run(rid)
        if not recs:
            print("no such run: %s" % rid); return 1
        print("=== run %s (%d events) ===" % (rid, len(recs)))
        for rec in recs:
            ev = rec.get("event", "?")
            rest = {k: v for k, v in rec.items() if k not in ("ts", "run_id", "event")}
            print("  %s  %-11s %s" % (rec.get("ts", ""), ev, json.dumps(rest)))
        return 0
    if not runs:                                        # list mode
        print("no runs logged yet (logs at %s)" % run_logger.log_dir()); return 0
    print("recent runs (newest first) — `lathe logs <id>` for the full trace:")
    for rid in runs[:25]:
        recs = run_logger.read_run(rid)
        res = next((r for r in reversed(recs) if r.get("event") == "result"), {})
        start = next((r for r in recs if r.get("event") == "start"), {})
        tag = ("ok" if res.get("build_ok") else "FAIL") if res else "?"
        print("  %s  %-14s %-5s  %d events" % (rid, start.get("plan", "?"), tag, len(recs)))
    return 0


def cmd_lint_spec(args):
    """TEST-QUALITY check: score a plan's tests BEFORE building. Static gaps + a MUTATION PROBE (does a trivial
    stub impl pass every test? -> the tests don't pin behavior). `lathe lint-spec <plan.py>`."""
    if not args:
        print("usage: lathe lint-spec <plan.py>"); return 2
    sys.path.insert(0, TOOLS)
    try:
        from spec_lint import lint_plan
    except Exception as e:
        print("lint-spec: unavailable (%s)" % e); return 1
    verdicts = lint_plan(args[0])
    if not verdicts:
        print("lint-spec: no FUNCTIONS found in %s" % args[0]); return 0
    bad = 0
    for v in verdicts:
        mark = "OK" if v["ok"] else ("BLOCK" if v["blocking"] else "warn")
        print("  [%-5s] %s" % (mark, v["function"]))
        if v["mutation_survivors"]:
            print("          weak: a trivial impl (%s) passes ALL its tests -> tests don't pin behavior" % ", ".join(v["mutation_survivors"]))
        if v["static_gaps"]:
            print("          advisory: %s" % "; ".join(v["static_gaps"]))
        if v["blocking"]:
            bad += 1
    print("%d/%d function(s) have BLOCKING weak tests" % (bad, len(verdicts)))
    return 1 if bad else 0


def cmd_map(args):
    """Multi-language CODE-STRUCTURE MAP (repo-map) via universal-ctags — names, kinds, signatures, scopes — so
    a large model reads the STRUCTURE instead of full files (less context, fewer tool calls). Works across ~150
    languages incl. Python + JS. `lathe map <file-or-dir> ...`. Needs ctags (universal-ctags) on PATH."""
    if not args:
        print("usage: lathe map <file-or-dir> [...]"); return 2
    sys.path.insert(0, TOOLS)
    try:
        from repomap import ctags_available, render_map
    except Exception as e:
        print("map: unavailable (%s)" % e); return 1
    if not ctags_available():
        print("map: ctags not found. Install universal-ctags (winget install UniversalCtags.Ctags) to enable the repo-map."); return 1
    m = render_map(list(args))
    print(m or "(no definitions found)")
    return 0


def cmd_flow(args):
    """Named, transparent WORKFLOWS (code-review, bug-fix, enhancement, doc-review, new-project). `lathe flow`
    lists them; `lathe flow <name>` shows the exact ordered steps (so you know how the harness handles a job
    BEFORE running it); `lathe flow <name> --run [targets...]` executes the automatable [AUTO]/[GATE] steps in
    order (halting on failure) and prints the human-judgment [YOU] steps as checkpoints."""
    import shlex
    sys.path.insert(0, TOOLS)
    try:
        from workflows import list_workflows, get_workflow, get_contract
        from flow_report import classify_step, workflow_verdict, render_report   # harness-built (gated+pinned)
    except Exception as e:
        print("flow: unavailable (%s)" % e); return 1
    if not args:
        print("workflows (lathe flow <name> to see the steps; add --run <targets> to execute):")
        for n, d in list_workflows():
            print("  %-13s %s" % (n, d))
        return 0
    name = args[0]
    wf = get_workflow(name)
    if not wf:
        print("unknown workflow '%s'. available: %s" % (name, ", ".join(n for n, _ in list_workflows()))); return 2
    run = "--run" in args
    tgt = " ".join(a for a in args[1:] if a != "--run")
    print("workflow: %s — %s" % (name, wf["desc"]))
    _c = get_contract(name)                               # up-front EXPECTATIONS (contract) before any step runs
    if _c:
        print("  when:        %s" % _c.get("when", "—"))
        print("  entry:       %s" % _c.get("entry", "—"))
        print("  deliverable: %s" % _c.get("deliverable", "—"))
        print("  done when:   %s" % _c.get("done", "—"))
    print()
    rows = []                                              # (label, status) rows for the transparent run-report
    for i, (kind, label, action) in enumerate(wf["steps"], 1):
        act = action.replace("{files}", tgt).replace("{plan}", tgt)
        if kind == "you":
            print("  %d. [YOU]  %s" % (i, label))
            rows.append((label, classify_step("you", 0, "")))     # human-judgment step -> 'todo'
            continue
        tag = "GATE" if kind == "gate" else "AUTO"
        shown = "lathe gate" if kind == "gate" else ("lathe " + act)
        print("  %d. [%s] %s  ->  %s" % (i, tag, label, shown))
        if not run:
            continue
        if kind != "gate" and ("{files}" in action or "{plan}" in action) and not tgt:
            print("       (needs a target — pass files/plan after --run)")
            rows.append((label, "blocked"))                       # a missing target is BLOCKED, never a silent pass
            break
        rc = cmd_gate([]) if kind == "gate" else main(shlex.split(act))   # re-enter the CLI (reuse the real command)
        status = classify_step(kind, rc, "")                      # harness-built classifier (rc-driven; steps now fail loud)
        rows.append((label, status))
        print("       -> step [%s]" % status.upper())
        if status == "blocked":
            print("       -> BLOCKED — stopping the workflow"); break
    if run:
        print("\n" + render_report(name, rows))                   # transparent report + fail-loud PASS/BLOCKED verdict
        return 0 if workflow_verdict([s for _, s in rows]) == "PASS" else 1
    print("\n(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)")
    return 0


def _spawn_one(e):
    """One canonical fetch implementation — tools/persona_spawn.py (shared with the D7 in-flow deciders)."""
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    from persona_spawn import spawn_one
    return spawn_one(e)

def cmd_agent(args):
    """Load-the-program: instantiate the best expert persona for a NEED — from the vendored set, or a locally-mirrored
    copy fetched ON DEMAND from a permissively-licensed source (refreshed if reachable, else the cached copy).
    LLM-INDEPENDENT: outputs a persona (prompt text) to inject into whatever endpoint is configured.
    `lathe agent "<need>"` matches; `--spawn` mirrors it (with its LICENSE); `lathe agent refill` pre-mirrors all
    permissive agents for fast/offline spawn. Decider is harness-built (tools/agent_router.py); inventory is agents/catalog.json."""
    import json
    sys.path.insert(0, TOOLS)
    from agent_router import pick_best, license_ok
    try:
        entries = json.load(open(os.path.join(INNER, "agents", "catalog.json"), encoding="utf-8")).get("agents", [])
    except Exception as ex:
        print("agent: catalog unavailable (%s)" % ex); return 1
    if args and args[0] == "refill":                          # pre-mirror all permissive agents + their licenses
        n = 0
        for e in entries:
            if e.get("vendored") or not license_ok(e.get("license", "")):
                continue
            md, how = _spawn_one(e)
            print(("  mirrored %-22s [%s] %s" % (e["name"], e["license"], how)) if md else ("  skip     %-22s (%s)" % (e["name"], how)))
            n += 1 if md else 0
        print("refill: %d permissive agents mirrored locally (+ their licenses)." % n); return 0
    need = " ".join(a for a in args if not a.startswith("--")).strip()
    if not need:
        print('usage: lathe agent "<need>" [--spawn]   |   lathe agent refill'); return 2
    name = pick_best(need, [[e["name"], e.get("capability", "")] for e in entries])
    if not name:
        print("no catalogued agent matches '%s'." % need); return 1
    e = next(x for x in entries if x["name"] == name)
    print("best match: %s  [%s · %s]\n  %s" % (name, e.get("source") or e.get("repo"), e.get("license"), e.get("capability", "")))
    if e.get("vendored"):
        print("  VENDORED (ready): %s" % e["path"]); return 0
    if not license_ok(e.get("license", "")):
        print("  NOT auto-fetchable — license '%s' is not permissive; verify + vendor manually." % e.get("license")); return 1
    if "--spawn" not in args:
        print("  fetchable under %s. Add --spawn to mirror it locally (with its license)." % e.get("license")); return 0
    md, how = _spawn_one(e)
    if not md:
        print("  spawn failed: %s" % how); return 1
    print("  SPAWNED (%s): agents/_fetched/%s.md + license stored. Ready to inject into any endpoint." % (how, name))
    return 0


def cmd_ack(args):
    """Test-ack gate (the analyst's tests were the ONE ungated artifact — they define what 'correct' means).
    `lathe ack <plan>` shows every function's tests for human review and records an ack keyed by a digest of
    the exact test set; with LATHE_TEST_ACK=1 the engine refuses to build un-acked (or rewritten) tests."""
    import importlib.util, json, hashlib
    yes = "--yes" in args
    paths = [a for a in args if not a.startswith("--")]
    if not paths:
        print("usage: lathe ack <plan.py> [--yes]   (records approval of the plan's CURRENT test set)"); return 2
    plan_path = os.path.abspath(paths[0])
    if not os.path.exists(plan_path):
        print("ack: no such plan: %s" % plan_path); return 2
    spec = importlib.util.spec_from_file_location("plan", plan_path)
    plan = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(plan)
    except Exception as e:
        print("ack: plan does not load: %s" % e); return 1
    fns = getattr(plan, "FUNCTIONS", []) or []
    if not fns:
        print("ack: plan has no FUNCTIONS (nothing to acknowledge)"); return 0
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    from test_ack import tests_digest
    print("TESTS UNDER REVIEW — these asserts DEFINE correct behavior for this build:\n")
    for f in fns:
        print("  %s:" % f.get("name", "?"))
        for t in f.get("tests", []) or []:
            print("      %s" % t)
    digest = tests_digest(fns)
    if not yes:
        try:
            resp = input("\nAcknowledge this exact test set? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            resp = ""
        if resp not in ("y", "yes"):
            print("NOT acknowledged — nothing recorded."); return 1
    ack_file = os.path.join(os.path.dirname(plan_path), ".test_ack.json")
    try:
        acks = json.loads(open(ack_file, encoding="utf-8").read())
    except Exception:
        acks = {}
    acks[os.path.basename(plan_path)] = digest
    open(ack_file, "w", encoding="utf-8").write(json.dumps(acks, indent=1))
    print("acknowledged: %s (digest %s...) -> %s" % (os.path.basename(plan_path), digest[:12], ack_file))
    print("(the engine enforces this only when LATHE_TEST_ACK=1; any test rewrite forces a re-ack)")
    return 0


def cmd_trace(args):
    """Requirement→test→pin→model traceability matrix (enforcement mechanism #2 / the compliance artifact).
    A plan may declare acceptance CRITERIA; the validator REFUSES any criterion not mapped to ≥1 named,
    existing test (unmapped = a requirement nothing verifies). `lathe trace <plan>` emits the matrix."""
    import importlib.util, json, hashlib
    paths = [a for a in args if not a.startswith("--")]
    if not paths:
        print("usage: lathe trace <plan.py> [model]   (matrix for the plan's declared CRITERIA)"); return 2
    plan_path = os.path.abspath(paths[0])
    if not os.path.exists(plan_path):
        print("trace: no such plan: %s" % plan_path); return 2
    spec = importlib.util.spec_from_file_location("plan", plan_path)
    plan = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(plan)
    except Exception as e:
        print("trace: plan does not load: %s" % e); return 1
    fns = getattr(plan, "FUNCTIONS", []) or []
    criteria = getattr(plan, "CRITERIA", None)
    if not criteria:
        print("trace: plan declares no CRITERIA — nothing to trace. (Declare CRITERIA=[{'id','text','tests'}] "
              "to get requirement→test enforcement + this matrix.)"); return 0
    model = paths[1] if len(paths) > 1 else os.environ.get("LATHE_MODEL", "openai:local")
    # per-function pin lookup — the same key the engine uses: sha256(name+prompt+tests+model)
    out_dir = getattr(plan, "OUT_DIR", "") or os.path.dirname(plan_path)
    pin_file = os.path.join(out_dir if os.path.isabs(out_dir) else os.path.join(ROOT, out_dir), ".pins.json")
    try:
        pins = json.loads(open(pin_file, encoding="utf-8").read())
    except Exception:
        pins = {}
    fn_tests, fn_pins = {}, {}
    for f in fns:
        name = f.get("name", ""); tests = f.get("tests", []) or []
        fn_tests[name] = tests
        prompt = f.get("prompt", "") + (("\n\n" + f["context"]) if f.get("context") else "")
        fmodel = f.get("model") or model
        pkey = hashlib.sha256((name + "\x00" + prompt + "\x00" + repr(tests) + "\x00" + fmodel).encode()).hexdigest()
        if pkey in pins:
            fn_pins[name] = [pkey[:12], fmodel]
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    from trace_logic import trace_rows
    rows = trace_rows(criteria, fn_tests, fn_pins)
    print("TRACEABILITY MATRIX — %s  (model=%s; UNPINNED = not yet built/pinned for this model)" % (os.path.basename(plan_path), model))
    print("%-8s %-18s %-14s %-14s %s" % ("CRIT", "FUNCTION", "PIN", "MODEL", "TEST"))
    unresolved = 0
    for r in rows:
        unresolved += 1 if r["fn"] == "(unresolved)" else 0
        print("%-8s %-18s %-14s %-14s %s" % (r["criterion"], r["fn"], r["pin"], r["model"], r["test"][:80]))
    covered = len({r["criterion"] for r in rows if r["fn"] != "(unresolved)"})
    print("\n%d criteria, %d covered, %d unresolved; %d matrix rows." % (len(criteria), covered, unresolved, len(rows)))
    return 0 if unresolved == 0 else 1


def cmd_checkin(args):
    """Gated check-in — extends the pristine model to the remote: refuse to commit/push unless the standing gates
    are green, the tree has NO relics (caches, logs, _fn_fails, journals), and you're not behind the upstream.
    `lathe checkin -m "msg"` commits; add `--push` to also push (a secret scan runs first; skipped if no upstream).
    Decision logic is harness-built (tools/checkin_logic.py); this wires the git I/O around it."""
    import subprocess, re
    do_push = "--push" in args
    rest = [a for a in args if a != "--push"]
    msg = " ".join(rest[1:]) if (rest and rest[0] == "-m") else (" ".join(rest) or "checkin")
    sys.path.insert(0, TOOLS)
    from checkin_logic import is_relic, checkin_blockers
    g = lambda a: subprocess.run(["git", "-C", ROOT] + a, capture_output=True, text=True, encoding="utf-8", errors="replace")
    gate_green = (cmd_gate([]) == 0)
    paths = [ln[3:].strip().strip('"') for ln in g(["status", "--porcelain", "-uall"]).stdout.splitlines() if ln.strip()]
    relics = [p for p in paths if is_relic(p)]
    behind = 0
    u = g(["rev-list", "--count", "HEAD..@{u}"])
    if u.returncode == 0 and u.stdout.strip().isdigit():
        behind = int(u.stdout.strip())
    blockers = checkin_blockers(gate_green, behind, relics)
    if blockers:
        print("checkin BLOCKED — tree/remote not pristine:")
        for b in blockers:
            print("  - " + b)
        if relics:
            print("  relics: " + ", ".join(relics[:12]))
        print("  (fix: run `lathe clean`, get the gates green, or pull the remote — then retry)")
        return 1
    g(["add", "-A"])
    c = g(["commit", "-m", msg])
    print(("committed: " + msg) if c.returncode == 0 else ((c.stdout + c.stderr).strip()[:200] or "nothing to commit"))
    if do_push:
        if g(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]).returncode != 0:
            print("checkin: no upstream configured — committed locally, not pushed."); return 0
        if re.search(r'ghp_[A-Za-z0-9]{20}|sk-[A-Za-z0-9]{20}|AKIA[0-9A-Z]{16}|-----BEGIN', g(["show", "HEAD"]).stdout):
            print("checkin: REFUSING to push — a secret-like token is in the commit."); return 1
        from lathe_config import pick
        remote = pick(os.environ.get("LATHE_REMOTE", ""), (_lathe_config().get("checkin") or {}).get("remote") or "", "")
        p = g(["push"] + ([remote, "HEAD"] if remote else []))   # configured remote, else the tracked upstream
        print((p.stdout + p.stderr).strip()[:300]); return p.returncode
    print("(committed locally — add --push to push to the upstream)")
    return 0


def _lathe_config():
    """Load the optional single config file: env LATHE_CONFIG, else ./lathe.config.json, else ~/.lathe/config.json.
    Parsing is harness-built (lathe_config.parse_config, gated+pinned)."""
    for p in (os.environ.get("LATHE_CONFIG"), os.path.join(ROOT, "lathe.config.json"),
              os.path.join(os.path.expanduser("~"), ".lathe", "config.json")):
        if p and os.path.exists(p):
            try:
                sys.path.insert(0, TOOLS)
                from lathe_config import parse_config
                return parse_config(open(p, encoding="utf-8").read())
            except Exception:
                return {}
    return {}


def _apply_config_env(cfg):
    """Map config -> env with setdefault so an explicit env var ALWAYS overrides the file (env > config > default).
    Secrets (e.g. a push token) are NEVER read from the file — use env / the git credential helper."""
    _m = {("analyst", "url"): "HARNESS_CLAUDE_URL", ("analyst", "model"): "HARNESS_ANALYST_MODEL",
          ("implementer", "url"): "LOCAL_OPENAI_URL", ("implementer", "model"): "HARNESS_MODEL",
          ("tries", None): "LATHE_TRIES"}
    for (sec, key), env in _m.items():
        node = cfg.get(sec)
        v = node if key is None else (node.get(key) if isinstance(node, dict) else None)
        if isinstance(v, (str, int)) and str(v):
            os.environ.setdefault(env, str(v))


def main(argv):
    os.environ["LATHE_VALIDATE_PLAN"] = "1"    # FORCE (not setdefault): a stale/hostile env var must not disable plan-as-data validation — same reason the validator path below is forced
    os.environ["LATHE_VALIDATOR_PY"] = os.path.join(TOOLS, "plan_validator.py")   # FORCE the trusted validator (a stale/hostile env var must not redirect it)
    _apply_config_env(_lathe_config())         # config file -> env defaults (an explicit env var still overrides)
    if not argv or argv[0] in ("help", "-h", "--help"):
        print(__doc__); return 0
    cmd, rest = argv[0], argv[1:]
    table = {
        "build": cmd_build, "do": cmd_do, "chat": cmd_chat, "auto": cmd_auto,
        "gate": cmd_gate, "review": cmd_review, "status": cmd_status,
        "board": cmd_board, "verify": cmd_verify, "selftest": cmd_selftest,
        "decompose": cmd_decompose, "checkpoint": cmd_checkpoint, "run": cmd_run,
        "metrics": cmd_metrics, "plans": cmd_plans, "dups": cmd_dups, "whatis": cmd_whatis,
        "clean": cmd_clean, "wait": cmd_wait, "resume": cmd_resume, "waiting": cmd_waiting,
        "report": cmd_report, "issues": cmd_issues, "logs": cmd_logs, "lint-spec": cmd_lint_spec,
        "flow": cmd_flow, "map": cmd_map, "checkin": cmd_checkin, "agent": cmd_agent, "ack": cmd_ack, "trace": cmd_trace,
    }
    if cmd in table:
        return table[cmd](rest)
    # bare `lathe "<goal>"` -> treat the whole argv as a goal
    return cmd_do(argv)


def _cli():                                    # console-script entry point (see pyproject.toml)
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
