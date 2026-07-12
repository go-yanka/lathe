"""review_gate.py (#51) — turn the CE review layer from an optional, read-only end-step into a stage-wired,
CONDITIONAL-MANDATORY, severity-routed GATE.

The 16 CE personas already emit P0-P3 severities; what was missing is routing + enforcement:
  1. CONDITIONAL-MANDATORY applicability — each lens is mandatory WHEN ITS TRIGGER APPLIES (always-core lenses on
     essentially all code; conditional lenses when their domain is detected) — coverage without the noise of
     running data-migration on code with no migration.
  2. SEVERITY-ROUTED verdict — P0/P1 fail-closed (BLOCK), P2 fold/track, P3 record.

Pure + deterministic (routing predicates + severity scan + verdict); the actual lens runs + the fold-into-spec /
Healer loop are wired by the caller. No model, no I/O.
"""
import os
import re

# Fire on essentially all code — the non-negotiable floor.
ALWAYS_CORE = ["correctness", "adversarial", "security", "maintainability", "reliability", "testing"]


def _touches_api(code):
    return bool(re.search(r"@app\.|@router\.|\bFastAPI\b|\bAPIRouter\b|def (get|post|put|delete|patch)\b|"
                          r"\broute\(|\bendpoint\b|@(get|post|put|delete)\b", code, re.I))


def _touches_migration(code):
    return bool(re.search(r"\bmigrat|ALTER TABLE|CREATE TABLE|DROP TABLE|ADD COLUMN|\bschema\b|"
                          r"op\.(create|add|drop|alter)_", code, re.I))


def _touches_persistence(code):
    return bool(re.search(r"\bsqlite3\b|\bpsycopg|\bsqlalchemy|INSERT INTO|UPDATE .+ SET|\.commit\(\)|"
                          r"\bcursor\b|\bMongoClient\b|\bredis\b", code, re.I))


def _touches_async_ui(code):
    return bool(re.search(r"\baddEventListener\b|\buseEffect\b|\bPromise\b|\basync\b|\bawait\b|"
                          r"Turbo|Stimulus|\bfetch\(", code))


def _touches_hot_path(code):
    # a nested loop, or a loop over an explicit collection walk — a plausible hot path worth the performance lens.
    return bool(re.search(r"for .+:\s*\n(\s+.*\n)*?\s+for .+:", code) or re.search(r"while .+:\s*\n(\s+.*\n)*?\s+for", code))


# domain -> predicate(code_text) -> which LENS is mandatory for this code.
# Names MUST be real lens tokens (the decider/hreview vocabulary), because scan_findings_dir looks for
# review_<lens>.txt and hreview only writes a file for a lens it actually ran. A conditional named for a PERSONA
# ("api-contract") would demand review_api-contract.txt that is never written -> the mandatory lens is forever
# "missing" -> a permanent, unclearable BLOCK (#51). So each domain maps to the lens the decider really runs.
CONDITIONAL = [
    ("api", _touches_api),                 # was api-contract
    ("data", _touches_migration),          # was data-migration
    ("data", _touches_persistence),        # was data-integrity-guardian (same lens; dedup handles the repeat)
    ("ui", _touches_async_ui),             # was julik-frontend-races
    ("perf", _touches_hot_path),           # was performance
]


def applicable(code, release=False):
    """The lenses that MUST fire for this code: always-core + every conditional whose trigger fires + (at
    release) project-standards. Deterministic, deduped, order-stable."""
    lenses = list(ALWAYS_CORE)
    for name, pred in CONDITIONAL:
        try:
            if pred(code or ""):
                lenses.append(name)
        except re.error:
            pass
    if release:
        lenses.append("project-standards")
    seen, out = set(), []
    for x in lenses:
        if x not in seen:
            seen.add(x); out.append(x)
    return out


_SEV_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
# hreview forces every finding to `SEVERITY (critical/high/medium/low) | file | issue | fix` — WORD severities,
# not P-codes. A P-code-only scan therefore reads real reviewer output as CLEAN and the gate FAILS OPEN (#51).
_WORD_TO_P = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def max_severity(text):
    """The most-severe level in a lens's findings text as a P-code (P0 highest), or None if it flagged nothing.
    Reads BOTH P0-P3 literals AND the word severities the live reviewer actually emits (critical/high/medium/
    low), case-insensitively. A word only counts as a finding LABEL — immediately followed by the `<sev> | file
    | ...` pipe (allowing markdown `**`/`]`) or introduced by `SEVERITY` — so prose like 'high latency' or
    'critical path' does NOT false-trigger the gate."""
    s = str(text or "")
    nums = [int(x) for x in re.findall(r"\bP([0-3])\b", s)]
    for m in re.finditer(r"(?i)\b(critical|high|medium|low)\b[\s*\]\)]*\|", s):          # `<sev> | file | issue | fix`
        nums.append(_WORD_TO_P[m.group(1).lower()])
    for m in re.finditer(r"(?i)\bseverity\b[\s:=|\-*\[\(]*\b(critical|high|medium|low)\b", s):   # `SEVERITY: high`
        nums.append(_WORD_TO_P[m.group(1).lower()])
    if not nums:
        return None
    return "P%d" % min(nums)


def count_findings(text):
    """(#37) Count the gradeable findings in a lens's output so the bandit can grade on VALUE FOUND, not just
    'the lens ran': `raised` = lines carrying a real severity label (a P-code or `<word> | …`), `confirmed` =
    those at P0/P1 (the high-value ones). Prose/headers with no severity label don't count. Returns (raised,
    confirmed) with confirmed <= raised."""
    raised = confirmed = 0
    for line in str(text or "").splitlines():
        sev = max_severity(line)
        if sev is not None:
            raised += 1
            if sev in ("P0", "P1"):
                confirmed += 1
    return raised, confirmed


def verdict(findings_by_lens, applicable_lenses=None, waive=None):
    """Severity-routed gate verdict over {lens: findings_text}. Fail-closed on P0/P1.
    Returns {blocked, blockers, missing, by_lens, waived}: `blockers` = lenses at P0/P1; `missing` = mandatory
    lenses that did not run (a mandatory lens that couldn't run is NOT a silent pass — it blocks, like the
    tri-state gates). `waive` is the OPERATOR OVERRIDE — a set/list of lens names the operator CONSCIOUSLY
    accepts (so a genuinely-stuck gate can be cleared on purpose); a waived lens can neither block nor count as
    missing. Pure: the caller reads the env (LATHE_REVIEW_WAIVE) and passes it in."""
    _waive = set(waive or [])
    by = {}
    blockers = []
    for lens, text in (findings_by_lens or {}).items():
        sev = max_severity(text)
        by[lens] = sev or "clean"
        if sev in ("P0", "P1") and lens not in _waive:
            blockers.append((lens, sev))
    missing = [l for l in (applicable_lenses or []) if l not in (findings_by_lens or {}) and l not in _waive]
    blocked = bool(blockers) or bool(missing)
    return {"blocked": blocked, "blockers": blockers, "missing": missing, "by_lens": by, "waived": sorted(_waive)}


def scan_findings_dir(ce_dir, lenses):
    """Read hreview's per-lens findings files (docs/ce/review_<lens>.txt) into {lens: text} for the lenses that
    ran. Missing file => the lens didn't produce findings (absent from the map => the gate treats a MANDATORY
    absent lens as a block via verdict()'s `missing`)."""
    out = {}
    for lens in lenses:
        for cand in ("review_%s.txt" % lens, "%s.txt" % lens):
            p = os.path.join(ce_dir, cand)
            if os.path.isfile(p):
                try:
                    out[lens] = open(p, encoding="utf-8", errors="replace").read()
                except OSError:
                    pass
                break
    return out
