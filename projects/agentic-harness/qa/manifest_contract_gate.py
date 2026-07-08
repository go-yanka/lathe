"""Operating-contract acceptance gate (#12 Phase 0) — executable probes over the REAL dispatcher.

T2 un-skippable (return/raise/SystemExit all still emit), T3 structural completeness, T4 analyst tokens
instrumented (the gap is closed and cannot silently regress), T5 role-split imputed cost, T6 bare command
routes through the contract. Runs in-process against lathe.main() with stub handlers — fast + deterministic
(standing regression runs this on every build). T1-full (~35 real commands), T7 (verbatim hash-match) and
T8 (byte-identical reruns) are covered by the reviewer's external stress suite, not this fast gate.
"""

# UTF-8 stdout: this gate is captured via a cp1252 pipe by the engine; a unicode print would
# crash it mid-run and read as a spurious failure. (#12 U1 hardening.)
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import glob
import json
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(QA)))
TOOLS = os.path.join(os.path.dirname(QA), "tools")
sys.path.insert(0, ROOT)
sys.path.insert(0, TOOLS)

import lathe                                    # noqa: E402
import manifest as mfmod                        # noqa: E402
import manifest_core as core                    # noqa: E402


def _new_manifest(known):
    """The manifest THIS probe's invocation emitted = a file that was NOT there before it ran. The old
    version used an mtime window with a 1s slack — back-to-back probes land in the same second under the
    full suite, so a probe could read its PREDECESSOR's manifest and fail with a WRONG-content assert
    ('T2c outcome wrong', 'KeyError: analyst') pointing at the wrong file. Set-difference is exact."""
    files = [f for f in glob.glob(os.path.join(mfmod.out_dir(), "*.manifest.json")) if f not in known]
    assert files, "no manifest emitted (probe produced no NEW manifest file)"
    latest = max(files, key=os.path.getmtime)
    return json.load(open(latest, encoding="utf-8")), latest


def _invoke(argv):
    known = set(glob.glob(os.path.join(mfmod.out_dir(), "*.manifest.json")))   # snapshot BEFORE the probe
    try:
        rc = lathe.main(argv)
    except SystemExit as e:
        rc = e.code
    except RuntimeError:
        rc = "raised"
    return rc, _new_manifest(known)[0]


def main():
    # Runs as a subprocess of the engine's standing regression, possibly under an outer spine — the guard
    # env is inherited. This gate calls lathe.main() as a LIBRARY, so emulate the process-entry clear
    # (a real child `lathe` process does this at its own entry) before the in-process top-level probes.
    os.environ.pop("_LATHE_SPINE_RUN", None)
    import tempfile                            # isolate manifest probes from a concurrent nested build (LATHE_CE_DIR)
    os.environ["LATHE_CE_DIR"] = tempfile.mkdtemp(prefix="mf_gate_")
    # RECURSION BREAK (#12 P2): promoted workflows carry real `gate` steps that run the standing suite —
    # but THIS gate runs INSIDE that suite. A probe on a promoted command (T6's bare goal -> `do`) would
    # re-enter run_gates -> this gate -> ... forever (found live: it timed out the engine's regression and
    # rolled back a green build). Probes assert manifest/routing behavior, not gate content — stub it.
    lathe.cmd_gate = lambda rest: 0
    emitted = []

    # T2 — un-skippable under every terminal path (stub handlers injected into the REAL table via cmd names)
    real_status = lathe.cmd_status
    try:
        lathe.cmd_status = lambda rest: 2                                   # (a) non-zero return
        rc, m = _invoke(["status"])
        assert m["outcome"]["status"] == "refuse" and m["outcome"]["exit_code"] == 2, "T2a outcome wrong"
        lathe.cmd_status = lambda rest: (_ for _ in ()).throw(RuntimeError("boom"))   # (b) raise
        rc, m = _invoke(["status"])
        assert m["outcome"]["status"] == "error" and "boom" in str(m["outcome"]["error"]), "T2b outcome wrong"
        lathe.cmd_status = lambda rest: sys.exit(3)                         # (c) SystemExit
        rc, m = _invoke(["status"])
        assert m["outcome"]["status"] == "refuse" and m["outcome"]["exit_code"] == 3, "T2c outcome wrong"
        emitted.append("T2 un-skippable: return/raise/SystemExit all emitted")
    finally:
        lathe.cmd_status = real_status

    # T3 — structural completeness: every top-level group present, integrity self-hash verifies
    real_status = lathe.cmd_status
    lathe.cmd_status = lambda rest: 0                # network-free: this gate runs on every build
    try:
        rc, m = _invoke(["status"])
        for grp in ("schema_version", "run_id", "invocation", "intake", "front_end", "selection",
                    "contributors", "work", "gates", "models", "usage", "timing", "outcome", "integrity"):
            assert grp in m, "T3 missing group: " + grp
        assert m["schema_version"] == mfmod.SCHEMA_VERSION
        assert m["integrity"]["partial"] is False
        assert core.manifest_hash(m) == m["integrity"]["manifest_sha256"], "T3 self-hash mismatch"
        emitted.append("T3 completeness: all groups + verified self-hash")
    finally:
        lathe.cmd_status = real_status

    # T4 — analyst tokens instrumented: a measured analyst call must be attributed + completeness true
    real_status = lathe.cmd_status
    try:
        def _with_analyst(rest):
            import request_spec as rs
            rs.USAGE_HOOK("analyst", {"prompt_tokens": 4120, "completion_tokens": 2310,
                                      "total_tokens": 6430, "token_source": "measured"})
            return 0
        lathe.cmd_status = _with_analyst
        rc, m = _invoke(["status"])
        u = m["usage"]["tokens"]
        assert u["by_role"]["analyst"]["total"] == 6430, "T4 analyst tokens not attributed"
        assert u["by_role"]["analyst"]["source"] == "measured"
        assert u["completeness"]["all_calls_attributed"] is True
        assert "NOT INSTRUMENTED" not in json.dumps(m), "T4 regression: NOT INSTRUMENTED reappeared"
        # and the inverse: calls WITHOUT tokens must be visibly incomplete, never silently green
        g = core.role_usage({"analyst": {"p": 0, "e": 0, "calls": 3, "src": "n/a"}})
        assert g["tokens"]["completeness"]["all_calls_attributed"] is False
        emitted.append("T4 analyst instrumented + gap visible when unmeasured")
    finally:
        lathe.cmd_status = real_status

    # T5 — imputed cost is role-split and exact (sonnet list price on the T4 token counts)
    c = core.imputed_cost({"analyst": {"p": 4120, "e": 2310}},
                          {"analyst": {"in_per_mtok": 3.0, "out_per_mtok": 15.0}})
    assert abs(c["imputed_by_role"]["analyst"] - 0.04701) < 1e-9, "T5 cost math wrong"
    real_status = lathe.cmd_status
    lathe.cmd_status = lambda rest: 0
    try:
        rc, m = _invoke(["status"])
    finally:
        lathe.cmd_status = real_status
    assert "imputed_total" in m["usage"]["cost_usd"] and "pricebook_version" in m["usage"], "T5 cost absent"
    emitted.append("T5 role-split imputed cost present + exact")

    # T6 — bare goal routes THROUGH the contract (stub cmd_do so no model call happens)
    real_do = lathe.cmd_do
    try:
        lathe.cmd_do = lambda argv: 0
        rc, m = _invoke(["just a bare goal, no subcommand"])
        assert m["invocation"]["routed_via"] == "bare-goal" and m["invocation"]["is_bare_goal"] is True, \
            "T6 bare goal not stamped"
        emitted.append("T6 bare command routed through the contract")
    finally:
        lathe.cmd_do = real_do

    # T7 — a workflow-backed command records the RESOLVED workflow in the intake header (MANIFEST_DESIGN §1;
    # reviewer's Phase-2a gap). `review` is contracted to code-review; stub its steps to stay network-free.
    real_review, real_gate = lathe.cmd_review, lathe.cmd_gate
    try:
        lathe.cmd_review = lambda rest: 0
        lathe.cmd_gate = lambda rest: 0
        rc, m = _invoke(["review", "somefile.py"])
        assert m["intake"]["skill"] == "code-review", "T7 intake.skill not recorded: %r" % m["intake"]["skill"]
        assert isinstance(m["intake"]["workflow_steps"], list) and m["intake"]["workflow_steps"], \
            "T7 intake.workflow_steps not recorded"
        emitted.append("T7 resolved workflow named in intake header")
    finally:
        lathe.cmd_review, lathe.cmd_gate = real_review, real_gate

    print("; ".join(emitted))
    print("manifest contract: %d/6 probes pass" % len(emitted))


if __name__ == "__main__":
    main()
