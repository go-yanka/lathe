"""pristine_gate — the tree must stay PRISTINE, enforced, GIT-INDEPENDENT.

Cleanliness is a property of the working tree itself, not something we lean on git to keep. So this gate
fails (exit 1) if the source tree contains code that should never be there: a plan file that does not parse
as Python (corrupt/half-written), or a generated module that does not parse. Such files pollute enumeration,
mislead the next build, and are exactly the rot that accumulates over iterations. `lathe clean` quarantines
them to _archive/ (also git-free). Clean tree -> exit 0.

  python qa/pristine_gate.py            # gate mode
  python qa/pristine_gate.py --list     # list offenders
"""
import ast
import os
import sys

_QA = os.path.dirname(os.path.abspath(__file__))
_INNER = os.path.dirname(_QA)


def _unparseable(paths):
    bad = []
    for p in paths:
        try:
            ast.parse(open(p, encoding="utf-8").read())
        except Exception as e:
            bad.append((p, "%s: %s" % (type(e).__name__, str(e)[:60])))
    return bad


_SKIP = ("_archive", "_legacy", "_retired", "_fn_fails", "__pycache__", ".git")


def _py_under(*parts):
    """Every .py under a dir, RECURSIVELY — a corrupt file hidden in a subdir must not sail through a flat glob;
    skips quarantine/cache dirs (their contents are intentionally retired and may not parse)."""
    root = os.path.join(_INNER, *parts)
    out = []
    for dp, dns, fns in os.walk(root):
        if any(s in dp.replace("\\", "/").split("/") for s in _SKIP):
            continue
        for fn in fns:
            if fn.endswith(".py") and not fn.startswith("test_"):
                out.append(os.path.join(dp, fn))
    return out


def offenders():
    return _unparseable(_py_under("plans") + _py_under("tools"))


def main(argv):
    bad = offenders()
    if "--list" in argv:
        for p, why in bad:
            print("  %s  (%s)" % (p, why))
        return 0
    if not bad:
        print("pristine_gate: clean - every plan and module parses (no corrupt/half-written files in the tree).")
        return 0
    print("pristine_gate: %d UNPARSEABLE file(s) in the source tree." % len(bad))
    print("Recover (git-free): run `python lathe.py clean` from the harness root, OR move each file below to")
    print("_archive/<date>-<reason>/ by hand and re-run this gate:")
    for p, why in bad:
        print("  - %s  (%s)" % (os.path.relpath(p, _INNER), why))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
