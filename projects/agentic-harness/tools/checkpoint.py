"""A0 — lean git-backed checkpoint / rollback for the agentic harness.

The corruption insurance. Snapshots the FULL working tree before a risky build step,
WITHOUT touching HEAD or the user's git index — so any bad edit (the 268x app.py
corruption class we hit) is one-command recoverable.

Snapshots are stored as a commit log on refs/harness/ckpt. They never move HEAD,
never stage into the user's index, and don't show up in `git log` (they live on a
dedicated ref), so they're invisible until you ask for them.

Inspired by a prior agent `tools/checkpoint_manager.py`, reduced to the essential
snapshot/list/restore via plumbing commands. ~70 LOC, no deps beyond git + stdlib.

Usage:
    from checkpoint import snapshot, list_checkpoints, restore
    sha = snapshot(repo, reason="before write_file: api/app.py")
    ...                                   # a build step corrupts a file
    restore(repo, sha)                    # everything back to the snapshot
    restore(repo, sha, "api/app.py")      # or just one file
"""
import os
import subprocess
import tempfile
import time

CKPT_REF = "refs/harness/ckpt"


def _git(args, repo, env=None):
    return subprocess.run(["git", "-C", repo] + args, capture_output=True, text=True, env=env)


def is_repo(repo: str) -> bool:
    return _git(["rev-parse", "--is-inside-work-tree"], repo).returncode == 0


def snapshot(repo: str, reason: str = "auto") -> str:
    """Snapshot the full working tree to a checkpoint commit. Returns its sha ('' on failure).
    Uses a private temp index (GIT_INDEX_FILE) so the user's staging area is untouched."""
    if not is_repo(repo):
        return ""
    idx = os.path.join(tempfile.gettempdir(), f".harness_ckpt_index_{os.getpid()}_{int(time.time()*1000)}")
    env = dict(os.environ, GIT_INDEX_FILE=idx)
    try:
        if _git(["add", "-A"], repo, env=env).returncode != 0:
            return ""
        tree = _git(["write-tree"], repo, env=env).stdout.strip()
        if not tree:
            return ""
        parent = _git(["rev-parse", "--verify", "-q", CKPT_REF], repo).stdout.strip()
        msg = f"ckpt: {reason} @ {int(time.time())}"
        cmd = ["commit-tree", tree, "-m", msg]
        if parent:
            cmd += ["-p", parent]
        sha = _git(cmd, repo, env=env).stdout.strip()
        if not sha:
            return ""
        _git(["update-ref", CKPT_REF, sha], repo)
        return sha
    finally:
        try:
            os.remove(idx)
        except OSError:
            pass


def list_checkpoints(repo: str, limit: int = 50):
    """Return [(sha, reason, epoch)] newest-first, or [] if none."""
    if not is_repo(repo):
        return []
    r = _git(["log", "--format=%H%x09%s", f"-{limit}", CKPT_REF], repo)
    if r.returncode != 0:
        return []
    out = []
    for ln in r.stdout.splitlines():
        if "\t" not in ln:
            continue
        sha, msg = ln.split("\t", 1)
        reason, epoch = msg, 0
        if msg.startswith("ckpt: ") and " @ " in msg:
            reason, _, e = msg[len("ckpt: "):].rpartition(" @ ")
            try:
                epoch = int(e)
            except ValueError:
                epoch = 0
        out.append((sha, reason, epoch))
    return out


def restore(repo: str, sha: str, path: str = None) -> bool:
    """Restore files from a checkpoint commit into the working tree.
    path=None restores the whole tree; otherwise just that path. Returns True on success."""
    if not is_repo(repo):
        return False
    return _git(["checkout", sha, "--", path if path else "."], repo).returncode == 0
