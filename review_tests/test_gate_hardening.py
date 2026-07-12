"""ACCEPTANCE — the four fail-open / crash shakedown findings:

  #39  run_gates retried EVERY gate, so an intermittently-REAL failure in a DETERMINISTIC gate cleared on
       re-run and shipped green. Retries must be scoped to the HEAVY browser gates only.
  #40  int(GATE_RETRIES)/int(GATE_TIMEOUT) had no guard — a blank/typo env var crashed the whole regression.
       _int_env must fall back + warn, and reject negatives.
  #41  artifact/web-only builds (module_ok=False) SKIPPED the standing regression and still shipped green.
       The regression must run whenever the build produced output (module OR artifacts).
  #42  an integration-test TIMEOUT shipped as a GREEN build. build_ok must reject a non-optional TIMEOUT.

#40 is a live unit test of the shipped helper; #39/#41/#42 assert the fix is present in the shipped source
(their full behavioral paths need a model build). Model-free. Run:  python review_tests/test_gate_hardening.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATES = os.path.join(ROOT, "projects", "agentic-harness", "qa", "run_gates.py")
ENGINE = os.path.join(ROOT, "engine_v2.py")
fails = []


def check(name, ok, detail=""):
    print("  %-66s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


# ---- #40: _int_env is a live, crash-proof env reader ----
import importlib.util
spec = importlib.util.spec_from_file_location("run_gates", GATES)
rg = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(rg)
    _loaded = True
except SystemExit:
    _loaded = True          # run_gates has no main-guard side effects at import beyond defs; tolerate
except Exception as e:
    _loaded = False
    check("#40 run_gates imports", False, str(e))

if _loaded and hasattr(rg, "_int_env"):
    for env, default, want, label in [
        (None, 5, 5, "unset -> default"),
        ("", 5, 5, "blank -> default"),
        ("foo", 5, 5, "non-int -> default (no crash)"),
        ("-1", 5, 5, "negative -> default (would break range/timeout)"),
        ("7", 5, 7, "valid int -> parsed"),
        ("0", 5, 0, "zero -> honored (disables retries)"),
    ]:
        os.environ.pop("GX", None)
        if env is not None:
            os.environ["GX"] = env
        try:
            got = rg._int_env("GX", default)
        except Exception as e:
            got = "EXC:%s" % e
        check("#40 _int_env %s" % label, got == want, "got %r" % got)
        os.environ.pop("GX", None)
else:
    check("#40 _int_env exists in run_gates", False)

# ---- #39: retries scoped to HEAVY (not every gate) ----
gsrc = open(GATES, encoding="utf-8").read()
check("#39 retries are scoped to HEAVY gates only",
      "_int_env(\"GATE_RETRIES\", 2) if name in HEAVY else 0" in gsrc,
      "retry line is not HEAVY-scoped")
check("#39 GATE_TIMEOUT read through the crash-proof _int_env",
      "_int_env(\"GATE_TIMEOUT\"" in gsrc)
check("#39 the old fail-open 'int(GATE_RETRIES)' is gone",
      'int(os.environ.get("GATE_RETRIES"' not in gsrc)

# ---- #41 + #42: engine source carries the fixes ----
esrc = open(ENGINE, encoding="utf-8").read()
check("#41 regression gates on _produced (module OR artifacts), not module_ok alone",
      ("_produced = module_ok or artifacts_total > 0" in esrc)
      and ("if _produced and os.environ.get(\"SKIP_REGRESSION\")" in esrc))
check("#41 the old module_ok-only regression guard is gone",
      'if module_ok and os.environ.get("SKIP_REGRESSION")' not in esrc)
check("#42 build_ok rejects a non-optional integration TIMEOUT",
      'startswith("TIMEOUT") and not _itest_optional' in esrc)
check("#42 _itest_optional honors INTEGRATION_OPTIONAL + LATHE_ITEST_OPTIONAL",
      ('getattr(plan, "INTEGRATION_OPTIONAL"' in esrc) and ('LATHE_ITEST_OPTIONAL' in esrc))

# ---- #42: env var is registered (keeps env_not_drifted gate green) ----
ecsrc = open(os.path.join(ROOT, "env_catalog.py"), encoding="utf-8").read()
check("#42 LATHE_ITEST_OPTIONAL registered in env_catalog", "LATHE_ITEST_OPTIONAL" in ecsrc)

print("\ngate-hardening acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
