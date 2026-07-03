"""Test the on-demand persona fetch-and-create MECHANISM (the '--spawn' path), with only the GitHub
network call mocked — because api.github.com returns 403 in this sandbox, the happy-path fetch can't be
exercised live. This isolates and verifies the real logic: decider picks a NON-vendored persona -> license
gate -> pull the persona body -> decode -> store it + its LICENSE + attribution -> instantiate.

It does NOT claim the review/planner deciders AUTO-trigger this — they don't (verified separately). Here the
decider->spawn chain is wired by hand to prove the pieces work end-to-end when a source is reachable.
"""
import base64
import importlib.util
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "projects", "agentic-harness", "tools")
sys.path.insert(0, TOOLS)

spec = importlib.util.spec_from_file_location("lathe_mod", os.path.join(ROOT, "lathe.py"))
lathe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lathe)

# redirect fetch/license dirs to temp so we don't pollute the repo
tmp = tempfile.mkdtemp(prefix="persona_fetch_")
CACHE, LICDIR = os.path.join(tmp, "_fetched"), os.path.join(tmp, "licenses")
lathe._agent_dirs = lambda: (CACHE, LICDIR)

PERSONA_MD = "# backend-architect\nYou are a rigorous backend architecture reviewer. Find design flaws.\n"
LICENSE_TXT = "MIT License\n\nCopyright (c) 2025 wshobson\nPermission is hereby granted...\n"


def fake_gh_json(url):
    # mock ONLY the network — mimic the exact GitHub API JSON shape _spawn_one/_store_license parse
    if url.endswith("/license"):
        return {"license": {"spdx_id": "MIT"}, "content": base64.b64encode(LICENSE_TXT.encode()).decode()}
    if "/contents/" in url:
        return {"content": base64.b64encode(PERSONA_MD.encode()).decode()}
    raise RuntimeError("unexpected url: " + url)


lathe._gh_json = fake_gh_json

from agent_router import select_agents_for_goal, license_ok   # noqa: E402

fails = []


def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)


cat = json.load(open(os.path.join(ROOT, "projects", "agentic-harness", "agents", "catalog.json")))["agents"]

# 1) decider picks a persona for a need with NO vendored match -> a non-vendored catalog entry
picked = select_agents_for_goal("backend microservices api distributed architecture",
                                 [[e["name"], e.get("capability", "")] for e in cat], 1)
print("decider picked:", picked)
entry = next((e for e in cat if e["name"] == picked[0]), None)
check(entry is not None and not entry.get("vendored"),
      "decider selected a NON-vendored persona (%s)" % (picked[0] if picked else "none"))
check(entry and license_ok(entry.get("license", "")), "its license is permissive -> fetch allowed")

# 2) tap the library -> pull the code -> create the persona (network mocked)
md, how = lathe._spawn_one(entry)
print("spawn result:", how)
check(bool(md) and os.path.exists(md), "persona .md created on disk (%s)" % how)
check(md and "backend-architect" in open(md, encoding="utf-8").read(), "persona BODY was fetched + decoded")
check(os.path.exists(os.path.join(LICDIR, entry["repo"].replace("/", "__") + ".LICENSE.txt")),
      "source LICENSE stored alongside (compliance)")
check(os.path.exists(os.path.join(CACHE, entry["name"] + ".SOURCE.txt")), "attribution/SOURCE note written")

# 3) license gate must REFUSE a non-permissive persona (no fetch)
bad = next((e for e in cat if e.get("license") == "NOASSERTION"), None)
check(bad is not None and not license_ok(bad.get("license", "")),
      "NOASSERTION persona is refused by the license gate (never auto-fetched)")

# 4) fail-closed: unreachable source + no cache -> refuse, no fabricated file
lathe._gh_json = lambda url: (_ for _ in ()).throw(RuntimeError("network down"))
entry2 = dict(entry, name="graphql-architect")
md2, how2 = lathe._spawn_one(entry2)
check(md2 is None, "unreachable + no cache -> refuses (no fabricated persona): %s" % how2)

import shutil
shutil.rmtree(tmp, ignore_errors=True)
print("\ntest_persona_fetch: %d/%d checks pass" % (5 - len(fails) + 1 if False else (6 - len(fails)), 6))
sys.exit(1 if fails else 0)
