"""contract_hygiene_gate.py — MASTER_PLAN B3/B5: the command->contract table carries NO dead decorative data
and every promotion RESOLVES.

WORKFLOWS_MAP found `front_end`/`select` in CONTRACT_FOR were never read (the spine reads only `workflow` and
`gate`) — decorative flags that implied the spine did intake/persona-selection when it doesn't. They were
removed (v2.40.0); front-end + selection actually happen at the command layer (cmd_do / _intake_panel). This
gate keeps the table honest:
  B3  no CONTRACT_FOR entry may carry the retired `front_end`/`select` keys, and every key must be in the known
      allowlist (workflow, gate, writes, argmap) — no new decorative key sneaks in.
  B5  every `workflow` named by a contract MUST exist in WORKFLOWS with non-empty steps (no dangling promotion),
      so `lathe flow <name>`/promotion can never point at a missing workflow.
"""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(QA), "tools"))
import workflows as wf   # noqa: E402

ALLOWED_KEYS = {"workflow", "gate", "writes", "argmap"}
RETIRED_KEYS = {"front_end", "select"}


def main():
    problems = []
    for cmd, c in wf.CONTRACT_FOR.items():
        if not isinstance(c, dict):
            problems.append("%s: contract is not a dict" % cmd); continue
        dead = RETIRED_KEYS & set(c)
        if dead:
            problems.append("%s: carries retired decorative key(s) %s (front_end/select are handled at the command layer)" % (cmd, sorted(dead)))
        unknown = set(c) - ALLOWED_KEYS
        if unknown:
            problems.append("%s: unknown contract key(s) %s (not in %s)" % (cmd, sorted(unknown), sorted(ALLOWED_KEYS)))
        w = c.get("workflow")
        if w:
            steps = (wf.WORKFLOWS.get(w) or {}).get("steps")
            if not steps:
                problems.append("%s: promotes workflow %r which is MISSING or has no steps (dangling promotion)" % (cmd, w))

    if problems:
        print("contract-hygiene gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)
    promos = sum(1 for c in wf.CONTRACT_FOR.values() if isinstance(c, dict) and c.get("workflow"))
    print("contract-hygiene gate: PASS — %d contracts, no dead front_end/select flags, all %d promotions "
          "resolve to a real workflow" % (len(wf.CONTRACT_FOR), promos))
    sys.exit(0)


if __name__ == "__main__":
    main()
