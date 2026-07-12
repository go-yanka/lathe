import os, subprocess, sys, tempfile
PY, ROOT = sys.executable, os.path.dirname(os.path.abspath(__file__))
fails = []
for cmd in ("ack", "assume", "trace"):
    with tempfile.TemporaryDirectory() as td:
        sentinel = os.path.join(td, "PWNED")
        plan = os.path.join(td, "evil_plan.py")
        with open(plan, "w", encoding="utf-8") as f:
            f.write("open(%r, 'w').write('x')\n" % sentinel)      # top-level RCE side effect
            f.write("MODULE_NAME = 'm'\nOUT_DIR = '.'\n")
            f.write("FUNCTIONS = [{'name': 'f', 'prompt': 'p', 'tests': ['assert True']}]\n")
        r = subprocess.run([PY, os.path.join(ROOT, "lathe.py"), cmd, plan],
                           cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        out = (r.stdout or "") + (r.stderr or "")
        executed = os.path.exists(sentinel)                        # did the RCE fire?
        refused  = ("REFUSING" in out) and r.returncode != 0
        ok = refused and not executed
        print("  %-8s %s  (refused=%s executed=%s rc=%s)" % (cmd, "PASS" if ok else "FAIL",
              refused, executed, r.returncode))
        if not ok:
            fails.append(cmd)
print("\n#36 RCE-guard canary:", "ALL PASS — intact" if not fails
      else "FAILED: %s  <-- SECURITY REGRESSION, do not ship" % ", ".join(fails))
sys.exit(1 if fails else 0)
