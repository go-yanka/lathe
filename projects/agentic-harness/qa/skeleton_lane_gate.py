"""skeleton_lane_gate.py — the v2.26 post-mortem gate (owner: "how do we stop this stupidness").

ROOT CAUSE it guards: the artifact generation path serves TWO contracts (whole-file, region-fill). A change
reasoned about one lane silently broke the other — the engine sent whole-file orders to skeleton fills, the
model OBEYED, and 9 builds failed with the model wrongly blamed. No standing gate covered the skeleton lane,
so the regression shipped green.

This gate runs BOTH lanes against a deterministic local stub implementer (no real model, ~2s) and asserts:
  P1  the skeleton-lane request carries the REGION-FILL contract (never the whole-file contract)
  P2  the whole-file-lane request carries the WHOLE-FILE contract
  P3  splice correctness: marker replaced, fill present, marker ECHO stripped, scaffold intact
  P4  salvage: preamble chatter before <!doctype is stripped from a whole-file reply
"""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

QA = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(QA)))
TOOLS = os.path.join(os.path.dirname(QA), "tools")

REQUESTS = []          # captured prompts, in arrival order

FILL_REPLY = "const PROBE_A = 1; // __FILL__"                     # echoes the marker on purpose (P3)
WHOLE_REPLY = ("Sure thing! Here is the complete file you asked for:\n"
               "<!doctype html><html><body><canvas id='c'></canvas>"
               "<script>const WHOLE_PROBE = 1;</script></body></html>")


class _Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        prompt = " ".join(str(m.get("content", "")) for m in body.get("messages", []))
        REQUESTS.append(prompt)
        content = FILL_REPLY if "completing ONE bounded region" in prompt else WHOLE_REPLY
        out = json.dumps({"choices": [{"message": {"content": content}}],
                          "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


SKEL_PLAN = '''OUT_DIR = "projects/agentic-harness/goals/_skelgate"
MODULE_NAME = "skelgate_probe"
HEADER = ""
GLUE = ""
FUNCTIONS = []
ARTIFACTS = [
    {
        "path": "_artifacts/probe.html",
        "model": "openai:local",
        "prompt": "Provide the constants for the fill region. Output ONLY the region content - no HTML tags, no prose, no markdown.",
        "tests": [
            "assert 'PROBE_A' in content",
            "assert '__fill__' not in content.lower()",
            "assert 'scaffold_ok' in content",
            "assert content.lower().startswith('<!doctype')",
        ],
        "skeleton": """<!DOCTYPE html>
<html><body><canvas id="board"></canvas>
<script>
/* scaffold_ok */
__FILL__
console.log(PROBE_A);
</script></body></html>
""",
    }
]
'''

WHOLE_PLAN = '''OUT_DIR = "projects/agentic-harness/goals/_skelgate2"
MODULE_NAME = "skelgate_probe2"
HEADER = ""
GLUE = ""
FUNCTIONS = []
ARTIFACTS = [
    {
        "path": "_artifacts/whole.html",
        "model": "openai:local",
        "prompt": "Create a minimal page with a canvas. Output ONLY the file contents - no prose, no markdown.",
        "tests": [
            "assert content.lower().startswith('<!doctype')",
            "assert '<canvas' in content.lower()",
            "assert 'WHOLE_PROBE' in content",
            "assert 'sure thing' not in content.lower()",
        ],
    }
]
'''


def main():
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    plans_dir = os.path.join(os.path.dirname(QA), "plans")
    p1 = os.path.join(plans_dir, "_skelgate_plan.py")
    p2 = os.path.join(plans_dir, "_skelgate_plan2.py")
    ce = tempfile.mkdtemp(prefix="skelgate_ce_")
    env = dict(os.environ)
    env.update({"LOCAL_OPENAI_URL": "http://127.0.0.1:%d/v1/chat/completions" % port,
                "LATHE_CE_DIR": ce, "LATHE_VALIDATE_PLAN": "1",
                "LATHE_VALIDATOR_PY": os.path.join(TOOLS, "plan_validator.py"),
                "LATHE_TRIES": "1"})
    ok = []
    try:
        open(p1, "w", encoding="utf-8").write(SKEL_PLAN)
        open(p2, "w", encoding="utf-8").write(WHOLE_PLAN)
        for plan in (p1, p2):
            r = subprocess.run([sys.executable, os.path.join(ROOT, "engine_v2.py"), plan, "openai:local", "1"],
                               cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=180, env=env)
            if "artifacts implemented: 1/1" not in (r.stdout or ""):
                print("skeleton-lane gate: BUILD FAILED for %s\n%s" % (os.path.basename(plan),
                                                                       "\n".join((r.stdout or "").splitlines()[-6:])))
                sys.exit(1)
        skel_reqs = [q for q in REQUESTS if "completing ONE bounded region" in q]
        whole_reqs = [q for q in REQUESTS if "raw file content" in q]
        assert skel_reqs and "raw file content" not in skel_reqs[0], "P1 skeleton lane got the WRONG contract"
        ok.append("P1 fill-contract routed")
        assert whole_reqs, "P2 whole-file lane missing its contract"
        ok.append("P2 whole-file contract routed")
        out1 = open(os.path.join(ROOT, "projects", "agentic-harness", "goals", "_skelgate",
                                 "_artifacts", "probe.html"), encoding="utf-8").read()
        assert "PROBE_A" in out1 and "__FILL__" not in out1 and "scaffold_ok" in out1, "P3 splice/echo-strip broken"
        ok.append("P3 splice + echo-strip")
        out2 = open(os.path.join(ROOT, "projects", "agentic-harness", "goals", "_skelgate2",
                                 "_artifacts", "whole.html"), encoding="utf-8").read()
        assert out2.lower().startswith("<!doctype") and "Sure thing" not in out2, "P4 salvage broken"
        ok.append("P4 preamble salvage")
    finally:
        srv.shutdown()
        for f in (p1, p2):
            try: os.remove(f)
            except OSError: pass
        for d in ("_skelgate", "_skelgate2"):
            shutil.rmtree(os.path.join(ROOT, "projects", "agentic-harness", "goals", d), ignore_errors=True)
        shutil.rmtree(ce, ignore_errors=True)
    print("skeleton-lane gate: %d/4 probes pass (%s)" % (len(ok), "; ".join(ok)))
    sys.exit(0 if len(ok) == 4 else 1)


if __name__ == "__main__":
    main()
