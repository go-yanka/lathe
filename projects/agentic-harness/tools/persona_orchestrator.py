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
    """Explore/exploit selection is ON BY DEFAULT (#9 rollout, validated 143/143 reachable). It replaces the
    word-match path that left ~99/143 personas unreachable, and turns on usage-ledger/grade RECORDING. The
    graceful-degrade fallback still applies (a missing ledger just means all-explore). Explicit opt-out:
    env LATHE_PERSONA_UCB in (0/false/no/off) or config personas.explore_exploit=false."""
    _env = str(os.environ.get("LATHE_PERSONA_UCB", "")).strip().lower()
    if _env in ("0", "false", "no", "off"):
        return False
    if _env in ("1", "true", "yes", "on"):
        return True
    try:
        _root = os.path.dirname(os.path.dirname(_INNER))
        cfg = json.load(open(os.path.join(_root, "lathe.config.json"), encoding="utf-8"))
        _cfg = (cfg.get("personas") or {}).get("explore_exploit")
        if _cfg is not None:
            return bool(_cfg)
    except Exception:
        pass
    return True                              # default ON


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
        update_grades()                       # #18 H2: recompute verified grades from the ledger after each run
    except Exception:
        pass
    return manifest


def record_outcomes(outcomes, run_id):
    """#37: turn per-persona review OUTCOMES into ledger rows with raised/confirmed so update_grades() forms
    real bandit grades — the exploit signal that never populated because the only ledger writer (record_run,
    at SELECTION time) can't know outcomes yet (the review hasn't run). This is the missing post-review
    feedback. `outcomes` maps a persona/lens name to either an engaged flag (bool — an ENGAGED lens produced
    verifiable findings, so it scores 1/1) or a {"raised":int, "confirmed":int} dict for a richer signal.
    A lens that did not engage contributes nothing (raised=0). Returns the grades dict written (or {})."""
    try:
        _tools_on_path()
        from usage_ledger import usage_record
        rows = []
        for name, o in (outcomes or {}).items():
            if not name:
                continue
            if isinstance(o, dict):
                raised = int(o.get("raised", 0) or 0)
                confirmed = int(o.get("confirmed", 0) or 0)
            else:
                raised = confirmed = 1 if o else 0
            if raised <= 0:                               # a lens that didn't engage produced no verifiable work
                continue
            rows.append(usage_record(name, run_id, True, True, raised, confirmed, ""))
        if rows:
            os.makedirs(os.path.dirname(ledger_path()), exist_ok=True)
            with open(ledger_path(), "a", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")
        return update_grades()
    except Exception:
        return {}


def update_grades(prior=0.5, prior_weight=2.0, min_conf=0.5):
    """#18 H2 — turn the usage ledger into work-based grades so grade_update/finding_score are LIVE (not dead
    code) and grades.json is written. A persona's grade is the smoothed mean of its VERIFIED findings: for
    each run it fired, confidence = confirmed/raised (a proxy for 'how many surfaced findings survived
    verification'); finding_score gates it by min_conf; grade_update applies the cold-start prior. Best-effort:
    a persona with no confirmed work keeps the prior. Returns the grades dict written (or {} on failure)."""
    try:
        _tools_on_path()
        from usage_ledger import parse_usage
        from persona_grade import finding_score, grade_update
        records = parse_usage(_read_text(ledger_path()))
        by_persona = {}
        for r in records:
            if not isinstance(r, dict):
                continue
            nm = r.get("persona")
            if not nm or not r.get("fired"):
                continue
            raised = r.get("raised") or 0
            confirmed = r.get("confirmed") or 0
            if raised and raised > 0:                         # only runs that produced verifiable findings score
                conf = min(1.0, float(confirmed) / float(raised))
                s = finding_score({"pass": confirmed > 0, "confidence": conf}, min_conf)
                if s is not None:
                    by_persona.setdefault(nm, []).append(s)
        grades = {}
        for nm, scores in by_persona.items():
            grades[nm] = round(grade_update(prior, prior_weight, scores), 4)
        if grades:
            os.makedirs(os.path.dirname(grades_path()), exist_ok=True)
            _tmp = grades_path() + ".tmp"
            open(_tmp, "w", encoding="utf-8").write(json.dumps(grades, indent=1))
            os.replace(_tmp, grades_path())
        return grades
    except Exception:
        return {}
