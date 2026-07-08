"""workflow_wiring_gate.py — B4: the DECLARED == EXECUTED invariant (the anti-disconnect gate).

Root disease it guards (the one that let clarify/assume/front-end silently never run): a workflow could
DECLARE a step that the runner never executed AND never recorded — invisible, uncaught, for weeks. This
gate makes that impossible: every DECLARED step of a promoted workflow MUST appear in the executed record
(manifest work.steps), with a status. A silent drop fails the build.

It runs the REAL runner (`lathe._run_workflow`) against synthetic workflows with primitives stubbed
(deterministic, no model calls, ~ms), plus a manifest-level check on every command-promoted workflow.

Probes:
  P1  every declared step of a normal workflow is recorded (count in == count out)
  P2  a step whose placeholder binds to NOTHING is recorded as "skipped" (not silently dropped) — the exact
      historical bug
  P3  after a BLOCKED/halt, remaining declared steps are recorded "not-reached" (declared==executed still holds)
  P4  for EVERY command in CONTRACT_FOR that promotes a workflow, the declared step labels are a subset of a
      dry-run's recorded step labels (no command silently loses a step)
"""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(QA)))
TOOLS = os.path.join(os.path.dirname(QA), "tools")
sys.path.insert(0, ROOT)
sys.path.insert(0, TOOLS)

import lathe                                       # noqa: E402
import workflows as wfmod                          # noqa: E402


class _RecMf:
    """Minimal manifest stub: records every append_step call — nothing else."""
    def __init__(self):
        self.steps = []
        self._d = {"run_id": "wiretest"}
    def append_step(self, label, status, kind="auto"):
        self.steps.append({"label": label, "status": status, "kind": kind})
    def record_gate(self, *a, **k):
        pass


def _run(wf, cmd="do", rest=None, argv=None, eff_cmd=None):
    """Run the REAL _run_workflow with cmd_gate/_dispatch/main stubbed to no-ops; return the recording mf."""
    rest = rest if rest is not None else []
    argv = argv if argv is not None else [cmd] + rest
    mf = _RecMf()
    _sav = (lathe.cmd_gate, lathe._dispatch, lathe.main)
    try:
        lathe.cmd_gate = lambda a: 0
        lathe._dispatch = lambda c, r, av: 0
        lathe.main = lambda av: 0            # sub-command steps (build/trace/...) become no-ops
        lathe._run_workflow(wf, cmd, rest, argv, mf=mf, eff_cmd=eff_cmd)
    finally:
        lathe.cmd_gate, lathe._dispatch, lathe.main = _sav
    return mf


def main():
    emitted = []

    # P1 — normal workflow: every declared step recorded
    wf1 = {"steps": [("auto", "primitive", "do {args}"), ("gate", "gates", ""), ("you", "checkpoint", "")]}
    m = _run(wf1, cmd="do", rest=["x"])
    assert len(m.steps) == 3, "P1 declared 3, recorded %d" % len(m.steps)
    emitted.append("P1 all declared steps recorded")

    # P2 — a placeholder that binds to nothing is RECORDED as skipped (the historical silent-drop bug)
    wf2 = {"steps": [("auto", "primitive", "do {args}"),
                     ("auto", "needs a plan we don't have", "trace {plan}")]}   # {plan} empty -> would skip
    m = _run(wf2, cmd="do", rest=[])       # no positional -> {plan} binds to nothing
    labels = [s["label"] for s in m.steps]
    assert "needs a plan we don't have" in labels, "P2 unbound-placeholder step was SILENTLY DROPPED"
    assert any(s["status"] == "skipped" for s in m.steps), "P2 skip not recorded as 'skipped'"
    emitted.append("P2 unbound step recorded as skipped (no silent drop)")

    # P3 — after a halt, remaining steps recorded not-reached. Force a block: make the primitive return blocked
    #      by stubbing classify_step via a workflow whose first gate blocks.
    _savg = lathe.cmd_gate
    try:
        lathe.cmd_gate = lambda a: 2       # nonzero -> classify_step -> "blocked" for a gate step
        wf3 = {"steps": [("gate", "will block", ""), ("auto", "after", "do {args}"), ("you", "note", "")]}
        mf = _RecMf()
        _sd, _sm = lathe._dispatch, lathe.main
        lathe._dispatch, lathe.main = (lambda c, r, av: 0), (lambda av: 0)
        try:
            lathe._run_workflow(wf3, "do", ["x"], ["do", "x"], mf=mf)
        finally:
            lathe._dispatch, lathe.main = _sd, _sm
    finally:
        lathe.cmd_gate = _savg
    labels = {s["label"]: s["status"] for s in mf.steps}
    assert len(mf.steps) == 3, "P3 declared 3, recorded %d after halt" % len(mf.steps)
    assert labels.get("after") == "not-reached" and labels.get("note") == "not-reached", \
        "P3 post-halt steps not recorded not-reached: %s" % labels
    emitted.append("P3 post-halt steps recorded not-reached (declared==executed holds)")

    # P4 — every command-promoted workflow: declared labels ⊆ recorded labels on a dry run
    bad = []
    for cmd, c in wfmod.CONTRACT_FOR.items():
        wfn = c.get("workflow")
        if not wfn:
            continue
        wf = wfmod.get_workflow(wfn)
        if not wf:
            bad.append("%s -> missing workflow %s" % (cmd, wfn))
            continue
        declared = [lbl for _k, lbl, _a in wf["steps"]]
        eff = "do" if cmd == "do" else cmd
        m = _run(wf, cmd=cmd, rest=["dummy"], eff_cmd=eff)
        rec = {s["label"] for s in m.steps}
        missing = [d for d in declared if d not in rec]
        if missing:
            bad.append("%s(%s): declared-but-unrecorded %s" % (cmd, wfn, missing))
    assert not bad, "P4 workflows with un-executed declared steps: " + "; ".join(bad)
    emitted.append("P4 all %d promoted workflows: declared==executed" %
                   sum(1 for c in wfmod.CONTRACT_FOR.values() if c.get("workflow")))

    print("workflow-wiring gate: %d/4 probes pass (%s)" % (len(emitted), "; ".join(emitted)))
    sys.exit(0 if len(emitted) == 4 else 1)


if __name__ == "__main__":
    main()
