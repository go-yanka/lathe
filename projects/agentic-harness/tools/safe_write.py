"""A1 — safe file writes for the agentic harness.

Three guarantees, each fixing a real failure mode we hit or that a prior agent guards against:
  1. ATOMIC  — write to a temp file in the same dir, then os.replace(). A crash mid-write
               never leaves a half-written / corrupt file.
  2. SYNTAX-VERIFIED — before writing a .py, ast.parse() the new content. If it doesn't
               parse, the write is REJECTED and the original file is untouched. This alone
               rejects the exact corruption class from tonight (`rom fastapi`, 268x dup imports):
               broken Python can no longer reach disk.
  3. DENY-LIST — never write to credentials / system / .git internals (ported pattern from
               a prior agent `agent/file_safety.py`, re-pointed to harness-relevant paths).

Pairs with A0 checkpoint (snapshot before a build step; safe_write blocks bad writes;
if something still slips, restore()).

Usage:
    ok, err = safe_write("api/app.py", new_source)   # ok=False + err if unsafe
"""
import ast
import os
import tempfile

# Basenames that must never be overwritten (credentials / secrets).
_DENY_BASENAMES = {
    ".env", "id_rsa", "id_ed25519", "id_dsa", "credentials", ".pgpass",
    ".netrc", ".htpasswd", ".npmrc", ".pypirc", "secrets.yaml", "secrets.json",
}
# Path fragments that must never be written into.
_DENY_FRAGMENTS = (
    os.sep + ".ssh" + os.sep, os.sep + ".aws" + os.sep, os.sep + ".gnupg" + os.sep,
    os.sep + ".git" + os.sep,
)


def is_write_denied(path: str) -> bool:
    """True if `path` points at a credential / secret / system / .git-internal file."""
    p = os.path.abspath(path)
    low = p.lower()
    if os.path.basename(p) in _DENY_BASENAMES:
        return True
    if any(frag in p for frag in _DENY_FRAGMENTS):
        return True
    # System roots
    if low.startswith(r"c:\windows") or p.startswith("/etc/") or p.startswith("/usr/") or p.startswith("/boot/"):
        return True
    return False


def verify_python(content: str):
    """Return None if `content` is valid Python, else a one-line error string."""
    try:
        ast.parse(content)
        return None
    except SyntaxError as e:
        return f"SyntaxError: {e.msg} (line {e.lineno})"


def safe_write(path: str, content: str, verify_syntax: bool = True):
    """Atomically write `content` to `path`, with safety checks.
    Returns (ok: bool, error: str). On any failure the original file is untouched."""
    if is_write_denied(path):
        return False, f"write denied: {path} is a protected (credential/system/.git) path"

    if verify_syntax and path.endswith(".py"):
        err = verify_python(content)
        if err:
            return False, f"refused to write broken Python to {os.path.basename(path)}: {err}"

    d = os.path.dirname(os.path.abspath(path)) or "."
    try:
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".part")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)   # atomic on the same filesystem
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    except OSError as e:
        return False, f"write failed: {e}"
    return True, ""
