"""dup_report — ADVISORY structural-duplication report (NOT a blocking gate).

Uses the harness-BUILT tools/structural_signature.py to fingerprint every function's AST shape (names and
literals stripped), then groups functions that share a fingerprint ACROSS different modules. That surfaces
'same logic implemented in two places' even when variables were renamed or a loop became a comprehension --
the case naive text/embedding dedup misses (the "shortcut learning" trap).

Advisory on purpose: trivial pure helpers legitimately share a shape, so this REPORTS candidates for review /
for a phase-2 LLM judge to confirm -- it does not fail the build (unlike resource_dups_gate, where a duplicate
DB is always wrong).

  python tools/dup_report.py            # print cross-module duplicate-logic candidates
  python tools/dup_report.py --min N    # only signatures with >= N AST nodes (default 12; filters trivia)
"""
import ast
import os
import sys

_TOOLS = os.path.dirname(os.path.abspath(__file__))
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
from structural_signature import structural_signature  # the harness-built core


def _module_functions(path):
    try:
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src)
    except Exception:
        return []
    out = []
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_"):
            seg = ast.get_source_segment(src, n)
            if seg:
                out.append((n.name, seg))
    return out


def find_duplicate_logic(tools_dir, min_nodes=12):
    """Return {signature: [(module, func), ...]} for every shape shared by >=2 functions (>= min_nodes).
    Cross-module groups are the high-signal ones (same logic in different places); same-module groups are
    lower-signal consolidation candidates. Caller separates them."""
    by_sig = {}
    for fn in sorted(os.listdir(tools_dir)):
        if not fn.endswith(".py") or fn.startswith(("_", "test_")):
            continue
        for name, seg in _module_functions(os.path.join(tools_dir, fn)):
            sig = structural_signature(seg)
            if sig and sig.count(",") + 1 >= min_nodes:            # skip trivially-short shapes (noise)
                by_sig.setdefault(sig, []).append((fn[:-3], name))
    return {sig: hits for sig, hits in by_sig.items() if len(hits) >= 2}


def main(argv):
    min_nodes = 12
    if "--min" in argv:
        try:
            min_nodes = int(argv[argv.index("--min") + 1])
        except Exception:
            pass
    groups = find_duplicate_logic(_TOOLS, min_nodes)
    cross = {s: h for s, h in groups.items() if len({m for m, _ in h}) >= 2}
    same = {s: h for s, h in groups.items() if len({m for m, _ in h}) == 1}
    if not groups:
        print("dup_report: no duplicate-logic candidates (>= %d AST nodes). Generated code is structurally distinct." % min_nodes)
        return 0
    print("dup_report (advisory — review/consolidate, not a build blocker):")
    if cross:
        print(" CROSS-MODULE (same logic in different places — higher priority):")
        for i, (sig, hits) in enumerate(sorted(cross.items(), key=lambda kv: -len(kv[1])), 1):
            print("  %d. shape(%d nodes): %s" % (i, sig.count(",") + 1, ", ".join("%s.%s" % h for h in hits)))
    if same:
        print(" SAME-MODULE (possible local consolidation):")
        for i, (sig, hits) in enumerate(sorted(same.items(), key=lambda kv: -len(kv[1])), 1):
            print("  %d. shape(%d nodes): %s" % (i, sig.count(",") + 1, ", ".join("%s.%s" % h for h in hits)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
