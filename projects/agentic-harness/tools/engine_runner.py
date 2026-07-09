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


def run_engine(engine_args, cwd, env=None, timeout=600, trace_path=None, stream=True, label=""):
    """Run the engine (engine_args = full argv), tee-ing output. Writes BUILD_TRACE.md if trace_path is given.
    Returns (returncode, raw_output). rc 124 on timeout."""
    buf = []
    killed = {"v": False}
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
                sys.stdout.write("    | " + line); sys.stdout.flush()
        proc.wait()
    finally:
        timer.cancel()
    out = "".join(buf)
    narr = _narrate(out, label)

    if stream and narr:
        sys.stdout.write("\n" + narr + "\n"); sys.stdout.flush()
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
                sys.stdout.write("    +-- full trace + interpretation -> %s\n" % trace_path); sys.stdout.flush()
        except Exception:
            pass
    return (124 if killed["v"] else proc.returncode), out
