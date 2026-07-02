# hand-maintained spine — I/O glue for the on-demand persona fetch (GitHub + disk), NOT harness-regeneratable.
# ONE canonical copy (was lathe.py's private helpers; moved here so BOTH the CLI (`lathe agent`) and the
# in-flow deciders (review auto + planner, D7) share it — vendor-don't-fork, no duplication).
# The pure DECISIONS stay harness-built in agent_router.py (license_ok, spawn_candidates); this file only
# does the fetching/mirroring around them. License compliance: every fetch stores the source repo's LICENSE
# + a SOURCE attribution note next to the cached persona (see agents/catalog.json _meta.compliance).
import base64
import json
import os

_INNER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # projects/agentic-harness


def agent_dirs():
    return os.path.join(_INNER, "agents", "_fetched"), os.path.join(_INNER, "agents", "licenses")


def gh_json(url):
    import subprocess
    r = subprocess.run(["curl", "-s", "-m", "25", url], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return json.loads(r.stdout)


def store_license(repo):
    """Download the source repo's LICENSE locally (compliance — kept alongside any cached agent). Best-effort."""
    _, lic_dir = agent_dirs()
    dest = os.path.join(lic_dir, repo.replace("/", "__") + ".LICENSE.txt")
    try:
        d = gh_json("https://api.github.com/repos/%s/license" % repo)
        os.makedirs(lic_dir, exist_ok=True)
        open(dest, "w", encoding="utf-8").write("Source repo: %s  (SPDX: %s)\n\n" % (repo, d.get("license", {}).get("spdx_id", "")) +
                                                base64.b64decode(d["content"]).decode("utf-8", "replace"))
        return True
    except Exception:
        return os.path.exists(dest)      # already have a copy -> fine

def spawn_one(e):
    """Refresh the agent .md from source if reachable, else use the local copy; ALWAYS keep its license. Compliant + resilient."""
    cache, _ = agent_dirs()
    os.makedirs(cache, exist_ok=True)
    md = os.path.join(cache, e["name"] + ".md")
    fresh = False
    try:                                  # try to refresh to latest before launch
        d = gh_json("https://api.github.com/repos/%s/contents/%s" % (e["repo"], e["path"]))
        _content = base64.b64decode(d["content"]).decode("utf-8", "replace")   # decode BEFORE opening — a failed fetch must not truncate/create the file
        open(md, "w", encoding="utf-8").write(_content); fresh = True
    except Exception:
        fresh = False
    if not os.path.exists(md):
        return None, "source unreachable and no local copy cached"
    store_license(e["repo"])
    open(os.path.join(cache, e["name"] + ".SOURCE.txt"), "w", encoding="utf-8").write(
        "%s\nsource: %s (%s)\npath: %s\nused under its %s license (see ../licenses/%s.LICENSE.txt).\n"
        % (e["name"], e["repo"], e["license"], e["path"], e["license"], e["repo"].replace("/", "__")))
    return md, ("refreshed from source" if fresh else "used local cache (source unreachable)")


def auto_spawn_for_goal(goal_text, k=2):
    """D7 — the decider's auto-fetch: match the goal against the FULL catalog; for the top picks that are
    non-vendored + license-permissive (harness-built spawn_candidates decides — fail closed), pull each
    persona body on demand. Returns [(name, md_path, body)] for every persona actually available on disk.
    Vendored picks are skipped here (the callers already carry the vendored lenses). Best-effort: any
    failure returns [] rather than blocking the review/plan."""
    try:
        import sys
        _here = os.path.dirname(os.path.abspath(__file__))
        if _here not in sys.path:
            sys.path.insert(0, _here)
        from agent_router import select_agents_for_goal, spawn_candidates
        cat = json.load(open(os.path.join(_INNER, "agents", "catalog.json"), encoding="utf-8"))
        ents = cat.get("agents", [])
        picked = select_agents_for_goal(goal_text, [[e["name"], e.get("capability", "")] for e in ents], k)
        todo = spawn_candidates(picked, [[e["name"], bool(e.get("vendored")), e.get("license")] for e in ents])
        by = {e["name"]: e for e in ents}
        out = []
        for name in todo:
            md, _how = spawn_one(by[name])
            if md:
                try:
                    out.append((name, md, open(md, encoding="utf-8", errors="replace").read()))
                except OSError:
                    pass
        return out
    except Exception:
        return []
