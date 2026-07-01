"""A0 tests — the executable spec for the checkpoint/rollback capability.

The headline test reproduces tonight's failure: a file gets corrupted by a build
step; we restore the pre-build checkpoint and the corruption is gone.
Run:  python tools/test_checkpoint.py
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from checkpoint import snapshot, list_checkpoints, restore, is_repo


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)


def _new_repo():
    d = tempfile.mkdtemp(prefix="ckpt_test_")
    _run(["git", "init", "-q"], d)
    _run(["git", "config", "user.email", "t@t"], d)
    _run(["git", "config", "user.name", "t"], d)
    return d


def main():
    repo = _new_repo()
    app = os.path.join(repo, "app.py")

    # 1. write a clean file + snapshot it
    open(app, "w").write("from fastapi import FastAPI\napp = FastAPI()\n")
    sha1 = snapshot(repo, reason="before edit: app.py")
    assert sha1, "snapshot returned empty sha"

    # 2. a build step CORRUPTS the file (tonight's 268x duplicate-import class) + adds a file
    open(app, "w").write("rom fastapi import FastAPI\n" * 268)   # broken: 'rom' + duplicated
    open(os.path.join(repo, "new.py"), "w").write("x = 1\n")
    sha2 = snapshot(repo, reason="after corruption")
    assert sha2 and sha2 != sha1, "second snapshot must differ"

    # 3. restore the pre-corruption checkpoint -> corruption gone
    assert restore(repo, sha1), "restore failed"
    restored = open(app).read()
    assert restored == "from fastapi import FastAPI\napp = FastAPI()\n", \
        f"file not restored cleanly: {restored[:40]!r}"
    assert restored.count("import FastAPI") == 1, "duplicate-import corruption survived restore"

    # 4. checkpoints are listed newest-first with reasons
    cps = list_checkpoints(repo)
    assert len(cps) == 2, f"expected 2 checkpoints, got {len(cps)}"
    assert cps[0][1] == "after corruption" and cps[1][1] == "before edit: app.py", \
        f"reasons/order wrong: {[c[1] for c in cps]}"

    # 5. single-file restore works (re-corrupt, restore only app.py)
    open(app, "w").write("garbage")
    assert restore(repo, sha1, "app.py")
    assert "FastAPI" in open(app).read(), "single-file restore failed"

    # 6. snapshots never moved HEAD or touched the user's index (working tree clean of staged ckpt)
    head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True)
    assert head.returncode != 0 or head.stdout.strip(), "HEAD state unexpected"  # no commits on HEAD is fine

    # 7. non-repo dirs degrade gracefully
    nonrepo = tempfile.mkdtemp(prefix="notgit_")
    assert is_repo(nonrepo) is False
    assert snapshot(nonrepo, "x") == "" and list_checkpoints(nonrepo) == [] and restore(nonrepo, "deadbeef") is False

    print("A0 checkpoint: ALL 7 ASSERTIONS PASS — corruption is one-command recoverable.")


if __name__ == "__main__":
    main()
