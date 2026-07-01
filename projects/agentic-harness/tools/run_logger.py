"""run_logger — structured, per-run JSONL logs so a REPORTED BUG IS SELF-DIAGNOSING.

Before this, "logging" was ~120 bare prints to stdout + scattered artifacts; a bug report was a stdout paste
with no full trace. Now every engine run gets a run_id and a `runs/<run_id>.jsonl` capturing each stage (start,
every model call with tokens+latency, per-function verdict, integration, regression, result). Secrets are
redacted (never write an API key to disk). Old runs rotate. `lathe logs` reads them. The run_id also tags the
metrics row, so triage = "send me runs/<id>.jsonl".

Env: LATHE_LOG_DIR (default <harness>/runs), LATHE_LOG_KEEP (default 100 runs), LATHE_LOG (1=on, default on).
"""
import json
import os
import time
import glob

_HERE = os.path.dirname(os.path.abspath(__file__))                 # .../projects/agentic-harness/tools
_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "runs")   # .../projects/agentic-harness/runs

try:
    from log_redact import redact_secrets                          # the harness-BUILT pure redactor
except Exception:
    def redact_secrets(s):
        return s if isinstance(s, str) else ""


def log_dir():
    return os.environ.get("LATHE_LOG_DIR") or _DEFAULT


def enabled():
    return os.environ.get("LATHE_LOG", "1") != "0"


def new_run_id():
    return time.strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(2).hex()   # sortable + collision-safe (no random import)


def _redact_val(v):
    return redact_secrets(v) if isinstance(v, str) else v


def log(run_id, event, **fields):
    """Append one JSONL entry {ts, run_id, event, ...redacted fields}. Best-effort: logging must never crash a build."""
    if not run_id or not enabled():
        return
    try:
        d = log_dir()
        os.makedirs(d, exist_ok=True)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "run_id": run_id, "event": event}
        for k, v in fields.items():
            rec[k] = _redact_val(v)
        with open(os.path.join(d, run_id + ".jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def rotate(keep=None):
    """Keep only the newest `keep` run logs (default LATHE_LOG_KEEP or 100). Cleanliness: logs don't accumulate forever."""
    try:
        keep = keep or int(os.environ.get("LATHE_LOG_KEEP", "100"))
        files = sorted(glob.glob(os.path.join(log_dir(), "*.jsonl")), key=os.path.getmtime, reverse=True)
        for old in files[keep:]:
            try: os.remove(old)
            except OSError: pass
    except Exception:
        pass


def list_runs():
    """Run ids, newest first."""
    try:
        fs = sorted(glob.glob(os.path.join(log_dir(), "*.jsonl")), key=os.path.getmtime, reverse=True)
        return [os.path.splitext(os.path.basename(p))[0] for p in fs]
    except Exception:
        return []


def read_run(run_id):
    """The parsed JSONL entries of one run (list of dicts)."""
    out = []
    try:
        with open(os.path.join(log_dir(), run_id + ".jsonl"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try: out.append(json.loads(line))
                    except Exception: pass
    except OSError:
        pass
    return out
