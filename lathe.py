#!/usr/bin/env python
"""lathe - the command-line interface to the Lathe harness.

Treat AI code generation like a build system, not a conversation. This CLI is the user/agent surface
over the harness: draft a spec, build it on the local model under gates, run quality gates, get a CE
review, and inspect the autonomous board - all reproducible and pinned.

Usage:
  lathe do "<goal>"            THE canonical one-shot: intake -> draft a spec -> build -> gate -> pin
  lathe "<goal>"               labeled shorthand for `lathe do "<goal>"` (a multi-word bare goal routes to do)
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
  lathe agent bucket [name]    the persona library grouped by when-to-invoke bucket
  lathe agent rate --all [N]   grade every agent (field probe + judge -> 0-10; resumable, skips rated)
  lathe clarify "<goal>"       requirements LIAISON: interrogate you for clarity (inputs/outputs/success/
                               edge/non-goals) BEFORE thinking; emits CLARIFIED_GOAL.md to feed do/sdlc
  lathe sdlc "<goal>" [--out]  SDLC authoring: analyst writes UC->BR->FR->TS (ID-traced); the RTM gate
                               refuses orphans/dangling refs; emits REQUIREMENTS.md + a CRITERIA block
  lathe selftest               exercise every capability and report PASS/FAIL
  lathe help                   this help

Two roles, both PLUGGABLE (any OpenAI-compatible endpoint — the analyst need not be Claude):
  THINKER  (analyst) drafts + repairs the spec   -> HARNESS_CLAUDE_URL
  BUILDER  (implementer) writes the code          -> LOCAL_OPENAI_URL
Env: LATHE_MODEL (default openai:local), LATHE_TRIES (default 3).
"""
import os
import sys
import json
import glob
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
INNER = os.path.join(ROOT, "projects", "agentic-harness")
TOOLS = os.path.join(INNER, "tools")
# Per-goal build workspaces are OUTPUTS — they must NOT live inside the repo. Default them OUTSIDE it so the
# code tree stays clean and they can never be checked into the hub. Absolute + forward slashes so it's an
# absolute path everywhere (os.path.join(ROOT, ws) then correctly discards ROOT) and safe inside a generated
# plan's OUT_DIR string literal. Override with LATHE_WORKSPACE_ROOT.
WORKSPACE_ROOT = (os.environ.get("LATHE_WORKSPACE_ROOT") or "C:/lathe-workspaces").replace("\\", "/").rstrip("/")
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


def _run(cmd, cwd=ROOT, timeout=None, env=None):
    """Run a subprocess inheriting this terminal's stdout/stderr so the user sees live output.
    timeout (seconds) bounds the call; on expiry the child is killed and 124 is returned (GNU-timeout
    convention) so a wedged rig/engine can't freeze the CLI forever — the documented '503 for minutes while
    loading a 20GB model' is exactly this. Default ceiling from LATHE_RUN_TIMEOUT (unset = unbounded, so
    interactive commands aren't surprised); pass an explicit timeout for unattended paths."""
    import subprocess
    timeout = timeout or _RUN_TIMEOUT
    try:
        return subprocess.run(cmd, cwd=cwd, timeout=timeout, env=env).returncode
    except subprocess.TimeoutExpired:
        sys.stderr.write("\nlathe: command exceeded %ss timeout — killed (raise LATHE_RUN_TIMEOUT or pass --timeout)\n" % timeout)
        return 124


def _run_engine(plan, model, tries, label=""):
    """Run the engine through the shared engine_runner so EVERY build command (build/run/selftest) gets the
    same three things as `do`: the live stream, the plain-English interpretation, and a BUILD_TRACE.md next to
    the plan. Falls back to _run (inherit stdout) if engine_runner can't load."""
    try:
        er = _tool("engine_runner")
        _stream = os.environ.get("LATHE_STREAM_ENGINE", "1") not in ("0", "off", "false")
        _trace = os.path.join(os.path.dirname(os.path.abspath(plan)), "BUILD_TRACE.md")
        rc, _out = er.run_engine([PY, ENGINE, plan, str(model), str(tries)], cwd=ROOT, env=dict(os.environ),
                                 timeout=(_RUN_TIMEOUT or 900), trace_path=_trace, stream=_stream,
                                 label=label or ("build — %s on %s" % (os.path.basename(plan), model)))
        return rc
    except Exception as _e:
        sys.stderr.write("(engine_runner unavailable, plain run: %s)\n" % _e)
        return _run([PY, ENGINE, plan, str(model), str(tries)])


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
    as_json = "--json" in args                            # PR#1 CLI-review #3: stable machine-readable output for CI
    pos = [a for a in args if a != "--json"]
    if not pos:
        print("usage: lathe build <plan> [model] [tries] [--json]"); return 2
    plan = _resolve_plan(pos[0])
    if not os.path.isfile(plan):
        print("plan not found: %s" % pos[0]); return 2
    if not _validate_plan_file(plan):
        return 2
    model = pos[1] if len(pos) > 1 else MODEL             # honor `lathe build <plan> [model] [tries]`
    tries = pos[2] if len(pos) > 2 else TRIES
    if as_json:
        # capture the engine's ===METRICS_JSON=== block and print ONLY that stable object (no PASS/REUSED
        # column drift for a wrapper to misparse); exit code reflects build_ok.
        import subprocess, re, json as _json
        r = subprocess.run([PY, ENGINE, plan, model, tries], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=_RUN_TIMEOUT or None)
        m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", r.stdout or "", re.S)
        if not m:
            print(_json.dumps({"build_ok": False, "error": "no metrics emitted", "rc": r.returncode})); return r.returncode or 1
        obj = _json.loads(m.group(1))
        print(_json.dumps(obj))
        return 0 if obj.get("build_ok") else 1
    print("> building %s on %s (best-of-%s)..." % (os.path.basename(plan), model, tries))
    rc = _run_engine(plan, model, tries)
    if rc == 0:
        return 0
    # DEFAULT FEEDBACK LOOP (owner rule): when the implementer fails, the HIGHER model adjusts the SPEC —
    # in every workflow, not just `lathe do`. One bounded auto-repair round: analyst rewrites the plan from
    # its banked failure evidence, then the SAME implementer retries the repaired spec. Opt out with
    # LATHE_REPAIR=0 (or --json, whose primitive-only output is a compat guarantee).
    if os.environ.get("LATHE_REPAIR", "on").strip().lower() in ("0", "false", "no", "off"):
        return rc
    # never "repair" an environment problem — the gate itself was inoperative, the spec is not at fault
    try:
        import json as _json
        _last = _json.loads(open(os.path.join(ROOT, "metrics", "runs.jsonl"), encoding="utf-8").read()
                            .strip().splitlines()[-1])
        if _last.get("plan") == os.path.basename(plan) and any(
                "INOPERATIVE" in str(a.get("gate", "")) for a in (_last.get("per_artifact") or [])):
            print("> auto-repair SKIPPED: the gate was INOPERATIVE (environment) - fix the env and rebuild")
            return rc
    except Exception:
        pass
    print("> build failed - invoking the analyst to adjust the spec from banked evidence (LATHE_REPAIR=0 to disable)...")
    live = _load_autonomy()
    _mfx = _manifest()
    if _mfx is not None:
        try:
            import pricebook as _pb
            _am = os.environ.get("HARNESS_ANALYST_MODEL", "sonnet")
            live._reqspec.USAGE_HOOK = lambda role, u: _mfx.record_usage(
                "analyst", u.get("prompt_tokens", 0), u.get("completion_tokens", 0), 1,
                "measured" if u.get("total_tokens") else "unmetered", _pb.price_for(_am))
        except Exception:
            pass
    try:
        new_text, _fb = live.repair_plan(plan)
    except ValueError as e:
        print("> auto-repair skipped: %s" % e)
        return rc
    if not new_text.strip():
        print("> auto-repair skipped: analyst returned no rewrite")
        return rc
    v = _tool("plan_validator").is_valid_plan(new_text)
    if not (v.get("ok") if isinstance(v, dict) else v):
        print("> auto-repair REJECTED - rewritten plan failed validation: %s"
              % (v.get("reason") if isinstance(v, dict) else "invalid"))
        return rc
    rplan = os.path.splitext(plan)[0] + "_repaired.py"
    with open(rplan, "w", encoding="utf-8") as f:
        f.write(new_text)
    if _mfx is not None:
        try:
            _mfx.append_contributor({"id": "analyst-repair", "role": "analyst", "kind": "model",
                                     "action": "auto-repair: rewrote spec of %s -> %s after failed build" % (
                                         os.path.basename(plan), os.path.basename(rplan)), "status": "ok"})
        except Exception:
            pass
    print("> repaired spec -> %s ; rebuilding on %s..." % (os.path.relpath(rplan, ROOT), model))
    return _run_engine(rplan, model, tries, label="repair rebuild")


def _goal_board():
    """An ISOLATED board for one-shot goals, so `lathe do`/`chat` draft+build the user's goal instead of
    draining the standing autonomy self-feed board (`lathe auto`'s pending tasks). Fresh per call."""
    import tempfile
    fd, path = tempfile.mkstemp(prefix="lathe_goal_", suffix=".db")
    os.close(fd)
    os.remove(path)                                          # mkstemp made an empty file; board.init creates the schema
    return path


def _intake_panel(goal, k=3):
    """A1: pick a goal-matched PANEL of expert lenses for the intake — REUSES the same decider the planner
    already uses (agent_router.select_agents_for_goal over agents/catalog.json), with the CE floor. Returns
    persona names (token-lean; no body fetch). The panel gives well-rounded questions from diverse viewpoints;
    a single moderator pass (the intake analyst call) merges them. Best-effort -> [] on any failure."""
    try:
        import json as _json
        if TOOLS not in sys.path:
            sys.path.insert(0, TOOLS)
        cat = _json.load(open(os.path.join(INNER, "agents", "catalog.json"), encoding="utf-8"))
        ents = cat.get("agents", [])
        # E3: the decider is lexical by default (free); LATHE_DECIDER_MODE=semantic|auto uses the analyst to
        # rank by MEANING (semantic_decider.decide, honest about which path ran). Same behavior as before when
        # unset, so no cost regression.
        from semantic_decider import decide as _decide
        names, _how = _decide(goal, [(e["name"], e.get("capability", "")) for e in ents], k)
        try:
            from persona_market import ensure_ce_floor
            _ce = [e["name"] for e in ents if e.get("source", "").startswith("EveryInc")]
            names = ensure_ce_floor(names, _ce, "correctness-reviewer")
        except Exception:
            pass
        # E1: guarantee the prompt-architect MODERATOR lens is in the room (crafts the brief from the panel).
        try:
            from panel_floor import with_architect
            names = with_architect(names)
        except Exception:
            pass
        return [n for n in names if n][:max(k, 1) + 1]   # +1 so the architect never displaces a matched lens
    except Exception:
        return []


def _goal_discovery(goal, live, panel):
    """DISCOVERY — the stage BEFORE assumptions: interrogate the GOAL ITSELF (why, who, what does 'done well'
    mean, the real intent) so everything downstream is grounded in what the user ACTUALLY wants — not just
    implementation gap-filling. The analyst generates the questions; the CLI asks them; the answers ENRICH the
    goal that then drives the assumption pass + the spec. Non-interactive stdin -> skip (never hang). Returns
    (enriched_goal, [(q,a)...])."""
    # OWNED by the dedicated requirements-liaison persona (the goal's first interrogator) — comprehensive
    # discovery across ALL dimensions, not just "why". It hands a sharp understanding to the assumption pass.
    import re                                             # BUGFIX: was never imported here; every re.* below threw
    #                                                        NameError that the broad except swallowed -> discovery
    #                                                        was silently DEAD on every run. This restores it.
    _persona = ""
    try:
        _lp = os.path.join(INNER, "ce_personas", "requirements-liaison.md")
        if os.path.exists(_lp):
            _persona = open(_lp, encoding="utf-8").read()
    except Exception:
        _persona = ""
    _pl = ("Other experts in the room: %s. " % ", ".join(panel)) if panel else ""
    _ask = ("%s\n\n---\n%sYou are the FIRST mind this goal meets. Interrogate it for clarity BEFORE any design "
            "or assumptions. The user's goal, verbatim:\n\n  %s\n\nProduce the FEWEST, highest-signal clarifying "
            "questions that most reduce ambiguity — enough to COMPLETE the discovery. Cover, as relevant: the "
            "real purpose/intent and audience; inputs; outputs and what 'done well' looks like; success/"
            "acceptance criteria; constraints (platform, offline, size, performance, security); edge cases; and "
            "explicit NON-GOALS. Ask only what you cannot safely infer; never more than 7. Where the answer "
            "space is bounded, EMBED the choices inline as '[options: A | B | C]'. Reply with ONLY a JSON array "
            "of question strings (each may contain an [options: ...] tail), nothing else." % (_persona, _pl, goal))
    def _parse_qs(_raw):
        import json as _json
        import re
        s = (_raw or "").strip()
        s = re.sub(r"^```[a-zA-Z]*", "", s).strip()          # strip a ```json fence the analyst may wrap it in
        s = re.sub(r"```$", "", s).strip()
        _mm = re.search(r"\[.*\]", s, re.DOTALL)
        if not _mm:
            return []
        try:
            _arr = _json.loads(_mm.group())
        except Exception:
            return []
        return [q.strip() for q in _arr if isinstance(q, str) and q.strip()][:5]

    questions, raw = [], ""
    for _try in range(2):                                    # one retry: a slow/timed-out analyst must NOT silently drop discovery
        try:
            raw = live._reqspec.request_spec(_ask) or ""
        except Exception as _de:
            sys.stderr.write("discovery: analyst call failed (%r)\n" % (_de,)); raw = ""
        questions = _parse_qs(raw)
        if questions:
            break
    if not questions:
        # NEVER a silent skip (owner mandate: nothing overlooked). Say plainly what happened.
        if raw.strip():
            print("  discovery: got an analyst reply but could not extract clarifying questions from it — this is "
                  "a parse bug, NOT a clean skip. Reply head: %r" % raw.strip()[:140])
        else:
            print("  discovery: the analyst returned nothing for clarifying questions (call may have timed out).")
        print("  discovery: proceeding with the goal as written — no clarifying questions were captured.")
        return goal, []
    print("\n  " + "=" * 66)
    print("  First — help me understand what you REALLY want (the WHY behind this),")
    print("  so I don't build the wrong thing. Answer in your words, or Enter to skip one.")
    print("  " + "=" * 66)
    qa = []
    _noninteractive = False
    for _i, _q in enumerate(questions, 1):
        _om = re.search(r"\[option[s]?:\s*([^\]]+)\]", _q, re.I)      # options between [ ]
        _dm = re.search(r"\(default:\s*([^)]+)\)", _q, re.I)         # a recommended default, if any
        _qtext = re.sub(r"\s*\(default:[^)]+\)\s*", " ",
                        re.sub(r"\s*\[option[s]?:[^\]]+\]\s*", " ", _q, flags=re.I), flags=re.I).strip()
        _qtext = re.sub(r"^\d+[.)]\s*", "", _qtext)                  # drop any leading "1." the persona added
        _opts = [o.strip() for o in _om.group(1).split("|") if o.strip()] if _om else []
        _default = _dm.group(1).strip() if _dm else ""
        print("\n  --- question %d of %d ---" % (_i, len(questions)))
        print("  %s" % _qtext)
        if _opts:
            print("  options:  " + "   /   ".join(_opts))
        try:
            _ans = input("  > %s" % (("[Enter = %s]  " % _default) if _default else "")).strip()
        except (EOFError, KeyboardInterrupt):
            _noninteractive = True
            break
        if not _ans and _default:                                    # Enter accepts the recommended default
            _ans = _default
        if _ans:
            qa.append((_qtext, _ans))
    if _noninteractive:
        print("\n  ! No interactive terminal — skipping goal discovery (the build won't know your deeper intent).\n")
        return goal, []
    if not qa:
        return goal, []
    print("\n  intake: captured %d answer(s) about your intent — folding them into the goal.\n" % len(qa))
    _block = "\n\nWHAT THE USER ACTUALLY WANTS (from discovery — treat these as the real intent):\n" + "\n".join(
        "- Q: %s\n  A: %s" % (q, a) for q, a in qa)
    return goal + _block, qa


class IntakeAbort(Exception):
    """Raised when `lathe do` cannot confirm material input (no interactive terminal) and the caller did NOT
    explicitly opt into building on defaults (--assume). The harness REFUSES to build on guessed material
    input — the input-first guarantee is not overridable by the absence of a terminal."""


def _goal_intake(goal, ws, live, mf, interactive=False):
    """MASTER_PLAN A: INTAKE before drafting. FIRST a DISCOVERY interview interrogates the goal's real intent
    (why/who/success); THEN an analyst pass surfaces the UNSTATED assumptions the (enriched) goal leaves open —
    the choices an implementer would otherwise GUESS — and the user confirms them. So the spec is built on what
    the user actually wants, not on the harness's own guesses. Returns (augmented_goal, assumptions)."""
    assumptions = []
    panel = _intake_panel(goal)                          # A1: goal-matched expert lenses (reused decider)
    # STAGE 0 — DISCOVERY: understand the goal + real intent BEFORE surfacing implementation assumptions.
    goal, _discovery_qa = _goal_discovery(goal, live, panel)
    _panel_line = ("\n\nINTERVIEW PANEL — surface the assumptions each of these experts would flag, then MERGE "
                   "them (dedupe): %s.\n" % ", ".join(panel)) if panel else ""
    try:
        _al = _tool("assumption_logic")
        _ap = os.path.join(INNER, "ce_personas", "assumption-auditor.md")
        _persona = open(_ap, encoding="utf-8").read() if os.path.exists(_ap) else ""
        _ask = ("%s%s\n\n--- GOAL TO AUDIT ---\n%s\n\nList the UNSTATED assumptions this goal leaves open — the "
                "specific choices an implementer must make that the goal never pins down (behaviour, controls, "
                "physics, edge cases, win/lose, defaults, scope). One per line, EXACTLY this format, nothing else:\n"
                "[assumption | high|med|low | <category>] <the specific unstated choice + the default you'd take>\n"
                "Only real ambiguities that change the result. No preamble, no trailing prose.") % (_persona, _panel_line, goal)
        raw = live._reqspec.request_spec(_ask)
        assumptions = _al.parse_assumptions(raw or "")
    except Exception as e:
        sys.stderr.write("intake: assumption pass skipped (%r)\n" % (e,))
    if panel:
        print("  intake panel: %s" % ", ".join(panel))
    if mf is not None:
        try: mf.set_front_end(ran=True, clarify=("interactive" if interactive else "assume-and-record"),
                              assumptions=assumptions)
        except Exception: pass
    if not assumptions:
        print("  intake: no material assumptions surfaced (goal is specific)")
        return goal, [], panel
    _hi = sum(1 for a in assumptions if a.get("materiality") == "high")
    print("  intake: surfaced %d assumption(s) (%d high) — these are the choices your goal left open:" % (len(assumptions), _hi))
    for a in assumptions:
        print("    [%s|%s] %s" % (a["materiality"].upper(), a["category"], a["text"][:90]))
    # INPUT-FIRST (the fundamental fix): a build must NOT proceed on assumptions the harness guessed and then
    # rubber-stamped ITSELF — bad input -> bad output, no model or gate can save that. So when the goal left
    # MATERIAL (high/med) choices open, INTERVIEW the user to get the input right BEFORE the analyst drafts the
    # spec. This is the DEFAULT now, not an opt-in flag. isatty() is unreliable cross-platform (backwards on
    # MSYS), so we don't guess: we just prompt, and if stdin has no interactive input the FIRST prompt EOFs and
    # we fall back to auto-accept + a LOUD warning (never hangs). Autonomy skips intake entirely via --assume.
    _material = [a for a in assumptions if a.get("materiality") in ("high", "med")]
    _did_interview = False
    if _material:
        print("\n  " + "=" * 66)
        print("  Before I build, confirm the choices your goal left open.")
        print("  Bad input -> bad output, so nothing gets built until these are right.")
        print("  For each: press Enter to keep it, type what you want instead, or 'd' to drop.")
        print("  " + "=" * 66)
        _low = [a for a in assumptions if a.get("materiality") not in ("high", "med")]
        _noninteractive = {"v": False}
        _prog = {"i": 0, "n": len(_material)}
        import re as _re

        def _resp(a):
            try:
                _prog["i"] += 1
                _txt = (a.get("text") or "").strip()
                # split the "[options: A | B | C]" tail off the decision so BOTH are shown in full (no truncation)
                _m = _re.search(r"\[option[s]?:\s*(.+?)\]?\s*$", _txt, _re.I)
                _decision = (_txt[:_m.start()] if _m else _txt).strip().rstrip(".")
                _opts = [o.strip() for o in _m.group(1).split("|") if o.strip()] if _m else []
                _imp = "HIGH IMPACT" if a.get("materiality") == "high" else "matters"
                print("\n  --- choice %d of %d   [%s | %s] ---" % (_prog["i"], _prog["n"], _imp, a.get("category", "")))
                print("  %s." % _decision)
                if _opts:
                    print("  options:  " + "   /   ".join(_opts))
                return input("  Keep it? [Enter = yes]  or type your choice (or 'd' to drop):  ").strip()
            except (EOFError, KeyboardInterrupt):            # no interactive stdin -> note it, accept (never hang)
                _noninteractive["v"] = True
                return ""
        try:
            _ic = _tool("intake_confirm")
            _kept = _ic.confirm_assumptions(_material, _resp)
            assumptions = _kept + _low                       # material ones handled; low-impact ones recorded as-is
        except Exception as e:
            sys.stderr.write("intake: interview skipped (%r)\n" % (e,))
            _noninteractive["v"] = True
        if _noninteractive["v"]:
            # HARD STOP (owner mandate): the harness must NOT let the absence of a terminal become a silent
            # override of its own input-first step. Building on guessed material choices is exactly the
            # bad-input->bad-output failure the interview exists to prevent. Refuse — do not auto-accept.
            raise IntakeAbort(len(_material))
        else:
            _did_interview = True
            print("\n  intake: %d material choice(s) confirmed — the spec will be built to THESE.\n" % len(_kept))
    interactive = _did_interview                             # reflect what actually happened in the manifest label
    # confirmed: assume-and-record auto-accepts (recorded intent); interactive keeps only what the user OK'd.
    _confirmed = [a["text"] for a in assumptions]
    if ws:
        _wsabs = os.path.join(ROOT, ws.replace("/", os.sep))
        try:
            _lines = ["# ASSUMPTIONS — surfaced by intake (%s)" % ("interactive" if interactive else "assume-and-record"),
                      "", "Goal: %s" % goal, ""]
            _lines += ["- [%s | %s] %s" % (a["materiality"].upper(), a["category"], a["text"]) for a in assumptions]
            open(os.path.join(_wsabs, "ASSUMPTIONS.md"), "w", encoding="utf-8").write("\n".join(_lines) + "\n")
        except Exception:
            pass
        # A6: emit the ledger in the EXISTING assumption-gate format (goal-scope, keyed "*") so the engine's
        # assumption gate — now covering the artifact lane — reads + enforces it. Reuses assumption_logic's
        # {ledger, confirmed} shape; no new gate.
        try:
            import json as _json
            _led = {"*": {"scope": "goal", "digest": "goal", "ledger": assumptions, "confirmed": _confirmed}}
            open(os.path.join(_wsabs, ".assumptions.json"), "w", encoding="utf-8").write(_json.dumps(_led, indent=1))
        except Exception:
            pass
    _block = ("\n\nRESOLVED ASSUMPTIONS (the goal was ambiguous — BUILD TO THESE EXACTLY, do not silently "
              "re-decide them):\n" + "\n".join("- %s" % a["text"] for a in assumptions))
    return goal + _block, assumptions, panel


def _do_targeted(goal, spec_for):
    """`lathe do "<goal>" --for <class|all>` — draft spec variant(s) FOR the requested model class(es),
    save them in the goal's workspace, and BUILD one: the requested class (single) or the variant matching
    the configured implementer ('all'). Builds go through cmd_build, so the default feedback loop applies."""
    live = _load_autonomy()
    _mf = _manifest()
    if _mf:
        _mf.set_goal(goal)
        try:
            import pricebook as _pb
            _am = os.environ.get("HARNESS_ANALYST_MODEL", "sonnet")
            live._reqspec.USAGE_HOOK = lambda role, u: _mf.record_usage(
                "analyst", u.get("prompt_tokens", 0), u.get("completion_tokens", 0), 1,
                "measured" if u.get("total_tokens") else "unmetered", _pb.price_for(_am))
        except Exception:
            pass
    ws, focus = _goal_workspace(goal)
    if not ws:
        print("do --for: goal_router unavailable"); return 1
    os.makedirs(os.path.join(ROOT, ws.replace("/", os.sep)), exist_ok=True)
    classes = ["frontier", "local-large", "local-small"] if spec_for == "all" else [spec_for]
    print("> drafting spec variant(s) for: %s" % ", ".join(classes))
    print("  workspace: %s   (focus: %s)\n" % (ws, focus))
    made = {}
    for cls in classes:
        p = live.draft_spec_for(goal, focus, ws, cls)
        print("  %-12s %s" % (cls, os.path.relpath(p, ROOT) if p else "DRAFT FAILED (analyst/validator)"))
        if p:
            made[cls] = p
    if not made:
        return 1
    if spec_for == "all":
        try:
            _build_cls = _tool("model_class").model_class(os.environ.get("LATHE_MODEL", "openai:local"))
        except Exception:
            _build_cls = "local-small"
        target = made.get(_build_cls) or list(made.values())[0]
        print("\n> building the %s variant (configured implementer)..." % _build_cls)
    else:
        target = made[spec_for]
        print("\n> building the %s variant..." % spec_for)
    if _mf:
        try:
            _mf.set_workspace(ws)
            _mf.set_selection("goal-router", [], [focus] + ["spec-for:" + c for c in classes] + [ws])
        except Exception:
            pass
    return cmd_build([target])


def _goal_workspace(goal):
    """(workspace_abs, focus) for a goal — harness-built goal_router decides both. The workspace is a
    per-goal folder under WORKSPACE_ROOT (OUTSIDE the repo by default, e.g. C:/lathe-workspaces/goals/
    <slug>_<stamp>/) so a goal's plan, module, artifacts and fail bank accumulate in ONE clean place —
    never inside the code tree. Falls back to (None, 'helper') = legacy behavior if the router is unavailable."""
    try:
        gr = _tool("goal_router")
        import datetime
        stamp = datetime.datetime.now().strftime("%m%d-%H%M%S")   # short: year is noise at project scale
        # owner design: the folder NAME says WHAT is being built and WITH WHICH model —
        # e.g. goals/conway-game-life-canvas_9b_0708-122704
        try:
            slug = gr.short_goal(goal) + "_" + gr.model_abbrev(os.environ.get("LATHE_MODEL", "openai:local"))
        except AttributeError:                                    # pre-v2.29 goal_router build
            slug = gr.slugify_goal(goal)
        ws = WORKSPACE_ROOT + "/" + gr.workspace_rel(slug, stamp)   # absolute, OUTSIDE the repo
        return ws, gr.pick_focus(goal)
    except Exception as e:
        print("  (goal_router unavailable - building in tools/: %s)" % e)
        return None, "helper"


_ADV_DOC_FILES = {"ADVOCATE.md", "GOAL.md", "README.md", "PROJECT.md", "ASSUMPTIONS.md", "BUILD_TRACE.md", "MANIFEST.json"}


def _advocate_artifact_summary(ws_abs, budget=12000):
    """Assemble what the Advocate reviews at delivery: the DELIVERED artifact files (not our own scaffolding
    docs). Reads the workspace's code/markup, each under a filename header, truncated to a budget. Best-effort:
    an unreadable file is noted, never fatal."""
    if not ws_abs or not os.path.isdir(ws_abs):
        return ""
    exts = (".html", ".htm", ".js", ".mjs", ".css", ".py", ".ts", ".json", ".md", ".txt")
    # Review BOTH the plan/spec+tests (top-level plan_*.py) AND the actually-shipped artifact (in _artifacts/),
    # so the Advocate judges intent against what was really built, not just the prompt that asked for it.
    paths = []
    try:
        for n in sorted(os.listdir(ws_abs)):
            if os.path.isfile(os.path.join(ws_abs, n)) and not n.startswith(".") and n not in _ADV_DOC_FILES \
                    and n.lower().endswith(exts):
                paths.append((n, os.path.join(ws_abs, n)))
        _art = os.path.join(ws_abs, "_artifacts")
        if os.path.isdir(_art):
            for n in sorted(os.listdir(_art)):
                if os.path.isfile(os.path.join(_art, n)) and n.lower().endswith(exts):
                    paths.append(("_artifacts/" + n, os.path.join(_art, n)))
    except OSError:
        return ""
    parts, used = [], 0
    for label, p in paths:
        if used >= budget:
            parts.append("... (%d more file(s) not shown)" % (len(paths) - len([x for x in parts if x.startswith("=== ")])))
            break
        try:
            body = open(p, encoding="utf-8", errors="replace").read()
        except Exception as e:
            parts.append("=== %s === (unreadable: %s)" % (label, e)); continue
        chunk = body[: max(600, budget - used)]
        parts.append("=== %s (%d bytes) ===\n%s" % (label, len(body), chunk))
        used += len(chunk)
    return "\n\n".join(parts) if parts else "(workspace produced no reviewable artifact files)"


def _adv_step(charter, stage, summary, ws_abs, context="", memory=None):
    """One Advocate checkpoint at a stage boundary: consult, PRINT the verdict, and LOG it to ADVOCATE_LOG.md
    so every call the Advocate makes across the run is on the record. Returns the verdict dict. Never raises.

    EVOLVING CONTEXT (owner mandate): the Advocate carries forward what it has already seen this run — each
    checkpoint is given its own prior observations, so its understanding compounds across steps like a user's
    would, instead of judging each stage cold."""
    prior = ""
    if memory:
        prior = ("\n\n=== WHAT YOU (the Advocate) HAVE ALREADY OBSERVED THIS RUN (carry it forward) ===\n" +
                 "\n".join("- [%s -> %s] %s" % (m["stage"], m["verdict"], (m["note"] or "")[:180]) for m in memory))
    try:
        _adv = _tool("advocate")
        v = _adv.checkpoint(charter, stage, summary, context=(context or "") + prior)
        line = _adv.render(v)
    except Exception as e:
        v = {"verdict": "concern", "note": "advocate step error: %s" % e, "route": ""}
        line = "[ADVOCATE: CONCERN] advocate step error: %s" % e
    print("  %-16s %s" % (stage + ":", line))
    if ws_abs:
        try:
            with open(os.path.join(ws_abs, "ADVOCATE_LOG.md"), "a", encoding="utf-8") as f:
                f.write("## checkpoint: %s\n%s\n\n" % (stage, line))
        except Exception:
            pass
    if memory is not None:
        memory.append({"stage": stage, "verdict": v.get("verdict", "?"), "note": v.get("note", "")})
    return v


def _adv_hold(stage, verdict, ws):
    """A VETO at any checkpoint HOLDS the run — not certified, non-zero exit, routed back."""
    print("\nHELD at '%s' - the Advocate VETOED as not serving the sponsor's intent:" % stage)
    print("  %s" % verdict.get("note", ""))
    if verdict.get("route"):
        print("  -> route it back to: %s" % verdict["route"])
    print("Not certified. Address the veto (or set LATHE_ADVOCATE=off to overrule) and re-run.")
    if ws:
        print("work-in-progress is in: %s" % ws)
    return 1


def cmd_do(args):
    # owner design (draft-time targeting): --for <frontier|local-large|local-small|all> drafts the spec(s)
    # FOR a chosen model class up front (not post-failure adaptation). 'all' saves all three variants in
    # the workspace and builds the one matching the configured implementer.
    spec_for = None
    args = list(args)
    _interactive = "--interactive" in args
    if _interactive:
        args = [a for a in args if a != "--interactive"]
    _no_intake = "--assume" in args or os.environ.get("LATHE_INTAKE", "").strip().lower() in ("0", "off", "no")
    if "--assume" in args:
        args = [a for a in args if a != "--assume"]
    if "--for" in args:
        _i = args.index("--for")
        spec_for = args[_i + 1].strip().lower() if _i + 1 < len(args) else ""
        del args[_i:_i + 2]
        _valid = ("frontier", "local-large", "local-small", "all")
        if spec_for not in _valid:
            print("usage: lathe do \"<goal>\" [--for frontier|local-large|local-small|all]"); return 2
    goal = " ".join(args).strip()
    if not goal:
        print("usage: lathe do \"<goal>\" [--for <class>|all]"); return 2
    if spec_for:
        return _do_targeted(goal, spec_for)
    _mf = _manifest()                                    # #19 M1: record the goal in the run manifest
    if _mf:
        _mf.set_goal(goal)
    live = _load_autonomy()
    # #59: the drafter loads its OWN request_spec instance (importlib), so the hook _manifest_begin bound to
    # the `import request_spec` module never saw draft calls -> analyst usage was silently uncounted and the
    # manifest claimed COMPLETE. Bind the hook on the instance the drafter actually calls.
    _draft_calls = {"n": 0}
    if _mf is not None:
        try:
            import pricebook as _pb
            _am = os.environ.get("HARNESS_ANALYST_MODEL", "sonnet")
            def _do_hook(role, u, _mf=_mf, _pb=_pb, _am=_am, _dc=_draft_calls):
                _dc["n"] += 1
                _mf.record_usage("analyst", u.get("prompt_tokens", 0), u.get("completion_tokens", 0), 1,
                                 "measured" if u.get("total_tokens") else "unmetered", _pb.price_for(_am))
            live._reqspec.USAGE_HOOK = _do_hook
        except Exception:
            pass
    ws, focus = _goal_workspace(goal)
    if ws:
        os.makedirs(os.path.join(ROOT, ws.replace("/", os.sep)), exist_ok=True)
        print("> drafting + building toward: %s" % goal)
        print("  workspace: %s   (focus: %s)\n" % (ws, focus))
    else:
        print("> drafting + building toward: %s\n" % goal)
    # MASTER_PLAN A: intake FIRST — surface the goal's unstated assumptions and feed them into drafting
    # (assume-and-record default; --interactive to confirm; --assume or LATHE_INTAKE=0 to skip).
    _build_goal, _assumptions, _panel = (goal, [], [])
    if not _no_intake:
        try:
            _build_goal, _assumptions, _panel = _goal_intake(goal, ws, live, _mf, interactive=_interactive)
        except IntakeAbort as _ab:
            _n = _ab.args[0] if _ab.args else "several"
            print("\n  " + "=" * 66)
            print("  REFUSED — %s material choice(s) need your confirmation and there is no" % _n)
            print("  interactive terminal to ask. The harness will not build on guessed input;")
            print("  that is the bad-input->bad-output failure the interview exists to stop.")
            print("  " + "=" * 66)
            print("  Do one of:")
            print("    - run `lathe do \"<goal>\"` in a real terminal and answer the questions, or")
            print("    - pass --assume to CONSCIOUSLY build on the recorded defaults (you own the guess).")
            print("\nno build — input was not confirmed.")
            return 2
        # A6: intake wrote the goal-scope ledger next to the plan → ARM the (now artifact-lane-covering)
        # assumption gate so the build reads + enforces it. assume-and-record auto-confirms, so it passes but
        # is recorded + enforceable; under STRICT or unconfirmed HIGH it blocks. setdefault: an explicit
        # env still wins.
        if _assumptions:
            os.environ.setdefault("LATHE_ASSUMPTION_GATE", "1")
        # A4: with --interactive, show the refined spec (goal + resolved assumptions) and require approval
        # BEFORE building. A revision request is folded into the build goal; a reject aborts. Logic is the
        # gated intake_confirm.approve_spec; here we supply an input()-backed responder.
        if _interactive:
            try:
                _ic = _tool("intake_confirm")
                _summary = "%s\n  Resolved assumptions:\n%s" % (
                    goal, "\n".join("   - %s" % a["text"] for a in _assumptions) or "   (none)")
                print("\n> SPEC FOR APPROVAL:\n  %s" % _summary.replace("\n", "\n  "))
                _ok, _rev = _ic.approve_spec(_summary, lambda s: input(
                    "\n  Approve this spec and build? [Enter=yes, 'n'=abort, or type a revision]: "))
                if not _ok and _rev is None:
                    print("do: aborted at spec approval (no build)."); return 0
                if _rev:
                    _build_goal = _build_goal + "\n\nUSER REVISION (apply this): " + _rev
                    print("  revision folded into the spec.")
            except Exception as e:
                sys.stderr.write("do: spec-approval step skipped (%r)\n" % (e,))
    elif _mf is not None:
        try: _mf.set_front_end(ran=False, clarify="skipped (--assume)", assumptions=[])
        except Exception: pass
    # F1: drop a human-readable GOAL.md (intent + resolved assumptions + panel) and README.md (layout) into the
    # workspace, so the folder says what it is at a glance. Best-effort — never blocks the build.
    if ws:
        try:
            _wd = _tool("workspace_docs")
            _wd.write_workspace_docs(os.path.join(ROOT, ws.replace("/", os.sep)), goal, _assumptions, _panel, focus)
        except Exception:
            pass
    # THE ADVOCATE (default-on): seed the sponsor's standing representative with the intent BEFORE the build.
    # It holds the charter (goal + discovery + confirmed choices) for the whole run and judges the delivery
    # against it. Off only if LATHE_ADVOCATE in {0,off,no}. Best-effort seeding — never blocks the build.
    _advocate_on = os.environ.get("LATHE_ADVOCATE", "on").strip().lower() not in ("0", "off", "no")
    _charter = None
    if _advocate_on:
        try:
            _adv = _tool("advocate")
            _charter = _adv.build_charter(goal, _build_goal, _assumptions)
            if ws:
                _ap = os.path.join(ROOT, ws.replace("/", os.sep), "ADVOCATE.md")
                open(_ap, "w", encoding="utf-8").write(_charter)
                open(os.path.join(ROOT, ws.replace("/", os.sep), "ADVOCATE_LOG.md"), "w",
                     encoding="utf-8").write("# Advocate log — every call the Advocate made this run\n\n")
            print("  advocate: seeded - I hold the sponsor's intent for this run.")
        except Exception as e:
            sys.stderr.write("advocate: seeding skipped (%r)\n" % (e,))
            _advocate_on = False
    _ws_abs = os.path.join(ROOT, ws.replace("/", os.sep)) if ws else None
    # UPSTREAM Advocate checkpoints (owner mandate: rule at EVERY step, not just delivery). The Advocate judges
    # the INPUT before a single line is built — a VETO here HOLDS the build, so bad intent/assumptions never
    # reach the model. This is where the leverage is: catching a wrong choice now beats vetoing a wrong build.
    _adv_mem = []                                            # the Advocate's evolving memory across this run's steps
    if _advocate_on and _charter:
        _disc = ""
        if "WHAT THE USER ACTUALLY WANTS" in _build_goal:
            _disc = _build_goal.split("WHAT THE USER ACTUALLY WANTS", 1)[1].strip()
        _v = _adv_step(_charter, "discovery", _disc or "(no discovery answers were captured)", _ws_abs,
                       context="Does the captured intent genuinely reflect the sponsor's goal, or is it thin/guessed/off-target?",
                       memory=_adv_mem)
        if _v.get("verdict") == "veto":
            return _adv_hold("discovery", _v, ws)
        _asum = "\n".join("- [%s|%s] %s" % ((a.get("materiality") or "").upper(), a.get("category", ""), a.get("text", ""))
                          for a in _assumptions) or "(no material assumptions)"
        _v = _adv_step(_charter, "assumptions", _asum, _ws_abs,
                       context="Are these the RIGHT choices for the sponsor's intent? Flag any that contradict the goal, "
                               "contradict each other, or that a sponsor would likely reject.",
                       memory=_adv_mem)
        if _v.get("verdict") == "veto":
            return _adv_hold("assumptions", _v, ws)
    _gdb = _goal_board()
    try:
        tr = live.run(_build_goal, max_plans=1, max_steps=4, build_one=True, max_repairs=2, db_path=_gdb,
                      focus=focus, out_dir=ws)
    finally:
        try: os.remove(_gdb)
        except OSError: pass
    # F4: if the build produced a genuine MULTI-FILE project (2+ code files), write a PROJECT.md map of the
    # code/docs/scripts/config layout. Physical reorganization is opt-in (LATHE_PROJECT_LAYOUT=1) so we never
    # silently move a built file and break a relative reference. Single-goal workspaces stay flat (no trigger).
    if _ws_abs and os.path.isdir(_ws_abs):
        try:
            _pl = _tool("project_layout")
            _pfiles = [os.path.join(_ws_abs, n) for n in os.listdir(_ws_abs)
                       if os.path.isfile(os.path.join(_ws_abs, n)) and not n.startswith(".")]
            if _pl.is_multifile_project(_pfiles):
                _apply = os.environ.get("LATHE_PROJECT_LAYOUT", "") in ("1", "true")
                _res = _pl.organize(_ws_abs, _pfiles, apply=_apply)
                print("  project layout: %s (%d files bucketed%s)" % (
                    os.path.relpath(_res["project_md"], ROOT) if _res.get("project_md") else "PROJECT.md",
                    len(_res.get("moves") or []), ", organized into subdirs" if _apply else " — set LATHE_PROJECT_LAYOUT=1 to move"))
        except Exception:
            pass
    if _mf is not None:
        try:
            # #59b: the goal-router's decision IS this run's selection — record it (was "- not reached -").
            # Owner design: also record WHICH model-class standard shaped the drafted spec.
            try:
                _cls = _tool("model_class").model_class(os.environ.get("LATHE_MODEL", "openai:local"))
            except Exception:
                _cls = "?"
            # A1/E2: record the intake PANEL personas (was permanently personas=[] for do).
            _mf.set_selection("goal-router+intake-panel" if _panel else "goal-router",
                              [{"id": p, "role": "intake-panel"} for p in _panel],
                              [focus, "spec-for:" + _cls] + ([ws] if ws else []))
        except Exception:
            pass
    if _mf is not None and _draft_calls["n"]:
        try:
            _nd = sum(1 for r in tr if r.get("step") == "planned")           # #59b: split draft vs repair
            _nr = sum(1 for r in tr if r.get("step") == "spec_repaired")
            _mf.append_contributor({"id": "analyst-draft", "role": "analyst", "kind": "model",
                                    "action": "%d draft + %d repair analyst call(s) via %s (focus=%s)" % (
                                        _nd, _nr,
                                        os.environ.get("HARNESS_ANALYST_MODEL", "analyst endpoint"), focus),
                                    "status": "ok"})
            _mf.add_model({"role": "analyst",
                           "model": os.environ.get("HARNESS_ANALYST_MODEL", "?"),
                           "endpoint": os.environ.get("HARNESS_CLAUDE_URL", "?")})
        except Exception:
            pass
    greens = sum(1 for r in tr if r["step"] == "ran_ok")
    for i, r in enumerate(tr, 1):
        print("  %2d. %s %s" % (i, r["step"], r.get("reason", "")))
    if _mf and ws:
        try: _mf.set_workspace(ws)                       # report: where this goal's outputs live
        except Exception: pass
    # THE ADVOCATE — enforced DELIVERY checkpoint: does what shipped still serve the sponsor's intent? A green
    # build proves the code RUNS; the Advocate proves it is the sponsor's THING. A VETO HOLDS certification: the
    # run is not reported DONE, and the route (rebuild/redraft/reassume/rediscover) says where to send it back.
    # Fail-safe: any Advocate trouble degrades to a printed CONCERN and never blocks a green build from shipping.
    if _advocate_on and _charter and greens:
        _artifact = _advocate_artifact_summary(_ws_abs) if _ws_abs else ""
        _v = _adv_step(_charter, "delivery", _artifact, _ws_abs,
                       context="The build finished with %d gated-green module(s). Judge the SHIPPED artifact and "
                               "its spec/tests against the charter." % greens,
                       memory=_adv_mem)
        if _v.get("verdict") == "veto":
            return _adv_hold("delivery", _v, ws)
    print("\n%s - %d module(s) built gated-green." % ("DONE" if greens else "no green build this run", greens))
    if greens and ws:
        print("everything for this goal is in: %s" % ws)
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
    # Full-verbose (heavy gates + every PASS line) is driven by the TOP-LEVEL command being `gate` (set in
    # run_spine), NOT here — so a gate step that runs as part of a `do`/build stays quiet + per-build.
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
        try:                                        # #43: user config steers the market — mandatory personas are
            from persona_spawn import persona_overrides       # injected on EVERY invocation; priority reweights picks
            _prio, _mand = persona_overrides()
            for _m in _mand:
                if _m in _ALL_LENSES and _m not in lenses:
                    lenses.append(_m)
                    print("mandatory persona (config): %s" % _m)
        except Exception:
            pass
        print("decider selected lenses for this code: %s" % ", ".join(lenses))
        _spawned = []
        try:                                        # D7: a needed-but-absent expert is FETCHED (license-gated) and injected
            from persona_spawn import auto_spawn_for_goal
            for _name, _md, _body in auto_spawn_for_goal(_sample, 2):
                lenses.append("@" + _md)            # hreview loads the fetched persona BODY from this path
                _spawned.append(_name)
                print("decider auto-spawned expert persona: %s (license-gated fetch -> %s)" % (_name, os.path.relpath(_md, ROOT)))
        except Exception as _sp_e:
            print("(persona auto-spawn skipped: %s)" % _sp_e)   # best-effort — never blocks the review floor
        # #19 M1: record the resolved selection in the run manifest (the #9 "who's in the room" payload).
        _mf = _manifest()
        if _mf:
            _mf.set_selection({"mode": "review-decider"},
                              [{"id": p, "role": "reviewer"} for p in (_picked + _spawned)], lenses)
        # #18 H3: record who-FIRED to the usage ledger so the grade loop (update_grades) has data. The lens
        # decider is word-match today; recording its picks makes the UCB1 visit-counts + grades real on the
        # live review path (was the missing recording end). Best-effort; never blocks the review.
        try:
            import persona_orchestrator as _po
            if _po.is_enabled():
                _considered = [{"name": p, "grade": 0.0, "picked": True, "reason": "review-decider"}
                               for p in (_picked + _spawned)]
                if _considered:
                    _po.record_run(_sample, _considered, [c["name"] for c in _considered], {},
                                   os.environ.get("LATHE_RUN_ID", "review"))
        except Exception:
            pass
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
    _lens_verdicts = {}
    for lens in lenses:
        print("\n========== lathe review: %s  (%d file%s) ==========" % (lens, len(files), "s" if len(files) != 1 else ""))
        _lrc = _run([PY, HREVIEW, lens] + list(files), cwd=INNER)
        rc |= _lrc
        # E4: a valid review (rc 0) means the lens ENGAGED; a nonzero rc is an inoperative/non-review (D5b).
        _lens_verdicts[lens] = "engaged" if _lrc == 0 else "inoperative"
    # E4: feed the outcomes back into persona ratings (opt-in) so the decider LEARNS which lenses reliably
    # deliver — not just the manual `agent rate`. EWMA-blended (one review nudges; a pattern moves it).
    if os.environ.get("LATHE_GRADE_FEEDBACK", "") in ("1", "true"):
        try:
            from outcome_feedback import record_review_outcomes
            from persona_spawn import load_ratings, save_rating
            _upd = record_review_outcomes(_lens_verdicts, load_ratings, save_rating)
            if _upd:
                print("\nreview outcomes -> ratings updated: %s" % ", ".join("%s=%.2f" % (k, v) for k, v in _upd.items()))
        except Exception as _fe:
            sys.stderr.write("review: grade-feedback skipped (%r)\n" % (_fe,))
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
    # last time the autonomy board did anything (max updated across tasks) — so we can flag a stale/idle queue
    # instead of implying work is live right now.
    _last_active = ""
    try:
        _stamps = [t.get("updated") or t.get("created") or "" for t in ts]
        _last_active = max([s for s in _stamps if s], default="")[:10]
    except Exception:
        pass
    _project = os.environ.get("LATHE_PROJECT", "agentic-harness")
    _plans = len(glob.glob(os.path.join(INNER, "plans", "*.py")))

    # Endpoints derived from the ACTUAL configured env (config file already applied at process start).
    _impl_url = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions")
    _anl_url = os.environ.get("HARNESS_CLAUDE_URL", "http://127.0.0.1:8787/v1/chat/completions")
    _hostport = lambda u: u.split("//", 1)[-1].split("/", 1)[0]
    _impl_model = os.environ.get("LATHE_MODEL", "openai:local")
    _anl_model = os.environ.get("HARNESS_ANALYST_MODEL", "sonnet")
    # what the config FILE asked for (before env setdefault could win) — lets us diagnose an env override.
    _cfg_impl = ""
    try:
        _cfgp = os.environ.get("LATHE_CONFIG") or os.path.join(ROOT, "lathe.config.json")
        if os.path.exists(_cfgp):
            _cfg = json.load(open(_cfgp, encoding="utf-8"))
            _cfg_impl = ((_cfg.get("implementer") or {}).get("url") or "")
    except Exception:
        pass

    def _up(url, path):                                  # returns (bool_up, human)
        r = _probe(url + path)
        return ("up" in str(r).lower(), str(r))
    _anl_up, _anl_h = _up(_anl_url.replace("/v1/chat/completions", ""), "/health")
    # the implementer speaks the OpenAI shape; /v1/models is the cheap liveness check (the claude proxy has it too)
    _impl_up, _impl_h = _up(_impl_url.replace("/chat/completions", ""), "/models")
    _same = _hostport(_impl_url) == _hostport(_anl_url)   # fable-as-both: one endpoint doing both roles

    _ready = _anl_up and _impl_up
    print("Lathe - %s" % ("READY to build" if _ready else "NOT ready (see below)"))
    print()
    print("  engine   (who writes your code)")
    print("    analyst      %-13s %-18s %s" % (_anl_model, _hostport(_anl_url),
          "up   thinker: specs + review" if _anl_up else "DOWN - start:  python claude_proxy.py --port 8787"))
    print("    implementer  %-13s %-18s %s" % (_impl_model, _hostport(_impl_url),
          ("up   (= analyst; one endpoint, both roles)" if _same else "up   coder: writes functions") if _impl_up else "DOWN"))
    if not _impl_up:
        # the #1 real cause: a persistent env var overriding the config's endpoint.
        if _cfg_impl and _hostport(_cfg_impl) != _hostport(_impl_url) and "LOCAL_OPENAI_URL" in os.environ:
            print("        ^ config wants %s but env LOCAL_OPENAI_URL forces this one." % _hostport(_cfg_impl))
            print("          clear it:  setx LOCAL_OPENAI_URL \"\"   then open a NEW shell")
        else:
            print("        ^ start the implementer endpoint, or point LOCAL_OPENAI_URL at a live one")
    _strict = os.environ.get("LATHE_STRICT", "").strip().lower() in ("1", "true", "yes", "on")
    print("    gates        %s" % ("STRICT - every enforcement gate armed" if _strict
          else "default - arm all:  $env:LATHE_STRICT=1   (PowerShell, this shell)"))
    print()
    print("  project  %s" % _project)
    print("    specs    %d plans -> %d pinned functions" % (_plans, pins))
    print("             a plan IS the spec; a pin is its accepted build, keyed by spec+tests+model.")
    print("             rebuild any plan at 0 model calls:  python lathe.py build <plan>")
    print("             see which model built each function:  python lathe.py trace <plan>")
    _q = counts.get("pending", 0) + counts.get("escalated", 0)
    _ip, _bl = counts.get("in_progress", 0), counts.get("blocked", 0)
    if _ip or _bl or _q:
        print("    board    %d in progress, %d blocked  (+%d queued)%s" % (_ip, _bl, _q,
              ("   last active %s" % _last_active) if _last_active else ""))
        print("             this is `lathe auto`'s self-generated practice queue, not your tasks.")
        print("             view:  python lathe.py board       clear the stale run:  python lathe.py board --reset")
    return 0 if _ready else 1


def cmd_board(args):
    b = _board()
    ts = b.list_tasks(b.DEFAULT_DB)
    if "--reset" in args:
        # Requeue orphaned work from an interrupted `lathe auto` run: in_progress/blocked -> pending.
        # Non-destructive (nothing deleted; `done`/`escalated` untouched) so `status` stops implying live work.
        _stuck = [t for t in ts if t["status"] in ("in_progress", "blocked")]
        for t in _stuck:
            b.set_status(t.get("id") or t.get("name"), "pending", reason="requeued by board --reset", db_path=b.DEFAULT_DB)
        print("requeued %d task(s) (in_progress/blocked -> pending). done/escalated left as-is." % len(_stuck))
        return 0
    flt = args[0] if args and not args[0].startswith("--") else None
    for t in ts:
        if flt and t["status"] != flt:
            continue
        print("  [%-10s] %-22s %s" % (t["status"], t.get("name") or t.get("id"), (t.get("reason") or "")[:60]))
    return 0


def cmd_repair(args):
    """lathe repair <plan> — the two-tier feedback loop as a first-class command: the ANALYST reads the
    plan plus its banked failure evidence (_fn_fails/ + _artifact_fails/) and rewrites the SPEC so the
    CURRENT implementer can succeed (tighter prompts, split functions, or a skeleton the small model
    fills). Saves <stem>_repaired.py next to the original — the original is preserved for comparison.
    Was previously only reachable inside `lathe do`/auto; a failing `lathe build` had no repair path."""
    paths = [a for a in args if not a.startswith("--")]
    if not paths:
        print("usage: lathe repair <plan>   (rewrites the spec from banked failures -> <plan>_repaired.py)"); return 2
    plan = _resolve_plan(paths[0])
    if not os.path.isfile(plan):
        print("repair: no such plan: %s" % paths[0]); return 2
    live = _load_autonomy()
    _mf = _manifest()
    if _mf is not None:                                   # analyst usage attribution, same fix as cmd_do
        try:
            import pricebook as _pb
            _am = os.environ.get("HARNESS_ANALYST_MODEL", "sonnet")
            live._reqspec.USAGE_HOOK = lambda role, u: _mf.record_usage(
                "analyst", u.get("prompt_tokens", 0), u.get("completion_tokens", 0), 1,
                "measured" if u.get("total_tokens") else "unmetered", _pb.price_for(_am))
        except Exception:
            pass
    print("> repair: analyst diagnosing %s from its banked failures..." % os.path.basename(plan))
    try:
        new_text, feedback = live.repair_plan(plan)
    except ValueError as e:
        print("repair: %s" % e); return 1
    if not new_text.strip():
        print("repair: analyst returned no rewrite (endpoint down or over budget)"); return 1
    v = _tool("plan_validator").is_valid_plan(new_text)   # model output is DATA: validate before saving
    if not (v.get("ok") if isinstance(v, dict) else v):
        print("repair: REJECTED - rewritten plan failed validation: %s" %
              (v.get("reason") if isinstance(v, dict) else "invalid")); return 1
    out_path = os.path.splitext(plan)[0] + "_repaired.py"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("repaired plan -> %s" % os.path.relpath(out_path, ROOT))
    print("  evidence used: %d chars of banked failure feedback" % len(feedback))
    print("  next: python lathe.py build %s" % os.path.splitext(os.path.basename(out_path))[0])
    if _mf is not None:
        try:
            _mf.append_contributor({"id": "analyst-repair", "role": "analyst", "kind": "model",
                                    "action": "rewrote spec of %s from banked failures -> %s" % (
                                        os.path.basename(plan), os.path.basename(out_path)), "status": "ok"})
        except Exception:
            pass
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
    rc = _run_engine(plan, MODEL, TRIES)
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
                wsroot = os.path.realpath(WORKSPACE_ROOT.replace("/", os.sep))   # the sanctioned external workspace root
                _rf = os.path.realpath(full)
                # allow the repo OR the sanctioned workspace root; refuse any other (arbitrary-write) path
                if not (_rf == root or _rf.startswith(root + os.sep) or _rf == wsroot or _rf.startswith(wsroot + os.sep)):
                    print("REFUSING to build: OUT_DIR escapes the working tree and the sanctioned workspace root (%s). "
                          "Set LATHE_TRUST_PLAN=1 to override." % od)
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
    rc = _run_engine(plan, MODEL, TRIES) if os.path.isfile(plan) else 1
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


def cmd_serve(args):
    """Start the opt-in local REST API (lathe_api.py) — for NON-agent consumers (a web dashboard, a
    language-agnostic service, CI-over-HTTP). Agents already have MCP. Bearer-token auth is required
    (`LATHE_API_TOKEN`), binds 127.0.0.1 by default; `--bind 0.0.0.0` additionally requires a docker sandbox.
    Every endpoint wraps the SAME gated engine path — no gate is weakened. See API.md."""
    import importlib.util
    def _flagval(flag, default):                               # guard a value-less --bind/--port (PR#1 v2.8.0 #4d)
        if flag in args:
            i = args.index(flag)
            if i + 1 < len(args):
                return args[i + 1]
            print("serve: %s needs a value" % flag); return None
        return default
    bind = _flagval("--bind", "127.0.0.1")
    port = _flagval("--port", None)
    spec = importlib.util.spec_from_file_location("lathe_api", os.path.join(ROOT, "lathe_api.py"))
    api = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(api)
    except Exception as e:
        print("serve: API unavailable (%s)" % e); return 1
    api.serve(bind=bind, port=port)
    return 0


def cmd_env(args):
    """The canonical ENVIRONMENT-VARIABLE surface (PR#1 CLI-review #1). `lathe env` prints every env var the
    harness recognizes — grouped, with role + default — from the single source of truth `env_catalog.py`.
    A `set` marker shows which are currently exported. This is the registry the `env_drift` gate checks the
    code against, so a new undocumented var fails the build rather than drifting in silently."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("env_catalog", os.path.join(ROOT, "env_catalog.py"))
    ec = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(ec)
    except Exception as e:
        print("env: catalog unavailable (%s)" % e); return 1
    groups = ec.grouped()
    total = sum(len(v) for v in groups.values())
    print("Lathe environment variables (%d documented; source of truth: env_catalog.py)" % total)
    print("Precedence: an explicit env var ALWAYS wins over lathe.config.json, which wins over the default.\n")
    for group, rows in groups.items():
        print("[%s]" % group)
        for name, role, default in rows:
            mark = " (set)" if os.environ.get(name) not in (None, "") else ""
            print("  %-28s %s%s" % (name, role, mark))
            print("  %-28s   default: %s" % ("", default))
        print()
    return 0


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
        # PR#1 CLI-review #2: graceful degrade — repo-map is optional; warn + skip rather than hard-fail (rc=1),
        # so a script/workflow that calls `lathe map` opportunistically isn't broken by a missing optional dep.
        print("map: SKIPPED — universal-ctags not on PATH (optional). Install it to enable the repo-map: "
              "winget install UniversalCtags.Ctags"); return 0
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
    from agent_router import pick_best, license_ok, score_match
    try:
        entries = json.load(open(os.path.join(INNER, "agents", "catalog.json"), encoding="utf-8")).get("agents", [])
    except Exception as ex:
        print("agent: catalog unavailable (%s)" % ex); return 1
    if args and args[0] == "bucket":                          # organize the library by when-to-invoke
        from collections import defaultdict
        want = args[1] if len(args) > 1 else None
        by_b = defaultdict(list)
        for e in entries:
            by_b[e.get("bucket", "specialized")].append(e["name"])
        for b in sorted(by_b):
            if want and b != want:
                continue
            print("== %s (%d) ==" % (b, len(by_b[b])))
            print("   " + ", ".join(sorted(by_b[b])))
        return 0
    if args and args[0] == "rate" and "--all" in args:        # #39 batch: grade EVERY agent (resumable)
        from persona_spawn import spawn_one, load_ratings, save_rating
        from persona_ratings import parse_judge_score
        from agent_router import license_ok
        sys.path.insert(0, TOOLS)
        from request_spec import request_spec
        cap = next((int(a) for a in args[2:] if a.isdigit()), 0)
        done = load_ratings()
        todo = [e for e in entries if e["name"] not in done and (e.get("vendored") or license_ok(e.get("license", "")))]
        if cap:
            todo = todo[:cap]
        import time
        pace = float(os.environ.get("LATHE_RATE_PACE", "2"))    # seconds between agents — don't burst the endpoint
        _err = lambda t: (not t) or not t.strip() or "API Error" in t or "usage policy" in t.lower()   # endpoint failure
        _thin = lambda t: len(t.strip()) < 40                   # a substantive ANSWER floor (NOT for the short score)
        def _ask(prompt):                                       # resilient: one backoff-retry on an endpoint failure
            r = request_spec(prompt) or ""
            if _err(r):
                time.sleep(min(30, pace * 8))                   # a rate-limit needs a real pause, not an instant retry
                r = request_spec(prompt) or ""
            return r
        print("rating %d agent(s) (%d already done; resumable — reruns skip the rated; pace=%ss)..." % (len(todo), len(done), pace))
        rated = errs = 0
        for e in todo:
            name = e["name"]
            if e.get("vendored"):
                try:
                    body = open(os.path.join(ROOT, e["path"]), encoding="utf-8").read()
                except OSError:
                    body = e.get("capability", "")
            else:
                md, _how = spawn_one(e)
                if not md:
                    print("  %-28s fetch failed — skipped" % name); continue
                body = open(md, encoding="utf-8", errors="replace").read()
            probe = ("You are this specialist:\n%s\n\nTASK: list the 3 most critical, CONCRETE checks you would "
                     "run in your domain (%s). Number them; one line each; be specific." % (body[:1400], e.get("capability", "")[:80]))
            ans = _ask(probe)
            if _err(ans) or _thin(ans):         # no substantive answer -> can't judge; skip (don't false-0)
                print("  %-28s unmeasurable (answer filtered/errored) — skipped" % name)
                errs += 1
                if errs >= 8:                   # the endpoint is down/capped — stop hammering; the run is resumable
                    print("  ... 8 consecutive endpoint failures — stopping (rerun later to resume; %d rated this run)" % rated); break
                continue
            judge = _ask("Rate 0-10 how specific/actionable/domain-expert this answer is (10=precise "
                         "expert checks; 0=generic). Reply exactly 'SCORE: <n>'.\n\nANSWER:\n%s" % ans[:1800])
            if _err(judge):                     # judge endpoint failed (short 'SCORE: n' is FINE — no length floor)
                print("  %-28s unmeasurable (judge filtered/errored) — skipped" % name)
                errs += 1
                if errs >= 8:
                    print("  ... 8 consecutive endpoint failures — stopping (rerun later to resume; %d rated this run)" % rated); break
                continue
            errs = 0
            s = parse_judge_score(judge)
            if s >= 0:
                save_rating(name, s, "batch:" + e.get("bucket", ""))
                print("  %-28s %.1f  [%s]" % (name, s, e.get("bucket", ""))); rated += 1
            else:
                print("  %-28s no score — skipped" % name)
            time.sleep(pace)
        print("rated %d (total now %d) -> agents/ratings.json" % (rated, len(load_ratings())))
        return 0 if rated else 1
    if args and args[0] == "ratings":                         # #39: show the measured persona ratings
        from persona_spawn import load_ratings
        r = load_ratings()
        if not r:
            print("no ratings yet — run: lathe agent rate \"<need>\" [k]"); return 0
        for n, v in sorted(r.items(), key=lambda kv: -(kv[1].get("rating") or 0) if isinstance(kv[1], dict) else 0):
            print("  %-28s %4.1f  (probe: %s)" % (n, v.get("rating", -1), (v.get("need") or "")[:50]))
        return 0
    if args and args[0] == "rate":                            # #39: EVALUATE the matched personas on a field probe
        from persona_spawn import auto_spawn_for_goal, load_ratings, save_rating, persona_overrides
        from persona_ratings import parse_judge_score
        need = " ".join(a for a in args[1:] if not a.startswith("--")).strip()
        if not need:
            print('usage: lathe agent rate "<need>" '); return 2
        sys.path.insert(0, TOOLS)
        from request_spec import request_spec
        rated = 0
        cands = auto_spawn_for_goal(need, 3)                  # fetched bodies (license-gated) for the top matches
        for name, _md, body in cands:
            probe = ("You are this specialist:\n%s\n\nTASK: list the 3 most critical, CONCRETE checks you "
                     "would run for: %s. Number them; one line each; be specific to the domain." % (body[:1500], need))
            ans = request_spec(probe) or ""
            judge = request_spec("Rate 0-10 how specific, actionable and domain-expert this answer is (10 = "
                                 "precise expert checks; 0 = generic filler). Reply with exactly 'SCORE: <n>'.\n\n"
                                 "NEED: %s\n\nANSWER:\n%s" % (need, ans[:2000])) or ""
            s = parse_judge_score(judge)
            if s >= 0:
                save_rating(name, s, need)
                print("  rated %-26s %.1f / 10" % (name, s)); rated += 1
            else:
                print("  %-26s judge gave no usable score — skipped" % name)
        print("%d persona(s) rated -> agents/ratings.json (the decider now weighs these; `lathe agent ratings` to view)" % rated)
        return 0 if rated else 1
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
    _scored = [[e["name"], score_match(need, e["name"].replace("-", " ") + " " + e.get("capability", ""))
                + score_match(need, e["name"].replace("-", " "))] for e in entries]   # name weighted (as auto_spawn)
    _best = max(_scored, key=lambda p: p[1]) if _scored else ["", 0]
    name = _best[0] if _best[1] > 0 else ""
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


def _assume_decisions_md(plan_path):
    """Committed audit artifact path: <plandir>/<planstem>.decisions.md (one per plan, tracked in git)."""
    stem = os.path.splitext(os.path.basename(plan_path))[0]
    return os.path.join(os.path.dirname(plan_path), "%s.decisions.md" % stem)


def _assume_write_decisions(plan_path, key, ledger, decisions, blockers):
    """Render the committed decisions ledger: every surfaced assumption + how it was RESOLVED (or that it's
    still open). This is the audit trail — an assumption, once resolved, is a stated decision, not a guess."""
    by_text = {d.get("assumption_text"): d for d in (decisions or [])}
    open_texts = {b.get("text") for b in (blockers or [])}
    md = ["# Assumption decisions — %s\n\n" % key,
          "The adversarial auditor surfaced the choices the goal never stated. Speculation is noise; each is "
          "resolved by an explicit human decision (accepted as-is, an alternative chosen, or intent stated) "
          "before the build proceeds. Nothing here is silently accepted.\n\n"]
    if not ledger:
        md.append("> **ADVISORY** — the auditor surfaced **0** assumptions. This is **not** the same as a "
                  "human clearing the list — a model self-audit can collapse its own ledger. Confirm the auditor "
                  "actually ran against a real endpoint before trusting this as \"nothing to decide.\"\n")
    for b in (ledger or []):
        t = b.get("text")
        d = by_text.get(t)
        head = "- **[%s | %s]** %s\n" % (b.get("materiality"), b.get("category"),
                                         _assume_clean(t))
        md.append(head)
        if d:
            md.append("  - **decision** (%s): %s\n" % (d.get("via", "resolved"), d.get("decision")))
        elif t in open_texts:
            md.append("  - _UNRESOLVED — blocks the build until decided._\n")
        else:
            md.append("  - _(not a blocker at the current scrutiny level)_\n")
    open(_assume_decisions_md(plan_path), "w", encoding="utf-8").write("".join(md))


def _assume_clean(text):
    """Strip an inline [options: ...] marker for display (the auditor may offer alternatives)."""
    try:
        if TOOLS not in sys.path:
            sys.path.insert(0, TOOLS)
        from clarify_logic import parse_options
        return parse_options(text)[0] or text
    except Exception:
        return text


def cmd_assume(args):
    """ASSUMPTION GATE: no assumption is silently accepted — each is thrown back for an explicit decision.
    `lathe assume <plan>` runs an ADVERSARIAL auditor over the plan's spec and emits a materiality-ranked
    ledger; with LATHE_ASSUMPTION_GATE=1 (forced by STRICT) the engine refuses to build while any
    blocking-materiality assumption is UNRESOLVED. `lathe assume <plan> --resolve` (alias `--confirm`) walks
    each blocker and makes YOU decide it: [a]ccept it as the real intent, pick an alternative the auditor
    offered, or type what you actually want — recorded as a stated decision in a committed `<plan>.decisions.md`.
    The DEFAULT is per-item; nothing is auto-accepted. `--accept-all` is an EXPLICIT opt-in to accept every
    blocker as-stated without individual review (your choice — logged as "accepted in bulk"); never the default.
    `--answers <file>` gives one decision per blocker (for scripted/CI use, still per-item). Skipping leaves a
    blocker blocking. `--scrutiny all|high+med|high|off` (or config `assumptions.scrutiny`) sets what blocks.
    Resolutions are keyed to a spec digest, so any spec change re-opens the audit."""
    import importlib.util, json
    resolve = ("--resolve" in args) or ("--confirm" in args)
    accept_all = "--accept-all" in args        # explicit opt-in bulk accept (NEVER the default) — the user's own choice
    ans_file = args[args.index("--answers") + 1] if "--answers" in args else None
    # scrutiny: --scrutiny/--policy flag > config/env (LATHE_ASSUMPTION_POLICY) > default 'high'
    if "--scrutiny" in args:
        policy = args[args.index("--scrutiny") + 1]
    elif "--policy" in args:
        policy = args[args.index("--policy") + 1]
    else:
        policy = os.environ.get("LATHE_ASSUMPTION_POLICY", "high")
    _VALUE_FLAGS = {"--policy", "--scrutiny", "--answers"}
    pos, _i = [], 0
    while _i < len(args):
        _a = args[_i]
        if _a in _VALUE_FLAGS:
            _i += 2; continue
        if _a.startswith("-"):
            _i += 1; continue
        pos.append(_a); _i += 1
    if not pos:
        print('usage: lathe assume <plan.py> [--resolve [--accept-all] | --answers <file>] [--scrutiny all|high+med|high|off]'); return 2
    plan_path = os.path.abspath(pos[0])
    if not os.path.exists(plan_path):
        print("assume: no such plan: %s" % plan_path); return 2
    spec = importlib.util.spec_from_file_location("plan", plan_path)
    plan = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(plan)
    except Exception as e:
        print("assume: plan does not load: %s" % e); return 1
    fns = getattr(plan, "FUNCTIONS", []) or []
    if not fns:
        print("assume: plan has no FUNCTIONS (nothing to audit)"); return 0
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    from assumption_logic import spec_digest, parse_assumptions, unconfirmed_blockers
    from clarify_logic import parse_options
    asm_file = os.path.join(os.path.dirname(plan_path), ".assumptions.json")
    try:
        data = json.loads(open(asm_file, encoding="utf-8").read())
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    key = os.path.basename(plan_path)
    entry = data.get(key) if isinstance(data.get(key), dict) else None
    digest = spec_digest(fns)

    # ---- RESOLVE MODE: throw each blocker back; require an explicit per-item DECISION (no blanket accept) ----
    if resolve:
        if not entry or entry.get("digest") != digest:
            print("assume: no current audit for this spec — run `lathe assume %s` first." % key); return 2
        pol = entry.get("policy", "high")
        confirmed = list(entry.get("confirmed") or [])
        decisions = list(entry.get("decisions") or [])
        blockers = unconfirmed_blockers(entry.get("ledger"), confirmed, pol)
        if not blockers:
            print("assume: every blocking assumption is already a stated decision. (build may proceed)"); return 0
        # EXPLICIT bulk accept — opt-in only (never default). The user chooses to accept all as-stated without
        # individual review; the audit trail records that honestly ("accepted in bulk"), so it's their call on record.
        if accept_all:
            print("=== ACCEPT-ALL: %d blocking assumption(s) accepted as-stated WITHOUT individual review "
                  "(your explicit choice) ===" % len(blockers))
            for b in blockers:
                clean = parse_options(b.get("text", ""))[0]
                confirmed.append(b.get("text"))
                decisions.append({"assumption_text": b.get("text"), "assumption": clean,
                                  "materiality": b.get("materiality"), "category": b.get("category"),
                                  "decision": clean, "via": "accepted in bulk (not individually reviewed)"})
                print("  [%s | %s] %s" % (b.get("materiality"), b.get("category"), clean))
            entry["confirmed"] = confirmed
            entry["decisions"] = decisions
            data[key] = entry
            open(asm_file, "w", encoding="utf-8").write(json.dumps(data, indent=1))
            _assume_write_decisions(plan_path, key, entry.get("ledger"), decisions, [])
            print("\naccepted %d in bulk; build is UNBLOCKED. audit trail -> %s" % (len(blockers), _assume_decisions_md(plan_path)))
            return 0
        scripted = None
        if ans_file:
            try:
                scripted = [l.rstrip("\n") for l in open(ans_file, encoding="utf-8")]
            except OSError as e:
                print("assume: --answers file unreadable: %s" % e); return 2
        print("=== RESOLVE %d blocking assumption(s) — decide each; nothing is auto-accepted ===" % len(blockers))
        for i, b in enumerate(blockers):
            clean, opts, default = parse_options(b.get("text", ""))
            print("\n  [%s | %s] %s" % (b.get("materiality"), b.get("category"), clean))
            for j, o in enumerate(opts, 1):
                print("       %d) %s" % (j, o))
            print("       decide: [a]ccept as the real intent%s, or type what you actually want, or [s]kip (stays blocking)"
                  % (" / pick a number" if opts else ""))
            if scripted is not None:
                raw = (scripted[i] if i < len(scripted) else "").strip()
                print("     > %s" % raw)
            else:
                try:
                    raw = input("     > ").strip()
                except (EOFError, KeyboardInterrupt):
                    raw = ""
            low = raw.lower()
            if low in ("s", "skip", ""):
                continue                                   # unresolved — still blocks (fail-safe default)
            if low in ("a", "accept", "y", "yes"):
                decision, via = clean, "accepted as-is"
            elif opts and raw.isdigit() and 1 <= int(raw) <= len(opts):
                decision, via = opts[int(raw) - 1], "chose alternative"
            else:
                decision, via = raw, "stated intent"
            confirmed.append(b.get("text"))               # matches the ledger text -> unblocks this one
            decisions.append({"assumption_text": b.get("text"), "assumption": clean,
                              "materiality": b.get("materiality"), "category": b.get("category"),
                              "decision": decision, "via": via})
            print("       => DECISION (%s): %s" % (via, decision))
        entry["confirmed"] = confirmed
        entry["decisions"] = decisions
        data[key] = entry
        open(asm_file, "w", encoding="utf-8").write(json.dumps(data, indent=1))
        remaining = unconfirmed_blockers(entry.get("ledger"), confirmed, pol)
        _assume_write_decisions(plan_path, key, entry.get("ledger"), decisions, remaining)
        print("\nrecorded %d decision(s); %d assumption(s) still UNRESOLVED%s"
              % (len(decisions), len(remaining), " — build is UNBLOCKED" if not remaining else " (build stays blocked)"))
        print("audit trail -> %s" % _assume_decisions_md(plan_path))
        return 0 if not remaining else 1

    # ---- AUDIT MODE: run the adversarial auditor, (re)generate the ledger ----
    _persona = ""
    try:
        _persona = open(os.path.join(INNER, "ce_personas", "assumption-auditor.md"), encoding="utf-8").read()
    except OSError:
        pass
    from request_spec import request_spec
    _spec_txt = "GOAL / INTENT:\n%s\n\nSPEC — the functions to be built:\n" % ((plan.__doc__ or getattr(plan, "MODULE_NAME", key)).strip())
    for f in fns:
        _spec_txt += "- %s: %s\n  acceptance tests: %s\n" % (f.get("name", "?"), (f.get("prompt", "") or "").strip(), f.get("tests", []))
    raw = request_spec("%s\n\n--- ARTIFACT TO AUDIT ---\n%s\n\nList the unstated assumptions now, one per line "
                       "in your exact format. If there are genuinely none, output: NO ASSUMPTIONS." % (_persona, _spec_txt)) or ""
    ledger = [] if "no assumptions" in raw.lower()[:40] else parse_assumptions(raw)
    keep = (entry and entry.get("digest") == digest)         # spec unchanged -> keep prior decisions
    prior = list(entry.get("confirmed") or []) if keep else []
    prior_dec = list(entry.get("decisions") or []) if keep else []
    data[key] = {"digest": digest, "policy": policy, "ledger": ledger, "confirmed": prior, "decisions": prior_dec}
    open(asm_file, "w", encoding="utf-8").write(json.dumps(data, indent=1))
    blockers = unconfirmed_blockers(ledger, prior, policy)
    _assume_write_decisions(plan_path, key, ledger, prior_dec, blockers)
    print("=== ASSUMPTION AUDIT — %d assumption(s), %d blocking (scrutiny=%s) ===" % (len(ledger), len(blockers), policy))
    for b in ledger:
        clean = parse_options(b.get("text", ""))[0]
        mark = "  BLOCKS" if b in blockers else ""
        print("  [%s | %s] %s%s" % (b.get("materiality"), b.get("category"), clean, mark))
    print("\naudit trail -> %s   (state: %s)" % (_assume_decisions_md(plan_path), asm_file))
    if blockers:
        print("decide each blocker before build:  lathe assume %s --resolve" % key)
    elif not ledger:
        print("advisory: the auditor surfaced 0 assumptions — NOT the same as human review (a model self-audit "
              "can collapse its own ledger). Confirm the auditor ran against a real endpoint.")
    return 0


def cmd_clarify(args):
    """Requirements LIAISON (thinking-BEFORE-thinking): interrogate the user for clarity before the harness
    designs anything. `lathe clarify "<goal>"` -> the liaison persona asks clarifying questions; you answer
    (interactively, or `--answers <file>` / stdin for scripted use); it synthesizes a CLARIFIED_GOAL.md brief
    (refined goal + assumptions + constraints + acceptance criteria + non-goals). That brief feeds `do`/`sdlc`.
    A goal that's already clear (has inputs+outputs) is passed straight through with a note."""
    import importlib.util
    _VALUE_FLAGS = {"--answers", "--out"}                  # flags that consume the NEXT arg (its value)
    goal_parts, _i = [], 0
    while _i < len(args):
        _a = args[_i]
        if _a in _VALUE_FLAGS:
            _i += 2; continue                              # skip the flag AND its value (path) — not part of the goal
        if _a.startswith("-"):
            _i += 1; continue
        goal_parts.append(_a); _i += 1
    goal = " ".join(goal_parts).strip()
    if not goal:
        print('usage: lathe clarify "<goal>" [--answers <file>] [--out <dir>]'); return 2
    out_dir = os.path.abspath(args[args.index("--out") + 1]) if "--out" in args else INNER
    ans_file = args[args.index("--answers") + 1] if "--answers" in args else None
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    from clarify_logic import goal_vagueness, parse_questions, parse_options
    from request_spec import request_spec
    needs, missing = goal_vagueness(goal)
    if not needs:
        print("clarify: the goal already states inputs + outputs — clear enough to design. (missing niceties: %s)"
              % (", ".join(missing) or "none"))
    _persona = ""
    for _p in (os.path.join(INNER, "ce_personas", "requirements-liaison.md"),):
        try:
            _persona = open(_p, encoding="utf-8").read()
        except OSError:
            pass
    q_prompt = ("%s\n\n--- GOAL FROM THE USER ---\n%s\n\nProduce your clarifying questions now (numbered, "
                "one per line, only what you cannot safely assume; at most 7). Where a question has a small "
                "bounded set of likely answers, attach selectable options inline as "
                "'[options: A | B | C] (default: A)' so the user can pick. If the goal is already "
                "unambiguous, reply with the single line: NO QUESTIONS." % (_persona, goal))
    raw_q = request_spec(q_prompt) or ""
    if "no questions" in raw_q.lower()[:40]:
        questions = []
    else:
        questions = parse_questions(raw_q)
    print("\n=== REQUIREMENTS LIAISON — %d clarifying question(s) ===" % len(questions))
    answers = []
    scripted = None
    if ans_file:
        try:
            scripted = [l.rstrip("\n") for l in open(ans_file, encoding="utf-8")]
        except OSError as e:
            print("clarify: --answers file unreadable: %s" % e); return 2
    for i, q in enumerate(questions, 1):
        clean, opts, default = parse_options(q)          # the liaison may attach selectable options + a default
        print("  Q%d. %s" % (i, clean))
        if opts:
            for j, opt in enumerate(opts, 1):
                print("       %d) %s%s" % (j, opt, "   (default)" if opt == default else ""))
            print("       (pick a number, type your own answer, or Enter for the default)")
        # gather the RAW reply — a scripted line, or interactive input
        if scripted is not None:
            raw = (scripted[i - 1] if i - 1 < len(scripted) else "").strip()
            print("     > %s" % raw)
        else:
            try:
                raw = input("     > ").strip()
            except (EOFError, KeyboardInterrupt):
                raw = ""
        # resolve the reply against the options: a bare number picks; empty -> default; else free text
        chosen = raw
        if opts and raw.isdigit() and 1 <= int(raw) <= len(opts):
            chosen = opts[int(raw) - 1]
        elif not raw and default:
            chosen = default
        if opts and chosen != raw:
            print("       => %s" % chosen)
        answers.append("Q: %s\nA: %s" % (clean, chosen))
    brief_prompt = ("%s\n\n--- GOAL ---\n%s\n\n--- CLARIFYING Q&A ---\n%s\n\nNow SYNTHESIZE the brief: a one-line "
                    "'Refined goal:', then bulleted Assumptions, Constraints, Acceptance criteria (each testable), "
                    "Non-goals, and Open questions. Concrete enough to write tests from."
                    % (_persona, goal, "\n\n".join(answers) or "(no answers provided)"))
    brief = request_spec(brief_prompt) or ""
    if not brief.strip() or "API Error" in brief:
        print("clarify: the liaison endpoint returned no brief (analyst unavailable)."); return 1
    # ASSUMPTION PASS (advisory at the clarify stage; the hard gate runs pre-build). An adversarial auditor
    # re-reads the brief against the goal and surfaces the choices it still leaves unstated — so ambiguity the
    # Q&A missed is visible now, not after code exists.
    _asm_section = ""
    try:
        from assumption_logic import parse_assumptions
        _auditor = open(os.path.join(INNER, "ce_personas", "assumption-auditor.md"), encoding="utf-8").read()
        _araw = request_spec("%s\n\n--- ARTIFACT TO AUDIT (a clarified brief) ---\nGOAL: %s\n\n%s\n\nList the "
                             "unstated assumptions now in your exact format, or output NO ASSUMPTIONS."
                             % (_auditor, goal, brief.strip())) or ""
        _led = [] if "no assumptions" in _araw.lower()[:40] else parse_assumptions(_araw)
        if _led:
            _asm_section = "\n\n## Unstated assumptions (adversarial auditor — confirm the HIGH ones)\n" + \
                "".join("- **[%s | %s]** %s\n" % (b.get("materiality"), b.get("category"), b.get("text")) for b in _led)
            _nhigh = sum(1 for b in _led if b.get("materiality") == "high")
            print("\n=== ASSUMPTION AUDITOR — %d unstated assumption(s), %d high-materiality ===" % (len(_led), _nhigh))
            for b in _led:
                print("  [%s | %s] %s" % (b.get("materiality"), b.get("category"), b.get("text")))
    except Exception:
        pass                                   # auditor is best-effort at clarify time; the pre-build gate is the enforcer
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "CLARIFIED_GOAL.md")
    open(path, "w", encoding="utf-8").write("# Clarified goal (requirements liaison)\n\n> Original: %s\n\n%s%s\n"
                                            % (goal, brief.strip(), _asm_section))
    print("\nbrief -> %s  (feed it to: lathe do / lathe sdlc)" % path)
    return 0


def cmd_sdlc(args):
    """SDLC authoring (#41): from a goal, the analyst writes LAYERED, ID-TRACED requirements —
    UC (use case) -> BR (business req) -> FR (functional req) -> TS (technical spec) — and the harness-built
    RTM gate REFUSES the set unless every item traces down AND is covered up (no orphans, no dangling refs).
    Output: <out>/REQUIREMENTS.md + <out>/rtm.json + a suggested plan CRITERIA block (TS -> criteria), ready
    for a STRICT-mode build. The proven template shipped a real product; this makes it a first-class command."""
    import json as _json, re as _re
    goal = " ".join(a for a in args if not a.startswith("--")).strip()
    if "--out" in args:
        goal = " ".join(a for a in args[:args.index("--out")] if not a.startswith("--")).strip()
    if not goal:
        print('usage: lathe sdlc "<goal>" [--out <dir>]'); return 2
    out_dir = INNER
    if "--out" in args:
        try:
            out_dir = os.path.abspath(args[args.index("--out") + 1])
        except IndexError:
            print("--out needs a directory"); return 2
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    from sdlc_rtm import rtm_gaps
    from request_spec import request_spec
    prompt = (
        "You are a rigorous requirements analyst following a strict SDLC. GOAL:\n%s\n\n"
        "Produce the LAYERED requirement set as PURE JSON (no prose, no markdown fence):\n"
        '{"UC": [{"id": "UC-1", "text": "..."}], "BR": [{"id": "BR-1", "text": "...", "traces_to": ["UC-1"]}], '
        '"FR": [{"id": "FR-1", "text": "...", "traces_to": ["BR-1"]}], "TS": [{"id": "TS-1", "text": "...", "traces_to": ["FR-1"]}]}\n'
        "Rules: 2-4 UC; each UC covered by >=1 BR; each BR by >=1 FR; each FR by >=1 TS; ids unique; every "
        "traces_to references only the layer directly above; TS entries must be concrete, testable technical "
        "contracts (they become acceptance criteria)." % goal)
    gaps = ["no attempt"]
    for attempt in (1, 2):
        raw = request_spec(prompt) or ""
        m = _re.search(r"\{.*\}", raw, _re.S)
        try:
            layers = _json.loads(m.group(0)) if m else None
        except Exception:
            layers = None
        gaps = rtm_gaps(layers)
        if not gaps:
            break
        print("RTM GATE (attempt %d): %d gap(s) — %s" % (attempt, len(gaps), "; ".join(gaps[:4])))
        prompt += "\n\nYOUR PREVIOUS ATTEMPT FAILED THE RTM GATE:\n- " + "\n- ".join(gaps[:10]) + "\nFix EVERY gap."
    if gaps:
        print("sdlc: REFUSED — the analyst could not produce a fully-traceable requirement set (%d gaps remain)." % len(gaps))
        return 1
    lines = ["# %s — Requirements (layered, ID-traced)" % goal[:60], "",
             "Chain: UC -> BR -> FR -> TS, enforced by the RTM gate (no orphans, no dangling refs).", ""]
    for layer, title in (("UC", "Business use cases"), ("BR", "Business requirements"),
                         ("FR", "Functional requirements"), ("TS", "Technical specifications")):
        lines += ["## %s (%s)" % (title, layer), "", "| ID | Text | Traces to |", "|---|---|---|"]
        lines += ["| **%s** | %s | %s |" % (it["id"], it["text"], ", ".join(it.get("traces_to") or []) or "—")
                  for it in layers.get(layer, [])]
        lines += [""]
    lines += ["## Suggested plan CRITERIA (each TS becomes an acceptance criterion)", "", "```python", "CRITERIA = ["]
    lines += ["    {'id': %r, 'text': %r, 'tests': ['<fn or fn:idx>']}," % (t["id"], t["text"]) for t in layers.get("TS", [])]
    lines += ["]", "```", "", "Build under STRICT mode (`LATHE_STRICT=1`) so the chain is enforced end-to-end."]
    os.makedirs(out_dir, exist_ok=True)
    req_md = os.path.join(out_dir, "REQUIREMENTS.md")
    open(req_md, "w", encoding="utf-8").write("\n".join(lines))
    open(os.path.join(out_dir, "rtm.json"), "w", encoding="utf-8").write(_json.dumps(layers, indent=1))
    n = sum(len(layers.get(k, [])) for k in ("UC", "BR", "FR", "TS"))
    print("RTM gate: PASS — %d traced items -> %s (+ rtm.json)" % (n, req_md))
    return 0


def cmd_trace(args):
    """Requirement→test→pin→model traceability matrix (enforcement mechanism #2 / the compliance artifact).
    A plan may declare acceptance CRITERIA; the validator REFUSES any criterion not mapped to ≥1 named,
    existing test (unmapped = a requirement nothing verifies). `lathe trace <plan>` emits the matrix."""
    import importlib.util, json, hashlib
    paths = [a for a in args if not a.startswith("--")]
    if not paths:
        print("usage: lathe trace <plan.py> [model]   (matrix for the plan's declared CRITERIA)"); return 2
    plan_path = _resolve_plan(paths[0])      # #17: resolve a bare stem (H_x) like cmd_build, not os.path.abspath
    if not os.path.exists(plan_path):
        print("trace: no such plan: %s" % paths[0]); return 2
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
          ("model", None): "LATHE_MODEL",                          # default implementer the CLI picks (e.g. openai:fable)
          ("tries", None): "LATHE_TRIES",
          ("assumptions", "scrutiny"): "LATHE_ASSUMPTION_POLICY"}   # user-governed assumption-gate level (high|high+med|all|off)
    for (sec, key), env in _m.items():
        node = cfg.get(sec)
        v = node if key is None else (node.get(key) if isinstance(node, dict) else None)
        if isinstance(v, (str, int)) and str(v):
            os.environ.setdefault(env, str(v))


# Operating contract #12 Phase 1 — the ENFORCEMENT SPINE (hand-edited CORE_INFRA, the dispatcher chokepoint).
# main() is the ONLY way any command runs AND the only in-process re-entry point (cmd_flow re-enters main per
# AUTO step). The guard makes the split: a TOP-LEVEL call runs the full spine (contract -> thinking depth ->
# work -> gates -> manifest, phases in CODE around the data); a re-entrant inner step runs RAW because the
# outer spine already owns the contract — exactly one manifest per top-level invocation. The process entry
# FORCE-clears the guard (same rationale as the forced LATHE_VALIDATE_PLAN below): a stale/hostile pre-set
# env var can never trick the top level into skipping its contract. A skill that shells out to `lathe` gets a
# FRESH process -> cleared guard -> its own full spine + manifest. There is no data/skill escape valve; the
# only honored bypass is LATHE_SPINE=off set by the operator before process start — and even that still emits
# a manifest recording the bypass.
_SPINE_GUARD = "_LATHE_SPINE_RUN"
_CURRENT_MF = None                                        # #19 M1: the current run's manifest (set by run_spine)


def _manifest():
    """The manifest object for the in-flight invocation, or None outside a spine run. Deciders use it to
    populate the audit fields (set_goal/set_selection) the record exists to carry."""
    return _CURRENT_MF


def _dispatch(cmd, rest, argv):
    """RAW dispatch — underscore-private; reached only via main() (top-level through run_spine, or re-entrant
    under the guard). No manifest here: the record belongs to the spine."""
    table = {
        "build": cmd_build, "do": cmd_do, "chat": cmd_chat, "auto": cmd_auto,
        "gate": cmd_gate, "review": cmd_review, "status": cmd_status,
        "board": cmd_board, "verify": cmd_verify, "repair": cmd_repair, "selftest": cmd_selftest,
        "decompose": cmd_decompose, "checkpoint": cmd_checkpoint, "run": cmd_run,
        "metrics": cmd_metrics, "plans": cmd_plans, "dups": cmd_dups, "whatis": cmd_whatis,
        "clean": cmd_clean, "wait": cmd_wait, "resume": cmd_resume, "waiting": cmd_waiting,
        "report": cmd_report, "issues": cmd_issues, "logs": cmd_logs, "lint-spec": cmd_lint_spec,
        "flow": cmd_flow, "map": cmd_map, "env": cmd_env, "serve": cmd_serve, "checkin": cmd_checkin, "agent": cmd_agent, "ack": cmd_ack, "trace": cmd_trace, "sdlc": cmd_sdlc, "clarify": cmd_clarify, "assume": cmd_assume,
    }
    if cmd in table:
        return table[cmd](rest)
    return cmd_do(argv)                        # bare `lathe "<goal>"`


def main(argv):
    # Windows-safe stdout: the CLI prints unicode (→, box chars) in several commands (trace, review). The
    # default Windows console codec is cp1252, which raises UnicodeEncodeError on those and crashes mid-command
    # (e.g. a build workflow's trailing trace step). Force UTF-8 on our own streams; harmless on POSIX.
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    os.environ["LATHE_VALIDATE_PLAN"] = "1"    # FORCE (not setdefault): a stale/hostile env var must not disable plan-as-data validation — same reason the validator path below is forced
    os.environ["LATHE_VALIDATOR_PY"] = os.path.join(TOOLS, "plan_validator.py")   # FORCE the trusted validator (a stale/hostile env var must not redirect it)
    _apply_config_env(_lathe_config())         # config file -> env defaults (an explicit env var still overrides)
    global MODEL, TRIES                        # #59: these were read at IMPORT time, before the config applied —
    MODEL = os.environ.get("LATHE_MODEL", "openai:local")   # so a config "model" was silently ignored by
    TRIES = os.environ.get("LATHE_TRIES", "3")              # cmd_build/verify. Re-read after config.
    if not argv or argv[0] in ("help", "-h", "--help"):
        print(__doc__); return 0
    cmd, rest = argv[0], argv[1:]
    # TYPO GUARD (usability): a bare SINGLE token that isn't a command (e.g. `lathe stauts`) used to be
    # treated as a one-word GOAL and drafted+built into garbage. Now it's a clear error with a suggestion.
    # A MULTI-word bare arg IS a real goal and flows to the bare-goal path below (run_spine -> do), which
    # keeps the manifest's routed_via="bare-goal" stamp. (The build-step-never-fires bug that made bare
    # goals a silent no-op is fixed in _run_workflow via the effective-primitive command.)
    if (_is_bare(cmd) and not os.environ.get(_SPINE_GUARD)
            and " " not in cmd and not cmd.startswith("-") and len(rest) == 0):
        import difflib
        _known = ("build", "do", "chat", "auto", "gate", "review", "status", "board", "verify", "repair",
                  "selftest", "trace", "clean", "checkin", "env", "metrics", "plans", "sdlc")
        _near = difflib.get_close_matches(cmd, _known, n=1)
        _hint = (" Did you mean `lathe %s`?" % _near[0]) if _near else ""
        print("unknown command: %r.%s\n"
              "To build from a goal, put it in quotes:  python lathe.py do \"%s ...\"\n"
              "See all commands:  python lathe.py help" % (cmd, _hint, cmd))
        return 2
    if os.environ.get(_SPINE_GUARD):           # RE-ENTRANT inner step: the outer spine owns the contract
        return _dispatch(cmd, rest, argv)
    return run_spine(cmd, rest, argv)          # TOP-LEVEL: the enforced contract


def run_spine(cmd, rest, argv):
    """The six-phase operating contract, in deterministic code around the data (#12 Phase 1). A workflow can
    define bad steps but cannot delete a phase — phases are not in the data. Emission is unconditional."""
    routed = "table" if cmd not in ("",) and not _is_bare(cmd) else "bare-goal"
    # FULL-verbose gate suite (heavy browser proofs + every PASS line) runs ONLY when the user's TOP-LEVEL
    # command is `gate`. Any gate that runs inside a do/build stays quiet + per-build (skips heavy). This is
    # the single source of truth — cmd_gate no longer mutates the env, so nothing leaks full mode into a build.
    if cmd == "gate":
        os.environ["LATHE_GATE_FULL"] = "1"
    mf = _manifest_begin(argv, cmd if routed == "table" else "do", routed)
    global _CURRENT_MF                                   # #19 M1: expose the run's manifest to the deciders
    _CURRENT_MF = mf                                     #         so cmd_do/cmd_review can set_goal/set_selection
    _mm0 = _metrics_offset()
    try:
        if TOOLS not in sys.path:
            sys.path.insert(0, TOOLS)
        try:
            from spine_core import resolve_thinking, depth_env, contract_of   # pinned pure decisions
            from workflows import CONTRACT_FOR
        except Exception:
            resolve_thinking = depth_env = None
            CONTRACT_FOR = {}
            contract_of = lambda c, t: {}
        if os.environ.get("LATHE_SPINE") == "off":           # operator bypass — honored, but ON THE RECORD
            if mf:
                mf.record_gate("spine", "disabled-by-operator", False, "LATHE_SPINE=off (pre-process env)")
            rc = _dispatch(cmd, rest, argv)
            if mf:
                mf.set_outcome(status=("pass" if not rc else "refuse"), exit_code=rc or 0)
            return rc
        contract = contract_of(cmd if routed == "table" else "do", CONTRACT_FOR)
        if resolve_thinking:                                  # phase 0 intake: thinking dial -> depth stamps
            think = resolve_thinking(_flag_of(rest, "--think"), os.environ.get("LATHE_THINK"),
                                     ((_lathe_config().get("thinking") or {}).get("level")
                                      if isinstance(_lathe_config().get("thinking"), dict) else None))
            for k, v in depth_env(think).items():
                os.environ.setdefault(k, v)                  # env > profile > config > default: fill only unset
            if mf:
                mf.record_gate("intake", "pass", False, "thinking=%s contract=%s" % (think, contract or "TRIVIAL"))
                try: mf.set_thinking(think)                  # #59: first-class field, not buried in a gate detail
                except Exception: pass
        _tok = mf._d["run_id"] if mf else "1"
        os.environ[_SPINE_GUARD] = _tok                      # from here, inner main() calls run RAW
        os.environ["LATHE_SPINE_TOKEN"] = _tok               # #12 U3: proves engine subprocesses ran via the spine
        # phase 3 work — #12 P2 PROMOTION: a contracted command runs its per-invocation WORKFLOW (primitive
        # step + gates in order, halt on blocked). --json stays primitive-only (compat guarantee: the stable
        # metrics object is the ONLY stdout). No workflow / unknown name -> the primitive, exactly as today.
        wf = None
        if contract.get("workflow") and "--json" not in rest:
            try:
                from workflows import get_workflow
                wf = get_workflow(contract["workflow"])
            except Exception:
                wf = None
        if wf:
            if mf:
                mf.record_gate("promotion", "pass", False, "workflow=%s" % contract["workflow"])
                mf.set_workflow(contract["workflow"],                    # #12 MANIFEST_DESIGN §1: name the
                                [lbl for _k, lbl, _a in wf.get("steps", [])])   # resolved workflow in intake
            # bare goal: the effective primitive is `do` even though `cmd` is the goal text — so the build
            # step matches and fires (else only the gate steps ran = silent no-op). _dispatch still gets the
            # real cmd (-> cmd_do(argv) for a bare goal). Table commands: effective == cmd, unchanged.
            _eff = cmd if routed == "table" else "do"
            rc = _run_workflow(wf, cmd, rest, argv, mf, eff_cmd=_eff)
        else:
            rc = _dispatch(cmd, rest, argv)
        if contract.get("gate") and rc == 0:                 # phase 4: standing gates after a green write
            rc = _phase_gates(mf) or rc
        if mf:
            mf.set_outcome(status=("pass" if not rc else "refuse"), exit_code=rc or 0)
        return rc
    except SystemExit as e:                                  # a handler called sys.exit()
        if mf:
            mf.set_outcome(status=("refuse" if e.code else "pass"), exit_code=e.code or 0)
        raise
    except BaseException as e:                               # crash / KeyboardInterrupt / gate abort
        if mf:
            mf.set_outcome(status="error", exit_code=1, error=repr(e))
        raise
    finally:
        os.environ.pop(_SPINE_GUARD, None)
        _CURRENT_MF = None                                # cleared (global already declared at top of run_spine)
        if mf:
            _manifest_merge_metrics(mf, _mm0)
            mf.finalize()                                    # phase 5: ALWAYS


def _run_workflow(wf, cmd, rest, argv, mf=None, eff_cmd=None):
    """#12 P2: run a per-invocation workflow's steps IN ORDER, halting on the first blocked step. Verdicts
    come from rc via the pinned classifier (flow_report), never from model text. Steps re-enter main() and
    run RAW under the spine's guard — the outer manifest records every step; no nested manifests.

    #17 fix — binding is no longer a blind global replace (which double-bound `review auto {files}` into
    `review auto auto <file>` and mis-resolved `trace {stem}`). Instead: the PRIMITIVE-FIRST step (the first
    auto step whose action's command == the invoked command) re-runs the operator's ORIGINAL argv verbatim
    (identity — never a re-template); ENFORCEMENT steps bind `{plan}` to the first positional arg (a
    resolvable stem) and `{files}`/`{args}`/`{goal}` to the full arg string."""
    import shlex
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    from flow_report import classify_step, workflow_verdict
    _positional = [a for a in rest if not a.startswith("--")]
    _plan_arg = _positional[0] if _positional else ""       # {plan} -> first positional (build/trace/verify)
    _joined = " ".join(rest)                                 # {files}/{args}/{goal} -> the full arg string
    _primitive_done = False
    rows = []
    _declared = wf.get("steps", [])
    _halted_at = None                                       # index of the step we halted on (blocked)
    for _i, (kind, label, action) in enumerate(_declared):
        action = action or ""
        if kind == "you":
            print("  [YOU checkpoint] %s" % label)
            rows.append("todo")
            if mf:
                mf.append_step(label, "todo", "you")
            continue
        if kind == "gate":
            rc = cmd_gate([])
        elif (not _primitive_done) and action.split(" ", 1)[0] == (eff_cmd or cmd):
            # the primitive-first step IS what the operator invoked — run their ORIGINAL argv, don't re-template.
            # eff_cmd lets a bare goal (cmd=goal text) match its `do` primitive; _dispatch still routes the
            # real cmd (a bare goal -> cmd_do(argv)).
            _primitive_done = True
            rc = _dispatch(cmd, rest, argv)
        else:
            act = (action.replace("{plan}", _plan_arg).replace("{args}", _joined)
                         .replace("{files}", _joined).replace("{goal}", _joined))
            if "{" in action and not act.replace(action.split(" ", 1)[0], "").strip():
                # B4: a step whose placeholder bound to nothing is SKIPPED — but it must still be RECORDED,
                # never silently dropped. A silent drop is exactly how declared steps went un-run and unnoticed.
                rows.append("skipped")
                if mf:
                    mf.append_step(label, "skipped", kind)
                continue
            rc = main(shlex.split(act))
        status = classify_step(kind, rc, "")
        rows.append(status)
        if mf:
            mf.append_step(label, status, kind)
        if status == "blocked":
            print("  [workflow] step BLOCKED — halting: %s" % label)
            if mf:
                # #59b: a refused run must NAME its cause — outcome used to read "REFUSE - reason: None"
                # while only the buried step row said which workflow step blocked.
                mf.record_gate("workflow", "blocked", True, "step blocked: %s (rc=%s)" % (label, rc))
            _halted_at = _i
            break
    # B4 INVARIANT: every DECLARED step must appear in the executed record. Steps after a halt didn't run —
    # record them as "not-reached" so declared==executed always holds and the reason is visible (never a
    # silent gap the wiring-gate can't see).
    if _halted_at is not None and mf:
        for kind, label, _a in _declared[_halted_at + 1:]:
            mf.append_step(label, "not-reached", kind)
    return 0 if workflow_verdict(rows) == "PASS" else 1


def _is_bare(cmd):
    return cmd not in (
        "build", "do", "chat", "auto", "gate", "review", "status", "board", "verify", "repair", "selftest",
        "decompose", "checkpoint", "run", "metrics", "plans", "dups", "whatis", "clean", "wait",
        "resume", "waiting", "report", "issues", "logs", "lint-spec", "flow", "map", "env", "serve",
        "checkin", "agent", "ack", "trace", "sdlc", "clarify", "assume")


def _flag_of(rest, flag):
    """--think=high style flag from argv (None if absent)."""
    try:
        for a in rest:
            if isinstance(a, str) and a.startswith(flag + "="):
                return a.split("=", 1)[1]
    except Exception:
        pass
    return None


def _phase_gates(mf):
    """Phase 4: standing gates as a real subprocess — the rc decides, never model text. 0 = green."""
    try:
        import subprocess
        rg = os.path.join(QA, "run_gates.py")
        if not os.path.exists(rg):
            if mf:
                mf.record_gate("standing-gates", "fail", True, "run_gates.py missing")
            return 1
        r = subprocess.run([sys.executable, rg], cwd=QA, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=int(os.environ.get("REGRESSION_TIMEOUT", "300")))
        last = ((r.stdout or "").strip().splitlines() or [""])[-1]
        if mf:
            mf.record_gate("standing-gates", "pass" if r.returncode == 0 else "fail", True, last[:120])
        return 0 if r.returncode == 0 else 1
    except Exception as e:
        if mf:
            mf.record_gate("standing-gates", "fail", True, "gate runner error: %r" % (e,))
        return 1


def _manifest_begin(argv, command, routed):
    """Open the per-invocation record (#12). Degrades VISIBLY (stderr) if the module is unavailable —
    a broken install must not also lose the CLI."""
    try:
        if TOOLS not in sys.path:
            sys.path.insert(0, TOOLS)
        import manifest as _mfmod
        m = _mfmod.Manifest.begin(argv=list(argv), command=command, routed_via=routed)
        try:                                       # bind the analyst usage reporter (#12 L2)
            import request_spec as _rs
            import pricebook as _pb
            _amodel = os.environ.get("HARNESS_ANALYST_MODEL", "sonnet")
            _rs.USAGE_HOOK = lambda role, u: m.record_usage(
                role, u.get("prompt_tokens", 0), u.get("completion_tokens", 0), 1,
                u.get("token_source", "measured" if u.get("total_tokens") else "n/a"),
                _pb.price_for(_amodel))
        except Exception:
            pass
        return m
    except Exception as e:
        sys.stderr.write("manifest unavailable (record NOT emitted this run): %r\n" % (e,))
        return None


def _metrics_offset():
    try:
        return os.path.getsize(os.path.join(ROOT, "metrics", "runs.jsonl"))
    except OSError:
        return 0


def _manifest_merge_metrics(mf, offset):
    """Engine builds run as subprocesses; their runs.jsonl rows appended during THIS invocation are merged
    into the manifest (contributors, per-role usage, gate verdicts). Best-effort."""
    try:
        import json as _json
        import pricebook as _pb
        path = os.path.join(ROOT, "metrics", "runs.jsonl")
        with open(path, encoding="utf-8") as f:
            f.seek(offset)
            new = f.read()
        _rp = {"implementer": _pb.price_for("local"), "judge": _pb.price_for("sonnet"),
               "analyst": _pb.price_for(os.environ.get("HARNESS_ANALYST_MODEL", "sonnet"))}
        for line in new.strip().splitlines():
            try:
                row = _json.loads(line)
            except ValueError:
                continue
            # #59b INTEGRITY: scope the merge to THIS run's lineage. The window is time-based, so a
            # CONCURRENT build from another process used to leak into the wrong manifest. Engine rows now
            # carry parent_run (= the spine token = this manifest's run_id); mismatched rows are skipped.
            # Rows with no parent_run (legacy / direct engine bypass) are kept for compatibility.
            _pr = row.get("parent_run")
            if _pr and mf._d.get("run_id") and _pr != mf._d["run_id"]:
                continue
            _nfn, _nart = row.get("functions_total", 0), row.get("artifacts_total", 0)
            mf.append_contributor({
                "id": "engine-build", "role": "build", "kind": "engine",
                "action": "%s on %s: %s/%s fns, %s/%s artifacts" % (
                    row.get("plan"), row.get("resolved_model") or row.get("model"),
                    row.get("functions_passed"), _nfn, row.get("artifacts_passed"), _nart),
                "status": "ok" if row.get("build_ok") else "failed"})
            for role, b in (row.get("tok_by_role") or {}).items():
                if isinstance(b, dict):
                    mf.record_usage(role, b.get("p", 0), b.get("e", 0), b.get("calls", 0),
                                    b.get("src"), _rp.get(role))
            reg = str(row.get("regression") or "")
            if reg and not reg.upper().startswith("SKIP"):   # #59: a SKIPPED regression is "not armed", not a FAIL
                mf.record_gate("standing-regression", "pass" if reg.startswith("PASS") else "fail",
                               True, reg[:120])
            mf.record_gate("build", "pass" if row.get("build_ok") else "fail", True,
                           "%s: %s/%s fns" % (row.get("plan"), row.get("functions_passed"),
                                              row.get("functions_total")))
            # #59: the full build record — per-function/per-artifact results, pins, resolved model, out dir.
            try:
                _build_row = {k: row.get(k) for k in
                              ("plan", "model", "resolved_model", "endpoint", "elapsed_s", "out_dir",
                               "pins_added", "per_function", "per_artifact", "build_ok")}
                # #59b: attach the actual assert CHECKLIST from the plan (the spec-coverage proof) — parsed
                # as DATA (ast literals), never imported/executed.
                try:
                    import ast as _ast
                    _pp = row.get("plan_path")
                    if _pp and not os.path.isabs(_pp):
                        _pp = os.path.join(ROOT, _pp)
                    if _pp and os.path.exists(_pp):
                        _tree = _ast.parse(open(_pp, encoding="utf-8").read())
                        _checks = {}
                        for _n in _ast.walk(_tree):
                            if isinstance(_n, _ast.Assign) and any(
                                    isinstance(t, _ast.Name) and t.id in ("ARTIFACTS", "FUNCTIONS") for t in _n.targets):
                                for _el in getattr(_n.value, "elts", []):
                                    if not isinstance(_el, _ast.Dict):
                                        continue
                                    _kv = {k.value: v for k, v in zip(_el.keys, _el.values)
                                           if isinstance(k, _ast.Constant)}
                                    _nm = _kv.get("path") or _kv.get("name")
                                    _ts = _kv.get("tests")
                                    if isinstance(_nm, _ast.Constant) and isinstance(_ts, (_ast.List, _ast.Tuple)):
                                        _checks[str(_nm.value)] = [e.value for e in _ts.elts
                                                                   if isinstance(e, _ast.Constant) and isinstance(e.value, str)]
                        if _checks:
                            _build_row["checks"] = _checks
                except Exception:
                    pass
                mf.append_build(_build_row)
                mf.add_model({"role": "implementer", "model": row.get("resolved_model") or row.get("model"),
                              "endpoint": row.get("endpoint")})
                _arts = ["%s/%s" % (row.get("out_dir") or "?", (a.get("path") or "").lstrip("/"))
                         for a in (row.get("per_artifact") or []) if a.get("ok")]
                _npins = int(row.get("pins_added") or 0)
                mf.merge_outputs(artifacts=_arts,
                                 pins=(["%d new pin(s) in %s/.pins.json" % (_npins, row.get("out_dir") or "?")]
                                       if _npins else []))
            except Exception:
                pass
    except Exception:
        pass


def _cli():                                    # console-script entry point (see pyproject.toml)
    os.environ.pop(_SPINE_GUARD, None)         # #12 Phase 1: a hostile/inherited guard must not disable the spine
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    os.environ.pop(_SPINE_GUARD, None)         # same guard-forge defense on the script entry
    sys.exit(main(sys.argv[1:]))
