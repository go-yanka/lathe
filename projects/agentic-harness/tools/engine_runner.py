"""engine_runner.py — the ONE way every workflow runs the engine (no more per-caller drift).

Every user-facing path that builds (`do`, `auto`, `build`, `run`, `selftest`) now goes through here, so they
ALL get the same three things instead of a few:
  1. LIVE stream — the engine's play-by-play echoed to the terminal (nested under the CLI with a `│` prefix),
  2. PLAIN-ENGLISH interpretation — build_narrator's human summary printed after the run,
  3. a persisted BUILD_TRACE.md holding BOTH the plain-English summary and the full technical output.
A watchdog timer bounds a hung engine. Returns (returncode, raw_output). Never raises out.
"""

import os
import subprocess
import sys
import threading


def _narrate(raw, label):
    try:
        import importlib.util
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_narrator.py")
        s = importlib.util.spec_from_file_location("build_narrator", p)
        m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        return m.interpret(raw, label)
    except Exception:
        return ""


def _write(s):
    """Encoding-SAFE stdout write: on a Windows cp1252 terminal a Unicode char (em-dash, arrow) in the engine's
    output used to raise UnicodeEncodeError and KILL the live stream mid-run — so the operator saw a few lines
    then nothing. Never let a stray glyph break observability."""
    try:
        sys.stdout.write(s)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        sys.stdout.write(s.encode(enc, "replace").decode(enc, "replace"))
    try:
        sys.stdout.flush()
    except Exception:
        pass


def run_engine(engine_args, cwd, env=None, timeout=600, trace_path=None, stream=True, label=""):
    """Run the engine (engine_args = full argv), tee-ing output. Writes BUILD_TRACE.md if trace_path is given.
    Returns (returncode, raw_output). rc 124 on timeout."""
    try:
        sys.stdout.reconfigure(errors="replace")   # belt-and-suspenders: never crash the stream on a glyph
    except Exception:
        pass
    buf = []
    killed = {"v": False}
    # CRITICAL for LIVE streaming: when the engine's stdout is a PIPE (as here), Python BLOCK-buffers it, so we
    # would receive nothing until the engine EXITS — invisible for minutes on a slow build. Force the child
    # unbuffered so every print() flushes immediately and the operator watches it happen in real time.
    env = dict(env or os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    try:
        proc = subprocess.Popen(engine_args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", env=env, bufsize=1)
    except Exception as e:
        sys.stderr.write("engine spawn error: %s\n" % e)
        return 1, ""

    def _kill():
        killed["v"] = True
        try:
            proc.kill()
        except Exception:
            pass
    timer = threading.Timer(timeout, _kill); timer.start()
    try:
        for line in proc.stdout:
            buf.append(line)
            if stream:
                _write("    | " + line)
        proc.wait()
    finally:
        timer.cancel()
    out = "".join(buf)
    narr = _narrate(out, label)

    if stream and narr:
        _write("\n" + narr + "\n")
    if trace_path:
        try:
            if os.path.dirname(trace_path):
                os.makedirs(os.path.dirname(trace_path), exist_ok=True)
            with open(trace_path, "w", encoding="utf-8") as tf:
                tf.write("# BUILD TRACE\n\n")
                if label:
                    tf.write("**%s**\n\n" % label)
                tf.write("## Plain English (what happened + what it means)\n\n")
                tf.write((narr or "(no interpretation available)") + "\n\n")
                tf.write("## Full engine output (technical)\n\n```\n" + out.strip() + "\n```\n")
            if stream:
                _write("    +-- full trace + interpretation -> %s\n" % trace_path)
        except Exception:
            pass
    return (124 if killed["v"] else proc.returncode), out
