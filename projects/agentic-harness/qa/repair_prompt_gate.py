"""repair_prompt_gate.py — loop #2 proof: a targeted-repair prompt carries the EXACT failure + the failed code
+ a fix-only instruction (so a retry converges instead of re-rolling blind).

Proves build() embeds the specific failure text, the previous code, the "fix ONLY / do not rewrite" directive,
and a raw-file output contract; that reason_from() picks structural vs functional correctly; and that a huge
file is truncated (stays in context). This is the difference between the helicopter failing 3 blind ways and
being handed "you used 0.018, the spec said 500 — fix that".
"""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(QA), "tools"))
import repair_prompt as rp   # noqa: E402


def main():
    problems = []

    task = "Helicopter game. Use gravity +500, thrust -800 (net -300). Score increases with distance."
    code = "<!doctype html><script>var GRAVITY=0.018; var THRUST=-0.038;</script>"
    reason = ("FUNCTIONAL/behavioral test failed: {'hold':'Space','expect':'up'} -> expected foreground to "
              "move UP (dy=143.8, need<-19.2)")
    p = rp.build(task, code, reason)

    if reason[:40] not in p:
        problems.append("repair prompt does not contain the exact failure reason")
    if "var GRAVITY=0.018" not in p:
        problems.append("repair prompt does not contain the previous failed code")
    if task[:30] not in p:
        problems.append("repair prompt does not restate the task/spec")
    low = p.lower()
    if "fix only" not in low or "do not" not in low:
        problems.append("repair prompt lacks the 'fix only / do not rewrite' directive")
    if "output contract" not in low or "markdown" not in low:
        problems.append("repair prompt lacks a raw-file output contract")

    # reason_from: structural vs functional selection.
    r1 = rp.reason_from(["missing <canvas>", "no <script>"], "", structural_ok=False)
    if "STRUCTURAL" not in r1 or "missing <canvas>" not in r1:
        problems.append("reason_from did not report structural fails: %r" % r1)
    r2 = rp.reason_from([], "copter fell holding Space", structural_ok=True)
    if "FUNCTIONAL" not in r2 or "copter fell" not in r2:
        problems.append("reason_from did not report the functional detail: %r" % r2)

    # truncation: a huge file is capped.
    big = "x" * 50000
    pb = rp.build(task, big, reason, max_code=16000)
    if "truncated" not in pb or len(pb) > 30000:
        problems.append("repair prompt did not truncate a huge file (len=%d)" % len(pb))

    # never raises on None.
    try:
        rp.build(None, None, None)
    except Exception as e:
        problems.append("build raised on None input: %s" % e)

    if problems:
        print("repair-prompt gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)
    print("repair-prompt gate: PASS — targeted-repair prompt carries the exact failure + failed code + fix-only "
          "directive + output contract; reason_from picks structural/functional; truncates; never raises")
    sys.exit(0)


if __name__ == "__main__":
    main()
