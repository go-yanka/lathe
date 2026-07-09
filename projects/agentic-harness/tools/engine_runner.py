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


import re as _re


def _clean_line(line):
    """Translate ONE raw engine line into a readable STEP, or None to SUPPRESS it. Turns the firehose
    (tracebacks, JSON, headers, paths) into a human workflow view: what step, what happened, loop-backs."""
    st = line.strip()
    if not st:
        return None
    # suppress raw noise
    if st.startswith(("File \"", "Traceback", "assert ", "AssertionError", "{", "metrics ->", "local tokens",
                      "run report:", "program written", "integration:", "regression:", "===METRICS")):
        return None
    if st.startswith("=== ENGINE:"):
        return "  building the page ..."
    if "[spec<->test WARNING]" in st:
        return "  ! the acceptance test disagreed with the spec - reconciling ..."
    if "[spec<->test REFINED]" in st:
        return "  ok - reconciled the test with the spec, then building"
    if "[spec<->test UNRESOLVED" in st:
        return "  ! couldn't reconcile the test (thinker busy) - building anyway"
    if "[targeted repair]" in st:
        m = _re.search(r"attempt (\d+)", st)
        return "  -> fixing the exact problem and retrying (attempt %s) ..." % (m.group(1) if m else "?")
    m = _re.search(r"\[attempt (\d+) FAILED . why: (.+?)\]?\s*$", st)
    if m:
        from build_narrator import _layman as _lm  # translate the technical reason to plain English
        return "  x attempt %s failed: %s" % (m.group(1), _lm(m.group(2)))
    if "artifact" in st and "functional=yes" in st:
        return "  ok - built and passed the checks"
    if st.startswith("..") and "still working" in st:              # analyst heartbeat - keep, it shows progress
        return "  " + st.strip(". ").strip()
    if "SUCCESS" in st or "NOTHING SHIPPED" in st:                 # the per-cycle summary is shown at the end instead
        return None
    return None                                                    # default: suppress in clean mode


def run_engine(engine_args, cwd, env=None, timeout=600, trace_path=None, stream=True, label=""):
    """Run the engine (engine_args = full argv), tee-ing output. Writes BUILD_TRACE.md if trace_path is given.
    Returns (returncode, raw_output). rc 124 on timeout.

    Streaming mode (LATHE_STREAM_ENGINE): 'clean' (default) shows a readable STEP view; 'raw'/'1'/'verbose'
    shows the full engine firehose; '0'/'off' is silent. The full raw output always lands in BUILD_TRACE.md."""
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
    _mode = os.environ.get("LATHE_STREAM_ENGINE", "clean").lower()
    _silent = (not stream) or _mode in ("0", "off", "false")
    _raw = _mode in ("raw", "1", "true", "verbose", "on")     # firehose; else CLEAN human-step view (default)
    timer = threading.Timer(timeout, _kill); timer.start()
    _in_metrics = {"v": False}                                # the ===METRICS_JSON_BEGIN...END block
    try:
        for line in proc.stdout:
            buf.append(line)
            if _silent:
                continue
            if _raw:
                _write("    | " + line)
            else:                                             # CLEAN: readable step lines, noise suppressed —
                # EXCEPT the METRICS_JSON block: it is a machine-readable CONTRACT that CI + tooling parse from
                # `lathe build` stdout, so it must pass through verbatim even in the clean view (else CI breaks).
                if "===METRICS_JSON_BEGIN===" in line:
                    _in_metrics["v"] = True
                if _in_metrics["v"]:
                    _write(line if line.endswith("\n") else line + "\n")
                    if "===METRICS_JSON_END===" in line:
                        _in_metrics["v"] = False
                    continue
                cl = _clean_line(line)
                if cl is not None:
                    _write(cl + "\n")
        proc.wait()
    finally:
        timer.cancel()
    out = "".join(buf)
    narr = _narrate(out, label)

    # In RAW mode print the full plain-English block; in CLEAN mode the step lines already told the story, and a
    # per-cycle summary (there can be two — a failed build then a repaired one) would re-add the confusion.
    if _raw and narr:
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
            if not _silent:
                _write("    (full technical log saved -> %s)\n" % os.path.relpath(trace_path, os.getcwd()) if trace_path else trace_path)
        except Exception:
            pass
    return (124 if killed["v"] else proc.returncode), out
