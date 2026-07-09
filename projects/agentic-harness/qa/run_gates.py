"""STANDING REGRESSION for the agentic-harness project.

The engine (engine_v2.py) runs this after every successful build (it resolves projects/<proj>/qa/run_gates.py
from the plan path — see the decoupling fix 2026-06-29). A non-zero exit makes the build RED, so a build that
leaves the tree dirty cannot ship. Keep it FAST and deterministic — it runs on every plan.

Currently enforces:
  - stale_gate: no backup/dup/superseded files linger in tools/ or plans/ (cleanup discipline)

Add more standing checks here as the harness grows (e.g. no two tools exporting the same MODULE_NAME).
"""
import os, subprocess, sys, time

# Force UTF-8 on our own stdout/stderr: the ENGINE captures this via a pipe, whose default Windows encoding is
# cp1252 — a gate summary line containing any non-latin1 char (an arrow, em-dash) would crash `print` with
# UnicodeEncodeError, kill the regression mid-run, and read as a spurious FAIL (which rolled back a green build).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

QA = os.path.dirname(os.path.abspath(__file__))
CHECKS = [("tree_no_stale_dups", os.path.join(QA, "stale_gate.py")),
          ("no_duplicate_resources", os.path.join(QA, "resource_dups_gate.py")),  # one canonical DB/resource, not several
          ("capability_registry", os.path.join(QA, "registry_gate.py")),          # one 'live' canonical per capability
          ("pristine_tree", os.path.join(QA, "pristine_gate.py")),                 # no corrupt/half-written files linger
          ("lint_no_real_bugs", os.path.join(QA, "lint_gate.py")),                 # ruff: no undefined-name/syntax/format defects in generated code
          ("docs_not_drifted", os.path.join(QA, "docs_drift_gate.py")),            # every CLI command documented with an example in LATHE_COMMANDS.md
          ("env_not_drifted", os.path.join(QA, "env_drift_gate.py")),               # every env var the code reads is documented in env_catalog.py (lathe env)
          ("manifest_contract", os.path.join(QA, "manifest_contract_gate.py")),     # #12: every invocation emits a complete, un-skippable manifest (T2-T6)
          ("skeleton_lane", os.path.join(QA, "skeleton_lane_gate.py")),             # v2.26 post-mortem: BOTH artifact lanes get the RIGHT output contract (deterministic stub implementer)
          ("workflow_wiring", os.path.join(QA, "workflow_wiring_gate.py")),         # B4: every DECLARED workflow step is EXECUTED+recorded (no silent disconnect); declared==executed
          ("failure_registry", os.path.join(QA, "failure_registry_gate.py")),       # C4: every known failure CLASS that claims a gate has it wired; open holes tracked loudly (the adversarial ratchet)
          ("behavioral_lane", os.path.join(QA, "behavioral_lane_gate.py")),          # D1: input->response is enforced (working helicopter passes, dead-control one fails) — not just liveness
          ("vision_lane", os.path.join(QA, "vision_lane_gate.py")),                  # D3: the screenshot->judge->verdict pipeline works + is fail-safe advisory (stub judge; live judging opt-in)
          ("refute_lane", os.path.join(QA, "refute_lane_gate.py")),                  # C1/C2: the second-spec + refute pipeline works + is fail-safe advisory (stub analyst; live red-team opt-in)
          ("intake_confirm", os.path.join(QA, "intake_confirm_gate.py")),            # A3/A4: per-assumption confirm (accept/drop/edit) + spec approve/reject/revise logic is correct
          ("contract_hygiene", os.path.join(QA, "contract_hygiene_gate.py")),        # B3/B5: no dead front_end/select contract flags; every workflow promotion resolves (no dangling)
          ("persona_wiring", os.path.join(QA, "persona_wiring_gate.py")),            # E1/E3: prompt-architect always in the intake panel; decider is honest about lexical-vs-semantic (no overclaim)
          ("outcome_feedback", os.path.join(QA, "outcome_feedback_gate.py")),        # E4: review outcomes EWMA-blend into persona ratings (engaged up, inoperative skipped); the grade loop learns
          ("workspace_docs", os.path.join(QA, "workspace_docs_gate.py")),            # F1: every goal workspace gets a GOAL.md (intent+assumptions+panel) + README.md (layout)
          ("project_layout", os.path.join(QA, "project_layout_gate.py")),            # F4: genuine multi-file projects get a code/docs/scripts/config PROJECT.md map (+ opt-in organize)
          ("spec_test_consistency", os.path.join(QA, "spec_test_consistency_gate.py")),  # catch a behavioral test that contradicts its own spec (score-vs-grace, undeclared selector) before the build wastes attempts
          ("spec_review", os.path.join(QA, "spec_review_gate.py")),                    # the CLOSED LOOP: a contradictory spec refines ITSELF to clean before the implementer runs (converges or surfaces unresolved)
          ("repair_prompt", os.path.join(QA, "repair_prompt_gate.py")),                # loop 2 targeted repair: a retry gets its OWN failed code + the EXACT gate failure to fix (not a blind re-roll)
          ("build_narrator", os.path.join(QA, "build_narrator_gate.py")),              # the plain-English layer over the engine's technical output (every build path routes through it)

          ("spine_enforced", os.path.join(QA, "spine_gate.py")),                     # #12 P1: guard-forge/skill-subprocess/bypass attacks all defeated (P1-P5)
          ("gate_tristate", os.path.join(QA, "tristate_gate.py"))]                    # #12 U1: gates fail CLOSED (INOPERATIVE), never open, on their own error

# HEAVY gates spawn a full engine/Chromium BUILD inside themselves (they are capability PROOFS, not tree
# checks). The regression's contract is "FAST + deterministic, runs on every plan" — a heavyweight sub-build
# violates it and, under load, false-BLOCKS a genuinely-green user build (observed 2026-07-08: a shipped
# helicopter game blocked by skeleton_lane failing 3x under contention). So these run ONLY in the EXPLICIT
# full suite (`lathe gate`, which sets LATHE_GATE_FULL=1), NOT in the per-build post-regression. The user's OWN
# artifact still gets its behavioral/functional gate in the engine; we just don't re-prove harness capabilities
# after every build.
HEAVY = {"skeleton_lane", "behavioral_lane", "vision_lane"}


def main():
    failed = []
    _full = os.environ.get("LATHE_GATE_FULL", "") in ("1", "true")
    for name, path in CHECKS:
        if name in HEAVY and not _full:
            continue                                       # silently skip heavy gates per-build (they run on `lathe gate`)
        if not os.path.exists(path):
            # #12 (PR#7 round-3 finding): a MISSING gate file used to be silently skipped while the run
            # still printed "regression clean" — a vacuous green. A registered gate that is absent is a FAIL.
            print("%-22s FAIL :: gate file missing: %s" % (name, os.path.basename(path)))
            failed.append(name + "(missing)")
            continue
        # FLAKE TOLERANCE (2026-07-08): the browser-based gates (skeleton_lane, behavioral_lane, vision_lane)
        # can flake on a transient Chromium/subprocess timing hiccup, and a single flake used to BLOCK an
        # otherwise-green build's post-regression — masking a real success. So a FAILED gate is RETRIED: a
        # genuine failure recurs across attempts, a flake clears. Applies to every gate (whole class). Set
        # GATE_RETRIES=0 to disable.
        _retries = int(os.environ.get("GATE_RETRIES", "2"))
        r = None; _exc = None
        for _attempt in range(_retries + 1):
            try:
                r = subprocess.run([sys.executable, path], capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=int(os.environ.get("GATE_TIMEOUT", "300")))
                _exc = None
            except Exception as e:
                r = None; _exc = e
            if r is not None and r.returncode == 0:
                break                                      # passed — done
            if _attempt < _retries:                        # failed/errored with retries left -> flake check
                print("%-22s retry %d/%d (nonzero — flake check before condemning)" % (name, _attempt + 1, _retries))
                time.sleep(2)                              # let a transient lock (AV scan, browser launch) clear
        if r is None:
            # #12 U1: a gate whose PROCESS could not run (timeout, spawn error) after retries is INOPERATIVE —
            # the standing regression always fails closed (a gate that can't run is never a silent pass).
            print("%-22s INOPERATIVE :: gate could not run: %s" % (name, _exc))
            failed.append(name + "(inoperative)")
            continue
        # returncode 0 -> PASS; nonzero -> FAIL/INOPERATIVE. A crashed gate (traceback, no clean summary line)
        # is labelled INOPERATIVE for the operator; either way it fails the regression closed.
        _out_lines = (r.stdout or "").strip().splitlines()
        _crashed = r.returncode != 0 and not _out_lines and ("Traceback" in (r.stderr or ""))
        tag = "PASS" if r.returncode == 0 else ("INOPERATIVE" if _crashed else "FAIL")
        last = _out_lines[-1] if _out_lines else ((r.stderr or "").strip().splitlines() or [""])[-1]
        # READABILITY: the per-build regression printed 23 "gate PASS" lines after every build — noise. Show
        # each line only in the EXPLICIT full suite (`lathe gate`) or when a gate FAILS; per-build stays quiet
        # on pass and prints a single clean summary at the end.
        if _full or r.returncode != 0:
            print("%-22s %s :: %s" % (name, tag, last[:200]))
        if r.returncode != 0:
            failed.append(name + ("(inoperative)" if _crashed else ""))
    if failed:
        print("REGRESSION: " + ", ".join(failed)); sys.exit(1)
    _ran = sum(1 for n, _ in CHECKS if _full or n not in HEAVY)
    print("regression clean (%d checks)" % len(CHECKS) if _full
          else "  workspace + tree checks: clean (%d checks passed)" % _ran)
    sys.exit(0)

if __name__ == "__main__":
    main()
