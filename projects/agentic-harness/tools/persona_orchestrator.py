# hand-maintained spine — composes the pinned persona-redesign pure modules into the LIVE selection path.
# I/O glue ONLY: reads the usage ledger + grades from disk, writes the per-run manifest. EVERY decision lives
# in a pinned, test-gated pure module (usage_ledger, persona_select, persona_grade, persona_modes,
# persona_manifest) — this file just wires them to disk and to the goal-relevance pre-filter. NOT
# harness-regeneratable (like persona_spawn.py / plan_validator.py). Backwards-compatible: with no ledger and
# no grades on disk, every candidate is unseen -> UCB1's explore term dominates -> the relevance pool order is
# preserved, i.e. it degrades to plain relevance selection. Rollout is feature-flagged (see is_enabled).
import json
import os

_INNER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # projects/agentic-harness


def _tools_on_path():
    import sys
    _here = os.path.dirname(os.path.abspath(__file__))
    if _here not in sys.path:
        sys.path.insert(0, _here)


def is_enabled():
    """Explore/exploit selection is OPT-IN until validated: env LATHE_PERSONA_UCB=1 or config
    personas.explore_exploit=true. Default OFF keeps the live decider on today's proven path."""
    if str(os.environ.get("LATHE_PERSONA_UCB", "")).strip() in ("1", "true", "yes", "on"):
        return True
    try:
        _root = os.path.dirname(os.path.dirname(_INNER))
        cfg = json.load(open(os.path.join(_root, "lathe.config.json"), encoding="utf-8"))
        return bool((cfg.get("personas") or {}).get("explore_exploit"))
    except Exception:
        return False


def ledger_path():
    return os.path.join(_INNER, "agents", "usage_ledger.jsonl")


def grades_path():
    return os.path.join(_INNER, "agents", "grades.json")


def manifests_dir():
    return os.path.join(_INNER, "agents", "manifests")


def _read_text(path):
    try:
        return open(path, encoding="utf-8").read()
    except Exception:
        return ""


def load_grades():
    """name -> verified grade in [0,1]. Missing/bad file -> {} (all personas cold-start)."""
    try:
        g = json.load(open(grades_path(), encoding="utf-8"))
        out = {}
        for k, v in g.items():
            if isinstance(v, dict):
                v = v.get("grade")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[str(k)] = float(v)
        return out
    except Exception:
        return {}


def relevance_pool(goal, entries, pool_k):
    """Existing goal-relevance ranking (agent_router.score_match) -> the candidate pool UCB1 chooses among.
    Keeps selection ON-TOPIC; UCB1 only balances explore/exploit WITHIN what is relevant. pool_k<=0 -> all."""
    _tools_on_path()
    from agent_router import score_match
    scored = []
    for e in (entries or []):
        try:
            name = e["name"]
            cap = e.get("capability", "")
        except Exception:
            continue
        s = score_match(goal, name.replace("-", " ") + " " + cap) + score_match(goal, name.replace("-", " "))
        if s > 0:
            scored.append((-s, name))
    scored.sort()
    names = [n for _, n in scored]
    return names[:pool_k] if (pool_k and pool_k > 0) else names


def select_live(goal, entries, k, c=1.4, pool_factor=4):
    """The redesigned decider: relevance pre-filter -> UCB1 explore/exploit over the pool, using the usage
    ledger for visit counts and the grades file for the exploitation weight. Returns (selected, considered)
    where `considered` is a list of {name, grade, picked, reason} rows for the manifest. Best-effort: any
    failure -> ([], [])."""
    try:
        _tools_on_path()
        from usage_ledger import parse_usage, persona_stats
        from persona_select import ucb1
        try:
            kk = int(k)
        except Exception:
            return [], []
        if kk <= 0:
            return [], []
        pool = relevance_pool(goal, entries, kk * max(1, int(pool_factor)))   # best-first by relevance
        if not pool:
            return [], []
        records = parse_usage(_read_text(ledger_path()))
        grades = load_grades()
        counts = {name: int(persona_stats(records, name).get("fired", 0)) for name in pool}   # visits = times fired
        total = max(1, sum(counts.values()))
        # UCB1 score per persona (pinned math); TIE-BREAK BY RELEVANCE RANK, not name — so at cold-start
        # (all unseen -> all +inf) the most-relevant persona wins, and relevance still breaks later ties.
        ranked = []
        for rank, name in enumerate(pool):
            score = ucb1(grades.get(name, 0.0), counts.get(name, 0), total, c)
            ranked.append((0 if score == float("inf") else 1, -score if score != float("inf") else 0.0, rank, name))
        ranked.sort()
        selected = [name for _, _, _, name in ranked[:kk]]
        sel_set = set(selected)
        considered = []
        for name in pool:
            cnt = counts.get(name, 0)
            reason = "explore (unseen)" if cnt == 0 else "exploit (grade=%.2f, n=%d)" % (grades.get(name, 0.0), cnt)
            considered.append({"name": name, "grade": float(grades.get(name, 0.0)),
                               "picked": name in sel_set, "reason": reason})
        return selected, considered
    except Exception:
        return [], []


def record_run(goal, considered, selected, contributions, run_id):
    """Append one usage row per considered persona to the ledger, and write the per-run manifest. All decisions
    (row shape, manifest shape) are made by the pinned pure modules; this only persists them. Returns the
    manifest dict (or {} on failure). Best-effort — never raises into the caller."""
    manifest = {}
    try:
        _tools_on_path()
        from usage_ledger import usage_record
        from persona_manifest import build_manifest, render_manifest
        sel_set = set(selected or [])
        try:
            os.makedirs(os.path.dirname(ledger_path()), exist_ok=True)
            with open(ledger_path(), "a", encoding="utf-8") as f:
                for row in (considered or []):
                    name = row.get("name") if isinstance(row, dict) else None
                    contrib = 0
                    if isinstance(contributions, dict):
                        try:
                            contrib = int(contributions.get(name, 0) or 0)
                        except Exception:
                            contrib = 0
                    rec = usage_record(name, run_id, True, name in sel_set, contrib, contrib, "")
                    f.write(json.dumps(rec) + "\n")
        except Exception:
            pass
        manifest = build_manifest(goal, considered, selected, contributions or {})
        try:
            os.makedirs(manifests_dir(), exist_ok=True)
            open(os.path.join(manifests_dir(), str(run_id) + ".md"), "w", encoding="utf-8").write(
                render_manifest(manifest))
        except Exception:
            pass
    except Exception:
        pass
    return manifest
