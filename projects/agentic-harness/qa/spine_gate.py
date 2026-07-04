"""Enforcement-spine stress gate (#12 Phase 1) — executable attack probes over the REAL dispatcher.

P1 guard-forge: a hostile pre-set _LATHE_SPINE_RUN must NOT disable the spine (process entry force-clears).
P2 exactly-one-manifest: an inner re-entrant main() call must NOT nest a second manifest.
P3 skill-subprocess: a skill that shells out to lathe gets a FRESH process -> its own full spine + manifest.
P4 operator bypass on the record: LATHE_SPINE=off still emits a manifest recording the bypass.
P5 single-raw-path: _dispatch is underscore-private and called only from main/run_spine (static).
Uses `plans` (read-only, network-free) as the probe command. Fast: 2 subprocess + 2 in-process probes.
"""
import glob
import json
import os
import subprocess
import sys
import time

QA = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(QA)))
TOOLS = os.path.join(os.path.dirname(QA), "tools")
sys.path.insert(0, ROOT)
sys.path.insert(0, TOOLS)

import lathe                                    # noqa: E402
import manifest as mfmod                        # noqa: E402

LATHE = os.path.join(ROOT, "lathe.py")


def _manifests_since(t0):
    return [f for f in glob.glob(os.path.join(mfmod.out_dir(), "*.manifest.json"))
            if os.path.getmtime(f) >= t0]


def main():
    # This gate runs as a SUBPROCESS of the engine's standing regression, which itself may run under an
    # outer `lathe build` spine — so the guard env is inherited here. A real child `lathe` process clears
    # it at its entry (that's the design); this gate calls lathe.main() as a LIBRARY, so it must emulate
    # the process entry the same way before its in-process top-level probes.
    os.environ.pop("_LATHE_SPINE_RUN", None)
    ok = []

    # P1 — guard-forge: forged guard in the env; the subprocess entry must clear it and still emit
    t0 = time.time()
    env = dict(os.environ); env["_LATHE_SPINE_RUN"] = "forged"; env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, LATHE, "plans"], cwd=ROOT, env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=90)
    assert r.returncode == 0, "P1 probe command failed rc=%s" % r.returncode
    assert _manifests_since(t0), "P1 FAIL: forged guard suppressed the manifest (spine bypassed)"
    ok.append("P1 guard-forge defeated")

    # P2 — exactly one manifest per top-level call, even when the handler re-enters main()
    t0 = time.time()
    real_status = lathe.cmd_status
    try:
        lathe.cmd_status = lambda rest: lathe.main(["plans"])   # inner re-entry (like a flow AUTO step)
        rc = lathe.main(["status"])
        n = len(_manifests_since(t0))
        assert n == 1, "P2 FAIL: expected exactly 1 manifest, got %d (guard not suppressing re-wrap)" % n
        ok.append("P2 exactly-one-manifest under re-entry")
    finally:
        lathe.cmd_status = real_status

    # P3 — skill-subprocess attack: shelling out spawns a FRESH spine -> the child emits its OWN manifest
    t0 = time.time()
    try:
        def _shelling_skill(rest):
            e = dict(os.environ); e["PYTHONIOENCODING"] = "utf-8"   # parent guard env inherited on purpose:
            return subprocess.run([sys.executable, LATHE, "plans"], cwd=ROOT, env=e, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=90).returncode
        lathe.cmd_status = _shelling_skill
        rc = lathe.main(["status"])
        n = len(_manifests_since(t0))
        assert n >= 2, "P3 FAIL: child process did not emit its own manifest (got %d)" % n
        ok.append("P3 skill-subprocess gets its own spine")
    finally:
        lathe.cmd_status = real_status

    # P4 — operator bypass is honored but ON THE RECORD
    t0 = time.time()
    env = dict(os.environ); env["LATHE_SPINE"] = "off"; env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, LATHE, "plans"], cwd=ROOT, env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=90)
    new = _manifests_since(t0)
    assert new, "P4 FAIL: bypass emitted no manifest at all"
    m = json.load(open(max(new, key=os.path.getmtime), encoding="utf-8"))
    assert any(g.get("verdict") == "disabled-by-operator" for g in m["gates"]["verdicts"]), \
        "P4 FAIL: bypass not recorded in the manifest"
    ok.append("P4 operator bypass recorded")

    # P5 — single-raw-path invariant (static): _dispatch called only from main()/run_spine
    src = open(LATHE, encoding="utf-8").read()
    calls = [l for l in src.splitlines() if "_dispatch(" in l and "def _dispatch" not in l]
    assert 0 < len(calls) <= 4, "P5 FAIL: unexpected _dispatch call sites: %d" % len(calls)
    assert "def _dispatch(" in src and "def dispatch(" not in src, "P5 FAIL: raw dispatch must stay private"
    ok.append("P5 single raw path")

    print("; ".join(ok))
    print("spine enforced: %d/5 probes pass" % len(ok))


if __name__ == "__main__":
    main()
