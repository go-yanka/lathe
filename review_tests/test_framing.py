"""ACCEPTANCE — issue #48: `lathe clarify` asks the project-FRAMING questions (purpose/users/scope/
deliverable/stack/hosting) and writes a 'Framing' section to CLARIFIED_GOAL.md; a goal that already states a
dimension isn't re-asked. Tests the pure framing helpers + statically verifies the wiring into cmd_clarify.
Model-free.

  Run:  python review_tests/test_framing.py     (repo root)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
fails = []


def check(name, ok, detail=""):
    print("  %-66s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


import framing  # noqa: E402

# 1) the six dimensions are present and ask-ordered
keys = [d["key"] for d in framing.FRAMING]
check("all six framing dimensions present", keys == ["purpose", "users", "scope", "deliverable", "stack", "hosting"], str(keys))

# 2) prefill SKIPS dimensions the goal clearly states (not re-asked)
pf = framing.prefill("Build a CLI tool in Python, deployed with Docker, as a production service")
check("prefill detects deliverable=CLI from the goal", pf.get("deliverable") == "CLI tool", str(pf))
check("prefill detects stack=python from the goal", "python" in (pf.get("stack") or ""), str(pf))
check("prefill detects hosting=Docker from the goal", "Docker" in (pf.get("hosting") or ""), str(pf))
check("prefill detects scope=production from the goal", pf.get("scope") == "production-ready", str(pf))

# 3) prefill is CONSERVATIVE on a vague goal (asks, doesn't guess)
pf2 = framing.prefill("sort a list of numbers")
check("prefill is conservative — vague goal pins few/no dimensions", len(pf2) <= 1, str(pf2))

# 4) render_md emits all six dimensions; unanswered -> 'unspecified' (honest, not a silent guess)
md = framing.render_md({"purpose": "learning exercise", "deliverable": "CLI tool"})
check("render_md has a Framing header", "## Framing" in md, md[:60])
check("render_md shows an answered dimension", "learning exercise" in md, md)
check("render_md marks unanswered dimensions 'unspecified'", md.count("unspecified") >= 3, md)

# 5) framing_summary is a compact one-liner of pinned dims only
s = framing.framing_summary({"purpose": "a SaaS / product", "stack": "python"})
check("framing_summary lists only answered dims", ("saas" in s.lower()) and ("unspecified" not in s), s)

# 6) STATIC: cmd_clarify is wired to the framing round + writes the section
src = open(os.path.join(ROOT, "lathe.py"), encoding="utf-8").read()
check("cmd_clarify imports the framing round", "from framing import FRAMING" in src)
check("cmd_clarify emits the Framing section to CLARIFIED_GOAL.md", "_framing_section" in src and "_fr_md(_framing)" in src)
check("cmd_clarify offsets scripted answers by the framing round", "_fr_off + i - 1" in src)

print("\nframing (#48) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
