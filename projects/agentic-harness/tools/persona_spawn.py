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
    r = subprocess.run(["curl", "-s", "-m", "8", "--connect-timeout", "3", url], capture_output=True, text=True,
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


def ratings_path():
    return os.path.join(_INNER, "agents", "ratings.json")


def load_ratings():
    """#39 — measured persona performance (0..10 per name). Per-user runtime data (gitignored)."""
    try:
        return json.load(open(ratings_path(), encoding="utf-8"))
    except Exception:
        return {}


def save_rating(name, score, need):
    r = load_ratings()
    r[name] = {"rating": round(float(score), 2), "need": need}
    open(ratings_path(), "w", encoding="utf-8").write(json.dumps(r, indent=1))
    return r[name]


def persona_overrides():
    """#43 — user steering for the persona market, from lathe.config.json:
        "personas": {"priority": {"<name>": <weight>}, "mandatory": ["<name>", ...]}
    Returns (priority_dict, mandatory_list); missing/invalid config -> ({}, [])."""
    try:
        _root = os.path.dirname(os.path.dirname(_INNER))
        cfg = json.load(open(os.path.join(_root, "lathe.config.json"), encoding="utf-8"))
        p = cfg.get("personas") or {}
        prio = {k: v for k, v in (p.get("priority") or {}).items()
                if isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool)}                if isinstance(p.get("priority"), dict) else {}
        mand = [m for m in p.get("mandatory") if isinstance(m, str) and m.strip()]                if isinstance(p.get("mandatory"), list) else []
        return prio, mand
    except Exception:
        return {}, []


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
        from agent_router import score_match, spawn_candidates
        from persona_overrides import apply_overrides
        from persona_ratings import apply_ratings
        cat = json.load(open(os.path.join(_INNER, "agents", "catalog.json"), encoding="utf-8"))
        ents = cat.get("agents", [])
        _names = {e["name"] for e in ents}
        prio, mand = persona_overrides()                      # #43: user priority weights + always-on personas
        _mand_present = [m for m in mand if m in _names]
        try:
            import persona_orchestrator as _orch                # issue #9: explore/exploit selection (opt-in)
        except Exception:
            _orch = None
        if _orch is not None and _orch.is_enabled():
            # redesigned decider: relevance pre-filter -> UCB1 explore/exploit over the usage ledger + verified
            # grades, then honour the always-on mandatory set. Records the run (ledger + per-run manifest).
            from persona_modes import apply_selection_overrides
            _selected, _considered = _orch.select_live(goal_text, ents, k)
            picked = apply_selection_overrides(_selected, [], [], _mand_present)
            try:
                _orch.record_run(goal_text, _considered, picked, {}, os.environ.get("LATHE_RUN_ID", "adhoc"))
            except Exception:
                pass
        else:
            scored = [[e["name"], score_match(goal_text, e["name"].replace("-", " ") + " " + e.get("capability", ""))
                       + score_match(goal_text, e["name"].replace("-", " "))]
                      for e in ents]                      # name overlap counted AGAIN: a specialist's NAME is signal
            _r = {n: v.get("rating") for n, v in load_ratings().items() if isinstance(v, dict)}
            scored = apply_ratings(scored, _r)                # #39: measured performance reweights the market
            picked = apply_overrides(scored, prio, _mand_present, k)
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
    except Exception as _e:
        import sys as _s
        _s.stderr.write("persona auto-spawn disabled by error: %r\n" % (_e,))   # a dead market must be VISIBLE
        return []
