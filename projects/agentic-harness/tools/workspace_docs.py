"""workspace_docs.py — MASTER_PLAN F1: every goal workspace gets a human-readable GOAL.md + README.md.

A per-goal workspace holds the spec, artifacts, assumptions ledger, and machine dotfiles — but nothing that
tells a human (or a returning you) WHAT this folder is for at a glance. F1 adds two lean docs: GOAL.md (the
intent + the resolved assumptions + who was in the room) and README.md (what each file/dir is). Machine state
stays in dotfiles; these are the only prose. Pure string builders + a thin writer, so a gate can prove them.
"""

import os


def goal_md(goal, assumptions=None, panel=None, focus=None, intake_ran=True):
    """The intent brief for a workspace: the goal, the resolved assumptions it was built to, the panel.
    `intake_ran=False` means intake was SKIPPED (e.g. `--assume`): 'no assumptions' then means 'not looked
    for', NOT 'none found' — the doc must say so honestly instead of claiming the goal was specific."""
    lines = ["# GOAL", "", (goal or "").strip() or "(unstated)", ""]
    if focus:
        lines += ["**Focus:** %s" % focus, ""]
    if panel:
        lines += ["**Interview panel:** %s" % ", ".join(panel), ""]
    lines += ["## Resolved assumptions", ""]
    if assumptions:
        for a in assumptions:
            mat = (a.get("materiality", "") or "").upper()
            cat = a.get("category", "")
            lines.append("- [%s | %s] %s" % (mat, cat, a.get("text", "")))
    elif not intake_ran:
        lines.append("- (intake SKIPPED via --assume — assumptions were NOT surfaced; the build may have "
                     "guessed unstated choices)")
    else:
        lines.append("- (none surfaced — the goal was specific)")
    lines.append("")
    lines += ["> Built to these EXACTLY. If any is wrong, correct it and rebuild — do not silently re-decide.", ""]
    return "\n".join(lines)


def readme_md(ws_name=""):
    """A lean layout guide for a goal workspace."""
    return "\n".join([
        "# %s" % (ws_name or "goal workspace"),
        "",
        "A Lathe goal workspace. Everything for this one goal lives here.",
        "",
        "- `GOAL.md` — the intent + the resolved assumptions the build was made to.",
        "- `plan_*.py` — the spec(s) the analyst drafted for the implementer (data, not code you run).",
        "- `_artifacts/` — the built deliverable(s).",
        "- `ASSUMPTIONS.md` — the surfaced assumptions (human copy of the ledger).",
        "- dotfiles (`.assumptions.json`, `.pins*`) — machine state; leave them alone.",
        "",
        "Rebuild: `lathe build <plan_*.py>`  ·  see the goal: open `GOAL.md`.",
        "",
    ])


def write_workspace_docs(ws_abs, goal, assumptions=None, panel=None, focus=None, intake_ran=True):
    """Write GOAL.md + README.md into an existing workspace dir. Returns the paths written. Never raises on a
    per-file error (best-effort docs must not break a build); raises only if the dir itself is unusable."""
    written = []
    for name, text in (("GOAL.md", goal_md(goal, assumptions, panel, focus, intake_ran)),
                       ("README.md", readme_md(os.path.basename(ws_abs.rstrip(os.sep))))):
        p = os.path.join(ws_abs, name)
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
            written.append(p)
        except OSError:
            pass
    return written
