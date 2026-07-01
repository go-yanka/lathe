"""A3 tests — executable spec for the autonomous driver (checkpoint + goal loop composed).
Deterministic: stub build + stub judge, real git checkpoints in a temp repo.
Run: python tools/test_driver.py"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from driver import drive, make_dod
from checkpoint import list_checkpoints


def _new_repo():
    d = tempfile.mkdtemp(prefix="driver_test_")
    for args in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"], ["git", "config", "user.name", "t"]):
        subprocess.run(args, cwd=d, capture_output=True, check=True)
    open(os.path.join(d, "seed.txt"), "w").write("seed\n")  # something to snapshot
    return d


def main():
    judge_pass = lambda goal, res: ("PASS" in res, "green" if "PASS" in res else "no")

    # 1. drive to DONE: build fails twice, passes turn 3; a checkpoint is taken before EACH attempt
    repo = _new_repo()
    seq = ["FAIL", "FAIL", "PASS gates 6/6"]
    r = drive("make gates green", lambda t, last: seq[t - 1], repo=repo, judge=judge_pass, max_turns=10)
    assert r["outcome"] == "done" and r["turns"] == 3, f"drive should finish at turn 3: {r}"
    assert r["checkpoints"] == 3, f"expected 3 checkpoints (one per attempt), got {r['checkpoints']}"
    # checkpoints really exist in the repo
    assert len(list_checkpoints(repo)) == 3, "checkpoints not persisted in repo"

    # 2. drive ESCALATES on a stuck build (anti-thrash), still having checkpointed
    repo2 = _new_repo()
    r2 = drive("fix it", lambda t, last: "SAME ERROR", repo=repo2, judge=lambda g, x: (False, "no"), max_turns=20)
    assert r2["outcome"] == "escalate" and r2["turns"] == 3, f"should escalate at turn 3: {r2}"
    assert r2["checkpoints"] == 3 and len(list_checkpoints(repo2)) == 3

    # 3. driver returns the loop's reason + a checkpoints count on every path
    assert "reason" in r and "checkpoints" in r

    # 4. DoD gate (A7): gated-green but the product does NOT boot -> downgraded to escalate
    repo3 = _new_repo()
    failing_dod = lambda: (False, "NOT road-ready — failed at import: boom")
    r4 = drive("ship it", lambda t, last: "PASS gates 2/2", repo=repo3, judge=judge_pass,
               max_turns=5, dod=failing_dod)
    assert r4["outcome"] == "escalate" and "NOT road-ready" in r4["reason"], f"DoD must block: {r4}"

    # 5. DoD gate: gated-green AND boots -> stays done, reason notes road-ready
    repo4 = _new_repo()
    ok_dod = lambda: (True, "road-ready (import, boot+health)")
    r5 = drive("ship it", lambda t, last: "PASS gates 2/2", repo=repo4, judge=judge_pass,
               max_turns=5, dod=ok_dod)
    assert r5["outcome"] == "done" and "road-ready" in r5["reason"], f"DoD pass must keep done: {r5}"

    # 6. make_dod returns None for an empty spec (pure-lib plans: unit gates are the whole bar)
    assert make_dod({}, ".") is None and make_dod(None, ".") is None

    # 7. make_dod builds a runnable DoD from an import spec (real, against a broken temp module)
    broken = tempfile.mkdtemp()
    open(os.path.join(broken, "bad.py"), "w").write("def x(:\n")
    dod = make_dod({"import": "bad", "cwd": "."}, broken)
    ok, detail = dod()
    assert ok is False and "import" in detail, f"make_dod import stage should fail: {detail}"

    print("A3 driver: ALL 7 ASSERTIONS PASS — checkpoint+loop composed, A7 DoD gate "
          "(green-but-won't-boot -> escalate), make_dod builder.")


if __name__ == "__main__":
    main()
