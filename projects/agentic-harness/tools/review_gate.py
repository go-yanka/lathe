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


# persona -> predicate(code_text) -> is it mandatory for this code?
CONDITIONAL = [
    ("api-contract", _touches_api),
    ("data-migration", _touches_migration),
    ("data-integrity-guardian", _touches_persistence),
    ("julik-frontend-races", _touches_async_ui),
    ("performance", _touches_hot_path),
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


def max_severity(text):
    """The most-severe P-level mentioned in a lens's findings text (P0 highest), or None if it flagged nothing."""
    found = re.findall(r"\bP([0-3])\b", str(text or ""))
    if not found:
        return None
    return "P%d" % min(int(x) for x in found)


def verdict(findings_by_lens, applicable_lenses=None):
    """Severity-routed gate verdict over {lens: findings_text}. Fail-closed on P0/P1.
    Returns {blocked, blockers, missing, by_lens}: `blockers` = lenses at P0/P1; `missing` = mandatory lenses that
    did not run (a mandatory lens that couldn't run is NOT a silent pass — it blocks, like the tri-state gates)."""
    by = {}
    blockers = []
    for lens, text in (findings_by_lens or {}).items():
        sev = max_severity(text)
        by[lens] = sev or "clean"
        if sev in ("P0", "P1"):
            blockers.append((lens, sev))
    missing = [l for l in (applicable_lenses or []) if l not in (findings_by_lens or {})]
    blocked = bool(blockers) or bool(missing)
    return {"blocked": blocked, "blockers": blockers, "missing": missing, "by_lens": by}


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
