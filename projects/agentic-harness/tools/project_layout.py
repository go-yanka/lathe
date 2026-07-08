"""project_layout.py — MASTER_PLAN F4: conventional code/docs/scripts/config layout for MULTI-FILE projects.

A single-goal workspace (one artifact + GOAL.md/README) stays flat — that is the common path and F1 already
covers it. But when a build produces a genuine multi-FILE project (several code files plus docs/scripts/config),
a flat dump is hard to navigate. F4 classifies the files into the conventional buckets, writes a PROJECT.md map,
and can physically organize them into subdirs. Pure classification + a safe writer/mover so a gate can prove it.

Only triggers for real projects: `is_multifile_project` requires MULTIPLE code files (2+), so a lone artifact
never gets reorganized. Physical organization is opt-in (the engine passes apply=True under LATHE_PROJECT_LAYOUT);
by default only the documentary PROJECT.md is written, which never breaks a relative reference.
"""

import os
import shutil

# extension / name -> bucket. Order of checks: explicit names, then scripts, config, docs, else code.
_DOC_EXT = {".md", ".rst", ".txt", ".adoc"}
_SCRIPT_EXT = {".sh", ".bash", ".bat", ".ps1", ".cmd"}
_CONFIG_EXT = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".properties"}
_DOC_NAMES = {"readme", "goal", "changelog", "license", "contributing", "notice", "project"}
_CONFIG_NAMES = {"dockerfile", "makefile", ".gitignore", ".editorconfig"}
BUCKETS = ("code", "docs", "scripts", "config")


def classify(filename):
    """Return the bucket ('code'|'docs'|'scripts'|'config') for a file name."""
    base = os.path.basename(filename)
    stem, ext = os.path.splitext(base)
    low = base.lower()
    ext = ext.lower()
    if low in _CONFIG_NAMES:
        return "config"
    if stem.lower() in _DOC_NAMES:
        return "docs"
    if ext in _SCRIPT_EXT:
        return "scripts"
    if ext in _CONFIG_EXT:
        return "config"
    if ext in _DOC_EXT:
        return "docs"
    return "code"


def plan_layout(files):
    """Group files by bucket. Returns {bucket: [files...]} for buckets that have any file."""
    out = {}
    for f in files or []:
        out.setdefault(classify(f), []).append(f)
    return out


def is_multifile_project(files):
    """True only for a GENUINE multi-file project: 2+ code files (a lone artifact + its docs is NOT one)."""
    plan = plan_layout(files)
    return len(plan.get("code", [])) >= 2


def project_md(name, categorized):
    """A PROJECT.md that maps the layout by bucket."""
    lines = ["# %s" % (name or "project"), "",
             "A Lathe multi-file project. Files are organized by role:", ""]
    for b in BUCKETS:
        items = categorized.get(b)
        if not items:
            continue
        lines.append("## %s/" % b)
        for f in sorted(os.path.basename(x) for x in items):
            lines.append("- `%s`" % f)
        lines.append("")
    return "\n".join(lines)


def organize(ws_abs, files, apply=False):
    """Plan (and if apply=True, perform) the move of each file into its bucket subdir under ws_abs. Always
    writes PROJECT.md describing the resulting layout. Returns {"moves": [(src, dst)...], "project_md": path}.
    Never raises on an individual move (best-effort); a project doc must not break a build."""
    cat = plan_layout(files)
    moves = []
    for bucket, items in cat.items():
        for src in items:
            dst = os.path.join(ws_abs, bucket, os.path.basename(src))
            moves.append((src, dst))
            if apply and os.path.abspath(src) != os.path.abspath(dst):
                try:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.move(src, dst)
                except OSError:
                    pass
    # PROJECT.md reflects the bucketed basenames regardless of apply (documentary map).
    pth = os.path.join(ws_abs, "PROJECT.md")
    try:
        with open(pth, "w", encoding="utf-8") as f:
            f.write(project_md(os.path.basename(ws_abs.rstrip(os.sep)), cat))
    except OSError:
        pth = None
    return {"moves": moves, "project_md": pth}
