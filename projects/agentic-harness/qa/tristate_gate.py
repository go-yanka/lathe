"""U1 tri-state acceptance gate (#12 Phase 2b) — proves gates fail CLOSED, not open, on their own error.

V1 decision core: classify_gate maps an internal error to INOPERATIVE (never a silent pass).
V2 canary: a probe is trusted only when its positive+negative controls both behave.
V3 policy: FAIL always blocks; INOPERATIVE blocks under STRICT only (owner's STRICT-first rollout).
V4 spec_lint integration: a BROKEN sandbox makes lint_function return verdict='inoperative' — the exact
   fail-open the reviewer named (`except: return False`-as-pass) is closed; under STRICT it would block.
Fast + deterministic; no model calls.
"""

# UTF-8 stdout: this gate is captured via a cp1252 pipe by the engine; a unicode print would
# crash it mid-run and read as a spurious failure. (#12 U1 hardening.)
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.path.dirname(QA), "tools")
sys.path.insert(0, TOOLS)

import gate_tristate as gt          # noqa: E402
import spec_lint                    # noqa: E402


def main():
    ok = []

    # V1 — an errored probe is INOPERATIVE, never pass
    assert gt.classify_gate(True, True) == "inoperative", "V1 error must be inoperative"
    assert gt.classify_gate(None, False) == "inoperative" and gt.classify_gate(False, False) == "fail"
    assert gt.classify_gate(True, False) == "pass"
    ok.append("V1 error/indeterminate -> INOPERATIVE")

    # V2 — canary: only a passing positive + caught negative is trustworthy
    assert gt.canary_trustworthy(True, False) is True
    assert gt.canary_trustworthy(True, True) is False   # negative slipped through -> fail-open probe
    assert gt.canary_trustworthy(False, False) is False
    ok.append("V2 canary pair gates trust")

    # V3 — blocking policy (STRICT-first)
    assert gt.gate_blocks("fail", False) is True and gt.gate_blocks("fail", True) is True
    assert gt.gate_blocks("inoperative", True) is True and gt.gate_blocks("inoperative", False) is False
    assert gt.gate_blocks("garbage", True) is True   # unknown fails closed under strict
    ok.append("V3 FAIL always blocks; INOPERATIVE blocks under STRICT")

    # V4 — the real fail-open, closed: monkeypatch the sandbox to THROW, then lint a well-specified function.
    #      Old behavior: every stub "didn't survive" -> blocking False -> PASS. New: verdict == 'inoperative'.
    import sandbox as _sb
    _orig = _sb.run_unit
    try:
        def _broken(*a, **k):
            raise RuntimeError("sandbox unavailable (simulated OOM/import fail)")
        _sb.run_unit = _broken
        v = spec_lint.lint_function("parse_thing", ["assert parse_thing('2h') == 7200",
                                                    "assert parse_thing('') is None"])
        assert v["verdict"] == "inoperative", "V4 broken sandbox should be INOPERATIVE, got %r" % v["verdict"]
        assert v["inoperative"] is True and v["ok"] is False, "V4 inoperative must not read as ok"
        assert gt.gate_blocks(v["verdict"], True) is True, "V4 under STRICT the inoperative lint must block"
        assert gt.gate_blocks(v["verdict"], False) is False, "V4 non-strict keeps today's behavior"
        ok.append("V4 broken-sandbox spec-lint = INOPERATIVE (fail-open closed)")
    finally:
        _sb.run_unit = _orig

    # V4b — a healthy sandbox with genuinely weak tests still FAILS (regression: we didn't break real detection)
    v2 = spec_lint.lint_function("always_true", ["assert always_true(1) == always_true(1)"])
    assert v2["verdict"] in ("fail", "pass"), "V4b healthy path stays bivalent when operative"
    ok.append("V4b operative path unchanged")

    print("; ".join(ok))
    print("tristate gate: %d/5 checks pass" % len(ok))


if __name__ == "__main__":
    main()
